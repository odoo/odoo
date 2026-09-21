import json
from functools import wraps

import orjson

from odoo.libs.debug_log import DebugLog
from odoo.libs.hashing import cache_hash

__all__ = ["versioned", "versioned_envelope"]

_debug = DebugLog(__name__)

_CANONICAL_OPT = orjson.OPT_SORT_KEYS | orjson.OPT_PASSTHROUGH_DATETIME


def _canonical_default(value):
    if isinstance(value, (set, frozenset)):
        return sorted(value, key=_canonical_bytes)
    return str(value)


def _canonical_bytes(value):
    try:
        return orjson.dumps(value, option=_CANONICAL_OPT, default=_canonical_default)
    except orjson.JSONEncodeError, TypeError:
        _debug.logic("cache_version.orjson_fallback", type=type(value).__name__)
        return json.dumps(
            value, sort_keys=True, default=_canonical_default, separators=(",", ":")
        ).encode()


def _canonical_digest(value):
    return cache_hash(_canonical_bytes(value))


def versioned(method):

    @wraps(method)
    def wrapper(*args, **kwargs):
        result = method(*args, **kwargs)
        if isinstance(result, dict) and "__version" not in result:
            result = {**result, "__version": _canonical_digest(result)}
            _debug.perf.count(
                "cache_version.stamped", method=method.__qualname__, keys=len(result)
            )
        return result

    return wrapper


def versioned_envelope(method):

    @wraps(method)
    def wrapper(*args, **kwargs):
        result = method(*args, **kwargs)
        try:
            from odoo.http import request
        except ModuleNotFoundError:
            return result
        if request and _is_dispatched_call(request, method):
            request._response_version = _canonical_digest(result)  # type: ignore[attr-defined]
            _debug.perf.count(
                "cache_version.envelope_stamped", method=method.__qualname__
            )
        return result

    return wrapper


def _is_dispatched_call(request, method):
    # the envelope's version describes the response; a versioned method called
    # from inside another one (onchange snapshots its record through web_read)
    # would otherwise stamp its own digest onto a response it is not
    params = getattr(request, "params", None) or {}
    return params.get("method") == method.__name__
