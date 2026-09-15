from typing import Any
from urllib.parse import urlsplit

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


def is_cors_preflight(request: Any, endpoint: Any) -> bool:
    return request.httprequest.method == "OPTIONS" and bool(
        endpoint.routing.get("cors", False)
    )


def _get_origin_parts(url: str) -> tuple[str, str, int | None] | None:
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if not parts.hostname:
        return None
    try:
        port = parts.port
    except ValueError:
        return None
    return parts.scheme, parts.hostname, port


def resolve_cors_same_host(request: Any) -> str | None:
    origin = request.httprequest.headers.get("Origin")
    if not origin:
        return None
    theirs = _get_origin_parts(origin)
    ours = _get_origin_parts(request.httprequest.host_url)
    if theirs is None or ours is None:
        _debug.logic("http.cors.same_host", allowed=False, reason="unparsable")
        return None
    if theirs[1:] != ours[1:]:
        _debug.logic("http.cors.same_host", allowed=False, reason="host_mismatch")
        return None
    if theirs[0] != ours[0] and request.httprequest.is_secure:
        _debug.logic("http.cors.same_host", allowed=False, reason="scheme_downgrade")
        return None
    _debug.logic("http.cors.same_host", allowed=True, origin=origin)
    return origin
