"""orjson wrapper with stdlib json fallback."""

import json as _json
from collections.abc import Callable
from typing import Any

__all__ = [
    "OPT_SORT_KEYS",
    "ORJSON_AVAILABLE",
    "dumps",
    "dumps_bytes",
    "loads",
]

ORJSON_AVAILABLE: bool

try:
    import orjson as _orjson

    ORJSON_AVAILABLE = True
    OPT_SORT_KEYS: int = _orjson.OPT_SORT_KEYS

    # Match stdlib json behavior: auto-convert non-string keys (int, etc.) to str.
    # Without this, orjson raises TypeError for dicts like {1: "value"} which are
    # common in Odoo (record IDs as keys, field metadata, etc.).
    # OPT_PASSTHROUGH_DATETIME: route datetime/date objects through the
    # ``default`` handler instead of orjson's native ISO serialization.
    # Odoo's JS client expects space-separated format ("2026-02-15 10:30:00"),
    # not ISO with T ("2026-02-15T10:30:00").  The orjson_default handler in
    # odoo.tools.json converts via fields.Datetime.to_string().
    _DEFAULT_OPT = _orjson.OPT_NON_STR_KEYS | _orjson.OPT_PASSTHROUGH_DATETIME

    def dumps(
        obj: Any,
        *,
        default: Callable | None = None,
        ensure_ascii: bool = False,
        option: int | None = None,
    ) -> str:
        """Serialize ``obj`` to a JSON string.

        Always returns ``str`` (not bytes) for stdlib json compatibility.
        The ``ensure_ascii`` parameter is accepted but ignored — orjson
        always produces UTF-8.
        """
        raw = _orjson.dumps(obj, default=default, option=_DEFAULT_OPT | (option or 0))
        return raw.decode("utf-8")

    def dumps_bytes(
        obj: Any,
        *,
        default: Callable | None = None,
        option: int | None = None,
    ) -> bytes:
        """Serialize ``obj`` to JSON bytes (native orjson output).

        Use this when the consumer expects bytes (e.g. websocket, bus).
        """
        return _orjson.dumps(obj, default=default, option=_DEFAULT_OPT | (option or 0))

    def loads(s: str | bytes | bytearray | memoryview) -> Any:
        """Deserialize JSON string or bytes to a Python object."""
        return _orjson.loads(s)

except ImportError:
    ORJSON_AVAILABLE = False
    OPT_SORT_KEYS: int = 1 << 1  # Sentinel; matched by fallback dumps

    def dumps(  # type: ignore[misc]
        obj: Any,
        *,
        default: Callable | None = None,
        ensure_ascii: bool = False,
        option: int | None = None,
    ) -> str:
        sort_keys = bool(option and option & OPT_SORT_KEYS)
        return _json.dumps(
            obj, default=default, ensure_ascii=ensure_ascii, sort_keys=sort_keys
        )

    def dumps_bytes(  # type: ignore[misc]
        obj: Any,
        *,
        default: Callable | None = None,
        option: int | None = None,
    ) -> bytes:
        return _json.dumps(obj, default=default, ensure_ascii=False).encode("utf-8")

    def loads(s: str | bytes | bytearray | memoryview) -> Any:  # type: ignore[misc]
        return _json.loads(s)
