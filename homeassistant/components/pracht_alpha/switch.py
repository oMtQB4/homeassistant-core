"""Support for Pracht Alpha switch entities."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PrachtAlphaConfigEntry, PrachtAlphaCoordinatorData
from .entity import PrachtAlphaEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class PrachtAlphaSwitchDescription(SwitchEntityDescription):
    """Describe a Pracht Alpha switch entity."""

    has_fn: Callable[[PrachtAlphaCoordinatorData], bool] = lambda _: True
    is_on_fn: Callable[[PrachtAlphaCoordinatorData], bool]
    side: int


DESCRIPTIONS: tuple[PrachtAlphaSwitchDescription, ...] = (
    PrachtAlphaSwitchDescription(
        key="lock_side1",
        translation_key="lock_side1",
        device_class=SwitchDeviceClass.SWITCH,
        has_fn=lambda x: x.all_data.support_lock_unlock,
        is_on_fn=lambda x: (
            x.lock_status is not None and x.lock_status.lock_status1 == "Locked"
        ),
        side=0,
    ),
    PrachtAlphaSwitchDescription(
        key="lock_side2",
        translation_key="lock_side2",
        device_class=SwitchDeviceClass.SWITCH,
        has_fn=lambda x: (
            x.all_data.support_lock_unlock and x.all_data.num_charging_points == 2
        ),
        is_on_fn=lambda x: (
            x.lock_status is not None and x.lock_status.lock_status2 == "Locked"
        ),
        side=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PrachtAlphaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Pracht Alpha switch entities based on a config entry."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        PrachtAlphaSwitchEntity(
            entry=entry,
            coordinator=coordinator,
            description=description,
        )
        for description in DESCRIPTIONS
        if description.has_fn(coordinator.data)
    )


class PrachtAlphaSwitchEntity(PrachtAlphaEntity, SwitchEntity):
    """Defines a Pracht Alpha switch entity for lock/unlock."""

    entity_description: PrachtAlphaSwitchDescription

    @property
    def is_on(self) -> bool:
        """Return true if the side is locked."""
        return self.entity_description.is_on_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Lock the side."""
        await self.coordinator.api.lock(self.entity_description.side)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Unlock the side."""
        await self.coordinator.api.unlock(self.entity_description.side)
        await self.coordinator.async_request_refresh()
