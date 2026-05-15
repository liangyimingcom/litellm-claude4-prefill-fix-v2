"""Unit tests for model matching regex in AppendContinueCallback."""
import re

_NO_PREFILL_RE = re.compile(
    r"claude-(?:sonnet|opus|haiku)-4-([6-9]|\d{2,})"
    r"|claude-(?:sonnet|opus|haiku)-([5-9]|\d{2,})-"
    r"|claude-mythos"
)


def _model_needs_fix(model: str) -> bool:
    return bool(_NO_PREFILL_RE.search(model.lower()))


# === Should TRIGGER (Claude 4.6+ no prefill support) ===
TRIGGER_MODELS = [
    "claude-sonnet-4-6",
    "claude-opus-4-6",
    "claude-opus-4-7",
    "claude-haiku-4-6",
    "claude-sonnet-4-8",
    "claude-sonnet-4-10",
    "us.anthropic.claude-sonnet-4-6-v1",
    "anthropic.claude-opus-4-7-v1",
    "bedrock/us.anthropic.claude-sonnet-4-6-v1:0",
    "claude-mythos",
    "claude-mythos-preview",
]

# === Should NOT trigger (still support prefill) ===
NO_TRIGGER_MODELS = [
    "claude-sonnet-4-5",
    "claude-haiku-4-5",
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307",
    "qwen-max",
    "gpt-4o",
    "kimi-chat",
    "deepseek-chat",
]


def test_trigger_models():
    for m in TRIGGER_MODELS:
        assert _model_needs_fix(m), f"Should trigger for: {m}"


def test_no_trigger_models():
    for m in NO_TRIGGER_MODELS:
        assert not _model_needs_fix(m), f"Should NOT trigger for: {m}"


if __name__ == "__main__":
    test_trigger_models()
    test_no_trigger_models()
    print(f"✅ All {len(TRIGGER_MODELS) + len(NO_TRIGGER_MODELS)} model matching tests passed")
