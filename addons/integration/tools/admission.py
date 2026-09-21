from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import werkzeug.wrappers
from werkzeug.exceptions import HTTPException

from odoo.http import request

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
    def response(self) -> werkzeug.wrappers.Response | None:  # type: ignore[override]
        if not self.commit:
            return None
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
    exchange: Any = None
    extra: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
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

    def settle(self, error: str | None = None, *, retry: bool = False) -> None:
        self.error = error
        if self.exchange is None:
            return
        if error:
            self.exchange.mark_failed(error, schedule_retry=retry)
        else:
            self.exchange.mark_success()


@dataclass
class Resolution:
    subject: Any
    extra: dict[str, Any] = field(default_factory=dict)
    gate: Any = None
    verify: Callable[[Mapping[str, Any], bytes], bool] | None = None
    claimed: str | None = None
