# Product value and evidence

[English README](../README.md) · [中文首页](../README.zh-CN.md)

## The decision this supports

For engineers changing a vision model, quantization setting or serving deployment:
should the candidate replace the baseline on this workload? A smaller checkpoint
or unchanged overall exact-match score cannot answer that alone. The useful
outputs are a paired error report and an explicit decision against requirements
chosen before looking at the candidate.

The README's CPU replay is a first look at a historical comparison. Real deployment
decisions need your own labeled images, controlled service runs and thresholds.

## Current advantages, with inspectable evidence

| Capability | Why it matters | Implementation and evidence |
| --- | --- | --- |
| Pair predictions by sample, summarize by task, bootstrap by source group | A recovered easy sample cannot conceal a newly broken critical field; questions from one document are not treated as independent sources | [metrics.py](../src/precisionlab/metrics.py), [regression tests](../tests/test_regression_gate.py) |
| Verify dataset/prediction hashes and regenerate request fingerprints | Detect changed inputs or incompatible saved comparison controls before a gate decides | [provenance.py](../src/precisionlab/provenance.py), [gate.py](../src/precisionlab/gate.py), [evidence tests](../tests/test_evidence.py) |
| Keep failed service requests in the denominator and gate quality plus observed service budgets | Success-only accuracy and latency summaries can hide failed work | [serving.py](../src/precisionlab/serving.py), [service tests](../tests/test_serving.py), [measurement definitions](service-evaluation.md) |
| Block new errors separately from absolute quality | A candidate can fail relative regression limits even when average accuracy is unchanged | [regression.py](../src/precisionlab/regression.py), [equal-score regression test](../tests/test_regression_gate.py) |

These are evaluation and evidence-handling choices, not a new quantization method.
AWQ uses LLM Compressor. The package does not replace a serving engine or a broad
benchmark suite.

## What the first replay does and does not show

The bundled historical BF16/AWQ predictions contain 300 questions from 150 generated
source groups. The graph task goes from 41% to 33% exact match, with 11 newly wrong
and 3 recovered answers; the other two diagnostic tasks stay at 100%. The CPU
command recomputes that comparison and renders saved images; it runs no model.
See [original experiment record](../experiments/results/2026-10-03/README.md) and
[raw report](../experiments/results/2026-10-03/p1-awq-report.json).

These HF records are not service-run inputs to `regression-gate`. To use the gate,
produce reference and candidate directories with `evaluate`, following the
[service protocol](service-evaluation.md), then run both absolute and paired gates.
All output decisions are based on observed requirements, not statistical
noninferiority guarantees. API request equality does not attest hidden server
weights, image tensors, GPU state or cache controls.

## What could become a durable advantage

A maintained workload library with independently checked labels, controlled
multi-engine/GPU comparisons and repeatable links between specific regressions
and deployment settings would be valuable accumulated evidence. It does not yet
exist here at production scale. The verified CORD import is data preparation,
not model evaluation; controlled CORD service/GPU results remain unrecorded.
