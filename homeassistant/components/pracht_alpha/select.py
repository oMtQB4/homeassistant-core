"""Support for Pracht Alpha select entities."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import LED_MODE_MAP, LED_MODE_REVERSE_MAP
from .coordinator import PrachtAlphaConfigEntry, PrachtAlphaDataUpdateCoordinator
from .entity import PrachtAlphaEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PrachtAlphaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Pracht Alpha select entities based on a config entry."""
    coordinator = entry.runtime_data.coordinator
    if coordinator.data.all_data.led_support:
        async_add_entities(
            [
                PrachtAlphaLedModeSelectEntity(
                    entry=entry,
                    coordinator=coordinator,
                )
            ]
        )


class PrachtAlphaLedModeSelectEntity(PrachtAlphaEntity, SelectEntity):
    """Defines a Pracht Alpha LED mode select entity."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(LED_MODE_MAP.values())
    _attr_translation_key = "led_mode"

    def __init__(
        self,
        *,
        entry: PrachtAlphaConfigEntry,
        coordinator: PrachtAlphaDataUpdateCoordinator,
    ) -> None:
        """Initialize the LED mode select entity."""
        super().__init__(
            entry=entry,
            coordinator=coordinator,
            description=SelectEntityDescription(key="led_mode"),
        )

    @property
    def current_option(self) -> str | None:
        """Return the current LED mode."""
        # The LED mode is not in the /all response, so we track it separately
        return self._attr_current_option

    async def async_added_to_hass(self) -> None:
        """Fetch initial LED mode when added to hass."""
        await super().async_added_to_hass()
        try:
            mode = await self.coordinator.api.get_led_mode()
            self._attr_current_option = LED_MODE_MAP.get(mode, "on")
        except Exception:  # noqa: BLE001
            self._attr_current_option = "on"

    async def async_select_option(self, option: str) -> None:
        """Change the LED mode."""
        mode = LED_MODE_REVERSE_MAP.get(option, 0)
        await self.coordinator.api.set_led_mode(mode)
        self._attr_current_option = option
        self.async_write_ha_state()
