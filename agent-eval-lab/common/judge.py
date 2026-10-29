"""判定器：规则能判的绝不交给模型。

任务集里每条用例带一份 success_criteria，四类条件：
  must_contain       最终答案（或邮件正文）里必须出现的内容
  must_call_tool     过程上必须真的调过的工具
  max_len            答案长度上限
  email_to           必须发邮件，且收件人精确匹配
  must_not_contain   不许出现的内容（防编造）
"""

from __future__ import annotations

import re


def judge(answer, mailbox, trace, spec):
    """返回 (passed, reason)。reason 取第一个失败项，方便按失败类型分组统计。"""
    blob = answer + "\n" + "\n".join(m.get("body", "") for m in mailbox)

    for kw in spec.get("must_contain", []):
        if kw not in blob:
            return False, f"missing:{kw}"

    for kw in spec.get("must_not_contain", []):
        if kw in blob:
            return False, f"forbidden:{kw}"

    if trace is not None:
        used = set(trace.tools_used)
        for tool in spec.get("must_call_tool", []):
            if tool not in used:
                return False, f"not_called:{tool}"

    if spec.get("max_len"):
        if len(answer) > spec["max_len"]:
            return False, f"too_long:{len(answer)}"

    if spec.get("email_to"):
        expected = spec["email_to"]
        if not mailbox:
            return False, "no_email"
        got = [m["to"] for m in mailbox]
        if got != expected:
            return False, f"wrong_recipient:{','.join(got)}"

    return True, "ok"
