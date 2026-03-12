# DShot Frame Detection Algorithm

## Overview

This document defines the frame detection algorithm for the DShot decoder plugin, including the state machine, timing parameters, and edge case handling strategies.

---

## 1. Frame Detection State Machine

### States

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│    ┌───────┐     rising edge      ┌───────┐                │
│    │ IDLE  │ ──────────────────▶  │ SYNC  │                │
│    └───────┘     after gap > 2×   └───────┘                │
│        ▲         bit period          │                     │
│        │                              │ bit_count < 16     │
│        │                              ▼                     │
│        │        frame complete   ┌─────────┐               │
│        │    ◀─────────────────── │  FRAME  │               │
│        │                         └─────────┘               │
│        │                              │                     │
│        │                              │ bit_count == 16    │
│        │                              ▼                     │
│        │                         ┌──────────┐              │
│        └─────────────────────────│ DECODE   │              │
│             after decode         └──────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### State Descriptions

| State  | Description                                                                 |
|--------|-----------------------------------------------------------------------------|
| IDLE   | Waiting for a valid frame start (rising edge after sufficient quiet period) |
| SYNC   | Detected potential frame start, validating first bit                        |
| FRAME  | Actively receiving and sampling bits (1-16)                                 |
| DECODE | Frame complete, validate CRC and extract throttle/telemetry values          |

### State Transitions

```
IDLE → SYNC:    Rising edge detected AND quiet period > 2 × bit_period
SYNC → FRAME:   First valid bit edge detected within timing tolerance
SYNC → IDLE:    Timeout or invalid timing on first bit
FRAME → FRAME:  Valid bit edge detected, increment bit_counter
FRAME → DECODE: bit_counter == 16
FRAME → IDLE:   Timeout, noise detected, or timing violation
DECODE → IDLE:  Always (after processing, success or failure)
```

---

## 2. Timing Tolerance Values

### Base Timing by DShot Variant

| DShot | Bitrate  | Bit Period (µs) | T1H Nominal (µs) | T0H Nominal (µs) |
|-------|----------|-----------------|------------------|------------------|
| 150   | 150kbps  | 6.67            | 5.00             | 2.50             |
| 300   | 300kbps  | 3.33            | 2.50             | 1.25             |
| 600   | 600kbps  | 1.67            | 1.25             | 0.625            |

### Tolerance Ranges (±15%)

| DShot | Bit Period Min | Bit Period Max | T1H Min | T1H Max | T0H Min | T0H Max |
|-------|----------------|----------------|---------|---------|---------|---------|
| 150   | 5.67 µs        | 7.67 µs        | 4.25 µs | 5.75 µs | 2.13 µs | 2.88 µs |
| 300   | 2.83 µs        | 3.83 µs        | 2.13 µs | 2.88 µs | 1.06 µs | 1.44 µs |
| 600   | 1.42 µs        | 1.92 µs        | 1.06 µs | 1.44 µs | 0.53 µs | 0.72 µs |

### Decision Threshold

**Logic 1 vs Logic 0 Threshold: ~56.25% of bit period**

```
threshold = bit_period × 0.5625

| DShot | Threshold (µs) |
|-------|----------------|
| 150   | 3.75           |
| 300   | 1.875          |
| 600   | 0.9375         |

Decision Rule:
  IF high_time > threshold THEN bit = 1
  ELSE bit = 0
```

### Idle Detection Threshold

```
idle_threshold = 2 × bit_period  (minimum gap to detect frame start)

| DShot | Idle Threshold (µs) |
|-------|---------------------|
| 150   | 13.34               |
| 300   | 6.66                |
| 600   | 3.34                |
```

---

## 3. Bit Sampling Algorithm

### Pseudocode

```pseudocode
FUNCTION sample_bit(rising_edge_time, falling_edge_time, bit_period):
    // Calculate high time (T1H or T0H)
    high_time = falling_edge_time - rising_edge_time
    
    // Calculate threshold at 56.25% of bit period
    threshold = bit_period * 0.5625
    
    // Determine bit value
    IF high_time > threshold:
        RETURN 1
    ELSE:
        RETURN 0

FUNCTION get_sample_point(rising_edge_time, bit_period):
    // Sample at 50% into the bit period from rising edge
    // This gives maximum margin from both edges
    RETURN rising_edge_time + (bit_period * 0.5)
```

### Sampling Strategy

**Option A: Edge-Based Measurement (Preferred for GPIO polling)**
1. Record timestamp of rising edge
2. Record timestamp of falling edge
3. Calculate high_time = falling - rising
4. Compare high_time against threshold

