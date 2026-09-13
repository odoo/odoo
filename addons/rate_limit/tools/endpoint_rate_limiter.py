import logging
from typing import Any

_logger = logging.getLogger(__name__)


class EndpointRateLimiter:
    def __init__(self, env: Any, endpoint: Any, company_id: int | None = None) -> None:
        self.env = env
        self.endpoint = endpoint
        self.company_id = company_id

    def check_limit(self) -> bool:
        if not getattr(self.endpoint, "rate_limit_enabled", False):
            return True

        allowed = self.env["rate.limit.bucket"].consume_for(
            self.endpoint,
            self.company_id,
            strict=bool(getattr(self.endpoint, "rate_limit_strict", False)),
        )

        if not allowed:
            _logger.warning(
                "Rate limit exceeded: model=%s, record_id=%s, company=%s",
                self.endpoint._name,
                self.endpoint.id,
                self.company_id or "global",
            )

        return allowed
