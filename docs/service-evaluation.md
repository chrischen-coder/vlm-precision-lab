# Evaluate a vision model service

The client targets streaming vision chat endpoints compatible with vLLM's
OpenAI chat API. Protocol tests run against a local fixture server; they are
not GPU or model-quality benchmarks.

For a first run without a service, use the README's **CPU replay**. It reads saved
HF predictions and writes an HTML report plus JSON; it does not create the
`manifest.json`, `profile.json` and API request records needed by a service gate.

## 1. Prepare images and labels

Use one JSONL record per question. Paths are relative to the JSONL directory.
Keep every question from the same source document in one split.

```json
{"id":"receipt-1:total","group_id":"receipt-1","split":"dev","task":"receipt_total_price","image":"images/receipt-1.png","prompt":"Read the total amount exactly as printed.","answer":"61.799","features":[]}
```

This is a schema example. The expected answer is used for scoring, never sent
as a separate label to the service. Image hashes, duplicate IDs and source leakage
are checked before requests are sent. PNG, JPEG and WebP are supported.

## 2. Measure each deployment

Use the same GPU, engine version, image-processing settings, decoding, cache
policy and concurrency. On one GPU, stop the first deployment before starting
the second. Different aliases on one server can still name the same checkpoint.

```bash
precisionlab evaluate --dataset samples.jsonl --split dev \
  --endpoint http://localhost:8000/v1 --model model \
  --concurrency 4 --max-tokens 32 --output runs/bf16
# Restart the service with the quantized checkpoint, using the same controls.
precisionlab evaluate --dataset samples.jsonl --split dev \
  --endpoint http://localhost:8000/v1 --model model \
  --concurrency 4 --max-tokens 32 --output runs/quantized
```

For an authenticated endpoint, set `PRECISIONLAB_API_KEY` in the environment.
Keys and remote error bodies are not saved. `--base-revision` records a declared
base revision; `--server-config shared-controls.json` records shared processor,
engine and cache settings. Keep model paths and quantization variants outside
this shared-controls file. These declarations are not server attestation.

Each run writes `predictions.jsonl`, `profile.json` and `manifest.json`.
HTTP errors, missing stream termination and empty answers remain failed rows.
A failed warmup aborts the benchmark; two warmup requests are used by default.

Check connectivity with one question before starting a long run:

```bash
precisionlab evaluate --dataset samples.jsonl --endpoint http://localhost:8000/v1 --model model \
  --limit 1 --warmup 0 --timeout 10 --output runs/connection-check
```

Inspect `profile.json` and `predictions.jsonl`, including `success` and `error_type`.
This is a connection check, not a useful quality estimate. A failed request still
produces a failed prediction row. Correct the endpoint/model or credentials and
use a new output directory for the full run; do not reuse `connection-check` as
the full benchmark. With normal warmup enabled, a failed warmup stops the run.

| Metric | Definition |
| --- | --- |
| Task exact match | Correct answers / all requested questions, including failures |
| p95 response latency | Request serialization through completion or failure; all requests |
| p95 first-answer latency | First nonempty visible content delta; successful streams only |
| Throughput | Successful requests / full closed-loop wall time, including client preparation and failures |

Image encoding is outside per-request latency but inside throughput wall time.
Hidden reasoning tokens are outside first-answer timing. No cache reset is
claimed. Token-limit completions are counted separately. These are client-observed
measurements, not isolated GPU token throughput or VRAM measurements.

## 3. Compare answers

```bash
precisionlab compare --dataset samples.jsonl \
  --reference runs/bf16/predictions.jsonl \
  --candidate runs/quantized/predictions.jsonl \
  --output runs/comparison.html
```

The comparison checks recorded dataset and prediction hashes before scoring.
The report separates losses and recoveries by task, shows the original images
and bootstraps paired differences by source document. API request fingerprints
cannot be combined with HF input-tensor fingerprints. Matching requests alone
cannot isolate a quantization effect from undisclosed server changes.

