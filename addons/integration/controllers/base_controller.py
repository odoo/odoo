import json
import logging
from dataclasses import dataclass
from typing import Any

from odoo.http import Response, request

_logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    success: bool
    endpoint: Any | None = None
    payload: dict[str, Any] | None = None
    payload_hash: str | None = None
    event_log: Any | None = None
    response: Response | None = None
    error_message: str | None = None


class BaseCommController:
    def _error_response(self, error_code: str, message: str, status: int) -> Response:
        return self._json_response(
            {"error": error_code, "message": message},
            status=status,
        )

    def _get_remote_address(self) -> str:
        if request.httprequest:
            return request.httprequest.remote_addr or "unknown"
        return "unknown"

    def _json_response(self, data: dict, status: int = 200) -> Response:
        return Response(
            json.dumps(data),
            status=status,
            mimetype="application/json",
            headers={
                "Content-Type": "application/json",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "Cache-Control": "no-store, no-cache, must-revalidate, private",
                "Pragma": "no-cache",
            },
        )

    def _log_request(
        self,
        endpoint: Any,
        success: bool,
        message: str,
        duration: float | None = None,
        error: str | None = None,
    ) -> None:
        level = logging.INFO if success else logging.ERROR
        status = "SUCCESS" if success else "FAILURE"

        _logger.log(
            level,
            "COMM_REQUEST_%s endpoint=%s model=%s duration=%.3fs message='%s' error='%s'",
            status,
            endpoint.display_name if endpoint else "unknown",
            endpoint._name if endpoint else "unknown",
            duration or 0.0,
            message,
            error or "",
        )
