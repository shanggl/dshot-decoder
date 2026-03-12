Task: Research test capture strategy for DShot signals across six combinations (DShot150/300/600 × unidirectional/bidirectional).

MUST DO:
- Compile a document detailing the test-capture strategy, including decision on using existing captures, synthetic data, or both.
- Provide a concrete plan to obtain test data for all six combinations, including hardware requirements, data formats, and sample-rate calculations.
- If synthetic data is required, include a Python-script approach outline to generate SR-format (sigrok) test data and the rationale.
- If real captures are preferred, specify the hardware/setup required to obtain DShot captures at the six configurations, including telemetry considerations for bidirectional tests.
- Document sample-rate requirements (minimum 10× bitrate) and how this maps to the six DShot speeds.
- Address bidirectional capture complexity (telemetry on the same data line) and how to verify correctness.
- Ensure the document references existing sigrok-dumps resources and notes where to place or find suitable .sr files.
- Output should be a single, self-contained plan with clear next steps and acceptance criteria.

MUST NOT DO:
- Do not assume test data exists for any of the six configurations without verification.
- Do not skip the data plan; synthetic data should only be used to fill gaps where real captures are unavailable.
- Do not publish or expose any secret keys or device identifiers in the test plan.

EXPECTED OUTPUT:
- A Markdown document at .sisyphus/evidence/task-2-test-strategy.md containing:
  - A clear Decision: existing captures OR synthetic data OR both
  - A Plan for obtaining test data for all 6 combinations (unidirectional and bidirectional with telemetry)
  - If synthetic, a detailed Python script approach outline (data structures, encoding, and SR-writer strategy) or references to libraries/tools to be used
  - If real, hardware setup, signal lines to capture, suggested sampling rates, and file naming conventions for the six combinations
  - Sample-rate mapping for each DShot speed:
    - DShot150: min 1.5 MHz, recommended higher (e.g., 60–100 MS/s per channel depending on device)
    - DShot300: min 3.0 MHz
    - DShot600: min 6.0 MHz
  - Notes on bidirectional capture: telemetry timing, potential need for two channels to verify line state, and expected telemetry bit patterns

Context notes (for traceability):
- DShot timing reference (from project docs): 150 kbps -> 6.67 µs per bit, 300 kbps -> 3.33 µs per bit, 600 kbps -> 1.67 µs per bit, etc.
- Sigrok-dumps repositories host example .sr datasets; PulseView can decode DShot if a suitable decoder exists.
- The plan aligns with the plan color-coding in the repository: use existing captures first, then synthetic where gaps exist.

Date: 2026-03-13
Author: Sisyphus-Junior (OhMyOpenCode)
