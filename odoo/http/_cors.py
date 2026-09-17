import logging
from collections.abc import Collection, Mapping
from typing import Any
from urllib.parse import urlsplit

from odoo.libs.debug_log import DebugLog

from ._protocols import RequestState
from .constants import (
    CORS_DEFAULT_ALLOWED_HEADERS,
    CORS_MAX_AGE,
    DEFAULT_ALLOWED_METHODS,
    WILDCARD_CORS_CREDENTIALS_WARNING,
)

_logger = logging.getLogger(__name__)
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


def _get_cors_methods(
    dispatcher_methods: Collection[str] | None,
    routing: Mapping[str, Any],
) -> Collection[str]:
    methods = dispatcher_methods
    if methods is None:
        methods = routing.get("methods")
    if methods is None:
        # A route with no methods= accepts every verb at runtime; advertise
        # the same unrestricted set the Allow header uses, not a guess.
        return DEFAULT_ALLOWED_METHODS
    # An explicitly empty list means OPTIONS-only at runtime; an empty
    # Allow-Methods header would be malformed per the Fetch spec.
    return methods or ("OPTIONS",)


def stage_cors_headers(
    request: RequestState,
    routing: Mapping[str, Any],
    dispatcher_methods: Collection[str] | None,
) -> list[str]:
    cors = routing.get("cors")
    if not cors:
        return []

    set_header = request.future_response.headers.set
    vary: list[str] = []
    if callable(cors):
        vary.append("Origin")
        allow_origin = cors(request)
    else:
        allow_origin = cors
    if routing.get("cors_credentials"):
        if "Origin" not in vary:
            vary.append("Origin")
        origin = request.httprequest.headers.get("Origin")
        if allow_origin == "*":
            _logger.warning(WILDCARD_CORS_CREDENTIALS_WARNING, request.httprequest.path)
            _debug.logic(
                "http.cors.wildcard_credentials_refused",
                path=request.httprequest.path,
            )
            allow_origin = None
        elif origin and allow_origin == origin:
            set_header("Access-Control-Allow-Credentials", "true")
        else:
            allow_origin = None
    if allow_origin:
        set_header("Access-Control-Allow-Origin", allow_origin)
        set_header(
            "Access-Control-Allow-Methods",
            ", ".join(_get_cors_methods(dispatcher_methods, routing)),
        )
        expose = routing.get("cors_expose_headers")
        if expose:
            set_header(
                "Access-Control-Expose-Headers",
                expose if isinstance(expose, str) else ", ".join(expose),
            )
    _debug.logic(
        "http.cors.headers",
        allow_origin=bool(allow_origin),
        resolver=callable(cors),
        credentials=bool(routing.get("cors_credentials")),
        vary=len(vary),
    )
    return vary


def stage_preflight_headers(
    request: RequestState, routing: Mapping[str, Any]
) -> list[str]:
    set_header = request.future_response.headers.set
    set_header("Access-Control-Max-Age", CORS_MAX_AGE)
    allow_headers = routing.get("cors_allow_headers")
    _debug.logic(
        "http.cors.preflight",
        allow_headers="declared" if allow_headers is not None else "echoed",
    )
    if allow_headers is None:
        set_header(
            "Access-Control-Allow-Headers",
            request.httprequest.headers.get("Access-Control-Request-Headers")
            or CORS_DEFAULT_ALLOWED_HEADERS,
        )
        return ["Access-Control-Request-Headers"]
    set_header(
        "Access-Control-Allow-Headers",
        allow_headers if isinstance(allow_headers, str) else ", ".join(allow_headers),
    )
    return []
