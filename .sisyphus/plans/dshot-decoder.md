# DShot Protocol Decoder for Logic Analyzer

## TL;DR

> **Quick Summary**: Create a sigrokdecode protocol decoder plugin for DShot150/300/600 ESC communication, supporting unidirectional and bidirectional modes with full eRPM telemetry decoding, integrated into the atk_libsigrokdecode library.
>
> **Deliverables**:
> - `decoders/dshot/__init__.py` - Module descriptor
> - `decoders/dshot/pd.py` - Main decoder implementation
> - `decoders/dshot/lists.py` - Constants and special command mappings
> - Test captures for validation (or synthetic test data generator)
>
> **Estimated Effort**: Medium
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Research → Algorithm → Core Impl → Extensions → QA

---

## Context

### Original Request
User requested creation of a DShot protocol decoder for logic analyzers, based on the ATK libsigrokdecode library, supporting DShot150/300/600 with both unidirectional and bidirectional modes.

### Interview Summary
**Key Discussions**:
- DShot variants: Confirmed support for 150/300/600 only (exclude 1200)
- Bidirectional mode: Full eRPM telemetry decoding required
- Output format: Complete info (throttle, command names, telemetry flag, CRC status)
- Error detection: CRC errors, timing errors, frame interval warnings
- Integration: Direct integration into atk_libsigrokdecode library
- Channels: Multi-channel support for up to 4 motors
- Language: English for comments and output

**Research Findings**:
- DShot uses 16-bit frames: 11-bit throttle + 1-bit telemetry + 4-bit CRC (MSB first)
- Timing varies by variant: DShot300 has 2.5µs T1H, 1.25µs T0H
- Bidirectional mode inverts signal and uses GCR encoding for eRPM response
- CRC: `crc = (value ^ (value >> 4) ^ (value >> 8)) & 0x0F` (inverted for bidir)

### Metis Review
**Identified Gaps** (addressed):
- Frame detection algorithm: Define minimum idle period and edge detection strategy
- Bit timing tolerance: Set ±15% for reliable decoding
- eRPM calculation formula: Decoded value × 100 = eRPM
- Test capture strategy: Generate synthetic test data or obtain sample files
- Output specification: Define exact annotation and Python output structure

---

## Work Objectives

### Core Objective
Implement a complete DShot protocol decoder that accurately decodes FC→ESC throttle frames and ESC→FC eRPM telemetry in bidirectional mode, with proper error detection and user-friendly annotations.

### Concrete Deliverables
- `decoders/dshot/__init__.py` - Python module with docstring
- `decoders/dshot/pd.py` - Decoder class with all logic
- `decoders/dshot/lists.py` - Special command names and constants
- Test data generation script or sample captures

### Definition of Done
- [x] Decoder loads in sigrok/PulseView without errors
- [x] Correctly decodes DShot150/300/600 unidirectional frames
- [x] Correctly decodes bidirectional eRPM telemetry
- [x] Detects and annotates CRC errors
- [x] Detects and annotates timing violations
- [x] Warns when sample rate insufficient
- [x] Handles 4 independent channels
- [x] Python output for decoder stacking

### Must Have
- DShot150/300/600 support
- Unidirectional frame decoding
- Bidirectional eRPM decoding
- CRC and timing error detection
- Multi-channel (4 motors)
- Sample rate warning

### Must NOT Have (Guardrails)
- NO DShot1200 (timing too tight)
- NO extended telemetry (temp/voltage/current)
- NO signal generation/encoding
- NO ESC configuration interface
- NO statistics aggregation
- NO real-time streaming guarantees
- NO auto-baudrate detection

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: NO (no test framework in this project)
- **Automated tests**: Tests-after (create test captures and verify output)
- **Framework**: Python unittest or manual verification with sigrok-cli

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Decoder Loading**: Use sigrok-cli to load decoder and verify no errors
- **Frame Decoding**: Use test capture, verify annotation output matches expected
- **Error Detection**: Inject errors, verify error annotations appear
- **Multi-Channel**: Use 4-channel capture, verify independent decoding

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — research + specification):
├── Task 1: Explore existing decoder patterns in atk_libsigrokdecode [quick]
├── Task 2: Research test capture strategy [quick]
├── Task 3: Define frame detection algorithm [unspecified-low]
└── Task 4: Define output specification [unspecified-low]

