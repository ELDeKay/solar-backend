from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://mysolarfollower.onrender.com"]
    }
})

# ---------------------------
# Globale Zustände (RAM)
# ---------------------------
datenbank = []

aktueller_status = False  # manuell / automatisch
schneeModus = False
calibration = False

letzte_coord = {"latitude": None, "longitude": None}
letzte_ip = {"ipWLANschuko": None}
letzte_motor_Zielwert = {"motor1_Zielwert": None, "motor2_Zielwert": None}
letzte_werkseinstellungbool = False

# ✅ Heartbeat (Website lebt?)
last_heartbeat = 0.0  # unix time in seconds


# ---------------------------
# POST: Wetterdaten vom Pico
# ---------------------------
@app.route("/api/getdata", methods=["POST"])
def receive_getdata():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "no data found"}), 400

    MAX_ENTRIES = 1000

    datenbank.append({
        "wind": data.get("wind"),
        "sunrise": data.get("sunrise"),
        "sunset": data.get("sunset"),
        "sunhours": data.get("sunhours"),
        "motor1": data.get("motor1"),
        "motor2": data.get("motor2"),
        "manuell": data.get("manuell"),
        "voltage": data.get("voltage"),
        "current": data.get("current"),
        "einstellungen": data.get("einstellungen"),
        "zeit": data.get("zeit")  # Pico-Zeit
    })

    if len(datenbank) > MAX_ENTRIES:
        datenbank.pop(0)

    return jsonify({"status": "ok"}), 200


# ---------------------------
# GET: Wetterdaten abrufen (für Website)
# ---------------------------
@app.route("/api/data", methods=["GET"])
def get_data():
    return jsonify(datenbank), 200


# ---------------------------
# POST: Motor-Zielwerte von Website
# ---------------------------
@app.route("/api/motor_Zielwert", methods=["POST"])
def set_motor_Zielwert():
    data = request.get_json(silent=True) or {}

    m1 = data.get("motor1_Zielwert")
    m2 = data.get("motor2_Zielwert")

    if m1 is None and m2 is None:
        return jsonify({"error": "motor1_Zielwert/motor2_Zielwert fehlen"}), 400

    try:
        if m1 is not None:
            letzte_motor_Zielwert["motor1_Zielwert"] = int(m1)
        if m2 is not None:
            letzte_motor_Zielwert["motor2_Zielwert"] = int(m2)
    except (TypeError, ValueError):
        return jsonify({"error": "Motor Zielwerte müssen Integer sein"}), 400

    return jsonify({"status": "ok"}), 200


# ---------------------------
# ✅ POST/OPTIONS: Heartbeat von Website (Steuerung.html)
# ---------------------------
@app.route("/api/heartbeat", methods=["POST", "OPTIONS"])
def heartbeat():
    global last_heartbeat

    # Preflight für CORS
    if request.method == "OPTIONS":
        return ("", 200)

    # JSON ist optional – wir werten es nicht streng aus
    _data = request.get_json(silent=True) or {}

    last_heartbeat = time.time()
    return jsonify({"status": "ok", "last_heartbeat": last_heartbeat}), 200


# ---------------------------
# POST: Koordinaten +/oder IP +/oder Factory Reset
# ---------------------------
@app.route("/api/einstellungen", methods=["POST"])
def set_koordinaten_und_ip():
    global letzte_werkseinstellungbool

    data = request.get_json(silent=True) or {}

    lat = data.get("latitude")
    lon = data.get("longitude")
    ipWLAN = data.get("ipWLANschuko")
    werkseinstellungbool = data.get("werkseinstellungbool")

    if lat is not None or lon is not None:
        if lat is None or lon is None:
            return jsonify({"error": "latitude und longitude müssen zusammen gesendet werden"}), 400
        try:
            letzte_coord["latitude"] = float(lat)
            letzte_coord["longitude"] = float(lon)
        except (TypeError, ValueError):
            return jsonify({"error": "latitude/longitude müssen Zahlen sein"}), 400

    if ipWLAN is not None:
        ipWLAN = str(ipWLAN).strip()
        if ipWLAN == "":
            return jsonify({"error": "ipWLANschuko darf nicht leer sein"}), 400
        letzte_ip["ipWLANschuko"] = ipWLAN

    if werkseinstellungbool is not None:
        if not isinstance(werkseinstellungbool, bool):
            return jsonify({"error": "werkseinstellungbool muss true/false sein"}), 400
        letzte_werkseinstellungbool = werkseinstellungbool

    if (lat is None and lon is None and ipWLAN is None and werkseinstellungbool is None):
        return jsonify({"error": "keine gültigen Felder gesendet"}), 400

    return jsonify({
        "status": "ok",
        "latitude": letzte_coord.get("latitude"),
        "longitude": letzte_coord.get("longitude"),
        "ipWLANschuko": letzte_ip.get("ipWLANschuko"),
        "werkseinstellungbool": letzte_werkseinstellungbool
    }), 200


# ---------------------------
# GET: Alles für den Pico
# ---------------------------
@app.route("/api/einstellungen", methods=["GET"])
def einstellungen_get():
    global calibration, aktueller_status, schneeModus, last_heartbeat

    # ✅ Auto-Reset wenn Website weg ist (kein Heartbeat > 60s)
    if (aktueller_status or schneeModus):
        if last_heartbeat == 0.0 or (time.time() - last_heartbeat) > 60:
            aktueller_status = False
            schneeModus = False

    calib_value = calibration
    calibration = False  # Event verbrauchen

    return jsonify({
        "latitude": letzte_coord.get("latitude"),
        "longitude": letzte_coord.get("longitude"),
        "ipWLANschuko": letzte_ip.get("ipWLANschuko"),
        "motor1_Zielwert": letzte_motor_Zielwert.get("motor1_Zielwert"),
        "motor2_Zielwert": letzte_motor_Zielwert.get("motor2_Zielwert"),
        "manuell": aktueller_status,
        "werkseinstellungbool": letzte_werkseinstellungbool,
        "schneeModus": schneeModus,
        "calibration": calib_value
    }), 200


# ---------------------------
# POST: Manuell / Automatik (Steuerung.html)
# ---------------------------
@app.route("/api/manuell", methods=["POST"])
def manuell():
    global aktueller_status, schneeModus

    data = request.get_json(silent=True) or {}

    if "aktiv" in data:
        status = data.get("aktiv")
        if not isinstance(status, bool):
            return jsonify({"error": "aktiv muss true/false sein"}), 400
        aktueller_status = status

    if "schneeModus" in data:
        snow = data.get("schneeModus")
        if not isinstance(snow, bool):
            return jsonify({"error": "schneeModus muss true/false sein"}), 400
        schneeModus = snow

    if ("aktiv" not in data) and ("schneeModus" not in data):
        return jsonify({"error": "Sende 'aktiv' und/oder 'schneeModus'."}), 400

    return jsonify({"manuell": aktueller_status, "schneeModus": schneeModus}), 200


# ---------------------------
# POST: Calibration Event (Paneel Button)
# ---------------------------
@app.route("/api/calibra", methods=["POST"])
def calibration_post():
    global calibration

    data = request.get_json(silent=True) or {}

    if "calibration" not in data:
        return jsonify({"error": "Sende 'calibration'."}), 400

    if data.get("calibration") is not True:
        return jsonify({"error": "calibration muss true sein"}), 400

    calibration = True
    return jsonify({"status": "ok"}), 200


# ---------------------------
# Start
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
