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
        For non-stacked decoders, this method uses self.wait() to get samples.
        '''
        # TODO: Implement decode logic in Task 6
        # For now, this is a skeleton that waits for samples
        while True:
            # Wait for samples
            (data,) = self.wait()

            # Placeholder: actual decode logic will be implemented in Task 6
            pass

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
