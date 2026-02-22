"""Support for Pracht Alpha sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.dt import utcnow

from .const import CAR_STATUS_MAP
from .coordinator import PrachtAlphaConfigEntry, PrachtAlphaCoordinatorData
from .entity import PrachtAlphaEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class PrachtAlphaSensorDescription(SensorEntityDescription):
    """Describe a Pracht Alpha sensor."""

    has_fn: Callable[[PrachtAlphaCoordinatorData], bool] = lambda _: True
    value_fn: Callable[
        [PrachtAlphaCoordinatorData], datetime | float | int | str | None
    ]


DESCRIPTIONS: tuple[PrachtAlphaSensorDescription, ...] = (
    PrachtAlphaSensorDescription(
        key="power_car1",
        translation_key="power_car1",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_fn=lambda x: x.all_data.current_meas_support > 0,
        value_fn=lambda x: x.all_data.power_car1,
    ),
    PrachtAlphaSensorDescription(
        key="power_car2",
        translation_key="power_car2",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        has_fn=lambda x: (
            x.all_data.num_charging_points == 2 and x.all_data.current_meas_support > 0
        ),
        value_fn=lambda x: x.all_data.power_car2,
    ),
    PrachtAlphaSensorDescription(
        key="current_car1",
        translation_key="current_car1",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda x: x.all_data.current_car1,
    ),
    PrachtAlphaSensorDescription(
        key="current_car2",
        translation_key="current_car2",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        has_fn=lambda x: x.all_data.num_charging_points == 2,
        value_fn=lambda x: x.all_data.current_car2,
    ),
    PrachtAlphaSensorDescription(
        key="status_car1",
        translation_key="status_car1",
        device_class=SensorDeviceClass.ENUM,
        options=list(CAR_STATUS_MAP.values()),
        value_fn=lambda x: CAR_STATUS_MAP.get(x.all_data.status_car1, "disconnected"),
    ),
    PrachtAlphaSensorDescription(
        key="status_car2",
        translation_key="status_car2",
        device_class=SensorDeviceClass.ENUM,
        options=list(CAR_STATUS_MAP.values()),
        has_fn=lambda x: x.all_data.num_charging_points == 2,
        value_fn=lambda x: CAR_STATUS_MAP.get(x.all_data.status_car2, "disconnected"),
    ),
    PrachtAlphaSensorDescription(
        key="comm_pcb_temperature",
        translation_key="comm_pcb_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=1,
        value_fn=lambda x: x.all_data.comm_pcb_temperature,
    ),
    PrachtAlphaSensorDescription(
        key="box_temperature",
        translation_key="box_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
        has_fn=lambda x: x.all_data.box_temperature != 255,
        value_fn=lambda x: x.all_data.box_temperature,
    ),
    PrachtAlphaSensorDescription(
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda x: (
            utcnow().replace(microsecond=0) - timedelta(milliseconds=x.all_data.uptime)
        ),
    ),
    PrachtAlphaSensorDescription(
        key="energy_car1",
        translation_key="energy_car1",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        has_fn=lambda x: x.all_data.energy_car1 is not None,
        value_fn=lambda x: x.all_data.energy_car1,
    ),
    PrachtAlphaSensorDescription(
        key="energy_car2",
        translation_key="energy_car2",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        has_fn=lambda x: (
            x.all_data.num_charging_points == 2 and x.all_data.energy_car2 is not None
        ),
        value_fn=lambda x: x.all_data.energy_car2,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PrachtAlphaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Pracht Alpha sensors based on a config entry."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        PrachtAlphaSensorEntity(
            entry=entry,
            coordinator=coordinator,
            description=description,
        )
        for description in DESCRIPTIONS
        if description.has_fn(coordinator.data)
    )


class PrachtAlphaSensorEntity(PrachtAlphaEntity, SensorEntity):
    """Defines a Pracht Alpha sensor."""

    entity_description: PrachtAlphaSensorDescription

    @property
    def native_value(self) -> datetime | float | int | str | None:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
