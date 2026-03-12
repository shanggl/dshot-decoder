'''
DShot (Digital Shot) Protocol Decoder

DShot is a digital protocol for flight controller (FC) to electronic speed
controller (ESC) communication used in UAV applications including FPV drones.

This decoder supports:
- DShot150, DShot300, DShot600 variants
- Unidirectional and bidirectional modes
- Multi-channel decoding (up to 4 motors)
- eRPM telemetry decoding (bidirectional mode)

Frame Structure (FC -> ESC):
- 16 bits total, MSB first
- Bits 0-10: Throttle value (0-2047)
  - 0: Disarm command
  - 1-47: Special commands
  - 48-2047: Throttle values (2000 steps)
- Bit 11: Telemetry request flag
- Bits 12-15: CRC checksum

Bidirectional Mode:
- Signal is inverted (high = 0, low = 1)
- ESC returns eRPM telemetry frame after each throttle frame
- Telemetry frame uses GCR encoding

For more information:
- https://betaflight.com/docs/development/API/Dshot
- https://blheli.gitbook.io/blheli-32-manual/dshot-command-reference
'''

from .pd import Decoder
