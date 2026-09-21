from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import werkzeug.wrappers
from werkzeug.exceptions import HTTPException


class Refused(HTTPException):
    """An inbound request the gate did not admit: the status is the gate's
    verdict and the body a problem document, so every open route refuses the
    same way whatever it serves once admitted."""

    def __init__(self, status: int, reason: str, code: str) -> None:
        super().__init__(description=reason)
        self.code = status
        self.reason = reason
        self.error_code = code

    def get_response(self, environ=None, scope=None) -> werkzeug.wrappers.Response:  # type: ignore[override]
        return werkzeug.wrappers.Response(
            json.dumps(
                {
                    "type": f"urn:odoo:inbound:{self.error_code}",
                    "title": self.error_code.replace("_", " "),
                    "status": self.code,
                    "detail": self.reason,
                    "error": self.error_code,
                    "message": self.reason,
                }
            ),
            status=self.code,
            content_type="application/problem+json; charset=utf-8",
        )


class Acknowledged(HTTPException):
    """The request is not for any subject of ours but must be answered as if it
    were -- a vendor that retries and disables the endpoint on a non-2xx --
    so the resolver answers it here and no handler runs."""

    code = 200

    def __init__(
        self, body: str = "", status: int = 200, content_type: str = "text/plain"
    ) -> None:
        super().__init__(
            response=werkzeug.wrappers.Response(
                body, status=status, content_type=content_type
            )
        )
        self.code = status

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
    exchange: Any = None
    payload: dict[str, Any] | None = None
    payload_hash: str | None = None
    duplicate_of: Any = None
    extra: dict[str, Any] = field(default_factory=dict)

    def json(self) -> dict[str, Any]:
        if self.payload is None:
            raise Refused(400, "the request body is not a JSON object", "invalid_json")
        return self.payload
