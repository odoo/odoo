from __future__ import annotations

import logging
import re
import typing
from urllib.parse import unquote_plus, urlparse, urlunparse

if typing.TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "MASK",
    "REGISTERED_PATTERNS",
    "SECRET_SHAPES",
    "SENSITIVE_KEY_FRAGMENTS",
    "SENSITIVE_KEY_SEGMENTS",
    "find_secret_shapes",
    "is_sensitive_key",
    "mask_data",
    "mask_text",
    "mask_url",
    "register_pattern",
]

_logger = logging.getLogger(__name__)

MASK = "***REDACTED***"

SENSITIVE_KEY_FRAGMENTS: tuple[str, ...] = (
    "password",
    "passwd",
    "pwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "access_token",
    "refresh_token",
    "client_secret",
    "private_key",
    "privatekey",
    "credential",
    "bearer",
    "signature",
    "x_amz_security_token",
    "x_amz_signature",
)

# Too short to match inside a word: "auth" is in "author" and "oauth_provider_name".
SENSITIVE_KEY_SEGMENTS: tuple[str, ...] = ("auth",)

_LABEL_SHAPES: tuple[tuple[str, str], ...] = (
    ("password", r"\b(password|passwd|pwd)[\"']?\s*[:=]\s*\S+"),
    ("api_key", r"\b(api[_-]?key|apikey)[\"']?\s*[:=]\s*\S+"),
    ("secret_or_token", r"\b(secret|token)[\"']?\s*[:=]\s*\S+"),
    ("aws_style_key", r"\b(access[_-]?key|secret[_-]?key)[\"']?\s*[:=]\s*\S+"),
)

_VALUE_SHAPES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private_key_pem",
        re.compile(
            r"-----BEGIN[\w ]*PRIVATE KEY-----.*?(?:-----END[\w ]*PRIVATE KEY-----|\Z)",
            re.DOTALL,
        ),
    ),
    ("github_token", re.compile(r"\bghp_[a-zA-Z0-9]{36}\b")),
    ("openai_api_key", re.compile(r"\bsk-[a-zA-Z0-9]{48}\b")),
    (
        "prefixed_api_key",
        re.compile(r"\bsk-(?:proj|ant|svcacct|admin)-[A-Za-z0-9_-]{20,}"),
    ),
    ("stripe_secret_key", re.compile(r"\b[rs]k_(?:live|test)_[0-9a-zA-Z]{24,}\b")),
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bearer_token", re.compile(r"(?i:(?<=\bbearer\s))[A-Za-z0-9._~+/-]{8,}=*")),
)

SECRET_SHAPES: tuple[tuple[str, re.Pattern[str]], ...] = (
    *((name, re.compile(pattern, re.IGNORECASE)) for name, pattern in _LABEL_SHAPES),
    *_VALUE_SHAPES,
)

REGISTERED_PATTERNS: list[
    tuple[re.Pattern[str], str | Callable[[re.Match[str]], str]]
] = []

_URL_IN_TEXT = re.compile(r"https?://[^\s'\"<>]+")

_KEY_VALUE = re.compile(
    r"(?i)(?P<key>(?:"
    + "|".join(re.escape(fragment) for fragment in SENSITIVE_KEY_FRAGMENTS)
    + "|"
    + "|".join(
        rf"(?<![a-z0-9]){re.escape(segment)}(?![a-z0-9])"
        for segment in SENSITIVE_KEY_SEGMENTS
    )
    + r")(?:[_-][a-z0-9]*)*)"
    r"(?P<sep>[\"']?\s*[:=]\s*)"
    r"(?:(?P<quote>[\"'])(?:\\[\s\S]?|(?!(?P=quote))[^\\])*(?:(?P=quote)|\Z)"
    r"|(?P<scheme>(?:bearer|basic|digest|token)\s+)?(?P<bare>[^\s&;'\"<>]+))",
)

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

_PAIR_LABEL_KEYS = ("name", "key", "header", "field")


def register_pattern(
    pattern: str | re.Pattern[str],
    replacement: str | Callable[[re.Match[str]], str],
) -> None:
    compiled = re.compile(pattern) if isinstance(pattern, str) else pattern
    REGISTERED_PATTERNS.append((compiled, replacement))


def is_sensitive_key(key: object) -> bool:
    normalized = _NON_ALNUM.sub("_", _CAMEL_BOUNDARY.sub("_", str(key)).lower())
    if any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS):
        return True
    segments = normalized.split("_")
    return any(segment in segments for segment in SENSITIVE_KEY_SEGMENTS)


def find_secret_shapes(text: str) -> list[str]:
    if not text:
        return []
    return [name for name, pattern in SECRET_SHAPES if pattern.search(text)]


def _apply_registered(value: str) -> str:
    for pattern, replacement in REGISTERED_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def _mask_pairs(encoded: str) -> str:
    pairs = []
    for pair in encoded.split("&"):
        key, sep, _value = pair.partition("=")
        pairs.append(
            f"{key}={MASK}" if sep and is_sensitive_key(unquote_plus(key)) else pair
        )
    return "&".join(pairs)


def mask_url(url: str) -> str:
    masked = _apply_registered(url)
    try:
        parsed = urlparse(masked)
    except ValueError:
        return masked

    netloc = parsed.netloc
    if "@" in netloc:
        netloc = f"***:***@{netloc.rsplit('@', 1)[1]}"

    return urlunparse(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            _mask_pairs(parsed.query),
            _mask_pairs(parsed.fragment),
        ),
    )


def _mask_key_value(match: re.Match[str]) -> str:
    head = match["key"] + match["sep"]
    if match["quote"] is not None:
        return f"{head}{match['quote']}{MASK}{match['quote']}"
    return f"{head}{match['scheme'] or ''}{MASK}"


def mask_text(text: str) -> str:
    if not text:
        return text
    masked = _apply_registered(str(text))
    masked = _URL_IN_TEXT.sub(lambda match: mask_url(match.group(0)), masked)
    masked = _KEY_VALUE.sub(_mask_key_value, masked)
    for _name, shape in _VALUE_SHAPES:
        masked = shape.sub(MASK, masked)
    return masked


def _is_sensitive_pair(data: dict[typing.Any, typing.Any]) -> bool:
    if "value" not in data:
        return False
    return any(
        isinstance(label := data.get(key), str) and is_sensitive_key(label)
        for key in _PAIR_LABEL_KEYS
    )


def mask_data(data: typing.Any, *, max_depth: int = 50, _depth: int = 0) -> typing.Any:
    if not data:
        return data
    if isinstance(data, str):
        return mask_text(data)
    if _depth > max_depth:
        _logger.warning(
            "Redaction depth limit (%s) exceeded; the structure below it is dropped",
            max_depth,
        )
        return "***REDACTED_DEEP_NESTING***"

    def walk(value: typing.Any) -> typing.Any:
        return mask_data(value, max_depth=max_depth, _depth=_depth + 1)

    if isinstance(data, dict):
        pair = _is_sensitive_pair(data)
        return {
            key: (
                MASK
                if is_sensitive_key(key) or (pair and key == "value")
                else walk(value)
            )
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [walk(item) for item in data]
    if isinstance(data, tuple):
        if len(data) == 2 and isinstance(data[0], str) and is_sensitive_key(data[0]):
            return (data[0], MASK)
        return tuple(walk(item) for item in data)
    if isinstance(data, (set, frozenset)):
        return type(data)(walk(item) for item in data)
    return data
