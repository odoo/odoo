from __future__ import annotations

import json
import logging
import re
import typing
from urllib.parse import unquote_plus, urlparse, urlunparse

if typing.TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "MASK",
    "REGISTERED_PATTERNS",
    "dump_masked",
    "find_secret_shapes",
    "is_sensitive_key",
    "mask_data",
    "mask_text",
    "mask_url",
    "register_pattern",
]

_logger = logging.getLogger(__name__)

MASK = "***REDACTED***"

_SENSITIVE_KEY_FRAGMENTS: tuple[str, ...] = (
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
    ("bearer_token", re.compile(r"(?i:(?<=\bbearer\s))\s*[A-Za-z0-9._~+/-]{8,}=*")),
)

_SECRET_SHAPES: tuple[tuple[str, re.Pattern[str]], ...] = (
    *((name, re.compile(pattern, re.IGNORECASE)) for name, pattern in _LABEL_SHAPES),
    *_VALUE_SHAPES,
)

REGISTERED_PATTERNS: list[
    tuple[re.Pattern[str], str | Callable[[re.Match[str]], str]]
] = []

_URL_IN_TEXT = re.compile(r"https?://[^\s'\"<>]+")

# "auth" is a fragment everywhere but in "author", which names a person
_SENSITIVE_KEY = re.compile(
    "|".join(
        "auth(?!or)" if fragment == "auth" else re.escape(fragment)
        for fragment in _SENSITIVE_KEY_FRAGMENTS
    )
)

