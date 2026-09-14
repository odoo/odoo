import re

from odoo.addons.integration.tools.exceptions import ClientError

_GEMINI_MODEL_IN_PATH = re.compile(r"/models/([^/:]+):")


class SpendCapReached(ClientError):
    pass


def _number(value):
    return (
        value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0
    )


def _request_model(request_kwargs):
    for key in ("json", "data", "params"):
        payload = request_kwargs.get(key)
        if isinstance(payload, dict) and isinstance(payload.get("model"), str):
            return payload["model"]
    return ""


def read_openai_compatible(url, request_kwargs, body):
    usage = body.get("usage") if isinstance(body, dict) else None
    if not isinstance(usage, dict):
        return None
    return {
        "model": _request_model(request_kwargs) or body.get("model") or "",
        "input_tokens": _number(usage.get("prompt_tokens"))
        or _number(usage.get("input_tokens")),
        "output_tokens": _number(usage.get("completion_tokens"))
        or _number(usage.get("output_tokens")),
        "audio_seconds": _number(usage.get("seconds")),
    }


def read_anthropic_messages(url, request_kwargs, body):
    usage = body.get("usage") if isinstance(body, dict) else None
    if not isinstance(usage, dict):
        return None
    return {
        "model": _request_model(request_kwargs) or body.get("model") or "",
        "input_tokens": _number(usage.get("input_tokens"))
        + _number(usage.get("cache_creation_input_tokens"))
        + _number(usage.get("cache_read_input_tokens")),
        "output_tokens": _number(usage.get("output_tokens")),
        "audio_seconds": 0,
    }


def read_gemini_native(url, request_kwargs, body):
    usage = body.get("usageMetadata") if isinstance(body, dict) else None
    if not isinstance(usage, dict):
        return None
    match = _GEMINI_MODEL_IN_PATH.search(url or "")
    return {
        "model": match.group(1) if match else body.get("modelVersion") or "",
        "input_tokens": _number(usage.get("promptTokenCount")),
        "output_tokens": _number(usage.get("candidatesTokenCount"))
        + _number(usage.get("thoughtsTokenCount")),
        "audio_seconds": 0,
    }


def read_deepgram(url, request_kwargs, body):
    metadata = body.get("metadata") if isinstance(body, dict) else None
    if not isinstance(metadata, dict) or not _number(metadata.get("duration")):
        return None
    return {
        "model": _request_model(request_kwargs),
        "input_tokens": 0,
        "output_tokens": 0,
        "audio_seconds": _number(metadata.get("duration")),
    }


USAGE_READERS = {
    "openai_compatible": read_openai_compatible,
    "anthropic_messages": read_anthropic_messages,
    "gemini_native": read_gemini_native,
    "deepgram": read_deepgram,
}


def usage_cost(model, usage):
    return (
        usage["input_tokens"] * model.cost_per_1m_input / 1_000_000
        + usage["output_tokens"] * model.cost_per_1m_output / 1_000_000
        + usage["audio_seconds"] / 60 * model.cost_per_audio_minute
    )
