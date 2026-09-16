from __future__ import annotations

import logging
import threading
import typing
import weakref
from time import monotonic

import psycopg

from odoo.libs.breaker import CircuitBreaker
from odoo.libs.debug_log import DebugLog

from .lag import LAG_SQL, ReplicaLagGate
from .pool import PoolError
from .settings import PoolSettings, resolve

if typing.TYPE_CHECKING:
    from .cursor import BaseCursor, Connection

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

REPLICA_RETRY_TIME = 20 * 60

# A replica borrow has a fallback, so it never waits out db_borrow_timeout:
# a dead replica cost the first read-only request the full 30 s, once per
# breaker half-open attempt (measured against a refused port). The probe's
# own connect timeout bounds the reachable-but-slow case.
REPLICA_BORROW_TIMEOUT = 5.0

CursorMode = typing.Literal["ro", "ro->rw", "rw"]


# Which sessions read from the primary for a while because they just wrote:
# a replica that has not applied a client's own commit would show that
# client its write as missing. Keyed by whatever the caller identifies a
# client by (the http layer passes the session id); pruned on insert past
# `_PRUNE_ABOVE` entries so an idle server does not keep every session ever
# seen.
class WritePins:
    __slots__ = ("_clock", "_deadlines", "_lock", "window")

    _PRUNE_ABOVE = 1024

    def __init__(
        self, window: float, *, clock: typing.Callable[[], float] = monotonic
    ) -> None:
        self.window = window
        self._clock = clock
        self._deadlines: dict[typing.Hashable, float] = {}
        self._lock = threading.Lock()

    def pin(self, key: typing.Hashable) -> None:
        if not self.window:
            return
        now = self._clock()
        with self._lock:
            self._deadlines[key] = now + self.window
            if len(self._deadlines) > self._PRUNE_ABOVE:
                self._deadlines = {k: d for k, d in self._deadlines.items() if d > now}
        # The key is a session id at the http call site: never log it.
        _debug.logic("replica.pinned", window=self.window, pinned=len(self._deadlines))

    def is_pinned(self, key: typing.Hashable) -> bool:
        deadline = self._deadlines.get(key)
        if deadline is None:
            return False
        if deadline > self._clock():
            return True
        with self._lock:
            if self._deadlines.get(key) == deadline:
                del self._deadlines[key]
        return False

    def __len__(self) -> int:
        now = self._clock()
        return sum(deadline > now for deadline in list(self._deadlines.values()))


def is_readonly_cursor_enabled(settings: PoolSettings | None = None) -> bool:
    return resolve(settings).readonly_cursors


# Every live router with a replica, so the health surface can report what
# the log lines say: a registry owns its router, and the registry table is
# the ORM's, which this package does not read.
_routers: weakref.WeakSet[ReplicaRouter] = weakref.WeakSet()


def get_replica_health() -> dict[str, dict]:
    return {
        getattr(router.primary, "dbname", None) or "unknown": router.get_health()
        for router in list(_routers)
    }


