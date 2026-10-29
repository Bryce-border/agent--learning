"""最小可用评测脚本：任务集 -> 跑 Agent -> 判定 -> 结果表。

用法：
    python t08_first_run/eval_min.py --mock                     # 离线跑，不花钱
    python t08_first_run/eval_min.py --mock --flaw skip_source  # 对照组：模拟"跳过底稿"
    python t08_first_run/eval_min.py --live                     # 接真模型（需配 .env）
    python t08_first_run/eval_min.py --mock --fault read_doc:timeout   # 故障注入

输出落到 runs/<时间戳>/results.csv 与 summary.json。
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.weekly_report import WeeklyReportAgent   # noqa: E402
from common.judge import judge                      # noqa: E402
from common.llm import MockLLM, OpenAICompatibleLLM  # noqa: E402
from common.tools import ToolRegistry               # noqa: E402


def load_tasks(limit=None):
    path = ROOT / "data" / "tasks.jsonl"
    tasks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return tasks[:limit] if limit else tasks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="用剧本模型，不联网")
    ap.add_argument("--live", action="store_true", help="用真模型（OpenAI 兼容）")
    ap.add_argument("--flaw", default="none", help="mock 模型的手滑项：skip_source,wrong_recipient,no_email,overlong")
    ap.add_argument("--fault", default="", help="工具故障：read_doc:timeout,search_web:error ...")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if not args.mock and not args.live:
        args.mock = True  # 默认离线，跑得起来比什么都重要

    tasks = load_tasks(args.limit)
    run_dir = Path(args.out) if args.out else ROOT / "runs" / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    rows, traces = [], []
    for task in tasks:
        llm = MockLLM(flaw=args.flaw) if args.mock else OpenAICompatibleLLM()
        tools = ToolRegistry(fault=args.fault)
        agent = WeeklyReportAgent(llm, tools)

        t0 = time.time()
        try:
            result = agent.run(task["input"], task_id=task["id"])
            passed, reason = judge(result["answer"], result["mailbox"], result["trace"],
                                   task["success_criteria"])
            answer, stop = result["answer"], result["stop_reason"]
            trace_obj = result["trace"]
        except Exception as exc:                      # 执行异常不该让整批评测挂掉
            passed, reason, answer, stop = False, f"error:{type(exc).__name__}", "", "exception"
            result = {"trace": None, "steps": 0}
            trace_obj = None

        latency = round((time.time() - t0) * 1000)
        usage = trace_obj.usage if trace_obj else {"prompt_tokens": 0, "completion_tokens": 0}
        row = {
            "id": task["id"],
            "tags": "|".join(task["tags"]),
            "passed": "Y" if passed else "N",
            "reason": reason,
            "steps": result.get("steps", 0),
            "tools": ">".join(trace_obj.tools_used) if trace_obj else "",
            "latency_ms": latency,
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "stop_reason": stop,
            "answer": answer.replace("\n", " ")[:200],
        }
        rows.append(row)
        if trace_obj:
            traces.append(trace_obj.to_dict())

    csv_path = run_dir / "results.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    passed = [r for r in rows if r["passed"] == "Y"]
    by_tag = defaultdict(lambda: [0, 0])
    for r in rows:
        for tag in r["tags"].split("|"):
            by_tag[tag][0] += 1
            by_tag[tag][1] += r["passed"] == "Y"

    fail_reasons = Counter(r["reason"] for r in rows if r["passed"] == "N")
    summary = {
        "model": (MockLLM(flaw=args.flaw).name if args.mock else OpenAICompatibleLLM().name),
        "mode": "mock" if args.mock else "live",
        "flaw": args.flaw if args.mock else None,
        "fault": args.fault or None,
        "total": len(rows),
        "passed": len(passed),
        "pass_rate": round(len(passed) / len(rows), 4) if rows else 0,
        "avg_latency_ms": round(statistics.mean(r["latency_ms"] for r in rows)) if rows else 0,
        "p95_latency_ms": sorted(r["latency_ms"] for r in rows)[int(len(rows) * 0.95) - 1] if rows else 0,
        "total_tokens": sum(r["prompt_tokens"] + r["completion_tokens"] for r in rows),
        "by_tag": {k: {"total": v[0], "passed": v[1], "rate": round(v[1] / v[0], 3)} for k, v in by_tag.items()},
        "fail_reasons": dict(fail_reasons),
        "run_dir": str(run_dir),
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "traces.jsonl").write_text(
        "\n".join(json.dumps(t, ensure_ascii=False) for t in traces), encoding="utf-8")

    # -- 控制台输出：别只盯着那个百分比 -------------------------------------- #
    print(f"run: {run_dir}")
    print(f"mode={summary['mode']} flaw={summary['flaw']} fault={summary['fault']}")
    print(f"pass {len(passed)}/{len(rows)} = {summary['pass_rate']:.1%}   "
          f"avg {summary['avg_latency_ms']}ms  p95 {summary['p95_latency_ms']}ms  "
          f"tokens {summary['total_tokens']}")
    print("-" * 78)
    for r in rows:
        flag = "PASS" if r["passed"] == "Y" else "FAIL"
        print(f"{r['id']:7} {flag}  {r['reason']:<28} {r['tools'][:34]:<34} {r['latency_ms']:>4}ms")
    print("-" * 78)
    for tag, v in sorted(summary["by_tag"].items()):
        print(f"  {tag:<12} {v['passed']}/{v['total']} = {v['rate']:.1%}")
    if fail_reasons:
        print("失败原因分布:", dict(fail_reasons))


if __name__ == "__main__":
    main()
