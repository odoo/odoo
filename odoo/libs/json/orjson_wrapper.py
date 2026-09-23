import datetime
import json as _json
import math
from collections.abc import Callable
from typing import Any

import orjson as _orjson

__all__ = [
    "OPT_INDENT_2",
    "OPT_SORT_KEYS",
    "dumps",
    "dumps_bytes",
    "loads",
]

OPT_INDENT_2: int = _orjson.OPT_INDENT_2
OPT_SORT_KEYS: int = _orjson.OPT_SORT_KEYS

_DEFAULT_OPT = _orjson.OPT_NON_STR_KEYS | _orjson.OPT_PASSTHROUGH_DATETIME


def _orjson_shaped(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {_orjson_key(key): _orjson_shaped(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_orjson_shaped(item) for item in value]
    return value


def _orjson_key(key: Any) -> Any:
    if isinstance(key, (datetime.date, datetime.time)):
        return key.isoformat()
    return key


def _encode(obj: Any, default: Callable | None, option: int) -> bytes:
    try:
        return _orjson.dumps(obj, default=default, option=option)
    except TypeError as error:
        # orjson refuses what JSON can carry: an integer past 64 bits, and a
        # str holding a lone surrogate (text decoded with surrogateescape).
        # The stdlib writes both; the payload keeps orjson's shape otherwise.
        if str(error) not in _STDLIB_CAN_WRITE:
            raise
    indent = 2 if option & _orjson.OPT_INDENT_2 else None
    return _json.dumps(
        _orjson_shaped(obj),
        default=default,
        indent=indent,
        separators=(",", ": ") if indent else (",", ":"),
        sort_keys=bool(option & _orjson.OPT_SORT_KEYS),
    ).encode()


_STDLIB_CAN_WRITE = frozenset(
    {
        "Integer exceeds 64-bit range",
        "str is not valid UTF-8: surrogates not allowed",
    }
)


def dumps(
    obj: Any,
    *,
    default: Callable | None = None,
    ensure_ascii: bool = False,
    option: int | None = None,
) -> str:
    if ensure_ascii:
        msg = "orjson cannot produce ASCII-escaped output; use stdlib json.dumps"
        raise ValueError(msg)
    return _encode(obj, default, _DEFAULT_OPT | (option or 0)).decode("utf-8")


def dumps_bytes(
    obj: Any,
    *,
    default: Callable | None = None,
    option: int | None = None,
) -> bytes:
    return _encode(obj, default, _DEFAULT_OPT | (option or 0))


def loads(s: str | bytes | bytearray | memoryview) -> Any:
    return _orjson.loads(s)
