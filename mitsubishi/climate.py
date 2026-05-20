"""
Adds support for the Mitsubishi AC
"""
from datetime import timedelta
import logging

from homeassistant.components.climate import ClimateEntity

from .const import (
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_DRY,
    CURRENT_HVAC_FAN,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_OFF,
    CURRENT_HVAC_MAINTAINING,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_OFF,
    FAN_HIGHEST,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    DATA_MITSUBISHI,
    DEVICES,
    PAR_HVAC_MODE,
    PAR_TEMPERATURE,
    PAR_FAN_MODE,
    PAR_SWING_MODE,
    PAR_POWERFUL,
    PAR_ECONOMY,
    CLIMATE_PRESET_PARAMETERS,
    TEMP_MIN,
    TEMP_MAX,
    SUPPORT_FLAGS,
    SUPPORTED_HVAC_MODES,
    SUPPORTED_FAN_MODES,
    SUPPORTED_SWING_MODES,
    SUPPORTED_PRESET_MODES,
    normalize_hvac_mode,
    normalize_fan_mode,
    normalize_swing_mode,
    PRESET_NONE,
    ATTR_TEMPERATURE,
    CONF_NAME,
    TEMP_CELSIUS,
)

DEFAULT_TEMPERATURE = 0
DEFAULT_HUMIDITY = None

STATE_SCAN_INTERVAL_SECS = 3

