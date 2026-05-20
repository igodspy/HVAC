"""Suppoort for Mitsubishi."""
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
    CONF_NAME,
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import discovery

from .ir_generator import generate_broadlink_base64
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
    PAR_CLEANING,
    PAR_POWERFUL,
    PAR_ECONOMY,
    OPTION_PARAMETERS,
    OPTION_OFF,
    OPTION_ON,
    STANDALONE_OPTION_PARAMETERS,
    HVAC_MODE_OFF,
    REMOTE_ENTITY,
    FAN_AUTO,
    HUMIDITY_ENTITY,
    TEMPERARURE_ENTITY,
    SUPPORTED_HVAC_MODES,
    SUPPORTED_FAN_MODES,
    SUPPORTED_SWING_MODES,
    SUPPORTED_HSWING_MODES,
    SUPPORTED_OPTION_VALUES,
    TEMP_MIN,
    TEMP_MAX,
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


def _normalize_option_data(config_data, changed_data=None):
    """Apply option compatibility rules in place."""
    changed_data = changed_data or {}
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
        for parameter in [PAR_QUIET, PAR_POWERFUL, PAR_ECONOMY]
        if changed_data.get(parameter) == OPTION_ON
    ]
    if enabled_regular_options:
        for parameter in STANDALONE_OPTION_PARAMETERS:
            config_data[parameter] = OPTION_OFF

    if changed_data.get(PAR_POWERFUL) == OPTION_ON:
        config_data[PAR_ECONOMY] = OPTION_OFF
        config_data[PAR_QUIET] = OPTION_OFF
    if changed_data.get(PAR_ECONOMY) == OPTION_ON or changed_data.get(PAR_QUIET) == OPTION_ON:
        config_data[PAR_POWERFUL] = OPTION_OFF

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
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(PAR_SWING_MODE): vol.In(SUPPORTED_SWING_MODES),
        vol.Optional(PAR_HSWING_MODE): vol.In(SUPPORTED_HSWING_MODES),
        vol.Optional(PAR_QUIET): vol.In(SUPPORTED_OPTION_VALUES),
        vol.Optional(PAR_SLEEP): vol.In(SUPPORTED_OPTION_VALUES),
        vol.Optional(PAR_PURIFIER): vol.In(SUPPORTED_OPTION_VALUES),
        vol.Optional(PAR_CLEANING): vol.In(SUPPORTED_OPTION_VALUES),
        vol.Optional(PAR_POWERFUL): vol.In(SUPPORTED_OPTION_VALUES),
        vol.Optional(PAR_ECONOMY): vol.In(SUPPORTED_OPTION_VALUES),
    }
)

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
                if read_data[PAR_HVAC_MODE] in SUPPORTED_HVAC_MODES:
                    self._config_data[PAR_HVAC_MODE] = copy.deepcopy(read_data[PAR_HVAC_MODE])
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
                if read_data[PAR_FAN_MODE] in SUPPORTED_FAN_MODES:
                    self._config_data[PAR_FAN_MODE] = copy.deepcopy(read_data[PAR_FAN_MODE])
                else:
                    self._config_data[PAR_FAN_MODE] = DEFAULT_FAN_MODE
                    must_reset = True
            else:
                self._config_data[PAR_FAN_MODE] = DEFAULT_FAN_MODE
                must_reset = True

            if PAR_SWING_MODE in read_data and read_data[PAR_SWING_MODE] in SUPPORTED_SWING_MODES:
                self._config_data[PAR_SWING_MODE] = copy.deepcopy(read_data[PAR_SWING_MODE])
            else:
                self._config_data[PAR_SWING_MODE] = DEFAULT_SWING_MODE
                must_reset = True

            if PAR_HSWING_MODE in read_data and read_data[PAR_HSWING_MODE] in SUPPORTED_HSWING_MODES:
                self._config_data[PAR_HSWING_MODE] = copy.deepcopy(read_data[PAR_HSWING_MODE])
            else:
                self._config_data[PAR_HSWING_MODE] = DEFAULT_HSWING_MODE
                must_reset = True

            for parameter in [
                PAR_QUIET,
                PAR_SLEEP,
                PAR_PURIFIER,
                PAR_CLEANING,
                PAR_POWERFUL,
                PAR_ECONOMY,
            ]:
                if parameter in read_data and read_data[parameter] in SUPPORTED_OPTION_VALUES:
                    self._config_data[parameter] = copy.deepcopy(read_data[parameter])
                else:
                    self._config_data[parameter] = OPTION_OFF
                    must_reset = True

            original_config_data = copy.deepcopy(self._config_data)
            _normalize_option_data(self._config_data)
            if self._config_data != original_config_data:
                must_reset = True

        except:
            self._config_data[PAR_HVAC_MODE] = DEFAULT_HVAC_MODE
            self._config_data[PAR_TEMPERATURE] = DEFAULT_TEMP
            self._config_data[PAR_FAN_MODE] = DEFAULT_FAN_MODE
            self._config_data[PAR_SWING_MODE] = DEFAULT_SWING_MODE
            self._config_data[PAR_HSWING_MODE] = DEFAULT_HSWING_MODE
            for parameter in OPTION_PARAMETERS:
                if parameter not in [PAR_SWING_MODE, PAR_HSWING_MODE]:
                    self._config_data[parameter] = OPTION_OFF
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

    def set_data_json(self, parameter_list=None):
        """Set Mitsubishi data in json file"""
        if parameter_list is None:
            parameter_list = {}
        ir_code = None
        should_send = False
        with self._lock:
            self._read_data_json()
            if PAR_HVAC_MODE in parameter_list:
                self._config_data[PAR_HVAC_MODE] = copy.deepcopy(parameter_list[PAR_HVAC_MODE])
            if PAR_FAN_MODE in parameter_list:
                self._config_data[PAR_FAN_MODE] = copy.deepcopy(parameter_list[PAR_FAN_MODE])
            if PAR_TEMPERATURE in parameter_list:
                self._config_data[PAR_TEMPERATURE] = copy.deepcopy(parameter_list[PAR_TEMPERATURE])
            for parameter in OPTION_PARAMETERS:
                if parameter in parameter_list:
                    self._config_data[parameter] = copy.deepcopy(parameter_list[parameter])

            _normalize_option_data(self._config_data, parameter_list)

            try:
                ir_code = generate_broadlink_base64(self._config_data)
                if (PAR_HVAC_MODE in parameter_list and self._config_data[PAR_HVAC_MODE] == HVAC_MODE_OFF) or self._config_data[PAR_HVAC_MODE] != HVAC_MODE_OFF:
                    should_send = True
                # store data
                self._set_data_json()
                _LOGGER.info("AC generated code {}".format(ir_code))
            except Exception as ex:
                _LOGGER.error(f"Unknown IR code with exception: {ex}")

        if should_send:
            try:
                self._send_ir_code(ir_code)
            except Exception as ex:
                _LOGGER.error("Failed to schedule IR command: %s", ex)

def setup(hass, config):
    """Set up the Mitsubishi component."""
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
        name = call.data[CONF_NAME]
        device = hass.data[DATA_MITSUBISHI][DEVICES].get(name)
        if device is None:
            _LOGGER.error("Unknown Mitsubishi device %s", name)
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
        schema=SET_OPTIONS_SCHEMA,
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
