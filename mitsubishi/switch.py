"""Switch entities for Mitsubishi AC options."""
from datetime import timedelta
import logging

from homeassistant.components.switch import SwitchEntity

from .const import (
    CONF_NAME,
    DATA_MITSUBISHI,
    DEVICES,
    DOMAIN,
    HVAC_MODE_COOL,
    HVAC_MODE_OFF,
    OPTION_OFF,
    OPTION_ON,
    PAR_CLEANING,
    PAR_ECONOMY,
    PAR_HVAC_MODE,
    PAR_POWERFUL,
    PAR_PURIFIER,
    PAR_QUIET,
    PAR_SLEEP,
)

STATE_SCAN_INTERVAL_SECS = 3

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=STATE_SCAN_INTERVAL_SECS)

OPTION_SWITCHES = {
    PAR_QUIET: ("Silent", "mdi:volume-low"),
    PAR_SLEEP: ("Night Setback", "mdi:sleep"),
    PAR_PURIFIER: ("Purifier", "mdi:air-purifier"),
    PAR_CLEANING: ("Cleaning", "mdi:spray-bottle"),
    PAR_POWERFUL: ("Powerful", "mdi:flash"),
    PAR_ECONOMY: ("Economy", "mdi:leaf"),
}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Mitsubishi switch platform."""
    if discovery_info is None:
        return
    name = discovery_info[CONF_NAME]
    device = hass.data[DATA_MITSUBISHI][DEVICES][name]

    add_entities(
        [MitsubishiPowerSwitch(name, device)]
        + [
            MitsubishiOptionSwitch(name, device, parameter, icon)
            for parameter, (_, icon) in OPTION_SWITCHES.items()
        ]
    )


class MitsubishiPowerSwitch(SwitchEntity):
    """Main power switch for a Mitsubishi AC."""

    def __init__(self, name, device):
        """Initialize the power switch entity."""
        self._name = name
        self._api = device.api
        self._attr_has_entity_name = True
        self._attr_name = None
        self._attr_translation_key = "power"

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this switch."""
        return "_".join([self._name, "power"])

    @property
    def device_info(self):
        """Return device information for this switch."""
        return {
            "identifiers": {(DOMAIN, self._name)},
            "manufacturer": "Mitsubishi Heavy Industries",
            "model": "RLA502A700B",
            "name": self._name,
        }

    @property
    def icon(self):
        """Return the icon for this switch."""
        return "mdi:power"

    @property
    def available(self):
        """Return True if entity is available."""
        return self._api.available

    @property
    def should_poll(self):
        """Polling is required."""
        return True

    @property
    def is_on(self):
        """Return True when the AC is not off."""
        try:
            self._api.read_data_json()
            return self._api._config_data[PAR_HVAC_MODE] != HVAC_MODE_OFF
        except Exception as ex:
            _LOGGER.error("Failed to read power state: %s", ex)
        return False

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

    def update(self):
        """Update entity state."""
        return


class MitsubishiOptionSwitch(SwitchEntity):
    """Switch for a Mitsubishi AC on/off option."""

    def __init__(self, name, device, parameter, icon):
        """Initialize the switch entity."""
        self._name = name
        self._api = device.api
        self._parameter = parameter
        self._icon = icon
        self._attr_has_entity_name = True
        self._attr_name = None
        self._attr_translation_key = parameter

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this switch."""
        return "_".join([self._name, self._parameter])

    @property
    def device_info(self):
        """Return device information for this switch."""
        return {
            "identifiers": {(DOMAIN, self._name)},
            "manufacturer": "Mitsubishi Heavy Industries",
            "model": "RLA502A700B",
            "name": self._name,
        }

    @property
    def icon(self):
        """Return the icon for this switch."""
        return self._icon

    @property
    def available(self):
        """Return True if entity is available."""
        return self._api.available

    @property
    def should_poll(self):
        """Polling is required."""
        return True

    @property
    def is_on(self):
        """Return True when the option is enabled."""
        try:
            self._api.read_data_json()
            return self._api._config_data[self._parameter] == OPTION_ON
        except Exception as ex:
            _LOGGER.error("Failed to read %s option: %s", self._parameter, ex)
        return False

    def turn_on(self, **kwargs):
        """Enable the option."""
        self._api.set_data_json({self._parameter: OPTION_ON})

    def turn_off(self, **kwargs):
        """Disable the option."""
        self._api.set_data_json({self._parameter: OPTION_OFF})

    def update(self):
        """Update entity state."""
        return
