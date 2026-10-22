# VLM Precision Lab

**用自己的图片，检查量化模型的正确率和服务成本，决定能否部署。**

[演示](https://chrischen-coder.github.io/vlm-precision-lab/) · [使用步骤](docs/service-evaluation.md) · [实现原理](docs/design.zh-CN.md) · [English](README.md)

权重文件变小，不代表部署更快、关键字段读得准。
在同一批标注图片上比较量化前后结果，再按质量、失败率和延迟目标放行或拒绝。

## 使用

```bash
pip install git+https://github.com/chrischen-coder/vlm-precision-lab.git@v0.2.0
precisionlab evaluate --dataset samples.jsonl \
  --endpoint http://localhost:8000/v1 --model model \
  --concurrency 4 --output runs/quantized
precisionlab gate --dataset samples.jsonl --run runs/quantized \
  --constraints targets.json --output runs/decision.json
```

达标返回状态码 **0**，未达标返回 **2**，可接入 CI。
[数据格式、目标设置和配对比较](docs/service-evaluation.md)见使用文档。

## 已验证

| 内容 | 状态 |
| --- | --- |
| 服务客户端、失败计数、证据核验、预算检查 | 20 项 CPU 检查通过 |
| CORD-v2 真实数据接入 | 100 张收据、273 个字段问题；原始文件哈希已核对 |
| Qwen3-VL-8B AWQ 旧实验 | 文件 17.53 → 7.22 GB；HF 峰值 allocated 16.47 → 20.26 GiB |

**真实收据上的模型结果、受控 vLLM GPU 压测尚未完成。**
API 指纹核对请求，不能证明服务器内部张量或权重相同。
本版完成评测与部署检查；AWQ 算法复用 LLM Compressor。

[原始实验](experiments/results/2026-10-03/) · [真实数据导入记录](experiments/results/2026-10-04/cord-import.json) · [GPU 复现](docs/reproduce.md)

代码 Apache-2.0；模型与外部数据沿用各自许可。

## 基线回归门禁

```bash
precisionlab regression-gate --dataset samples.jsonl --reference runs/bf16 --candidate runs/quantized --constraints regression-targets.json --output runs/regression-decision.json
```

约束示例：`{"max_task_regressions":{"receipt_total.total_price":0},"max_task_loss_pp":{"receipt_total.total_price":2},"min_source_groups":30}`。字段名与数据集 task 对应。即使总体准确率不变，只要关键字段新增错误超过上限就拒绝，报告列出具体样本。先复核两份服务运行记录、请求哈希与对照参数；缺少要求的字段也拒绝。通过退出 0，未通过退出 2，输出文件必须不存在。绝对准确率和延迟预算继续用 `gate` 检查。统计区间仅作描述，不声称非劣性保证或服务器权重身份验证。失败请求即使留下正确文本，也计为错误。
