from __future__ import annotations

import contextlib
import logging
import selectors
import time
import typing
from collections.abc import Iterable, Iterator, Sized

from odoo import db
from odoo.db import is_maintenance_db
from odoo.libs import backoff
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, OrderedSet
from odoo.tools.constants import CRON_TRIGGER_CHANNEL, JOB_QUEUE_CHANNEL

from ._dispatch import get_static_dbfilter
from ._limits import BACKOFF_BASE_S, BACKOFF_CEILING_S
from .db import list_dbs
from .settings import current

if typing.TYPE_CHECKING:
    from odoo.db import BaseCursor

_logger = logging.getLogger("odoo.service.server")
_debug = DebugLog(__name__)

__all__ = [
    "CRON_NOTIFY_JITTER_MAX_S",
    "CRON_POLL_INTERVAL_S",
    "CRON_TRIGGER_CHANNEL",
    "JOB_QUEUE_CHANNEL",
    "CronListener",
    "CronSchedule",
    "ReconnectBackoff",
    "arm_cron_listen",
    "close_cron_cursor",
    "drain_cron_notifies",
    "drain_swept_database",
    "get_cron_databases",
    "open_cron_listener",
    "order_notified_first",
]

CRON_POLL_INTERVAL_S = 60
"""How long a cron or job loop waits for a notify before sweeping anyway.

Named for what it is.  As `SLEEP_INTERVAL` in `_cron` it read as a generic
number and was borrowed by the back-off ceiling and by the threaded server's
reload grace period, so the three could not be tuned apart.
"""

CRON_NOTIFY_JITTER_MAX_S = 0.1


def arm_cron_listen(
    cr: BaseCursor,
    logger: logging.Logger,
    *,
    channel: str = CRON_TRIGGER_CHANNEL,
    disable_idle_timeout: bool = False,
) -> bool:
    cr.execute("SELECT pg_is_in_recovery()")
    recovery = cr.fetchone()
    if recovery and recovery[0]:
        logger.warning("PG cluster in recovery mode, %s trigger not activated", channel)
        _debug.logic("cron.listen.in_recovery", channel=channel)
        return False
    if disable_idle_timeout:
        cr.execute("SET idle_session_timeout = 0")
    cr.execute(SQL("LISTEN %s", SQL.identifier(channel)))
    _debug.lifecycle(
        "cron.listen_armed",
        channel=channel,
        idle_timeout_disabled=disable_idle_timeout,
    )
    return True


def drain_cron_notifies(
    connection: typing.Any, *, channel: str = CRON_TRIGGER_CHANNEL
) -> OrderedSet:
    notifies = list(connection.notifies(timeout=0))
    payloads = OrderedSet(
        notif.payload for notif in notifies if notif.channel == channel
    )
    if _debug.pipeline.enabled and notifies:
        _debug.pipeline(
            "cron.notifies_drained",
            channel=channel,
            received=len(notifies),
            distinct=len(payloads),
        )
    return payloads


def order_notified_first(notified: Iterable[str], all_dbs: Iterable[str]) -> list[str]:
    if isinstance(notified, Iterator):
        notified = list(notified)
    all_list = list(all_dbs)
    all_set = set(all_list)
    notified_set = set(notified)
    emitted: set[str] = set()
    result: list[str] = []
    for name in notified:
        if name in all_set and name not in emitted:
            emitted.add(name)
            result.append(name)
    for name in all_list:
        if name not in notified_set and name not in emitted:
            emitted.add(name)
            result.append(name)
    _debug.logic(
        "cron.order_resolved",
        notified=len(notified_set),
        unknown=len(notified_set - all_set),
        total=len(result),
    )
    return result