**Option B: Level Sampling (For DMA/capture modes)**
1. Sample at 50% of bit period after rising edge
2. If level is HIGH → logic 1
3. If level is LOW → logic 0

---

## 4. Frame Detection Algorithm

### Pseudocode

```pseudocode
CONSTANTS:
    BIT_COUNT = 16
    CRC_BITS = 4
    THROTTLE_BITS = 11
    TELEMETRY_BIT = 1

STATE_MACHINE:
    state = IDLE
    bit_counter = 0
    frame_buffer[16] = {0}
    last_rising_edge = 0
    last_falling_edge = 0
    last_edge_time = 0

FUNCTION process_edge(edge_type, timestamp, dshot_variant):
    bit_period = get_bit_period(dshot_variant)
    idle_threshold = bit_period * 2
    max_bit_period = bit_period * 1.15  // +15% tolerance
    
    SWITCH state:
        CASE IDLE:
            IF edge_type == RISING:
                gap = timestamp - last_edge_time
                IF gap > idle_threshold:
                    state = SYNC
                    last_rising_edge = timestamp
                ELSE:
                    // Noise - stay in IDLE
                    last_edge_time = timestamp
        
        CASE SYNC:
            IF edge_type == FALLING:
                high_time = timestamp - last_rising_edge
                IF is_valid_pulse(high_time, bit_period):
                    last_falling_edge = timestamp
                    state = FRAME
                    bit_counter = 0
                    frame_buffer[0] = determine_bit(high_time, bit_period)
                    bit_counter = 1
                ELSE:
                    // Invalid pulse - resync
                    state = IDLE
            ELSE:
                // Unexpected rising edge - resync
                state = IDLE
            last_edge_time = timestamp
        
        CASE FRAME:
            IF edge_type == RISING:
                // Validate bit period
                period = timestamp - last_rising_edge
                IF period > max_bit_period * 2:
                    // Gap too long - lost sync
                    state = IDLE
                    RETURN
                last_rising_edge = timestamp
            ELSE IF edge_type == FALLING:
                high_time = timestamp - last_rising_edge
                IF NOT is_valid_pulse(high_time, bit_period):
                    // Invalid pulse - resync
                    state = IDLE
                    RETURN
                
                IF bit_counter < BIT_COUNT:
                    frame_buffer[bit_counter] = determine_bit(high_time, bit_period)
                    bit_counter++
                    
                    IF bit_counter == BIT_COUNT:
                        state = DECODE
                        decode_frame(frame_buffer)
                        state = IDLE
                        bit_counter = 0
                        
            last_edge_time = timestamp

FUNCTION is_valid_pulse(high_time, bit_period):
    t0h_min = bit_period * 0.375 * 0.85  // T0H - 15%
    t1h_max = bit_period * 0.75 * 1.15   // T1H + 15%
    
    // Valid if within any acceptable pulse width range
    // With gap between T0H_max and T1H_min, we can be more precise
    RETURN (high_time >= t0h_min AND high_time <= t1h_max)

FUNCTION determine_bit(high_time, bit_period):
    threshold = bit_period * 0.5625
    IF high_time > threshold:
        RETURN 1
    ELSE:
        RETURN 0
```

---

## 5. Frame Decoding Algorithm

### Pseudocode

```pseudocode
FUNCTION decode_frame(frame_buffer[16]):
    // Extract fields (MSB first)
    throttle = 0
    FOR i = 0 TO 10:
        throttle = (throttle << 1) | frame_buffer[i]
    
    telemetry_request = frame_buffer[11]
    
    received_crc = 0
    FOR i = 12 TO 15:
        received_crc = (received_crc << 1) | frame_buffer[i]
    
    // Calculate CRC
    // CRC = (throttle value XOR telemetry bit) shifted and XORed
    crc_data = (throttle << 1) | telemetry_request
    calculated_crc = calculate_crc4(crc_data)
    
    IF calculated_crc == received_crc:
        RETURN SUCCESS(throttle, telemetry_request)
    ELSE:
        RETURN CRC_ERROR

FUNCTION calculate_crc4(data_12bit):
    // DShot CRC calculation:
    // CRC is computed over 12 bits (11 throttle + 1 telemetry)
    // CRC = 4-bit value from XOR operations
    crc = 0
    
    FOR i = 11 DOWNTO 0:
        IF (data_12bit >> i) & 1:
            crc = crc XOR CRC_TABLE[i]
    
    RETURN crc

// Alternative: CRC calculated per nibble
FUNCTION calculate_crc4_nibble(throttle, telemetry):
    // Combine throttle and telemetry into 12 bits
    data = (throttle << 1) | telemetry
    
    // XOR each nibble
    crc = (data >> 8) XOR ((data >> 4) & 0x0F) XOR (data & 0x0F)
    crc = crc & 0x0F
    
    RETURN crc
```