# A key is one identifier run, found at its start only, so a run is scanned
# once however many fragments repeat in it; it is sensitive when a fragment
# is followed by nothing or by further _/- segments, as in secret_key.
_KEY_CANDIDATE = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]++(?=[\"']?\s*[:=])")
_SENSITIVE_KEY_TAIL = re.compile(
    "(?:"
    + "|".join(
        "auth(?!or)" if fragment == "auth" else re.escape(fragment)
        for fragment in _SENSITIVE_KEY_FRAGMENTS
    )
    + ")(?=[_-]|$)"
)
_KEY_VALUE_AFTER = re.compile(
    r"(?i)(?P<sep>[\"']?\s*[:=]\s*)"
    r"(?:(?P<quote>[\"'])(?:\\[\s\S]?|(?!(?P=quote))[^\\])*(?:(?P=quote)|\Z)"
    r"|(?P<scheme>(?:bearer|basic|digest|token)\s+)?(?P<bare>[^\s&;'\"<>]+))"
)

_PAIR_LABEL_KEYS = ("name", "key", "header", "field")


def register_pattern(
    pattern: str | re.Pattern[str],
    replacement: str | Callable[[re.Match[str]], str],
) -> None:
    compiled = re.compile(pattern) if isinstance(pattern, str) else pattern
    REGISTERED_PATTERNS.append((compiled, replacement))


def is_sensitive_key(key: object) -> bool:
    return _SENSITIVE_KEY.search(str(key).lower().replace("-", "_")) is not None


def find_secret_shapes(text: str) -> list[str]:
    if not text:
        return []
    return [name for name, pattern in _SECRET_SHAPES if pattern.search(text)]


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


# a sensitive word counting something (token_count, secret_length) whose value
# is a plain number carries no secret
_COUNTER_KEY = re.compile(r"(?:^|[_-])(?:count|total|length|len|size|limit|ttl)$")
_DIGITS = re.compile(r"\d+")


def _is_counter(key: object, value: typing.Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, str):
        if not _DIGITS.fullmatch(value):
            return False
    elif not isinstance(value, int):
        return False
    return _COUNTER_KEY.search(str(key).lower()) is not None


def _masks(key: object, value: typing.Any) -> bool:
    return is_sensitive_key(key) and not _is_counter(key, value)


def _mask_key_values(text: str) -> str:
    parts: list[str] = []
    done = 0
    for key in _KEY_CANDIDATE.finditer(text):
        if key.start() < done or not _SENSITIVE_KEY_TAIL.search(key[0].lower()):
            continue
        value = _KEY_VALUE_AFTER.match(text, key.end())
        if value is None or (
            value["bare"] is not None
            and value["scheme"] is None
            and _is_counter(key[0], value["bare"])
        ):
            continue
        parts.append(text[done : value.start()])
        parts.append(value["sep"])
        if value["quote"] is not None:
            parts.append(f"{value['quote']}{MASK}{value['quote']}")
        else:
            parts.append(f"{value['scheme'] or ''}{MASK}")
        done = value.end()
    parts.append(text[done:])
    return "".join(parts)


# A bounded mask reads this much past the limit, so a secret straddling the
# cut is still matched whole: every fixed-length shape is far shorter, and the
# open-ended ones (a quoted value, a PEM block) match to the end of the window.
_WINDOW_MARGIN = 4096


def mask_text(text: str, limit: int | None = None) -> str:
    if not text:
        return text
    if limit:
        return _mask_text(str(text)[: limit + _WINDOW_MARGIN])[:limit]
    return _mask_text(str(text))


def _mask_text(text: str) -> str:
    masked = _apply_registered(text)
    masked = _URL_IN_TEXT.sub(lambda match: mask_url(match.group(0)), masked)
    masked = _mask_key_values(masked)
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


class _BudgetSpent(Exception):
    pass


def _json_key(key: typing.Any) -> str:
    if isinstance(key, str):
        return key
    if key is True:
        return "true"
    if key is False:
        return "false"
    if key is None:
        return "null"
    if isinstance(key, (int, float)):
        return json.dumps(key)
    return str(key)


def _json_scalar(value: typing.Any) -> str:
    try:
        return json.dumps(value)
    except TypeError, ValueError:
        return json.dumps(str(value))


def _json_default(value: typing.Any) -> typing.Any:
    if isinstance(value, (set, frozenset)):
        return list(value)
    return str(value)


def dump_masked(
    data: typing.Any, max_bytes: int | None = None, *, max_depth: int = 50
) -> str:
    limit = max_bytes or None
    if limit is None:
        # nothing to stop early for: the C encoder over the masked copy is faster
        try:
            return json.dumps(
                mask_data(data, max_depth=max_depth), default=_json_default
            )
        except TypeError, ValueError:
            pass
    parts: list[str] = []
    used = 0

    def write(chunk: str) -> None:
        nonlocal used
        parts.append(chunk)
        used += len(chunk)
        if limit is not None and used > limit:
            raise _BudgetSpent

    def emit(value: typing.Any, depth: int) -> None:
        if isinstance(value, str):
            window = None if limit is None else max(limit - used, 1)
            write(json.dumps(mask_text(value, window) if window else mask_text(value)))
            return
        if value and depth > max_depth:
            _logger.warning(
                "Redaction depth limit (%s) exceeded; the structure below it is "
                "dropped",
                max_depth,
            )
            write(json.dumps("***REDACTED_DEEP_NESTING***"))
            return
        if isinstance(value, dict):
            pair = _is_sensitive_pair(value)
            write("{")
            for index, (key, item) in enumerate(value.items()):
                if index:
                    write(", ")
                write(json.dumps(_json_key(key)))
                write(": ")
                if _masks(key, item) or (pair and key == "value"):
                    write(json.dumps(MASK))
                else:
                    emit(item, depth + 1)
            write("}")
            return
        if isinstance(value, (list, tuple, set, frozenset)):
            if (
                isinstance(value, tuple)
                and len(value) == 2
                and isinstance(value[0], str)
                and is_sensitive_key(value[0])
            ):
                value = (value[0], MASK)
            write("[")
            for index, item in enumerate(value):
                if index:
                    write(", ")
                emit(item, depth + 1)
            write("]")
            return
        write(_json_scalar(value))

    try:
        emit(data, 0)
    except _BudgetSpent:
        return "".join(parts)[:limit]
    return "".join(parts)


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
                MASK if _masks(key, value) or (pair and key == "value") else walk(value)
            )
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [walk(item) for item in data]
    if isinstance(data, tuple):
        if len(data) == 2 and isinstance(data[0], str) and is_sensitive_key(data[0]):
            return (mask_text(data[0]), MASK)
        return tuple(walk(item) for item in data)
    if isinstance(data, (set, frozenset)):
        return type(data)(walk(item) for item in data)
    return data
