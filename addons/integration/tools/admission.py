from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import werkzeug.wrappers
from werkzeug.exceptions import HTTPException

from odoo.http import request
from odoo.libs import redact

from .exchange_queue import queue_exchange_values
from .payload import compute_payload_hash, inspect_json_payload


class Refused(HTTPException):
    def __init__(
        self,
        status: int,
        reason: str,
        code: str,
        *,
        commit: bool = False,
        detail: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(description=reason)
        self.status = status
        self.reason = reason
        self.error_code = code
        self.detail = dict(detail or {})
        self.code = None if commit else status
        self.commit = commit

    @property
    def response(self) -> werkzeug.wrappers.Response:  # type: ignore[override]
        # Always rendered: whether the request commits is `code`'s to say.
        return self._render()

    @response.setter
    def response(self, value) -> None:
        pass

    def _render(self) -> werkzeug.wrappers.Response:
        render = getattr(request, "receiver_refusal", None) if request else None
        if render is not None:
            return render(self)
        return self._problem_response()

    def problem(self) -> dict[str, Any]:
        return {
            "type": f"urn:odoo:inbound:{self.error_code}",
            "title": self.error_code.replace("_", " "),
            "status": self.status,
            "detail": self.reason,
            "error": self.error_code,
            "message": self.reason,
            **self.detail,
        }

    def _problem_response(self) -> werkzeug.wrappers.Response:
        return werkzeug.wrappers.Response(
            json.dumps(self.problem()),
            status=self.status,
            content_type="application/problem+json; charset=utf-8",
        )

    def get_response(self, environ=None, scope=None) -> werkzeug.wrappers.Response:  # type: ignore[override]
        return self._render()


class Acknowledged(HTTPException):
    code = None

    def __init__(
        self, body: str = "", status: int = 200, content_type: str = "text/plain"
    ) -> None:
        super().__init__(
            response=werkzeug.wrappers.Response(
                body, status=status, content_type=content_type
            )
        )

    @classmethod
    def json(cls, value: Any, status: int = 200) -> Acknowledged:
        return cls(json.dumps(value), status, "application/json; charset=utf-8")

    @classmethod
    def redirect(cls, location: str, status: int = 303) -> Acknowledged:
        acknowledged = cls("", status)
        acknowledged.response.headers["Location"] = location
        return acknowledged


@dataclass
class Admission:
    gate: Any
    subject: Any
    body: bytes
    remote_addr: str | None
    event_type: str | None = None
    method: str = "POST"
    path: str = ""
    user_agent: str | None = None
    auth_mode: str = "enforce"
    event_id: str | None = None
    exchange: Any = None
    extra: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    annotations: dict[str, Any] = field(default_factory=dict)
    started: float = field(default_factory=time.monotonic)
    settled: bool = False
    _payload: Any = field(default=None, repr=False)
    _payload_error: str | None = field(default=None, repr=False)
    _payload_read: bool = field(default=False, repr=False)

    def _read_payload(self) -> None:
        if self._payload_read:
            return
        self._payload_read = True
        text = self.body.decode("utf-8", errors="replace")
        is_valid, parsed, error = inspect_json_payload(text)
        if is_valid:
            self._payload = parsed
        else:
            self._payload_error = error

    @property
    def payload(self) -> Any:
        self._read_payload()
        return self._payload

    @property
    def payload_hash(self) -> str:
        return compute_payload_hash(self.body.decode("utf-8", errors="replace"))

    def json(self) -> dict[str, Any]:
        self._read_payload()
        if not isinstance(self._payload, dict):
            self.refuse(
                400,
                self._payload_error or "the request body is not a JSON object",
                "invalid_json",
            )
        return self._payload

    def refuse(self, status: int, reason: str, code: str) -> None:
        self.settle(reason)
        raise Refused(status, reason, code, commit=True)

    def retag(self, event_type: str) -> None:
        """Name the event once the body says what it is."""
        self.event_type = event_type
        if self.exchange is not None:
            self.exchange.event_type = event_type

    def keep(self) -> None:
        """A withheld call that turned out to be worth a row: a poll that
        delivered something. Opens the row now, with what was annotated."""
        if self.exchange is not None:
            return
        self.gate._open_inbound_exchange(self, self.event_type)
        if self.annotations:
            self.exchange.write(self.annotations)

    def annotate(self, **vals: Any) -> None:
        """What the handler learnt about the call that the gate could not:
        the user it ran as, the record it touched, what it did."""
        self.annotations.update(vals)
        if self.exchange is not None:
            self.exchange.write(vals)

    @property
    def elapsed_ms(self) -> float:
        return (time.monotonic() - self.started) * 1000

    def settle(self, error: str | None = None, *, retry: bool = False) -> None:
        self.error = error
        self.settled = True
        if self.exchange is None:
            if error:
                self._record_withheld_failure(error)
            return
        if error:
            if retry:
                # the retry cron replays the row, so it keeps the body as
                # received, as an async work item does, not the log copy
                self.exchange.request_payload = self.body.decode(
                    "utf-8", errors="replace"
                )
            self.exchange.mark_failed(redact.mask_text(error), schedule_retry=retry)
        else:
            self.exchange.mark_success()
        self.exchange.duration_ms = self.elapsed_ms

    def _record_withheld_failure(self, error: str) -> None:
        """A call whose kind leaves no row still leaves one when it fails."""
        vals = {
            **self.gate._inbound_exchange_vals(self, self.event_type),
            **self.annotations,
            "state": "failed",
            "error_type": "other",
            "error_message": redact.mask_text(error),
            "duration_ms": self.elapsed_ms,
        }
        queue_exchange_values(self.gate.env, vals)


@dataclass
class Resolution:
    subject: Any
    extra: dict[str, Any] = field(default_factory=dict)
    gate: Any = None
    verify: Callable[[Mapping[str, Any], bytes], bool] | None = None
    claimed: str | None = None
    # The sender's own id for the event, when the resolver read one: the
    # row claims it, and a redelivery is refused as a duplicate.
    event_id: str | None = None
