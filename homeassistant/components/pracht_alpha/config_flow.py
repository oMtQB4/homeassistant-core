"""Config flow to configure the Pracht Alpha integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import PrachtAlphaApi, PrachtAlphaAuthError, PrachtAlphaConnectionError
from .const import DOMAIN, LOGGER


class PrachtAlphaFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a Pracht Alpha config flow."""

    VERSION = 1

    _discovery_info: ZeroconfServiceInfo

    async def _async_validate_input(
        self, host: str, password: str
    ) -> tuple[dict[str, str], str | None]:
        """Validate host and password, return (errors, device_id)."""
        errors: dict[str, str] = {}
        device_id: str | None = None
        session = async_create_clientsession(self.hass)
        api = PrachtAlphaApi(host=host, session=session)
        try:
            await api.login(password=password)
            data = await api.get_all()
        except PrachtAlphaAuthError:
            errors[CONF_PASSWORD] = "invalid_auth"
        except PrachtAlphaConnectionError:
            errors[CONF_HOST] = "cannot_connect"
        except Exception:  # noqa: BLE001
            LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            device_id = data.device_id
        return errors, device_id

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, device_id = await self._async_validate_input(
                user_input[CONF_HOST], user_input[CONF_PASSWORD]
            )
            if not errors and device_id:
                await self.async_set_unique_id(device_id, raise_on_progress=False)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Pracht Alpha", data=user_input)
        else:
            user_input = {}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=user_input.get(CONF_HOST)
                    ): TextSelector(TextSelectorConfig(autocomplete="off")),
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery of a Pracht Alpha device."""
        self._discovery_info = discovery_info
        host = str(discovery_info.ip_address)

        # Abort if this host is already configured
        self._async_abort_entries_match({CONF_HOST: host})

        self.context.update(
            {
                "title_placeholders": {"name": discovery_info.hostname.rstrip(".")},
                "configuration_url": f"http://{discovery_info.host}",
            },
        )
        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by zeroconf."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(self._discovery_info.ip_address)
            errors, device_id = await self._async_validate_input(
                host, user_input[CONF_PASSWORD]
            )
            if not errors and device_id:
                await self.async_set_unique_id(device_id, raise_on_progress=False)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(
                    title="Pracht Alpha",
                    data={
                        CONF_HOST: host,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            description_placeholders={
                "hostname": self._discovery_info.hostname.rstrip("."),
                "host": str(self._discovery_info.ip_address),
            },
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle initiation of re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle re-authentication."""
        errors: dict[str, str] = {}

        if user_input is not None:
            reauth_entry = self._get_reauth_entry()
            errors, _device_id = await self._async_validate_input(
                reauth_entry.data[CONF_HOST], user_input[CONF_PASSWORD]
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data={
                        CONF_HOST: reauth_entry.data[CONF_HOST],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )
