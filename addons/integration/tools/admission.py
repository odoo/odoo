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
