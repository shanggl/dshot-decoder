# DShot Decoder - Learnings

## Session Log

### 2026-03-12 Session Start
- Git repository initialized
- Plan created with 12 implementation tasks + 4 verification tasks
- Wave 1 tasks (1-4) can run in parallel

### Annotation Type IDs
- Use integers 0-8 for annotation types (compatible with sigrok conventions)
- Color hints: Red for errors, Green for valid, Yellow for telemetry, Cyan for commands

### Special Commands
- Throttle values 0-47 are reserved for special commands
- 0: MOTOR_STOP (disarm command)
- 1-5: BEEP commands (audible feedback)
- 6: ESC_INFO request
- 7-8: SPIN_DIRECTION commands
- 20-21: Normal/Reversed direction
- 42-47: Telemetry and audio stream commands

### CRC Calculation
- CRC = (throttle ^ (throttle >> 4) ^ (throttle >> 8)) & 0xF
- Telemetry bit XORed into position 3 if set
- 4-bit checksum (bits 12-15 of frame)

- Output structure uses `type` field to classify: 'frame', 'error', 'telemetry'
- `special_command` is resolved name, `throttle` is raw numeric value
- `erpm` field only populated in bidirectional mode
- Null/None values used when data unavailable (e.g., timing errors)

- Throttle 0 is a valid special command (MOTOR_STOP), not a throttle value
- In bidirectional mode, eRPM is returned from ESC, not calculated
- CRC validation is critical for frame acceptance

### 2026-03-13 Task 4: Output Specification
- Created comprehensive output specification document
- Defined 9 annotation types (BIT, FRAME, THROTTLE, TELEMETRY, CRC, SPECIAL_CMD, ERPM, ERROR, WARNING)
- Defined 4 annotation rows (bits, frames, values, errors)
- Documented Python output dictionary structure with type hints
- Included 8 example output scenarios covering all cases

### 2026-03-13 Task 5: Decoder Skeleton
- Created decoders/dshot/ directory structure
- __init__.py: Module docstring describing DShot protocol
- lists.py: All constants (DSHOT_TIMING, DSHOT_SPECIAL_COMMANDS, GCR_NIBBLE_MAP, ERROR_TYPES)
- pd.py: Decoder class skeleton with api_version=3, channels, options, annotations
- Decoder options: variant (DSHOT150/300/600), mode (unidirectional/bidirectional), num_channels (1-4)
- Optional channels for ESC 2-4 (multi-motor support)
- CRC calculation methods: calculate_crc() for normal, calculate_crc_bidirectional() for inverted
- eRPM decode stub: decode_erpm() and decode_gcr() for bidirectional telemetry
- Python syntax verified with py_compile
- sigrokdecode module is runtime dependency (not installed in dev environment)
