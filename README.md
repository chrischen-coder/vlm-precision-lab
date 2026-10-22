# VLM Precision Lab

**See which image answers broke when a vision model changed, then decide against your quality and service budgets.**

[中文](README.zh-CN.md) · [Recorded demo](https://crown-sports.github.io/vlm-precision-lab/) · [Value and evidence](docs/product.md) · [Service guide](docs/service-evaluation.md)

For engineers comparing a baseline with a quantized model or a new serving setup.
Smaller weights do not guarantee a faster deployment. Average accuracy can also
stay unchanged while a critical receipt field becomes wrong.

Get a paired HTML report with the actual failing samples, plus JSON decisions
for absolute quality/latency limits and newly introduced errors. Choose the
requirements before evaluating the candidate.

## First result: replay a saved comparison on CPU

Python 3.11+. This route uses included images and historical predictions; it needs
no GPU, model download, running service or API key.

```bash
git clone --branch v0.3.0 https://github.com/crown-sports/vlm-precision-lab.git
cd vlm-precision-lab
python -m venv .venv
```

Activate with `source .venv/bin/activate` on macOS/Linux or `.venv\Scripts\Activate.ps1`
in Windows PowerShell, then:

```bash
python -m pip install .
precisionlab compare --dataset examples/diagnostic-v2/samples.jsonl \
  --reference experiments/results/2026-10-03/p1-bf16/predictions.jsonl \
  --candidate experiments/results/2026-10-03/p1-awq-reload/predictions.jsonl \
  --output replay.html
```

Open `replay.html` in a browser. Expected: **300 questions, 150 source groups**.
For the graph task, **literal exact match falls from 41% to 33%**: 11 new format
violations and 3 recoveries. All 11 still name the correct endpoint set; for
example `B,D` becomes `D,B`, violating the requested alphabetical order.
**Endpoint-set correctness rises from 50% to 53%, with no new semantic endpoint
errors.** Both OCR tasks stay at 100%. This example shows an output-format
regression, not evidence of worse graph understanding; inspect both measures.

This recomputes a report from saved HF model predictions on **generated diagnostic
images**. It is not a new GPU benchmark, real-receipt evaluation or service release
gate. [Original experiment and limits](experiments/results/2026-10-03/README.md).
Use a new report filename to retain previous comparisons.

## Then evaluate your own deployment

Prepare labeled image questions and explicit targets using the
[complete input format and service protocol](docs/service-evaluation.md).
Start a compatible streaming vision chat service, then:

```bash
precisionlab evaluate --dataset samples.jsonl \
  --endpoint http://localhost:8000/v1 --model model \
  --concurrency 4 --output runs/quantized
precisionlab gate --dataset samples.jsonl --run runs/quantized \
  --constraints targets.json --output runs/decision.json
```

Here `samples.jsonl` and `targets.json` are **your files**, not bundled demo paths.
`evaluate` saves predictions, observed timings and a manifest. `gate` exits **0**
when observed requirements pass, **2** when they fail. Failed requests remain in
the accuracy denominator. Review unconstrained tasks before relying on a decision.

To block new critical errors, create **both** reference and candidate runs using
`evaluate` with matching comparison controls, then:

```bash
precisionlab regression-gate --dataset samples.jsonl \
  --reference runs/bf16 --candidate runs/quantized \
  --constraints regression-targets.json --output runs/regression-decision.json
```

Example constraint: `{"max_task_regressions":{"receipt_total_price":0}}`.
The task name must match your dataset. The report lists newly failing sample IDs;
missing required tasks fail. Exit **0** means pass, **2** means fail, and the
output file must be new. Use `gate` as well for absolute quality and service
budgets. The historical HF replay above cannot substitute for these service runs.

## Why the checks are useful

| Decision risk | Current behavior | Evidence |
| --- | --- | --- |
| Recoveries conceal new critical errors | Paired sample and task regression limits | [Equal-score regression test](tests/test_regression_gate.py) |
| Inputs or run controls changed unnoticed | Verify saved hashes and regenerate request fingerprints | [Provenance](src/precisionlab/provenance.py), [evidence tests](tests/test_evidence.py) |
| Failed work disappears from a summary | Count failures and recompute budgets from individual requests | [Service tests](tests/test_serving.py), [metric definitions](docs/service-evaluation.md) |

Source-group intervals are descriptive. A passing gate is not a statistical
noninferiority guarantee or proof of hidden server weight identity. AWQ uses
[LLM Compressor](https://github.com/vllm-project/llm-compressor); this project
contributes evaluation and evidence handling, not a new quantization method.
[Current advantages, limits and future evidence to accumulate](docs/product.md).

## Recorded evidence

- CPU regression tests cover the client, failure handling, evidence checks and gates.
- CORD-v2 import verified **100 receipts and 273 field questions**, with pinned source hashes.
- Earlier Qwen3-VL-8B AWQ files: **17.53 → 7.22 GB**; HF peak allocated memory:
  **16.47 → 20.26 GiB**. Smaller files did not mean lower peak memory in that run.

**CORD model predictions and controlled vLLM GPU benchmarks are not yet recorded.**
[Raw experiment evidence](experiments/results/2026-10-03/) · [Import receipts](docs/service-evaluation.md#receipt-data) · [GPU reproduction](docs/reproduce.md)

Apache-2.0. External models and datasets retain their own licenses.
