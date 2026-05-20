## Control of Mitsubishi Heavy Industries RLA502A700B via Broadlink IR for Home Assistant
A small Home Assistant custom component for Mitsubishi Heavy Industries ACs controlled by the RLA502A700B remote. IR commands are generated on demand and sent through an existing Home Assistant `remote` entity.

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
- Vertical swing: off, auto, 90, 60, 45, 30, 0.
- Presets: quiet, sleep, purifier, cleaning, powerful, economy.
- Horizontal swing: auto, wide, far right, right, middle, left, far left, off.
- Individual option switches: quiet, sleep, purifier, cleaning, powerful, economy.

Horizontal swing and individual options are exposed as Home Assistant entities:
- `select.<name>_horizontal_swing`
- `switch.<name>_quiet`
- `switch.<name>_sleep`
- `switch.<name>_purifier`
- `switch.<name>_cleaning`
- `switch.<name>_powerful`
- `switch.<name>_economy`

The `mitsubishi.set_options` service is still available for existing automations.

### Lovelace card example
```
type: vertical-stack
cards:
  - type: thermostat
    entity: climate.livingroom_cond
    name: Living Room

  - type: entities
    title: Air conditioner options
    features:
      - style: dropdown
        type: climate-swing-modes
      - style: icons
        type: climate-fan-modes
      - style: icons
        type: climate-preset-modes
      - type: climate-hvac-modes
    entities:
      - entity: select.livingroom_cond_horizontal_swing
        name: Horizontal swing
        icon: mdi:arrow-left-right
      - entity: switch.livingroom_cond_quiet
        name: Silent
        icon: mdi:volume-low
      - entity: switch.livingroom_cond_purifier
        name: Air purifier
        icon: mdi:air-purifier
      - entity: switch.livingroom_cond_sleep
        name: Night Setback
        icon: mdi:sleep
      - entity: switch.livingroom_cond_cleaning
        name: Self cleaning
        icon: mdi:spray-bottle

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
  name: "Living Room"
  hswing_mode: "middle"
  quiet: "on"
```

### Afternote
You are free to use or modify this software, but i do not take any responsibility for any issues.
