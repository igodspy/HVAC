"""Suppoort for Mitsubishi."""
from datetime import datetime, timedelta
import logging
import threading
import voluptuous as vol
import copy
import json
import os

from homeassistant.components.climate import DOMAIN as CLIMATE
from homeassistant.components.select import DOMAIN as SELECT
from homeassistant.components.switch import DOMAIN as SWITCH
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_NAME,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery

from .entity_config import sync_icons_config, sync_strings_config
from .ir_generator import generate_broadlink_base64, generate_install_position_base64
from .const import (
    CLIMATES,
    DATA_MITSUBISHI,
    DEVICES,
    DOMAIN,
    PAR_HVAC_MODE,
    PAR_TEMPERATURE,
    PAR_FAN_MODE,
    PAR_SWING_MODE,
    PAR_HSWING_MODE,
    PAR_QUIET,
    PAR_SLEEP,
    PAR_PURIFIER,
    PAR_PURIFIER_ENDS_AT,
    PAR_CLEANING,
    PAR_CLEANING_ENDS_AT,
    PAR_POWERFUL,
    PAR_POWERFUL_ENDS_AT,
    PAR_ECONOMY,
    PAR_3D_AUTO,
    PAR_INSTALL_POSITION,
    OPTION_PARAMETERS,
    OPTION_OFF,
    OPTION_ON,
    STANDALONE_OPTION_PARAMETERS,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    REMOTE_ENTITY,
    FAN_AUTO,
    HUMIDITY_ENTITY,
    TEMPERARURE_ENTITY,
    SUPPORTED_HVAC_MODES,
    SUPPORTED_FAN_MODES,
    SUPPORTED_SWING_MODES,
    SUPPORTED_HSWING_MODES,
    SUPPORTED_INSTALL_POSITIONS,
    SUPPORTED_OPTION_VALUES,
    TEMP_MIN,
    TEMP_MAX,
    SWING_MODE_ALIASES,
    normalize_hvac_mode,
    normalize_fan_mode,
    normalize_swing_mode,
)

_LOGGER = logging.getLogger(__name__)

def _has_unique_names(devices):
    names = [device[CONF_NAME] for device in devices]
    vol.Schema(vol.Unique())(names)
    return devices

DEFAULT_NAME = "Mitsubishi"
DEFAULT_HUMIDITY_ENTITY = ""
DEFAULT_TEMPERATURE_ENTITY = ""

DEFAULT_TEMP = 24.0
DEFAULT_HVAC_MODE = HVAC_MODE_OFF
DEFAULT_FAN_MODE = FAN_AUTO
DEFAULT_SWING_MODE = "off"
DEFAULT_HSWING_MODE = "auto"
DEFAULT_INSTALL_POSITION = "center"
HVAC_MODES_WITHOUT_3D_AUTO = [HVAC_MODE_DRY, HVAC_MODE_FAN_ONLY]
CLEANING_DURATION = timedelta(hours=2)
PURIFIER_DURATION = timedelta(minutes=90)
POWERFUL_DURATION = timedelta(minutes=15)


def _parse_json_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _serialize_json_datetime(value):
    return value.replace(microsecond=0).isoformat()


def _sync_timed_option(
    config_data,
    option_parameter,
    end_parameter,
    duration,
    turn_off_hvac_on_expire=True,
):
    ends_at = _parse_json_datetime(config_data.get(end_parameter))
    if config_data.get(option_parameter) == OPTION_ON:
        if ends_at is None:
            config_data[end_parameter] = _serialize_json_datetime(
                datetime.now() + duration
            )
            return True
        if datetime.now() >= ends_at:
            config_data[option_parameter] = OPTION_OFF
            if turn_off_hvac_on_expire:
                config_data[PAR_HVAC_MODE] = HVAC_MODE_OFF
            config_data.pop(end_parameter, None)
            return True
    elif config_data.pop(end_parameter, None) is not None:
        return True
    return False


