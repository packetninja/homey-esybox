# DAB Pumps / Esybox — Homey App

Monitor and control your DAB Pumps Esybox water pressure pump from [Homey](https://homey.app).

Connects via the DAB DConnect / DAB Live cloud. Supports all Esybox models (Esybox, Esybox Mini, Esybox Max).

---

## Features

| Capability | Description |
|---|---|
| Water Pressure (bar) | Current system pressure |
| Flow Rate (L/min) | Current water flow |
| Temperature (°C) | Heatsink temperature |
| Water Meter (m³) | Total delivered water |
| Pump Running | Whether the pump is currently active |
| Power Shower | Activates the temporary pressure boost mode |

**Flow automations:**
- Trigger when pump starts or stops
- Action: Turn Power Shower on/off (with boost % and duration arguments)
- Action: Set target pressure (flow-only — no device tile to avoid accidental changes)

**Power Shower device settings** (tap ⚙ on the device card):
- Boost percentage (20 / 30 / 40 %) — default 40 %
- Duration in minutes (5 – 30 min) — default 30 min

These defaults are used when toggling Power Shower from the device tile or via the flow action without explicit arguments.

---

## Requirements

- A DAB DConnect or DAB Live account ([register here](https://www.dconnect.dabpumps.com))
- Your pump paired in the DAB app and visible in your account
- **Recommended:** use a dedicated account to avoid session conflicts on the DAB platform
- For Power Shower and target pressure control: your DAB account needs Installer-level access on the installation

---

## Installation

1. Install the app on your Homey.
2. Go to **Devices → Add Device → DAB Pumps / Esybox**.
3. Enter your DAB account email and password when prompted — Homey will verify the credentials and discover all pumps in your account.
4. Select your pump and tap **Add**.

> Your credentials are stored in the app and can be updated later via **Settings → Apps → DAB Pumps → Configure**.

---

## Development

Built with the [Homey Python Apps SDK v3](https://apps.developer.homey.app).

```bash
npm install -g homey              # Homey CLI
cd Esybox
homey app install-dependencies    # compiles Python deps (requires Docker)
homey app run                     # deploys to your Homey for live testing
```

**Validate before publishing:**
```bash
homey app validate --level publish
```

---

## Credits & Acknowledgements

- **[pydabpumps](https://github.com/ankohanse/pydabpumps)** — Python library for the DAB DConnect / DAB Live API, used for all cloud communication in this app.
- **[hass-dab-pumps](https://github.com/ankohanse/hass-dab-pumps)** by [@ankohanse](https://github.com/ankohanse) — Home Assistant integration for DAB Pumps. The API research, parameter key mapping, and power shower control sequence in this app are heavily inspired by and would not have been possible without this reference implementation.

---

## Publishing to the Homey App Store

1. Run `homey app validate --level publish` and fix any warnings.
2. Ensure `assets/images/` contains `small.jpg` (250×175), `large.jpg` (500×350), and `xlarge.jpg` (1000×700).
3. Same images required under `drivers/esybox/assets/images/`.
4. Run `homey app publish` — this bumps the version, packages the app, and submits it for review.
5. Track status at [tools.developer.homey.app](https://tools.developer.homey.app) under *Apps SDK → My Apps*.

**Note:** Publishing to cloud/hybrid platforms (`"platforms": ["local", "cloud"]`) requires a [Homey Verified Developer](https://homey.app/en-us/developer/) subscription.

Review typically takes up to 2 weeks.

---

## License

MIT
