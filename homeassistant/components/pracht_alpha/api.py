"""Async API client for Pracht Alpha wallbox."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class PrachtAlphaAuthError(Exception):
    """Raised when authentication fails."""


class PrachtAlphaConnectionError(Exception):
    """Raised when the device is unreachable."""


class PrachtAlphaError(Exception):
    """Raised on generic API errors."""


@dataclass
class PrachtAlphaData:
    """Data returned by GET /api/v1/all."""

    device_id: str
    software_version: str
    hardware_revision: int
    system_initialized: bool
    num_charging_points: int
    error_code: int
    uptime: int
    max_current_total: int
    max_current_car1: int
    max_current_car2: int
    max_current_per_side: int
    current_car1: int
    current_car2: int
    power_car1: float
    power_car2: float
    status_car1: int
    status_car2: int
    current_meas_support: int
    support_lock_unlock: bool
    led_support: bool
    rfid_supported: bool
    comm_pcb_temperature: float
    box_temperature: float
    current_setting_input_lead: int
    energy_car1: float | None
    energy_car2: float | None


@dataclass
class PrachtAlphaLockStatus:
    """Data returned by GET /api/v1/lock_status."""

    lock_status1: str
    lock_status2: str
    timer_status1: str
    timer_remaining_time1: int
    timer_status2: str
    timer_remaining_time2: int
    power_status1: str
    timer_remaining_power1: float
    power_status2: str
    timer_remaining_power2: float


def _parse_all_data(data: dict[str, Any]) -> PrachtAlphaData:
    """Parse the /api/v1/all response into a dataclass."""
    return PrachtAlphaData(
        device_id=data.get("DeviceId", ""),
        software_version=str(data.get("SoftwareVersion", "")),
        hardware_revision=data.get("HardwareRevision", 0),
        system_initialized=data.get("SystemInitialized", 0) == 1,
        num_charging_points=2 if data.get("NumChargingPoints", 1) == 0 else 1,
        error_code=data.get("ErrorCode", 0),
        uptime=data.get("Uptime", 0),
        max_current_total=data.get("MaxCurrentTotal", 0),
        max_current_car1=data.get("MaxCurrentCar1", 0),
        max_current_car2=data.get("MaxCurrentCar2", 0),
        max_current_per_side=data.get("MaxCurrentPerSide", 0),
        current_car1=data.get("CurrentCar1", 0),
        current_car2=data.get("CurrentCar2", 0),
        power_car1=data.get("PowerCar1", 0.0),
        power_car2=data.get("PowerCar2", 0.0),
        status_car1=data.get("StatusCar1", 0),
        status_car2=data.get("StatusCar2", 0),
        current_meas_support=data.get("CurrentMeasSupport", 0),
        support_lock_unlock=data.get("SupportLockUnlock", 0) == 1,
        led_support=data.get("LedSupport", 0) == 1,
        rfid_supported=data.get("RfidSupported", 0) == 1,
        comm_pcb_temperature=data.get("CommPcbTemperature", 0.0),
        box_temperature=data.get("BoxTemperature", 0.0),
        current_setting_input_lead=data.get("CurrentSettingInputLead", 0),
        energy_car1=data.get("EnergyCar1"),
        energy_car2=data.get("EnergyCar2"),
    )


def _parse_lock_status(data: dict[str, Any]) -> PrachtAlphaLockStatus:
    """Parse the /api/v1/lock_status response into a dataclass."""
    return PrachtAlphaLockStatus(
        lock_status1=data.get("LockStatus1", "Unlocked"),
        lock_status2=data.get("LockStatus2", "Unlocked"),
        timer_status1=data.get("TimerStatus1", "Stopped"),
        timer_remaining_time1=data.get("TimerRemainingTime1", 0),
        timer_status2=data.get("TimerStatus2", "Stopped"),
        timer_remaining_time2=data.get("TimerRemainingTime2", 0),
        power_status1=data.get("PowerStatus1", "Stopped"),
        timer_remaining_power1=data.get("TimerRemainingPower1", 0.0),
        power_status2=data.get("PowerStatus2", "Stopped"),
        timer_remaining_power2=data.get("TimerRemainingPower2", 0.0),
    )


class PrachtAlphaApi:
    """Async API client for Pracht Alpha wallbox."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self._host = host
        self._session = session
        self._base_url = f"http://{host}"
        self._auth_key: str | None = None
        self._password: str | None = None

    @property
    def host(self) -> str:
        """Return the host."""
        return self._host

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: dict[str, Any] | None = None,
        authenticated: bool = True,
        retry_auth: bool = True,
    ) -> dict[str, Any] | str:
        """Make an API request with optional authentication and retry."""
        url = f"{self._base_url}{path}"
        headers: dict[str, str] = {}
        if authenticated and self._auth_key:
            headers["AuthKey"] = self._auth_key

        try:
            resp = await self._session.request(
                method, url, json=json_data, headers=headers
            )
        except (aiohttp.ClientError, TimeoutError) as err:
            raise PrachtAlphaConnectionError(
                f"Cannot connect to {self._host}: {err}"
            ) from err

        if resp.status == 403:
            # Try to re-authenticate once
            if retry_auth and authenticated and self._password:
                await self._do_login(self._password)
                return await self._request(
                    method,
                    path,
                    json_data=json_data,
                    authenticated=authenticated,
                    retry_auth=False,
                )
            raise PrachtAlphaAuthError("Authentication failed")
        if resp.status != 200:
            text = await resp.text()
            raise PrachtAlphaError(f"API error {resp.status}: {text}")
        try:
            return await resp.json(content_type=None)
        except ValueError, aiohttp.ContentTypeError:
            return await resp.text()

    async def _do_login(self, password: str) -> str:
        """Perform login and return the auth key."""
        result = await self._request(
            "POST",
            "/api/v1/login",
            json_data={"Password": password},
            authenticated=False,
            retry_auth=False,
        )
        if not isinstance(result, dict) or "AuthKey" not in result:
            raise PrachtAlphaAuthError("Login failed: no AuthKey in response")
        self._auth_key = result["AuthKey"]
        return self._auth_key

    async def login(self, password: str) -> str:
        """Login to the wallbox and store credentials for auto-relogin."""
        self._password = password
        return await self._do_login(password)

    async def get_all(self) -> PrachtAlphaData:
        """Fetch all wallbox data from GET /api/v1/all."""
        result = await self._request("GET", "/api/v1/all")
        if not isinstance(result, dict):
            raise PrachtAlphaError("Unexpected response from /api/v1/all")
        return _parse_all_data(result)

    async def get_lock_status(self) -> PrachtAlphaLockStatus:
        """Fetch lock status from GET /api/v1/lock_status."""
        result = await self._request("GET", "/api/v1/lock_status")
        if not isinstance(result, dict):
            raise PrachtAlphaError("Unexpected response from /api/v1/lock_status")
        return _parse_lock_status(result)

    async def set_power(self, max_total: int, max_car1: int, max_car2: int) -> None:
        """Set current levels via POST /api/v1/power."""
        _LOGGER.debug(
            "Setting power: total=%s, car1=%s, car2=%s", max_total, max_car1, max_car2
        )
        result = await self._request(
            "POST",
            "/api/v1/power",
            json_data={
                "MaxCurrentTotal": max_total,
                "MaxCurrentCar1": max_car1,
                "MaxCurrentCar2": max_car2,
            },
        )
        _LOGGER.debug("set_power response: %s", result)

    async def lock(self, side: int) -> None:
        """Lock a side of the wallbox."""
        await self._request(
            "POST",
            "/api/v1/lock",
            json_data={"action": "lock", "side": side},
        )

    async def unlock(self, side: int) -> None:
        """Unlock a side of the wallbox."""
        await self._request(
            "POST",
            "/api/v1/lock",
            json_data={"action": "unlock", "side": side},
        )

    async def get_led_mode(self) -> int:
        """Get LED mode from GET /api/v1/led_mode."""
        result = await self._request("GET", "/api/v1/led_mode")
        if not isinstance(result, dict):
            raise PrachtAlphaError("Unexpected response from /api/v1/led_mode")
        return result.get("ledMode", 0)

    async def set_led_mode(self, mode: int) -> None:
        """Set LED mode via POST /api/v1/led_mode."""
        await self._request(
            "POST",
            "/api/v1/led_mode",
            json_data={"ledMode": mode},
        )
