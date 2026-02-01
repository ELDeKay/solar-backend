from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time

app = Flask(__name__)

# =========================================================
# CORS
# - Erlaubt Browser-Requests von deiner Website-Domain auf /api/*
# =========================================================
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://mysolarfollower.onrender.com"]
    }
})

# =========================================================
# Globale Zustände (RAM)

# datenbank: Liste mit den letzten Messdatensätzen vom Pico
datenbank = []

# manuell_status: Checkboxen für manuell/schneeModus (wird von der Website gesetzt,
#                 vom Pico über /api/einstellungen abgefragt)
manuell_status = False
schneeModus = False

# kalibrierung: einmaliges Event (True wird einmal an Pico geliefert und dann wieder False)
#               dient der Kalibrierung/Ausrichtung des Solarmoduls + Gerüst                             
kalibrierung = False

# letzte_coord / letzte_ip: letzte Konfigurationseinstellungen aus dem Frontend
letzte_coord = {"latitude": None, "longitude": None}
letzte_ip = {"ipWLANschuko": None}

# letzte_motor_Zielwert: Zielwerte, die das Frontend setzt und der Pico abholt
letzte_motor_Zielwert = {"motor1_Zielwert": None, "motor2_Zielwert": None}

# letzte_werkseinstellungbool: Factory-Reset-Checkbox (Frontend setzt bool, Pico liest Zustand)
letzte_werkseinstellungbool = False

# last_heartbeat: Unix-Zeitstempel, wann die Steuerungsseite zuletzt "lebt" gemeldet hat
last_heartbeat = 0.0


# =========================================================
# POST /api/getdata
# - Pico sendet Messdaten ans Backend
# - Backend speichert sie in datenbank (max. 1000 Einträge)
# =========================================================
@app.route("/api/getdata", methods=["POST"])
def receive_getdata():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "no data found"}), 400

    MAX_ENTRIES = 1000

    # Ein Datensatz aus dem Pico-JSON wird 1:1 in die In-Memory-Liste übernommen
    datenbank.append({
        "wind": data.get("wind"),
        "sonneauf": data.get("sonneauf"),
        "sonneunter": data.get("sonneunter"),
        "sonnenstunden": data.get("sonnenstunden"),
        "motor1": data.get("motor1"),
        "motor2": data.get("motor2"),
        "spannung": data.get("spannung"),
        "ampere": data.get("ampere"),
        "zeit": data.get("zeit")
    })

    # Speicher begrenzen: ältesten Eintrag entfernen, wenn zu viele vorhanden sind (um RAM nicht zu überlasten)
    if len(datenbank) > MAX_ENTRIES:
        datenbank.pop(0)

    return jsonify({"status": "ok"}), 200


# =========================================================
# GET /api/data
# - Website holen die gespeicherten Messdaten
# - Rückgabe: komplette datenbank-Liste (bis MAX_ENTRIES)
# =========================================================

@app.route("/api/data", methods=["GET"])
def get_data():
    return jsonify(datenbank), 200


# =========================================================
# POST /api/motor_Zielwert
# - Website setzt Zielwerte für Motor 1/2
# - Pico holt diese Werte später über GET /api/einstellungen
# =========================================================
@app.route("/api/motor_Zielwert", methods=["POST"])
def set_motor_Zielwert():
    data = request.get_json(silent=True) or {}

    m1 = data.get("motor1_Zielwert")
    m2 = data.get("motor2_Zielwert")

    # Mindestens ein Zielwert muss vorhanden sein
    if m1 is None and m2 is None:
        return jsonify({"error": "motor1_Zielwert/motor2_Zielwert fehlen"}), 400

    # Zielwerte in Integer umwandeln und speichern
    try:
        if m1 is not None:
            letzte_motor_Zielwert["motor1_Zielwert"] = int(m1)
        if m2 is not None:
            letzte_motor_Zielwert["motor2_Zielwert"] = int(m2)
    except (TypeError, ValueError):
        return jsonify({"error": "Motor Zielwerte müssen Integer sein"}), 400

    return jsonify({"status": "ok"}), 200


# =========================================================
# POST/OPTIONS /api/heartbeat
# - Steuerung.html sendet regelmäßig ein Lebenszeichen
# - last_heartbeat wird aktualisiert
# =========================================================
@app.route("/api/heartbeat", methods=["POST", "OPTIONS"])
def heartbeat():
    global last_heartbeat

    # Preflight für CORS
    if request.method == "OPTIONS":
        return ("", 200)

    # JSON ist optional – wird aktuell nicht ausgewertet
    _data = request.get_json(silent=True) or {}

    last_heartbeat = time.time()
    return jsonify({"status": "ok", "last_heartbeat": last_heartbeat}), 200


