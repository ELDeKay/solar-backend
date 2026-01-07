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

# POST: Wetterdaten vom Pico
@app.route("/api/getdata", methods=["POST"])
def receive_getdata():
    data = request.get_json()

    if data is None:
        return jsonify({"error": "no data found"}), 400

    datenbank.append({
        "wind": data.get("windstaerke"),
        "sunrise": data.get("sunrise"),
        "sunset": data.get("sunset"),
        "sunhours": data.get("sunhours"),
        "motor1": data.get("motor1"),
        "motor2": data.get("motor2"),
        "manuell": data.get("manuell"),
        "tilt": data.get("tilt"),
        "orient": data.get("orient"),
        "voltage": data.get("voltage"),
        "current": data.get("current"),
        "coordscheck": data.get("coordscheck"),
        "zeit": datetime.now().isoformat()
    })

    return jsonify({"status": "ok"}), 200


# GET: Wetterdaten abrufen
@app.route("/api/data", methods=["GET"])
def get_data():
    return jsonify(datenbank)
    
@app.route("/api/koordinaten", methods=["POST"])
def koordinaten():
    data = request.get_json()

    latitude = data.get("latitude")
    longitude = data.get("longitude")

    print("Empfangen:", latitude, longitude)

    return jsonify({"status": "ok"}), 200

# POST: Sturmmodus von der Website setzen
@app.route("/api/sturmmodus", methods=["POST"])
def sturmmodus():
    global aktueller_status

    data = request.get_json()
    status = data.get("aktiv")

    if not isinstance(status, bool):
        return jsonify({"error": "Status muss true/false sein"}), 400

    aktueller_status = status
    return jsonify({"sturmmodus": aktueller_status}), 200


# GET: Sturmmodus abfragen (vom Pico)
@app.route("/api/get_sturmmodus", methods=["GET"])
def get_sturmmodus():
    return jsonify({"sturmmodus": aktueller_status})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
