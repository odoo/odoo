from __future__ import annotations

from typing import Any

from odoo.libs.debug_log import DebugLog

from ._protocols import RequestState

_debug = DebugLog(__name__)


def rewind_uploaded_files(
    httprequest: Any, *, cause: BaseException | None = None
) -> None:
    rewound = 0  # debuglog
    for filename, file in httprequest.files.items(multi=True):
        if hasattr(file, "seekable") and file.seekable():
            file.seek(0)
            rewound += 1  # debuglog
        else:
            _debug.logic("http.upload.not_seekable", filename=filename)
            raise RuntimeError(
                f"Cannot retry request on input file {filename!r} after a "
                f"transaction error"
            ) from cause
    _debug.lifecycle(
        "http.upload.rewound",
        files=rewound,
        cause=None if cause is None else type(cause).__name__,
    )


class RequestRetryParticipant:
    __slots__ = ("_request",)

    def __init__(self, request: RequestState) -> None:
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
