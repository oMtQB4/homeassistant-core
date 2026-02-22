"""Constants for the Pracht Alpha integration."""

from __future__ import annotations

import logging

DOMAIN = "pracht_alpha"
LOGGER = logging.getLogger(__package__)

CAR_STATUS_MAP: dict[int, str] = {
    0: "disconnected",
    1: "connected",
    2: "charging",
    3: "charging_with_cooling",
    4: "error",
}

LED_MODE_MAP: dict[int, str] = {
    0: "on",
    1: "on_if_required",
    2: "off",
}

LED_MODE_REVERSE_MAP: dict[str, int] = {v: k for k, v in LED_MODE_MAP.items()}
