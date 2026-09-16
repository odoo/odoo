from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import werkzeug.datastructures
import werkzeug.wrappers

from odoo.libs.debug_log import DebugLog

from ._protocols import get_ir_http
from .core import request

_debug = DebugLog(__name__)


def get_cookie_name(set_cookie_value: str) -> str:
    return set_cookie_value.partition("=")[0].strip()


def get_cookie_identity(value: str) -> tuple[str, str, str, bool]:
    # A Set-Cookie field contains one cookie followed by attributes. Unknown
    # attributes are ignored by browsers, not parsed as additional cookies.
    cookie, *attributes = value.split(";")
    scope = {}
    for attribute in attributes:
        key, _, content = attribute.partition("=")
        scope[key.strip().lower()] = content.strip()
    return (
        get_cookie_name(cookie),
        scope.get("domain", "").lower().lstrip("."),
        scope.get("path", ""),
        "partitioned" in scope,
    )


def _remove_duplicate_cookies(carrier: Any) -> None:
    staged = carrier.headers.getlist("Set-Cookie")
    newest = staged[-1]
    identity = get_cookie_identity(newest)
    kept = [cookie for cookie in staged[:-1] if get_cookie_identity(cookie) != identity]
    kept.append(newest)
    if len(kept) != len(staged):
        carrier.headers.setlist("Set-Cookie", kept)
        _debug.logic(
            "http.cookie.deduplicated",
            name=identity[0],
            dropped=len(staged) - len(kept),
        )


def _prepare_set_cookie_args(
    expires: datetime | int | None,
    max_age: int | None,
    cookie_type: str,
    secure: bool | None,
    samesite: str | None,
) -> tuple[datetime | int | None, int | None, bool, str | None]:
    if expires == -1:
        expires = datetime.now(tz=UTC) + timedelta(days=365)

    if (
        request
        and request.env is not None
        and not get_ir_http(request.env)._is_allowed_cookie(cookie_type)
    ):
        _debug.logic("http.cookie.consent_refused", cookie_type=cookie_type)
        max_age = 0
        expires = None

    if secure is None:
        secure = bool(request and request.httprequest.is_secure)
    if samesite is None:
        samesite = "Lax"

    return expires, max_age, secure, samesite


def _set_cookie_on(
    carrier: Any,
    key: str,
    value: str,
    max_age: int | None,
    expires: datetime | int | None,
    path: str | None,
    domain: str | None,
    secure: bool | None,
    httponly: bool,
    samesite: str | None,
    partitioned: bool,
    cookie_type: str,
) -> None:
    expires, max_age, secure, samesite = _prepare_set_cookie_args(
        expires,
        max_age,
        cookie_type,
        secure,
        samesite,
    )
    werkzeug.wrappers.Response.set_cookie(
        carrier,
        key,
        value=value,
        max_age=max_age,
        expires=expires,
        path=path,
        domain=domain,
        secure=secure,
        httponly=httponly,
        samesite=samesite,
        partitioned=partitioned,
    )
    # Compare the encoded domain/path that the browser receives, not the
    # caller's Unicode spelling. Serialize successfully before replacing a cookie.
    _remove_duplicate_cookies(carrier)


class FutureResponse:
    max_cookie_size = 4093

    def __init__(self) -> None:
        self.headers = werkzeug.datastructures.Headers()

    def set_cookie(
        self,
        key: str,
        value: str = "",
        max_age: int | None = None,
        expires: datetime | int | None = -1,
        path: str | None = "/",
        domain: str | None = None,
        secure: bool | None = None,
        httponly: bool = False,
        samesite: str | None = None,
        partitioned: bool = False,
        cookie_type: str = "required",
    ) -> None:
        _debug.lifecycle(
            "http.cookie.staged", key=key, max_age=max_age, cookie_type=cookie_type
        )
        _set_cookie_on(
            self,
            key,
            value,
            max_age,
            expires,
            path,
            domain,
            secure,
            httponly,
            samesite,
            partitioned,
            cookie_type,
        )