def _normalize_option_data(config_data, changed_data=None, previous_data=None):
    """Apply option compatibility rules in place."""
    changed_data = changed_data or {}
    previous_data = previous_data or {}
    enabled_standalone_options = [
        parameter
        for parameter in STANDALONE_OPTION_PARAMETERS
        if changed_data.get(parameter) == OPTION_ON
    ]
    if enabled_standalone_options:
        active_standalone_option = enabled_standalone_options[-1]
        for parameter in OPTION_PARAMETERS:
            if parameter not in [PAR_SWING_MODE, PAR_HSWING_MODE]:
                config_data[parameter] = OPTION_OFF
        config_data[active_standalone_option] = OPTION_ON

    enabled_regular_options = [
        parameter
        for parameter in [PAR_QUIET, PAR_POWERFUL, PAR_ECONOMY, PAR_3D_AUTO]
        if changed_data.get(parameter) == OPTION_ON
    ]
    if enabled_regular_options:
        for parameter in STANDALONE_OPTION_PARAMETERS:
            config_data[parameter] = OPTION_OFF

    if changed_data.get(PAR_POWERFUL) == OPTION_ON:
        config_data[PAR_ECONOMY] = OPTION_OFF
        config_data[PAR_QUIET] = OPTION_OFF
        config_data[PAR_3D_AUTO] = OPTION_OFF
    if changed_data.get(PAR_ECONOMY) == OPTION_ON or changed_data.get(PAR_QUIET) == OPTION_ON:
        config_data[PAR_POWERFUL] = OPTION_OFF
    if changed_data.get(PAR_ECONOMY) == OPTION_ON:
        config_data[PAR_3D_AUTO] = OPTION_OFF
    if changed_data.get(PAR_SLEEP) == OPTION_ON:
        config_data[PAR_ECONOMY] = OPTION_OFF
    if changed_data.get(PAR_SLEEP) == OPTION_ON or changed_data.get(PAR_3D_AUTO) == OPTION_ON:
        config_data[PAR_POWERFUL] = OPTION_OFF
    if changed_data.get(PAR_3D_AUTO) == OPTION_ON:
        config_data[PAR_ECONOMY] = OPTION_OFF
    if config_data.get(PAR_HVAC_MODE) == HVAC_MODE_FAN_ONLY:
        config_data[PAR_ECONOMY] = OPTION_OFF
    if config_data.get(PAR_HVAC_MODE) in [HVAC_MODE_DRY, HVAC_MODE_FAN_ONLY]:
        config_data[PAR_QUIET] = OPTION_OFF
    if (
        config_data.get(PAR_HVAC_MODE) in [HVAC_MODE_HEAT, HVAC_MODE_FAN_ONLY]
        or config_data.get(PAR_SLEEP) == OPTION_ON
        or config_data.get(PAR_PURIFIER) == OPTION_ON
    ):
        config_data[PAR_CLEANING] = OPTION_OFF
    if config_data.get(PAR_HVAC_MODE) in [HVAC_MODE_DRY, HVAC_MODE_FAN_ONLY]:
        config_data[PAR_POWERFUL] = OPTION_OFF
    if config_data.get(PAR_HVAC_MODE) in HVAC_MODES_WITHOUT_3D_AUTO:
        config_data[PAR_3D_AUTO] = OPTION_OFF
    if (
        config_data.get(PAR_3D_AUTO) == OPTION_ON
        and (
            config_data.get(PAR_POWERFUL) == OPTION_ON
            or config_data.get(PAR_ECONOMY) == OPTION_ON
        )
    ):
        config_data[PAR_3D_AUTO] = OPTION_OFF

    standalone_enabled = any(config_data.get(parameter) == OPTION_ON for parameter in STANDALONE_OPTION_PARAMETERS)
    if standalone_enabled:
        active_standalone_option = next(
            parameter
            for parameter in STANDALONE_OPTION_PARAMETERS
            if config_data.get(parameter) == OPTION_ON
        )
        for parameter in OPTION_PARAMETERS:
            if parameter not in [PAR_SWING_MODE, PAR_HSWING_MODE]:
                config_data[parameter] = OPTION_OFF
        config_data[active_standalone_option] = OPTION_ON

    if config_data.get(PAR_POWERFUL) == OPTION_ON:
        config_data[PAR_ECONOMY] = OPTION_OFF
        config_data[PAR_QUIET] = OPTION_OFF

