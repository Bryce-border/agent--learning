"""周报助手：能查资料、能读内部底稿、能发邮件的那个 Agent。

它故意做得很小——一个 while 循环、一个工具注册表、一份 Trace。
系列里要评的就是它，所以它必须可跑、可坏、可复现。
"""

from __future__ import annotations

import json
import time

from common.trace import Trace

SYSTEM_PROMPT = """你是销售周报助手。任务要求：
1. 先用 search_web 了解大致情况，再用 read_doc 读内部底稿拿准确数字；
2. 只能使用工具返回的信息，底稿里没有的内容就说"底稿未提及"，不许编；
3. 如果需要发给某个人，先 look up 联系人，再用 send_email 发送；
4. 最终用一段话汇报：每个区的销售额、环比，以及是否已发送。"""


class WeeklyReportAgent:
    def __init__(self, llm, tools, max_steps=8, system_prompt=SYSTEM_PROMPT):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.system_prompt = system_prompt

    def run(self, task_input, task_id=""):
        trace = Trace(task_id=task_id, model=getattr(self.llm, "name", "unknown"))
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task_input},
        ]
        answer, stop_reason = "", "max_steps"

        for step in range(1, self.max_steps + 1):
            resp = self.llm.chat(messages, tools=self.tools.specs())
            trace.add_llm(resp.get("text", ""), resp.get("tool_calls") or [], resp.get("usage"))

            calls = resp.get("tool_calls") or []
            if not calls:
                answer, stop_reason = resp.get("text", ""), "final"
                break

            # 真模型返回的 tool_calls 需要回填到对话里，否则下一轮它不知道自己调过什么
            messages.append({
                "role": "assistant",
                "content": resp.get("text", ""),
                "tool_calls": [{"id": f"call_{step}_{i}", "type": "function",
                                "function": {"name": c["name"], "arguments": json.dumps(c["args"], ensure_ascii=False)}}
                               for i, c in enumerate(calls)],
            })

            for i, call in enumerate(calls):
                t0 = time.time()
                result = self.tools.call(call["name"], call["args"])
                trace.add_tool(call["name"], call["args"], result, round((time.time() - t0) * 1000))
                messages.append({
                    "role": "tool",
                    "tool_call_id": f"call_{step}_{i}",
                    "name": call["name"],
                    "content": json.dumps(result, ensure_ascii=False),
                })

        if stop_reason == "max_steps":
            trace.add("stop", reason="max_steps_exceeded", steps=self.max_steps)

        return {
            "answer": answer,
            "trace": trace,
            "steps": len(trace.tool_calls),
            "stop_reason": stop_reason,
            "mailbox": list(self.tools.mailbox),
        }
