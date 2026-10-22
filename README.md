# VLM Precision Lab

Compare two vision-model runs and inspect the answers that changed.

[中文](README.zh-CN.md) · [Browse the recorded demo](https://crown-sports.github.io/vlm-precision-lab/) · [Service evaluation](docs/service-evaluation.md) · [v0.3.0 preview](https://github.com/crown-sports/vlm-precision-lab/releases/tag/v0.3.0)

When you change a model, quantization or serving settings, an average score only
tells part of the story. Precision Lab pairs the same questions across runs,
shows the changed answers, and checks quality and latency limits you choose.

## One answer, two different checks

![A saved graph question: BF16 answers B,D; AWQ answers D,B. Both identify the right endpoints, but only BF16 follows the requested order](docs/figures/recorded-case.png)

*Qwen3-VL-8B, recorded on 2026-10-03 with a generated diagnostic image. The question asks for alphabetical order.*

Here `D,B` names the correct nodes but breaks the requested format. Across the
100 graph questions, **strict exact match falls from 41% to 33%**, while
**unordered endpoint correctness rises from 50% to 53%**. The 11 new strict
failures are all format violations; there are **zero new semantic endpoint errors**.

![Historical comparison showing strict graph exact match 41 to 33 percent and semantic endpoint correctness 50 to 53 percent; both OCR tasks stay at 100 percent](docs/figures/p1-awq-metrics.png)

*Saved HF predictions on 300 generated questions from 150 source groups. Both OCR tasks stay at 100%. [Experiment details](experiments/results/2026-10-03/README.md).*

## Replay the comparison on CPU

Python 3.11+. The images and saved predictions are included; no GPU or API key is needed.

```bash
git clone --branch v0.3.0 https://github.com/crown-sports/vlm-precision-lab.git
cd vlm-precision-lab
python -m venv .venv
```

Activate with `source .venv/bin/activate` on macOS/Linux or `.venv\Scripts\Activate.ps1` in PowerShell, then:

```bash
python -m pip install .
precisionlab compare --dataset examples/diagnostic-v2/samples.jsonl \
  --reference experiments/results/2026-10-03/p1-bf16/predictions.jsonl \
  --candidate experiments/results/2026-10-03/p1-awq-reload/predictions.jsonl \
  --output replay.html
```

Open `replay.html` to inspect the comparison. This replays historical predictions;
it does not run the model again. Use a different filename to keep previous reports.

## Evaluate your service

Prepare labeled image questions and your quality/latency targets using the
[input format and service guide](docs/service-evaluation.md). With a compatible
streaming vision chat service running:

```bash
precisionlab evaluate --dataset samples.jsonl \
  --endpoint http://localhost:8000/v1 --model model \
  --concurrency 4 --output runs/quantized
precisionlab gate --dataset samples.jsonl --run runs/quantized \
  --constraints targets.json --output runs/decision.json
```

`samples.jsonl` and `targets.json` are your own files. The run saves predictions,
timings and input hashes. Failed requests still count in the accuracy denominator.
`gate` returns `0` when the observed requirements pass, `2` when they fail.

To catch a new mistake even when the overall score stays the same, run `evaluate`
for both the reference and candidate with matching controls, then:

```bash
precisionlab regression-gate --dataset samples.jsonl \
  --reference runs/bf16 --candidate runs/quantized \
  --constraints regression-targets.json --output runs/regression-decision.json
```

For example, `{"max_task_regressions":{"receipt_total_price":0}}` blocks newly
wrong answers in that task. Use a task name from your dataset and a new output
filename. Pass/fail exits are `0`/`2`; use `gate` alongside this for absolute limits.
The historical HF files above are for replay, not these service gates.

## More experiments

The recorded AWQ run reduced weight files from **17.53 to 7.22 GB**, but its HF
peak allocated memory rose from **16.47 to 20.26 GiB**. The runtime matters too.
[Raw runs and reproduction](docs/reproduce.md).

CORD-v2 import includes 100 receipts and 273 field questions; model predictions
on those receipts and controlled vLLM GPU benchmarks are still pending.
A passing gate describes the measured run, not a guarantee about future traffic.

[Metric definitions](docs/service-evaluation.md) · [Implementation notes](docs/product.md) · [Tests](tests/) · [Changelog](CHANGELOG.md)

Apache-2.0. AWQ uses [LLM Compressor](https://github.com/vllm-project/llm-compressor); external models and datasets retain their own licenses.
