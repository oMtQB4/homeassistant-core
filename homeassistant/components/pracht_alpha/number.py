"""Support for Pracht Alpha number entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.const import EntityCategory, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import (
    PrachtAlphaConfigEntry,
    PrachtAlphaCoordinatorData,
    PrachtAlphaDataUpdateCoordinator,
)
from .entity import PrachtAlphaEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class PrachtAlphaNumberDescription(NumberEntityDescription):
    """Describe a Pracht Alpha number entity."""

    has_fn: Callable[[PrachtAlphaCoordinatorData], bool] = lambda _: True
    value_fn: Callable[[PrachtAlphaCoordinatorData], int]
    max_value_fn: Callable[[PrachtAlphaCoordinatorData], int]


DESCRIPTIONS: tuple[PrachtAlphaNumberDescription, ...] = (
    PrachtAlphaNumberDescription(
        key="max_current_total",
        translation_key="max_current_total",
        device_class=NumberDeviceClass.CURRENT,
        entity_category=EntityCategory.CONFIG,
        native_min_value=6,
        native_step=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda x: x.all_data.max_current_total,
        max_value_fn=lambda x: x.all_data.current_setting_input_lead,
    ),
    PrachtAlphaNumberDescription(
        key="max_current_car1",
        translation_key="max_current_car1",
        device_class=NumberDeviceClass.CURRENT,
        entity_category=EntityCategory.CONFIG,
        native_min_value=6,
        native_step=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda x: x.all_data.max_current_car1,
        max_value_fn=lambda x: x.all_data.max_current_per_side,
    ),
    PrachtAlphaNumberDescription(
        key="max_current_car2",
        translation_key="max_current_car2",
        device_class=NumberDeviceClass.CURRENT,
        entity_category=EntityCategory.CONFIG,
        native_min_value=6,
        native_step=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        has_fn=lambda x: x.all_data.num_charging_points == 2,
        value_fn=lambda x: x.all_data.max_current_car2,
        max_value_fn=lambda x: x.all_data.max_current_per_side,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PrachtAlphaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Pracht Alpha number entities based on a config entry."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        PrachtAlphaNumberEntity(
            entry=entry,
            coordinator=coordinator,
            description=description,
        )
        for description in DESCRIPTIONS
        if description.has_fn(coordinator.data)
    )


class PrachtAlphaNumberEntity(PrachtAlphaEntity, NumberEntity):
    """Defines a Pracht Alpha number entity."""

    entity_description: PrachtAlphaNumberDescription

    def __init__(
        self,
        *,
        entry: PrachtAlphaConfigEntry,
        coordinator: PrachtAlphaDataUpdateCoordinator,
        description: PrachtAlphaNumberDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(entry=entry, coordinator=coordinator, description=description)
        self._attr_native_max_value = description.max_value_fn(coordinator.data)

    @property
    def native_value(self) -> int:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        """Set the current limit value.

        The API requires all three current values to be sent together.
        """
        data = self.coordinator.data.all_data
        total = data.max_current_total
        car1 = data.max_current_car1
        car2 = data.max_current_car2

        key = self.entity_description.key
        int_value = int(value)
        if key == "max_current_total":
            total = int_value
        elif key == "max_current_car1":
            car1 = int_value
        elif key == "max_current_car2":
            car2 = int_value

        await self.coordinator.api.set_power(total, car1, car2)
        await self.coordinator.async_request_refresh()
