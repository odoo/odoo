from __future__ import annotations

import typing

from odoo.libs.debug_log import DebugLog

from .helpers import rewind_uploaded_files

_debug = DebugLog(__name__)


class RequestRetryParticipant:
    __slots__ = ("_request",)

    def __init__(self, request: typing.Any) -> None:
        self._request = request

    def on_rollback(self, exc: BaseException) -> None:
        request = self._request
        request._restore_session_snapshot()
        _debug.lifecycle(
            "http.retry.session_restored",
            error=type(exc).__name__,
            uid=request.session.uid,
        )

    def on_retry(self, exc: BaseException) -> None:
        request = self._request
        rewind_uploaded_files(request.httprequest, cause=exc)
        reset = getattr(request, "_reset_for_replay", None)
        _debug.lifecycle(
            "http.retry.replay", error=type(exc).__name__, reset=reset is not None
        )
        if reset is not None:
            reset()

    def is_uncommitted_warning_suppressed(self) -> bool:
        return bool(getattr(self._request, "database_detached", False))