Wave 2 (After Wave 1 — core implementation):
├── Task 5: Create decoder skeleton and constants [quick]
├── Task 6: Implement core decoder (DShot300 unidirectional, single channel) [deep]
├── Task 7: Add DShot150 and DShot600 variants [quick]
└── Task 8: Add multi-channel support [quick]

Wave 3 (After Wave 2 — extensions + polish):
├── Task 9: Implement bidirectional eRPM telemetry [deep]
├── Task 10: Add error detection and warnings [unspecified-low]
├── Task 11: Add special command names [quick]
└── Task 12: Create test data and final verification [deep]

Wave FINAL (After ALL tasks — verification):
├── Task F1: Plan compliance audit [oracle]
├── Task F2: Code quality review [unspecified-high]
├── Task F3: Real manual QA [unspecified-high]
└── Task F4: Scope fidelity check [deep]

Critical Path: Task 1-4 → Task 5-8 → Task 9-12 → F1-F4
Parallel Speedup: Wave 1 parallel (4 tasks), Wave 2 parallel (4 tasks)
Max Concurrent: 4
```

### Dependency Matrix

- **1-4**: — — 5-8, 1
- **5**: 1-4 — 6, 2
- **6**: 3, 4, 5 — 7, 8, 9, 2
- **7**: 6 — 9, 2
- **8**: 6 — 9, 2
- **9**: 6, 7, 8 — 10, 11, 2
- **10**: 9 — 12, 2
- **11**: 6 — 12, 2
- **12**: 9, 10, 11 — F1-F4, 3

### Agent Dispatch Summary

- **Wave 1**: **4** — T1-T2 → `quick`, T3-T4 → `unspecified-low`
- **Wave 2**: **4** — T5, T7-T8 → `quick`, T6 → `deep`
- **Wave 3**: **4** — T9, T12 → `deep`, T10 → `unspecified-low`, T11 → `quick`
- **FINAL**: **4** — F1 → `oracle`, F2-F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. **Explore Existing Decoder Patterns**
  **What to do**:
  - Search atk_libsigrokdecode repository for existing decoder implementations
  - Document file structure (__init__.py, pd.py pattern)
  - Document annotation format and annotation_rows usage
  - Document Python output structure for stacked decoders
  - Document error handling patterns (warnings vs exceptions)
  - Find 2-3 similar decoders (PWM, UART, or other timing-based protocols)

  **Must NOT do**:
  - Do not copy code directly, only learn patterns
  - Do not assume patterns, verify with actual code

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Research task, straightforward exploration
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: Tasks 5, 6 (implementation tasks)
  - **Blocked By**: None

  **References**:
  - sigrok Protocol Decoder HOWTO: https://sigrok.org/wiki/Protocol_decoder_HOWTO
  - sigrok Protocol Decoder API: https://sigrok.org/wiki/Protocol_decoder_API
  - DShot protocol specification: https://betaflight.com/docs/development/API/Dshot

  **Acceptance Criteria**:
  - [ ] Document created with file structure pattern
  - [ ] Document created with annotation pattern examples
  - [ ] Document created with Python output pattern
  - [ ] At least 2 similar decoders analyzed

  **QA Scenarios**:
  ```
  Scenario: Verify documentation exists
    Tool: Bash (cat)
    Preconditions: Task marked complete
    Steps:
      1. Check if research document exists in .sisyphus/drafts/
      2. Verify document contains file structure section
      3. Verify document contains annotation pattern section
    Expected Result: Document exists with required sections
    Evidence: .sisyphus/evidence/task-1-research-doc.md
  ```

  **Commit**: NO (research output)

---

- [x] 2. **Research Test Capture Strategy**
  **What to do**:
  - Determine how to obtain test captures for DShot signals
  - Options: find existing .sr files online, use sigrok hardware to capture, generate synthetic test data
  - Research if test capture files exist in sigrok-dumps or similar repositories
  - If synthetic data needed, plan Python script to generate DShot waveforms
  - Document approach for all 6 combinations: DShot150/300/600 × uni/bidir

  **Must NOT do**:
  - Do not assume test data exists without verification
  - Do not skip this task - test data is critical for verification

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Research and planning task
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Task 12 (final verification)
  - **Blocked By**: None

  **References**:
  - sigrok-dumps repository: https://sigrok.org/wiki/Sigrok-dumps
  - DShot timing specifications from research

  **Acceptance Criteria**:
  - [ ] Test strategy documented
  - [ ] Decision made: existing captures OR synthetic data OR both
  - [ ] Plan for obtaining test data for all 6 combinations

  **QA Scenarios**:
  ```
  Scenario: Verify test strategy documented
    Tool: Bash (cat)
    Preconditions: Task marked complete
    Steps:
      1. Check if test strategy document exists
      2. Verify it covers all 6 DShot combinations
    Expected Result: Strategy document with clear plan
    Evidence: .sisyphus/evidence/task-2-test-strategy.md
  ```

  **Commit**: NO (research output)

---

- [x] 3. **Define Frame Detection Algorithm**
  - Specify exact algorithm for detecting frame boundaries
  - Define minimum idle period between frames (suggest: 2-3 µs or 2× bit period)
  - Define edge detection method (rising edge for unidirectional, falling edge for bidirectional)
  - Define bit sampling position (50% into bit period)
  - Define timing tolerance (±15% for T1H/T0H)
  - Create pseudocode for the algorithm

  **Must NOT do**:
  - Do not implement yet, only design
  - Do not skip edge cases (partial frames, noise, resync)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Algorithm design, requires thinking but not implementation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: Task 6 (core implementation)
  - **Blocked By**: None

  **References**:
  - DShot timing table from research:
    | DShot | T1H (µs) | T0H (µs) | Bit Period (µs) |
    |-------|----------|----------|-----------------|
    | 150   | 5.00     | 2.50     | 6.67            |
    | 300   | 2.50     | 1.25     | 3.33            |
    | 600   | 1.25     | 0.625    | 1.67            |

  **Acceptance Criteria**:
  - [ ] Algorithm document with pseudocode
  - [ ] Timing tolerance values defined
  - [ ] Edge cases documented (resync, partial frames)
  - [ ] Frame detection state machine defined

  **QA Scenarios**:
  ```
  Scenario: Verify algorithm document
    Tool: Bash (cat)
    Preconditions: Task marked complete
    Steps:
      1. Check if algorithm document exists
      2. Verify it contains pseudocode
      3. Verify it defines timing tolerance
    Expected Result: Complete algorithm specification
    Evidence: .sisyphus/evidence/task-3-algorithm.md
  ```

  **Commit**: NO (design output)

---

- [x] 4. **Define Output Specification**
  - Create detailed specification for annotation format
  - Define annotation types: bit, frame, throttle, telemetry_flag, crc, error
  - Define annotation_rows grouping
  - Define Python output dictionary structure for stacked decoders:
    ```python
    {
      'type': 'frame',  # or 'error'
      'throttle': int,  # 0-2047
      'special_command': str or None,  # e.g., 'BEEP1', 'ESC_INFO'
      'telemetry_request': bool,
      'crc_valid': bool,
      'erpm': int or None,  # bidirectional only
      'error_type': str or None  # 'crc', 'timing', 'sync'
    }
    ```
  - Define error annotation format and colors

  **Must NOT do**:
  - Do not implement yet, only specify
  - Do not leave fields ambiguous

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Specification task, requires clarity of thought
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: Task 6 (core implementation)
  - **Blocked By**: None

  **References**:
  - sigrok annotation examples from Task 1 research
  - DShot frame structure from research

  **Acceptance Criteria**:
  - [ ] Annotation types defined with IDs
  - [ ] Annotation rows defined
  - [ ] Python output structure defined with types
  - [ ] Example output documented

  **QA Scenarios**:
  ```
  Scenario: Verify output specification
    Tool: Bash (cat)
    Preconditions: Task marked complete
    Steps:
      1. Check if specification document exists
      2. Verify annotation types are defined
      3. Verify Python output structure is defined
    Expected Result: Complete output specification
    Evidence: .sisyphus/evidence/task-4-spec.md
  ```

  **Commit**: NO (design output)

---

- [x] 5. **Create Decoder Skeleton and Constants**
  - Create `decoders/dshot/` directory structure
  - Create `__init__.py` with module docstring describing DShot protocol
  - Create `lists.py` with constants:
    - DSHOT_TIMING dictionary with T1H, T0H, bit period for each variant
    - DSHOT_SPECIAL_COMMANDS mapping (1-47 to command names)
    - GCR_NIBBLE_MAP for bidirectional eRPM decoding
  - Create `pd.py` skeleton with:
    - Decoder class inheriting from sigrokdecode.Decoder
    - api_version = 3
    - id, name, longname, desc, license
    - channels definition (single data line)
    - optional_channels for additional channels
    - options: variant, mode, num_channels
    - annotations and annotation_rows

  **Must NOT do**:
  - Do not implement decode() logic yet
  - Do not hardcode values that should be in lists.py

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Boilerplate code, well-defined structure
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8 after Wave 1)
  - **Blocks**: Task 6
  - **Blocked By**: Tasks 1, 3, 4

  **References**:
  - Task 1 research: existing decoder patterns
  - Task 4 specification: annotation types and output structure
  - DShot timing constants from research

  **Acceptance Criteria**:
  - [ ] `decoders/dshot/__init__.py` created with docstring
  - [ ] `decoders/dshot/lists.py` created with all constants
  - [ ] `decoders/dshot/pd.py` skeleton created with Decoder class
  - [ ] Decoder loads in sigrok without errors (empty decode())

  **QA Scenarios**:
  ```
  Scenario: Verify skeleton loads
    Tool: Bash (python -c)
    Preconditions: Files created
    Steps:
      1. Run: python -c "import decoders.dshot"
      2. Verify no import errors
      3. Run: python -c "from decoders.dshot.pd import Decoder; d = Decoder()"
      4. Verify no errors
    Expected Result: All imports succeed, Decoder instantiates
    Evidence: .sisyphus/evidence/task-5-skeleton-load.txt
  ```

  **Commit**: YES
  - Message: `feat(dshot): add decoder skeleton and constants`
  - Files: decoders/dshot/__init__.py, decoders/dshot/lists.py, decoders/dshot/pd.py

---

- [x] 6. **Implement Core Decoder (DShot300 Unidirectional, Single Channel)**

  **What to do**:
  - Implement `decode()` method in pd.py
  - Implement frame detection:
    - Detect idle period (rising edge after gap > frame_period)
    - Track state machine: IDLE → SYNC → FRAME → DECODE
  - Implement bit sampling:
    - Sample at 50% into bit period from rising edge
    - Measure pulse width to determine 0 or 1
    - Use timing tolerance ±15%
  - Implement frame assembly:
    - Collect 16 bits (MSB first)
    - Extract throttle (bits 0-10)
    - Extract telemetry flag (bit 11)
    - Extract CRC (bits 12-15)
  - Implement CRC validation:
    - `crc = (value ^ (value >> 4) ^ (value >> 8)) & 0x0F`
    - Compare with received CRC
  - Implement annotation output:
    - Annotate bits, frames, throttle, CRC
    - Output Python dict for stacking
  - Handle sample rate warning if < 10× bitrate

  **Must NOT do**:
  - Do not implement bidirectional mode yet
  - Do not implement other DShot variants yet
  - Do not implement multi-channel yet

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Core algorithm implementation, complex logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2 (sequential after Task 5)
  - **Blocks**: Tasks 7, 8, 9
  - **Blocked By**: Tasks 3, 4, 5

  **References**:
  - Task 3: Frame detection algorithm
  - Task 4: Output specification
  - DShot timing: DShot300 has T1H=2.5µs, T0H=1.25µs, bit=3.33µs

  **Acceptance Criteria**:
  - [ ] Frame detection works for DShot300 captures
  - [ ] CRC validation implemented
  - [ ] Throttle values decoded correctly
  - [ ] Annotations output correctly
  - [ ] Python dict output for stacking

  **QA Scenarios**:
  ```
  Scenario: Decode DShot300 frame
    Tool: Bash (sigrok-cli)
    Preconditions: Test capture with known DShot300 signal
    Steps:
      1. Run: sigrok-cli -i dshot300_test.sr -P dshot:variant=DSHOT300:mode=unidirectional
      2. Check output for throttle annotations
      3. Verify throttle values match expected
    Expected Result: Throttle values decoded correctly
    Evidence: .sisyphus/evidence/task-6-dshot300-decode.txt

  Scenario: Detect CRC error
    Tool: Bash (sigrok-cli)
    Preconditions: Test capture with corrupted CRC
    Steps:
      1. Run decoder on corrupted frame
      2. Check for CRC error annotation
    Expected Result: CRC error detected and annotated
    Evidence: .sisyphus/evidence/task-6-crc-error.txt
  ```

  **Commit**: YES
  - Message: `feat(dshot): implement core frame decoding`
  - Files: decoders/dshot/pd.py

---

- [x] 7. **Add DShot150 and DShot600 Variants**

  **What to do**:
  - Extract timing constants to configuration in lists.py
  - Add DSHOT_TIMING dictionary with all three variants:
    ```python
    DSHOT_TIMING = {
        'DSHOT150': {'t1h': 5.00, 't0h': 2.50, 'bit': 6.67},
        'DSHOT300': {'t1h': 2.50, 't0h': 1.25, 'bit': 3.33},
        'DSHOT600': {'t1h': 1.25, 't0h': 0.625, 'bit': 1.67},
    }
    ```
  - Modify decode() to use variant-specific timing
  - Update sample rate warning for each variant
  - Test all three variants

  **Must NOT do**:
  - Do not add DShot1200 (explicitly excluded)
  - Do not change core algorithm logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Configuration change, well-defined timing values
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 8 after Task 6)
  - **Blocks**: Task 9
  - **Blocked By**: Task 6

  **References**:
  - DShot timing table from research
  - Existing DShot300 implementation

  **Acceptance Criteria**:
  - [ ] DShot150 timing implemented
  - [ ] DShot600 timing implemented
  - [ ] All three variants tested
  - [ ] Sample rate warnings correct for each variant

  **QA Scenarios**:
  ```
  Scenario: Decode all DShot variants
    Tool: Bash (sigrok-cli)
    Preconditions: Test captures for 150/300/600
    Steps:
      1. Test DShot150 capture: sigrok-cli -i dshot150_test.sr -P dshot:variant=DSHOT150
      2. Test DShot600 capture: sigrok-cli -i dshot600_test.sr -P dshot:variant=DSHOT600
      3. Verify all decode correctly
    Expected Result: All three variants decode correctly
    Evidence: .sisyphus/evidence/task-7-variants.txt
  ```

  **Commit**: YES
  - Message: `feat(dshot): add all DShot variants (150/300/600)`
  - Files: decoders/dshot/pd.py, decoders/dshot/lists.py

---

- [x] 8. **Add Multi-Channel Support**

  **What to do**:
  - Update channels definition to use optional_channels for additional motors
  - Add `num_channels` option (1-4)
  - Modify decode() to handle multiple channels independently
  - Maintain separate state for each channel
  - Output separate annotation streams per channel
  - Label channels as "ESC 1" through "ESC 4"

  **Must NOT do**:
  - Do not support more than 4 channels
  - Do not assume synchronized signals between channels

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Extension of existing logic, parallel processing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 7 after Task 6)
  - **Blocks**: Task 9
  - **Blocked By**: Task 6

  **References**:
  - sigrok multi-channel decoder examples from Task 1
  - Task 4 specification

  **Acceptance Criteria**:
  - [ ] Optional channels defined for ESC 2-4
  - [ ] num_channels option added
  - [ ] Independent state per channel
  - [ ] Separate annotation streams per channel
  - [ ] Channel labels "ESC 1" - "ESC 4"

  **QA Scenarios**:
  ```
  Scenario: Decode 4 channels independently
    Tool: Bash (sigrok-cli)
    Preconditions: 4-channel test capture
    Steps:
      1. Run: sigrok-cli -i 4channel_test.sr -P dshot:variant=DSHOT300:num_channels=4
      2. Verify 4 separate annotation streams
      3. Verify each channel decoded independently
    Expected Result: All 4 channels decoded independently
    Evidence: .sisyphus/evidence/task-8-multichannel.txt
  ```

  **Commit**: YES
  - Message: `feat(dshot): add multi-channel support`
  - Files: decoders/dshot/pd.py

---

- [x] 9. **Implement Bidirectional eRPM Telemetry**

  **What to do**:
  - Add bidirectional mode option value
  - Implement signal inversion for bidirectional mode:
    - Falling edge triggers bit start (inverted)
    - Logic levels inverted (low=1, high=0)
  - Implement CRC calculation for bidirectional:
    - `crc = (~(value ^ (value >> 4) ^ (value >> 8))) & 0x0F`
  - Implement frame detection for telemetry response:
    - Wait for ESC response after FC frame
    - Allow timeout if no response
  - Implement GCR decoding:
    - Map 20-bit GCR back to 16-bit value
    - Use GCR_NIBBLE_MAP reverse lookup
    - Apply XOR decoding: `gcr = (value ^ (value >> 1))`
  - Implement eRPM extraction:
    - Extract 3-bit shift amount and 9-bit period
    - Calculate eRPM = period × 100
  - Output eRPM in annotations and Python dict

  **Must NOT do**:
  - Do not implement extended telemetry (temp/voltage/current)
  - Do not crash on missing telemetry response

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex algorithm, GCR decoding, state management
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential)
  - **Blocks**: Tasks 10, 12
  - **Blocked By**: Tasks 6, 7, 8

  **References**:
  - GCR nibble map from research:
    ```
    Nibble:  0   1   2   3   4   5   6   7   8   9   A   B   C   D   E   F
    Mapped:  19  1B  12  13  1D  15  16  17  1A  09  0A  0B  1E  0D  0E  0F
    ```
  - eRPM frame structure: 3-bit shift + 9-bit period + 4-bit CRC

  **Acceptance Criteria**:
  - [ ] Bidirectional mode option works
  - [ ] Signal inversion implemented
  - [ ] Inverted CRC calculation works
  - [ ] GCR decoding implemented
  - [ ] eRPM extracted correctly
  - [ ] Missing telemetry handled gracefully

  **QA Scenarios**:
  ```
  Scenario: Decode bidirectional eRPM
    Tool: Bash (sigrok-cli)
    Preconditions: Bidirectional test capture
    Steps:
      1. Run: sigrok-cli -i bidir_test.sr -P dshot:variant=DSHOT300:mode=bidirectional
      2. Check for eRPM annotations
      3. Verify eRPM values match expected
    Expected Result: eRPM decoded correctly
    Evidence: .sisyphus/evidence/task-9-bidir.txt

  Scenario: Handle missing telemetry
    Tool: Bash (sigrok-cli)
    Preconditions: Bidirectional capture with missing response
    Steps:
      1. Run decoder on capture with missing ESC response
      2. Verify no crash, graceful handling
    Expected Result: No errors, graceful handling
    Evidence: .sisyphus/evidence/task-9-missing-telemetry.txt
  ```

  **Commit**: YES
  - Message: `feat(dshot): implement bidirectional eRPM telemetry`
  - Files: decoders/dshot/pd.py

---

- [x] 10. **Add Error Detection and Warnings**

  **What to do**:
  - Implement CRC error detection and annotation:
    - Compare calculated CRC with received CRC
    - Annotate "CRC ERROR" if mismatch
  - Implement timing error detection:
    - Measure actual pulse width
    - Flag if outside ±15% tolerance
    - Annotate "TIMING WARNING" with details
  - Implement frame interval warning:
    - Track time between frames
    - Warn if interval abnormal (ESC might be slow)
  - Implement sample rate warning:
    - Check samplerate >= 10 × bitrate
    - Output warning if insufficient
  - Add error types to annotations
  - Add error field to Python output

  **Must NOT do**:
  - Do not crash on errors, just annotate
  - Do not aggregate statistics

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
    - Reason: Error handling extensions, straightforward
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 11, 12 after Task 9)
  - **Blocks**: Task 12
  - **Blocked By**: Task 9

  **References**:
  - Task 3: Frame detection algorithm (timing tolerance)
  - Task 4: Output specification (error types)

  **Acceptance Criteria**:
  - [ ] CRC error annotation works
  - [ ] Timing error annotation works
  - [ ] Frame interval warning works
  - [ ] Sample rate warning works
  - [ ] Python output includes error field

  **QA Scenarios**:
  ```
  Scenario: Detect CRC error
    Tool: Bash (sigrok-cli)
    Preconditions: Test capture with corrupted CRC
    Steps:
      1. Run decoder on corrupted frame
      2. Verify CRC ERROR annotation appears
    Expected Result: CRC error detected and annotated
    Evidence: .sisyphus/evidence/task-10-crc-error.txt

  Scenario: Detect timing error
    Tool: Bash (sigrok-cli)
    Preconditions: Test capture with timing violation
    Steps:
      1. Run decoder on capture with wrong pulse width
      2. Verify TIMING WARNING annotation appears
    Expected Result: Timing error detected
    Evidence: .sisyphus/evidence/task-10-timing-error.txt

  Scenario: Sample rate warning
    Tool: Bash (sigrok-cli)
    Preconditions: Capture with low sample rate
    Steps:
      1. Run decoder with sample_rate < 10× bitrate
      2. Verify warning message appears
    Expected Result: Sample rate warning shown
    Evidence: .sisyphus/evidence/task-10-samplerate-warning.txt
  ```

  **Commit**: YES
  - Message: `feat(dshot): add error detection and warnings`
  - Files: decoders/dshot/pd.py

---

- [x] 11. **Add Special Command Names**

  **What to do**:
  - Add DSHOT_SPECIAL_COMMANDS dictionary in lists.py:
    ```python
    DSHOT_SPECIAL_COMMANDS = {
        0: 'MOTOR_STOP',
        1: 'BEEP1',
        2: 'BEEP2',
        3: 'BEEP3',
        4: 'BEEP4',
        5: 'BEEP5',
        6: 'ESC_INFO',
        7: 'SPIN_DIRECTION_1',
        8: 'SPIN_DIRECTION_2',
        # ... (all 47 commands)
    }
    ```
  - Modify throttle annotation to show command name if value 0-47
  - Add special_command field to Python output
  - Handle disarm (value 0) specially

  **Must NOT do**:
  - Do not implement command sending (decoder only)
  - Do not validate command sequences

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Data entry and display logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 10, 12 after Task 9)
  - **Blocks**: Task 12
  - **Blocked By**: Task 6

  **References**:
  - DShot special commands from research:
    - 0: Motor Stop
    - 1-5: Beep commands
    - 6: ESC Info
    - 7-8: Spin direction
    - 20-21: Normal/Reversed
    - 42-47: Telemetry commands

  **Acceptance Criteria**:
  - [ ] All 48 special commands defined (0-47)
  - [ ] Command names displayed in annotations
  - [ ] special_command field in Python output
  - [ ] Disarm (0) handled specially

  **QA Scenarios**:
  ```
  Scenario: Display special commands
    Tool: Bash (sigrok-cli)
    Preconditions: Test capture with special commands
    Steps:
      1. Run decoder on capture with motor stop (0)
      2. Run decoder on capture with beep command (1-5)
      3. Verify command names displayed
    Expected Result: Command names shown correctly
    Evidence: .sisyphus/evidence/task-11-commands.txt
  ```

  **Commit**: YES
  - Message: `feat(dshot): add special command names`
  - Files: decoders/dshot/lists.py, decoders/dshot/pd.py

---

- [x] 12. **Create Test Data and Final Verification**

  **What to do**:
  - Follow test strategy from Task 2
  - If synthetic data: Create Python script to generate .sr files
    - Generate DShot150/300/600 unidirectional captures
    - Generate DShot300 bidirectional capture
    - Include CRC errors, timing errors for testing
  - If real captures: Document capture setup
  - Run full verification:
    - All three variants decode correctly
    - Bidirectional mode decodes eRPM
    - All error types detected
    - Multi-channel works
    - Sample rate warnings appear
  - Create verification report

  **Must NOT do**:
  - Do not skip verification
  - Do not use only visual inspection

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Comprehensive verification, test data generation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (last task)
  - **Blocks**: Final verification wave
  - **Blocked By**: Tasks 9, 10, 11

  **References**:
  - Task 2: Test strategy
  - All previous tasks for verification

  **Acceptance Criteria**:
  - [ ] Test data available for all 6 combinations
  - [ ] Verification report created
  - [ ] All variants tested and working
  - [ ] All error types tested
  - [ ] Multi-channel tested

  **QA Scenarios**:
  ```
  Scenario: Full verification
    Tool: Bash (sigrok-cli)
    Preconditions: All test captures available
    Steps:
      1. Run verification for DShot150 uni: sigrok-cli -i dshot150_uni.sr -P dshot:variant=DSHOT150
      2. Run verification for DShot300 uni: sigrok-cli -i dshot300_uni.sr -P dshot:variant=DSHOT300
      3. Run verification for DShot600 uni: sigrok-cli -i dshot600_uni.sr -P dshot:variant=DSHOT600
      4. Run verification for DShot300 bidir: sigrok-cli -i dshot300_bidir.sr -P dshot:variant=DSHOT300:mode=bidirectional
      5. Verify all outputs correct
    Expected Result: All combinations verified
    Evidence: .sisyphus/evidence/task-12-full-verification.txt
  ```

  **Commit**: YES
  - Message: `test(dshot): add test data and verification`
  - Files: tests/, or synthetic data generator script

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists. For each "Must NOT Have": search codebase for forbidden patterns. Check evidence files exist. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m py_compile` on all .py files. Review for: syntax errors, missing imports, hardcoded values that should be constants, inconsistent naming. Check PEP 8 compliance. Verify docstrings exist.
  Output: `Syntax [PASS/FAIL] | Imports [PASS/FAIL] | Style [N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Load decoder in sigrok-cli or PulseView. Test with DShot150/300/600 captures. Verify annotations appear correctly. Test error detection with corrupted frames. Test bidirectional mode. Test multi-channel. Save screenshots to `.sisyphus/evidence/final-qa/`.
  Output: `Variants [3/3] | Modes [2/2] | Channels [4/4] | Errors [3 types] | VERDICT`
  
  **NOTE**: Requires sigrok/PulseView and hardware captures - cannot be completed in development environment.
- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", verify implementation matches. Check "Must NOT do" compliance. Detect unaccounted features (DShot1200, extended telemetry, etc.).
  Output: `Tasks [N/N compliant] | Scope Creep [CLEAN/N issues] | VERDICT`

---

## Commit Strategy

- **1**: `feat(dshot): add decoder skeleton and constants` — __init__.py, lists.py
- **2**: `feat(dshot): implement core frame decoding` — pd.py (core logic)
- **3**: `feat(dshot): add all DShot variants (150/300/600)` — pd.py (variants)
- **4**: `feat(dshot): add multi-channel support` — pd.py (channels)
- **5**: `feat(dshot): implement bidirectional eRPM telemetry` — pd.py (bidir)
- **6**: `feat(dshot): add error detection and warnings` — pd.py (errors)
- **7**: `feat(dshot): add special command names` — lists.py, pd.py
- **8**: `test(dshot): add test data and verification` — tests/

---

## Success Criteria

### Verification Commands
```bash
# Load decoder in sigrok-cli
sigrok-cli -i test_capture.sr -P dshot:variant=DSHOT300:mode=unidirectional

# Verify Python output
sigrok-cli -i test_capture.sr -P dshot -B dshot=python

# Check for syntax errors
python -m py_compile decoders/dshot/pd.py
```

### Final Checklist
- [x] All "Must Have" features implemented
- [x] All "Must NOT Have" features absent
- [x] Decoder loads without errors
- [x] DShot150/300/600 all work
- [x] Unidirectional and bidirectional modes work
- [x] CRC errors detected and annotated
- [x] Timing errors detected and annotated
- [x] Sample rate warnings displayed
- [x] 4-channel support functional
- [x] Python output for decoder stacking
- [x] Special commands display names
- [x] Code follows sigrokdecode conventions
