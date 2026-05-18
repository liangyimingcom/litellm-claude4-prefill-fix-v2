"""
Claude 4.6+ Prefill Auto-Fix Callback for LiteLLM Proxy (v2).

Starting with Claude 4.6, Anthropic removed assistant message prefill support.
This callback appends a user message when messages[-1].role == "assistant"
and the model is Claude 4.6+.

If the assistant message contains tool_use blocks, the appended user message
includes tool_result blocks (required by Anthropic API validation).

References:
  - https://platform.claude.com/docs/en/about-claude/models/migration-guide
  - https://github.com/BerriAI/litellm/issues/22930
"""

import json
import re
import sys
from typing import Optional, Union

from litellm.integrations.custom_logger import CustomLogger

TARGET_CALL_TYPES = {"completion", "acompletion", "anthropic_messages"}

_NO_PREFILL_RE = re.compile(
    r"claude-(?:sonnet|opus|haiku)-4-([6-9]|\d{2,})"
    r"|claude-(?:sonnet|opus|haiku)-([5-9]|\d{2,})-"
    r"|claude-mythos"
)


def _model_needs_fix(model: str) -> bool:
    return bool(_NO_PREFILL_RE.search(model.lower()))


def _extract_tool_use_ids(content) -> list:
    if isinstance(content, list):
        return [b["id"] for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
    return []


def _build_user_message(content) -> dict:
    tool_ids = _extract_tool_use_ids(content)
    if tool_ids:
        return {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": tid, "content": "continue"}
                for tid in tool_ids
            ],
        }
    return {"role": "user", "content": "continue"}


class AppendContinueCallback(CustomLogger):
    """
    Append a user message when messages[-1] is assistant and the target
    model is Claude 4.6+ (no prefill support).
    """

    async def async_pre_call_hook(
        self,
        user_api_key_dict,
        cache,
        data: dict,
        call_type,
    ) -> Optional[Union[dict, str, Exception]]:
        if call_type not in TARGET_CALL_TYPES:
            return data

        messages = data.get("messages", [])
        if not messages:
            return data

        last_msg = messages[-1]
        if not isinstance(last_msg, dict):
            return data

        if last_msg.get("role") != "assistant":
            return data

        model = data.get("model", "")
        if not _model_needs_fix(model):
            return data

        # Build and append user message
        tool_ids = _extract_tool_use_ids(last_msg.get("content"))
        user_msg = _build_user_message(last_msg.get("content"))
        data["messages"] = messages + [user_msg]

        # --- Logging (print to stdout → CloudWatch) ---
        trace_id = data.get("metadata", {}).get("trace_id", "") or data.get("litellm_trace_id", "")
        tool_ids_str = ",".join(tool_ids) if tool_ids else "none"

        # A) Summary line for CloudWatch Insights parse
        print(
            f"[AppendContinueCallback] model={model} call_type={call_type} "
            f"action=appended count={len(messages)}->{len(messages)+1} "
            f"tool_ids={tool_ids_str} trace_id={trace_id}",
            flush=True,
        )

        # B) JSON detail with original prompt (last assistant message)
        detail = {
            "tag": "AppendContinueCallback",
            "model": model,
            "call_type": call_type,
            "trace_id": trace_id,
            "original_count": len(messages),
            "tool_ids": tool_ids or None,
            "last_assistant_content": last_msg.get("content"),
            "appended_message": user_msg,
        }
        print(json.dumps(detail, ensure_ascii=False, separators=(",", ":")), flush=True)

        return data


proxy_handler_instance = AppendContinueCallback()
