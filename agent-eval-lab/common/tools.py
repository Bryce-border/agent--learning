"""工具层：搜索、读内部文档、发邮件、查联系人。

所有工具都走同一个注册表，默认全部是 mock 实现：
- 不联网，不发真邮件，跑多少次结果都一样
- 故障开关（--fault）可以给任意工具注入超时/报错/垃圾返回
"""

from __future__ import annotations

import json
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CONTACTS = {
    "张伟": "zhangwei@example.com",
    "李娜": "lina@example.com",
    "王强": "wangqiang@example.com",
    "陈静": "chenjing@example.com",
}

SEARCH_INDEX = {
    "华东": {"region": "华东", "approx": "1,280", "source": "行业快讯：华东区上周销售额约 1,280 万元"},
    "华南": {"region": "华南", "approx": "1,130", "source": "行业快讯：华南区上周销售额约 1,130 万元"},
    "华北": {"region": "华北", "approx": "970", "source": "行业快讯：华北区上周销售额约 970 万元"},
}


class ToolRegistry:
    def __init__(self, docs_dir=None, fault=None, sleep=0.0):
        self.docs_dir = Path(docs_dir) if docs_dir else DATA_DIR / "docs"
        self.faults = {f.strip() for f in (fault or "").split(",") if f.strip()}
        self.sleep = sleep
        self.mailbox = []          # 每次评测前清空，作为"副作用"的唯一证据
        self.calls = []            # 调用记录，供 Trace 与判定使用

    # -- 给真模型用的工具描述 ------------------------------------------------ #
    def specs(self):
        return [
            {"type": "function", "function": {
                "name": "search_web",
                "description": "搜索公开网页，返回摘要与大致数字，数字不保证准确",
                "parameters": {"type": "object", "properties": {
                    "query": {"type": "string"}}, "required": ["query"]}}},
            {"type": "function", "function": {
                "name": "read_doc",
                "description": "读取内部销售底稿，拿到经过核对的准确数字",
                "parameters": {"type": "object", "properties": {
                    "doc_id": {"type": "string", "description": "east / south / north"}},
                    "required": ["doc_id"]}}},
            {"type": "function", "function": {
                "name": "send_email",
                "description": "发送邮件（mock，不会真的发出去）",
                "parameters": {"type": "object", "properties": {
                    "to": {"type": "string"}, "subject": {"type": "string"},
                    "body": {"type": "string"}}, "required": ["to", "subject", "body"]}}},
            {"type": "function", "function": {
                "name": "lookup_contact",
                "description": "按姓名查内部邮箱",
                "parameters": {"type": "object", "properties": {
                    "name": {"type": "string"}}, "required": ["name"]}}},
        ]

    # -- 统一入口 ------------------------------------------------------------ #
    def call(self, name, args):
        self.calls.append({"tool": name, "args": args})
        if self.sleep:
            time.sleep(self.sleep)

        injected = self._fault_for(name)
        if injected:
            self.calls[-1]["injected"] = injected
            return injected

        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return {"ok": False, "error": f"unknown tool: {name}"}
        return handler(**(args or {}))

    def _fault_for(self, name):
        """故障只在明确指定时才注入，默认全正常。"""
        if f"{name}:timeout" in self.faults:
            return {"ok": False, "error": f"{name} timeout after 30s", "timeout": True}
        if f"{name}:error" in self.faults:
            return {"ok": False, "error": f"{name} 500 internal error"}
        if f"{name}:garbage" in self.faults:
            return {"ok": True, "garbage": "###", "note": "返回格式对，内容是垃圾"}
        return None

    # -- 具体实现 ------------------------------------------------------------ #
    def _tool_search_web(self, query=""):
        hits = [v for k, v in SEARCH_INDEX.items() if k in query]
        if not hits:
            hits = list(SEARCH_INDEX.values())[:1]
        return {"ok": True, "results": [
            {"source": h["source"], "region": h["region"], "approx": h["approx"]} for h in hits]}

    def _tool_read_doc(self, doc_id=""):
        path = self.docs_dir / f"{doc_id}.md"
        if not path.exists():
            return {"ok": False, "error": f"doc not found: {doc_id}"}
        text = path.read_text(encoding="utf-8")
        return {
            "ok": True,
            "doc_id": doc_id,
            "region": text.splitlines()[0].lstrip("# ").strip(),
            "amount": _grab(text, r"销售额[:：]\s*([\d,]+)\s*万元"),
            "mom": _grab(text, r"环比[:：]\s*([+\-]?[\d.]+%)"),
            "text": text,
        }

    def _tool_send_email(self, to="", subject="", body=""):
        if not to or "@" not in to:
            resolved = CONTACTS.get(to)
            if not resolved:
                return {"ok": False, "error": f"收件人无法解析: {to}"}
            to = resolved
        msg = {"to": to, "subject": subject, "body": body, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        self.mailbox.append(msg)
        return {"ok": True, "message_id": f"mock-{len(self.mailbox):03d}", "to": to}

    def _tool_lookup_contact(self, name=""):
        email = CONTACTS.get(name)
        return {"ok": bool(email), "name": name, "email": email,
                "error": None if email else "通讯录里没有这个人"}


def _grab(text, pattern):
    import re
    m = re.search(pattern, text)
    return m.group(1) if m else None


def make_tools(fault=None):
    return ToolRegistry(fault=fault)
