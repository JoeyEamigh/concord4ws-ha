"""Config flow for Concord4 WebSocket integration."""

from __future__ import annotations

import logging
from typing import Any

from concord4ws import Concord4WSClient
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("name"): str,
        vol.Required("host"): str,
        vol.Required("port", default=8080): cv.port,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    hub = Concord4WSClient(data["host"], data["port"])

    try:
        await hub.test_connect()
    except Exception as err:
        raise CannotConnect from err

    return {"name": data["name"]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Concord WebSocket."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["name"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    # @staticmethod
    # @callback
    # def async_get_options_flow(
    #     config_entry: config_entries.ConfigEntry,
    # ) -> config_entries.OptionsFlow:
    #     """Create the options flow."""
    #     return Concord4OptionsFlowHandler(config_entry)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


# STEP_INIT_CONFIG_SCHEMA = vol.Schema(
#     {
#         vol.Required("default_arm_stay_mode", default="normal"): SelectSelector(
#             SelectSelectorConfig(
#                 options=["normal", "instant", "silent"],
#                 mode=SelectSelectorMode.LIST,
#                 translation_key="default_arm_stay_mode",
#             )
#         ),
#         vol.Required("default_arm_away_mode", default="normal"): SelectSelector(
#             SelectSelectorConfig(
#                 options=["normal", "instant", "silent"],
#                 mode=SelectSelectorMode.LIST,
#                 translation_key="default_arm_away_mode",
#             )
#         ),
#     }
# )


# class Concord4OptionsFlowHandler(config_entries.OptionsFlow):
#     """Handle Concord4 options."""

#     def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
#         """Initialize options flow."""
#         self.config_entry = config_entry

#     async def async_step_init(
#         self, user_input: dict[str, Any] | None = None
#     ) -> FlowResult:
#         """Manage the options."""
#         if user_input is not None:
#             return self.async_create_entry(title="", data=user_input)

#         return self.async_show_form(
#             step_id="init",
#             data_schema=STEP_INIT_CONFIG_SCHEMA,
#         )
