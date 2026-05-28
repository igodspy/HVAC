
## Control of Mitsubishi Heavy Industries RLA502A700B via Broadlink IR for Home Assistant
A small Home Assistant custom component for Mitsubishi Heavy Industries ACs controlled by the RLA502A700B remote. IR commands are generated on demand and sent through an existing Home Assistant `remote` entity.


### Lovelace card with card-mod and mushroom
<img width="900" alt="AC" src="https://github.com/user-attachments/assets/810b6829-5e69-4e3f-a65c-1b67e00b5ac3" /><br/>
See `card-mod_and_mushroom_ac_card.example.yaml` for an example with card-mod and mushroom mods installed for wall installation indicators and better select entities.<br/>

### Installation
Copy folder `mitsubishi` to `/config/custom_components`. 
Include following in `configuration.yaml`:
```
mitsubishi:
  - remote_entity: remote.living_room_broadlink
    name: "Living Room"
```

### Configuration attributes
- `remote_entity` - **mandatory** Home Assistant remote entity used to send Broadlink commands.
- `name` - friendly name.
- `temperature_entity` - separate unrelated temperature sensor entity, which will be used as part of climate entity (for observability in google home for example). For example if you have xiaomi bluetooth sensor in the room where AC is located, then measured temperature will be also visible in newly created climate entity as part of AC and will be accessible from google.
- `humidity_entity` - separate unrelated humidity sensor entity, which will be used as part of climate entity (for observability in google home for example). For example if you have xiaomi bluetooth sensor in the room where AC is located, then measured humidity will be also visible in newly created climate entity as part of AC and will be accessible from google.

### Supported controls
- HVAC mode: off, heat, cool, dry, fan only, auto.
- Temperature: 18-30 C.
- Fan: auto, lowest, low, medium, high, highest.
- Vertical swing: off, auto, highest, high, middle, low, lowest. Legacy numeric values 90, 60, 45, 30, 0 are still accepted.
- Presets: quiet, sleep, Allergen Clear (`purifier`), cleaning, powerful, economy, 3D auto. 3D auto is disabled in dry, fan only, powerful, and economy modes.
- Horizontal swing: off, auto, wide, far right, right, middle, left, far left.
- Install position setup command: wall_on_the_left, center, wall_on_the_right. This is sent as a separate off-mode setup command.
- Main power switch: turns off with HVAC mode `off`; turns on with HVAC mode `cool`.
- Individual option switches: quiet, sleep, Allergen Clear, cleaning, powerful, economy.
- Allergen Clear turns off locally after 90 minutes. Self cleaning turns off locally after 2 hours. These timer-based state updates do not send an IR command.
- Powerful turns off locally after 15 minutes. Powerful is not available during dry and fan only modes and is canceled when the HVAC mode changes, 3D auto is enabled, silent is enabled, or night setback is enabled.
- Economy is not available during fan only mode and is canceled when night setback is enabled.
- Silent is not available during dry and fan only modes.
- Self cleaning is not available after heat, fan only, sleep, and Allergen Clear operations. OFF timer is not modeled by this integration.
- In case of SCM multi system, ALLERGEN CLEAR control function is invalid. In case of SCM multi system, if ALLERGEN button is pressed by mistake, the indoor unit which received such command stops.

Swing modes and individual options are exposed as Home Assistant entities:
- `select.<name>_swing_mode`
- `select.<name>_horizontal_swing`
- `select.<name>_install_position`
- `switch.<name>_power`
- `switch.<name>_quiet`
- `switch.<name>_sleep`
- `switch.<name>_purifier`
- `switch.<name>_cleaning`
- `switch.<name>_powerful`
- `switch.<name>_economy`
- `switch.<name>_3d_auto`

The `mitsubishi.set_options` service is still available for existing automations.

### Entity labels and icons
Entity labels, select option labels, and icons are configured in `mitsubishi/entity_config.json`.
This file is the main place to customize how Mitsubishi entities and modes are shown in Home Assistant.

The integration synchronizes Home Assistant metadata from `entity_config.json` on startup:
- `icons.json` is regenerated when configured icons are changed.
- The entity section of `strings.json` is regenerated when configured English labels are changed.

After changing `entity_config.json`, restart Home Assistant or reload the custom integration. If the UI still shows old icons or labels, clear the Home Assistant frontend cache or reload the browser page.

### Yandex Smart Home mode mapping
Home Assistant keeps the full set of Mitsubishi controls. For Yandex Smart Home, map unsupported values in `configuration.yaml` so Yandex receives only common mode names and does not show fallback labels like numbers.

See `yandex_smart_home.example.yaml` for a ready example. Replace `climate.livingroom_cond` with your climate entity ID.

### Lovelace card example
```
type: vertical-stack
cards:
  - type: thermostat
    entity: climate.livingroom_cond
    name: Living Room
    features:
      - style: icons
        type: climate-fan-modes
      - style: icons
        type: climate-preset-modes
      - style: icons
        type: climate-hvac-modes
        hvac_modes:
          - "off"
          - cool
          - heat
          - dry
          - fan_only
          - heat_cool
    show_current_as_primary: false
  - type: entities
    title: Air conditioner options
    entities:
      - entity: select.livingroom_cond_swing_mode
        name: Vertical swing
      - entity: select.livingroom_cond_horizontal_swing
        name: Horizontal swing
      - entity: switch.mitsubishi_livingroom_cond_3d_auto
        name: 3D auto
      - entity: switch.livingroom_cond_quiet
        name: Silent
      - entity: switch.livingroom_cond_purifier
        name: Allergen Clear
      - entity: switch.livingroom_cond_sleep
        name: Night Setback
      - entity: switch.livingroom_cond_cleaning
        name: Self cleaning
    show_header_toggle: false
```

### Configuration saving possible issues
Integration saves wanted configuration in JSON file located under `/config/custom_components/mitsubishi/json/` so no need to use input_select or input_number entities. 
It might happen that due to not found folder `json` configuration shall not be saved. To solve it, simply create `json` folder under `/config/custom_components/mitsubishi` and set rights for everyone to be able to modify contents of this folder. After first request to change data files with corresponding friendly names shall be created.
Examples of JSON files are included in `json` folder in this repository.

### configuration.yaml entry example
```
mitsubishi:
  - remote_entity: remote.living_room_broadlink
    name: "Living Room"
    temperature_entity: "sensor.living_room_temperature"
    humidity_entity: "sensor.living_room_humidity"
  - remote_entity: remote.bedroom_broadlink
    name: "Bedroom"
    temperature_entity: "sensor.bedroom_temperature"
    humidity_entity: "sensor.bedroom_humidity"
```

### Service example
```
service: mitsubishi.set_options
data:
  entity_id: climate.livingroom_cond
  hswing_mode: "middle"
  quiet: "on"
```

### Install position setup service example
Send this while the indoor unit is off.
```
service: mitsubishi.set_install_position
data:
  entity_id: climate.livingroom_cond
  install_position: "wall_on_the_left"
```

or control it via lovelace card
```
type: entities
title: Mitsubishi install position
entities:
  - entity: select.mitsubishi_livingroom_install_position
    name: Current install position
```

### Afternote
You are free to use or modify this software, but i do not take any responsibility for any issues.
