from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

from concord4ws import Concord4WSClient, Concord4Zone

from .const import DOMAIN, ZONE_STATE


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities
):
    """Add sensors for passed config_entry in HA."""
    name: str = hass.data[DOMAIN][config.entry_id]["name"]
    hub: Concord4WSClient = hass.data[DOMAIN][config.entry_id]["hub"]

    devices = []
    for zone in hub._state.zones:
        devices.append(ZoneSensor(name, hub, zone))
    if devices:
        async_add_entities(devices)


class SensorBase(Entity):
    """Base representation of a Hello World Sensor."""

    should_poll: bool = False

    def __init__(self, name: str, hub: Concord4WSClient, zone_id: str):
        """Initialize the sensor."""
        self._internal_config_name: str = name
        self._hub: Concord4WSClient = hub
        self._zone_id: str = zone_id

    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(DOMAIN, f"{self._internal_config_name}")}}

    @property
    def available(self) -> bool:
        """Return True if roller and hub is available."""
        return self._hub.connected

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._hub.register_callback(self._zone_id, self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._hub.remove_callback(self._zone_id, self.async_write_ha_state)

    @property
    def _zone(self) -> Concord4Zone:
        return self._hub._state.zones[self._zone_id]


class ZoneSensor(SensorBase):
    """Representation of a Sensor."""

    device_class: SensorDeviceClass = SensorDeviceClass.ENUM
    _attr_unit_of_measurement = None
    _attr_has_entity_name = True

    def __init__(self, name: str, hub: Concord4WSClient, zone_id: str):
        """Initialize the sensor."""
        super().__init__(name, hub, zone_id)

        self._attr_unique_id = f"concord4_{self._zone.id}_zone"
        self.entity_description = SensorEntityDescription(
            name=f"{self._zone.zone_text}",
            device_class=SensorDeviceClass.ENUM,
            key="zone_status",
            native_unit_of_measurement=None,
            options=ZONE_STATE,
        )

    @property
    def name(self):
        """Name of the entity."""
        return f"{self._zone.zone_text}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._zone.zone_status
