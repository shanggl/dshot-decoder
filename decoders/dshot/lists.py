'''
DShot Protocol Constants

This module contains timing parameters, special command mappings,
and GCR encoding tables for the DShot decoder.
'''

# DShot Timing Parameters (in microseconds)
# T1H = Time high for logic 1
# T0H = Time high for logic 0
# BIT_PERIOD = Total bit duration
# FRAME_PERIOD = 16 * BIT_PERIOD (total frame duration)
DSHOT_TIMING = {
    'DSHOT150': {
        't1h_us': 5.00,
        't0h_us': 2.50,
        'bit_period_us': 6.67,
        'frame_period_us': 106.72,
        'bitrate': 150000,
    },
    'DSHOT300': {
        't1h_us': 2.50,
        't0h_us': 1.25,
        'bit_period_us': 3.33,
        'frame_period_us': 53.28,
        'bitrate': 300000,
    },
    'DSHOT600': {
        't1h_us': 1.25,
        't0h_us': 0.625,
        'bit_period_us': 1.67,
        'frame_period_us': 26.72,
        'bitrate': 600000,
    },
}

# Minimum sample rate multiplier (samples per bit period)
# Recommended: 10x bitrate for reliable decoding
MIN_SAMPLE_RATE_MULTIPLIER = 10

# Timing tolerance for bit decoding (±15%)
TIMING_TOLERANCE = 0.15

# Threshold for distinguishing logic 1 vs logic 0
# If high_time > threshold * bit_period, it's a 1
# For DShot: T1H = 75% duty, T0H = 37.5% duty
# Threshold at ~56% provides margin
BIT_THRESHOLD = 0.56

# Idle detection: minimum gap between frames (in bit periods)
MIN_IDLE_BIT_PERIODS = 2.0

# DShot Special Commands (throttle values 0-47)
# Reference: https://betaflight.com/docs/development/API/Dshot
DSHOT_SPECIAL_COMMANDS = {
    0: 'MOTOR_STOP',
    1: 'BEEP_1',
    2: 'BEEP_2',
    3: 'BEEP_3',
    4: 'BEEP_4',
    5: 'BEEP_5',
    6: 'ESC_INFO',
    7: 'SPIN_DIRECTION_1',
    8: 'SPIN_DIRECTION_2',
    9: '3D_MODE_OFF',
    10: '3D_MODE_ON',
    11: 'SETTINGS_REQUEST',
    12: 'SAVE_SETTINGS',
    13: 'EXTENDED_TELEMETRY_ENABLE',
    14: 'EXTENDED_TELEMETRY_DISABLE',
    15: 'SPIN_DIRECTION_NORMAL_1',
    16: 'SPIN_DIRECTION_NORMAL_2',
    17: 'SPIN_DIRECTION_NORMAL_3',
    18: 'SPIN_DIRECTION_NORMAL_4',
    19: 'SPIN_DIRECTION_NORMAL_5',
    20: 'SPIN_DIRECTION_NORMAL',
    21: 'SPIN_DIRECTION_REVERSED',
    22: 'LED_0_ON',
    23: 'LED_1_ON',
    24: 'LED_2_ON',
    25: 'LED_3_ON',
    26: 'LED_0_OFF',
    27: 'LED_1_OFF',
    28: 'LED_2_OFF',
    29: 'LED_3_OFF',
    30: 'AUDIO_STREAM_MODE_ON',
    31: 'AUDIO_STREAM_MODE_OFF',
    32: 'SIGNAL_LINE_TELEMETRY_DISABLE',
    33: 'SIGNAL_LINE_TELEMETRY_ENABLE',
    34: 'SIGNAL_LINE_CONTINUOUS_ERPM_TELEMETRY',
    35: 'SIGNAL_LINE_CONTINUOUS_ERPM_PERIOD_TELEMETRY',
    36: 'SIGNAL_LINE_TEMP_TELEMETRY_1',
    37: 'SIGNAL_LINE_TEMP_TELEMETRY_2',
    38: 'SIGNAL_LINE_TEMP_TELEMETRY_3',
    39: 'SIGNAL_LINE_TEMP_TELEMETRY_4',
    40: 'SIGNAL_LINE_TEMP_TELEMETRY_5',
    41: 'SIGNAL_LINE_TEMP_TELEMETRY_6',
    42: 'SIGNAL_LINE_VOLTAGE_TELEMETRY',
    43: 'SIGNAL_LINE_CURRENT_TELEMETRY',
    44: 'SIGNAL_LINE_CONSUMPTION_TELEMETRY',
    45: 'SIGNAL_LINE_ERPM_TELEMETRY',
    46: 'SIGNAL_LINE_ERPM_PERIOD_TELEMETRY',
    47: 'STATUS_INFO_REQUEST',
}

