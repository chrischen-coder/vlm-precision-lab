# VLM Precision Lab

**模型换版或量化后，哪些图片答案变错了？先看具体样本，再按质量和服务预算决定是否放行。**

[English](README.md) · [历史结果演示](https://crown-sports.github.io/vlm-precision-lab/) · [价值与实现证据](docs/product.md) · [服务评测步骤](docs/service-evaluation.md)

适合比较基线模型、量化模型或新服务配置的工程师。权重文件变小，不代表部署更快；总体准确率不变，也可能是“修好一条、错掉另一条”，关键收据字段仍会退步。

你会拿到能查看错误样本的配对 HTML 报告，以及按绝对质量／延迟和新增错误上限作出的 JSON 决策。先定需求，再看候选结果。

## 第一次体验：CPU 重放已有结果

需要 Python 3.11+。仓库自带图片和历史预测，无需 GPU、模型下载、正在运行的服务或 API Key。

```bash
git clone --branch v0.3.0 https://github.com/crown-sports/vlm-precision-lab.git
cd vlm-precision-lab
python -m venv .venv
```

macOS/Linux 执行 `source .venv/bin/activate`；Windows PowerShell 执行 `.venv\Scripts\Activate.ps1`，再运行：

```bash
python -m pip install .
precisionlab compare --dataset examples/diagnostic-v2/samples.jsonl \
  --reference experiments/results/2026-10-03/p1-bf16/predictions.jsonl \
  --candidate experiments/results/2026-10-03/p1-awq-reload/predictions.jsonl \
  --output replay.html
```

用浏览器打开 `replay.html`。预期为 **300 个问题、150 个来源组**。图任务的**严格字符串匹配率从 41% 变成 33%**：11 条新增格式违例、3 条恢复。11 条违例的端点集合仍正确，例如 `B,D` 变成 `D,B`，违反了要求的字母排序。**端点集合正确率从 50% 升到 53%，新增语义端点错误为 0**；两个 OCR 任务仍为 100%。这个例子展示输出格式退步，不能据此声称图关系理解变差；应同时查看两种口径。

这是在**合成诊断图片**上保存的历史 HF 模型预测重放，不是本次新跑的 GPU 测试、真实收据评测或服务上线门禁。[原始实验与局限](experiments/results/2026-10-03/README.md)。要保留不同报告，请使用不同输出文件名。

## 再接自己的服务

按[完整输入格式与评测协议](docs/service-evaluation.md)准备标注图片、问题和目标，启动兼容的流式视觉对话服务：

```bash
precisionlab evaluate --dataset samples.jsonl \
  --endpoint http://localhost:8000/v1 --model model \
  --concurrency 4 --output runs/quantized
precisionlab gate --dataset samples.jsonl --run runs/quantized \
  --constraints targets.json --output runs/decision.json
```

这里的 `samples.jsonl`、`targets.json` 是**需要你准备的文件**。`evaluate` 保存逐条预测、观测时延和清单；`gate` 达标返回 **0**，未达标返回 **2**。失败请求仍进入正确率分母，未约束字段会明确列出。

要阻止关键字段新增错误，先用 `evaluate` 按相同对照条件生成基线和候选两份服务记录，再运行：

```bash
precisionlab regression-gate --dataset samples.jsonl \
  --reference runs/bf16 --candidate runs/quantized \
  --constraints regression-targets.json --output runs/regression-decision.json
```

约束示例：`{"max_task_regressions":{"receipt_total_price":0}}`，字段名须匹配自己的 task。报告列出新增错误样本；缺少指定任务也拒绝。通过退出 **0**，拒绝退出 **2**；输出文件必须不存在。绝对准确率和服务预算仍用 `gate` 检查。上面的历史 HF 重放记录不能代替这两份服务运行。

## 为什么值得用

| 决策风险 | 当前实现 | 可核对的证据 |
| --- | --- | --- |
| 修好的样本掩盖新增关键错误 | 按样本配对，按任务限制新增错误 | [总体分数相同仍拒绝的测试](tests/test_regression_gate.py) |
| 输入或对照参数变了却继续比较 | 检查哈希、重新生成请求指纹 | [来源核验](src/precisionlab/provenance.py)、[证据测试](tests/test_evidence.py) |
| 失败请求从汇总里消失 | 从逐条记录重算成功率和预算 | [服务测试](tests/test_serving.py)、[指标定义](docs/service-evaluation.md) |

来源组统计区间用于描述，门禁通过不等于统计非劣性保证。API 指纹不能证明服务器内部权重相同。AWQ 来自 [LLM Compressor](https://github.com/vllm-project/llm-compressor)，本项目的工作是评测与证据核验。[现有优势、局限与未来需要积累的证据](docs/product.md)。

## 已有证据

- CPU 回归测试覆盖服务客户端、失败计数、证据核验和门禁。
- CORD-v2 已导入 **100 张收据、273 个字段问题**，原始文件哈希已核对。
- Qwen3-VL-8B AWQ 旧实验：文件 **17.53 → 7.22 GB**，HF 峰值 allocated **16.47 → 20.26 GiB**；该次运行文件更小但峰值内存更高。

**真实收据上的模型预测、受控 vLLM GPU 压测尚未记录。**
[原始实验](experiments/results/2026-10-03/) · [收据导入](docs/service-evaluation.md#receipt-data) · [GPU 复现](docs/reproduce.md)

代码 Apache-2.0；模型与外部数据沿用各自许可。