def get_cron_databases() -> list[str]:
    configured = current().db_name
    if configured:
        _debug.logic("cron.databases", source="db_name", databases=len(configured))
        return list(configured)
    names = [name for name in list_dbs(True) if not is_maintenance_db(name)]
    dbfilter = get_static_dbfilter()
    if dbfilter is None:
        _debug.logic(
            "cron.databases", source="catalog", databases=len(names), filtered=False
        )
        return names
    matched = [name for name in names if dbfilter.match(name)]
    _debug.logic(
        "cron.databases",
        source="catalog",
        databases=len(matched),
        filtered=True,
        excluded=len(names) - len(matched),
    )
    return matched


def drain_swept_database(db_name: str) -> None:
    _debug.lifecycle("cron.database_drained", db=db_name)
    db.drain_db(db_name)


def close_cron_cursor(cursor: BaseCursor) -> None:
    with contextlib.suppress(Exception):
        cursor.close()


def open_cron_listener(channel: str, logger: logging.Logger) -> BaseCursor:
    cursor = db.db_connect("postgres").cursor()
    try:
        arm_cron_listen(cursor, logger, channel=channel, disable_idle_timeout=True)
        cursor.commit()
    except BaseException:
        _debug.logic("cron.listener.open_failed", channel=channel)
        close_cron_cursor(cursor)
        raise
    _debug.lifecycle("cron.listener.cursor_opened", channel=channel)
    return cursor


class ReconnectBackoff:
    def __init__(
        self, logger: logging.Logger, *, ceiling: int = BACKOFF_CEILING_S
    ) -> None:
        if ceiling < BACKOFF_BASE_S:
            raise ValueError(
                f"ceiling ({ceiling}) is below the {BACKOFF_BASE_S}s base, "
                f"which flattens the reconnect curve"
            )
        self._logger = logger
        self._ceiling = ceiling
        self.attempts = 0

    def reset(self) -> None:
        if _debug.lifecycle.enabled and self.attempts:
            _debug.lifecycle("cron.backoff_reset", attempts=self.attempts)
        self.attempts = 0

    def wait_after_failure(
        self,
        what: str,
        exc: BaseException,
        sleep: typing.Callable[[float], object] | None = None,
    ) -> None:
        self.attempts += 1
        delay = backoff.get_bound(self.attempts, base=BACKOFF_BASE_S, cap=self._ceiling)
        _debug.logic(
            "cron.backoff",
            what=what,
            attempt=self.attempts,
            delay_s=delay,
            error=type(exc).__name__,
        )
        self._logger.warning(
            "%s failed (attempt %d): %s; retrying in %ds",
            what,
            self.attempts,
            exc,
            delay,
        )
        (sleep or time.sleep)(delay)


class CronListener:
    def __init__(
        self,
        channel: str,
        logger: logging.Logger,
        *,
        extra_read_fd: int | None = None,
    ) -> None:
        self._channel = channel
        self._logger = logger
        self._extra_read_fd = extra_read_fd
        self._cursor: BaseCursor | None = None
        self._selector: selectors.BaseSelector | None = None
        self._backoff = ReconnectBackoff(logger)

    @property
    def connected(self) -> bool:
        return self._cursor is not None

    @property
    def connection_lost(self) -> bool:
        return self._cursor is None or self._cursor.connection.closed

    @property
    def backing_off(self) -> bool:
        return self._backoff.attempts > 0

    def connect(self) -> None:
        cursor = open_cron_listener(self._channel, self._logger)
        selector = None
        try:
            selector = selectors.DefaultSelector()
            if self._extra_read_fd is not None:
                selector.register(self._extra_read_fd, selectors.EVENT_READ)
            selector.register(cursor.connection, selectors.EVENT_READ)
        except BaseException as exc:
            _debug.logic(
                "cron.listener.selector_failed",
                channel=self._channel,
                error=type(exc).__name__,
            )
            if selector is not None:
                with contextlib.suppress(Exception):
                    selector.close()
            close_cron_cursor(cursor)
            raise
        self.close()
        self._cursor = cursor
        self._selector = selector
        self._backoff.reset()
        _debug.lifecycle(
            "cron.listener.connected",
            channel=self._channel,
            extra_fd=self._extra_read_fd is not None,
        )

    def reconnect_after_failure(
        self,
        what: str,
        sleep: typing.Callable[[float], object] | None = None,
    ) -> bool:
        self.close()
        try:
            self.connect()
        except Exception as exc:
            _debug.logic(
                "cron.listener.reconnect_failed", what=what, error=type(exc).__name__
            )
            self._backoff.wait_after_failure(what, exc, sleep)
            return False
        return True

    def wait(self, timeout: float) -> bool:
        if self._selector is None:
            return False
        with _debug.perf(
            "cron.listener.waited", channel=self._channel, timeout=timeout
        ) as span:
            ready = self._selector.select(timeout=timeout)
            span.set(woken=bool(ready))
        return bool(ready)

    def drain(self) -> OrderedSet:
        if self._cursor is None:
            _debug.logic("cron.listener.drain_before_connect", channel=self._channel)
            raise RuntimeError("CronListener.drain() before connect()")
        return drain_cron_notifies(self._cursor.connection, channel=self._channel)

    def close(self) -> None:
        selector, self._selector = self._selector, None
        if selector is not None:
            with contextlib.suppress(Exception):
                selector.close()
        cursor, self._cursor = self._cursor, None
        if cursor is not None:
            close_cron_cursor(cursor)
            _debug.lifecycle("cron.listener.closed", channel=self._channel)


