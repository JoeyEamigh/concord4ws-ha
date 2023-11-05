from typing import Final
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityDescription,
)
from homeassistant.components.alarm_control_panel.const import (
    AlarmControlPanelEntityFeature,
)
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_DISARMED,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from concord4ws import Concord4WSClient, Concord4Zone, Concord4PartitionArmingLevel

from .const import DOMAIN, ZONE_STATE


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities
):
    """Add sensors for passed config_entry in HA."""
    name: str = hass.data[DOMAIN][config.entry_id]["name"]
    hub: Concord4WSClient = hass.data[DOMAIN][config.entry_id]["hub"]

    async_add_entities([Concord4AlarmPanel(name, hub)])


class Concord4AlarmPanel(AlarmControlPanelEntity):
    """Base representation of a Hello World Sensor."""

    should_poll: bool = False

    def __init__(self, name: str, hub: Concord4WSClient):
        """Initialize the sensor."""

        self._internal_config_name: str = name
        self._attr_unique_id = f"{name}_concord_alarm_panel"
        self.entity_description = AlarmControlPanelEntityDescription(
            key="{name}_concord_alarm_panel",
            name=f"{name}",
            has_entity_name=True,
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{name}")},
            manufacturer="GE",
            model="Concord4",
            name=f"{name}",
            via_device=(DOMAIN, f"Concord4WS"),
        )

        self._hub: Concord4WSClient = hub
        self._attr_code_arm_required = False
        # self._attr_supported_features = (
        #     AlarmControlPanelEntityFeature.ARM_HOME
        #     | AlarmControlPanelEntityFeature.ARM_AWAY
        # )

    @property
    def name(self):
        """Name of the entity."""
        return f"{self._internal_config_name}"

    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, "concord_alarm_panel")}}

    @property
    def available(self) -> bool:
        """Return True if roller and hub is available."""
        return self._hub.connected

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._hub.register_callback(
            next(iter(self._hub.state.partitions)), self.async_write_ha_state
        )

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._hub.remove_callback(
            next(iter(self._hub.state.partitions)), self.async_write_ha_state
        )

    @property
    def state(self) -> str | None:
        """Return the state of the device."""
        states = set()

        for partition in self._hub.state.partitions.values():
            match partition.arming_level:
                case Concord4PartitionArmingLevel.OFF:
                    states.add(STATE_ALARM_DISARMED)
                case Concord4PartitionArmingLevel.STAY:
                    states.add(STATE_ALARM_ARMED_HOME)
                case Concord4PartitionArmingLevel.AWAY:
                    states.add(STATE_ALARM_ARMED_AWAY)

        if len(states) == 1:
            return states.pop()
        else:
            return None
