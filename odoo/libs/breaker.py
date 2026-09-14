from __future__ import annotations

import threading
from collections import deque
from time import monotonic

from odoo.libs.debug_log import DebugLog

__all__ = ["CircuitBreaker"]

_INITIAL_COOLDOWN = 1.0
_debug = DebugLog(__name__)

_PROBE_ABANDON_AFTER = 60.0


class CircuitBreaker:
    __slots__ = (
        "_cooldown",
        "_lock",
        "_open",
        "_opened_at",
        "_probing_since",
        "_recent_failures",
        "failure_threshold",
        "failure_window",
        "failures",
        "initial_cooldown",
        "max_cooldown",
        "trips",
    )

    def __init__(
        self,
        max_cooldown: float,
        initial_cooldown: float = _INITIAL_COOLDOWN,
        *,
        failure_threshold: int = 1,
        failure_window: float | None = None,
    ) -> None:
        if max_cooldown < initial_cooldown:
            raise ValueError(
                f"max_cooldown ({max_cooldown}) must be >= "
                f"initial_cooldown ({initial_cooldown})"
            )
        if failure_threshold < 1:
            raise ValueError(
                f"failure_threshold must be at least 1, got {failure_threshold}"
            )
        if failure_window is not None and failure_window <= 0:
            raise ValueError(f"failure_window must be positive, got {failure_window}")
        self.initial_cooldown = initial_cooldown
        self.max_cooldown = max_cooldown
        self.failure_threshold = failure_threshold
        self.failure_window = failure_window
        self._recent_failures: deque[float] = deque()
        self._lock = threading.Lock()
        self._open = False
        self._cooldown = 0.0
        self._opened_at = 0.0
        self._probing_since = 0.0
        self.failures = 0
        self.trips = 0
        _debug.lifecycle(
            "breaker.created",
            initial_cooldown=initial_cooldown,
            max_cooldown=max_cooldown,
            failure_threshold=failure_threshold,
            failure_window=failure_window,
        )

    @property
    def closed(self) -> bool:
        return not self._open

    @property
    def cooldown_remaining(self) -> float:
        with self._lock:
            return self._get_cooldown_remaining_locked()

    def _get_cooldown_remaining_locked(self) -> float:
        if not self._open:
            return 0.0
        return max(0.0, self._opened_at + self._cooldown - monotonic())

    def acquire_attempt(self) -> bool:
        with self._lock:
            if not self._open:
                return True
            now = monotonic()
            if now - self._opened_at < self._cooldown:
                _debug.logic(
                    "breaker.attempt_rejected",
                    reason="cooldown",
                    remaining_s=self._opened_at + self._cooldown - now,
                )
                return False
            if self._probing_since and now - self._probing_since < _PROBE_ABANDON_AFTER:
                _debug.logic(
                    "breaker.attempt_rejected",
                    reason="probe_in_flight",
                    probing_s=now - self._probing_since,
                )
                return False
            self._probing_since = now
            _debug.logic(
                "breaker.probe", cooldown=self._cooldown, failures=self.failures
            )
            return True

    def record_success(self) -> None:
        with self._lock:
            if _debug.lifecycle.enabled and self._open:
                _debug.lifecycle(
                    "breaker.closed", failures=self.failures, trips=self.trips
                )
            self._open = False
            self._cooldown = 0.0
            self._opened_at = 0.0
            self._probing_since = 0.0
            self._recent_failures.clear()
            self.failures = 0

    def _threshold_reached_locked(self, now: float) -> bool:
        recent = self._recent_failures
        recent.append(now)
        if self.failure_window is not None:
            while recent and now - recent[0] > self.failure_window:
                recent.popleft()
        while len(recent) > self.failure_threshold:
            recent.popleft()
        return len(recent) >= self.failure_threshold

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1
            if not self._open:
                if not self._threshold_reached_locked(monotonic()):
                    _debug.logic(
                        "breaker.failure_below_threshold",
                        recent=len(self._recent_failures),
                        threshold=self.failure_threshold,
                    )
                    return
                self._recent_failures.clear()
                self._open = True
                self._cooldown = self.initial_cooldown
                self._opened_at = monotonic()
                self._probing_since = 0.0
                self.trips += 1
                _debug.lifecycle(
                    "breaker.opened", cooldown=self._cooldown, trips=self.trips
                )
                return
            if _debug.logic.enabled and not self._probing_since:
                _debug.logic(
                    "breaker.failure_while_open",
                    failures=self.failures,
                    cooldown=self._cooldown,
                )
            if self._probing_since:
                self._cooldown = min(self._cooldown * 2, self.max_cooldown)
                self._opened_at = monotonic()
                self._probing_since = 0.0
                _debug.logic(
                    "breaker.cooldown_extended",
                    cooldown=self._cooldown,
                    failures=self.failures,
                )

    def get_snapshot(self) -> dict[str, bool | int | float | None]:
        with self._lock:
            closed = not self._open
            remaining = self._get_cooldown_remaining_locked()
            return {
                "closed": closed,
                "failures": self.failures,
                "trips": self.trips,
                "failure_threshold": self.failure_threshold,
                "failure_window_seconds": self.failure_window,
                "cooldown_seconds": round(self._cooldown, 3),
                "cooldown_remaining_seconds": round(remaining, 3),
            }
