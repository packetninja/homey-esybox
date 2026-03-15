DAB Pumps / Esybox
==================

Monitor and control your DAB Pumps Esybox water pressure pump from Homey.

Supports all Esybox models (Esybox, Esybox Mini, Esybox Max) via the DAB
DConnect cloud. An active internet connection and a DAB account are required.


Prerequisites
-------------
1. A DAB DConnect or DAB Live account
   Register at: https://www.dconnect.dabpumps.com
   or via the DConnect mobile app.

2. Your pump must already be paired with the DAB app and appear in your account.

3. Recommended: create a dedicated email address for your Homey integration
   to avoid "multiple login" conflicts on the DAB platform.


Setup
-----
1. Install this app on your Homey.

2. Go to Devices > Add Device > DAB Pumps / Esybox.
   Enter your DAB account email and password when prompted.
   Homey will verify your credentials and discover all pumps in your account.
   Select yours and tap Add.

   Your credentials are stored in the app and can be updated later via
   Settings > Apps > DAB Pumps > Configure.


Capabilities
------------
Sensor (read-only):
  • Water Pressure (bar)         – current system pressure
  • Flow Rate (L/min)            – current water flow
  • Temperature (°C)             – heatsink temperature
  • Water Meter (m³)             – total delivered water
  • Pump Running (on/off)        – whether the pump is currently active

Control (read/write — requires Installer role in the DAB app):
  • Target Pressure (bar)        – setpoint pressure the pump maintains
  • Power Shower (on/off)        – activates the Power Shower boost mode


Power Shower
------------
Power Shower is a boost feature that temporarily increases water pressure for
a better shower experience. The boost level (intensity code) used when enabling
it via Homey defaults to "30" (30 % boost). Once you've activated it through the
DAB app or a physical button press, Homey will remember the last active boost
code and restore it on the next enable.

Note: the Power Shower and Target Pressure controls require your DAB account to
have "Installer" or "Professional" permissions on the installation. Standard
"Customer" accounts have read-only access.


Flow cards (automations)
------------------------
Homey automatically creates flow cards for all capabilities:
  • "When Water Pressure changes" trigger
  • "When Pump Running becomes true/false" trigger
  • "Set Target Pressure to …" action
  • "Set Power Shower to on/off" action


Poll interval
-------------
The app polls the DAB cloud every 30 seconds by default. You can adjust this
in the app settings. DAB's cloud recommends ≥ 30 s to avoid rate limiting.
The minimum allowed interval is 10 seconds.


Development & contribution
--------------------------
Source: https://github.com/packetninja/homey-esybox
DAB Python library: https://github.com/ankohanse/pydabpumps
HA reference integration: https://github.com/ankohanse/hass-dab-pumps

To run locally:
  npm install -g homey             # Homey CLI
  cd Esybox
  homey app install-dependencies   # installs Python deps (requires Docker)
  homey app run                    # deploys to your Homey for testing


Images for App Store submission
--------------------------------
Replace the placeholder SVG icons with proper images before publishing:
  assets/images/small.jpg   (250 × 175 px)
  assets/images/large.jpg   (500 × 350 px)
  assets/images/xlarge.jpg  (1000 × 700 px)
  drivers/esybox/assets/images/  (same sizes)
