"""Data update coordinator for Pracht Alpha wallbox."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    PrachtAlphaApi,
    PrachtAlphaAuthError,
    PrachtAlphaConnectionError,
    PrachtAlphaData,
    PrachtAlphaError,
    PrachtAlphaLockStatus,
)
from .const import DOMAIN, LOGGER


@dataclass
class PrachtAlphaCoordinatorData:
    """Combined data from the wallbox."""

    all_data: PrachtAlphaData
    lock_status: PrachtAlphaLockStatus | None


@dataclass(kw_only=True)
class PrachtAlphaRuntimeData:
    """Runtime data for the Pracht Alpha integration."""

    coordinator: PrachtAlphaDataUpdateCoordinator
    api: PrachtAlphaApi


type PrachtAlphaConfigEntry = ConfigEntry[PrachtAlphaRuntimeData]


class PrachtAlphaDataUpdateCoordinator(
    DataUpdateCoordinator[PrachtAlphaCoordinatorData]
):
    """Class to manage fetching Pracht Alpha data."""

    config_entry: PrachtAlphaConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: PrachtAlphaConfigEntry,
        api: PrachtAlphaApi,
    ) -> None:
        """Initialize the coordinator."""
        self.api = api
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"Pracht Alpha {entry.title}",
            update_interval=timedelta(seconds=15),
        )

    async def _async_update_data(self) -> PrachtAlphaCoordinatorData:
        """Fetch data from the Pracht Alpha wallbox."""
        try:
            all_data = await self.api.get_all()
        except PrachtAlphaAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="authentication_error",
            ) from err
        except PrachtAlphaConnectionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="communication_error",
                translation_placeholders={"error": str(err)},
            ) from err
        except PrachtAlphaError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="unknown_error",
                translation_placeholders={"error": str(err)},
            ) from err

        lock_status = None
        if all_data.support_lock_unlock:
            try:
                lock_status = await self.api.get_lock_status()
            except (PrachtAlphaConnectionError, PrachtAlphaError) as err:
                LOGGER.debug("Failed to fetch lock status: %s", err)

        return PrachtAlphaCoordinatorData(
            all_data=all_data,
            lock_status=lock_status,
        )
