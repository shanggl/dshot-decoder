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
    )

    # Annotation rows for grouping
    annotation_rows = (
        ('bits', 'Bits', (ANN_BIT,)),
        ('frames', 'Frames', (ANN_FRAME,)),
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
                     [ANN_WARNING, [f'Warning: Sample rate {self.samplerate} Hz is below '
                                    f'recommended minimum {min_sample_rate} Hz for {self.variant}']])

    def decode(self):
        '''
        Main decode method.

        This method is called by the sigrokdecode backend to decode samples.
        Uses self.wait() for edge-triggered sample handling.
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

        # State machine constants
        STATE_IDLE = 'IDLE'
        STATE_SYNC = 'SYNC'
        STATE_FRAME = 'FRAME'
        STATE_DECODE = 'DECODE'

        # Channel state aliases (single channel for now)
        channel_state = self.states[0]

        # Initialize edge tracking
        last_pin_state = None
        rising_edge_sample = 0

        while True:
            # Wait for samples with edge conditions
            # Pattern: (condition,) - wait for rising or falling edge
            (data,) = self.wait({0: 'e'})  # 'e' = edge on channel 0
            current_sample = self.samplenum
            current_pin = data

            # Get current channel state
            state = channel_state['state']

            # Detect edge type
            if last_pin_state is None:
                last_pin_state = current_pin
                continue

            is_rising = (last_pin_state == 0 and current_pin == 1)
            is_falling = (last_pin_state == 1 and current_pin == 0)
            last_pin_state = current_pin

            # === IDLE STATE ===
            if state == STATE_IDLE:
                if is_rising:
                    # Check if gap since last edge is sufficient
                    gap = current_sample - channel_state['last_edge_sample']
                    if gap > idle_threshold_samples:
                        # Valid frame start detected
                        channel_state['state'] = STATE_SYNC
                        rising_edge_sample = current_sample
                        channel_state['frame_start_sample'] = current_sample
                    else:
                        # Noise or within previous frame, stay in IDLE
                        channel_state['last_edge_sample'] = current_sample

            # === SYNC STATE ===
            elif state == STATE_SYNC:
                if is_falling:
                    high_time = current_sample - rising_edge_sample
                    # Validate pulse width
                    if t0h_min_samples <= high_time <= t1h_max_samples:
                        # Valid first bit, transition to FRAME
                        channel_state['state'] = STATE_FRAME
                        channel_state['bit_count'] = 1
                        channel_state['frame_bits'] = [1 if high_time > threshold_samples else 0]
                        channel_state['last_edge_sample'] = current_sample
                        # Emit bit annotation
                        bit_value = channel_state['frame_bits'][0]
                        self.put(rising_edge_sample, current_sample, self.out_ann,
                                 [ANN_BIT, [f'Bit {bit_value}', f'{bit_value}']])
                    else:
                        # Invalid pulse width, resync
                        channel_state['state'] = STATE_IDLE
                        channel_state['bit_count'] = 0
                        channel_state['frame_bits'] = []
                        channel_state['last_edge_sample'] = current_sample
                else:
                    # Unexpected rising edge in SYNC, restart
                    channel_state['state'] = STATE_IDLE
                    channel_state['last_edge_sample'] = current_sample

            # === FRAME STATE ===
            elif state == STATE_FRAME:
                if is_rising:
                    rising_edge_sample = current_sample
                    # Check for timeout/gap between bits
                    gap = current_sample - channel_state['last_edge_sample']
                    if gap > max_bit_gap_samples:
                        # Lost sync, reset to IDLE
                        channel_state['state'] = STATE_IDLE
                        channel_state['bit_count'] = 0
                        channel_state['frame_bits'] = []
                        channel_state['last_edge_sample'] = current_sample
                        continue
                    channel_state['last_edge_sample'] = current_sample

                elif is_falling:
                    high_time = current_sample - rising_edge_sample
                    # Validate pulse width
                    if not (t0h_min_samples <= high_time <= t1h_max_samples):
                        # Invalid pulse - noise, resync
                        channel_state['state'] = STATE_IDLE
                        channel_state['bit_count'] = 0
                        channel_state['frame_bits'] = []
                        channel_state['last_edge_sample'] = current_sample
                        continue

                    # Determine bit value
                    bit_value = 1 if high_time > threshold_samples else 0
                    channel_state['frame_bits'].append(bit_value)
                    channel_state['bit_count'] += 1
                    channel_state['last_edge_sample'] = current_sample

                    # Emit bit annotation
                    bit_idx = channel_state['bit_count'] - 1
                    self.put(rising_edge_sample, current_sample, self.out_ann,
                             [ANN_BIT, [f'Bit {bit_idx}: {bit_value}', f'{bit_value}']])

                    # Check if frame complete (16 bits)
                    if channel_state['bit_count'] >= 16:
                        channel_state['state'] = STATE_DECODE

            # === DECODE STATE ===
            elif state == STATE_DECODE:
                # Process the frame
                self._decode_frame(channel_state)
                # Reset to IDLE
                channel_state['state'] = STATE_IDLE
                channel_state['bit_count'] = 0
                channel_state['frame_bits'] = []
                channel_state['last_edge_sample'] = current_sample

    def _decode_frame(self, channel_state):
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
        # We'll use the last bit position from frame_bits
        frame_end = self.samplenum

        # Emit frame annotation
        self.put(frame_start, frame_end, self.out_ann,
                 [ANN_FRAME, [f'Frame: 0x{raw_value:04X}', f'0x{raw_value:04X}']])

        # Emit throttle annotation
        if throttle < THROTTLE_MIN:
            # Special command
            cmd_name = self.get_special_command_name(throttle)
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_SPECIAL_CMD, [f'Special: {cmd_name}', f'{cmd_name}']])
        else:
            # Normal throttle
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_THROTTLE, [f'Throttle: {throttle}', f'{throttle}']])

        # Emit telemetry annotation
        tel_str = 'Telemetry: Yes' if telemetry else 'Telemetry: No'
        self.put(frame_start, frame_end, self.out_ann,
                 [ANN_TELEMETRY, [tel_str, 'TEL' if telemetry else 'NO_TEL']])

        # Emit CRC annotation
        if crc_valid:
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_CRC, [f'CRC OK: 0x{received_crc:X}', f'CRC OK']])
        else:
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_CRC, [f'CRC ERR: got 0x{received_crc:X}, exp 0x{calculated_crc:X}', f'CRC ERR']])
            self.put(frame_start, frame_end, self.out_ann,
                     [ANN_ERROR, [f'CRC mismatch: got 0x{received_crc:X}, expected 0x{calculated_crc:X}', 'CRC Error']])

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
        }
        self.put(frame_start, frame_end, self.out_python, frame_data)

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
            return DSHOT_SPECIAL_COMMANDS.get(throttle, f'UNKNOWN_{throttle}')
        return None

    def decode_erpm(self, raw_value):
        '''
        Decode eRPM from bidirectional telemetry frame.

        The telemetry frame is 16 bits:
        - Bits 0-2: Shift count (3 bits)
        - Bits 3-11: Period base (9 bits)
        - Bits 12-15: CRC (4 bits)

        eRPM = period_base * 100

        Args:
            raw_value: 16-bit raw value from telemetry frame

        Returns:
            Tuple of (eRPM, shift_count, period_base, crc_valid)
        '''
        # TODO: Implement eRPM decoding in Task 9
        # Extract shift count, period base, and CRC
        shift_count = (raw_value >> 13) & 0x07
        period_base = (raw_value >> 4) & 0x1FF
        received_crc = raw_value & 0x0F

        # Calculate expected CRC
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
        transmission. This function reverses that mapping.

        Args:
            gcr_value: 21-bit GCR-encoded value

        Returns:
            16-bit decoded value, or None if decoding fails
        '''
        # TODO: Implement GCR decoding in Task 9
        # GCR decoding: XOR each bit with the previous bit
        decoded = gcr_value ^ (gcr_value >> 1)

        # Extract 5-bit groups and map back to 4-bit nibbles
        result = 0
        for i in range(4):
            gcr_nibble = (decoded >> (i * 5)) & 0x1F
            if gcr_nibble in GCR_NIBBLE_REVERSE:
                result |= GCR_NIBBLE_REVERSE[gcr_nibble] << (i * 4)
            else:
                return None  # Invalid GCR encoding

        return result
