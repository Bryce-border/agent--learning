"""模型调用封装。

两条路：
- MockLLM：不联网、确定性、可注入"手滑"，用来跑通评测链路（推荐先跑这个）
- OpenAICompatibleLLM：任何 OpenAI 兼容接口，填 YOUR_BASE_URL / YOUR_API_KEY 就能换成真模型

对上层只暴露一个方法：chat(messages, tools) -> {"text": str, "tool_calls": [...], "usage": {...}}
工具调用的格式统一成 {"name": ..., "args": {...}}，换模型不用改 Agent。
"""

from __future__ import annotations

import json
import os
import re
import urllib.request


class BaseLLM:
    name = "base"

    def chat(self, messages, tools=None):
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# 真模型：OpenAI 兼容接口（DeepSeek / Qwen / Moonshot / vLLM 都能用）
# --------------------------------------------------------------------------- #
class OpenAICompatibleLLM(BaseLLM):
    def __init__(self, base_url=None, api_key=None, model=None, temperature=0.0, timeout=90):
        self.base_url = (base_url or os.getenv("YOUR_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("YOUR_API_KEY", "")
        self.model = model or os.getenv("YOUR_MODEL", "YOUR_MODEL_NAME")
        self.temperature = temperature
        self.timeout = timeout
        self.name = f"openai-compatible:{self.model}"

    def chat(self, messages, tools=None):
        if not self.base_url or not self.api_key:
            raise RuntimeError("缺 YOUR_BASE_URL / YOUR_API_KEY，先配 .env 或改用 --mock")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        msg = data["choices"][0]["message"]
        calls = []
        for call in msg.get("tool_calls") or []:
            fn = call["function"]
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append({"name": fn["name"], "args": args})

        return {
            "text": msg.get("content") or "",
            "tool_calls": calls,
            "usage": data.get("usage") or {},
        }


# --------------------------------------------------------------------------- #
# 假模型：按剧本走，用来在没有 API Key 的情况下把评测链路跑通
# --------------------------------------------------------------------------- #
REGION_DOC = {"华东": "east", "华南": "south", "华北": "north"}


class MockLLM(BaseLLM):
    """确定性剧本模型。

    flaw 用来模拟真实 Agent 常见的毛病，做"回归评测"的对照组：
      skip_source      跳过读底稿，直接拿搜索摘要下结论（数字精度会掉）
      wrong_recipient  收件人发错（发到 all@company.com）
      no_email         该发邮件却没发
      overlong         答案写超长
    """

    name = "mock"

    def __init__(self, flaw="none"):
        self.flaws = {f.strip() for f in (flaw or "none").split(",") if f.strip()}
        self.reset()

    def reset(self):
        self._plan = []
        self._cursor = 0
        self._facts = {}
        self._emails_sent = 0
        self._task = ""

    # -- 内部：根据用户输入排一份行动计划 ---------------------------------- #
    def _build_plan(self, user_text):
        regions = [r for r in ("华东", "华南", "华北") if r in user_text]
        if not regions:
            regions = ["华东"]
        m = re.search(r"发给([\u4e00-\u9fa5]{2,4})", user_text)
        recipient = m.group(1) if m else None
        need_email = recipient is not None and "发" in user_text

        plan = [{"tool": "search_web", "args": {"query": f"{'、'.join(regions)} 上周 销售额"}}]
        if "skip_source" not in self.flaws:
            for r in regions:
                plan.append({"tool": "read_doc", "args": {"doc_id": REGION_DOC[r]}})
        if need_email:
            if "no_email" not in self.flaws:
                to = "all@company.com" if "wrong_recipient" in self.flaws else recipient
                plan.append({"tool": "send_email", "args": {"to": to, "subject": "销售周报", "body": None}})
        return plan

    def _compose(self, user_text):
        """把工具观测拼成答案。数字只从底稿取，取不到就老实说不确定。"""
        parts = []
        for region, facts in self._facts.items():
            if facts.get("amount"):
                parts.append(f"{region}区上周销售额 {facts['amount']} 万元，环比 {facts.get('mom', '未知')}")
            else:
                parts.append(f"{region}区只查到搜索摘要（约 {facts.get('approx', '未知')} 万元），未核到底稿，数字仅供参考")
        body = "；".join(parts) + "。"
        if "overlong" in self.flaws:
            body = body + "另外建议关注渠道结构、退货率、客单价变化、促销节奏、库存周转等指标，" * 6
        if len(self._facts) > 1:
            body = "对比结果：" + body
        return body

    def chat(self, messages, tools=None):
        user_text = next((m["content"] for m in messages if m["role"] == "user"), "")

        if not self._plan:
            self._task = user_text
            self._plan = self._build_plan(user_text)

        # 先把上一条工具结果吃掉
        last = messages[-1]
        if last.get("role") == "tool":
            obs = json.loads(last["content"]) if isinstance(last["content"], str) else last["content"]
            name = last.get("name")
            if name == "read_doc" and obs.get("ok"):
                self._facts[obs["region"]] = {
                    "amount": obs["amount"],
                    "mom": obs["mom"],
                }
            elif name == "search_web" and obs.get("ok"):
                for hit in obs.get("results", []):
                    region = hit.get("region")
                    if region and region not in self._facts:
                        self._facts[region] = {"approx": hit.get("approx")}
            elif name == "send_email" and obs.get("ok"):
                self._emails_sent += 1

        if self._cursor < len(self._plan):
            step = self._plan[self._cursor]
            self._cursor += 1
            args = dict(step["args"])
            if step["tool"] == "send_email" and args.get("body") is None:
                args["body"] = self._compose(user_text)
            return {"text": "", "tool_calls": [{"name": step["tool"], "args": args}],
                    "usage": {"prompt_tokens": 320, "completion_tokens": 48}}

        answer = self._compose(user_text)
        if self._emails_sent:
            answer = f"周报已生成并发送。{answer}"
        return {"text": answer, "tool_calls": [],
                "usage": {"prompt_tokens": 480, "completion_tokens": 120}}