# Minimum throttle value for actual throttle (not special command)
THROTTLE_MIN = 48

# Maximum throttle value
THROTTLE_MAX = 2047

# GCR Nibble Map for bidirectional eRPM decoding
# Maps 4-bit nibble to 5-bit GCR encoded value
# Reference: https://betaflight.com/docs/development/API/Dshot
GCR_NIBBLE_MAP = {
    0x0: 0x19,  # 0 -> 25 (0b11001)
    0x1: 0x1B,  # 1 -> 27 (0b11011)
    0x2: 0x12,  # 2 -> 18 (0b10010)
    0x3: 0x13,  # 3 -> 19 (0b10011)
    0x4: 0x1D,  # 4 -> 29 (0b11101)
    0x5: 0x15,  # 5 -> 21 (0b10101)
    0x6: 0x16,  # 6 -> 22 (0b10110)
    0x7: 0x17,  # 7 -> 23 (0b10111)
    0x8: 0x1A,  # 8 -> 26 (0b11010)
    0x9: 0x09,  # 9 -> 9  (0b01001)
    0xA: 0x0A,  # 10 -> 10 (0b01010)
    0xB: 0x0B,  # 11 -> 11 (0b01011)
    0xC: 0x1E,  # 12 -> 30 (0b11110)
    0xD: 0x0D,  # 13 -> 13 (0b01101)
    0xE: 0x0E,  # 14 -> 14 (0b01110)
    0xF: 0x0F,  # 15 -> 15 (0b01111)
}

# Reverse GCR map for decoding (5-bit GCR -> 4-bit nibble)
GCR_NIBBLE_REVERSE = {v: k for k, v in GCR_NIBBLE_MAP.items()}

# eRPM telemetry frame structure
# 16 bits: 3-bit shift count + 9-bit period + 4-bit CRC
ERPM_SHIFT_BITS = 3
ERPM_PERIOD_BITS = 9
ERPM_CRC_BITS = 4

# Extended DShot Telemetry (EDT) types
EDT_TELEMETRY_TYPES = {
    0x02: 'TEMPERATURE',    # Temperature in °C
    0x04: 'VOLTAGE',        # Voltage in 0.25V steps
    0x06: 'CURRENT',        # Current in Amps
    0x08: 'DEBUG_1',        # Debug value 1
    0x0A: 'DEBUG_2',        # Debug value 2
    0x0C: 'DEBUG_3',        # Debug value 3
    0x0E: 'STATE_EVENT',    # State/Event
}

# Error types for annotation
ERROR_TYPES = {
    'TIMING_ERROR': 'Bit timing outside valid tolerance',
    'CRC_ERROR': 'CRC checksum mismatch',
    'FRAME_ERROR': 'Invalid frame structure',
    'GLITCH_ERROR': 'Signal glitch detected',
    'TIMEOUT_ERROR': 'Frame timeout',
    'SYNC_ERROR': 'Frame synchronization lost',
    'VARIANT_MISMATCH': 'Detected variant conflicts with configured variant',
}

# Warning types for annotation
WARNING_TYPES = {
    'LOW_SAMPLE_RATE': 'Sample rate below recommended minimum (10x bitrate)',
    'FRAME_GAP': 'Unexpected gap between frames',
    'PARTIAL_FRAME': 'Incomplete frame detected',
}
