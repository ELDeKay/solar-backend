from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://mysolarfollower.onrender.com"
        ]
    }
})

# Wetterdaten im RAM
datenbank = []

# Sturmmodus-Status
aktueller_status = False  # True = aktiviert, False = deaktiviert

# Letzte Koordinaten (von der Website gesetzt)
latest_coords = {"latitude": None, "longitude": None}
latest_ip = {"powertracker": None}
latest_motor_targets = {"motor1_target": None, "motor2_target": None}


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
    
        # ✅ nur Pico-Zeit, kein Server-Fallback
        "zeit": data.get("zeit")
    })
    
    # ✅ Datenbank begrenzen (RAM-sicher)
    if len(datenbank) > MAX_ENTRIES:
        datenbank.pop(0)


    return jsonify({"status": "ok"}), 200


# ---------------------------
# GET: Wetterdaten abrufen
# ---------------------------
@app.route("/api/data", methods=["GET"])
def get_data():
    return jsonify(datenbank)

# -----------------------------------------
# ✅ NEU: POST Motor-Zielwerte von Website
# -----------------------------------------
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

# -----------------------------------------
# POST: Koordinaten von Website empfangen
# GET:  Koordinaten (und sturmmodus) an Pico
# -----------------------------------------
@app.route("/api/coordscheck", methods=["POST"])
def set_koordinaten():
    data = request.get_json() or {}

    lat = data.get("latitude")
    lon = data.get("longitude")
    powtrack = data.get("powertracker")

    if lat is None or lon is None:
        return jsonify({"error": "latitude/longitude fehlen"}), 400
    if powtrack is None:
        return jsonify({"error": "ipadresse powtrack fehlt"}), 400

    # als float speichern (sauber)
    latest_coords["latitude"] = float(lat)
    latest_coords["longitude"] = float(lon)
    latest_ip["powertracker"] = str(powtrack)

    return jsonify({
        "status": "ok",
        "latitude": latest_coords["latitude"],
        "longitude": latest_coords["longitude"],
        "powertracker" : latest_ip["powertracker"]
    }), 200


@app.route("/api/coordscheck", methods=["GET"])
def coordscheck_get():
    return jsonify({
        "latitude": latest_coords.get("latitude"),
        "longitude": latest_coords.get("longitude"),
        "powertracker": latest_ip.get("powertracker"),
        "motor1_target": latest_motor_targets.get("motor1_target"),
        "motor2_target": latest_motor_targets.get("motor2_target"),
        "manuell": aktueller_status
    }), 200


# -----------------------------------------
# POST: Sturmmodus von der Website setzen
# -----------------------------------------
@app.route("/api/manuell", methods=["POST"])
def manuell():
    global aktueller_status
    data = request.get_json() or {}
    status = data.get("aktiv")

    if not isinstance(status, bool):
        return jsonify({"error": "Status muss true/false sein"}), 400

    aktueller_status = status
    return jsonify({"manuell": aktueller_status}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