MITSUBISHI_SCHEMA = vol.Schema(
    {
        vol.Required(REMOTE_ENTITY): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(TEMPERARURE_ENTITY, default=DEFAULT_TEMPERATURE_ENTITY): cv.entity_id,
        vol.Optional(HUMIDITY_ENTITY): cv.entity_id,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.All(cv.ensure_list, [MITSUBISHI_SCHEMA], _has_unique_names)},
    extra=vol.ALLOW_EXTRA,
)

SET_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(PAR_SWING_MODE): vol.In(
            SUPPORTED_SWING_MODES + list(SWING_MODE_ALIASES)
        ),
        vol.Optional(PAR_HSWING_MODE): vol.In(SUPPORTED_HSWING_MODES),
        vol.Optional(PAR_QUIET): vol.In(SUPPORTED_OPTION_VALUES),
        vol.Optional(PAR_SLEEP): vol.In(SUPPORTED_OPTION_VALUES),
        vol.Optional(PAR_PURIFIER): vol.In(SUPPORTED_OPTION_VALUES),
        vol.Optional(PAR_CLEANING): vol.In(SUPPORTED_OPTION_VALUES),
        vol.Optional(PAR_POWERFUL): vol.In(SUPPORTED_OPTION_VALUES),
        vol.Optional(PAR_ECONOMY): vol.In(SUPPORTED_OPTION_VALUES),
        vol.Optional(PAR_3D_AUTO): vol.In(SUPPORTED_OPTION_VALUES),
    }
)

SET_INSTALL_POSITION_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
        vol.Optional(CONF_NAME): cv.string,
        vol.Required(PAR_INSTALL_POSITION): vol.In(SUPPORTED_INSTALL_POSITIONS),
    }
)


def _service_schema(schema):
    def validate(value):
        value = schema(value)
        if ATTR_ENTITY_ID not in value and CONF_NAME not in value:
            raise vol.Invalid("entity_id or name is required")
        return value

    return validate


def _get_service_device(hass, service_data):
    devices = hass.data[DATA_MITSUBISHI][DEVICES]
    if CONF_NAME in service_data:
        device = devices.get(service_data[CONF_NAME])
        if device is not None:
            return device

    entity_ids = service_data.get(ATTR_ENTITY_ID)
    if isinstance(entity_ids, str):
        entity_ids = [entity_ids]
    if entity_ids:
        for device in devices.values():
            if device.api.has_entity_id(entity_ids):
                return device
    return None


