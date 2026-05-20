"""Constants for the Mitsubishi Heavy Industries RLA502A700B integration."""
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_NAME,
    UnitOfTemperature,
)

TEMP_CELSIUS = UnitOfTemperature.CELSIUS

CURRENT_HVAC_COOL = "cooling"
CURRENT_HVAC_DRY = "drying"
CURRENT_HVAC_FAN = "fan"
CURRENT_HVAC_HEAT = "heating"
CURRENT_HVAC_OFF = "off"

HVAC_MODE_AUTO = "heat_cool"
HVAC_MODE_COOL = "cool"
HVAC_MODE_DRY = "dry"
HVAC_MODE_FAN_ONLY = "fan_only"
HVAC_MODE_HEAT = "heat"
HVAC_MODE_HEAT_COOL = "heat_cool"
HVAC_MODE_OFF = "off"


def _value(value):
    return getattr(value, "value", value)


def normalize_hvac_mode(hvac_mode):
    """Return a supported HVAC mode, accepting external string aliases."""
    if hvac_mode == "auto":
        return HVAC_MODE_HEAT_COOL
    for supported_mode in [
        HVAC_MODE_COOL,
        HVAC_MODE_DRY,
        HVAC_MODE_FAN_ONLY,
        HVAC_MODE_HEAT,
        HVAC_MODE_HEAT_COOL,
        HVAC_MODE_OFF,
    ]:
        if hvac_mode == supported_mode or hvac_mode == _value(supported_mode):
            return supported_mode
    return hvac_mode


SWING_MODE_OFF = "off"
SWING_MODE_AUTO = "auto"
SWING_MODE_HIGHEST = "highest"
SWING_MODE_HIGH = "high"
SWING_MODE_MIDDLE = "middle"
SWING_MODE_LOW = "low"
SWING_MODE_LOWEST = "lowest"

SWING_MODE_ALIASES = {
    "90": SWING_MODE_HIGHEST,
    "60": SWING_MODE_HIGH,
    "45": SWING_MODE_MIDDLE,
    "30": SWING_MODE_LOW,
    "0": SWING_MODE_LOWEST,
}


def normalize_swing_mode(swing_mode):
    """Return a supported swing mode, accepting old numeric aliases."""
    return SWING_MODE_ALIASES.get(swing_mode, swing_mode)

SUPPORT_TARGET_TEMPERATURE = ClimateEntityFeature.TARGET_TEMPERATURE
SUPPORT_FAN_MODE = ClimateEntityFeature.FAN_MODE
SUPPORT_SWING_MODE = ClimateEntityFeature.SWING_MODE
SUPPORT_PRESET_MODE = ClimateEntityFeature.PRESET_MODE
SUPPORT_TURN_ON = getattr(ClimateEntityFeature, "TURN_ON", 0)
SUPPORT_TURN_OFF = getattr(ClimateEntityFeature, "TURN_OFF", 0)

DOMAIN = "mitsubishi"
DATA_MITSUBISHI = DOMAIN
DEVICES = "devices"
CLIMATES = "climates"

HUMIDITY_ENTITY = "humidity_entity"
TEMPERARURE_ENTITY = "temperature_entity"
REMOTE_ENTITY = "remote_entity"

CURRENT_HVAC_MAINTAINING = "maintaining"

FAN_HIGHEST = "highest"
FAN_LOWEST = "lowest"

FAN_MODE_ALIASES = {
    "max": FAN_HIGHEST,
    "turbo": FAN_HIGHEST,
}


def normalize_fan_mode(fan_mode):
    """Return a supported fan mode, accepting old aliases."""
    return FAN_MODE_ALIASES.get(fan_mode, fan_mode)

PAR_HVAC_MODE = "hvac_mode"
PAR_FAN_MODE = "fan_mode"
PAR_TEMPERATURE = "temperature"
PAR_SWING_MODE = "swing_mode"
PAR_HSWING_MODE = "hswing_mode"
PAR_QUIET = "quiet"
PAR_SLEEP = "sleep"
PAR_PURIFIER = "purifier"
PAR_PURIFIER_ENDS_AT = "purifier_ends_at"
PAR_CLEANING = "cleaning"
PAR_CLEANING_ENDS_AT = "cleaning_ends_at"
PAR_POWERFUL = "powerful"
PAR_POWERFUL_ENDS_AT = "powerful_ends_at"
PAR_ECONOMY = "economy"
PAR_3D_AUTO = "3d_auto"

OPTION_PARAMETERS = [
    PAR_SWING_MODE,
    PAR_HSWING_MODE,
    PAR_QUIET,
    PAR_SLEEP,
    PAR_PURIFIER,
    PAR_CLEANING,
    PAR_POWERFUL,
    PAR_ECONOMY,
    PAR_3D_AUTO,
]

TEMP_MIN = 18
TEMP_MAX = 30

SUPPORTED_HVAC_MODES = [
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
]
SUPPORTED_FAN_MODES = [
    FAN_AUTO,
    FAN_LOWEST,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_HIGHEST,
]
SUPPORTED_SWING_MODES = [
    SWING_MODE_OFF,
    SWING_MODE_AUTO,
    SWING_MODE_HIGHEST,
    SWING_MODE_HIGH,
    SWING_MODE_MIDDLE,
    SWING_MODE_LOW,
    SWING_MODE_LOWEST,
]
SUPPORTED_HSWING_MODES = [
    "auto",
    "wide",
    "far right",
    "right",
    "middle",
    "left",
    "far left",
    "off",
]

OPTION_OFF = "off"
OPTION_ON = "on"
SUPPORTED_OPTION_VALUES = [OPTION_OFF, OPTION_ON]

PRESET_NONE = "none"
PRESET_QUIET = PAR_QUIET
PRESET_SLEEP = PAR_SLEEP
PRESET_PURIFIER = PAR_PURIFIER
PRESET_CLEANING = PAR_CLEANING
PRESET_POWERFUL = PAR_POWERFUL
PRESET_ECONOMY = PAR_ECONOMY
SUPPORTED_PRESET_MODES = [
    PRESET_NONE,
    PRESET_POWERFUL,
    PRESET_ECONOMY,
]

STANDALONE_OPTION_PARAMETERS = [
    PAR_SLEEP,
    PAR_PURIFIER,
    PAR_CLEANING,
]

CLIMATE_PRESET_PARAMETERS = [
    PAR_POWERFUL,
    PAR_ECONOMY,
]

SUPPORT_FLAGS = (
    SUPPORT_FAN_MODE
    | SUPPORT_TARGET_TEMPERATURE
    | SUPPORT_SWING_MODE
    | SUPPORT_PRESET_MODE
    | SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
)
