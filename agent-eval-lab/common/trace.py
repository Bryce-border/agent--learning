"""Trace：一次运行的完整过程记录。

原则很简单：能记的都记，事后可以裁，但没记就永远找不回来。
"""

from __future__ import annotations

import time
import uuid


class Trace:
    def __init__(self, task_id="", model="unknown"):
        self.run_id = f"{task_id}-{uuid.uuid4().hex[:6]}"
        self.task_id = task_id
        self.model = model
        self.started_at = time.time()
        self.events = []
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0}

    def add(self, kind, **payload):
        self.events.append({"t": round(time.time() - self.started_at, 3), "kind": kind, **payload})

    def add_llm(self, text, tool_calls, usage):
        for k in self.usage:
            self.usage[k] += int((usage or {}).get(k, 0) or 0)
        self.events.append({
            "t": round(time.time() - self.started_at, 3),
            "kind": "llm",
            "text": text,
            "tool_calls": [c["name"] for c in tool_calls],
        })

    def add_tool(self, name, args, result, ms):
        self.events.append({
            "t": round(time.time() - self.started_at, 3),
            "kind": "tool",
            "tool": name,
            "args": args,
            "ok": bool(result.get("ok")),
            "error": result.get("error"),
            "ms": ms,
        })

    # -- 给判定器用的便捷视图 ------------------------------------------------ #
    @property
    def tool_calls(self):
        return [e for e in self.events if e["kind"] == "tool"]

    @property
    def tools_used(self):
        return [e["tool"] for e in self.tool_calls]

    @property
    def retries(self):
        """同名工具连续调用超过一次，就记为一次无效重试的候选。"""
        count, prev, retry = 0, None, 0
        for name in self.tools_used:
            if name == prev:
                count += 1
                retry += 1
            else:
                count, prev = 1, name
        return retry

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "model": self.model,
            "wall_ms": round((time.time() - self.started_at) * 1000),
            "usage": self.usage,
            "tools_used": self.tools_used,
            "retries": self.retries,
            "events": self.events,
        }
