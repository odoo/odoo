from __future__ import annotations

import logging
import re
import typing
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

if typing.TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "MASK",
    "REGISTERED_PATTERNS",
    "SECRET_SHAPES",
    "SENSITIVE_KEY_FRAGMENTS",
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
    "auth",
    "bearer",
    "signature",
    "x_amz_security_token",
    "x_amz_signature",
)

SECRET_SHAPES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern, re.IGNORECASE))
    for name, pattern in (
        ("password", r"\b(password|passwd|pwd)\s*[:=]\s*\S+"),
        ("api_key", r"\b(api[_-]?key|apikey)\s*[:=]\s*\S+"),
        ("secret_or_token", r"\b(secret|token)\s*[:=]\s*\S+"),
        ("aws_style_key", r"\b(access[_-]?key|secret[_-]?key)\s*[:=]\s*\S+"),
        ("private_key_pem", r"-----BEGIN\s+\w+\s+PRIVATE\s+KEY-----"),
        ("github_token", r"\bghp_[a-zA-Z0-9]{36}\b"),
        ("openai_api_key", r"\bsk-[a-zA-Z0-9]{48}\b"),
        ("aws_access_key_id", r"\bAKIA[0-9A-Z]{16}\b"),
    )
)

REGISTERED_PATTERNS: list[
    tuple[re.Pattern[str], str | Callable[[re.Match[str]], str]]
] = []

_VALUE_SHAPES: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"-----BEGIN[\w ]*PRIVATE KEY-----.*?(?:-----END[\w ]*PRIVATE KEY-----|\Z)",
        re.DOTALL,
    ),
    re.compile(r"\bghp_[a-zA-Z0-9]{36}\b"),
    re.compile(r"\bsk-[a-zA-Z0-9]{48}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
)

_URL_IN_TEXT = re.compile(r"https?://[^\s'\"<>]+")

_KEY_VALUE = re.compile(
    r"(?i)("
    + "|".join(re.escape(fragment) for fragment in SENSITIVE_KEY_FRAGMENTS)
    + r")(\s*[:=]\s*)([^\s&;'\"<>]+)",
)


def register_pattern(
    pattern: str | re.Pattern[str],
    replacement: str | Callable[[re.Match[str]], str],
) -> None:
    compiled = re.compile(pattern) if isinstance(pattern, str) else pattern
    REGISTERED_PATTERNS.append((compiled, replacement))


def is_sensitive_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS)


def find_secret_shapes(text: str) -> list[str]:
    if not text:
        return []
    return [name for name, pattern in SECRET_SHAPES if pattern.search(text)]


def _apply_registered(value: str) -> str:
    for pattern, replacement in REGISTERED_PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def mask_url(url: str) -> str:
    masked = _apply_registered(url)
    try:
        parsed = urlparse(masked)
    except ValueError:
        return masked

    netloc = parsed.netloc
    if "@" in netloc:
        netloc = f"***:***@{netloc.rsplit('@', 1)[1]}"

    query = parsed.query
    if query:
        query = urlencode(
            [
                (key, MASK if is_sensitive_key(key) else value)
                for key, value in parse_qsl(query, keep_blank_values=True)
            ]
        )

    return urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, query, parsed.fragment),
    )


def mask_text(text: str) -> str:
    if not text:
        return text
    masked = _apply_registered(str(text))
    masked = _URL_IN_TEXT.sub(lambda match: mask_url(match.group(0)), masked)
    masked = _KEY_VALUE.sub(rf"\1\2{MASK}", masked)
    for shape in _VALUE_SHAPES:
        masked = shape.sub(MASK, masked)
    return masked


def mask_data(data: typing.Any, *, max_depth: int = 50, _depth: int = 0) -> typing.Any:
    if not data:
        return data
    if _depth > max_depth:
        _logger.warning(
            "Redaction depth limit (%s) exceeded; the structure below it is dropped",
            max_depth,
        )
        return "***REDACTED_DEEP_NESTING***"
    if isinstance(data, dict):
        return {
            key: (
                MASK
                if is_sensitive_key(key)
                else mask_data(value, max_depth=max_depth, _depth=_depth + 1)
                if isinstance(value, (dict, list))
                else value
            )
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [
            mask_data(item, max_depth=max_depth, _depth=_depth + 1) for item in data
        ]
    return data
