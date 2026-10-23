# Changelog

## 0.3.1 — 2026-10-23

- Preserve comparison HTML/JSON, gate decisions, recipe decisions and calibration selections on repeated or conflicting output paths. Reserve both selection files before writing and fingerprint original inputs first.
- Reject a comparison JSON filename that would collide with its HTML report.
- Report expected input/output failures without a traceback and show report locations; add first-run connection and recovery guidance.

## 0.3.0 — 2026-10-22

- Include public fixtures and reproduction material in the source distribution; CI runs its bundled tests outside the checkout.
- Add paired `regression-gate` checks for new critical-task errors, observed quality loss and minimum source groups, with per-sample regression evidence.
- Treat failed service predictions as incorrect in exact and semantic comparisons, even if residual text matches the label.


## 0.2.0

- Evaluate streaming vision chat services on labelled images, keeping failed requests in quality and throughput counts.
- Check quality and response-time budgets with auditable records and CI exit codes.
- Import pinned CORD-v2 receipt data; 100 validation receipts and 273 questions verified.
- Distinguish API request fingerprints from actual HF input tensors.
- Shorten project docs and retain the original 300-case replay and AWQ evidence.

Controlled vLLM GPU runs and real-receipt model scores are not part of this release's measured evidence.
