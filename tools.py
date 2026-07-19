"""
tools.py — mock tool the assistant can "call."

VULNERABILITY SURFACE: execute_tool_calls() scans raw LLM output for a
specific text pattern and executes send_refund() if found — with zero
permission check, zero amount validation, and zero verification that the
user asking actually has authority to issue a refund. Whatever text
produced that pattern (system prompt, user question, or a poisoned
document) is treated as equally authoritative.
"""

import re
from datetime import datetime

REFUND_LOG_PATH = "refund_log.txt"

# Matches: TOOL_CALL: send_refund(amount=1234, account='some-string')
TOOL_CALL_PATTERN = re.compile(
    r"TOOL_CALL:\s*send_refund\(\s*amount\s*=\s*([\d.]+)\s*,\s*account\s*=\s*['\"]([^'\"]+)['\"]\s*\)"
)


def send_refund(amount: float, account: str) -> str:
    """
    Mock tool — no real money moves. Simulates the consequence by logging
    to disk, exactly like a real tool call would hit a real payments API.
    """
    entry = f"[{datetime.now().isoformat()}] REFUND ISSUED: ${amount} -> account '{account}'\n"
    with open(REFUND_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry)
    return f"Refund of ${amount} issued to account '{account}'."


def execute_tool_calls(llm_response: str) -> list[dict]:
    """
    VULNERABLE: scans the model's raw text output for the tool-call
    pattern and executes it immediately. No check on:
      - who is asking (any user, any session)
      - whether the amount is reasonable
      - whether the account is legitimate
      - whether this response should have triggered a tool call at all
    """
    executed = []
    for match in TOOL_CALL_PATTERN.finditer(llm_response):
        amount = float(match.group(1))
        account = match.group(2)
        result = send_refund(amount, account)
        executed.append({"amount": amount, "account": account, "result": result})
    return executed