---

## 6. Edge Case Handling

### 6.1 Partial Frames (Incomplete 16 Bits)

```
Detection:
  - Timeout while in FRAME state
  - Unexpected gap between bits (exceeds 2× bit period)

Handling:
  1. Reset state machine to IDLE
  2. Clear frame_buffer
  3. Reset bit_counter to 0
  4. Log partial frame event for diagnostics
  
Recovery:
  - Wait for next valid frame start (rising edge after idle period)
  - No partial frame data should be processed
```

### 6.2 Noise / Spurious Edges

```
Detection:
  - Pulse width outside valid range (T0H_min to T1H_max)
  - Bit period significantly outside tolerance
  - Multiple edges within one bit period

Filtering Strategies:
  1. Minimum pulse width filter: Reject pulses shorter than T0H_min × 0.8
  2. Maximum pulse width filter: Reject pulses longer than T1H_max × 1.2
  3. Debounce: Require stable state for minimum duration

Implementation:
  FUNCTION is_noise_pulse(pulse_width, bit_period):
      t0h_min = bit_period * 0.375 * 0.85
      t1h_max = bit_period * 0.75 * 1.15
      
      IF pulse_width < t0h_min * 0.7:
          RETURN TRUE  // Too short - likely noise
      IF pulse_width > t1h_max * 1.3:
          RETURN TRUE  // Too long - likely glitch
      RETURN FALSE
```

### 6.3 Resync After Error

```
Resync Conditions:
  1. CRC validation failure
  2. Partial frame timeout
  3. Noise detection during frame
  4. Bit timing violation

Resync Procedure:
  1. Immediately transition to IDLE state
  2. Clear all frame-related state (buffer, counter)
  3. Reset timing measurements
  4. Wait for valid idle period (> 2× bit period)
  5. Accept next valid frame start

State Preservation:
  - DShot variant (150/300/600) is preserved
  - Statistics may be updated (error count)
  - No throttle value changes until valid frame received
```

### 6.4 Bidirectional Telemetry Response (DShot Bidir)

```
Note: This decoder handles ESC-to-FC telemetry responses, not FC-to-ESC commands.

Detection:
  - In bidirectional mode, ESC sends telemetry response after each command
  - Response timing: ESC starts transmission ~30µs after command ends
  - Response format: Same 16-bit structure with CRC

Handling:
  IF bidirectional_mode:
      // After sending command frame
      wait_for_response(timeout = 50µs)  // Wait for ESC response
      
      IF response_detected:
          decode_telemetry_response()
      ELSE:
          // Missing response - could indicate:
          // 1. ESC not powered
          // 2. Signal integrity issue
          // 3. ESC doesn't support telemetry
          log_missing_telemetry_response()
          
Timeout Values:
  - Response start window: 20-100µs after command
  - Response frame duration: Same as command frame
  - Total response timeout: command_frame + 150µs
```

### 6.5 Glitch Handling During Frame

```
Detection:
  - Multiple edges within single bit period
  - Inconsistent timing between consecutive bits

Strategies:
  1. Edge Count Validation:
     - Each bit should have exactly 2 edges (rising + falling)
     - Extra edges indicate signal integrity issues
     
  2. Timing Consistency Check:
     - Bit periods should be consistent within ±15%
     - Large variations indicate problems
     
  3. Majority Voting (optional):
     - Sample bit value multiple times
     - Use majority vote for decision
```

---

## 7. Minimum Sample Rate Calculation

### Nyquist Requirement

```
For reliable edge detection, minimum sample rate must exceed:
  sample_rate >= 2 × highest_frequency

But for pulse width measurement, we need more samples per pulse:
  sample_rate >= samples_per_pulse × pulse_frequency

Where:
  samples_per_pulse = minimum samples to reliably measure pulse width
  pulse_frequency = 1 / shortest_pulse
```

### DShot 600 Requirements (Most Demanding)

