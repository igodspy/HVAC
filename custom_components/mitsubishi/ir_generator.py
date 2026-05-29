"""Broadlink IR generation for Mitsubishi Heavy Industries RLA502A700B.

The state layout follows Mitsubishi Heavy 152-bit support from
IRremoteESP8266 and the capabilities exposed by pyhvac for the RLA502A700B
remote. Only this remote family is implemented here.
"""
import base64
import struct

from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
)

from .const import (
    FAN_HIGHEST,
    FAN_LOWEST,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    INSTALL_POSITION_CENTER,
    INSTALL_POSITION_WALL_ON_THE_LEFT,
    INSTALL_POSITION_WALL_ON_THE_RIGHT,
    OPTION_ON,
    PAR_3D_AUTO,
    PAR_CLEANING,
    PAR_ECONOMY,
    PAR_FAN_MODE,
    PAR_HSWING_MODE,
    PAR_HVAC_MODE,
    PAR_POWERFUL,
    PAR_PURIFIER,
    PAR_QUIET,
    PAR_SLEEP,
    PAR_SWING_MODE,
    PAR_TEMPERATURE,
    TEMP_MAX,
    TEMP_MIN,
)

STATE_LENGTH = 19
SIGNATURE = [0xAD, 0x51, 0x3C, 0xE5, 0x1A]
TEMP_ENCODING_OFFSET = 17

INSTALL_POSITION_MAP = {
    INSTALL_POSITION_CENTER: 0xA0,
    INSTALL_POSITION_WALL_ON_THE_RIGHT: 0xC0,
    INSTALL_POSITION_WALL_ON_THE_LEFT: 0xE0,
}

MODE_MAP = {
    HVAC_MODE_HEAT_COOL: 0,
    HVAC_MODE_COOL: 1,
    HVAC_MODE_DRY: 2,
    HVAC_MODE_FAN_ONLY: 3,
    HVAC_MODE_HEAT: 4,
}

FAN_MAP = {
    FAN_AUTO: 0x0,
    FAN_LOWEST: 0x6,
    FAN_LOW: 0x1,
    FAN_MEDIUM: 0x2,
    FAN_HIGH: 0x3,
    FAN_HIGHEST: 0x4,
}

SWING_MAP = {
    "auto": 0,
    "highest": 1,
    "90": 1,
    "high": 2,
    "60": 2,
    "middle": 3,
    "45": 3,
    "low": 4,
    "30": 4,
    "lowest": 5,
    "0": 5,
    "off": 6,
}

HSWING_MAP = {
    "auto": 0,
    "far left": 1,
    "left": 2,
    "middle": 3,
    "right": 4,
    "far right": 5,
    "wide": 6,
    "off": 8,
}

HDR_MARK = 3140
HDR_SPACE = 1630
BIT_MARK = 370
ONE_SPACE = 420
ZERO_SPACE = 1220
GAP = 100000


def generate_broadlink_base64(config):
    """Return a Broadlink base64 command for the supplied climate state."""
    raw = _build_state(config)
    pulses = _to_lirc(raw)
    packet = _to_broadlink_packet(pulses)
    return base64.b64encode(packet).decode("ascii")


def generate_install_position_base64(position):
    """Return a Broadlink base64 command for the indoor unit install position."""
    raw = _build_install_position_state(position)
    pulses = _to_lirc(raw)
    packet = _to_broadlink_packet(pulses)
    return base64.b64encode(packet).decode("ascii")


def _build_state(config):
    state = bytearray(STATE_LENGTH)
    state[: len(SIGNATURE)] = bytes(SIGNATURE)
    state[17] = 0x80

    mode = config.get(PAR_HVAC_MODE, HVAC_MODE_OFF)
    power = mode != HVAC_MODE_OFF
    native_mode = MODE_MAP.get(mode, MODE_MAP[HVAC_MODE_HEAT_COOL])

    temperature = int(round(float(config.get(PAR_TEMPERATURE, 25))))
    temperature = max(TEMP_MIN, min(TEMP_MAX, temperature))

    fan = FAN_MAP.get(config.get(PAR_FAN_MODE, FAN_AUTO), FAN_MAP[FAN_AUTO])
    if config.get(PAR_POWERFUL) == OPTION_ON:
        fan = 0x8
    elif config.get(PAR_ECONOMY) == OPTION_ON:
        fan = 0x6

    swing = SWING_MAP.get(config.get(PAR_SWING_MODE, "off"), SWING_MAP["off"])
    hswing = HSWING_MAP.get(
        config.get(PAR_HSWING_MODE, "auto"), HSWING_MAP["auto"]
    )

    state[5] = native_mode & 0x07
    if power:
        state[5] |= 1 << 3
    if config.get(PAR_CLEANING) == OPTION_ON:
        state[5] |= 1 << 5
        state[5] |= 1 << 6
    elif config.get(PAR_PURIFIER) == OPTION_ON:
        state[5] |= 1 << 6

    state[7] = (temperature - TEMP_ENCODING_OFFSET) & 0x0F
    state[9] = fan & 0x0F
    state[11] = (swing & 0x07) << 5
    if (
        config.get(PAR_3D_AUTO) == OPTION_ON
        and mode not in [HVAC_MODE_DRY, HVAC_MODE_FAN_ONLY]
        and config.get(PAR_POWERFUL) != OPTION_ON
        and config.get(PAR_ECONOMY) != OPTION_ON
    ):
        state[11] |= 0x12
    state[13] = hswing & 0x0F

    if config.get(PAR_SLEEP) == OPTION_ON:
        state[15] |= 1 << 6
    if config.get(PAR_QUIET) == OPTION_ON:
        state[15] |= 1 << 7

    _invert_byte_pairs(state)
    return state


def _build_install_position_state(position):
    state = bytearray(STATE_LENGTH)
    state[: len(SIGNATURE)] = bytes(SIGNATURE)
    state[5] = 0x01
    state[7] = 0x07
    state[9] = 0x01
    state[17] = INSTALL_POSITION_MAP[position]

    _invert_byte_pairs(state)
    return state


def _invert_byte_pairs(state):
    for index in range(3, len(state) - 1, 2):
        state[index + 1] = state[index] ^ 0xFF


def _to_lirc(state):
    pulses = [HDR_MARK, HDR_SPACE]
    for byte in state:
        bit = 0x01
        while bit <= 0x80:
            pulses.append(BIT_MARK)
            pulses.append(ONE_SPACE if byte & bit else ZERO_SPACE)
            bit <<= 1
    pulses.extend([BIT_MARK, GAP])
    return pulses


def _to_broadlink_packet(pulses):
    payload = bytearray()
    for pulse in pulses:
        ticks = round(pulse * 269 / 8192)
        if ticks < 256:
            payload += struct.pack(">B", ticks)
        else:
            payload += b"\x00" + struct.pack(">H", ticks)

    packet = bytearray([0x26, 0x00])
    packet += struct.pack("<H", len(payload))
    packet += payload
    packet += b"\x0D\x05"

    remainder = (len(packet) + 4) % 16
    if remainder:
        packet += bytes(16 - remainder)
    return packet
