# Agent 评测入门 · CSDN 系列专栏

> 如果你已经把第一个 Agent 跑通了，却被人问住："它到底行不行？"——这个合集就是写给你的。

持续更新中，主线一周两篇。**已发布：T0 合集导言、TA 黑话地图、T1 到底在问什么。**

## 主线（共 35 篇）

| 部分 | 篇目 | 解决什么 |
|---|---|---|
| 开篇 | T0 / TA | 导言 + 黑话地图（随时回查） |
| 认知 | T1–T2 | 把"评测"这件事问清楚 |
| 见世面 | T3–T5 | 读懂别人的 Benchmark → 答案对≠办成 → 攒出自己的题 |
| 动手评测 | T6–T11 | 定义成功、选指标、首跑、非确定性、统计可靠性 |
| 打分 | T12–T18 | Judge 全套 + Judge Agent 三层路由 |
| 归因与异常 | T19–T25 | Trace、多轮与长程、工具调用、故障注入、成本、安全、过度拒绝 |
| 回归与上线 | T26–T29 | 回归 CI、灰度监控、闭环回流、报告 |
| 收尾实战 | P1–P4 | 手把手搭一个评测框架 |

## 番外

- F1 开源评测框架上手对比：新手先玩哪个
- F2 翻车合辑：评测踩坑错题本（长期更新）

## 赶时间的话走这条线

T0 → T3 → T6 → T7 → T8 → T11 → T26 → P1–P4

## 仓库里有什么

```
posts/            每篇正文（Markdown，可直接发 CSDN）
agent-eval-lab/   配套代码：一个真能跑的「周报助手」+ 最小评测脚本
00-*.md           合集总纲、完整目录、写作约定
02-*.md           新篇详细大纲
素材-*.md         写之前查过的资料（benchmark 事实核查等）
```

## 配套代码

[agent-test-learing](https://github.com/Bryce-border/agent-test-learing) → `agent-eval-lab/`

```bash
git clone https://github.com/Bryce-border/agent-test-learing.git
cd agent-test-learing/agent-eval-lab
python t08_first_run/eval_min.py --mock     # 不联网、不花钱，8 条用例跑通
```

只用标准库，不用装任何评测框架；接真模型只需改 `.env` 三个变量。
发邮件、删数据一律走 mock，clone 下来随便跑。
