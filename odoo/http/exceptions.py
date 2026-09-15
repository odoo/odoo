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


def abort(status: int | Response, *args: Any, **kwargs: Any) -> NoReturn:
    # Resolved per call: `wrappers` installs the Odoo `abort` on werkzeug after
    # this module is imported, so a name bound here at import time would be
    # werkzeug's original for the life of the process.
    werkzeug.exceptions.abort(status, *args, **kwargs)
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
    "set_error_response",
)
