"""
Claude 4.6+ Prefill Auto-Fix Callback for LiteLLM Proxy (v2).

Starting with Claude 4.6, Anthropic removed assistant message prefill support.
Requests ending with an assistant message return 400:
  "This model does not support assistant message prefill.
   The conversation must end with a user message."

This callback appends a user message when:
  1. call_type is in TARGET_CALL_TYPES
  2. messages[-1].role == "assistant"
  3. model is Claude 4.6+ (which does not support prefill)

If the assistant message contains tool_use blocks, the appended user message
includes tool_result blocks (required by Anthropic API validation).

References:
  - https://platform.claude.com/docs/en/about-claude/models/migration-guide
  - https://github.com/BerriAI/litellm/issues/22930
"""

import re
from typing import Optional, Union

from litellm._logging import verbose_logger
from litellm.integrations.custom_logger import CustomLogger

TARGET_CALL_TYPES = {"completion", "acompletion", "anthropic_messages"}

# Matches Claude models 4.6+ that do NOT support prefill.
_NO_PREFILL_RE = re.compile(
    r"claude-(?:sonnet|opus|haiku)-4-([6-9]|\d{2,})"
    r"|claude-(?:sonnet|opus|haiku)-([5-9]|\d{2,})-"
    r"|claude-mythos"
)


def _model_needs_fix(model: str) -> bool:
    """Return True if the model does not support assistant prefill."""
    return bool(_NO_PREFILL_RE.search(model.lower()))


def _extract_tool_use_ids(content) -> list:
    """Extract tool_use IDs from assistant message content."""
    if isinstance(content, list):
        return [
            block["id"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "tool_use"
        ]
    return []


def _build_user_message(content) -> dict:
    """Build the appropriate user message to append.

    If assistant content has tool_use blocks, return a user message with
    tool_result blocks (required by Anthropic API). Otherwise return
    a simple {"role": "user", "content": "continue"}.
    """
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

        user_msg = _build_user_message(last_msg.get("content"))
        verbose_logger.info(
            f"[AppendContinueCallback] Appended user message "
            f"for model={model} call_type={call_type}. "
            f"Original count={len(messages)}, new count={len(messages) + 1}."
        )
        data["messages"] = messages + [user_msg]
        return data


proxy_handler_instance = AppendContinueCallback()
