"""Base entity for the Pracht Alpha integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PrachtAlphaConfigEntry, PrachtAlphaDataUpdateCoordinator


class PrachtAlphaEntity(CoordinatorEntity[PrachtAlphaDataUpdateCoordinator]):
    """Defines a Pracht Alpha entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        *,
        entry: PrachtAlphaConfigEntry,
        coordinator: PrachtAlphaDataUpdateCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize the Pracht Alpha entity."""
        super().__init__(coordinator=coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"

        all_data = coordinator.data.all_data
        model = "Alpha DUO" if all_data.num_charging_points == 2 else "Alpha MONO"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, all_data.device_id)},
            manufacturer="Pracht",
            model=model,
            name="Pracht Alpha",
            sw_version=all_data.software_version,
            hw_version=str(all_data.hardware_revision),
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )
