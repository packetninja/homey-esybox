"""
DAB Pumps Esybox driver for Homey.

Handles device pairing by discovering pumps via the DAB cloud API.
Requires DAB credentials to be set in app settings first:
  Settings > Apps > DAB Pumps > Configure
"""

import logging

from homey.driver import Driver
from app.dab_api import DabPumpsApi

_LOGGER = logging.getLogger(__name__)


class EsyboxDriver(Driver):

    async def on_init(self) -> None:
        self.log("Esybox driver initialized")

        self.homey.flow.get_action_card("set_target_pressure") \
            .register_run_listener(self._on_flow_set_target_pressure)
        self.homey.flow.get_action_card("power_shower_on") \
            .register_run_listener(self._on_flow_power_shower_on)
        self.homey.flow.get_action_card("power_shower_off") \
            .register_run_listener(self._on_flow_power_shower_off)

    async def _on_flow_set_target_pressure(self, args, **kwargs) -> None:
        device = args["device"]
        await device.set_target_pressure(float(args["pressure"]))

    async def _on_flow_power_shower_on(self, args, **kwargs) -> None:
        device = args["device"]
        await device.start_power_shower(
            boost=str(args["boost"]),
            duration=int(args["duration"]),
        )

    async def _on_flow_power_shower_off(self, args, **kwargs) -> None:
        device = args["device"]
        await device.stop_power_shower()

    async def on_pair(self, session) -> None:
        """
        Pairing flow:
          1. login_credentials view  → 'login' event  → validate & store credentials
          2. list_devices view       → 'list_devices' event → discover pumps
          3. add_devices view        → standard Homey flow
        """

        async def on_login(data):
            username = (data.get("username") or "").strip()
            password = data.get("password") or ""

            if not username or not password:
                raise Exception("Please enter both email and password.")

            api = DabPumpsApi(username, password)
            try:
                await api.connect()
                await api.close()
            except Exception as exc:
                raise Exception(f"Login failed: {exc}") from exc

            # Persist credentials so the device can use them after pairing
            await self.homey.settings.set("username", username)
            await self.homey.settings.set("password", password)
            return True

        session.set_handler("login", on_login)
        session.set_handler("list_devices", self.on_pair_list_devices)

    async def on_pair_list_devices(self, view_data) -> list:
        """
        Called during device pairing to enumerate available pumps.
        Requires DAB credentials to be set in app settings first.
        """
        username = self.homey.settings.get("username")
        password = self.homey.settings.get("password")

        if not username or not password:
            raise Exception(
                "DAB credentials are not configured. "
                "Please go to Settings > Apps > DAB Pumps > Configure "
                "and enter your DAB account email and password first."
            )

        api = DabPumpsApi(username, password)
        devices = []

        try:
            await api.connect()
            installations = await api.get_installations()

            if not installations:
                raise Exception(
                    "No installations found in your DAB account. "
                    "Make sure your pump is registered in the DAB DConnect or DAB Live app."
                )

            for install in installations:
                pumps = await api.get_devices(install.id)
                for pump in pumps:
                    device_name = getattr(pump, "name", pump.serial)
                    if install.name and install.name != device_name:
                        device_name = f"{device_name} ({install.name})"

                    devices.append({
                        "name": device_name,
                        "data": {
                            # 'id' must be unique and stable across re-pairs
                            "id": pump.serial,
                            "serial": pump.serial,
                            "install_id": install.id,
                        },
                        "store": {
                            "install_name": getattr(install, "name", ""),
                            "product": getattr(pump, "product", ""),
                            "vendor": getattr(pump, "vendor", ""),
                            "hw_version": getattr(pump, "hw_version", ""),
                            "sw_version": getattr(pump, "sw_version", ""),
                            "config_id": getattr(pump, "config_id", ""),
                        },
                    })

        except Exception:
            _LOGGER.exception("Failed to list devices during pairing")
            raise
        finally:
            await api.close()

        if not devices:
            raise Exception(
                "No pumps found in your DAB account. "
                "Ensure your pump is paired in the DAB app and your account has access."
            )

        return devices


homey_export = EsyboxDriver
