"""
Database connection pool management.

Uses psycopg_pool for production-grade connection pooling with health checks,
max_lifetime rotation, background workers, and pool statistics.
"""

import logging
import threading
from time import monotonic

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg_pool import ConnectionPool as _PsycopgPool
from psycopg_pool import PoolClosed, PoolTimeout

from odoo.release import MIN_PG_VERSION
import contextlib

_logger = logging.getLogger(__name__)
_logger_conn = _logger.getChild("connection")


class _SuppressKnownPoolWarnings(logging.Filter):
    """Suppress or demote known psycopg_pool warnings that are not real errors.

    1. ``keep_in_pool=False`` warnings: When connections are intentionally
       closed before returning to the pool, psycopg_pool logs a WARNING
       about "discarding closed connection".  This is expected.

    2. "database does not exist" reconnection warnings: After a database
       is dropped, the pool may still attempt to reconnect for up to
       ``reconnect_timeout`` seconds.  These warnings are noise — the
       caller will get a ``PoolTimeout`` and the pool will be cleaned up.
    """

    def filter(self, record):
        msg = record.getMessage()
        if "discarding closed connection" in msg:
            return False
        return not ("FATAL" in msg and "does not exist" in msg)


logging.getLogger("psycopg.pool").addFilter(_SuppressKnownPoolWarnings())

MAX_IDLE_TIMEOUT = 60 * 10


class PoolError(Exception):
    """Connection pool error."""


def _normalize_dsn_key(dsn: dict | str) -> frozenset:
    """Normalize a DSN to a hashable key for pool lookup.

    Aliases ``dbname`` → ``database``, ignores ``password`` and non-libpq keys.
    """
    alias_keys = {"dbname": "database"}
    ignore_keys = frozenset(("password",))
    if isinstance(dsn, str):
        dsn = conninfo_to_dict(dsn)
    return frozenset(
        (alias_keys.get(k, k), str(v))
        for k, v in dsn.items()
        if k not in ignore_keys and v is not None
    )


def _configure_connection(conn: psycopg.Connection) -> None:
    """Configure each new connection created by psycopg_pool.

    Adapters are registered globally at module level in utils.py,
    so no per-connection registration is needed.

    Prepared statement tuning: Odoo's ORM generates the same query
    shapes repeatedly (SELECT with same columns, UPDATE same fields).
    Auto-preparing after the 2nd execution (instead of default 5)
    skips parse+plan on subsequent calls.  A 500-statement LRU cache
    (instead of default 100) covers the hot ORM paths without bloat.
    PG18's improved plan-cache invalidation makes this safe.

    Per-session GUCs (jit, work_mem) are set via the ``options``
    connection parameter in :func:`_get_or_create_pool` to avoid
    cursor operations in this callback (which runs in pool worker
    threads and can interact badly with pool lifecycle).
    """
    if conn.info.server_version < MIN_PG_VERSION * 10000:
        sv = conn.info.server_version
        actual = f"{sv // 10000}.{sv % 10000}"
        raise PoolError(
            f"PostgreSQL {actual} is below the minimum required "
            f"{MIN_PG_VERSION}.0. Please upgrade to PostgreSQL "
            f"{MIN_PG_VERSION} or later."
        )

    # Prepared statement tuning (PG18-optimized)
    conn.prepare_threshold = 2
    conn.prepared_max = 500


def _reset_connection(conn: psycopg.Connection) -> None:
    """Reset connection state when returned to pool.

    psycopg_pool auto-rolls back active transactions before calling
    this. We reset session-level settings that Cursor.__init__ may
    have changed (isolation_level, read_only) and ensure autocommit
    is off for the next user. Using attribute assignment avoids a
    round-trip (unlike ``RESET ALL``).
    """
    conn.autocommit = False
    conn.isolation_level = None  # restore server default
    conn.read_only = None  # restore server default


