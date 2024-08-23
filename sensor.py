"""Sensor platform for Concord4WS integration."""

import typing

from concord4ws import Concord4WSClient
from concord4ws.types import ZoneData, ZoneStatus

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, LOGGER, alarm_panel_identifier


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities
):
    """Add sensors for passed config_entry in HA."""
    name: str = hass.data[DOMAIN][config.entry_id]["name"]
    server: Concord4WSClient = hass.data[DOMAIN][config.entry_id]["server"]

    async_add_entities([ZoneSensor(server, name, zone) for zone in server.state.zones])


ZoneSensorType = typing.Literal[
    "motion", "window", "glass_break", "sliding_door", "door"
]

BaseZoneSensorStates = typing.Literal[
    "Faulted", "Alarm", "Trouble", "Bypassed", "Unknown"
]
BaseZoneSensorStatesMapping = {
    "faulted": "Faulted",
    "alarm": "Alarm",
    "trouble": "Trouble",
    "bypassed": "Bypassed",
    "unknown": "Unknown",
}
MotionSensorStates = typing.Literal["Clear", "Tripped", BaseZoneSensorStates]
MotionSensorStatesMapping: dict[ZoneStatus, MotionSensorStates] = {
    **typing.cast(dict[ZoneStatus, MotionSensorStates], BaseZoneSensorStatesMapping),
    "normal": "Clear",
    "tripped": "Tripped",
}
WindowSensorStates = typing.Literal["Closed", "Open", BaseZoneSensorStates]
WindowSensorStatesMapping: dict[ZoneStatus, WindowSensorStates] = {
    **typing.cast(dict[ZoneStatus, WindowSensorStates], BaseZoneSensorStatesMapping),
    "normal": "Closed",
    "tripped": "Open",
}
GlassBreakSensorStates = typing.Literal["Normal", "Broken", BaseZoneSensorStates]
GlassBreakSensorStatesMapping: dict[ZoneStatus, GlassBreakSensorStates] = {
    **typing.cast(
        dict[ZoneStatus, GlassBreakSensorStates], BaseZoneSensorStatesMapping
    ),
    "normal": "Normal",
    "tripped": "Broken",
}
SlidingDoorSensorStates = typing.Literal["Closed", "Open", BaseZoneSensorStates]
SlidingDoorSensorStatesMapping: dict[ZoneStatus, SlidingDoorSensorStates] = {
    **typing.cast(
        dict[ZoneStatus, SlidingDoorSensorStates], BaseZoneSensorStatesMapping
    ),
    "normal": "Closed",
    "tripped": "Open",
}
DoorSensorStates = typing.Literal["Closed", "Open", BaseZoneSensorStates]
DoorSensorStatesMapping: dict[ZoneStatus, DoorSensorStates] = {
    **typing.cast(dict[ZoneStatus, DoorSensorStates], BaseZoneSensorStatesMapping),
    "normal": "Closed",
    "tripped": "Open",
}
ZoneSensorTypeStatesMapping = {
    "motion": MotionSensorStatesMapping,
    "window": WindowSensorStatesMapping,
    "glass_break": GlassBreakSensorStatesMapping,
    "sliding_door": SlidingDoorSensorStatesMapping,
    "door": DoorSensorStatesMapping,
}
ZoneSensorTypeIconMapping = {
    "motion": {
        "Clear": "mdi:motion-sensor-off",
        "Tripped": "mdi:motion-sensor",
    },
    "window": {
        "Closed": "mdi:window-closed",
        "Open": "mdi:window-open",
    },
    "glass_break": {
        "Normal": "mdi:window-closed-variant",
        "Broken": "mdi:glass-fragile",
    },
    "sliding_door": {
        "Closed": "mdi:door-sliding",
        "Open": "mdi:door-sliding-open",
    },
    "door": {
        "Closed": "mdi:door",
        "Open": "mdi:door-open",
    },
}


class _Concord4ZoneConfig:
    sensor_type: ZoneSensorType

    def __init__(
        self, panel_name: str, sensor_name: str, zone_id: str, partition_number: int
    ):
        self.panel_name = panel_name
        self.sensor_name = sensor_name
        self.zone_id = zone_id
        self.partition_number = partition_number

        # assume sensor type based on name
        if "motion" in sensor_name.lower():
            self.sensor_type = "motion"
        elif "window" in sensor_name.lower():
            self.sensor_type = "window"
        elif "glass" in sensor_name.lower():
            self.sensor_type = "glass_break"
        elif "sliding" in sensor_name.lower():
            self.sensor_type = "sliding_door"
        else:
            self.sensor_type = "door"


class ZoneSensor(SensorEntity):
    """Representation of a Zone Sensor."""

    device_class: SensorDeviceClass = SensorDeviceClass.ENUM
    _attr_unit_of_measurement = None
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, server: Concord4WSClient, name: str, zone_id: str):
        """Initialize the sensor."""

        self._server: Concord4WSClient = server
        zone = self._server.state.zones[zone_id]

        sensor_name = zone.zone_text.title()
        LOGGER.debug("setting up zone sensor: %s", sensor_name)

        self._config = _Concord4ZoneConfig(
            panel_name=name,
            sensor_name=sensor_name,
            zone_id=zone_id,
            partition_number=zone.partition_number,
        )

        self.entity_description = SensorEntityDescription(
            name=sensor_name,
            device_class=SensorDeviceClass.ENUM,
            key=f"{self._config.zone_id}_zone_status",
            native_unit_of_measurement=None,
            options=list(
                ZoneSensorTypeStatesMapping[self._config.sensor_type].values()
            ),
        )
        self._attr_unique_id: str = (
            f"{self._server.state.panel.serial_number}_{self.entity_description.key}"
        )

    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    alarm_panel_identifier(
                        self._server.state.panel.serial_number,
                        self._config.partition_number,
                    ),
                )
            },
        )

    @property
    def available(self):
        """Return if the sensor data are available."""
        return self._server.connected

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._server.register_callback(
            self._get_zone().callback_id(), self.async_write_ha_state
        )

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._server.remove_callback(
            self._get_zone().callback_id(), self.async_write_ha_state
        )

    @property
    def state(self):
        """Return the state of the sensor."""
        return ZoneSensorTypeStatesMapping[self._config.sensor_type][
            self._get_zone().zone_status
        ]

    @property
    def icon(self) -> str | None:
        """Icon of the sensor, based on status and inferred type."""
        return ZoneSensorTypeIconMapping[self._config.sensor_type][self.state]

    def _get_zone(self) -> ZoneData:
        """Get the zone data."""
        return self._server.state.zones[self._config.zone_id]
