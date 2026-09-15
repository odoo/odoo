import threading
from typing import Any

import requests

from odoo.libs.breaker import CircuitBreaker

from odoo.addons.rate_limit.tools import registry_singleton

CONNECTION_CONTEXT_KEY = "integration_egress_connection_id"

_BREAKERS_ATTRIBUTE = "_integration_connection_breakers"


class ConnectionUnavailable(requests.ConnectionError):
    """No call leaves: the connection's breaker is open or its budget is spent.

    A `requests.ConnectionError`, so every caller's existing handling of an
    unreachable provider applies unchanged.
    """


class _BreakerRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._breakers: dict[tuple, CircuitBreaker] = {}

    def get(
        self, connection_id: int, threshold: int, window: int, max_cooldown: int
    ) -> CircuitBreaker:
        key = (connection_id, threshold, window, max_cooldown)
        with self._lock:
            breaker = self._breakers.get(key)
            if breaker is None:
                for stale in [k for k in self._breakers if k[0] == connection_id]:
                    del self._breakers[stale]
                breaker = self._breakers[key] = CircuitBreaker(
                    max_cooldown=float(max(max_cooldown, 1)),
                    failure_threshold=max(threshold, 1),
                    failure_window=float(max(window, 1)),
                )
            return breaker


def breaker_for(env: Any, connection) -> CircuitBreaker:
    registry = registry_singleton(env, _BREAKERS_ATTRIBUTE, _BreakerRegistry)
    return registry.get(
        connection.id,
        connection.breaker_failure_threshold,
        connection.breaker_failure_window,
        connection.breaker_max_cooldown,
    )


def is_failure(response=None, error: BaseException | None = None) -> bool:
    if error is not None:
        return isinstance(error, (requests.ConnectionError, requests.Timeout))
    return response is not None and response.status_code >= 500
