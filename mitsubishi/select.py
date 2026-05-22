"""Select entities for Mitsubishi AC options."""
from datetime import timedelta
import logging

from homeassistant.components.select import SelectEntity

from .entity_config import get_entity_icon
from .const import (
    CONF_NAME,
    DATA_MITSUBISHI,
    DEVICES,
    DOMAIN,
    PAR_HSWING_MODE,
    PAR_INSTALL_POSITION,
    PAR_SWING_MODE,
    SUPPORTED_HSWING_MODES,
    SUPPORTED_INSTALL_POSITIONS,
    SUPPORTED_SWING_MODES,
    normalize_swing_mode,
)

STATE_SCAN_INTERVAL_SECS = 3

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=STATE_SCAN_INTERVAL_SECS)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Mitsubishi select platform."""
    if discovery_info is None:
        return
    name = discovery_info[CONF_NAME]
    device = hass.data[DATA_MITSUBISHI][DEVICES][name]

    add_entities(
        [
            MitsubishiVerticalSwingSelect(name, device),
            MitsubishiHorizontalSwingSelect(name, device),
            MitsubishiInstallPositionSelect(name, device),
        ]
    )


class MitsubishiVerticalSwingSelect(SelectEntity):
    """Vertical swing control for a Mitsubishi AC."""

    def __init__(self, name, device):
        """Initialize the select entity."""
        self._name = name
        self._api = device.api
        self._attr_has_entity_name = True
        self._attr_name = None
        self._attr_translation_key = PAR_SWING_MODE
        self._api.register_entity(self)

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this select."""
        return "_".join([self._name, PAR_SWING_MODE])

    @property
    def device_info(self):
        """Return device information for this select."""
        return {
            "identifiers": {(DOMAIN, self._name)},
            "manufacturer": "Mitsubishi Heavy Industries",
            "model": "RLA502A700B",
            "name": self._name,
        }

    @property
    def icon(self):
        """Return the icon for this select."""
        return get_entity_icon("select", PAR_SWING_MODE)

    @property
    def available(self):
        """Return True if entity is available."""
        return self._api.available

    @property
    def should_poll(self):
        """Polling is required."""
        return True

    @property
    def options(self):
        """Return available vertical swing modes."""
        return SUPPORTED_SWING_MODES

    @property
    def current_option(self):
        """Return the current vertical swing mode."""
        try:
            self._api.read_data_json()
            return normalize_swing_mode(self._api._config_data[PAR_SWING_MODE])
        except Exception as ex:
            _LOGGER.error("Failed to read vertical swing option: %s", ex)
        return None

    def select_option(self, option):
        """Set the vertical swing mode."""
        option = normalize_swing_mode(option)
        if option in SUPPORTED_SWING_MODES:
            self._api.set_data_json({PAR_SWING_MODE: option})

    def update(self):
        """Update entity state."""
        return


class MitsubishiHorizontalSwingSelect(SelectEntity):
    """Horizontal swing control for a Mitsubishi AC."""

    def __init__(self, name, device):
        """Initialize the select entity."""
        self._name = name
        self._api = device.api
        self._attr_has_entity_name = True
        self._attr_name = None
        self._attr_translation_key = PAR_HSWING_MODE
        self._api.register_entity(self)

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this select."""
        return "_".join([self._name, PAR_HSWING_MODE])

    @property
    def device_info(self):
        """Return device information for this select."""
        return {
            "identifiers": {(DOMAIN, self._name)},
            "manufacturer": "Mitsubishi Heavy Industries",
            "model": "RLA502A700B",
            "name": self._name,
        }

    @property
    def icon(self):
        """Return the icon for this select."""
        return get_entity_icon("select", PAR_HSWING_MODE)

    @property
    def available(self):
        """Return True if entity is available."""
        return self._api.available

    @property
    def should_poll(self):
        """Polling is required."""
        return True

    @property
    def options(self):
        """Return available horizontal swing modes."""
        return SUPPORTED_HSWING_MODES

    @property
    def current_option(self):
        """Return the current horizontal swing mode."""
        try:
            self._api.read_data_json()
            return self._api._config_data[PAR_HSWING_MODE]
        except Exception as ex:
            _LOGGER.error("Failed to read horizontal swing option: %s", ex)
        return None

    def select_option(self, option):
        """Set the horizontal swing mode."""
        if option in SUPPORTED_HSWING_MODES:
            self._api.set_data_json({PAR_HSWING_MODE: option})

    def update(self):
        """Update entity state."""
        return


class MitsubishiInstallPositionSelect(SelectEntity):
    """Indoor unit install position setup for a Mitsubishi AC."""

    def __init__(self, name, device):
        """Initialize the select entity."""
        self._name = name
        self._api = device.api
        self._attr_has_entity_name = True
        self._attr_name = None
        self._attr_translation_key = PAR_INSTALL_POSITION
        self._api.register_entity(self)

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this select."""
        return "_".join([self._name, PAR_INSTALL_POSITION])

    @property
    def device_info(self):
        """Return device information for this select."""
        return {
            "identifiers": {(DOMAIN, self._name)},
            "manufacturer": "Mitsubishi Heavy Industries",
            "model": "RLA502A700B",
            "name": self._name,
        }

    @property
    def icon(self):
        """Return the icon for this select."""
        return get_entity_icon("select", PAR_INSTALL_POSITION)

    @property
    def available(self):
        """Return True if entity is available."""
        return self._api.available

    @property
    def should_poll(self):
        """Polling is required."""
        return True

    @property
    def options(self):
        """Return available install positions."""
        return SUPPORTED_INSTALL_POSITIONS

    @property
    def current_option(self):
        """Return the current install position."""
        try:
            self._api.read_data_json()
            return self._api._config_data[PAR_INSTALL_POSITION]
        except Exception as ex:
            _LOGGER.error("Failed to read install position: %s", ex)
        return None

    def select_option(self, option):
        """Set the indoor unit install position."""
        if option in SUPPORTED_INSTALL_POSITIONS:
            self._api.set_install_position(option)

    def update(self):
        """Update entity state."""
        return
