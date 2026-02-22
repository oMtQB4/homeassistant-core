"""Support for Pracht Alpha binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PrachtAlphaConfigEntry, PrachtAlphaCoordinatorData
from .entity import PrachtAlphaEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PrachtAlphaBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Pracht Alpha binary sensor."""

    has_fn: Callable[[PrachtAlphaCoordinatorData], bool] = lambda _: True
    is_on_fn: Callable[[PrachtAlphaCoordinatorData], bool]


DESCRIPTIONS: tuple[PrachtAlphaBinarySensorDescription, ...] = (
    PrachtAlphaBinarySensorDescription(
        key="car1_connected",
        translation_key="car1_connected",
        device_class=BinarySensorDeviceClass.PLUG,
        is_on_fn=lambda x: x.all_data.status_car1 >= 1,
    ),
    PrachtAlphaBinarySensorDescription(
        key="car2_connected",
        translation_key="car2_connected",
        device_class=BinarySensorDeviceClass.PLUG,
        has_fn=lambda x: x.all_data.num_charging_points == 2,
        is_on_fn=lambda x: x.all_data.status_car2 >= 1,
    ),
    PrachtAlphaBinarySensorDescription(
        key="car1_charging",
        translation_key="car1_charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        is_on_fn=lambda x: x.all_data.status_car1 >= 2,
    ),
    PrachtAlphaBinarySensorDescription(
        key="car2_charging",
        translation_key="car2_charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        has_fn=lambda x: x.all_data.num_charging_points == 2,
        is_on_fn=lambda x: x.all_data.status_car2 >= 2,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PrachtAlphaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Pracht Alpha binary sensors based on a config entry."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        PrachtAlphaBinarySensorEntity(
            entry=entry,
            coordinator=coordinator,
            description=description,
        )
        for description in DESCRIPTIONS
        if description.has_fn(coordinator.data)
    )


class PrachtAlphaBinarySensorEntity(PrachtAlphaEntity, BinarySensorEntity):
    """Defines a Pracht Alpha binary sensor."""

    entity_description: PrachtAlphaBinarySensorDescription

    @property
    def is_on(self) -> bool:
        """Return the state of the binary sensor."""
        return self.entity_description.is_on_fn(self.coordinator.data)
