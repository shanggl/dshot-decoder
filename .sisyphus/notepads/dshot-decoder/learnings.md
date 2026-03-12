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

### 2026-03-13 Task 6: Core Decoder Implementation
- Implemented decode() method with edge-triggered state machine
- State machine: IDLE → SYNC → FRAME → DECODE transitions
- Edge detection: self.wait({0: 'e'}) for rising/falling edge detection
- Bit threshold: high_time > 0.56 * bit_period → logic 1
- Timing tolerance: ±15% for T0H_min to T1H_max range
- Idle detection: gap > 2× bit_period for frame start
- Frame timeout: gap > 2.3× bit_period triggers resync
- CRC validation: (value ^ (value >> 4) ^ (value >> 8)) & 0x0F
- Annotations emitted for: bit, frame, throttle, special command, telemetry, CRC, error
- Python dict output for stacked decoders with raw, throttle, telemetry, crc_valid fields
- decode_erpm() and decode_gcr() are stubs for Task 9 (bidirectional)

### Gotchas
- self.wait({0: 'e'}) returns tuple (data,) not just data
- last_pin_state must be tracked to determine edge type (rising vs falling)
- Frame bits collected MSB first, shifted left into raw_value
- throttle = (raw_value >> 5) & 0x7FF extracts bits 0-10
- telemetry = (raw_value >> 4) & 0x01 extracts bit 11
- crc = raw_value & 0x0F extracts bits 12-15
- CRC is calculated on (throttle << 1) | telemetry, not just throttle

### 2026-03-13 Task 9: Bidirectional eRPM Telemetry
- Implemented bidirectional mode with WAITING_TELEMETRY and TELEMETRY_FRAME states
- ESC response signal is INVERTED: falling edge triggers bit start, low=1, high=0
- ESC responds ~30µs after FC frame ends with telemetry=1
- Telemetry timeout window: 100µs after FC frame
- ESC sends 21-bit GCR-encoded frame: 1 sync bit + 20 GCR bits
- GCR decoding: XOR each bit with previous, then reverse-map 5-bit symbols to 4-bit nibbles
- eRPM frame structure (16-bit after GCR decode):
  - Bits 13-15: Shift count (3 bits)
  - Bits 4-12: Period base (9 bits)
  - Bits 0-3: CRC (4 bits)
- eRPM = (period_base << shift_count) * 100
- CRC calculation for telemetry: same as FC frame but over 12-bit value (bits 4-15)
- In bidirectional mode, _decode_frame returns frame_data for linking to telemetry
- Python output for telemetry includes: type, raw_gcr, decoded, erpm, shift_count, period_base, crc_valid, fc_frame

### Gotchas
- In TELEMETRY_FRAME state, bit value is inverted: short low pulse = 1, long low pulse = 0
- Telemetry frame bit count is 21 (not 16)
- GCR_NIBBLE_REVERSE maps 5-bit symbols to 4-bit nibbles
- Must track falling_edge_sample for telemetry (not rising_edge_sample like FC frames)
- Use telemetry_start_sample for timeout calculation (not frame_start_sample)
- fc_frame is stored in channel state to link telemetry response to request

### 2026-03-13 Task 12: Verification
- All Python files compile successfully (py_compile verified)
- Decoder structure verified: all required methods present
- Constants verified: DSHOT_TIMING (3 variants), DSHOT_SPECIAL_COMMANDS (48), GCR_NIBBLE_MAP (16), GCR_NIBBLE_REVERSE
- sigrokdecode module is runtime dependency - not testable in dev environment
- Manual testing required with sigrok-cli or PulseView

### Implementation Summary
- Task 5: Decoder skeleton created
- Task 6: Core decoder (unidirectional, single channel)
- Task 7: DShot variants (150/300/600) - integrated into Task 5
- Task 8: Multi-channel support (up to 4 ESCs)
- Task 9: Bidirectional eRPM telemetry decoding
- Task 10: Error detection (CRC, GCR, sample rate, missing telemetry)
- Task 11: Special command names (48 commands)
- Task 12: Verification (syntax and structure verified)

```

### 2026-03-13 Final Status
- All 36 tasks completed (F3 blocked pending external verification)
- F3 (Manual QA) blocked: requires sigrok/PulseView and DShot captures
- Automated verification complete: syntax, structure, constants, features
- Blocker documented in .sisyphus/evidence/final-qa/F3-blocked.md

### Integration
To use: Copy decoders/dshot/ to atk_libsigrokdecode/decoders/
