"""Typed service exceptions mapped to the OpenAPI ErrorEnvelope.

Every failure in the service surfaces as one of these; ``app/main.py``
registers exception handlers that serialize them to the documented
``{"error": {"code", "message", ...}}`` shape with the correct HTTP status.
"""


class ServiceError(Exception):
    """Base class for all invoice-ai errors."""

    status_code: int = 500
    code: str = "E5000"

    def __init__(self, message: str = "", code: str | None = None,
                 retry_after_seconds: int | None = None, details: dict | None = None):
        super().__init__(message or self.code)
        self.message = message or self.code
        if code:
            self.code = code
        self.retry_after_seconds = retry_after_seconds
        self.details = details


class BadRequestError(ServiceError):
    status_code = 400
    code = "E4001"


class UploadTooLargeError(ServiceError):
    status_code = 413
    code = "E4131"


class UnsupportedMediaTypeError(ServiceError):
    status_code = 415
    code = "E4151"


class ExtractionValidationError(ServiceError):
    status_code = 422
    code = "E4221"


class ClaudeUpstreamError(ServiceError):
    status_code = 503
    code = "E5031"


class ClaudeRateLimitError(ClaudeUpstreamError):
    """Upstream Anthropic 429 surfaced as 503 to the Odoo client.

    The client contract (docs/openapi.yaml) treats *any* upstream AI
    provider failure — rate limit, 5xx, connection — as a 503 "service
    unavailable". The rate-limit nuance is preserved via
    ``retry_after_seconds`` in the envelope so Odoo can back off.
    """

    def __init__(self, message: str = "", retry_after_seconds: int | None = None):
        super().__init__(
            message=message,
            retry_after_seconds=retry_after_seconds,
        )


class RAGUnavailableError(ServiceError):
    """RAG retrieval or database is unavailable — surfaced as 503."""

    status_code = 503
    code = "E5033"

    def __init__(self, message: str = "", retry_after_seconds: int | None = None):
        super().__init__(
            message=message,
            retry_after_seconds=retry_after_seconds,
        )