class ReplicaRouter:
    __slots__ = ("__weakref__", "breaker", "lag", "pins", "primary", "readonly")

    def __init__(
        self,
        primary: Connection,
        readonly: Connection | None = None,
        *,
        max_lag: float | None = None,
        breaker: CircuitBreaker | None = None,
        lag: ReplicaLagGate | None = None,
        write_pin: float | None = None,
    ) -> None:
        settings = resolve(None)
        if max_lag is None:
            max_lag = settings.replica_max_lag
        if write_pin is None:
            write_pin = settings.replica_write_pin
        self.primary = primary
        self.readonly = readonly
        self.pins = WritePins(write_pin)
        self.breaker = (
            breaker
            if breaker is not None
            else CircuitBreaker(max_cooldown=REPLICA_RETRY_TIME)
        )
        self.lag = lag if lag is not None else ReplicaLagGate(max_lag)
        if readonly is not None:
            _routers.add(self)
        _debug.lifecycle(
            "replica.router_created",
            db=getattr(primary, "dbname", None),
            replica=readonly is not None,
            max_lag=max_lag,
            own_breaker=breaker is None,
            own_lag_gate=lag is None,
        )

    def get_health(self) -> dict:
        return {
            "lag": self.lag.get_snapshot(),
            "breaker": self.breaker.get_snapshot(),
            "write_pins": len(self.pins),
        }

    def cursor(
        self, readonly: bool = False, *, pin_key: typing.Hashable | None = None
    ) -> tuple[BaseCursor, CursorMode]:
        if self.readonly is None:
            return self.primary.cursor(), "rw"
        if not readonly:
            return self._primary_cursor(pin_key), "rw"
        if pin_key is not None and self.pins.is_pinned(pin_key):
            _debug.logic(
                "replica.route",
                db=getattr(self.primary, "dbname", None),
                mode="ro->rw",
                reason="pinned",
            )
            return self._primary_cursor(pin_key), "ro->rw"
        cr = self._resolve_replica_cursor(self.readonly)
        if cr is not None:
            _debug.logic(
                "replica.route",
                db=getattr(self.primary, "dbname", None),
                mode="ro",
                pin_key=pin_key is not None,
            )
            return cr, "ro"
        _debug.logic(
            "replica.route",
            db=getattr(self.primary, "dbname", None),
            mode="ro->rw",
            breaker_closed=self.breaker.closed,
            lagging=not self.lag.is_replica_usable(),
        )
        return self._primary_cursor(pin_key), "ro->rw"

    # Every primary cursor handed out with a key can pin, whatever branch
    # chose the primary: http acquires read-only first and reuses the cursor
    # when the route writes, so a pinned or demoted request that writes must
    # refresh the pin or its next read lands on the replica unpinned.
    def _primary_cursor(self, pin_key: typing.Hashable | None) -> BaseCursor:
        primary = self.primary.cursor()
        if pin_key is not None and self.pins.window:
            primary.on_commit_if_written(lambda: self.pins.pin(pin_key))
        return primary

    def _resolve_replica_cursor(self, replica: Connection) -> BaseCursor | None:
        sample_due = self.lag.is_sample_due()
        if not (self.lag.is_replica_usable() or sample_due):
            _debug.logic("replica.skipped", reason="lagging", lag=self.lag.last_lag)
            return None
        if not self.breaker.acquire_attempt():
            _debug.logic(
                "replica.skipped",
                reason="breaker_open",
                cooldown_remaining_s=self.breaker.cooldown_remaining,
            )
            return None
        try:
            cr = replica.cursor(borrow_timeout=REPLICA_BORROW_TIMEOUT, fail_fast=True)
        except (psycopg.OperationalError, PoolError) as e:
            self.breaker.record_failure()
            _debug.lifecycle(
                "replica.cursor_failed",
                error=type(e).__name__,
                failures=self.breaker.failures,
                cooldown_s=self.breaker.cooldown_remaining,
            )
            _logger.warning(
                "Failed to open a readonly cursor, falling back to the "
                "read-write cursor and retrying the replica in %.0fs "
                "(failure %d)",
                self.breaker.cooldown_remaining,
                self.breaker.failures,
            )
            return None
        if not self.breaker.closed:
            _debug.lifecycle("replica.recovered", trips=self.breaker.trips)
            _logger.info("Replica reachable again, resuming readonly cursors")
        self.breaker.record_success()
        if sample_due and self.lag.acquire_sample_interval():
            self._sample_lag(cr)
        if self.lag.is_replica_usable():
            return cr
        _debug.logic("replica.cursor_discarded_lagging", lag=self.lag.last_lag)
        cr.close()
        return None

    def _sample_lag(self, cr: BaseCursor) -> None:
        try:
            with _debug.perf("replica.lag_query", cr=cr):
                cr.execute(LAG_SQL)  # noqa: E8501  LAG_SQL is a module constant
            row = cr.fetchone()
            measured = row[0] if row else None
        except Exception as e:
            _debug.logic("replica.lag_query_failed", error=type(e).__name__)
            _logger.debug("Could not measure replica lag", exc_info=True)
            measured = None
        was_usable = self.lag.is_replica_usable()
        self.lag.record(measured)
        usable = self.lag.is_replica_usable()
        if usable == was_usable:
            return
        _debug.lifecycle(
            "replica.lag_state_changed",
            usable=usable,
            lag=self.lag.last_lag,
            max_lag=self.lag.max_lag,
        )
        if usable:
            _logger.info(
                "Replica caught up (%.1fs behind); resuming readonly cursors",
                self.lag.last_lag,
            )
        else:
            _logger.warning(
                "Replica %s behind (db_replica_max_lag=%.1fs); serving "
                "readonly requests from the primary until it catches up",
                "an unknown amount (WAL outstanding, nothing replayed yet)"
                if self.lag.last_lag == float("inf")
                else f"{self.lag.last_lag:.1f}s",
                self.lag.max_lag,
            )
