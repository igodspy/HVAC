"""UI entity labels and icons loaded from entity_config.json."""
from functools import lru_cache
import json
from pathlib import Path


CONFIG_FILE = Path(__file__).with_name("entity_config.json")
ICONS_FILE = Path(__file__).with_name("icons.json")
STRINGS_FILE = Path(__file__).with_name("strings.json")
POWER_SWITCH_KEY = "power"


@lru_cache(maxsize=1)
def get_entity_config():
    """Return the entity UI configuration."""
    with CONFIG_FILE.open(encoding="utf-8") as config_file:
        return json.load(config_file)


def get_entity_icon(platform, key):
    """Return the configured icon for an entity."""
    return get_entity_config().get(platform, {}).get(key, {}).get("icon")


def get_entity_name(platform, key):
    """Return the configured default label for an entity."""
    return get_entity_config().get(platform, {}).get(key, {}).get("name")


def get_option_switch_keys():
    """Return configured option switch keys, excluding the main power switch."""
    return [
        key
        for key in get_entity_config().get("switch", {})
        if key != POWER_SWITCH_KEY
    ]


def _get_state_icons(states):
    """Return Home Assistant state icon definitions."""
    return {
        state_key: state_config["icon"]
        for state_key, state_config in states.items()
        if state_config.get("icon")
    }


def _get_state_names(states):
    """Return Home Assistant state label definitions."""
    return {
        state_key: state_config["name"]
        for state_key, state_config in states.items()
        if state_config.get("name")
    }


def _get_state_attribute_icons(state_attributes):
    """Return Home Assistant state attribute icon definitions."""
    icon_attributes = {}
    for attribute_key, attribute_config in state_attributes.items():
        icon_attribute = {}
        if attribute_config.get("icon"):
            icon_attribute["default"] = attribute_config["icon"]

        state_icons = _get_state_icons(attribute_config.get("states", {}))
        if state_icons:
            icon_attribute["state"] = state_icons

        if icon_attribute:
            icon_attributes[attribute_key] = icon_attribute
    return icon_attributes


def _get_platform_icons(platform_config):
    """Return Home Assistant icon definitions for one platform."""
    platform_icons = {}
    for entity_key, entity_config in platform_config.items():
        entity_icons = {}
        if entity_config.get("icon"):
            entity_icons["default"] = entity_config["icon"]

        state_attribute_icons = _get_state_attribute_icons(
            entity_config.get("state_attributes", {})
        )
        if state_attribute_icons:
            entity_icons["state_attributes"] = state_attribute_icons

        if entity_icons:
            platform_icons[entity_key] = entity_icons
    return platform_icons


def build_icons_config():
    """Build Home Assistant icons.json content from entity_config.json."""
    return {
        "entity": {
            platform: platform_icons
            for platform, platform_icons in (
                (platform, _get_platform_icons(platform_config))
                for platform, platform_config in get_entity_config().items()
            )
            if platform_icons
        }
    }


def _get_state_attribute_strings(state_attributes):
    """Return Home Assistant state attribute label definitions."""
    string_attributes = {}
    for attribute_key, attribute_config in state_attributes.items():
        state_names = _get_state_names(attribute_config.get("states", {}))
        if state_names:
            string_attributes[attribute_key] = {"state": state_names}
    return string_attributes


def _get_platform_strings(platform, platform_config):
    """Return Home Assistant string definitions for one platform."""
    platform_strings = {}
    for entity_key, entity_config in platform_config.items():
        entity_strings = {}
        if platform != "climate" and entity_config.get("name"):
            entity_strings["name"] = entity_config["name"]

        state_names = _get_state_names(entity_config.get("states", {}))
        if state_names:
            entity_strings["state"] = state_names

        state_attribute_strings = _get_state_attribute_strings(
            entity_config.get("state_attributes", {})
        )
        if state_attribute_strings:
            entity_strings["state_attributes"] = state_attribute_strings

        if entity_strings:
            platform_strings[entity_key] = entity_strings
    return platform_strings


def build_entity_strings_config():
    """Build the Home Assistant entity strings from entity_config.json."""
    return {
        platform: platform_strings
        for platform, platform_strings in (
            (platform, _get_platform_strings(platform, platform_config))
            for platform, platform_config in get_entity_config().items()
        )
        if platform_strings
    }


def sync_icons_config():
    """Write icons.json from entity_config.json when it is out of date."""
    icons_config = build_icons_config()
    try:
        with ICONS_FILE.open(encoding="utf-8") as icons_file:
            if json.load(icons_file) == icons_config:
                return False
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    temp_file = ICONS_FILE.with_suffix(".json.tmp")
    with temp_file.open("w", encoding="utf-8") as icons_file:
        json.dump(icons_config, icons_file, ensure_ascii=False, indent=2)
        icons_file.write("\n")
    temp_file.replace(ICONS_FILE)
    return True


def sync_strings_config():
    """Update the entity section of strings.json from entity_config.json."""
    try:
        with STRINGS_FILE.open(encoding="utf-8") as strings_file:
            strings_config = json.load(strings_file)
    except (FileNotFoundError, json.JSONDecodeError):
        strings_config = {}

    updated_strings_config = dict(strings_config)
    updated_strings_config["entity"] = build_entity_strings_config()
    if updated_strings_config == strings_config:
        return False

    temp_file = STRINGS_FILE.with_suffix(".json.tmp")
    with temp_file.open("w", encoding="utf-8") as strings_file:
        json.dump(updated_strings_config, strings_file, ensure_ascii=False, indent=2)
        strings_file.write("\n")
    temp_file.replace(STRINGS_FILE)
    return True
