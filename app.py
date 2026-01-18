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
    data = request.get_json()
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
# GET: Wetterdaten abrufen
# ---------------------------
@app.route("/api/data", methods=["GET"])
def get_data():
    return jsonify(datenbank)


# ---------------------------
# POST: Motor-Zielwerte von Website
# ---------------------------
@app.route("/api/motor_targets", methods=["POST"])
def set_motor_targets():
    data = request.get_json() or {}

    m1 = data.get("motor1_target")
    m2 = data.get("motor2_target")

    if m1 is None or m2 is None:
        return jsonify({"error": "motor1_target/motor2_target fehlen"}), 400

    latest_motor_targets["motor1_target"] = int(m1)
    latest_motor_targets["motor2_target"] = int(m2)

    return jsonify({"status": "ok"}), 200


# ---------------------------
# POST: Koordinaten + IP + Factory Reset
# ---------------------------
@app.route("/api/coordscheck", methods=["POST"])
def set_koordinaten():
    global latest_factory_reset

    data = request.get_json() or {}

    lat = data.get("latitude")
    lon = data.get("longitude")
    powtrack = data.get("powertracker")
    factory_reset = data.get("factory_reset")

    if lat is None or lon is None:
        return jsonify({"error": "latitude/longitude fehlen"}), 400

    if powtrack is None:
        return jsonify({"error": "ipadresse powertracker fehlt"}), 400

    latest_coords["latitude"] = float(lat)
    latest_coords["longitude"] = float(lon)
    latest_ip["powertracker"] = str(powtrack)

    if isinstance(factory_reset, bool):
        latest_factory_reset = factory_reset

    return jsonify({
        "status": "ok",
        "factory_reset": latest_factory_reset
    }), 200


# ---------------------------
# GET: Alles für den Pico
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
        "factory_reset": latest_factory_reset
    }), 200


# ---------------------------
# POST: Manuell / Automatik
# ---------------------------
@app.route("/api/manuell", methods=["POST"])
def manuell():
    global aktueller_status

    data = request.get_json() or {}
    status = data.get("aktiv")

    if not isinstance(status, bool):
        return jsonify({"error": "Status muss true/false sein"}), 400

    aktueller_status = status
    return jsonify({"manuell": aktueller_status}), 200


# ---------------------------
# Start
# ---------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
