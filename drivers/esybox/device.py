"""
DAB Pumps Esybox device for Homey.

Polls the DAB cloud API on a configurable interval and maps the returned
status values to Homey capabilities.

Supported capabilities
──────────────────────
Read-only (sensors):
  measure_pressure     – current water pressure (bar)
  measure_flow_rate    – current flow rate (L/min)
  measure_temperature  – heatsink temperature (°C)
  meter_water          – total delivered water (m³)
  pump_running         – pump is currently active (bool)

Read/write (controls):
  target_pressure      – setpoint pressure (bar)
  power_shower         – power shower active (bool)

Parameter key mapping
─────────────────────
The DAB API returns parameters by key. Known keys for the E.sybox family:
  VP_PressureBar              → measure_pressure
  SP_SetpointPressureBar      → target_pressure
  VF_FlowLiter                → measure_flow_rate
  TE_HeatsinkTemperatureC     → measure_temperature
  FCt_Total_Delivered_Flow_mc → meter_water
  PumpStatus / ActualStatus   → pump_running
  PowerShowerCountdown        → power_shower (> 0 = active)

Power shower control sequence
──────────────────────────────
  1. Set PowerShowerBoost    – boost percentage code ('20', '30', '40')
  2. Set PowerShowerDuration – duration in seconds ('300'–'1800')
  3. Set PowerShowerCommand  – '1' = Start, '2' = Stop
"""

import asyncio
import logging

from homey.device import Device
from app.dab_api import DabPumpsApi

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Capability mapping
# ---------------------------------------------------------------------------

# Maps DAB parameter key → (Homey capability ID, value transformer)
DAB_CAPABILITY_MAP: dict[str, tuple[str, type]] = {
    "VP_PressureBar": ("measure_pressure", float),
    "SP_SetpointPressureBar": ("target_pressure", float),
    "VF_FlowLiter": ("measure_flow_rate", float),
    "TE_HeatsinkTemperatureC": ("measure_temperature", float),
    "FCt_Total_Delivered_Flow_mc": ("meter_water", float),
}

# Keys that indicate pump running status
PUMP_STATUS_KEYS = {"PumpStatus", "ActualStatus", "Pump_Status"}
PUMP_RUNNING_VALUES = {"1", "true", "True", "running", "Running", "on", "On", "active", "Active"}

# Power shower parameter keys
POWER_SHOWER_BOOST_KEY = "PowerShowerBoost"
POWER_SHOWER_DURATION_KEY = "PowerShowerDuration"
POWER_SHOWER_COMMAND_KEY = "PowerShowerCommand"
POWER_SHOWER_COUNTDOWN_KEY = "PowerShowerCountdown"

POWER_SHOWER_CMD_START = "1"
POWER_SHOWER_CMD_STOP = "2"

POWER_SHOWER_DEFAULT_BOOST = 40      # +40 % boost
POWER_SHOWER_DEFAULT_DURATION = 30   # 30 minutes (stored as minutes, sent as seconds)

# Minimum sensible poll interval (seconds)
MIN_POLL_INTERVAL = 10
DEFAULT_POLL_INTERVAL = 30


