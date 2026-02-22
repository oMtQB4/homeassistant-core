"""Integration for Pracht Alpha wallbox."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import PrachtAlphaApi, PrachtAlphaAuthError, PrachtAlphaConnectionError
from .coordinator import (
    PrachtAlphaConfigEntry,
    PrachtAlphaDataUpdateCoordinator,
    PrachtAlphaRuntimeData,
)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: PrachtAlphaConfigEntry) -> bool:
    """Set up Pracht Alpha from a config entry."""
    session = async_create_clientsession(hass)
    api = PrachtAlphaApi(host=entry.data[CONF_HOST], session=session)

    try:
        await api.login(password=entry.data[CONF_PASSWORD])
    except PrachtAlphaConnectionError as err:
        raise ConfigEntryNotReady(
            f"Could not connect to Pracht Alpha at {entry.data[CONF_HOST]}"
        ) from err
    except PrachtAlphaAuthError as err:
        raise ConfigEntryAuthFailed from err

    coordinator = PrachtAlphaDataUpdateCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = PrachtAlphaRuntimeData(
        coordinator=coordinator,
        api=api,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: PrachtAlphaConfigEntry
) -> bool:
    """Unload Pracht Alpha config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
