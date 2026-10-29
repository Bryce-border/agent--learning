# T3 素材：五个 Benchmark 的事实清单

> 用途：给 T3「读懂别人的 Benchmark」篇供料，**也供 T5（去污染）和 T11（重复运行一致性）引用**。
> 核查日期：2026-10-26。写作时以本文件为准，不要凭印象补数字。
> 使用原则：引用具体分数时要同时说明"谁在什么时候用什么脚手架跑出来的"，否则没有可比性。

---

## GAIA（General AI Assistants）

| 项 | 内容 |
|---|---|
| 全称 | GAIA: a benchmark for General AI Assistants |
| 提出方 | Meta FAIR、HuggingFace、AutoGPT、GenAI Meta（作者：Grégoire Mialon、Clémentine Fourrier、Craig Swift、Thomas Wolf、Yann LeCun、Thomas Scialom） |
| 时间 | arXiv:2311.12983，2023 年 11 月 |
| 任务形态 | 真实世界的开放式问答，需多步推理、网页浏览、工具使用、多模态处理（可能附带图片/表格/音频文件） |
| 规模 | 466 道题（公开其中 300 道的答案用于排行榜） |
| 难度分级 | 三个 Level，按所需工具链复杂度递增；Level 1 单次外部查询，Level 2 多步查找+格式转换，Level 3 跨源交叉验证 |
| 判定方式 | 答案是事实型、无歧义的字符串/数字/列表，**精确匹配**即可，不需要 Judge 模型 |
| 论文里的关键数字 | 人类答题正确率 92%，配备插件的 GPT-4 平均 15%（Level 1 约 30%，Level 3 接近 0） |
| 官网 | https://huggingface.co/gaia-benchmark |
| 对新手的启发 | 用"答案无歧义"换掉了"必须靠裁判打分"这个麻烦；缺点是只看最终答案，**不看推理过程** |

---

## AgentBench

| 项 | 内容 |
|---|---|
| 全称 | AgentBench: Evaluating LLMs as Agents |
| 提出方 | 清华大学 KEG 实验室（刘潇等），与俄亥俄州立大学、UC Berkeley 合作 |
| 时间 | arXiv:2308.03688，2023 年 8 月；ICLR 2024 Poster；2025 年 10 月有 v3 版预印本更新 |
| 任务形态 | **8 个交互环境**：操作系统(bash)、数据库(SQL)、知识图谱、数字卡牌对战、侧向思维谜题、家务(ALFWorld)、网络购物(WebShop)、网页浏览(Mind2Web) |
| 规模 | 约 1,360 条测试样本，覆盖上述 8 个环境 |
| 环境分类 | code-grounded / game-grounded / web-grounded 三大类；5 个自建，3 个改造自已有数据集 |
| 判定方式 | 程序化判定（成功率 SR），要求最终答案或环境状态与预期完全一致；跑在 Docker 里保证可复现 |
| 论文结论要点 | 顶级商用模型明显强于当时的开源模型；作者直指"长期的推理、决策和指令跟随能力不足"是可用 Agent 的主要障碍 |
| 开源 | https://github.com/THUDM/AgentBench ，Apache 2.0 |
| 对新手的启发 | 单个环境只会奖励特化能力，**横跨多环境才能看出是不是真泛化** |

---

## WebArena

| 项 | 内容 |
|---|---|
| 全称 | WebArena: A Realistic Web Environment for Building Autonomous Agents |
| 提出方 | 卡内基梅隆大学（Shuyan Zhou、Frank F. Xu、Hao Zhu 等，Graham Neubig 组） |
| 时间 | arXiv:2307.13854，2023 年；ICLR 2024 |
| 任务形态 | 自建的、完全可用可复现的**四个真实 Web 应用**：电商站（OneStopShop）、论坛（Postmill）、GitLab、类 Wikipedia 的 CMS（MediaWiki），外加计算器、地图、笔记等辅助站点 |
| 规模 | 812 条自然语言任务 |
| 观测空间 | 可选 URL + 页面内容（截图 / DOM 树 / 无障碍树） |
| 判定方式 | **每道题带一个可程序化校验的成功函数**，直接查数据库或页面最终状态；成功路径里没有 LLM Judge |
| 论文里的关键数字 | GPT-4 + ReAct 脚手架：14.41%；人类基线：78.24% |
| 官网 | https://webarena.dev |
| 对新手的启发 | 判定写在"环境状态"上而不是"答案文本"上——这是 Agent 评测最实用的一招。另外它承认"误打误撞也算成功"，这个取舍值得讲 |

---

## τ-bench（tau-bench）

