# DShot Decoder Output Specification

## 1. Annotation Types

Annotation types are integer IDs that categorize the visual representation of decoded data in the logic analyzer output.

```python
# Annotation Type IDs (pseudo-enum for clarity)
class AnnotationType:
    BIT = 0            # Individual bit (high/low)
    FRAME = 1          # Complete 16-bit frame
    THROTTLE = 2       # Throttle value (0-2047)
    TELEMETRY = 3      # Telemetry request flag
    CRC = 4            # CRC validation status
    SPECIAL_CMD = 5    # Special command name
    ERPM = 6           # eRPM value (bidirectional mode)
    ERROR = 7          # Error annotation
    WARNING = 8        # Warning annotation
```

### Annotation Type Descriptions

| ID | Name | Description | Color Hint |
|----|------|-------------|------------|
| 0 | BIT | Individual bit timing with value annotation | Light gray |
| 1 | FRAME | Complete 16-bit frame boundary | Blue |
| 2 | THROTTLE | Decoded throttle value with range indication | Green |
| 3 | TELEMETRY | Telemetry request flag status | Yellow |
| 4 | CRC | CRC validation result (valid/invalid) | Red (invalid) / Green (valid) |
| 5 | SPECIAL_CMD | Named special command when applicable | Cyan |
| 6 | ERPM | eRPM value in bidirectional mode | Magenta |
| 7 | ERROR | Critical error annotation | Red |
| 8 | WARNING | Non-critical warning annotation | Orange |

---

## 2. Annotation Rows

Annotation rows group related annotations vertically for organized display.

```python
# Annotation Row IDs
class AnnotationRow:
    BITS = 'bits'          # Individual bit-level annotations
    FRAMES = 'frames'      # Frame-level annotations (start/end)
    VALUES = 'values'      # Decoded value annotations
    ERRORS = 'errors'      # Error and warning annotations
```

### Row Descriptions

| Row ID | Purpose | Annotation Types Used |
|--------|---------|----------------------|
| `bits` | Individual bit timing and value | BIT (0) |
| `frames` | Frame boundaries and structure | FRAME (1) |
| `values` | Decoded protocol values | THROTTLE (2), TELEMETRY (3), CRC (4), SPECIAL_CMD (5), ERPM (6) |
| `errors` | Error and warning messages | ERROR (7), WARNING (8) |

---

## 3. Python Output Structure

The decoder returns a Python dictionary for each decoded frame.

### Primary Output Structure

```python
# Type definition (for documentation purposes)
DShotOutput = {
    'type': str,              # 'frame', 'error', 'telemetry'
    'throttle': int,          # 0-2047 (throttle value or command ID)
    'special_command': str | None,  # Named command or None
    'telemetry_request': bool,
    'crc_valid': bool,
    'erpm': int | None,       # eRPM in bidirectional mode, or None
    'error_type': str | None, # Error description or None
    'variant': str,           # 'DSHOT150', 'DSHOT300', 'DSHOT600'
    'mode': str,              # 'unidirectional', 'bidirectional'
}
```

### Field Specifications

| Field | Type | Range/Values | Description |
|-------|------|--------------|-------------|
| `type` | str | 'frame', 'error', 'telemetry' | Output classification |
| `throttle` | int | 0-2047 | Raw throttle/command value |
| `special_command` | str \| None | See Special Commands | Named command if throttle 0-47 |
| `telemetry_request` | bool | True/False | Bit 11 value |
| `crc_valid` | bool | True/False | CRC validation result |
| `erpm` | int \| None | 0-65535+ | eRPM (bidirectional mode only) |
| `error_type` | str \| None | See Error Types | Error classification |
| `variant` | str | 'DSHOT150', 'DSHOT300', 'DSHOT600' | DShot variant detected |
| `mode` | str | 'unidirectional', 'bidirectional' | Operating mode |

---

## 4. Special Commands Mapping

```python
SPECIAL_COMMANDS = {
    0: 'MOTOR_STOP',
    1: 'BEEP_1',
    2: 'BEEP_2',
    3: 'BEEP_3',
    4: 'BEEP_4',
    5: 'BEEP_5',
    6: 'ESC_INFO',
    7: 'SPIN_DIRECTION_1',
    8: 'SPIN_DIRECTION_2',
    9: 'SPIN_DIRECTION_3',
    10: 'SPIN_DIRECTION_4',
    11: 'SPIN_DIRECTION_5',
    12: 'SPIN_DIRECTION_6',
    20: 'SPIN_DIRECTION_NORMAL',
    21: 'SPIN_DIRECTION_REVERSED',
    22: 'LED_0_ON',
    23: 'LED_1_ON',
    24: 'LED_2_ON',
    25: 'LED_3_ON',
    26: 'LED_4_ON',
    27: 'LED_5_ON',
    28: 'LED_6_ON',
    29: 'LED_7_ON',
    30: 'LED_8_ON',
    31: 'LED_9_ON',
    32: 'LED_10_ON',
    33: 'LED_11_ON',
    34: 'LED_12_ON',
    35: 'LED_13_ON',
    36: 'LED_14_ON',
    37: 'LED_15_ON',
    38: 'LED_16_ON',
    39: 'LED_17_ON',
    40: 'LED_18_ON',
    41: 'LED_19_ON',
    42: 'AUDIO_STREAM_MODE_ON',
    43: 'AUDIO_STREAM_MODE_OFF',
    44: 'CONFIRM_STREAM_MODE_OFF',
    45: 'SAVE_SETTINGS',
    46: 'SETTINGS_REQUEST',
    47: 'TELEMETRY_REQUEST',
}
```

---

## 5. Error Types

