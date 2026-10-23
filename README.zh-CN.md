# VLM Precision Lab

对比两次视觉模型运行，逐条看清哪些答案变了。

[English](README.md) · [打开历史结果演示](https://crown-sports.github.io/vlm-precision-lab/) · [服务评测步骤](docs/service-evaluation.md) · [v0.3.0 预览版](https://github.com/crown-sports/vlm-precision-lab/releases/tag/v0.3.0)

换模型、做量化、调整服务参数后，只看平均分很容易漏掉细节。Precision Lab 将同一批问题逐条配对，
展示变化的答案，再按你设置的正确率和延迟要求检查结果。

## 同一个答案，要看两种口径

![历史图任务：BF16 回答 B,D，AWQ 回答 D,B；两者端点都答对，但只有前者遵守了排序要求](docs/figures/recorded-case.png)

*2026-10-03 保存的 Qwen3-VL-8B 结果，输入是生成的诊断图片；问题要求按字母顺序回答。*

`D,B` 找对了节点，但格式不符合要求。100 道图任务中，**严格字符串匹配率从 41% 降到 33%**，
**忽略顺序的端点集合正确率从 50% 升到 53%**。新增的 11 条严格匹配失败全部是格式违例，
**新增语义端点错误为 0**。

![历史汇总：图任务严格匹配率 41% 到 33%，端点语义正确率 50% 到 53%，两个 OCR 任务均为 100%](docs/figures/p1-awq-metrics.png)

*150 个来源组、300 个生成问题上的历史 HF 预测；两个 OCR 任务均保持 100%。[原始实验](experiments/results/2026-10-03/README.md)。*

## 在 CPU 上重放这组结果

需要 Python 3.11+。仓库自带图片和预测，无需 GPU 或 API Key。

```bash
git clone --branch v0.3.0 https://github.com/crown-sports/vlm-precision-lab.git
cd vlm-precision-lab
python -m venv .venv
```

macOS/Linux 执行 `source .venv/bin/activate`；PowerShell 执行 `.venv\Scripts\Activate.ps1`，然后：

```bash
python -m pip install .
precisionlab compare --dataset examples/diagnostic-v2/samples.jsonl \
  --reference experiments/results/2026-10-03/p1-bf16/predictions.jsonl \
  --candidate experiments/results/2026-10-03/p1-awq-reload/predictions.jsonl \
  --output replay.html
```

打开 `replay.html` 查看对比。这会重新生成历史预测的报告，不会再次运行模型。要保留旧报告，请换一个输出文件名。

## 接入自己的服务

按[输入格式与评测指南](docs/service-evaluation.md)准备标注图片和质量、延迟要求，启动兼容的流式视觉对话服务：

```bash
precisionlab evaluate --dataset samples.jsonl \
  --endpoint http://localhost:8000/v1 --model model \
  --concurrency 4 --output runs/quantized
precisionlab gate --dataset samples.jsonl --run runs/quantized \
  --constraints targets.json --output runs/decision.json
```

`samples.jsonl` 和 `targets.json` 是你自己的文件。每次运行保存预测、时延和输入哈希，失败请求也计入正确率分母。
`gate` 达标返回 `0`，不达标返回 `2`。

如果还要防止“平均分没变，却新错了一个关键字段”，先用相同对照条件分别执行基线和候选的 `evaluate`，再运行：

```bash
precisionlab regression-gate --dataset samples.jsonl \
  --reference runs/bf16 --candidate runs/quantized \
  --constraints regression-targets.json --output runs/regression-decision.json
```

例如 `{"max_task_regressions":{"receipt_total_price":0}}` 要求该任务不能新增错误。
任务名替换为自己数据中的名称，输出文件使用新路径。通过／拒绝的退出码为 `0`／`2`，绝对指标仍用 `gate` 检查。
上面的历史 HF 文件用于重放，不能代替这里的服务记录。

## 其他实验

已记录的 AWQ 运行将权重文件从 **17.53 GB 减到 7.22 GB**，但 HF 峰值 allocated 内存从
**16.47 GiB 增到 20.26 GiB**。运行方式同样影响结果。[原始记录与复现步骤](docs/reproduce.md)。

CORD-v2 已导入 100 张收据、273 个字段问题；收据模型预测和受控 vLLM GPU 压测仍待补充。
门禁结果描述的是这次测量，不能保证未来流量上的表现。

[指标定义](docs/service-evaluation.md) · [实现说明](docs/product.md) · [测试](tests/) · [版本记录](CHANGELOG.md)

代码 Apache-2.0。AWQ 使用 [LLM Compressor](https://github.com/vllm-project/llm-compressor)，模型与外部数据沿用各自许可。