## 4. Gate the measured run

Write `targets.json`, choosing requirements before evaluating the candidate:

```json
{
  "min_task_em": {"receipt_total_price": 0.95},
  "min_success_rate": 1.0,
  "max_latency_p95_ms": 1500,
  "max_ttft_p95_ms": 1000,
  "max_truncated_requests": 0,
  "min_source_groups": 30
}
```

These values illustrate the format; they are not validated defaults. Other
receipt fields are unconstrained in this example and are listed as such.

```bash
precisionlab gate --dataset samples.jsonl --run runs/quantized \
  --constraints targets.json --output runs/decision.json
```

Exit 0 means the observed requirements passed; exit 2 means they failed.
Before deciding, the gate checks source/prediction hashes, regenerates request
fingerprints and recomputes scores and latency statistics from individual records.
Optional `min_requests_per_second` adds a throughput floor. An observed pass
is not a statistical non-inferiority guarantee or proof of weight identity.

## Report paths and failed commands

Use `--output comparison.html` for a comparison. The matching `comparison.json`
contains machine-readable statistics. Open the HTML file relative to the working
directory in which you ran the command. Use new names for subsequent runs.

On main, comparison reports, calibration selections, recipe decisions and
service decisions refuse to replace existing files. `select --output picked.jsonl`
also needs a new `picked.selection.json`; both are checked before either is
written. Comparison JSON sidecars receive the same protection. Operational errors
return `2` with a short stderr message. With v0.3.0, choose unused output paths yourself. Never use a dataset or prediction file as an
output path.

| What happened | What to check |
| --- | --- |
| Input file missing or invalid JSON | Fix the path or JSON before connecting to a service. |
| No samples in requested split | The default is `dev`; match `--split` to your JSONL rows. |
| Image not found | Resolve its path from the dataset's directory, not the shell's directory. |
| Output already exists | Use a new run directory or report filename; keep earlier results. |
| Warmup failed | Check endpoint/model/access first; keep the real failures visible when evaluating. |
| Gate rejects saved HF files | Run `evaluate` against the service; historical HF replay cannot supply service timings. |

A gate's exit `2` can also mean measured requirements were not met. If a new
decision JSON exists, inspect its failed checks. If no decision was written,
inspect stderr for an input, provenance or output error.

## Receipt data

```bash
pip install '.[data]'
python experiments/download_cord.py --output runs/cord-parquet --splits validation
precisionlab import-cord --parquet-dir runs/cord-parquet \
  --source-manifest experiments/cord-source.json --splits validation \
  --output runs/cord-dev
```

The import verified revision `7f0115a4b758a71d6473b8d085751692da2fef98`:
100 validation receipts, 273 questions across total, cash, change and tax.
Missing or ambiguous fields are skipped and counted. Multiple fields from one
receipt share a source group. Train maps to calibration, validation to dev, test
to test; use `--splits train validation test` to import all downloaded sources.

Scoring is literal agreement with the CORD field annotation. It is not monetary
value equivalence or the official CORD parsing benchmark. Import is completed;
model predictions on these receipts are not yet recorded.

Source: [NAVER CLOVA CORD](https://github.com/clovaai/cord),
[pinned CORD-v2 release](https://huggingface.co/datasets/naver-clova-ix/cord-v2/tree/7f0115a4b758a71d6473b8d085751692da2fef98), CC-BY-4.0.
Full images and parquet files remain outside Git. [Verified import record](../experiments/results/2026-10-04/cord-import.json).

## Reproducibility boundaries

Record engine build, checkpoint hashes, processor settings, GPU, concurrent
processes and cache configuration alongside a controlled GPU experiment.
API runs alone do not attest these facts. Existing HF quality runs are
[preserved separately](experiments.zh-CN.md); they cannot be used as vLLM speedup evidence.
