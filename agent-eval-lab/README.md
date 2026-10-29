# agent-eval-lab

《Agent 评测入门》系列博客（CSDN）的配套代码。

主线案例是一个**真的能跑**的 Agent：**周报助手**——会搜网页、读内部底稿、发邮件（mock）。
它会被反复评测，也会被反复改坏；系列里每个评测概念，最终都落到它身上。

## 三分钟跑起来

```bash
git clone https://github.com/Bryce-border/agent-test-learing.git
cd agent-test-learing/agent-eval-lab
python t08_first_run/eval_min.py --mock
```

不需要 API Key，不联网，不发真邮件。跑完会在 `runs/<时间戳>/` 下生成 `results.csv`、`summary.json`、`traces.jsonl`。

想看它怎么翻车，换几个对照组：

```bash
python t08_first_run/eval_min.py --mock                                   # 基线，8/8
python t08_first_run/eval_min.py --mock --flaw wrong_recipient,overlong    # 发错人 + 答案超长，4/8
python t08_first_run/eval_min.py --mock --flaw skip_source                 # 跳过底稿直接下结论，0/8
python t08_first_run/eval_min.py --mock --fault read_doc:timeout           # 工具超时，看它会不会硬编
```

接真模型（任何 OpenAI 兼容接口，DeepSeek / Qwen / Moonshot / vLLM 都行）：

```bash
cp .env.example .env      # 填 YOUR_BASE_URL / YOUR_API_KEY / YOUR_MODEL
python t08_first_run/eval_min.py --live
```

## 目录结构

```
common/
  llm.py          模型封装：MockLLM（剧本）+ OpenAICompatibleLLM（真模型）
  tools.py        工具注册表：search_web / read_doc / send_email / lookup_contact
  trace.py        Trace：llm 调用、工具调用、耗时、token 全记
  judge.py        规则判定器（确定性，不花钱）
agents/
  weekly_report.py  被测 Agent：一个 while 循环 + 工具调用 + Trace
data/
  tasks.jsonl     8 条评测用例，带 success_criteria
  docs/           内部底稿（east / south / north），Agent 的"知识来源"
t08_first_run/
  eval_min.py     最小可用评测脚本：跑批 -> 判定 -> CSV
runs/             每次运行的产物（已 gitignore）
```

## 几个刻意的设计

- **MockLLM 不是 mock 掉整个 Agent**，它只替换"模型决策"这一步；工具调用、Trace、判定、CSV 全是真的跑了。所以评测框架本身可以被测试。
- **数字只从底稿取**：搜索工具返回的是"约 1,280 万"，底稿里才是"1,284 万"。跳过底稿就必然对不上，这个差异是故意留的检测点。
- **邮件是唯一副作用**：判定器查 `tools.mailbox`，不看 Agent 自己说没说"已发送"。
- **错误分级**：工具报错走 `ok: false`，Agent 可以选择降级或坦白；脚本层捕获异常记 `error:*`，不让单条用例拖死整批。
- **故障注入走命令行开关**，不改代码：`--fault read_doc:timeout`。

## 约定

- Python 3.10+，只用标准库，不装任何评测框架
- 每个脚本能单独跑，不依赖上一次运行的残留状态
- 需要填 Key 的地方统一 `YOUR_XXX` 占位
- 发邮件、删数据这类不可逆操作一律 mock，默认不真发