class ConnectionPool:
    """Manages per-database psycopg_pool.ConnectionPool instances.

    Each unique DSN (database) gets its own psycopg_pool with:
    - Health checks on borrow (detects dead connections)
    - max_lifetime rotation (recycles connections every hour)
    - Background workers for connection creation
    - Pool statistics via get_stats()
    """

    def __init__(self, maxconn: int = 64, readonly: bool = False):
        self._pools: dict[frozenset, _PsycopgPool] = {}
        self._maxconn = max(maxconn, 1)
        self._readonly = readonly
        self._lock = threading.Lock()
        self._global_sem = threading.BoundedSemaphore(self._maxconn)

    def __repr__(self):
        # NB: get_stats() acquires internal locks — looks expensive, but
        # __repr__ is only evaluated by logging when DEBUG is enabled
        # (Python's logger lazily evaluates %r).  Acceptable at DEBUG.
        total = sum(p.get_stats().get("pool_size", 0) for p in self._pools.values())
        available = sum(
            p.get_stats().get("pool_available", 0) for p in self._pools.values()
        )
        used = total - available
        mode = "read-only" if self._readonly else "read/write"
        return f"ConnectionPool({mode};used={used}/total={total}/limit={self._maxconn};dbs={len(self._pools)})"

    @property
    def readonly(self) -> bool:
        return self._readonly

    def _debug(self, msg: str, *args):
        _logger_conn.debug(("%r " + msg), self, *args)

    def _get_or_create_pool(
        self, key: frozenset, connection_info: dict
    ) -> _PsycopgPool:
        """Get an existing pool for this DSN or create a new one."""
        pool = self._pools.get(key)
        if pool is not None and not pool.closed:
            return pool

        with self._lock:
            # Double-check after acquiring lock
            pool = self._pools.get(key)
            if pool is not None and not pool.closed:
                return pool

            # Build conninfo: extract DSN string if present, rest as kwargs.
            # psycopg_pool passes kwargs to psycopg.connect().
            kwargs = dict(connection_info)
            conninfo = kwargs.pop("dsn", "")
            kwargs["autocommit"] = False

            # Per-session GUCs optimized for Odoo's OLTP workload on PG18.
            # Set via libpq ``options`` so they're applied during connection
            # establishment — no cursor ops needed in the configure callback.
            # - jit=off: compilation overhead (5-50ms) dwarfs execution
            #   savings for Odoo's sub-10ms OLTP queries.
            # - work_mem=16MB: default 4MB causes disk-based sorts for
            #   search_read() with many2one joins + ordering.
            # - idle_session_timeout=15min (PG14+): server-side safety net
            #   for connections that escape pool management.  Set above
            #   pool max_idle (10min) so normal pool recycling takes
            #   precedence; the server only kills truly leaked sessions.
            # NB: these are intentionally hardcoded, not configurable.
            # They are specifically tuned for Odoo's OLTP profile —
            # exposing them in odoo.conf invites misconfiguration with
            # no real upside.  Override via postgresql.conf if needed.
            options = kwargs.get("options", "")
            kwargs["options"] = (
                f"{options} -c jit=off -c work_mem=16MB"
                f" -c idle_session_timeout=900000"
            ).strip()

            pool = _PsycopgPool(
                conninfo,
                connection_class=psycopg.Connection,
                kwargs=kwargs,
                min_size=0,
                max_size=self._maxconn,
                max_lifetime=3600,
                max_idle=MAX_IDLE_TIMEOUT,
                reconnect_timeout=15,
                configure=_configure_connection,
                reset=_reset_connection,
                check=_PsycopgPool.check_connection,
                num_workers=3,
                open=True,
            )
            self._pools[key] = pool
            self._debug("Created pool for %s", dict(key))
            return pool

    def borrow(self, connection_info: dict) -> psycopg.Connection:
        """Borrow a connection from the appropriate per-database pool.

        Acquires a slot from the global semaphore first, ensuring the total
        number of checked-out connections across all databases never exceeds
        ``maxconn``.  The 30-second timeout budget is shared between the
        semaphore wait and the per-database ``getconn()`` call.

        :param dict connection_info: dict of psql connection keywords
        :rtype: psycopg.Connection
        """
        key = _normalize_dsn_key(connection_info)
        pool = self._get_or_create_pool(key, connection_info)

        deadline = monotonic() + 30.0

        if not self._global_sem.acquire(timeout=30.0):
            raise PoolError(
                f"Could not acquire connection: global limit ({self._maxconn}) reached, "
                f"all connections are in use across {len(self._pools)} database(s)"
            )
        try:
            remaining = max(0.1, deadline - monotonic())
            try:
                conn = pool.getconn(timeout=remaining)
            except psycopg.Error as e:
                if isinstance(e, (PoolTimeout, PoolClosed)):
                    # Pool couldn't provide a connection — remove it so
                    # the next borrow() creates a fresh pool instead of
                    # hitting the same dead pool (e.g. after DB drop).
                    with self._lock:
                        if self._pools.get(key) is pool:
                            del self._pools[key]
                    try:
                        pool.close()
                    except Exception:
                        _logger.debug("Failed to close dead pool", exc_info=True)
                    _logger.info("Connection to the database failed: %s", e)
                    raise PoolError(str(e)) from e
                _logger.info("Connection to the database failed: %s", e)
                raise
            except Exception as e:
                raise PoolError(str(e)) from e
        except BaseException:
            self._global_sem.release()
            raise

        self._debug("Borrow connection backend PID %d", conn.info.backend_pid)
        return conn

    def give_back(self, connection: psycopg.Connection, keep_in_pool: bool = True):
        """Return a connection to its pool.

        Releases a slot from the global semaphore after returning the
        connection, ensuring the global limit is correctly maintained.

        :param connection: The connection to return
        :param keep_in_pool: If False, close the connection before returning
            it so the pool discards it (used for template databases).
        """
        self._debug("Give back connection to %r", connection.info.dsn)
        pool = getattr(connection, "_pool", None)
        if pool is None:
            # Connection not from a psycopg_pool (e.g. manually created)
            if not connection.closed:
                connection.close()
            return

        try:
            if not keep_in_pool:
                # Close the connection first; the pool detects the closed
                # connection and discards it, creating a replacement if needed.
                with contextlib.suppress(Exception):
                    connection.close()

            try:
                pool.putconn(connection)
            except Exception:
                _logger.debug("Failed to return connection to pool", exc_info=True)
        finally:
            self._global_sem.release()

    def close_all(self, dsn: dict | str | None = None):
        """Close pool(s) — by DSN or all.

        :param dsn: If given, close only the pool matching this DSN.
            If None, close all pools.
        """
        if dsn is not None:
            key = _normalize_dsn_key(dsn)
            with self._lock:
                pool = self._pools.pop(key, None)
            if pool:
                pool.close()
                _logger.info("%r: Closed pool for %s", self, dict(key))
        else:
            with self._lock:
                pools = list(self._pools.values())
                self._pools.clear()
            count = 0
            for pool in pools:
                pool.close()
                count += 1
            if count:
                _logger.info("%r: Closed %d pool(s)", self, count)

    def drain(self, dsn: dict | str | None = None):
        """Drain pool(s) — replace all idle connections with fresh ones.

        After module upgrades, idle connections may hold stale prepared
        statement caches referencing old schema.  ``drain()`` recycles
        them so the next borrow gets a freshly configured connection.

        :param dsn: If given, drain only the pool matching this DSN.
            If None, drain all pools.
        """
        if dsn is not None:
            key = _normalize_dsn_key(dsn)
            pool = self._pools.get(key)
            if pool and not pool.closed:
                pool.drain()
                _logger.debug("%r: Drained pool for %s", self, dict(key))
        else:
            for key, pool in self._pools.items():
                if not pool.closed:
                    pool.drain()
            if self._pools:
                _logger.debug("%r: Drained %d pool(s)", self, len(self._pools))

    def get_stats(self) -> dict[str, dict]:
        """Return pool statistics for all databases.

        Returns a dict keyed by database name with psycopg_pool stats.
        """
        stats = {}
        for key, pool in self._pools.items():
            db_name = dict(key).get("database", "unknown")
            stats[db_name] = pool.get_stats()
        return stats


class Connection:
    """A lightweight instance of a connection to postgres"""

    __slots__ = ('__dbname', '__dsn', '__pool')

    def __init__(self, pool: ConnectionPool, dbname: str, dsn: dict):
        self.__dbname = dbname
        self.__dsn = dsn
        self.__pool = pool

    @property
    def dsn(self) -> dict:
        dsn = dict(self.__dsn)
        dsn.pop("password", None)
        return dsn

    @property
    def dbname(self) -> str:
        return self.__dbname

    def cursor(self):
        """Create a new cursor for this connection.

        Note: Import is done here to avoid circular imports.
        """
        from .cursor import Cursor

        _logger.debug("create cursor to %r", self.dsn)
        return Cursor(self.__pool, self.__dbname, self.__dsn)
