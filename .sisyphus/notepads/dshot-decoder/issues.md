# DShot Decoder - Issues and Blockers

## 2026-03-13 Session

### F3: Real Manual QA - BLOCKED

**Status**: Cannot complete in development environment

**Requirement**:
- Load decoder in sigrok-cli or PulseView
- Test with DShot150/300/600 captures
- Verify annotations appear correctly
- Test error detection with corrupted frames
- Test bidirectional mode
- Test multi-channel
- Save screenshots to `.sisyphus/evidence/final-qa/`

**Blocker**:
- `sigrokdecode` module is a runtime dependency not available in development environment
- No DShot capture files (.sr) available for testing
- No hardware logic analyzer connected

**Resolution Path**:
1. Install sigrok/PulseView on a system with the decoder
2. Obtain DShot capture files or connect hardware
3. Run manual tests as documented in learnings.md
4. Save evidence to `.sisyphus/evidence/final-qa/`

**Test Commands**:
```bash
# Test DShot300 unidirectional
sigrok-cli -i capture.sr -P dshot:variant=DSHOT300:mode=unidirectional

# Test DShot300 bidirectional with eRPM  
sigrok-cli -i capture.sr -P dshot:variant=DSHOT300:mode=bidirectional

# Test 4-channel setup
sigrok-cli -i capture.sr -P dshot:variant=DSHOT600:mode=unidirectional:num_channels=4
```

**Alternative**: Generate synthetic test data using Python script (see task-2-test-strategy.md)
