"""The Concord WebSocket integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from concord4ws import Concord4WSClient

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.ALARM_CONTROL_PANEL, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Concord WebSocket from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    hub = Concord4WSClient(entry.data["host"], entry.data["port"])
    await hub.connect()

    hass.data[DOMAIN][entry.entry_id] = {"hub": hub, "name": entry.data["name"]}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