| 项 | 内容 |
|---|---|
| 全称 | τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains |
| 提出方 | Sierra（Shunyu Yao、Noah Shinn、Pedram Razavi、Karthik Narasimhan） |
| 时间 | arXiv:2406.12045，2024 年 6 月 17 日；ICLR 2025 Poster |
| 任务形态 | **多轮对话**：LLM 扮演用户（带意图、人设、耐心），被测 Agent 通过领域 API 读写数据库，并在整段对话里遵守书面业务规则 |
| 领域与规模 | retail（退换货、订单）与 airline（取消、改签、行李）；共 165 道题（retail 115，airline 50） |
| 判定方式 | 比对**任务结束后的数据库状态**与预期是否一致；另有独立的"规则遵守（policy compliance）"判定 |
| 标志性指标 | **pass^k**——同一个任务独立跑 k 次全部成功的比例，衡量稳定性而非"碰运气的 best-of-k" |
| 论文里的关键数字 | 当时最强的 function calling 模型（如 gpt-4o）成功率不足 50%，retail 域 pass^8 低于 25% |
| 后续 | 官方排行榜固定 user simulator 为 GPT-4o；后续有 τ²-bench、τ³-bench |
| 开源 | https://github.com/sierra-research/tau-bench ，MIT |
| 对新手的启发 | 直接呼应本系列的 T10/T11：一次成功不算本事，稳定成功才算。**注意 pass^k 与常见的 pass@k 是两回事** |

---

## SWE-bench / SWE-bench Verified

| 项 | 内容 |
|---|---|
| 全称 | SWE-bench: Can Language Models Resolve Real-World GitHub Issues? |
| 提出方 | 普林斯顿大学（Carlos E. Jimenez、John Yang 等） |
| 时间 | 2024 年，ICLR 2024 Oral |
| 任务形态 | 给一个真实 GitHub issue + 出问题时的代码仓库快照，Agent 要自己定位、改代码、产出 patch |
| 规模 | 全集 2,294 条任务（来自 12 个流行 Python 开源项目：Django、Flask、scikit-learn、sympy、matplotlib、requests 等） |
| Verified 子集 | 2024 年 8 月 13 日，OpenAI Preparedness 团队与普林斯顿团队合作发布，**500 道经真人开发者逐题确认可解**的题，用于更可靠的横向对比 |
| 判定方式 | 跑单元测试：**FAIL_TO_PASS**（原本失败现在要通过）+ **PASS_TO_PASS**（原本通过不能被改坏）；通过才算 resolved，不给部分分 |
| 初始数字 | Verified 发布时，GPT-4o + Agentless 脚手架 33.2% |
| **重要时效性** | **OpenAI 已于 2026 年 2 月 23 日宣布不再把 SWE-bench Verified 用于前沿模型评测**，理由是测试本身存在缺陷 + 训练数据污染；社区普遍认为该子集已接近饱和，转而使用 SWE-bench Pro、SWE-Lancer 等后继基准 |
| 开源 | https://github.com/swe-bench/SWE-bench ，MIT；Docker 化评测，还有 SWE-bench Multimodal 等扩展 |
| 对新手的启发 | 这是"污染导致评测集失效"最鲜活的一个真实案例，T5 讲去污染时可以直接拿来当例子。**写 T3 时必须提到这条**，否则读者会觉得你在推一个已经过期的东西 |

---

## 五者横向速查（写 T3 正文时画这张表）

| Benchmark | 场景 | 题量 | 判定落在哪 | 是否需要 Judge 模型 |
|---|---|---|---|---|
| GAIA | 开放网络问答 + 工具 | 466 | 最终答案精确匹配 | 不需要 |
| AgentBench | 8 个交互环境 | ~1,360 | 环境状态 / 答案比对 | 不需要 |
| WebArena | 自建 Web 应用操作 | 812 | 数据库与页面状态（成功函数） | 不需要 |
| τ-bench | 客服多轮对话 + 工具 | 165 | 数据库状态 + 规则遵守 | 不需要（但用户模拟用 LLM） |
| SWE-bench | 真实 issue 修 bug | 2,294（Verified 500） | 单元测试 FAIL_TO_PASS / PASS_TO_PASS | 不需要 |

**一个贯穿五者的共同点，值得在正文里点出来**：它们都拼命把"判定"做成客观的、程序化的、不依赖模型主观打分的事。开放式输出必须上 Judge，那是后话（T12 之后的事）。

另外一个反差点：**五个里没有一个用轨迹（动作序列）匹配来判成败**，都是看 end state。这是 Agent 评测跟"按步骤给分"这种学校思维的差别。
