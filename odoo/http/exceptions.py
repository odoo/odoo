from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any, NoReturn

import werkzeug.exceptions
from werkzeug.exceptions import (
    BadGateway,
    BadRequest,
    Forbidden,
    GatewayTimeout,
    Gone,
    HTTPException,
    InternalServerError,
    Locked,
    MethodNotAllowed,
    NotFound,
    RequestEntityTooLarge,
    ServiceUnavailable,
    TooManyRequests,
    Unauthorized,
    UnprocessableEntity,
    UnsupportedMediaType,
)

from odoo.libs.debug_log import DebugLog

if TYPE_CHECKING:
    from .wrappers import Response

    type ErrorResponse = Response | HTTPException

_debug = DebugLog(__name__)


class RegistryError(RuntimeError):
    __module__ = "odoo.http"

    def __init__(
        self,
        message: str,
        *,
        db_absent: bool | None = None,
        transient: bool = False,
    ) -> None:
        super().__init__(message)
        self.db_absent = db_absent
        self.transient = transient


class SessionExpiredException(Exception):
    __module__ = "odoo.http"

    http_status: int = HTTPStatus.FORBIDDEN


class ParameterError(BadRequest):
    __module__ = "odoo.http"


def is_http_answer(exc: BaseException) -> bool:
    return (
        isinstance(exc, HTTPException)
        and exc.code is not None
        and exc.code < HTTPStatus.INTERNAL_SERVER_ERROR
    )


def abort(status: int | Response, *args: Any, **kwargs: Any) -> NoReturn:
    # A package Response is a proxy; werkzeug gets the response it wraps.
    target: Any = getattr(status, "_wrapped__", status)
    _debug.logic("http.abort", status=getattr(target, "status_code", target))
    werkzeug.exceptions.abort(target, *args, **kwargs)
    raise AssertionError("werkzeug.exceptions.abort returned")


def get_error_response(exc: BaseException) -> ErrorResponse | None:
    return getattr(exc, "error_response", None)


def set_error_response(exc: BaseException, response: ErrorResponse) -> None:
    carrier: Any = exc
    replaced = get_error_response(exc) is not None  # debuglog
    carrier.error_response = response
    _debug.lifecycle(
        "http.error_response.attached",
        error=type(exc).__name__,
        status=getattr(response, "status_code", None)
        or getattr(response, "code", None),
        replaced=replaced,
    )


__all__ = (
    "BadGateway",
    "BadRequest",
    "Forbidden",
    "GatewayTimeout",
    "Gone",
    "HTTPException",
    "InternalServerError",
    "Locked",
    "MethodNotAllowed",
    "NotFound",
    "ParameterError",
    "RegistryError",
    "RequestEntityTooLarge",
    "ServiceUnavailable",
    "SessionExpiredException",
    "TooManyRequests",
    "Unauthorized",
    "UnprocessableEntity",
    "UnsupportedMediaType",
    "abort",
    "get_error_response",
    "is_http_answer",
    "set_error_response",
)