class MitsubishiHandler():
    """Mitsubishi handler"""

    def __init__(self, hass, device, name, remote_entity, temperature, humidity):
        """Initialize."""
        self._config_data = {}
        self._device = device
        self._hass = hass
        self._lock = threading.Lock()
        self._name = name
        self._file_name = '/config/custom_components/mitsubishi/json/' + name + '.json'
        self._remote_entity = remote_entity
        self._temperature_entity = temperature
        self._humidity_entity = humidity
        self._entities = []

    @property
    def available(self):
        """Return if Mitsubishi is available."""
        return True


    def _read_data_json(self):
        try:
            # read data
            must_reset = False

            with open(self._file_name) as json_file:
                read_data = json.load(json_file)

            if PAR_HVAC_MODE in read_data:
                hvac_mode = normalize_hvac_mode(read_data[PAR_HVAC_MODE])
                if hvac_mode in SUPPORTED_HVAC_MODES:
                    self._config_data[PAR_HVAC_MODE] = copy.deepcopy(hvac_mode)
                else:
                    self._config_data[PAR_HVAC_MODE] = DEFAULT_HVAC_MODE
                    must_reset = True
            else:
                self._config_data[PAR_HVAC_MODE] = DEFAULT_HVAC_MODE
                must_reset = True

            if PAR_TEMPERATURE in read_data:
                if read_data[PAR_TEMPERATURE] >= TEMP_MIN and read_data[PAR_TEMPERATURE] <= TEMP_MAX:
                    self._config_data[PAR_TEMPERATURE] = round(read_data[PAR_TEMPERATURE])
                else:
                    self._config_data[PAR_TEMPERATURE] = DEFAULT_TEMP
                    must_reset = True
            else:
                self._config_data[PAR_TEMPERATURE] = DEFAULT_TEMP
                must_reset = True

            if PAR_FAN_MODE in read_data:
                fan_mode = normalize_fan_mode(read_data[PAR_FAN_MODE])
                if fan_mode in SUPPORTED_FAN_MODES:
                    self._config_data[PAR_FAN_MODE] = copy.deepcopy(fan_mode)
                else:
                    self._config_data[PAR_FAN_MODE] = DEFAULT_FAN_MODE
                    must_reset = True
            else:
                self._config_data[PAR_FAN_MODE] = DEFAULT_FAN_MODE
                must_reset = True

            if PAR_SWING_MODE in read_data:
                swing_mode = normalize_swing_mode(read_data[PAR_SWING_MODE])
                if swing_mode in SUPPORTED_SWING_MODES:
                    self._config_data[PAR_SWING_MODE] = copy.deepcopy(swing_mode)
                else:
                    self._config_data[PAR_SWING_MODE] = DEFAULT_SWING_MODE
                    must_reset = True
            else:
                self._config_data[PAR_SWING_MODE] = DEFAULT_SWING_MODE
                must_reset = True

            if PAR_HSWING_MODE in read_data and read_data[PAR_HSWING_MODE] in SUPPORTED_HSWING_MODES:
                self._config_data[PAR_HSWING_MODE] = copy.deepcopy(read_data[PAR_HSWING_MODE])
            else:
                self._config_data[PAR_HSWING_MODE] = DEFAULT_HSWING_MODE
                must_reset = True

            if (
                PAR_INSTALL_POSITION in read_data
                and read_data[PAR_INSTALL_POSITION] in SUPPORTED_INSTALL_POSITIONS
            ):
                self._config_data[PAR_INSTALL_POSITION] = copy.deepcopy(
                    read_data[PAR_INSTALL_POSITION]
                )
            else:
                self._config_data[PAR_INSTALL_POSITION] = DEFAULT_INSTALL_POSITION
                must_reset = True

            for parameter in [
                PAR_QUIET,
                PAR_SLEEP,
                PAR_PURIFIER,
                PAR_CLEANING,
                PAR_POWERFUL,
                PAR_ECONOMY,
                PAR_3D_AUTO,
            ]:
                if parameter in read_data and read_data[parameter] in SUPPORTED_OPTION_VALUES:
                    self._config_data[parameter] = copy.deepcopy(read_data[parameter])
                else:
                    self._config_data[parameter] = OPTION_OFF
                    must_reset = True

            for parameter in [
                PAR_PURIFIER_ENDS_AT,
                PAR_CLEANING_ENDS_AT,
                PAR_POWERFUL_ENDS_AT,
            ]:
                if parameter in read_data:
                    self._config_data[parameter] = copy.deepcopy(read_data[parameter])
                else:
                    self._config_data.pop(parameter, None)

            original_config_data = copy.deepcopy(self._config_data)
            _normalize_option_data(self._config_data)
            if self._config_data != original_config_data:
                must_reset = True

            must_reset = (
                _sync_timed_option(
                    self._config_data,
                    PAR_PURIFIER,
                    PAR_PURIFIER_ENDS_AT,
                    PURIFIER_DURATION,
                )
                or must_reset
            )
            must_reset = (
                _sync_timed_option(
                    self._config_data,
                    PAR_CLEANING,
                    PAR_CLEANING_ENDS_AT,
                    CLEANING_DURATION,
                )
                or must_reset
            )
            must_reset = (
                _sync_timed_option(
                    self._config_data,
                    PAR_POWERFUL,
                    PAR_POWERFUL_ENDS_AT,
                    POWERFUL_DURATION,
                    turn_off_hvac_on_expire=False,
                )
                or must_reset
            )

        except:
            self._config_data[PAR_HVAC_MODE] = DEFAULT_HVAC_MODE
            self._config_data[PAR_TEMPERATURE] = DEFAULT_TEMP
            self._config_data[PAR_FAN_MODE] = DEFAULT_FAN_MODE
            self._config_data[PAR_SWING_MODE] = DEFAULT_SWING_MODE
            self._config_data[PAR_HSWING_MODE] = DEFAULT_HSWING_MODE
            self._config_data[PAR_INSTALL_POSITION] = DEFAULT_INSTALL_POSITION
            for parameter in OPTION_PARAMETERS:
                if parameter not in [PAR_SWING_MODE, PAR_HSWING_MODE]:
                    self._config_data[parameter] = OPTION_OFF
            self._config_data.pop(PAR_PURIFIER_ENDS_AT, None)
            self._config_data.pop(PAR_CLEANING_ENDS_AT, None)
            self._config_data.pop(PAR_POWERFUL_ENDS_AT, None)
            must_reset = True
            pass
        return must_reset

    def read_data_json(self):
        """Get Mitsubishi data from json file"""
        with self._lock:
            if self._read_data_json():
                self._set_data_json()

    def _set_data_json(self):
        """Set Mitsubishi data in json file"""
        os.makedirs(os.path.dirname(self._file_name), exist_ok=True)
        temp_file_name = self._file_name + ".tmp"
        with open(temp_file_name, 'w') as json_file:
            json.dump(self._config_data, json_file)
        os.replace(temp_file_name, self._file_name)

    def _send_ir_code(self, ir_code):
        """Schedule a Broadlink command without blocking state updates."""
        service_data = {
            'entity_id': self._remote_entity,
            'command': 'b64:' + ir_code,
        }
        service_call = getattr(self._hass.services, "async_call", None)
        if service_call is None:
            service_call = self._hass.services.call
        self._hass.add_job(
            service_call,
            'remote',
            'send_command',
            service_data,
            False,
        )

    def register_entity(self, entity):
        """Track entities for immediate state refreshes."""
        self._entities.append(entity)

    def register_option_entity(self, entity):
        """Track option entities for immediate state refreshes."""
        self.register_entity(entity)

    def refresh_entities(self):
        """Request Home Assistant state updates for all related entities."""
        for entity in self._entities:
            if hasattr(entity, "_state_refresh"):
                entity._state_refresh = _serialize_json_datetime(datetime.now())
            refresh_state = getattr(entity, "_refresh_state", None)
            if refresh_state is not None:
                refresh_state()
                continue
            write_state = getattr(entity, "async_write_ha_state", None)
            if write_state is not None:
                self._hass.add_job(write_state)
            update_state = getattr(entity, "schedule_update_ha_state", None)
            if update_state is not None:
                try:
                    update_state(force_refresh=True)
                except TypeError:
                    update_state()

    def has_entity_id(self, entity_ids):
        """Return True when one of this device's entities matches an entity ID."""
        entity_ids = set(entity_ids)
        return any(
            getattr(entity, "entity_id", None) in entity_ids
            for entity in self._entities
        )

    def set_data_json(self, parameter_list=None, send_ir=True):
        """Set Mitsubishi data in json file"""
        if parameter_list is None:
            parameter_list = {}
        ir_code = None
        should_send = False
        with self._lock:
            self._read_data_json()
            previous_config_data = copy.deepcopy(self._config_data)
            if PAR_HVAC_MODE in parameter_list:
                hvac_mode = normalize_hvac_mode(parameter_list[PAR_HVAC_MODE])
                if hvac_mode in SUPPORTED_HVAC_MODES:
                    if (
                        self._config_data[PAR_HVAC_MODE] == HVAC_MODE_OFF
                        and hvac_mode == HVAC_MODE_HEAT_COOL
                    ):
                        hvac_mode = HVAC_MODE_COOL
                    self._config_data[PAR_HVAC_MODE] = copy.deepcopy(hvac_mode)
                    self._config_data[PAR_PURIFIER] = OPTION_OFF
                    self._config_data.pop(PAR_PURIFIER_ENDS_AT, None)
                    self._config_data[PAR_CLEANING] = OPTION_OFF
                    self._config_data.pop(PAR_CLEANING_ENDS_AT, None)
                    self._config_data[PAR_POWERFUL] = OPTION_OFF
                    self._config_data.pop(PAR_POWERFUL_ENDS_AT, None)
            if PAR_FAN_MODE in parameter_list:
                fan_mode = normalize_fan_mode(parameter_list[PAR_FAN_MODE])
                if fan_mode in SUPPORTED_FAN_MODES:
                    self._config_data[PAR_FAN_MODE] = copy.deepcopy(fan_mode)
            if PAR_TEMPERATURE in parameter_list:
                self._config_data[PAR_TEMPERATURE] = copy.deepcopy(parameter_list[PAR_TEMPERATURE])
            for parameter in OPTION_PARAMETERS:
                if parameter in parameter_list:
                    if parameter == PAR_SWING_MODE:
                        self._config_data[parameter] = copy.deepcopy(
                            normalize_swing_mode(parameter_list[parameter])
                        )
                    else:
                        self._config_data[parameter] = copy.deepcopy(parameter_list[parameter])

            _normalize_option_data(
                self._config_data,
                parameter_list,
                previous_config_data,
            )
            unsupported_option_request = (
                PAR_HVAC_MODE not in parameter_list
                and (
                    (
                        parameter_list.get(PAR_ECONOMY) == OPTION_ON
                        and self._config_data.get(PAR_HVAC_MODE)
                        == HVAC_MODE_FAN_ONLY
                    )
                    or (
                        parameter_list.get(PAR_POWERFUL) == OPTION_ON
                        and self._config_data.get(PAR_HVAC_MODE)
                        in [HVAC_MODE_DRY, HVAC_MODE_FAN_ONLY]
                    )
                )
            )
            if unsupported_option_request:
                if parameter_list.get(PAR_ECONOMY) == OPTION_ON:
                    self._config_data[PAR_ECONOMY] = OPTION_OFF
                if parameter_list.get(PAR_POWERFUL) == OPTION_ON:
                    self._config_data[PAR_POWERFUL] = OPTION_OFF
                    self._config_data.pop(PAR_POWERFUL_ENDS_AT, None)
                send_ir = False

            if parameter_list.get(PAR_POWERFUL) == OPTION_ON:
                if self._config_data.get(PAR_POWERFUL) == OPTION_ON:
                    self._config_data[PAR_POWERFUL_ENDS_AT] = _serialize_json_datetime(
                        datetime.now() + POWERFUL_DURATION
                    )
                else:
                    self._config_data.pop(PAR_POWERFUL_ENDS_AT, None)
            elif self._config_data.get(PAR_POWERFUL) != OPTION_ON:
                self._config_data.pop(PAR_POWERFUL_ENDS_AT, None)
            if parameter_list.get(PAR_PURIFIER) == OPTION_ON:
                self._config_data[PAR_PURIFIER_ENDS_AT] = _serialize_json_datetime(
                    datetime.now() + PURIFIER_DURATION
                )
            elif self._config_data.get(PAR_PURIFIER) != OPTION_ON:
                self._config_data.pop(PAR_PURIFIER_ENDS_AT, None)
            if parameter_list.get(PAR_CLEANING) == OPTION_ON:
                if self._config_data.get(PAR_CLEANING) == OPTION_ON:
                    self._config_data[PAR_CLEANING_ENDS_AT] = _serialize_json_datetime(
                        datetime.now() + CLEANING_DURATION
                    )
                else:
                    self._config_data.pop(PAR_CLEANING_ENDS_AT, None)
            elif self._config_data.get(PAR_CLEANING) != OPTION_ON:
                self._config_data.pop(PAR_CLEANING_ENDS_AT, None)
            if PAR_HVAC_MODE in parameter_list:
                self._config_data[PAR_PURIFIER] = OPTION_OFF
                self._config_data.pop(PAR_PURIFIER_ENDS_AT, None)
                self._config_data[PAR_CLEANING] = OPTION_OFF
                self._config_data.pop(PAR_CLEANING_ENDS_AT, None)
                self._config_data[PAR_POWERFUL] = OPTION_OFF
                self._config_data.pop(PAR_POWERFUL_ENDS_AT, None)

            try:
                ir_code = generate_broadlink_base64(self._config_data)
                if send_ir and (
                    (
                        PAR_HVAC_MODE in parameter_list
                        and self._config_data[PAR_HVAC_MODE] == HVAC_MODE_OFF
                    )
                    or self._config_data[PAR_HVAC_MODE] != HVAC_MODE_OFF
                ):
                    should_send = True
                # store data
                self._set_data_json()
                _LOGGER.info("AC generated code {}".format(ir_code))
            except Exception as ex:
                _LOGGER.error(f"Unknown IR code with exception: {ex}")

        self.refresh_entities()

        if should_send:
            try:
                self._send_ir_code(ir_code)
            except Exception as ex:
                _LOGGER.error("Failed to schedule IR command: %s", ex)

    def set_install_position(self, position):
        """Send and store the indoor unit install position setup command."""
        if position not in SUPPORTED_INSTALL_POSITIONS:
            return
        ir_code = None
        with self._lock:
            self._read_data_json()
            self._config_data[PAR_INSTALL_POSITION] = copy.deepcopy(position)
            try:
                ir_code = generate_install_position_base64(position)
                self._set_data_json()
                _LOGGER.info("AC generated install position code %s", ir_code)
            except Exception as ex:
                _LOGGER.error(
                    "Unknown install position IR code with exception: %s",
                    ex,
                )

        self.refresh_entities()

        if ir_code is not None:
            try:
                self._send_ir_code(ir_code)
            except Exception as ex:
                _LOGGER.error("Failed to schedule install position IR command: %s", ex)

