import json
import logging
import re

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)


def parse_json_response(text, env, expect=(dict, list)):
    if not text or not text.strip():
        raise UserError(
            env._(
                "The AI provider returned an empty response — there is no content "
                "to parse. This usually indicates a provider error or an "
                "unsupported or blocked request.",
            ),
        )

    stripped = text.strip()

    for candidate in _candidates(stripped):
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError, ValueError:
            continue
        if isinstance(value, expect):
            return value

    preview = stripped[:200] + ("..." if len(stripped) > 200 else "")
    _logger.error("Failed to parse JSON from an AI response. Preview: %s", preview)
    raise UserError(
        env._(
            "Could not read the AI provider's response as JSON. This usually means "
            "the provider returned an error or an unexpected format.\n\n"
            "Response preview:\n%(preview)s",
            preview=preview,
        ),
    )


def strip_json_fence(text):
    fence = _FENCE_RE.search(text or "")
    return fence.group(1) if fence else (text or "").strip()


def _candidates(text):
    yield text

    fence = _FENCE_RE.search(text)
    if fence:
        yield fence.group(1)

    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        if start == -1:
            continue
        end = text.rfind(closer)
        while end > start:
            yield text[start : end + 1]
            end = text.rfind(closer, start, end)
