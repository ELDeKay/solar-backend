<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <title>Einstellungen</title>

  <style>
    *,
    *::before,
    *::after { box-sizing: border-box; }

    html, body { height: 100%; }

    body {
      font-family: Arial, sans-serif;
      background: #f0f0f0;
      margin: 0;
      padding: 20px;
      padding-bottom: calc(20px + env(safe-area-inset-bottom));
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .topbar {
      width: 100%;
      max-width: 800px;
      position: relative;
      display: flex;
      align-items: center;
      margin-bottom: 30px;
    }

    .topbar h1 {
      position: absolute;
      left: 50%;
      transform: translateX(-50%);
      margin: 0;
      text-align: center;
    }

    .back-btn {
      text-decoration: none;
      background: #007BFF;
      color: white;
      padding: 10px 16px;
      border-radius: 10px;
      font-weight: bold;
      margin-left: auto;
      display: inline-block;
      touch-action: manipulation;
    }

    .box {
      width: 100%;
      max-width: 800px;
      background: white;
      border-radius: 16px;
      padding: 25px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      margin: 0;
    }

    .box h2 {
      margin-top: 0;
      margin-bottom: 20px;
      text-align: center;
    }

    .field { margin-bottom: 20px; }

    .field label {
      display: block;
      margin-bottom: 6px;
      font-weight: bold;
    }

    .field input[type="number"],
    .field input[type="text"] {
      width: 100%;
      padding: 12px;
      font-size: 16px;
      border-radius: 8px;
      border: 1px solid #ccc;
    }

    /* ✅ NEU: Button-Zeile (2 Buttons nebeneinander) */
    .btn-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-top: 10px;
    }

    .action-btn {
      width: 100%;
      padding: 12px;
      font-size: 16px;
      font-weight: bold;
      border: none;
      border-radius: 10px;
      background: #007BFF;
      color: white;
      cursor: pointer;
      touch-action: manipulation;
    }

    .action-btn:active {
      transform: scale(0.99);
    }

    .status {
      margin-top: 20px;
      font-size: 14px;
      text-align: center;
      color: #555;
    }

    @media (max-width: 600px) {
      body {
        padding: 14px;
        padding-bottom: calc(14px + env(safe-area-inset-bottom));
        align-items: stretch;
      }

      .topbar {
        flex-direction: column;
        align-items: stretch;
        gap: 12px;
        margin-bottom: 18px;
      }

      .topbar h1 {
        position: static;
        transform: none;
        text-align: center;
        order: 1;
      }

      .back-btn {
        width: 100%;
        text-align: center;
        order: 2;
        margin-left: 0;
      }

      .box { padding: 18px; }

      /* ✅ Mobile: Buttons untereinander */
      .btn-row {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>

<body>

  <div class="topbar">
    <h1>Einstellungen</h1>
    <a class="back-btn" href="index.html">Zurück zum Hauptmenü</a>
  </div>

  <div class="box">
    <h2>Standortdaten</h2>

    <div class="field">
      <label for="latitude">Breitengrad (Latitude)</label>
      <input type="number" id="latitude" step="0.000001" placeholder="z. B. 48.137154" />
    </div>

    <div class="field">
      <label for="longitude">Längengrad (Longitude)</label>
      <input type="number" id="longitude" step="0.000001" placeholder="z. B. 11.576124" />
    </div>

    <div class="field">
      <label for="powertracker">IP-Adresse Leistungsmesser</label>
      <input
        type="text"
        id="powertracker"
        placeholder="Tragen Sie hier die IP-Adresse des Leistungsmessers ein"
        autocomplete="off"
        spellcheck="false"
      />
    </div>

    <!-- ✅ HIER: zwei Buttons nebeneinander -->
    <div class="btn-row">
      <button id="sendGeoBtn" type="button" class="action-btn">Geo-Daten schicken</button>
      <button id="sendIpBtn" type="button" class="action-btn">IP-Adresse schicken</button>
    </div>

    <br>

    <!-- Werkseinstellung Button (volle Breite) -->
    <div class="field">
      <button id="factoryBtn" type="button" class="action-btn" style="width:100%;">
        Werkseinstellung
      </button>

      <div style="margin-top:10px; font-size:14px; color:#555; line-height:1.4; text-align:center;">
        setzt den Geo-Daten, die IP-Adresse des Leistungsmessers und den WLAN Zugang zurück.
      </div>
    </div>

    <div class="status" id="statusText">
      Daten werden nicht übertragen
    </div>
  </div>

<script>
const API_BASE = "https://solar-backend-ljck.onrender.com";

const latitudeInput = document.getElementById("latitude");
const longitudeInput = document.getElementById("longitude");
const powertrackerInput = document.getElementById("powertracker");

const sendGeoBtn = document.getElementById("sendGeoBtn");
const sendIpBtn = document.getElementById("sendIpBtn");
const factoryBtn = document.getElementById("factoryBtn");
const statusText = document.getElementById("statusText");

function istGueltigeIPv4(ip) {
  const parts = ip.split(".");
  if (parts.length !== 4) return false;
  return parts.every(p => {
    if (p.trim() === "") return false;
    if (!/^\d+$/.test(p)) return false;
    const n = Number(p);
    return n >= 0 && n <= 255;
  });
}

async function postCoordsCheck(payload) {
  const res = await fetch(`${API_BASE}/api/coordscheck`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error("HTTP " + res.status);
  return res.json().catch(() => ({}));
}

/* -----------------------
   Button: Geo senden
------------------------ */
sendGeoBtn.addEventListener("click", async () => {
  const latitude = parseFloat(latitudeInput.value);
  const longitude = parseFloat(longitudeInput.value);

  if (isNaN(latitude) || isNaN(longitude)) {
    alert("Bitte gültige Koordinaten eingeben");
    return;
  }

  try {
    statusText.innerText = "Übertragung läuft ...";
    await postCoordsCheck({ latitude, longitude });
    statusText.innerText = "Daten werden übertragen";
  } catch {
    statusText.innerText = "Übertragung fehlgeschlagen";
  }
});

/* -----------------------
   Button: IP senden
------------------------ */
sendIpBtn.addEventListener("click", async () => {
  const powertracker = (powertrackerInput.value || "").trim();

  if (powertracker.length === 0 || !istGueltigeIPv4(powertracker)) {
    alert("Bitte eine gültige IPv4-Adresse eingeben (z. B. 192.168.0.10)");
    return;
  }

  try {
    statusText.innerText = "Übertragung läuft ...";
    await postCoordsCheck({ powertracker });
    statusText.innerText = "Daten werden übertragen";
  } catch {
    statusText.innerText = "Übertragung fehlgeschlagen";
  }
});

/* -----------------------
   Button: Werkseinstellung
------------------------ */
factoryBtn.addEventListener("click", async () => {
  const ok = confirm(
    "Werkseinstellung ausführen?\n\n" +
    "Dabei werden Geo-Daten, IP-Adresse des Leistungsmessers und WLAN-Zugang zurückgesetzt."
  );
  if (!ok) return;

  try {
    statusText.innerText = "Werkseinstellung läuft ...";
    await postCoordsCheck({ factory_reset: true });

    // UI zurücksetzen
    latitudeInput.value = "";
    longitudeInput.value = "";
    powertrackerInput.value = "";

    statusText.innerText = "Daten werden übertragen";
  } catch {
    statusText.innerText = "Werkseinstellung fehlgeschlagen";
  }
});
</script>

</body>
</html>