```python
ERROR_TYPES = {
    'TIMING_ERROR': 'Bit timing outside valid tolerance',
    'CRC_ERROR': 'CRC checksum mismatch',
    'FRAME_ERROR': 'Invalid frame structure',
    'GLITCH_ERROR': 'Signal glitch detected',
    'TIMEOUT_ERROR': 'Frame timeout',
    'VARIANT_MISMATCH': 'Detected variant conflicts with configured variant',
}
```

---

## 6. Example Outputs

### 6.1 Normal Throttle Frame (Unidirectional)

```python
{
    'type': 'frame',
    'throttle': 1000,              # Mid-range throttle
    'special_command': None,
    'telemetry_request': False,
    'crc_valid': True,
    'erpm': None,                  # Not applicable in unidirectional
    'error_type': None,
    'variant': 'DSHOT600',
    'mode': 'unidirectional',
}
```

### 6.2 Special Command Frame (Motor Stop)

```python
{
    'type': 'frame',
    'throttle': 0,
    'special_command': 'MOTOR_STOP',
    'telemetry_request': False,
    'crc_valid': True,
    'erpm': None,
    'error_type': None,
    'variant': 'DSHOT600',
    'mode': 'unidirectional',
}
```

### 6.3 Special Command with Telemetry Request

```python
{
    'type': 'telemetry',
    'throttle': 47,
    'special_command': 'TELEMETRY_REQUEST',
    'telemetry_request': True,
    'crc_valid': True,
    'erpm': None,
    'error_type': None,
    'variant': 'DSHOT300',
    'mode': 'unidirectional',
}
```

### 6.4 CRC Error Frame

```python
{
    'type': 'error',
    'throttle': 1500,
    'special_command': None,
    'telemetry_request': False,
    'crc_valid': False,
    'erpm': None,
    'error_type': 'CRC_ERROR',
    'variant': 'DSHOT600',
    'mode': 'unidirectional',
}
```

### 6.5 Bidirectional eRPM Frame

```python
{
    'type': 'frame',
    'throttle': 1200,
    'special_command': None,
    'telemetry_request': True,
    'crc_valid': True,
    'erpm': 15000,                 # eRPM value from ESC
    'error_type': None,
    'variant': 'DSHOT600',
    'mode': 'bidirectional',
}
```

### 6.6 Timing Error Frame

```python
{
    'type': 'error',
    'throttle': None,              # Could not decode reliably
    'special_command': None,
    'telemetry_request': None,
    'crc_valid': False,
    'erpm': None,
    'error_type': 'TIMING_ERROR',
    'variant': 'DSHOT600',
    'mode': 'unidirectional',
}
```

### 6.7 Beep Command Sequence

```python
{
    'type': 'frame',
    'throttle': 3,
    'special_command': 'BEEP_3',
    'telemetry_request': False,
    'crc_valid': True,
    'erpm': None,
    'error_type': None,
    'variant': 'DSHOT300',
    'mode': 'unidirectional',
}
```

### 6.8 Save Settings Command

```python
{
    'type': 'frame',
    'throttle': 45,
    'special_command': 'SAVE_SETTINGS',
    'telemetry_request': False,
    'crc_valid': True,
    'erpm': None,
    'error_type': None,
    'variant': 'DSHOT600',
    'mode': 'unidirectional',
}
```

---

## 7. Annotation Output Format

For each decoded element, annotations follow this structure:

```python
# Annotation tuple format: (start_sample, end_sample, annotation_type, annotation_data)
annotation = (
    start_sample,      # Sample index where annotation starts
    end_sample,        # Sample index where annotation ends
    annotation_type,   # Integer from AnnotationType class
    annotation_data    # Dict or string with display information
)
```

### Example Annotation Data

```python
# Bit annotation
(1000, 1250, 0, {'value': 1, 'position': 15})  # MSB, position 15

# Frame annotation
(1000, 40000, 1, {'frame_value': 0b1010101010101010, 'hex': '0xAAAA'})

# Throttle annotation
(1000, 40000, 2, {'value': 1000, 'percent': 48.8})

# CRC annotation (valid)
(35000, 40000, 4, {'valid': True, 'checksum': 0b1010})

# CRC annotation (invalid)
(35000, 40000, 4, {'valid': False, 'expected': 0b1010, 'calculated': 0b0110})

# Special command annotation
(1000, 40000, 5, {'name': 'MOTOR_STOP', 'id': 0})

# Error annotation
(1000, 40000, 7, {'error': 'CRC_ERROR', 'message': 'CRC mismatch: expected 0b1010, got 0b0110'})
```

---

## 8. Implementation Notes

### Bit Timing Tolerances

| Variant | Bit Period | Tolerance | High/Low Threshold |
|---------|------------|-----------|-------------------|
| DSHOT150 | 6.67 μs | ±5% | 37.5% duty for '0', 75% for '1' |
| DSHOT300 | 3.33 μs | ±5% | 37.5% duty for '0', 75% for '1' |
| DSHOT600 | 1.67 μs | ±5% | 37.5% duty for '0', 75% for '1' |

### CRC Calculation

```python
def calculate_crc(throttle: int, telemetry: bool) -> int:
    """
    Calculate DShot CRC from throttle and telemetry bits.
    
    CRC = (throttle ^ (throttle >> 4) ^ (throttle >> 8)) & 0xF
    Then XOR with telemetry bit shifted into position.
    """
    crc = throttle ^ (throttle >> 4) ^ (throttle >> 8)
    if telemetry:
        crc ^= 0x8  # XOR with telemetry bit in position 3
    return crc & 0xF
```

---

## Document Status

- **Created**: 2026-03-13
- **Task**: Task 4 - Define Output Specification
- **Status**: Complete
