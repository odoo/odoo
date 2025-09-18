"""
Database cursor classes for PostgreSQL transactions.

This module provides cursor classes that manage database transactions,
savepoints, and pre/post commit hooks.
"""

import itertools
import logging
import os
import re as _re
import threading
import warnings
from contextlib import contextmanager
from contextlib import nullcontext as _nullcontext
from datetime import datetime, timedelta
from decimal import Decimal as _Decimal
from inspect import currentframe
from typing import TYPE_CHECKING, Any, Self

import psycopg
from psycopg import IsolationLevel
from psycopg import sql as _sql

from odoo import tools
from odoo.libs.func import frame_codeinfo
from odoo.tools import SQL
from odoo.tools.misc import Callbacks, real_time

from .utils import categorize_query

# Rust-accelerated rows→dicts conversion (~2.5x faster than pure Python).
# Falls back to Python list comprehension when odoo_rust is not installed.
try:
    from odoo_rust import rows_to_dicts as _rows_to_dicts
except ImportError:
    _rows_to_dicts = None

if TYPE_CHECKING:
    from odoo.orm.runtime import Transaction

    from .pool import ConnectionPool

    # when type checking, the BaseCursor exposes methods of the psycopg cursor
    _CursorProtocol = psycopg.Cursor
else:
    _CursorProtocol = object

_logger = logging.getLogger(__name__)

# Global SQL query counter (used for debugging/profiling).
# Intentionally a bare int — not atomic.  Under --workers=0 (threaded),
# concurrent += can lose counts.  This is acceptable: the counter is
# approximate by design and adding a lock would slow every query for
# debug-only data.  In forked mode each worker has its own copy.
sql_counter: int = 0

# Cache: table name → sequence name for the id column.
# Populated lazily by Cursor.copy_from() when returning_ids=True.
_id_sequence_cache: dict[str, str] = {}

# Monotonic counter for savepoint names (thread-safe via CPython's GIL).
_savepoint_counter = itertools.count()

# Cache: (table, columns) → list of PostgreSQL type names.
# Used by binary COPY to provide exact types via set_types().
_column_type_cache: dict[tuple[str, tuple[str, ...]], list[str]] = {}

# DDL statements that must use client-side parameter formatting.
# PostgreSQL's extended query protocol only accepts $N parameters in
# value positions (WHERE, INSERT VALUES, etc.).  DDL structural
# positions (column types, constraints, comments, sequence options)
# reject parameterized values outright.
_RE_DDL = _re.compile(
    r"^\s*(?:CREATE|ALTER|DROP|COMMENT|GRANT|REVOKE|DO)\b",
    _re.IGNORECASE,
)
# First two uppercase chars of DDL keywords for fast prefix filtering.
# Avoids regex on the 99% of queries that are SELECT/INSERT/UPDATE/DELETE.
_DDL_PREFIXES = frozenset(("CR", "AL", "DR", "CO", "GR", "RE", "DO"))


class Savepoint:
    """Reifies an active breakpoint, allows :meth:`BaseCursor.savepoint` users
    to internally rollback the savepoint (as many times as they want) without
    having to implement their own savepointing, or triggering exceptions.

    Should normally be created using :meth:`BaseCursor.savepoint` rather than
    directly.

    The savepoint will be rolled back on unsuccessful context exits
    (exceptions). It will be released ("committed") on successful context exit.
    The savepoint object can be wrapped in ``contextlib.closing`` to
    unconditionally roll it back.

    The savepoint can also safely be explicitly closed during context body. This
    will rollback by default.

    :param BaseCursor cr: the cursor to execute the `SAVEPOINT` queries on
    """

    __slots__ = ("_cr", "closed", "name")

    def __init__(self, cr: _CursorProtocol):
        self.name = f"sp{next(_savepoint_counter)}"
        self._cr = cr
        self.closed: bool = False
        # NB: f-string SQL is safe here — name is always "sp{int}" from our
        # own counter, never user input.  psycopg.sql.Identifier would add
        # overhead (quote + adapt) for zero security benefit.
        cr.execute(f'SAVEPOINT "{self.name}"')

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close(rollback=exc_type is not None)

    def close(self, *, rollback: bool = True):
        if not self.closed:
            self._close(rollback)

    def rollback(self):
        self._cr.execute(f'ROLLBACK TO SAVEPOINT "{self.name}"')

    def _close(self, rollback: bool):
        if rollback:
            self.rollback()
        self._cr.execute(f'RELEASE SAVEPOINT "{self.name}"')
        self.closed = True


