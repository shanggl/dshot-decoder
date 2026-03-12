# F3: Real Manual QA - BLOCKED

**Date**: 2026-03-13
**Status**: BLOCKED - Requires hardware/sigrok environment

## Blocker Details

The `sigrokdecode` Python module is a runtime dependency that is not available in this development environment. Additionally, no DShot capture files (.sr) are available for testing.

## What Was Verified

### Automated Verification (Completed)
- [x] All Python files compile without syntax errors
- [x] Decoder class structure matches sigrokdecode API
- [x] All required methods are implemented
- [x] All constants are defined (DSHOT_TIMING, DSHOT_SPECIAL_COMMANDS, GCR_NIBBLE_MAP, etc.)
- [x] No forbidden features (DShot1200, extended telemetry, etc.)

### Manual Verification Required (Pending)
- [ ] Decoder loads in sigrok/PulseView without errors
- [ ] DShot150 frames decode correctly
- [ ] DShot300 frames decode correctly  
- [ ] DShot600 frames decode correctly
- [ ] Bidirectional eRPM telemetry decodes correctly
- [ ] CRC errors are detected and annotated
- [ ] Timing errors are detected and annotated
- [ ] Sample rate warnings are displayed
- [ ] Multi-channel (4 motors) works independently
- [ ] Special command names display correctly

## Test Commands (for manual execution)

```bash
# Install sigrok (if not already installed)
# Ubuntu/Debian: sudo apt install sigrok sigrok-cli
# Windows: Download from https://sigrok.org/wiki/Downloads

# Test DShot300 unidirectional
sigrok-cli -i dshot300_test.sr -P dshot:variant=DSHOT300:mode=unidirectional

# Test DShot300 bidirectional with eRPM
sigrok-cli -i dshot300_bidir.sr -P dshot:variant=DSHOT300:mode=bidirectional

# Test 4-channel setup
sigrok-cli -i dshot_4ch.sr -P dshot:variant=DSHOT600:mode=unidirectional:num_channels=4
```

## Integration Instructions

To use this decoder with the atk_libsigrokdecode library:

1. Copy the entire `decoders/dshot/` directory to the library's decoders folder
2. Ensure the decoder is registered in the library's decoder list
3. Restart PulseView/sigrok-cli to pick up the new decoder

## Expected Test Results

When run with valid DShot captures, the decoder should output:
- Bit annotations for each bit in the frame
- Frame annotations showing the raw 16-bit value
- Throttle value or special command name
- Telemetry request flag
- CRC status (OK/ERR)
- eRPM value (bidirectional mode only)
- Error/warning annotations for CRC errors, timing errors, sample rate warnings