CONF_TO_CURRENT_HVAC = {
    HVAC_MODE_COOL: CURRENT_HVAC_COOL,
    HVAC_MODE_DRY: CURRENT_HVAC_DRY,
    HVAC_MODE_FAN_ONLY: CURRENT_HVAC_FAN,
    HVAC_MODE_HEAT: CURRENT_HVAC_HEAT,
    HVAC_MODE_HEAT_COOL: CURRENT_HVAC_MAINTAINING,
    HVAC_MODE_OFF: CURRENT_HVAC_OFF
}

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=STATE_SCAN_INTERVAL_SECS)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the Mitsubishi Platform."""
    if discovery_info is None:
        return
    name = discovery_info[CONF_NAME]
    device = hass.data[DATA_MITSUBISHI][DEVICES][name]

    add_entities([MitsubishiThermostat(name, device)])


class MitsubishiThermostat(ClimateEntity):
    """Representation of a Mitsubishi Thermostat."""

    def __init__(self, name, device):
        """Initialize the thermostat."""
        self._name = name
        self._api = device.api
        self._attr_translation_key = "aircon"
        self._state_refresh = None
        self._api.register_entity(self)

    @property
    def icon(self):
        """Return the name of the Climate device."""
        return "mdi:air-conditioner"
    
    @property
    def name(self):
        """Return the name of the Climate device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this thermostat."""
        return '_'.join([self._name, 'climate'])

    @property
    def should_poll(self):
        """Polling is required."""
        return True

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        if self._state_refresh is None:
            return None
        return {"state_refresh": self._state_refresh}

    @property
    def device_state_attributes(self):
        """Return extra state attributes for older Home Assistant versions."""
        return self.extra_state_attributes

    def _refresh_state(self):
        write_state = getattr(self, "async_write_ha_state", None)
        if write_state is not None:
            self._api._hass.add_job(write_state)
        update_state = getattr(self, "schedule_update_ha_state", None)
        if update_state is not None:
            try:
                update_state(force_refresh=True)
            except TypeError:
                update_state()

    @property
    def min_temp(self):
        """Return minimum temperature."""
        return TEMP_MIN

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return TEMP_MAX

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        try:
            if self._api._temperature_entity != "":
                current_temp = float(self._api._hass.states.get(self._api._temperature_entity).state)
            else:
                current_temp = DEFAULT_TEMPERATURE
        except:
            current_temp = DEFAULT_TEMPERATURE
            pass
        return current_temp

    @property
    def current_humidity(self):
        """Return the current humidity."""
        try:
            if self._api._humidity_entity:
                current_humid = float(self._api._hass.states.get(self._api._humidity_entity).state)
            else:
                current_humid = DEFAULT_HUMIDITY
        except:
            current_humid = DEFAULT_HUMIDITY
            pass
        return current_humid

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        try:
            self._api.read_data_json()
            target_temp = self._api._config_data[PAR_TEMPERATURE]
        except:
            target_temp = DEFAULT_TEMPERATURE
            pass
        return target_temp

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        try:
            self._api.read_data_json()
            curr_hvac_mode = self._api._config_data[PAR_HVAC_MODE]
        except:
          curr_hvac_mode = HVAC_MODE_OFF
          pass
        return curr_hvac_mode

    @property
    def hvac_modes(self):
        """HVAC modes."""
        return SUPPORTED_HVAC_MODES

    @property
    def fan_mode(self):
        """Return fan operation"""
        try:
            self._api.read_data_json()
            curr_fan_mode = self._api._config_data[PAR_FAN_MODE]
        except:
          curr_fan_mode = FAN_OFF
          pass
        return curr_fan_mode

    @property
    def fan_modes(self):
        """Fan modes."""
        return SUPPORTED_FAN_MODES

    @property
    def swing_mode(self):
        """Return the vertical swing mode."""
        try:
            self._api.read_data_json()
            curr_swing_mode = self._api._config_data[PAR_SWING_MODE]
        except:
            curr_swing_mode = "off"
            pass
        return curr_swing_mode

    @property
    def swing_modes(self):
        """Return available vertical swing modes."""
        return SUPPORTED_SWING_MODES

    @property
    def preset_mode(self):
        """Return the active extra mode shown as a climate preset."""
        try:
            self._api.read_data_json()
            for preset in CLIMATE_PRESET_PARAMETERS:
                if self._api._config_data[preset] == "on":
                    return preset
        except:
            pass
        return PRESET_NONE

    @property
    def preset_modes(self):
        """Return available extra modes."""
        return SUPPORTED_PRESET_MODES

    @property
    def hvac_action(self):
        """Return the current running hvac operation."""
        try:
            self._api.read_data_json()
            curr_hvac_action = CONF_TO_CURRENT_HVAC[self._api._config_data[PAR_HVAC_MODE]]
        except:
            curr_hvac_action = CURRENT_HVAC_OFF
        return curr_hvac_action

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def available(self):
        """Return True if entity is available."""
        return self._api.available
        
    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return 1
        
    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        hvac_mode = normalize_hvac_mode(hvac_mode)
        if hvac_mode in SUPPORTED_HVAC_MODES:
            self._api.set_data_json({PAR_HVAC_MODE: hvac_mode})

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        self.set_hvac_mode(hvac_mode)

    def turn_on(self, **kwargs):
        """Turn on the AC in Cool mode."""
        self._api.set_data_json({PAR_HVAC_MODE: HVAC_MODE_COOL})

    async def async_turn_on(self, **kwargs):
        """Turn on the AC in Cool mode."""
        self.turn_on(**kwargs)

    def turn_off(self, **kwargs):
        """Turn off the AC."""
        self._api.set_data_json({PAR_HVAC_MODE: HVAC_MODE_OFF})

    async def async_turn_off(self, **kwargs):
        """Turn off the AC."""
        self.turn_off(**kwargs)
            
    def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        fan_mode = normalize_fan_mode(fan_mode)
        if fan_mode in SUPPORTED_FAN_MODES:
            self._api.set_data_json({PAR_FAN_MODE: fan_mode})

    def set_swing_mode(self, swing_mode):
        """Set new vertical swing mode."""
        swing_mode = normalize_swing_mode(swing_mode)
        if swing_mode in SUPPORTED_SWING_MODES:
            self._api.set_data_json({PAR_SWING_MODE: swing_mode})

    def set_preset_mode(self, preset_mode):
        """Set one extra mode as the active climate preset."""
        if preset_mode in SUPPORTED_PRESET_MODES:
            preset_data = {
                PAR_POWERFUL: "off",
                PAR_ECONOMY: "off",
            }
            if preset_mode != PRESET_NONE:
                preset_data[preset_mode] = "on"
            self._api.set_data_json(preset_data)
            self._refresh_state()

    async def async_set_preset_mode(self, preset_mode):
        """Set one extra mode as the active climate preset."""
        self.set_preset_mode(preset_mode)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        new_temperature = kwargs.get(ATTR_TEMPERATURE)
        if new_temperature is not None:
            self._api.set_data_json({PAR_TEMPERATURE: new_temperature})

    def update(self):
        """Update all Node data as it is from json."""
        return