class _FlushingSavepoint(Savepoint):
    def __init__(self, cr: BaseCursor):
        cr.flush()
        super().__init__(cr)

    def rollback(self):
        assert isinstance(self._cr, BaseCursor)
        self._cr.clear()
        super().rollback()

    def _close(self, rollback: bool):
        assert isinstance(self._cr, BaseCursor)
        try:
            if not rollback:
                self._cr.flush()
        except Exception:
            rollback = True
            raise
        finally:
            super()._close(rollback)


# _CursorProtocol declares the available methods and type information,
# at runtime, it is just an `object`
class BaseCursor(_CursorProtocol):
    """Base class for cursors that manage pre/post commit hooks."""

    BATCH_SIZE = 1000  # max array size per = ANY() query — keeps planner efficient

    transaction: Transaction | None
    cache: dict[Any, Any]
    dbname: str

    def __init__(self) -> None:
        self.precommit = Callbacks()
        self.postcommit = Callbacks()
        self.prerollback = Callbacks()
        self.postrollback = Callbacks()
        self._now: datetime | None = None
        self.cache = {}
        # By default a cursor has no transaction object.  A transaction object
        # for managing environments is instantiated by registry.cursor().  It
        # is not done here in order to avoid cyclic module dependencies.
        self.transaction = None

    def flush(self) -> None:
        """Flush the current transaction, and run precommit hooks."""
        # In case some pre-commit added another pre-commit or triggered changes
        # in the ORM, we must flush and run it again.
        for _ in range(10):  # limit number of iterations
            if self.transaction is not None:
                self.transaction.flush()
            if not self.precommit:
                break
            self.precommit.run()
        else:
            _logger.warning("Too many iterations for flushing the cursor!")

    def clear(self) -> None:
        """Clear the current transaction, and clear precommit hooks."""
        if self.transaction is not None:
            self.transaction.clear()
        self.precommit.clear()

    def reset(self) -> None:
        """Reset the current transaction (this invalidates more that clear()).
        This method should be called only right after commit() or rollback().
        """
        if self.transaction is not None:
            self.transaction.reset()

    def execute(self, query, params=None, log_exceptions: bool = True) -> None:
        """Execute a query inside the current transaction."""
        raise NotImplementedError

    def commit(self) -> None:
        """Commit the current transaction."""
        raise NotImplementedError

    def rollback(self) -> None:
        """Rollback the current transaction."""
        raise NotImplementedError

    def savepoint(self, flush: bool = True) -> Savepoint:
        """context manager entering in a new savepoint

        With ``flush`` (the default), will automatically run (or clear) the
        relevant hooks.
        """
        if flush:
            return _FlushingSavepoint(self)
        else:
            return Savepoint(self)

    def __enter__(self) -> Self:
        """Using the cursor as a contextmanager automatically commits and
        closes it::

            with cr:
                cr.execute(...)

            # cr is committed if no failure occurred
            # cr is closed in any case
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is None:
                self.commit()
        finally:
            self.close()

    def fetchscalar(self) -> Any:
        """Fetch a single scalar value from a single-column query.

        Returns ``None`` if no rows are available.  Eliminates the
        common ``cr.fetchone()[0]`` pattern which raises on empty results.
        """
        raise NotImplementedError

    def dictfetchone(self) -> dict[str, Any] | None:
        """Return the first row as a dict (column_name -> value) or None if no rows are available."""
        raise NotImplementedError

    def dictfetchmany(self, size: int) -> list[dict[str, Any]]:
        res: list[dict[str, Any]] = []
        while size > 0 and (row := self.dictfetchone()) is not None:
            res.append(row)
            size -= 1
        return res

    def dictfetchall(self) -> list[dict[str, Any]]:
        """Return all rows as dicts (column_name -> value)."""
        res: list[dict[str, Any]] = []
        while (row := self.dictfetchone()) is not None:
            res.append(row)
        return res

    def now(self) -> datetime:
        """Return the transaction's timestamp ``NOW() AT TIME ZONE 'UTC'``."""
        if self._now is None:
            self.execute("SELECT (now() AT TIME ZONE 'UTC')")
            row = self.fetchone()
            assert row
            self._now = row[0]
        return self._now