# =========================================================
# POST /api/einstellungen
# - Website setzt Einstellungen (Koordinaten, IP, Werkseinstellung)
# - Pico holt diese Werte später über GET /api/einstellungen
# =========================================================
@app.route("/api/einstellungen", methods=["POST"])
def set_koordinaten_und_ip():
    global letzte_werkseinstellungbool

    data = request.get_json(silent=True) or {}

    lat = data.get("latitude")
    lon = data.get("longitude")
    ipWLAN = data.get("ipWLANschuko")
    werkseinstellungbool = data.get("werkseinstellungbool")

    # Koordinaten nur gültig, wenn latitude und longitude zusammen gesetzt werden
    if lat is not None or lon is not None:
        if lat is None or lon is None:
            return jsonify({"error": "latitude und longitude müssen zusammen gesendet werden"}), 400
        try:
            letzte_coord["latitude"] = float(lat)
            letzte_coord["longitude"] = float(lon)
        except (TypeError, ValueError):
            return jsonify({"error": "latitude/longitude müssen Zahlen sein"}), 400

    # IP-Adresse speichern, wenn vorhanden und nicht leer
    if ipWLAN is not None:
        ipWLAN = str(ipWLAN).strip()
        if ipWLAN == "":
            return jsonify({"error": "ipWLANschuko darf nicht leer sein"}), 400
        letzte_ip["ipWLANschuko"] = ipWLAN

    # Werkseinstellung speichern, wenn boolean
    if werkseinstellungbool is not None:
        if not isinstance(werkseinstellungbool, bool):
            return jsonify({"error": "werkseinstellungbool muss true/false sein"}), 400
        letzte_werkseinstellungbool = werkseinstellungbool

    # Wenn nichts Sinnvolles mitgesendet wurde, Fehler zurückgeben
    if (lat is None and lon is None and ipWLAN is None and werkseinstellungbool is None):
        return jsonify({"error": "keine gültigen Felder gesendet"}), 400

    return jsonify({
        "status": "ok",
        "latitude": letzte_coord.get("latitude"),
        "longitude": letzte_coord.get("longitude"),
        "ipWLANschuko": letzte_ip.get("ipWLANschuko"),
        "werkseinstellungbool": letzte_werkseinstellungbool
    }), 200


# =========================================================
# GET /api/einstellungen
# - Pico fragt diese Route regelmäßig ab, um Steuerwerte zu bekommen
# - enthält:
#   - Koordinaten / IP / Werkseinstellungbool
#   - Motor-Zielwerte
#   - manuell_status / schneeModus
#   - Kalibrierung (einmaliges Event)
# - Auto-Reset von manueller Steuerung
# =========================================================
@app.route("/api/einstellungen", methods=["GET"])
def einstellungen_get():
    global kalibrierung, manuell_status, schneeModus, last_heartbeat

    # Auto-Reset wenn Website weg ist (kein Heartbeat > 60s)
    if (manuell_status or schneeModus):
        if last_heartbeat == 0.0 or (time.time() - last_heartbeat) > 60:
            manuell_status = False
            schneeModus = False

    # Kalibrierung als "Event": einmal liefern, danach wieder auf False setzen
    calib_value = kalibrierung
    kalibrierung = False

    return jsonify({
        "latitude": letzte_coord.get("latitude"),
        "longitude": letzte_coord.get("longitude"),
        "ipWLANschuko": letzte_ip.get("ipWLANschuko"),
        "motor1_Zielwert": letzte_motor_Zielwert.get("motor1_Zielwert"),
        "motor2_Zielwert": letzte_motor_Zielwert.get("motor2_Zielwert"),
        "manuell": manuell_status,
        "werkseinstellungbool": letzte_werkseinstellungbool,
        "schneeModus": schneeModus,
        "kalibrierung": calib_value
    }), 200


# =========================================================
# POST /api/manuell
# - Website schaltet manuell/automatik und/oder Schneemodus
# - erwartet boolean Felder:
#   - manuellModus
#   - schneeModus
# =========================================================
@app.route("/api/manuell", methods=["POST"])
def manuell():
    global manuell_status, schneeModus

    data = request.get_json(silent=True) or {}

    if "manuellModus" in data:
        status = data.get("manuellModus")
        if not isinstance(status, bool):
            return jsonify({"error": "manuellModus muss true/false sein"}), 400
        manuell_status = status

    if "schneeModus" in data:
        snow = data.get("schneeModus")
        if not isinstance(snow, bool):
            return jsonify({"error": "schneeModus muss true/false sein"}), 400
        schneeModus = snow

    if ("manuellModus" not in data) and ("schneeModus" not in data):
        return jsonify({"error": "Sende 'manuellModus' und/oder 'schneeModus'."}), 400

    return jsonify({"manuell": manuell_status, "schneeModus": schneeModus}), 200


# =========================================================
# POST /api/calibra
# - Paneel-Seite sendet ein Kalibrier-Event
# - Flag wird bei GET /api/einstellungen einmal an den Pico ausgeliefert
# =========================================================
@app.route("/api/calibra", methods=["POST"])
def kalibrierung_post():
    global kalibrierung

    data = request.get_json(silent=True) or {}

    if "kalibrierung" not in data:
        return jsonify({"error": "Sende 'kalibrierung'."}), 400

    if data.get("kalibrierung") is not True:
        return jsonify({"error": "kalibrierung muss true sein"}), 400

    kalibrierung = True
    return jsonify({"status": "ok"}), 200


# =========================================================
# Start (lokal)
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
