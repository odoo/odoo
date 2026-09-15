from __future__ import annotations

import logging
import typing

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

CursorMode = typing.Literal["ro", "ro->rw", "rw"]


def is_readonly_cursor_enabled(settings: PoolSettings | None = None) -> bool:
    return resolve(settings).readonly_cursors


class ReplicaRouter:
    __slots__ = ("breaker", "lag", "primary", "readonly")

    def __init__(
        self,
        primary: Connection,
        readonly: Connection | None = None,
        *,
        max_lag: float = 0.0,
        breaker: CircuitBreaker | None = None,
        lag: ReplicaLagGate | None = None,
    ) -> None:
        self.primary = primary
        self.readonly = readonly
        self.breaker = (
            breaker
            if breaker is not None
            else CircuitBreaker(max_cooldown=REPLICA_RETRY_TIME)
        )
        self.lag = lag if lag is not None else ReplicaLagGate(max_lag)
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
        }

    def cursor(self, readonly: bool = False) -> tuple[BaseCursor, CursorMode]:
        if not readonly or self.readonly is None:
            return self.primary.cursor(), "rw"
        cr = self._resolve_replica_cursor(self.readonly)
        if cr is not None:
            _debug.logic(
                "replica.route", db=getattr(self.primary, "dbname", None), mode="ro"
            )
            return cr, "ro"
        _debug.logic(
            "replica.route",
            db=getattr(self.primary, "dbname", None),
            mode="ro->rw",
            breaker_closed=self.breaker.closed,
            lagging=not self.lag.is_replica_usable(),
        )
        return self.primary.cursor(), "ro->rw"

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
            cr = replica.cursor()
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
                "Replica %.1fs behind (db_replica_max_lag=%.1fs); serving "
                "readonly requests from the primary until it catches up",
                self.lag.last_lag,
                self.lag.max_lag,
            )
