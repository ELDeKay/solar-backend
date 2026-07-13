from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import time


app = Flask(__name__)


# =========================================================
# CORS
# =========================================================

CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://mysolarfollower.onrender.com"
        ]
    }
})


# =========================================================
# Globale Zustände im Arbeitsspeicher
# =========================================================

# Enthält die letzten Messdatensätze des Pico.
datenbank = []

# Sollzustand der Stallbeleuchtung.
licht = False

# Zeitpunkt des letzten Lebenszeichens der Website.
last_heartbeat = 0.0

# Zuletzt gespeicherte Standortkoordinaten.
letzte_coord = {
    "latitude": None,
    "longitude": None
}


# =========================================================
# Messdaten empfangen
# =========================================================

@app.route("/api/getdata", methods=["POST"])
def receive_getdata():
    """Speichert einen neuen Messdatensatz des Pico im RAM."""

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Keine gültigen JSON-Daten empfangen"
        }), 400

    max_entries = 5000

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

    # Entfernt den ältesten Eintrag, sobald das Limit überschritten wird.
    if len(datenbank) > max_entries:
        datenbank.pop(0)

    return jsonify({
        "status": "ok",
        "anzahlEintraege": len(datenbank)
    }), 200


# =========================================================
# Messdaten ausgeben
# =========================================================

@app.route("/api/data", methods=["GET"])
def get_data():
    """Liefert alle momentan im RAM gespeicherten Messdaten."""

    return jsonify(datenbank), 200


# =========================================================
# Lebenszeichen der Website
# =========================================================

@app.route("/api/heartbeat", methods=["POST", "OPTIONS"])
def heartbeat():
    """Aktualisiert den Zeitpunkt des letzten Website-Lebenszeichens."""

    global last_heartbeat

    if request.method == "OPTIONS":
        return "", 200

    last_heartbeat = time.time()

    return jsonify({
        "status": "ok",
        "last_heartbeat": last_heartbeat
    }), 200


# =========================================================
# Einstellungen speichern
# =========================================================

@app.route("/api/einstellungen", methods=["POST"])
def einstellungen_post():
    """Speichert Standortkoordinaten und den Licht-Sollzustand."""

    global licht

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Keine gültigen JSON-Daten empfangen"
        }), 400

    latitude = data.get("latitude")
    longitude = data.get("longitude")
    licht_neu = data.get("licht")


    # Koordinaten dürfen nur gemeinsam übertragen werden.
    if latitude is not None or longitude is not None:

        if latitude is None or longitude is None:
            return jsonify({
                "error": (
                    "latitude und longitude müssen "
                    "zusammen gesendet werden"
                )
            }), 400

        try:
            latitude = float(latitude)
            longitude = float(longitude)

        except (TypeError, ValueError):
            return jsonify({
                "error": "latitude und longitude müssen Zahlen sein"
            }), 400

        if not -90 <= latitude <= 90:
            return jsonify({
                "error": "latitude muss zwischen -90 und 90 liegen"
            }), 400

        if not -180 <= longitude <= 180:
            return jsonify({
                "error": "longitude muss zwischen -180 und 180 liegen"
            }), 400

        letzte_coord["latitude"] = latitude
        letzte_coord["longitude"] = longitude


    # Licht darf ausschließlich als Boolean übertragen werden.
    if licht_neu is not None:

        if not isinstance(licht_neu, bool):
            return jsonify({
                "error": "licht muss true oder false sein"
            }), 400

        licht = licht_neu


    if (
        latitude is None
        and longitude is None
        and licht_neu is None
    ):
        return jsonify({
            "error": "Keine gültigen Felder gesendet"
        }), 400


    return jsonify({
        "status": "ok",
        "latitude": letzte_coord["latitude"],
        "longitude": letzte_coord["longitude"],
        "licht": licht
    }), 200


# =========================================================
# Einstellungen an den Pico ausgeben
# =========================================================

@app.route("/api/einstellungen", methods=["GET"])
def einstellungen_get():
    """Liefert die aktuellen Steuerwerte und Koordinaten an den Pico."""

    return jsonify({
        "latitude": letzte_coord["latitude"],
        "longitude": letzte_coord["longitude"],
        "licht": licht
    }), 200


# =========================================================
# Statusseite
# =========================================================

@app.route("/")
def home():
    return jsonify({
        "status": "Backend läuft"
    }), 200


# =========================================================
# Lokaler Start
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
