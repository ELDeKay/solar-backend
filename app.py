from flask import Flask, request, jsonify
from flask_cors import CORS
import os

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
snowmode = False
calibration = False

latest_coords = {
    "latitude": None,
    "longitude": None
}

latest_ip = {
    "powertracker": None
}

latest_motor_targets = {
    "motor1_target": None,
    "motor2_target": None
}

latest_factory_reset = False


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
        "coordscheck": data.get("coordscheck"),
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
@app.route("/api/motor_targets", methods=["POST"])
def set_motor_targets():
    data = request.get_json(silent=True) or {}

    m1 = data.get("motor1_target")
    m2 = data.get("motor2_target")

    if m1 is None or m2 is None:
        return jsonify({"error": "motor1_target/motor2_target fehlen"}), 400

    try:
        latest_motor_targets["motor1_target"] = int(m1)
        latest_motor_targets["motor2_target"] = int(m2)
    except (TypeError, ValueError):
        return jsonify({"error": "motor targets müssen Integer sein"}), 400

    return jsonify({"status": "ok"}), 200


# ---------------------------
# POST: Koordinaten +/oder IP +/oder Factory Reset
# (passt zu deiner neuen einstellungen.html:
#  - Geo senden: {latitude, longitude}
#  - IP senden: {powertracker}
#  - Factory: {factory_reset:true}
#  - Kombinationen sind erlaubt)
# ---------------------------
@app.route("/api/coordscheck", methods=["POST"])
def set_koordinaten_und_ip():
    global latest_factory_reset

    data = request.get_json(silent=True) or {}

    # optional
    lat = data.get("latitude")
    lon = data.get("longitude")
    powtrack = data.get("powertracker")
    factory_reset = data.get("factory_reset")

    # Geo: nur wenn BEIDE da sind
    if lat is not None or lon is not None:
        if lat is None or lon is None:
            return jsonify({"error": "latitude und longitude müssen zusammen gesendet werden"}), 400
        try:
            latest_coords["latitude"] = float(lat)
            latest_coords["longitude"] = float(lon)
        except (TypeError, ValueError):
            return jsonify({"error": "latitude/longitude müssen Zahlen sein"}), 400

    # IP: nur wenn vorhanden
    if powtrack is not None:
        powtrack = str(powtrack).strip()
        if powtrack == "":
            return jsonify({"error": "powertracker darf nicht leer sein"}), 400
        latest_ip["powertracker"] = powtrack

    # Factory Reset: wenn bool
    if factory_reset is not None:
        if not isinstance(factory_reset, bool):
            return jsonify({"error": "factory_reset muss true/false sein"}), 400
        latest_factory_reset = factory_reset

    # Wenn gar nichts Sinnvolles kam:
    if (lat is None and lon is None and powtrack is None and factory_reset is None):
        return jsonify({"error": "keine gültigen Felder gesendet"}), 400

    return jsonify({
        "status": "ok",
        "latitude": latest_coords.get("latitude"),
        "longitude": latest_coords.get("longitude"),
        "powertracker": latest_ip.get("powertracker"),
        "factory_reset": latest_factory_reset
    }), 200


# ---------------------------
# GET: Alles für den Pico
# (Pico holt hier Geo + IP + MotorTargets + manuell + factory_reset)
# ---------------------------
@app.route("/api/coordscheck", methods=["GET"])
def coordscheck_get():
    return jsonify({
        "latitude": latest_coords.get("latitude"),
        "longitude": latest_coords.get("longitude"),
        "powertracker": latest_ip.get("powertracker"),
        "motor1_target": latest_motor_targets.get("motor1_target"),
        "motor2_target": latest_motor_targets.get("motor2_target"),
        "manuell": aktueller_status,
        "factory_reset": latest_factory_reset,
        "snowmode": snowmode,
        "calibration": calibration
    }), 200


# ---------------------------
# POST: Manuell / Automatik (Steuerung.html)
# ---------------------------
@app.route("/api/manuell", methods=["POST"])
def manuell():
    global aktueller_status, snowmode

    data = request.get_json(silent=True) or {}

    # optional: manuell
    if "aktiv" in data:
        status = data.get("aktiv")
        if not isinstance(status, bool):
            return jsonify({"error": "aktiv muss true/false sein"}), 400
        aktueller_status = status

    # optional: snowmode
    if "snowmode" in data:
        snow = data.get("snowmode")
        if not isinstance(snow, bool):
            return jsonify({"error": "snowmode muss true/false sein"}), 400
        snowmode = snow
        


    # wenn gar nichts Sinnvolles geschickt wurde
    if ("aktiv" not in data) and ("snowmode" not in data):
        return jsonify({"error": "Sende 'aktiv' und/oder 'snowmode'."}), 400

    return jsonify({
        "manuell": aktueller_status,
        "snowmode": snowmode
    }), 200


@app.route("/api/calibra", methods=["POST"])
def calibra():

    global calibration
    data = request.get_json(silent=True) or {}

    if "calibration" in data:
        calib = data.get("calibration")
        if not isinstance(calib, bool):
            return jsonify({"error": "calibration muss true/false sein"}), 400
        calibration = calib
        
    if ("calibration" not in data):
        return jsonify({"error": "Sende 'calibration'."}), 400

    return jsonify({
        "calibration": calibration
    }), 200

# ---------------------------
# Start
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
