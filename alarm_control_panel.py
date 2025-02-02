"""Alarm Control Panel for the Concord4 WebSocket integration."""

from concord4ws import Concord4WSClient
from concord4ws.types import code_to_keypresses

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityDescription,
)
from homeassistant.components.alarm_control_panel.const import (
    AlarmControlPanelEntityFeature,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_HOME,
    STATE_ALARM_DISARMED,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DOMAIN,
    LOGGER,
    USER_CODE_SERVICE_SCHEMA,
    alarm_panel_identifier,
    alarm_panel_uid,
)


async def async_setup_entry(
    hass: HomeAssistant, config: ConfigEntry, async_add_entities
):
    """Add sensors for passed config_entry in HA."""
    name: str = hass.data[DOMAIN][config.entry_id]["name"]
    server: Concord4WSClient = hass.data[DOMAIN][config.entry_id]["server"]

    async_add_entities(
        [
            Concord4AlarmPanel(
                server, name, server.state.partitions[partition].partition_number
            )
            for partition in server.state.partitions
            if len(server.state.partitions[partition].zones) > 0
        ]
    )

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "alarm_arm_home_instant",
        USER_CODE_SERVICE_SCHEMA,
        "async_alarm_arm_home_instant",
    )
    platform.async_register_entity_service(
        "alarm_arm_home_silent",
        USER_CODE_SERVICE_SCHEMA,
        "async_alarm_arm_home_silent",
    )
    platform.async_register_entity_service(
        "alarm_arm_away_instant",
        USER_CODE_SERVICE_SCHEMA,
        "async_alarm_arm_away_instant",
    )
    platform.async_register_entity_service(
        "alarm_arm_away_silent",
        USER_CODE_SERVICE_SCHEMA,
        "async_alarm_arm_away_silent",
    )


class _Concord4PanelConfig:
    def __init__(self, panel_name: str, partition_number: int):
        self.panel_name = panel_name
        self.partition_number = partition_number


class Concord4AlarmPanel(AlarmControlPanelEntity):
    """Representation of a Concord4 Alarm Panel."""

    should_poll: bool = False
    _attr_has_entity_name = True
    _attr_code_arm_required = True
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
    )
    _attr_code_format = CodeFormat.NUMBER

    def __init__(self, server: Concord4WSClient, name: str, partition_number: int):
        """Initialize the alarm panel."""

        LOGGER.debug(f"Creating alarm panel for {name} partition {partition_number}")

        self._server: Concord4WSClient = server
        self._config = _Concord4PanelConfig(
            panel_name=name, partition_number=partition_number
        )

        self._attr_unique_id = alarm_panel_uid(
            self._server.state.panel.serial_number, partition_number
        )
        self.entity_description = AlarmControlPanelEntityDescription(
            key=alarm_panel_identifier(
                self._server.state.panel.serial_number, partition_number
            ),
            name="Alarm Panel"
            if partition_number == 1
            else f"Partition {partition_number} Alarm Panel",
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
            manufacturer="GE",
            model=self._server.state.panel.panel_type.capitalize()
            if self._server.state.panel.panel_type is not None
            else "Concord",
            name=self._config.panel_name,
            serial_number=self._server.state.panel.serial_number,
            hw_version=self._server.state.panel.hardware_revision,
            sw_version=self._server.state.panel.software_revision,
        )

    @property
    def available(self) -> bool:
        """Return True if websocket server (and by extension the alarm panel) is available."""
        return self._server.connected

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        self._server.register_callback(
            self._get_partition().callback_id(), self.async_write_ha_state
        )

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        self._server.remove_callback(
            self._get_partition().callback_id(), self.async_write_ha_state
        )

    @property
    def state(self) -> str | None:
        """Return the state of the device."""

        match self._get_partition().arming_level:
            case "off":
                return STATE_ALARM_DISARMED
            case "away":
                return STATE_ALARM_ARMED_AWAY
            case "stay":
                return STATE_ALARM_ARMED_HOME
            case "home":     ###adde case to match return from panel
                return STATE_ALARM_ARMED_HOME
            case _:
                return None

    async def async_alarm_disarm(self, code=None) -> None:
        """Send disarm command."""
        if code is None:
            raise Concord4PanelError("Code required to disarm")

        await self._server.disarm(
            code=code_to_keypresses(code), partition=self._config.partition_number
        )

    async def async_handle_alarm_arm_home(self, code=None) -> None:
        """Send arm home command."""
        if code is None:
            raise Concord4PanelError("Code required to arm home")

        await self._server.arm(
            "stay",
            code=code_to_keypresses(code),
            partition=self._config.partition_number,
        )

    async def async_alarm_arm_home_instant(self, code: str | None = None) -> None:
        """Send arm stay instant command."""
        if code is None:
            raise Concord4PanelError("Code required to arm home")

        await self._server.arm(
            "stay",
            code=code_to_keypresses(code),
            level="instant",
            partition=self._config.partition_number,
        )

    async def async_alarm_arm_home_silent(self, code: str | None = None) -> None:
        """Send arm stay silent command."""
        if code is None:
            raise Concord4PanelError("Code required to arm home")

        await self._server.arm(
            "stay",
            code=code_to_keypresses(code),
            level="silent",
            partition=self._config.partition_number,
        )

    async def async_handle_alarm_arm_away(self, code=None) -> None:
        """Send arm away command."""
        if code is None:
            raise Concord4PanelError("Code required to arm away")

        await self._server.arm(
            "away",
            code=code_to_keypresses(code),
            partition=self._config.partition_number,
        )

    async def async_alarm_arm_away_instant(self, code: str | None = None) -> None:
        """Send arm away instant command."""
        if code is None:
            raise Concord4PanelError("Code required to arm away")

        await self._server.arm(
            "away",
            code=code_to_keypresses(code),
            level="instant",
            partition=self._config.partition_number,
        )

    async def async_alarm_arm_away_silent(self, code: str | None = None) -> None:
        """Send arm away silent command."""
        if code is None:
            raise Concord4PanelError("Code required to arm away")

        await self._server.arm(
            "away",
            code=code_to_keypresses(code),
            level="silent",
            partition=self._config.partition_number,
        )

    def _get_partition(self):
        return self._server.state.partitions[self._config.partition_number]


class Concord4PanelError(HomeAssistantError):
    """Base error class for Concord4 Panel."""

    def __init__(self, message: str):
        """Initialize the error."""
        super().__init__(message)
        self.message = message
        self.name = "Concord4PanelError"