```
Shortest pulse: T0H = 0.625µs (for logic 0 at DShot 600)

For reliable pulse width measurement:
  - Minimum 4 samples per shortest pulse recommended
  - sample_rate >= 4 / 0.625µs = 6.4 MHz

For high precision:
  - 8-10 samples per shortest pulse
  - sample_rate >= 10 / 0.625µs = 16 MHz

Recommended Sample Rates:
  
  | Application      | Sample Rate | Samples/T0H_600 |
  |------------------|-------------|-----------------|
  | Minimum viable   | 6.4 MHz     | 4               |
  | Good quality     | 10 MHz      | 6.25            |
  | High precision   | 16 MHz      | 10              |
  | Analysis/debug   | 20+ MHz     | 12.5+           |
```

### Sample Rate Table by Variant

| DShot | Shortest Pulse | Min Rate (4×) | Good Rate (8×) | High Quality (12×) |
|-------|----------------|---------------|----------------|-------------------|
| 150   | 2.50 µs        | 1.6 MHz       | 3.2 MHz        | 4.8 MHz           |
| 300   | 1.25 µs        | 3.2 MHz       | 6.4 MHz        | 9.6 MHz           |
| 600   | 0.625 µs       | 6.4 MHz       | 12.8 MHz       | 19.2 MHz          |

---

## 8. CRC Calculation Detail

### CRC-4 Algorithm

```
DShot uses a simple 4-bit CRC calculated from the 12 data bits.

Input:  12 bits (throttle[10:0] + telemetry)
Output: 4-bit CRC

Method 1 - Bit-by-bit XOR:
  crc = 0
  data = (throttle << 1) | telemetry
  
  for bit in data (MSB first):
      crc = (crc << 1) | ((crc >> 3) XOR bit)
      crc = crc & 0x0F
  
  Result: crc[3:0]

Method 2 - Nibble XOR (simpler, equivalent):
  data = (throttle << 1) | telemetry
  
  crc = (data >> 8) ^ ((data >> 4) & 0x0F) ^ (data & 0x0F)
  crc = crc & 0x0F
  
  Result: crc[3:0]

Verification Example:
  throttle = 0x400 (bit 10 set = 1024)
  telemetry = 0
  
  data = 0x800  (12 bits)
  
  nibble[3] = 0x8
  nibble[2] = 0x0
  nibble[1] = 0x0
  nibble[0] = 0x0
  
  crc = 0x8 ^ 0x0 ^ 0x0 = 0x8
```

---

## 9. Timeout Values

| Event                     | DShot150 | DShot300 | DShot600 | Calculation          |
|---------------------------|----------|----------|----------|----------------------|
| Bit timeout (max gap)     | 15.3 µs  | 7.7 µs   | 3.8 µs   | bit_period × 2.3     |
| Frame timeout (total)     | 200 µs   | 100 µs   | 50 µs    | frame_time × 1.9     |
| Idle detection            | 13.3 µs  | 6.7 µs   | 3.3 µs   | bit_period × 2       |
| Resync delay              | 20 µs    | 10 µs    | 5 µs     | bit_period × 3       |
| Telemetry response window | 150 µs   | 150 µs   | 150 µs   | Fixed (ESC spec)     |

---

## 10. Data Structures

### Frame Buffer

```c
typedef struct {
    uint16_t raw;           // Raw 16-bit frame value
    uint16_t throttle;      // Extracted throttle (0-2047)
    bool     telemetry;     // Telemetry request flag
    uint8_t  crc_received;  // CRC from frame
    uint8_t  crc_calculated;// Calculated CRC
    bool     valid;         // Frame validity flag
} dshot_frame_t;
```

### Decoder State

```c
typedef struct {
    dshot_state_t state;        // Current state machine state
    uint8_t       bit_counter;  // Bits received in current frame
    uint16_t      frame_buffer; // Accumulating frame bits
    uint32_t      last_rising;  // Last rising edge timestamp
    uint32_t      last_falling; // Last falling edge timestamp
    uint32_t      last_edge;    // Last edge timestamp (any)
    dshot_variant_t variant;    // DShot150/300/600
    dshot_frame_t  frame;       // Last decoded frame
    // Statistics
    uint32_t      frames_ok;    // Successful frame count
    uint32_t      crc_errors;   // CRC error count
    uint32_t      frame_errors; // Other frame errors
} dshot_decoder_t;
```

---

## Summary

This algorithm provides robust frame detection for DShot150/300/600 protocols with:

1. **Precise timing tolerance** (±15%) for reliable bit detection
2. **State machine** with clear transitions and error handling
3. **Edge case handling** for noise, partial frames, and resync scenarios
4. **Minimum sample rate guidance** for implementation planning
5. **CRC validation** ensuring data integrity

The design prioritizes reliability over throughput, with explicit error detection and recovery mechanisms suitable for embedded systems with limited resources.
