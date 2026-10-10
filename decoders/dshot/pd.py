'''
DShot Protocol Decoder Implementation

This module implements the sigrokdecode Decoder class for the DShot protocol.
'''

import sigrokdecode as srd
from .lists import (
    DSHOT_TIMING,
    DSHOT_SPECIAL_COMMANDS,
    THROTTLE_MIN,
    THROTTLE_MAX,
    GCR_NIBBLE_MAP,
    GCR_NIBBLE_REVERSE,
    ERROR_TYPES,
    WARNING_TYPES,
    MIN_SAMPLE_RATE_MULTIPLIER,
    TIMING_TOLERANCE,
    BIT_THRESHOLD,
    MIN_IDLE_BIT_PERIODS,
    ERPM_SHIFT_BITS,
    ERPM_PERIOD_BITS,
)


# Annotation type IDs (must match annotation tuple order)
ANN_BIT = 0
ANN_FRAME = 1
ANN_THROTTLE = 2
ANN_TELEMETRY = 3
ANN_CRC = 4
ANN_SPECIAL_CMD = 5
ANN_ERPM = 6
ANN_ERROR = 7
ANN_WARNING = 8
ANN_SUMMARY = 9


class Decoder(srd.Decoder):
    '''
    DShot (Digital Shot) Protocol Decoder

    Decodes DShot150, DShot300, and DShot600 signals in both
    unidirectional and bidirectional modes.
    '''

    api_version = 3
    id = 'dshot'
    name = 'DShot'
    longname = 'DShot ESC Protocol'
    desc = 'Digital Shot protocol for FC-ESC communication (DShot150/300/600, uni/bidirectional).'
    license = 'gplv3+'
    tags = ['ESC', 'RC']

    inputs = ['logic']
    outputs = ['dshot']

    # Primary channel (ESC 1 / Motor 1)
    channels = (
        {'id': 'data', 'name': 'DATA', 'desc': 'DShot data signal'},
    )

    # Optional channels for additional motors (ESC 2-4)
    optional_channels = (
        {'id': 'data2', 'name': 'DATA2', 'desc': 'DShot data signal (ESC 2)'},
        {'id': 'data3', 'name': 'DATA3', 'desc': 'DShot data signal (ESC 3)'},
        {'id': 'data4', 'name': 'DATA4', 'desc': 'DShot data signal (ESC 4)'},
    )

    # User-configurable options
    options = (
        {'id': 'variant', 'desc': 'DShot variant',
         'default': 'DSHOT300', 'values': ('DSHOT150', 'DSHOT300', 'DSHOT600')},
        {'id': 'mode', 'desc': 'Operating mode',
         'default': 'unidirectional', 'values': ('unidirectional', 'bidirectional')},
        {'id': 'num_channels', 'desc': 'Number of channels (motors)',
         'default': 1, 'values': (1, 2, 3, 4)},
    )

    # Annotation types
    annotations = (
        ('bit', 'Bit'),
        ('frame', 'Frame'),
        ('throttle', 'Throttle'),
        ('telemetry', 'Telemetry request'),
        ('crc', 'CRC status'),
        ('special-cmd', 'Special command'),
        ('erpm', 'eRPM'),
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('summary', 'Summary'),
    )

    # Annotation rows for grouping
    annotation_rows = (
        ('bits', 'Bits', (ANN_BIT,)),
        ('frames', 'Frames', (ANN_FRAME,)),
        ('summary-row', 'Summary', (ANN_SUMMARY,)),
        ('values', 'Values', (ANN_THROTTLE, ANN_TELEMETRY, ANN_CRC, ANN_SPECIAL_CMD, ANN_ERPM)),
        ('errors', 'Errors', (ANN_ERROR, ANN_WARNING)),
    )

    def __init__(self, **kwargs):
        '''Initialize decoder state.'''
        self.samplerate = None
        self.variant = None
        self.mode = None
        self.num_channels = None
        self.timing = None

        # State machine state for each channel
        self.states = []  # Will be initialized in start()

        # Output registrations
        self.out_ann = None
        self.out_python = None

    def metadata(self, key, value):
        '''Receive metadata from the backend.'''
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value

    def reset(self):
        '''Reset decoder state for a new decode pass.'''
        # Re-initialize channel states
        self._init_channel_states()

    def start(self):
        '''Register outputs and perform initialization.'''
        # Register output types
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.out_python = self.register(srd.OUTPUT_PYTHON)

        # Get user options
        self.variant = self.options['variant']
        self.mode = self.options['mode']
        self.num_channels = self.options['num_channels']

        # Get timing parameters for selected variant
        self.timing = DSHOT_TIMING[self.variant]

        # Check sample rate
        self._check_sample_rate()

        # Determine active channels based on num_channels and has_channel()
        self.active_channels = [0]  # Channel 0 is always active
        for i in range(1, self.num_channels):
            if self.has_channel(i):
                self.active_channels.append(i)

        # Initialize channel states
        self._init_channel_states()
    def _init_channel_states(self):
        '''Initialize state machine state for each active channel.'''
        self.states = []
        for _ in range(self.num_channels):
            self.states.append({
                'state': 'IDLE',
                'bit_count': 0,
                'frame_bits': [],
                'last_edge_sample': 0,
                'frame_start_sample': 0,
                'rising_edge_sample': 0,
                'last_pin': None,
                # Bidirectional telemetry state
                'telemetry_requested': False,
                'telemetry_start_sample': 0,
                'falling_edge_sample': 0,
                'last_fc_frame': None,
            })
    def _check_sample_rate(self):
        '''Check if sample rate is sufficient for reliable decoding.'''
        if self.samplerate is None:
            return

        bitrate = self.timing['bitrate']
        min_sample_rate = bitrate * MIN_SAMPLE_RATE_MULTIPLIER

        if self.samplerate < min_sample_rate:
            # Emit a warning annotation at sample 0
            self.put(0, 0, self.out_ann,
                     [ANN_WARNING, ['Warning: Sample rate {} Hz is below '
                                    'recommended minimum {} Hz for {}'.format(
                                        self.samplerate, min_sample_rate, self.variant)]])

    def decode(self):
        '''
        Main decode method.

        This method is called by the sigrokdecode backend to decode samples.
        Uses self.wait() for edge-triggered sample handling.
        Supports multiple channels (up to 4 motors).
        '''
        # Get timing parameters in samples
        bit_period_s = self.timing['bit_period_us'] / 1e6  # Convert to seconds
        samples_per_bit = int(bit_period_s * self.samplerate) if self.samplerate else 0
        idle_threshold_samples = int(samples_per_bit * MIN_IDLE_BIT_PERIODS)
        threshold_samples = int(samples_per_bit * BIT_THRESHOLD)

        # Valid pulse width range (with tolerance)
        t0h_min_samples = int(samples_per_bit * 0.375 * (1 - TIMING_TOLERANCE))  # T0H - 15%
        t1h_max_samples = int(samples_per_bit * 0.75 * (1 + TIMING_TOLERANCE))   # T1H + 15%
        max_bit_gap_samples = int(samples_per_bit * 2.3)  # Max gap between bits

        # Bidirectional telemetry timing
        # ESC responds ~30us after FC frame, with timeout window of ~100us
        telemetry_timeout_samples = int(self.samplerate * 100e-6) if self.samplerate else 0
        telemetry_start_window = int(self.samplerate * 30e-6) if self.samplerate else 0  # Min wait before ESC response

        # State machine constants
        STATE_IDLE = 'IDLE'
        STATE_SYNC = 'SYNC'
        STATE_FRAME = 'FRAME'
        STATE_DECODE = 'DECODE'
        STATE_WAITING_TELEMETRY = 'WAITING_TELEMETRY'
        STATE_TELEMETRY_FRAME = 'TELEMETRY_FRAME'
        STATE_DECODE_TELEMETRY = 'DECODE_TELEMETRY'

        # Check if bidirectional mode is enabled
        is_bidirectional = (self.mode == 'bidirectional')
        while True:
            # Build wait condition for all active channels
            wait_cond = {ch: 'e' for ch in self.active_channels}

            # Wait for edge on any active channel
            pins = self.wait(wait_cond)
            current_sample = self.samplenum

            # Process each active channel
            for ch in self.active_channels:
                ch_state = self.states[ch]
                current_pin = pins[ch]
                state = ch_state['state']
                last_pin = ch_state['last_pin']
                rising_edge_sample = ch_state['rising_edge_sample']

                # Skip if no edge detected (shouldn't happen with 'e' trigger)
                if last_pin is None:
                    ch_state['last_pin'] = current_pin
                    continue

                # Detect edge type
                is_rising = (last_pin == 0 and current_pin == 1)
                is_falling = (last_pin == 1 and current_pin == 0)
                ch_state['last_pin'] = current_pin

                # === IDLE STATE ===
                if state == STATE_IDLE:
                    if is_rising:
                        gap = current_sample - ch_state['last_edge_sample']
                        if gap > idle_threshold_samples:
                            ch_state['state'] = STATE_SYNC
                            ch_state['rising_edge_sample'] = current_sample
                            ch_state['frame_start_sample'] = current_sample
                        else:
                            ch_state['last_edge_sample'] = current_sample

                # === SYNC STATE ===
                elif state == STATE_SYNC:
                    if is_falling:
                        high_time = current_sample - ch_state['rising_edge_sample']
                        if t0h_min_samples <= high_time <= t1h_max_samples:
                            ch_state['state'] = STATE_FRAME
                            ch_state['bit_count'] = 1
                            bit_value = 1 if high_time > threshold_samples else 0
                            ch_state['frame_bits'] = [bit_value]
                            ch_state['last_edge_sample'] = current_sample
                            # Emit bit annotation
                            self.put(ch_state['frame_start_sample'], current_sample, self.out_ann,
                                     [ANN_BIT, ['CH{} Bit 0: {}'.format(ch + 1, bit_value), str(bit_value)]])
                        else:
                            ch_state['state'] = STATE_IDLE
                            ch_state['bit_count'] = 0
                            ch_state['frame_bits'] = []
                            ch_state['last_edge_sample'] = current_sample
                    elif is_rising:
                        ch_state['state'] = STATE_IDLE
                        ch_state['last_edge_sample'] = current_sample

                # === FRAME STATE ===
                elif state == STATE_FRAME:
                    if is_rising:
                        ch_state['rising_edge_sample'] = current_sample
                        gap = current_sample - ch_state['last_edge_sample']
                        if gap > max_bit_gap_samples:
                            ch_state['state'] = STATE_IDLE
                            ch_state['bit_count'] = 0
                            ch_state['frame_bits'] = []
                            ch_state['last_edge_sample'] = current_sample
                            continue
                        ch_state['last_edge_sample'] = current_sample

                    elif is_falling:
                        high_time = current_sample - ch_state['rising_edge_sample']
                        if not (t0h_min_samples <= high_time <= t1h_max_samples):
                            ch_state['state'] = STATE_IDLE
                            ch_state['bit_count'] = 0
                            ch_state['frame_bits'] = []
                            ch_state['last_edge_sample'] = current_sample
                            continue

                        bit_value = 1 if high_time > threshold_samples else 0
                        ch_state['frame_bits'].append(bit_value)
                        ch_state['bit_count'] += 1
                        ch_state['last_edge_sample'] = current_sample

                        bit_idx = ch_state['bit_count'] - 1
                        self.put(ch_state['rising_edge_sample'], current_sample, self.out_ann,
                                 [ANN_BIT, ['CH{} Bit {}: {}'.format(ch + 1, bit_idx, bit_value), str(bit_value)]])

                        if ch_state['bit_count'] >= 16:
                            ch_state['state'] = STATE_DECODE

                # === DECODE STATE ===
                elif state == STATE_DECODE:
                    fc_frame = self._decode_frame(ch_state, ch)
                    ch_state['bit_count'] = 0
                    ch_state['frame_bits'] = []
                    ch_state['last_edge_sample'] = current_sample

                    # In bidirectional mode with telemetry request, wait for ESC response
                    if is_bidirectional and fc_frame and fc_frame.get('telemetry', 0):
                        ch_state['state'] = STATE_WAITING_TELEMETRY
                        ch_state['telemetry_requested'] = True
                        ch_state['telemetry_start_sample'] = current_sample
                        ch_state['last_fc_frame'] = fc_frame
                    else:
                        ch_state['state'] = STATE_IDLE

                # === WAITING_TELEMETRY STATE ===
                # Wait for ESC response after FC frame (bidirectional mode)
                # ESC responds with INVERTED signal: falling edge = bit start
                elif state == STATE_WAITING_TELEMETRY:
                    time_since_frame = current_sample - ch_state['telemetry_start_sample']

                    # Check for timeout (no ESC response)
                    if time_since_frame > telemetry_timeout_samples:
                        ch_state['state'] = STATE_IDLE
                        ch_state['telemetry_requested'] = False
                        ch_state['last_fc_frame'] = None
                        # Emit warning about missing telemetry
                        self.put(ch_state['telemetry_start_sample'], current_sample, self.out_ann,
                                 [ANN_WARNING, ['CH{} No ESC telemetry response'.format(ch + 1), 'NO_TEL_RESP']])
                        continue

                    # In bidirectional mode, ESC response starts with FALLING edge (inverted signal)
                    # Wait for falling edge to start receiving telemetry frame
                    if is_falling:
                        # Check if enough time has passed for ESC to start responding
                        if time_since_frame >= telemetry_start_window:
                            ch_state['state'] = STATE_TELEMETRY_FRAME
                            ch_state['bit_count'] = 1
                            ch_state['frame_bits'] = []
                            ch_state['frame_start_sample'] = current_sample  # Telemetry frame starts here
                            ch_state['falling_edge_sample'] = current_sample
                            ch_state['last_edge_sample'] = current_sample

                # === TELEMETRY_FRAME STATE ===
                # Receive ESC telemetry frame (21 bits, GCR encoded, INVERTED signal)
                # Inverted signal: falling edge = bit start, low pulse = logic 1, high pulse = logic 0
                elif state == STATE_TELEMETRY_FRAME:
                    if is_falling:
                        # Falling edge = start of new bit in inverted signal
                        ch_state['falling_edge_sample'] = current_sample
                        gap = current_sample - ch_state['last_edge_sample']
                        if gap > max_bit_gap_samples:
                            # Timeout - lost sync
                            ch_state['state'] = STATE_IDLE
                            ch_state['bit_count'] = 0
                            ch_state['frame_bits'] = []
                            ch_state['telemetry_requested'] = False
                            ch_state['last_edge_sample'] = current_sample
                            continue
                        ch_state['last_edge_sample'] = current_sample

                    elif is_rising:
                        # Rising edge = end of bit in inverted signal
                        # Measure LOW time (time signal was LOW before rising)
                        low_time = current_sample - ch_state['falling_edge_sample']

                        # Validate pulse width
                        if not (t0h_min_samples <= low_time <= t1h_max_samples):
                            ch_state['state'] = STATE_IDLE
                            ch_state['bit_count'] = 0
                            ch_state['frame_bits'] = []
                            ch_state['telemetry_requested'] = False
                            ch_state['last_edge_sample'] = current_sample
                            continue

                        # INVERTED LOGIC: low_time > threshold means LONG low = logic 0
                        # Short low (like T0H in normal) = logic 1, Long low (like T1H) = logic 0
                        # Inverted: short pulse = 1, long pulse = 0
                        bit_value = 0 if low_time > threshold_samples else 1
                        ch_state['frame_bits'].append(bit_value)
                        ch_state['bit_count'] += 1
                        ch_state['last_edge_sample'] = current_sample

                        bit_idx = ch_state['bit_count'] - 1
                        self.put(ch_state['falling_edge_sample'], current_sample, self.out_ann,
                                 [ANN_BIT, ['CH{} TelBit {}: {}'.format(ch + 1, bit_idx, bit_value), 'T{}'.format(bit_value)]])

                        # Telemetry frame is 21 bits (GCR encoded 16-bit value)
                        if ch_state['bit_count'] >= 21:
                            ch_state['state'] = STATE_DECODE_TELEMETRY

                # === DECODE_TELEMETRY STATE ===
                elif state == STATE_DECODE_TELEMETRY:
                    self._decode_telemetry_frame(ch_state, ch)
                    ch_state['state'] = STATE_IDLE
                    ch_state['bit_count'] = 0
                    ch_state['frame_bits'] = []
                    ch_state['telemetry_requested'] = False
                    ch_state['last_fc_frame'] = None
                    ch_state['last_edge_sample'] = current_sample
    def _decode_frame(self, channel_state, channel_idx=0):
        '''
        Decode a complete 16-bit DShot frame.

        Frame structure (MSB first):
        - Bits 0-10: Throttle value (11 bits)
        - Bit 11: Telemetry request
        - Bits 12-15: CRC (4 bits)
        '''
        frame_bits = channel_state['frame_bits']
        frame_start = channel_state['frame_start_sample']

        if len(frame_bits) != 16:
            return  # Should not happen

        # Assemble 16-bit value (MSB first)
        raw_value = 0
        for bit in frame_bits:
            raw_value = (raw_value << 1) | bit

        # Extract fields
        throttle = (raw_value >> 5) & 0x7FF  # Bits 0-10 (11 bits)
        telemetry = (raw_value >> 4) & 0x01   # Bit 11
        received_crc = raw_value & 0x0F       # Bits 12-15 (4 bits)

        # Calculate CRC
        calculated_crc = self.calculate_crc(throttle, telemetry)
        crc_valid = (calculated_crc == received_crc)

        # Find frame end (approximate - last bit falling edge)
        frame_end = self.samplenum
        ch_label = 'ESC {}'.format(channel_idx + 1)

        # Emit frame annotation
        self.put(frame_start, frame_end, self.out_ann,
                 [ANN_FRAME, ['{} Frame: 0x{:04X}'.format(ch_label, raw_value), '0x{:04X}'.format(raw_value)]])

        # Emit summary annotation (throttle + telemetry flag in one line)
        tel_flag = 'T' if telemetry else '-'
        if throttle < THROTTLE_MIN:
            cmd_name = self.get_special_command_name(throttle)
            summary_text = '{}: {} [{}]'.format(ch_label, cmd_name, tel_flag)
            summary_short = '{} [{}]'.format(cmd_name, tel_flag)
        else:
            summary_text = '{}: {} [{}]'.format(ch_label, throttle, tel_flag)
            summary_short = '{} [{}]'.format(throttle, tel_flag)
        self.put(frame_start, frame_end, self.out_ann,
                 [ANN_SUMMARY, [summary_text, summary_short]])

        # Emit throttle annotation
        if throttle < THROTTLE_MIN:
            # Special command
            cmd_name = self.get_special_command_name(throttle)
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_SPECIAL_CMD, ['{} Special: {}'.format(ch_label, cmd_name), cmd_name]])
        else:
            # Normal throttle
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_THROTTLE, ['{} Throttle: {}'.format(ch_label, throttle), str(throttle)]])

        # Emit telemetry annotation
        tel_str = 'Telemetry: Yes' if telemetry else 'Telemetry: No'
        self.put(frame_start, frame_end, self.out_ann,
                 [ANN_TELEMETRY, ['{} {}'.format(ch_label, tel_str), 'TEL' if telemetry else 'NO_TEL']])

        # Emit CRC annotation
        if crc_valid:
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_CRC, ['{} CRC OK: 0x{:X}'.format(ch_label, received_crc), 'CRC OK']])
        else:
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_CRC, ['{} CRC ERR: got 0x{:X}, exp 0x{:X}'.format(
                         ch_label, received_crc, calculated_crc), 'CRC ERR']])
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_ERROR, ['{} CRC mismatch: got 0x{:X}, expected 0x{:X}'.format(
                         ch_label, received_crc, calculated_crc), 'CRC Error']])

        # Emit Python output for stacked decoders
        frame_data = {
            'raw': raw_value,
            'throttle': throttle,
            'telemetry': telemetry,
            'crc_received': received_crc,
            'crc_calculated': calculated_crc,
            'crc_valid': crc_valid,
            'start_sample': frame_start,
            'end_sample': frame_end,
            'variant': self.variant,
            'channel': channel_idx,
        }
        self.put(frame_start, frame_end, self.out_python, frame_data)

        return frame_data  # Return frame data for bidirectional mode
    def put(self, start_sample, end_sample, output_id, data):
        '''
        Emit decoded data.

        This is a convenience wrapper around the parent put() method.
        '''
        super().put(start_sample, end_sample, output_id, data)

    def calculate_crc(self, throttle, telemetry):
        '''
        Calculate DShot CRC from throttle and telemetry bits.

        CRC = (value ^ (value >> 4) ^ (value >> 8)) & 0x0F
        where value = (throttle << 1) | telemetry

        Args:
            throttle: 11-bit throttle value (0-2047)
            telemetry: Telemetry request flag (0 or 1)

        Returns:
            4-bit CRC value (0-15)
        '''
        value = (throttle << 1) | (1 if telemetry else 0)
        crc = (value ^ (value >> 4) ^ (value >> 8)) & 0x0F
        return crc

    def calculate_crc_bidirectional(self, throttle, telemetry):
        '''
        Calculate DShot CRC for bidirectional mode (inverted).

        CRC = (~(value ^ (value >> 4) ^ (value >> 8))) & 0x0F
        where value = (throttle << 1) | telemetry

        Args:
            throttle: 11-bit throttle value (0-2047)
            telemetry: Telemetry request flag (0 or 1)

        Returns:
            4-bit CRC value (0-15)
        '''
        value = (throttle << 1) | (1 if telemetry else 0)
        crc = (~(value ^ (value >> 4) ^ (value >> 8))) & 0x0F
        return crc

    def get_special_command_name(self, throttle):
        '''
        Get special command name for throttle value if applicable.

        Args:
            throttle: Throttle value (0-2047)

        Returns:
            Command name string if throttle is 0-47, None otherwise
        '''
        if throttle < THROTTLE_MIN:
            return DSHOT_SPECIAL_COMMANDS.get(throttle, 'UNKNOWN_{}'.format(throttle))
        return None

    def decode_erpm(self, raw_value):
        '''
        Decode eRPM from bidirectional telemetry frame.

        The telemetry frame is 16 bits (after GCR decoding):
        - Bits 13-15 (3 bits): Shift count (extends period range)
        - Bits 4-12 (9 bits): Period base
        - Bits 0-3 (4 bits): CRC

        eRPM = (period_base << shift_count) * 100

        Args:
            raw_value: 16-bit raw value from GCR-decoded telemetry frame

        Returns:
            Tuple of (eRPM, shift_count, period_base, crc_valid)
        '''
        # Extract shift count (bits 13-15, MSB first)
        shift_count = (raw_value >> 13) & 0x07
        # Extract period base (bits 4-12, 9 bits)
        period_base = (raw_value >> 4) & 0x1FF
        # Extract received CRC (bits 0-3)
        received_crc = raw_value & 0x0F

        # Calculate expected CRC (over bits 4-15, the 12-bit value without CRC)
        value_without_crc = raw_value >> 4
        expected_crc = (value_without_crc ^ (value_without_crc >> 4) ^ (value_without_crc >> 8)) & 0x0F

        crc_valid = (received_crc == expected_crc)

        # Calculate eRPM
        period = period_base << shift_count
        erpm = period * 100  # eRPM = period * 100

        return (erpm, shift_count, period_base, crc_valid)

    def decode_gcr(self, gcr_value):
        '''
        Decode GCR-encoded value to original 16-bit value.

        GCR encoding maps 16-bit values to 20-bit values for more robust
        transmission. The ESC sends 21 bits: 1 leading bit + 20 GCR bits.
        This function reverses that mapping.

        Args:
            gcr_value: 21-bit GCR-encoded value (first bit is ignored)

        Returns:
            16-bit decoded value, or None if decoding fails
        '''
        # The ESC sends 21 bits: first bit is 0 (sync), then 20 GCR bits
        # Extract the 20 GCR bits (mask off the leading bit)
        gcr_20bit = gcr_value & 0xFFFFF  # Keep lower 20 bits

        # GCR decoding: XOR each bit with the previous bit
        # This reverses the GCR encoding transformation
        decoded = gcr_20bit ^ (gcr_20bit >> 1)

        # Extract 4 groups of 5-bit symbols and map back to 4-bit nibbles
        # GCR encoding: nibble[0] -> symbol[0], nibble[1] -> symbol[1], etc.
        # Bits are stored MSB first, so nibble[0] is highest bits
        result = 0
        for i in range(4):
            # Extract 5-bit symbol (from LSB side, i=0 is LSB nibble)
            gcr_symbol = (decoded >> (i * 5)) & 0x1F
            if gcr_symbol in GCR_NIBBLE_REVERSE:
                result |= GCR_NIBBLE_REVERSE[gcr_symbol] << (i * 4)
            else:
                return None  # Invalid GCR encoding

        return result

    def _decode_telemetry_frame(self, channel_state, channel_idx=0):
        '''
        Decode a 21-bit GCR-encoded ESC telemetry frame.

        The frame contains:
        - 1 leading sync bit (ignored)
        - 20 bits of GCR-encoded data

        After GCR decoding, the 16-bit value contains:
        - Bits 13-15: Shift count (3 bits)
        - Bits 4-12: Period base (9 bits)
        - Bits 0-3: CRC (4 bits)

        Args:
            channel_state: Channel state dictionary
            channel_idx: Channel index for annotations
        '''
        frame_bits = channel_state['frame_bits']
        frame_start = channel_state['frame_start_sample']
        fc_frame = channel_state.get('last_fc_frame', {})

        if len(frame_bits) != 21:
            return  # Should not happen

        # Assemble 21-bit GCR value (MSB first)
        gcr_value = 0
        for bit in frame_bits:
            gcr_value = (gcr_value << 1) | bit

        # Decode GCR to 16-bit value
        decoded_value = self.decode_gcr(gcr_value)

        frame_end = self.samplenum
        ch_label = 'ESC {}'.format(channel_idx + 1)

        if decoded_value is None:
            # GCR decoding failed
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_ERROR, ['{} GCR decode failed'.format(ch_label), 'GCR ERR']])
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_FRAME, ['{} Telemetry: GCR Error'.format(ch_label), 'TEL_GCR_ERR']])
            return

        # Decode eRPM from the decoded value
        erpm, shift_count, period_base, crc_valid = self.decode_erpm(decoded_value)

        # Emit frame annotation
        self.put(frame_start, frame_end, self.out_ann,
                 [ANN_FRAME, ['{} Telemetry: 0x{:04X}'.format(ch_label, decoded_value), '0x{:04X}'.format(decoded_value)]])

        # Emit summary annotation for telemetry (eRPM value)
        if crc_valid:
            summary_text = '{}: eRPM {} [OK]'.format(ch_label, erpm)
            summary_short = '{} [OK]'.format(erpm)
        else:
            summary_text = '{}: eRPM {} [CRC ERR]'.format(ch_label, erpm)
            summary_short = '{} [ERR]'.format(erpm)
        self.put(frame_start, frame_end, self.out_ann,
                 [ANN_SUMMARY, [summary_text, summary_short]])

        # Emit eRPM annotation
        if crc_valid:
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_ERPM, ['{} eRPM: {}'.format(ch_label, erpm), str(erpm)]])
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_CRC, ['{} CRC OK'.format(ch_label), 'CRC OK']])
        else:
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_ERPM, ['{} eRPM: {} (CRC ERR)'.format(ch_label, erpm), str(erpm)]])
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_CRC, ['{} CRC ERR'.format(ch_label), 'CRC ERR']])

        # Emit Python output for stacked decoders
        telemetry_data = {
            'type': 'telemetry',
            'raw_gcr': gcr_value,
            'decoded': decoded_value,
            'erpm': erpm,
            'shift_count': shift_count,
            'period_base': period_base,
            'crc_valid': crc_valid,
            'start_sample': frame_start,
            'end_sample': frame_end,
            'variant': self.variant,
            'channel': channel_idx,
            'fc_frame': fc_frame,  # Link to FC frame that requested this telemetry
        }
        self.put(frame_start, frame_end, self.out_python, telemetry_data)

        return telemetry_data