class EsyboxDevice(Device):

    # Instance variables are set in on_init, not __init__,
    # because Device.__init__ takes SDK arguments provided by the runner.

    async def on_init(self) -> None:
        self._api: DabPumpsApi | None = None
        self._poll_timer: int | None = None
        self._pump_was_running: bool | None = None

        data = self.get_data()
        self._serial: str | None = data.get("serial")
        self._install_id: str | None = data.get("install_id")

        if not self._serial or not self._install_id:
            await self.set_unavailable("Device data missing — please re-pair")
            return

        # Writable capabilities: register listeners before first poll
        self.register_capability_listener("target_pressure", self._on_set_target_pressure)
        self.register_capability_listener("power_shower", self._on_set_power_shower)

        await self._connect()
        if self._api is not None:
            await self._poll()           # initial fetch
        await self._schedule_next_poll()

    async def on_deleted(self) -> None:
        """Clean up timers and HTTP session when device is removed."""
        self._cancel_timer()
        if self._api is not None:
            try:
                await self._api.close()
            except Exception:
                pass
            self._api = None

    # -----------------------------------------------------------------------
    # Connection
    # -----------------------------------------------------------------------

    async def _connect(self) -> None:
        """Create and authenticate an API client using stored credentials."""
        username = self.homey.settings.get("username")   # sync
        password = self.homey.settings.get("password")   # sync

        if not username or not password:
            await self.set_unavailable(
                "DAB credentials not configured. "
                "Go to Settings > Apps > DAB Pumps > Configure."
            )
            return

        try:
            api = DabPumpsApi(username, password)
            await api.connect()
            # Fetch install details once so metadata is cached for value encoding
            await api.get_devices(self._install_id)
            self._api = api
            self.log(f"Connected to DAB cloud for {self._serial}")
        except Exception as exc:
            self.error(f"Connection failed: {exc}")
            await self.set_unavailable(f"Connection error: {exc}")
            self._api = None

    # -----------------------------------------------------------------------
    # Polling
    # -----------------------------------------------------------------------

    async def _schedule_next_poll(self) -> None:
        """Schedule the next poll using the interval from app settings."""
        raw = self.homey.settings.get("poll_interval")   # sync
        interval_sec = max(MIN_POLL_INTERVAL, int(raw or DEFAULT_POLL_INTERVAL))
        self._poll_timer = self.homey.set_timeout(
            lambda: asyncio.create_task(self._poll_and_reschedule()),
            interval_sec * 1000,
        )

    async def _poll_and_reschedule(self) -> None:
        await self._poll()
        await self._schedule_next_poll()

    async def _poll(self) -> None:
        """Fetch device status from DAB cloud and update Homey capabilities."""
        if self._api is None:
            await self._connect()
            if self._api is None:
                return

        try:
            statuses = await self._api.get_device_statuses(self._install_id, self._serial)
            await self.set_available()
            await self._update_capabilities(statuses)
        except Exception as exc:
            # Try a token refresh before giving up – DAB tokens expire every 5 min
            try:
                await self._api.refresh_auth()
                statuses = await self._api.get_device_statuses(self._install_id, self._serial)
                await self.set_available()
                await self._update_capabilities(statuses)
                return
            except Exception as refresh_exc:
                self.error(f"Poll failed and refresh failed: {exc} / {refresh_exc}")
            await self.set_unavailable(f"Communication error: {exc}")
            # Force full reconnect on next poll
            try:
                await self._api.close()
            except Exception:
                pass
            self._api = None

    def _cancel_timer(self) -> None:
        if self._poll_timer is not None:
            self.homey.clear_timeout(self._poll_timer)
            self._poll_timer = None

    # -----------------------------------------------------------------------
    # Status processing
    # -----------------------------------------------------------------------

    async def _update_capabilities(self, statuses: list) -> None:
        """Map DAB status list to Homey capability updates."""
        pump_running: bool | None = None
        power_shower_active: bool | None = None  # None = countdown not seen this poll

        for status in statuses:
            key = status.key
            raw = status.value

            if raw is None:
                continue

            # Standard numeric sensors
            if key in DAB_CAPABILITY_MAP:
                capability, transform = DAB_CAPABILITY_MAP[key]
                try:
                    value = transform(raw)
                    if self.has_capability(capability):
                        await self.set_capability_value(capability, value)
                except (ValueError, TypeError) as exc:
                    self.log(f"Could not parse {key}={raw!r}: {exc}")

            # Pump running status
            elif key in PUMP_STATUS_KEYS:
                pump_running = str(raw) in PUMP_RUNNING_VALUES

            # Power shower active state – driven by the countdown timer
            elif key == POWER_SHOWER_COUNTDOWN_KEY:
                try:
                    power_shower_active = float(raw) > 0
                except (ValueError, TypeError):
                    power_shower_active = False

            else:
                _LOGGER.info("DAB parameter: %s = %s (%s)", key, raw, status.unit)

        # PowerShowerCountdown is a static param: absent = not running
        if power_shower_active is None:
            power_shower_active = False
        if self.has_capability("power_shower"):
            await self.set_capability_value("power_shower", power_shower_active)

        # Update pump_running and fire flow triggers on state changes
        if pump_running is not None and self.has_capability("pump_running"):
            prev = self._pump_was_running
            await self.set_capability_value("pump_running", pump_running)
            if prev is not None and prev != pump_running:
                trigger_id = "pump_started" if pump_running else "pump_stopped"
                await self._trigger_flow(trigger_id)
            self._pump_was_running = pump_running

    async def _trigger_flow(self, card_id: str) -> None:
        """Fire a device trigger flow card (best-effort)."""
        try:
            card = self.homey.flow.get_device_trigger_card(card_id)
            await card.trigger(self, {}, {})
        except Exception as exc:
            self.log(f"Flow trigger '{card_id}' failed: {exc}")

    # -----------------------------------------------------------------------
    # Writable capability handlers
    # -----------------------------------------------------------------------

    async def set_target_pressure(self, value: float) -> None:
        """Set the target pressure setpoint."""
        if self._api is None:
            raise Exception("Not connected to DAB cloud")
        await self._api.set_value(self._serial, "SP_SetpointPressureBar", value)
        self.log(f"Target pressure set to {value} bar")

    async def _on_set_target_pressure(self, value: float, **kwargs) -> None:
        """Called when user adjusts target pressure in Homey."""
        await self.set_target_pressure(value)

    async def start_power_shower(self, boost: str | None = None, duration: int | None = None) -> None:
        """Start power shower with the given or device-settings boost and duration."""
        if self._api is None:
            raise Exception("Not connected to DAB cloud")
        boost = boost or str(self.get_setting("power_shower_boost") or POWER_SHOWER_DEFAULT_BOOST)
        duration_s = str(duration if duration is not None
                         else int(self.get_setting("power_shower_duration") or POWER_SHOWER_DEFAULT_DURATION) * 60)
        try:
            self.log(f"Starting power shower (boost={boost}%, duration={duration_s}s)")
            await self._api.set_code(self._serial, POWER_SHOWER_BOOST_KEY, boost)
            await self._api.set_code(self._serial, POWER_SHOWER_DURATION_KEY, duration_s)
            await self._api.set_code(self._serial, POWER_SHOWER_COMMAND_KEY, POWER_SHOWER_CMD_START)
        except Exception as exc:
            msg = str(exc)
            if "403" in msg or "Forbidden" in msg:
                raise Exception(
                    "Power shower control requires installer-level access on your DAB account. "
                    "Grant installer role in the DAB DConnect or DAB Live app first."
                ) from exc
            raise

    async def stop_power_shower(self) -> None:
        """Stop the power shower."""
        if self._api is None:
            raise Exception("Not connected to DAB cloud")
        self.log("Stopping power shower")
        try:
            await self._api.set_code(self._serial, POWER_SHOWER_COMMAND_KEY, POWER_SHOWER_CMD_STOP)
        except Exception as exc:
            msg = str(exc)
            if "403" in msg or "Forbidden" in msg:
                raise Exception(
                    "Power shower control requires installer-level access on your DAB account. "
                    "Grant installer role in the DAB DConnect or DAB Live app first."
                ) from exc
            raise

    async def _on_set_power_shower(self, value: bool, **kwargs) -> None:
        """Called when user toggles Power Shower in Homey."""
        if value:
            await self.start_power_shower()   # reads boost/duration from picker capabilities
        else:
            await self.stop_power_shower()



homey_export = EsyboxDevice
