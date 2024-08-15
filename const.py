"""Constants for the Concord4 WebSocket integration."""

import logging

import voluptuous as vol

from homeassistant.const import ATTR_CODE
from homeassistant.helpers.typing import VolDictType

DOMAIN = "concord4ws"

LOGGER = logging.getLogger("concord4ws-ha")
LOGGER.setLevel(logging.DEBUG)

LIB_LOGGER = logging.getLogger("concord4ws")
LIB_LOGGER.setLevel(logging.DEBUG)


def alarm_panel_identifier(serial_number: str, partition_number: int) -> str:
    """Generate a unique identifier for a partition."""
    return f"{serial_number}_p{partition_number}"


def alarm_panel_uid(serial_number: str, partition_number: int) -> str:
    """Generate a unique identifier for a partition."""
    return f"{serial_number}_p{partition_number}_alarm_panel"


USER_CODE_SERVICE_SCHEMA: VolDictType = {
    vol.Required(ATTR_CODE): vol.All(vol.Coerce(int), vol.Range(0, 9999))
}
