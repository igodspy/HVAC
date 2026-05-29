"""Config flow for Mitsubishi Aircon."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import DOMAIN, HUMIDITY_ENTITY, REMOTE_ENTITY, TEMPERARURE_ENTITY

CONF_AREA_ID = "area_id"
DEFAULT_HUMIDITY_ENTITY = ""
DEFAULT_NAME = "AC"
DEFAULT_TEMPERATURE_ENTITY = ""
FLOW_TITLE = "Add AC"


def _entity_selector(domain):
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=domain)
    )


def _sensor_selector(device_class):
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="sensor",
            device_class=device_class,
        )
    )


def _sensor_options_schema(config_entry):
    current_data = {
        **config_entry.data,
        **config_entry.options,
    }
    return vol.Schema(
        {
            vol.Optional(
                TEMPERARURE_ENTITY,
                default=current_data.get(
                    TEMPERARURE_ENTITY,
                    DEFAULT_TEMPERATURE_ENTITY,
                ),
            ): _sensor_selector("temperature"),
            vol.Optional(
                HUMIDITY_ENTITY,
                default=current_data.get(
                    HUMIDITY_ENTITY,
                    DEFAULT_HUMIDITY_ENTITY,
                ),
            ): _sensor_selector("humidity"),
        }
    )


def _remote_area_id(hass, remote_entity):
    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get(remote_entity)
    if entity_entry is None:
        return None
    if entity_entry.area_id:
        return entity_entry.area_id
    if entity_entry.device_id:
        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get(entity_entry.device_id)
        if device_entry is not None:
            return device_entry.area_id
    return None


def _area_name(hass, area_id):
    if not area_id:
        return None
    area_registry = ar.async_get(hass)
    get_area = getattr(area_registry, "async_get_area", None)
    area_entry = get_area(area_id) if get_area else None
    if area_entry is None:
        return None
    return area_entry.name


def _default_ac_name(hass, remote_entity, area_id=None):
    area_name = _area_name(
        hass,
        area_id or _remote_area_id(hass, remote_entity),
    )
    if area_name:
        return f"AC {area_name}"
    return DEFAULT_NAME


def _configured_name_exists(hass, name):
    domain_data = hass.data.get(DOMAIN, {})
    if name in domain_data.get("devices", {}):
        return True
    return any(
        entry.data.get(CONF_NAME) == name
        for entry in hass.config_entries.async_entries(DOMAIN)
    )


class MitsubishiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mitsubishi Aircon."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return MitsubishiOptionsFlow(config_entry)

    def __init__(self):
        """Initialize the config flow."""
        self._device_data = {}

    def _set_flow_title(self):
        """Ensure Home Assistant uses the localized flow title."""
        self.context["title_placeholders"] = {"name": FLOW_TITLE}

    async def async_step_user(self, user_input=None):
        """Handle remote and sensor selection."""
        self._set_flow_title()
        if user_input is not None:
            remote_entity = user_input[REMOTE_ENTITY]
            await self.async_set_unique_id(remote_entity)
            self._abort_if_unique_id_configured()
            self._device_data = {
                REMOTE_ENTITY: remote_entity,
                TEMPERARURE_ENTITY: user_input.get(
                    TEMPERARURE_ENTITY,
                    DEFAULT_TEMPERATURE_ENTITY,
                ),
                HUMIDITY_ENTITY: user_input.get(
                    HUMIDITY_ENTITY,
                    DEFAULT_HUMIDITY_ENTITY,
                ),
            }
            return await self.async_step_details()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(REMOTE_ENTITY): _entity_selector("remote"),
                    vol.Optional(TEMPERARURE_ENTITY): _sensor_selector("temperature"),
                    vol.Optional(HUMIDITY_ENTITY): _sensor_selector("humidity"),
                }
            ),
        )

    async def async_step_details(self, user_input=None):
        """Handle optional display name and area."""
        self._set_flow_title()
        remote_entity = self._device_data[REMOTE_ENTITY]
        default_area_id = _remote_area_id(self.hass, remote_entity)
        default_name = _default_ac_name(
            self.hass,
            remote_entity,
            default_area_id,
        )
        errors = {}

        if user_input is not None:
            area_id = user_input.get(CONF_AREA_ID)
            name = user_input.get(CONF_NAME) or _default_ac_name(
                self.hass,
                remote_entity,
                area_id,
            )
            if _configured_name_exists(self.hass, name):
                errors[CONF_NAME] = "name_exists"
            else:
                data = {
                    **self._device_data,
                    CONF_NAME: name,
                }
                if area_id:
                    data[CONF_AREA_ID] = area_id
                return self.async_create_entry(title=name, data=data)

        schema = {
            vol.Optional(
                CONF_NAME,
                default=(
                    user_input.get(CONF_NAME, default_name)
                    if user_input
                    else default_name
                ),
            ): str,
        }
        if default_area_id:
            area_field = vol.Optional(
                CONF_AREA_ID,
                default=(
                    user_input.get(CONF_AREA_ID, default_area_id)
                    if user_input
                    else default_area_id
                ),
            )
        else:
            if user_input and user_input.get(CONF_AREA_ID):
                area_field = vol.Optional(
                    CONF_AREA_ID,
                    default=user_input[CONF_AREA_ID],
                )
            else:
                area_field = vol.Optional(CONF_AREA_ID)
        schema[area_field] = selector.AreaSelector()

        return self.async_show_form(
            step_id="details",
            data_schema=vol.Schema(schema),
            errors=errors,
        )

    async def async_step_import(self, import_data):
        """Import a YAML-configured AC as a config entry."""
        self._set_flow_title()
        remote_entity = import_data[REMOTE_ENTITY]
        await self.async_set_unique_id(remote_entity)
        self._abort_if_unique_id_configured()

        area_id = import_data.get(CONF_AREA_ID) or _remote_area_id(
            self.hass,
            remote_entity,
        )
        name = import_data.get(CONF_NAME) or _default_ac_name(
            self.hass,
            remote_entity,
            area_id,
        )
        data = {
            REMOTE_ENTITY: remote_entity,
            TEMPERARURE_ENTITY: import_data.get(
                TEMPERARURE_ENTITY,
                DEFAULT_TEMPERATURE_ENTITY,
            ),
            HUMIDITY_ENTITY: import_data.get(
                HUMIDITY_ENTITY,
                DEFAULT_HUMIDITY_ENTITY,
            ),
            CONF_NAME: name,
        }
        if area_id:
            data[CONF_AREA_ID] = area_id

        return self.async_create_entry(title=name, data=data)


class MitsubishiOptionsFlow(config_entries.OptionsFlow):
    """Handle Mitsubishi Aircon options."""

    def __init__(self, config_entry):
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage optional temperature and humidity sensors."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    TEMPERARURE_ENTITY: user_input.get(
                        TEMPERARURE_ENTITY,
                        DEFAULT_TEMPERATURE_ENTITY,
                    ) or DEFAULT_TEMPERATURE_ENTITY,
                    HUMIDITY_ENTITY: user_input.get(
                        HUMIDITY_ENTITY,
                        DEFAULT_HUMIDITY_ENTITY,
                    ) or DEFAULT_HUMIDITY_ENTITY,
                },
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_sensor_options_schema(self._config_entry),
        )
