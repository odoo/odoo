from __future__ import annotations

import threading
from time import monotonic

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ConnectionBudget:
    __slots__ = ("_cond", "_exhausted", "_in_use", "maxconn")

    def __init__(self, maxconn: int):
        if maxconn <= 0:
            raise ValueError(f"ConnectionBudget maxconn must be >= 1, got {maxconn}")
        self.maxconn = maxconn
        self._cond = threading.Condition(threading.Lock())
        self._in_use = 0
        self._exhausted = 0
        _debug.lifecycle("budget.created", maxconn=maxconn)

    def acquire(self, timeout: float) -> bool:
        endtime = None
        waited_since = 0.0  # debuglog
        with self._cond:
            while self._in_use >= self.maxconn:
                waited_since = waited_since or monotonic()  # debuglog
                if timeout == float("inf"):
                    self._cond.wait()
                    continue
                if endtime is None:
                    endtime = monotonic() + max(0.0, timeout)
                remaining = endtime - monotonic()
                if remaining <= 0 or not self._cond.wait(remaining):
                    if self._in_use < self.maxconn:
                        continue
                    self._exhausted += 1
                    _debug.logic(
                        "budget.exhausted",
                        maxconn=self.maxconn,
                        exhausted=self._exhausted,
                        waited_ms=(monotonic() - waited_since) * 1000.0,
                    )
                    return False
            self._in_use += 1
            if _debug.logic.enabled and self._in_use == self.maxconn:
                _debug.logic("budget.saturated", maxconn=self.maxconn)
            if _debug.perf.enabled and waited_since:
                _debug.perf.count(
                    "budget.waited",
                    maxconn=self.maxconn,
                    in_use=self._in_use,
                    waited_ms=(monotonic() - waited_since) * 1000.0,
                )
            return True

    def release(self) -> None:
        with self._cond:
            if self._in_use <= 0:
                _debug.logic("budget.over_released", maxconn=self.maxconn)
                raise ValueError("ConnectionBudget released more times than acquired")
            self._in_use -= 1
            self._cond.notify()

    @property
    def available(self) -> int:
        with self._cond:
            return self.maxconn - self._in_use

    @property
    def in_use(self) -> int:
        with self._cond:
            return self._in_use

    @property
    def exhausted_count(self) -> int:
        with self._cond:
            return self._exhausted

    def get_snapshot(self) -> dict[str, int]:
        with self._cond:
            in_use, exhausted = self._in_use, self._exhausted
        return {
            "budget_maxconn": self.maxconn,
            "budget_available": self.maxconn - in_use,
            "budget_in_use": in_use,
            "budget_exhausted": exhausted,
        }