class Cursor(BaseCursor):
    """Represents an open transaction to the PostgreSQL DB backend,
    acting as a lightweight wrapper around psycopg's
    ``Cursor`` objects (native server-side binding).

     ``Cursor`` is the object behind the ``cr`` variable used all
     over the Odoo code.

     .. rubric:: Transaction Isolation

     One very important property of database transactions is the
     level of isolation between concurrent transactions.
     The SQL standard defines four levels of transaction isolation,
     ranging from the most strict *Serializable* level, to the least
     strict *Read Uncommitted* level. These levels are defined in
     terms of the phenomena that must not occur between concurrent
     transactions, such as *dirty read*, etc.
     In the context of a generic business data management software
     such as Odoo, we need the best guarantees that no data
     corruption can ever be cause by simply running multiple
     transactions in parallel. Therefore, the preferred level would
     be the *serializable* level, which ensures that a set of
     transactions is guaranteed to produce the same effect as
     running them one at a time in some order.

     PostgreSQL implements ``REPEATABLE READ`` as
     `snapshot isolation <http://en.wikipedia.org/wiki/Snapshot_isolation>`_,
     which provides the consistency guarantees Odoo requires without
     the performance overhead of true ``SERIALIZABLE`` (which adds
     predicate locking and forced rollbacks for serialization anomalies).
     Odoo handles high-contention paths (stock reservations, sequence
     generation) with explicit row-level locking, so the additional
     heuristics of ``SERIALIZABLE`` mode are unnecessary.

     ``REPEATABLE READ`` is therefore the default isolation level for
     all Odoo cursors (requires PostgreSQL 18+).

     .. attribute:: cache

         Cache dictionary with a "request" (-ish) lifecycle, only lives as
         long as the cursor itself does and proactively cleared when the
         cursor is closed.

         This cache should *only* be used to store repeatable reads as it
         ignores rollbacks and savepoints, it should not be used to store
         *any* data which may be modified during the life of the cursor.

    """

    sql_from_log: dict[str, tuple[int, float]]
    sql_into_log: dict[str, tuple[int, float]]
    sql_log_count: int

    def __init__(self, pool: ConnectionPool, dbname: str, dsn: dict):
        super().__init__()
        self.sql_from_log = {}
        self.sql_into_log = {}

        # default log level determined at cursor creation, could be
        # overridden later for debugging purposes
        self.sql_log_count = 0

        # avoid the call of close() (by __del__) if an exception
        # is raised by any of the following initializations
        self._closed: bool = True

        self.__pool: ConnectionPool = pool
        self.dbname = dbname

        # Cache thread reference — a cursor is always used on its creating
        # thread (hard invariant; violating it corrupts the PG transaction).
        # This avoids calling threading.current_thread() on every execute().
        self._thread = threading.current_thread()

        self._cnx: psycopg.Connection = pool.borrow(dsn)
        try:
            self._obj: psycopg.Cursor = self._cnx.cursor()
            if _logger.isEnabledFor(logging.DEBUG):
                self.__caller = frame_codeinfo(currentframe(), 2)
            else:
                self.__caller = False
            # See the docstring of this class.
            self._cnx.isolation_level = IsolationLevel.REPEATABLE_READ
            self._cnx.read_only = pool.readonly
            self._closed = False  # only after all setup succeeds
        except Exception:
            pool.give_back(self._cnx)
            raise

        if (
            os.getenv("ODOO_FAKETIME_TEST_MODE")
            and self.dbname in tools.config["db_name"]
        ):
            self.execute("SET search_path = public, pg_catalog;")
            self.commit()  # ensure that the search_path remains after a rollback

    def fetchscalar(self) -> Any:
        row = self._obj.fetchone()
        return row[0] if row else None

    def dictfetchone(self) -> dict[str, Any] | None:
        row = self._obj.fetchone()
        if row is None:
            return None
        desc = self._obj.description
        assert desc, "Query does not have results"
        return {col.name: val for col, val in zip(desc, row, strict=False)}

    def _col_names(self) -> tuple[str, ...]:
        """Extract column names from the last query's description as a tuple."""
        return tuple(col.name for col in self._obj.description)

    def dictfetchmany(self, size) -> list[dict[str, Any]]:
        rows = self._obj.fetchmany(size)
        if not rows:
            return []
        if _rows_to_dicts is not None:
            return _rows_to_dicts(self._col_names(), rows)
        cols = self._col_names()
        return [dict(zip(cols, row, strict=False)) for row in rows]

    def dictfetchall(self) -> list[dict[str, Any]]:
        rows = self._obj.fetchall()
        if not rows:
            return []
        if _rows_to_dicts is not None:
            return _rows_to_dicts(self._col_names(), rows)
        cols = self._col_names()
        return [dict(zip(cols, row, strict=False)) for row in rows]

    # -- Explicit forwarding for commonly-used psycopg Cursor methods -------
    # These were previously resolved via __getattr__ on every call.
    # Explicit forwarding avoids attribute-lookup overhead on the hot path
    # and makes the public interface discoverable for IDEs/type checkers.

    def fetchone(self):
        return self._obj.fetchone()

    def fetchall(self):
        return self._obj.fetchall()

    def fetchmany(self, size=0):
        return self._obj.fetchmany(size)

    @property
    def description(self):
        return self._obj.description

    @property
    def rowcount(self) -> int:
        return self._obj.rowcount

    @property
    def statusmessage(self) -> str:
        return self._obj.statusmessage

    @property
    def connection(self) -> psycopg.Connection:
        return self._cnx

    def copy(self, statement, params=None, *, writer=None):
        return self._obj.copy(statement, params, writer=writer)

    def __del__(self):
        if not self._closed and not self._cnx.closed:
            # Oops. 'self' has not been closed explicitly.
            # The cursor will be deleted by the garbage collector,
            # but the database connection is not put back into the connection
            # pool, preventing some operation on the database like dropping it.
            # This can also lead to a server overload.
            msg = "Cursor not closed explicitly\n"
            if self.__caller:
                msg += f"Cursor was created at {self.__caller[0]}:{self.__caller[1]}"
            else:
                msg += "Please enable sql debugging to trace the caller."
            _logger.warning(msg)
            self._close(True)

    def _format(self, query, params=None) -> str:
        """Format a query for debug logging (approximate, not for execution)."""
        if isinstance(query, SQL):
            query, params = query.code, query.params
        if params is None:
            return str(query)
        try:
            if isinstance(params, dict):
                return str(query) % {k: repr(v) for k, v in params.items()}
            return str(query) % tuple(repr(v) for v in params)
        except Exception:
            return f"{query} [{params!r}]"

    def _record_metrics(
        self, delay: float, count: int = 1, *, query=None, params=None, start: float = 0.0,
    ) -> None:
        """Update query counters, thread-local metrics, and run query hooks.

        Centralises all post-execution bookkeeping so that execute(),
        executemany() and copy_from() share one code path.

        :param query: The executed query (passed to hooks, may be None)
        :param params: The query parameters (passed to hooks, may be None)
        :param start: Monotonic timestamp before execution (passed to hooks)
        """
        global sql_counter
        self.sql_log_count += count
        sql_counter += count
        # NB: hasattr() calls below look like optimization candidates (try/except
        # is faster on the happy path) but the difference is ~50ns/call — irrelevant
        # vs. the ~1-5ms average query time.  Keep the explicit style for clarity.
        t = self._thread
        if hasattr(t, "query_count"):
            t.query_count += count
        if hasattr(t, "query_time"):
            t.query_time += delay
        for hook in getattr(t, "query_hooks", ()):
            hook(self, query, params, start, delay)

    def execute(self, query, params=None, log_exceptions: bool = True) -> None:
        if isinstance(query, SQL):
            assert params is None, "Unexpected parameters for SQL query object"
            query, params = query.code, query.params
        elif params:
            if not isinstance(params, (tuple, list, dict)):
                raise ValueError(
                    f"SQL query parameters should be a tuple, list or dict; got {params!r}"
                )

        is_ddl = False

        if params:
            # DDL statements cannot use server-side parameter binding.
            # Format them client-side before sending to PostgreSQL.
            # Fast prefix check avoids regex for 99% of queries (SELECT/INSERT/UPDATE).
            qs = query if isinstance(query, str) else str(query)
            c = qs.lstrip()[:2].upper()
            if c in _DDL_PREFIXES and _RE_DDL.match(qs):
                is_ddl = True
                ctx = self._cnx
                if isinstance(params, dict):
                    query = qs % {k: str(_sql.quote(v, ctx)) for k, v in params.items()}
                else:
                    query = qs % tuple(str(_sql.quote(v, ctx)) for v in params)
                params = None

        start = real_time()
        try:
            self._obj.execute(query, params)
        except Exception as e:
            if log_exceptions:
                _logger.error("bad query: %s\nERROR: %s", query, e)
            raise
        finally:
            delay = real_time() - start
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug(
                    "[%.3f ms] query: %s",
                    1000 * delay,
                    self._format(query, params),
                )

        # After DDL, invalidate psycopg3's auto-prepared statement cache.
        # psycopg3's PrepareManager natively handles DROP/ROLLBACK, but
        # CREATE/ALTER also change schema — making cached plans for
        # SELECT * queries stale ("cached plan must not change result type").
        # For DDL-with-params, is_ddl was set above during client-side formatting.
        # For DDL-without-params (pre-formatted SQL), detect now.
        if not is_ddl and not params:
            qs = query if isinstance(query, str) else str(query)
            c = qs.lstrip()[:2].upper()
            is_ddl = c in _DDL_PREFIXES and _RE_DDL.match(qs)
        if is_ddl:
            # Private API: psycopg 3.x has no public method to invalidate
            # the auto-prepared statement cache.  _prepared.clear() queues a
            # DEALLOCATE ALL on the next execute().  Pinned to psycopg >=3.1.
            # If psycopg removes _prepared, set prepare_threshold=None on the
            # connection after DDL instead (disables auto-prepare entirely).
            self._cnx._prepared.clear()

        self._record_metrics(delay, query=query, params=params, start=start)

        # advanced stats
        if _logger.isEnabledFor(logging.DEBUG):
            query_type, table = categorize_query(str(query))
            log_target = None
            if query_type == "into":
                log_target = self.sql_into_log
            elif query_type == "from":
                log_target = self.sql_from_log
            if log_target:
                stat_count, stat_time = log_target.get(table or "", (0, 0))
                log_target[table or ""] = (
                    stat_count + 1,
                    stat_time + delay * 1e6,
                )

    def execute_values(
        self, query, argslist, template=None, page_size=100, fetch=False
    ):
        """Execute a query with multiple parameter sets using VALUES clause.

        Builds a single query with multiple VALUES rows per batch, useful for
        patterns like ``UPDATE ... FROM (VALUES %s) AS source(...)``.

        For simple multi-row INSERTs, prefer :meth:`executemany` which
        auto-pipelines for better performance.
        """
        if isinstance(query, _sql.Composable):
            query = query.as_string(self._obj)
        if not argslist:
            return [] if fetch else None
        results = []
        batches = range(0, len(argslist), page_size)
        # Pipeline multi-batch non-fetch executions for single round-trip
        use_pipeline = len(argslist) > page_size and not fetch
        ctx = self._cnx.pipeline() if use_pipeline else _nullcontext()
        with ctx:
            for i in batches:
                batch = argslist[i : i + page_size]
                placeholders = []
                params = []
                for row in batch:
                    if template:
                        placeholders.append(template)
                    elif isinstance(row, (list, tuple)):
                        placeholders.append("(" + ", ".join(["%s"] * len(row)) + ")")
                    else:
                        placeholders.append("(%s)")
                    if isinstance(row, (list, tuple)):
                        params.extend(row)
                    else:
                        params.append(row)
                full_query = query.replace("%s", ", ".join(placeholders), 1)
                self.execute(full_query, params)
                if fetch:
                    results.extend(self.fetchall())
        return results if fetch else None

    def executemany(self, query, params_seq, returning=False):
        """Execute a query with multiple parameter sets using pipeline mode.

        psycopg3's executemany automatically batches all statements in a
        single network round-trip on PostgreSQL 14+, avoiding the overhead
        of individual execute() calls.

        :param query: SQL query with ``%s`` placeholders
        :param params_seq: Sequence of parameter tuples/lists
        :param returning: If True, collect RETURNING results per statement.
            Use ``fetchall()`` + ``nextset()`` loop to read all result sets.
        """
        if isinstance(query, SQL):
            query, _ = query.code, query.params

        if not params_seq:
            return

        start = real_time()
        try:
            self._obj.executemany(query, params_seq, returning=returning)
        except Exception as e:
            _logger.error("bad query: %s\nERROR: %s", query, e)
            raise
        finally:
            delay = real_time() - start
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug(
                    "[%.3f ms] executemany (%d rows): %s",
                    1000 * delay,
                    len(params_seq) if hasattr(params_seq, "__len__") else -1,
                    query,
                )

        count = len(params_seq) if hasattr(params_seq, "__len__") else 1
        self._record_metrics(delay, count, query=query, start=start)

    @contextmanager
    def pipeline(self):
        """Enter pipeline mode for batching queries in a single round-trip.

        All execute() calls within the context are queued and sent together
        when the context exits, reducing network overhead for batch operations.

        Usage::

            with cr.pipeline():
                cr.execute("INSERT INTO t1 ...")
                cr.execute("INSERT INTO t2 ...")
                # Both sent in one round-trip
        """
        with self._cnx.pipeline():
            yield

    def copy_from(
        self,
        table: str,
        columns: list[str],
        rows,
        *,
        returning_ids: bool = False,
        binary: bool = False,
        on_error: str | None = None,
    ) -> list[int] | None:
        """Bulk insert rows using PostgreSQL COPY protocol.

        Streams rows via COPY FROM STDIN, bypassing SQL parsing and planning
        overhead.  2-5x faster than multi-row INSERT for large batches.

        All Python types (Json, datetime, None, etc.) are adapted automatically
        by psycopg3's Transformer — the same adapter system used by execute().

        :param table: Target table name
        :param columns: List of column names
        :param rows: Iterable of tuples/lists matching columns
        :param returning_ids: If True, pre-generate IDs via the table's
            serial sequence and return them.  ``'id'`` is prepended to
            *columns* automatically.
        :param binary: If True, use binary COPY format (faster but requires
            exact type matching via ``set_types()``). Column types are looked
            up from ``pg_attribute`` and cached per table.
        :param on_error: Error handling for data type conversion errors
            (PG17+, text/CSV mode only).  ``'ignore'`` skips malformed rows
            instead of aborting the entire operation.  Useful for fault-
            tolerant data imports.  Has no effect with ``binary=True``.
        :return: list of generated IDs when *returning_ids* is True, else None
        """
        if returning_ids:
            rows = list(rows)
            count = len(rows)
            if count == 0:
                return []
            # Look up the sequence for the id column (cached).
            # pg_get_serial_sequence only finds sequences *owned* by the
            # column, but _inherits child tables share the parent's
            # sequence.  We fall back to the pg_depend catalog which finds
            # the sequence referenced by the column's DEFAULT expression.
            seq_name = _id_sequence_cache.get(table)
            if seq_name is None:
                self.execute(SQL("SELECT pg_get_serial_sequence(%s, 'id')", table))
                (seq_name,) = self.fetchone()
                if seq_name is None:
                    # Shared sequence (e.g. _inherits): find via pg_depend
                    self.execute(
                        SQL(
                            """SELECT s.oid::regclass::text
                        FROM pg_attrdef ad
                        JOIN pg_class t ON t.oid = ad.adrelid
                        JOIN pg_attribute a ON a.attrelid = t.oid
                            AND a.attnum = ad.adnum
                        JOIN pg_depend d ON d.objid = ad.oid
                            AND d.classid = 'pg_attrdef'::regclass
                            AND d.refclassid = 'pg_class'::regclass
                        JOIN pg_class s ON s.oid = d.refobjid
                            AND s.relkind = 'S'
                        WHERE t.relname = %s AND a.attname = 'id'
                        LIMIT 1""",
                            table,
                        )
                    )
                    row = self.fetchone()
                    if not row or not row[0]:
                        raise ValueError(f"No serial sequence found for {table}.id")
                    seq_name = row[0]
                _id_sequence_cache[table] = seq_name
            # Pre-generate IDs from the sequence
            self.execute(
                SQL(
                    "SELECT nextval(%s::regclass) FROM generate_series(1, %s)",
                    seq_name,
                    count,
                )
            )
            ids = [row[0] for row in self.fetchall()]
            columns = ["id", *columns]
            rows = [((id_,) + tuple(row)) for id_, row in zip(ids, rows, strict=False)]
        else:
            ids = None

        cols_sql = _sql.SQL(", ").join(map(_sql.Identifier, columns))
        # Build COPY options: FORMAT and ON_ERROR are independent.
        # ON_ERROR ignore (PG17) skips rows with type conversion errors
        # in text/CSV mode; it has no effect in binary mode.
        copy_opts = []
        if binary:
            copy_opts.append("FORMAT BINARY")
        if on_error and not binary:
            copy_opts.append(f"ON_ERROR {on_error}")
        if copy_opts:
            opts_sql = _sql.SQL(" ({})".format(", ".join(copy_opts)))
        else:
            opts_sql = _sql.SQL("")
        copy_stmt = _sql.SQL("COPY {} ({}) FROM STDIN{}").format(
            _sql.Identifier(table),
            cols_sql,
            opts_sql,
        )

        # Look up column types BEFORE entering the COPY context.
        # Inside `with self._obj.copy(...)`, the connection is in COPY
        # mode and cannot execute other queries (would block forever).
        col_types = self._get_column_types(table, columns) if binary else None

        # psycopg3's NumericBinaryDumper rejects Python float for PG
        # "numeric" columns — it requires Decimal.  Pre-compute which
        # column indices need float→Decimal conversion (Monetary fields
        # and Float-with-digits both map to "numeric").
        if col_types:
            _numeric_idxs = frozenset(i for i, t in enumerate(col_types) if t == "numeric")
        else:
            _numeric_idxs = None

        start = real_time()
        row_count = 0
        try:
            with self._obj.copy(copy_stmt) as copy:
                if col_types:
                    copy.set_types(col_types)
                for row in rows:
                    if _numeric_idxs:
                        row = tuple(
                            (
                                _Decimal(str(v))
                                if i in _numeric_idxs and isinstance(v, float)
                                else v
                            )
                            for i, v in enumerate(row)
                        )
                    copy.write_row(row)
                    row_count += 1
        except Exception as e:
            _logger.error("bad COPY: %s\nERROR: %s", copy_stmt.as_string(self._obj), e)
            raise
        finally:
            delay = real_time() - start
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug(
                    "[%.3f ms] COPY %s (%d rows)",
                    1000 * delay,
                    table,
                    row_count,
                )

        self._record_metrics(
            delay, query=copy_stmt.as_string(self._obj), start=start,
        )

        if _logger.isEnabledFor(logging.DEBUG):
            stat_count, stat_time = self.sql_into_log.get(table, (0, 0))
            self.sql_into_log[table] = (stat_count + 1, stat_time + delay * 1e6)

        return ids

    def merge(
        self,
        table: str,
        columns: list[str],
        rows: list[tuple],
        on_columns: list[str],
        *,
        returning: str = "NEW.id",
    ) -> list[tuple]:
        """Atomic upsert via MERGE (PG15+, RETURNING since PG17).

        Inserts new rows or updates existing rows matching on ``on_columns``.
        Uses ``MERGE INTO ... USING (VALUES ...) ... RETURNING`` for a single
        atomic round-trip.

        PG17 adds ``merge_action()`` in RETURNING to distinguish inserted
        vs. updated rows.  Pass ``returning="merge_action(), NEW.id"`` to
        get ``('INSERT', id)`` or ``('UPDATE', id)`` tuples.

        :param table: target table name
        :param columns: list of column names for the data
        :param rows: list of tuples, each matching ``columns``
        :param on_columns: columns for the ON match predicate (typically
            the unique constraint columns)
        :param returning: RETURNING clause expression (default ``"NEW.id"``).
            Use ``merge_action()`` (PG17) to get the action type per row.
        :return: list of result tuples from the RETURNING clause
        """
        if not rows:
            return []

        comma = SQL(", ").join
        col_ids = [SQL.identifier(c) for c in columns]
        s_cols = [SQL("s.%s", SQL.identifier(c)) for c in columns]
        on_pred = SQL(" AND ").join(
            SQL("t.%s = s.%s", SQL.identifier(c), SQL.identifier(c)) for c in on_columns
        )
        update_cols = [c for c in columns if c not in on_columns]
        assignments = comma(
            SQL("%s = s.%s", SQL.identifier(c), SQL.identifier(c)) for c in update_cols
        )

        query = SQL(
            """
            MERGE INTO %(table)s t
            USING (VALUES %(values)s) AS s(%(cols)s)
            ON %(on_pred)s
            WHEN MATCHED THEN
                UPDATE SET %(assignments)s
            WHEN NOT MATCHED THEN
                INSERT (%(cols)s) VALUES (%(s_cols)s)
            RETURNING %(returning)s
            """,
            table=SQL.identifier(table),
            values=comma(rows),
            cols=comma(col_ids),
            on_pred=on_pred,
            assignments=assignments,
            s_cols=comma(s_cols),
            returning=SQL(returning),  # pylint: disable=sql-injection
        )

        start = real_time()
        try:
            self.execute(query)
            result = self.fetchall()
        except Exception as e:
            _logger.error("bad MERGE: %s\nERROR: %s", table, e)
            raise
        finally:
            delay = real_time() - start
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug(
                    "[%.3f ms] MERGE %s (%d rows)",
                    1000 * delay,
                    table,
                    len(rows),
                )

        return result

    def _get_column_types(self, table: str, columns: list[str]) -> list[str]:
        """Look up PostgreSQL base type names for binary COPY.

        Results are cached in ``_column_type_cache`` since schema doesn't
        change during a session.
        """
        key = (table, tuple(columns))
        types = _column_type_cache.get(key)
        if types is None:
            self.execute(
                SQL(
                    """SELECT a.attname, t.typname
                    FROM pg_attribute a
                    JOIN pg_type t ON a.atttypid = t.oid
                    JOIN pg_class c ON a.attrelid = c.oid
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    WHERE c.relname = %s AND n.nspname = current_schema
                      AND a.attname = ANY(%s)""",
                    table,
                    list(columns),
                )
            )
            type_map = dict(self.fetchall())
            types = [type_map[col] for col in columns]
            _column_type_cache[key] = types
        return types

    def print_log(self) -> None:
        if not _logger.isEnabledFor(logging.DEBUG):
            return

        def process(log_type: str):
            sqllogs = {"from": self.sql_from_log, "into": self.sql_into_log}
            sqllog = sqllogs[log_type]
            total = 0.0
            if sqllog:
                _logger.debug("SQL LOG %s:", log_type)
                for table, (stat_count, stat_time) in sorted(
                    sqllog.items(), key=lambda k: k[1]
                ):
                    delay = timedelta(microseconds=stat_time)
                    _logger.debug("table: %s: %s/%s", table, delay, stat_count)
                    total += stat_time
                sqllog.clear()
            total_delay = timedelta(microseconds=total)
            _logger.debug(
                "SUM %s:%s/%d [%d]",
                log_type,
                total_delay,
                self.sql_log_count,
                sql_counter,
            )

        process("from")
        process("into")
        self.sql_log_count = 0

    @contextmanager
    def _enable_logging(self):
        """Forcefully enables logging for this cursor, restores it afterwards.

        Updates the logger in-place, so not thread-safe.
        """
        level = _logger.level
        _logger.setLevel(logging.DEBUG)
        try:
            yield
        finally:
            _logger.setLevel(level)

    def close(self) -> None:
        if not self.closed:
            return self._close(False)
        return None

    def _close(self, leak: bool = False) -> None:
        if not self._obj:
            return

        self.cache.clear()

        # advanced stats only at logging.DEBUG level
        self.print_log()

        self._obj.close()

        # Mark cursor as closed BEFORE deleting _obj. This prevents
        # __getattr__ from entering infinite recursion if a rollback
        # hook accidentally accesses a delegated attribute (since _obj
        # no longer exists but _closed would still be False).
        self._closed = True

        # This force the cursor to be freed, and thus, available again. It is
        # important because otherwise we can overload the server very easily
        # because of a cursor shortage (because cursors are not garbage
        # collected as fast as they should). The problem is probably due in
        # part because browse records keep a reference to the cursor.
        del self._obj

        # Clean the underlying connection, then return it to the pool.
        # give_back() MUST run even if rollback() fails (e.g. broken
        # connection, failing hooks) — otherwise the connection and its
        # global semaphore slot leak permanently.
        chosen_template = tools.config["db_template"]
        keep_in_pool = self.dbname not in (
            "template0",
            "template1",
            "postgres",
            chosen_template,
        )
        try:
            self.rollback()
        except Exception:
            _logger.debug("Failed to rollback on cursor close", exc_info=True)
            keep_in_pool = False
        finally:
            self.__pool.give_back(self._cnx, keep_in_pool=keep_in_pool)

    def commit(self) -> None:
        """Perform an SQL `COMMIT`"""
        self.flush()
        self._cnx.commit()
        self.clear()
        self._now = None
        self.prerollback.clear()
        self.postrollback.clear()
        self.postcommit.run()

    def rollback(self) -> None:
        """Perform an SQL `ROLLBACK`.

        Hook order is intentional: prerollback runs BEFORE the SQL ROLLBACK
        so hooks can still read uncommitted transaction state (e.g. for cache
        invalidation decisions).  After ROLLBACK, that data is gone.
        """
        self.clear()
        self.postcommit.clear()
        self.prerollback.run()
        self._cnx.rollback()
        self._now = None
        self.postrollback.run()

    def __getattr__(self, name):
        if self._closed and name == "_obj":
            raise psycopg.InterfaceError("Cursor already closed")
        warnings.warn(
            f"Cursor.{name} is not part of the Odoo cursor API. "
            f"Add explicit forwarding in cursor.py or use cr._obj.{name} directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(self._obj, name)

    @property
    def closed(self) -> bool:
        return self._closed or bool(self._cnx.closed)

    @property
    def readonly(self) -> bool:
        return bool(self._cnx.read_only)
