"""
DAB Pumps API wrapper for the Homey Esybox app.

Uses the pydabpumps library for authenticated cloud communication with DAB's
DConnect / DAB Live backend. Supports automatic token refresh and multiple
authentication backends.

Install dependency:  homey app install-dependencies
  (or: pip install pydabpumps  — for local development only)
"""

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


class DabPumpsApi:
    """
    Thin wrapper around AsyncDabPumps that provides a stable interface
    for the Homey driver and device classes.
    """

    def __init__(self, username: str, password: str) -> None:
        try:
            from pydabpumps import AsyncDabPumps
        except ImportError as exc:
            raise ImportError(
                "pydabpumps is not installed. Run: homey app install-dependencies"
            ) from exc

        self._api = AsyncDabPumps(username, password)
        self._connected = False

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Authenticate against the DAB cloud."""
        await self._api.login()
        self._connected = True
        _LOGGER.info("Authenticated with DAB cloud")

    async def close(self) -> None:
        """Release the HTTP session."""
        await self._api.close()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def get_installations(self) -> list:
        """Return all installations linked to the account."""
        await self._api.fetch_install_list()
        return list(self._api.install_map.values())

    async def get_devices(self, install_id: str) -> list:
        """Return all devices within an installation."""
        await self._api.fetch_install_details(install_id)
        return [d for d in self._api.device_map.values() if d.install_id == install_id]

    # ------------------------------------------------------------------
    # Status polling
    # ------------------------------------------------------------------

    async def get_device_statuses(self, install_id: str, serial: str) -> list:
        """
        Fetch current device statuses from the DAB cloud.
        Returns a list of DabPumpsStatus objects, each with:
          .key    – parameter key (e.g. 'VP_PressureBar')
          .value  – human-readable value (e.g. '2.50')
          .unit   – unit string (e.g. 'bar')
        """
        await self._api.fetch_install_statuses(install_id)
        return [s for s in self._api.status_map.values() if s.serial == serial]

    def get_param_codes(self, serial: str, key: str) -> dict[str, str]:
        """
        Return the {code: label} dict for a parameter's allowed values.
        Returns an empty dict if the parameter is not found or has no ENUM values.
        """
        device = self._api.device_map.get(serial)
        config = self._api.config_map.get(device.config_id) if device else None
        params = config.meta_params.get(key) if config else None
        return dict(params.values) if params and params.values else {}


    async def refresh_auth(self) -> None:
        """Re-authenticate to obtain fresh tokens (called on 403 errors)."""
        await self._api.login()

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    async def set_value(self, serial: str, key: str, value: Any) -> bool:
        """
        Set a device parameter by human-readable value.
        pydabpumps handles encoding to the backend 'code' format.

        Returns True on success, False if the value was unchanged.
        """
        return await self._api.change_device_status(serial, key, value=value)

    async def set_code(self, serial: str, key: str, code: str) -> bool:
        """
        Set a device parameter by raw backend code (e.g. '0' to disable power shower).
        """
        return await self._api.change_device_status(serial, key, code=code)