def setup(hass, config):
    """Set up the Mitsubishi component."""
    sync_icons_config()
    sync_strings_config()
    hass.data.setdefault(DATA_MITSUBISHI, {DEVICES: {}, CLIMATES: []})
    for device in config[DOMAIN]:
        name = device[CONF_NAME]
        temperature = device[TEMPERARURE_ENTITY]
        humidity = device.get(HUMIDITY_ENTITY, DEFAULT_HUMIDITY_ENTITY)
        remote_entity = device[REMOTE_ENTITY]
        try:
            api = MitsubishiHandler(hass, device=device, name=name, remote_entity=remote_entity, temperature=temperature, humidity=humidity)
            api.read_data_json()
        except:
            _LOGGER.error("unknown error", name)
            pass
        hass.data[DATA_MITSUBISHI][DEVICES][name] = MitsubishiDevice(api)
        discovery.load_platform(
            hass, CLIMATE,
            DOMAIN,
            {CONF_NAME: name},
            config)
        discovery.load_platform(
            hass, SELECT,
            DOMAIN,
            {CONF_NAME: name},
            config)
        discovery.load_platform(
            hass, SWITCH,
            DOMAIN,
            {CONF_NAME: name},
            config)

    def set_options(call):
        device = _get_service_device(hass, call.data)
        if device is None:
            _LOGGER.error("Unknown Mitsubishi device for service data %s", call.data)
            return
        device.api.set_data_json(
            {
                parameter: value
                for parameter, value in call.data.items()
                if parameter in OPTION_PARAMETERS
            }
        )

    hass.services.register(
        DOMAIN,
        "set_options",
        set_options,
        schema=_service_schema(SET_OPTIONS_SCHEMA),
    )

    def set_install_position(call):
        device = _get_service_device(hass, call.data)
        if device is None:
            _LOGGER.error("Unknown Mitsubishi device for service data %s", call.data)
            return
        device.api.set_install_position(call.data[PAR_INSTALL_POSITION])

    hass.services.register(
        DOMAIN,
        "set_install_position",
        set_install_position,
        schema=_service_schema(SET_INSTALL_POSITION_SCHEMA),
    )

    if not hass.data[DATA_MITSUBISHI][DEVICES]:
        return False

    # Return boolean to indicate that initialization was successful.
    return True


class MitsubishiDevice:
    """Representation of a base Mitsubishi discovery device."""

    def __init__(
            self,
            api,
    ):
        """Initialize the entity."""
        self.api = api
