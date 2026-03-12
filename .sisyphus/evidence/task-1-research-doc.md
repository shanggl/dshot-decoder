Task: Document existing Sigrok/atk_libsigrokdecode DShot decoder patterns and APIs

Overview
- This document captures insights about how libsigrokdecode protocol decoders are structured and how DShot decoders could be approached, based on public SIGROK documentation and existing decoders (PWM/UART/timing-based protocols).

References used:
- Protocol decoder HOWTO (sigrok.org)
- Protocol decoder API (sigrok.org)
- atk_libsigrokdecode repository patterns (examples in decoders/PDs)
- DShot protocol notes in Betaflight docs (for framing and timing expectations)

1) File structure pattern (PD modules)
- __init__.py: a minimal module file that imports the Decoder from the PD implementation, e.g. from .pd import Decoder. It often contains a short module docstring describing the protocol.
- pd.py: the core implementation file containing a class Decoder(srd.Decoder) with metadata attributes and the logical decode pipeline.
  - Typical attributes:
    api_version, id, name, longname, desc, license
    inputs, outputs, channels, optional_channels, options
    annotations, annotation_rows, binary, tags (for frontend grouping)
  - Core methods:
    __init__(self, **kwargs): initialize state
    metadata(self, key, value): receive stream metadata (e.g., samplerate)
    reset(self): reset internal state between passes
    start(self): register outputs and perform pre-flight checks
    decode(self, startsample, endsample, data) or decode(self) for non-stacked decoders
  - Notes:
    - PDs can be stacked; OUTPUT_PYTHON is used for inter-decoder data exchange
    - The decode entry point differs between stacked and non-stacked decoders

2) Annotation format and annotation_rows usage
- Annotations: a tuple of (identifier, human-readable label).
  Example (from the I²C decoder in the HOWTO):
  annotations = (
      ('start', 'Start condition'), ('repeat-start', 'Repeat start condition'),
      ('stop', 'Stop condition'), ('ack', 'ACK'), ('nack', 'NACK'),
      ('bit', 'Data/address bit'), ('address-read', 'Address read'),
      ('address-write', 'Address write'), ('data-read', 'Data read'),
      ('data-write', 'Data write'), ('warnings', 'Warnings'),
  )
- annotation_rows groups related annotations into logical rows for PulseView output, enabling compact UIs.
  Example:
  annotation_rows = (
      ('bits', 'Bits', (0, 1, 2, 3, 4)),
      ('addr-data', 'Address/Data', (5, 6, 7, 8, 9, 10)),
      ('warnings', 'Warnings', (11,)),
  )
- Key takeaway: annotation_rows helps reduce visual collisions by grouping related annotations; keep the order of annotation indices in sync with the annotations tuple.

3) Python output format for stacked decoders (OUTPUT_PYTHON)
- libsigrokdecode supports stacking decoders; when a PD uses OUTPUT_PYTHON, it passes a Python object to the next PD in the stack via put(..., output_id, data).
- The format of data for OUTPUT_PYTHON is decoder-specific and documented in the upstream decoder file (pd.py) of the stack hop.
- A typical pattern is: self.put(startsample, endsample, self.out_python, ['PACKET', [...]]).
- In the API, OUTPUT_PYTHON is the mechanism for allowing a decoder to emit Python-structured data to downstream decoders in a pipeline.

4) Wait() and put() usage (sample handling)
- wait(): fetch the next sample window for decoding in a stacked/non-stacked pipeline.
- put(startsample, endsample, output_id, data): emit a piece of downstream output. The meaning of data depends on output_id (annotation, python, binary, meta).
- Common usage patterns show: self.put(10, 20, self.out_ann, [annotation_index, [text variants...]]).
- For Python outputs, put(..., self.out_python, data_object).

5) Error handling patterns (warnings vs exceptions)
- Use has_channel() to detect optional channels; if neither required channels exist, raise ChannelError (e.g., to signal misconfiguration).
- The Protocol Decoder HOWTO demonstrates grouping of many annotations into annotation_rows to avoid frontend clutter and to simplify user view.
- It is acceptable to emit human-readable warnings as an annotation type (e.g., the 'warnings' annotation) to communicate non-fatal issues to the user.
- Use standard Python exceptions only for clear programmer bugs or misconfiguration; avoid crashing on normal input streams.

6) At least 2 similar decoders analyzed (PWM, UART, or timing-based)
- UART-like decoders (timing-based serial): rely on start bit, data bits, parity/stop bits; typically process via time-based sampling, grouping with annotation_rows such as 'bit', 'start', 'stop', 'data', and a stacked approach if Python outputs feed another PD.
- PWM/timing-based decoders: interpret pulse widths to determine bit values; often rely on precise timing, edges, and sample windows; annotations might include 'pulse', 'bit', 'frame', and rows grouping for waveform clarity.
- Example decoders in sigrok/examples show:
  - __init__.py importing Decoder from pd.py
  - pd.py with class Decoder(srd.Decoder), api_version, id, name, longname, channels, annotation definitions, and a start/decode flow.

7) Summary of a typical DShot decoder integration path
- DShot is a timing-based, single-line protocol delivering 16-bit frames at 150/300/600 kbps ranges.
- A DShot PD in Sigrok would likely be structured similarly to existing timing-based decoders: detect edges, measure high/low durations, assemble bits, and produce high-level annotations or Python data for stacked decoders.
- The decoder would expose channels (logic input line) and possibly an optional bus for additional metadata; annotations would include bits, frame data, and potentially warnings for invalid frames.

Appendix: Sources used for this research
- sigrok Protocol_decoder_HOWTO (sections on __init__.py, pd.py, channels, annotation_rows, and the wait/put pattern)
- sigrok Protocol_decoder_API (sections on Decoder class functions, OUTPUT_PYTHON, and put semantics)
- Examples in atk_libsigrokdecode repository (structure, naming, and stacking patterns)
- DShot protocol notes (timing, framing details in Betaflight docs)

Next steps (not part of this document): implement a minimal DShot PD in atk_libsigrokdecode following the patterns outlined here, then test in PulseView/sigrok-cli with sample sr data.