class CronSchedule:
    def __init__(
        self,
        list_databases: typing.Callable[[], typing.Iterable[str]] | None = None,
        *,
        refresh_interval: float = CRON_POLL_INTERVAL_S,
        clock: typing.Callable[[], float] | None = None,
    ) -> None:
        self._list_databases = list_databases
        self._refresh_interval = refresh_interval
        self._clock = clock or time.monotonic
        self._known: OrderedSet[str] = OrderedSet()
        self._listed_at = float("-inf")
        self._relisted_for_unknown = False

    @property
    def known(self) -> OrderedSet[str]:
        return self._known

    def _is_stale(self) -> bool:
        return self._clock() - self._listed_at >= self._refresh_interval

    @property
    def polling_delay(self) -> float:
        """Bound listener sleep by the next sweep, including the first one."""
        return max(0.0, self._listed_at + self._refresh_interval - self._clock())

    def _list_known_databases(self, reason: str) -> OrderedSet[str]:
        previous = self._known
        # Late-bound so a patch on `get_cron_databases` scopes every sweep.
        list_databases = self._list_databases or get_cron_databases
        self._known = OrderedSet(list_databases())
        _debug.logic(
            "cron.schedule.databases_listed",
            reason=reason,
            databases=len(self._known),
            added=len(set(self._known) - set(previous)),
            removed=len(set(previous) - set(self._known)),
        )
        return self._known

    def reset_known_databases(self) -> OrderedSet[str]:
        self._listed_at = self._clock()
        self._relisted_for_unknown = False
        return self._list_known_databases("sweep")

    def _admit_unknown_databases(self, notified: Iterable[str]) -> None:
        # A database created since the last sweep notifies under a name the
        # list has never seen; one re-read per interval admits it now rather
        # than on the next sweep, while a storm of unknown names stays one scan.
        if self._relisted_for_unknown or all(n in self._known for n in notified):
            return
        self._relisted_for_unknown = True
        self._list_known_databases("unknown_notified")

    def get_due_databases(self, notified: Iterable[str]) -> list[str]:
        if not isinstance(notified, Sized):
            notified = list(notified)
        stale = self._is_stale()
        if stale:
            due = order_notified_first(notified, self.reset_known_databases())
        else:
            self._admit_unknown_databases(notified)
            due = [name for name in notified if name in self._known]
        _debug.pipeline(
            "cron.schedule.due",
            due=len(due),
            notified=len(notified),
            known=len(self._known),
            swept_all=stale,
        )
        return due
