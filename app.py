from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time
import re

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


licht = False

last_heartbeat = 0.0

# letzte_coord: letzte Konfigurationseinstellungen aus dem Frontend
letzte_coord = {"latitude": None, "longitude": None}

# letzte_werkseinstellungbool: Factory-Reset-Checkbox (Frontend setzt bool, Pico liest Zustand)
letzte_werkseinstellungbool = False


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

    MAX_ENTRIES = 5000

    datenbank.append({
        "luftfeucht": data.get("luftfeucht"),
        "temperatur": data.get("temperatur"),
        "statusTagNacht": data.get("statusTagNacht"),
        "helligkeit": data.get("helligkeit"),
        "motorLaeuft": data.get("motorLaeuft"),
        "zustand": data.get("zustand"),
        "torAUF": data.get("torAUF"),
        "torZU": data.get("torZU"),
        "zeit": data.get("zeit"),
        "licht": data.get("licht")
    })

    if len(datenbank) > MAX_ENTRIES:
        datenbank.pop(0)

    return jsonify({"status": "ok"}), 200


# =========================================================
# GET /api/data
# - Website holen die gespeicherten Messdaten
# =========================================================
@app.route("/api/data", methods=["GET"])
def get_data():
    return jsonify(datenbank), 200



# =========================================================
# POST/OPTIONS /api/heartbeat
# - Steuerung.html sendet regelmäßig ein Lebenszeichen
# =========================================================
@app.route("/api/heartbeat", methods=["POST", "OPTIONS"])
def heartbeat():
    global last_heartbeat

    if request.method == "OPTIONS":
        return ("", 200)

    _data = request.get_json(silent=True) or {}

    last_heartbeat = time.time()
    return jsonify({"status": "ok", "last_heartbeat": last_heartbeat}), 200


# =========================================================
# POST /api/einstellungen
# - Website setzt Einstellungen (Koordinaten, IP, Werkseinstellung, Schuko Werte, tzOffset)
# - Pico holt diese Werte später über GET /api/einstellungen
# =========================================================
@app.route("/api/einstellungen", methods=["POST"])
def set_koordinaten_und_ip():
    global letzte_werkseinstellungbool

    data = request.get_json(silent=True) or {}

    lat = data.get("latitude")
    lon = data.get("longitude")
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

    # Werkseinstellung speichern, wenn boolean
    if werkseinstellungbool is not None:
        if not isinstance(werkseinstellungbool, bool):
            return jsonify({"error": "werkseinstellungbool muss true/false sein"}), 400
        letzte_werkseinstellungbool = werkseinstellungbool

        # Wenn nichts Sinnvolles mitgesendet wurde
        if (
            lat is None and
            lon is None and
            werkseinstellungbool is None
        ):
            return jsonify({
                "error": "keine gültigen Felder gesendet"
            }), 400

    return jsonify({
        "status": "ok",
        "latitude": letzte_coord.get("latitude"),
        "longitude": letzte_coord.get("longitude"),
        "werkseinstellungbool": letzte_werkseinstellungbool,
    }), 200


# =========================================================
# GET /api/einstellungen
# - Pico fragt diese Route regelmäßig ab, um Steuerwerte zu bekommen
# =========================================================
@app.route("/api/einstellungen", methods=["GET"])
def einstellungen_get():



    return jsonify({
        "latitude": letzte_coord.get("latitude"),
        "longitude": letzte_coord.get("longitude"),


    }), 200

# =========================================================
# Start (lokal)
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
