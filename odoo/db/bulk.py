from __future__ import annotations

import logging
from contextlib import nullcontext as _nullcontext
from decimal import Decimal as _Decimal
from itertools import chain
from time import monotonic
from typing import TYPE_CHECKING, Any

from psycopg import errors as _errors
from psycopg import pq as _pq
from psycopg import sql as _sql
from psycopg.adapt import Transformer as _Transformer
from psycopg.types.json import Jsonb as _Jsonb

from odoo.libs.datetime import real_time
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import SQL

from .ddl import get_value_marker_positions
from .errors import CURSOR_LOGGER_NAME, has_reached_server

_logger = logging.getLogger(CURSOR_LOGGER_NAME)
_debug = DebugLog(__name__)

_NO_ROWS = object()

_TEXT_OID = 25
_NUMERIC_OID = 1700
_JSON_OIDS: frozenset[int] = frozenset({114, 3802})


def _dump_json_verbatim(value: str) -> str:
    return value


_BINARY_NUMERIC_MAX_FRACTION = 0.25

# The extended protocol counts bind parameters in a uint16; PostgreSQL refuses
# a statement carrying more ("number of parameters must be between 0 and 65535").
_MAX_BIND_PARAMS = 65535


def _get_table_identifier(table: str) -> _sql.Identifier:
    return _sql.Identifier(*table.split("."))


if TYPE_CHECKING:
    import threading
    from collections.abc import Iterable, Iterator
    from contextlib import AbstractContextManager
    from typing import Protocol

    import psycopg

    from .schema_cache import TransactionSchemaCache

    class _CursorInternals(Protocol):
        _obj: psycopg.Cursor
        _cnx: psycopg.Connection
        _thread: threading.Thread
        _schema_cache: TransactionSchemaCache
        dbname: str

        def _mark_table_locked(self, table: str) -> None: ...

        def execute(
            self,
            query: str | SQL | _sql.Composable,
            params: tuple | list | dict | None = None,
            log_exceptions: bool = True,
        ) -> None: ...

        @property
        def in_pipeline(self) -> bool: ...

        def pipeline(
            self, log_exceptions: bool = True, query: Any = None
        ) -> AbstractContextManager[None]: ...
        def fetchone(self) -> tuple[Any, ...] | None: ...
        def fetchall(self) -> list[tuple[Any, ...]]: ...
        def _record_metrics(
            self,
            delay: float,
            count: int = 1,
            *,
            statement: bool = True,
            query: Any = None,
            params: Any = None,
            start: float = 0.0,
            hooks: Any = None,
        ) -> None: ...
        def _record_sql_log(
            self, query_type: str, table: str | None, delay: float
        ) -> None: ...
        def _before_statement(self) -> None: ...
        def _statement_failed(
            self,
            exc: Exception,
            query: Any,
            *,
            label: str = "query",
            log_exceptions: bool = True,
            prepared: bool = True,
        ) -> bool: ...
        def _statement_done(
            self,
            delay: float,
            *,
            counts: bool,
            query: Any,
            params: Any = None,
            count: int = 1,
            label: str = "query",
            hooks: Any = None,
            start: float = 0.0,
            debug: bool = False,
        ) -> None: ...
        def _get_column_type_oids(
            self, table: str, columns: list[str]
        ) -> list[int]: ...
        def _can_dump_binary(self, oids: list[int]) -> bool: ...
        def _is_binary_copy_worthwhile(self, oids: list[int]) -> bool: ...
        def _get_id_sequence(self, table: str) -> str: ...
        def _lock_table_for_bulk(self, table: str) -> None: ...
        def _preallocate_copy_ids(self, table: str, count: int) -> list[int]: ...
        def _prepare_copy_rows(
            self,
            table: str,
            columns: list[str],
            rows: Any,
            returning_ids: bool,
        ) -> tuple[list[str], Any, list[int] | None] | None: ...


def _check_copy_args(
    cursor: _CursorInternals,
    table: str,
    columns: list[str],
    returning_ids: bool,
    binary: bool,
    on_error: str | None,
) -> None:
    if not columns:
        _debug.logic("bulk.copy.args_refused", table=table, reason="no_columns")
        raise ValueError("copy_from: columns must be a non-empty list")
    if on_error is not None and on_error not in ("ignore", "stop"):
        _debug.logic(
            "bulk.copy.args_refused",
            table=table,
            reason="on_error_value",
            on_error=on_error,
        )
        raise ValueError(
            f"copy_from: invalid on_error {on_error!r}; "
            f"allowed values: 'ignore', 'stop'."
        )
    if on_error and binary:
        _debug.logic("bulk.copy.args_refused", table=table, reason="on_error_binary")
        raise ValueError(
            "copy_from: on_error is not supported with binary=True; "
            "binary COPY has no ON_ERROR clause."
        )
    if on_error == "ignore" and returning_ids:
        _debug.logic(
            "bulk.copy.args_refused", table=table, reason="ignore_with_returning_ids"
        )
        raise ValueError(
            "copy_from: on_error='ignore' is incompatible with "
            "returning_ids=True — pre-allocated sequence IDs cannot be "
            "reconciled with rows silently dropped by the server. "
            "Use batched INSERT ... RETURNING id for fault-tolerant "
            "inserts that need IDs."
        )
    if returning_ids and "id" in columns:
        _debug.logic(
            "bulk.copy.args_refused", table=table, reason="id_column_with_returning_ids"
        )
        raise ValueError(
            "copy_from: columns must not already include 'id' when "
            "returning_ids=True — the id column is added automatically "
            "for the pre-allocated sequence values."
        )
    if cursor.in_pipeline:
        _debug.logic("bulk.copy.args_refused", table=table, reason="in_pipeline")
        raise _prepare_copy_in_pipeline_error(f"copy_from({table!r})")


def _prepare_copy_in_pipeline_error(call: str) -> _errors.NotSupportedError:
    return _errors.NotSupportedError(
        f"{call} cannot run inside pipeline mode; use execute_values, or move "
        f"the COPY out of the enclosing cr.pipeline() block."
    )


def _prepare_copy_statement(
    table: str, columns: list[str], binary: bool, on_error: str | None
) -> _sql.Composed:
    copy_opts = []
    if binary:
        copy_opts.append("FORMAT BINARY")
    if on_error and not binary:
        copy_opts.append(f"ON_ERROR {on_error}")
    if copy_opts:
        opts_sql = _sql.SQL(" ({})".format(", ".join(copy_opts)))
    else:
        opts_sql = _sql.SQL("")
    return _sql.SQL("COPY {} ({}) FROM STDIN{}").format(
        _get_table_identifier(table),
        _sql.SQL(", ").join(map(_sql.Identifier, columns)),
        opts_sql,
    )


def _add_binary_types_note(exc: Exception, table: str, columns: list) -> None:
    if has_reached_server(exc):
        return
    exc.add_note(
        f"copy_from({table!r}, binary=True) encodes values client-side from "
        f"the column types, which needs exactly the Python type each column "
        f"takes (int for int4, datetime.date for date, uuid.UUID for uuid). "
        f"Text COPY accepts a string for any of them; binary does not. "
        f"Columns: {columns}."
    )


def _coerce_rows(rows: Iterable[Any], col_types: list[int]) -> Iterator[Any]:
    numeric_idxs = tuple(i for i, oid in enumerate(col_types) if oid == _NUMERIC_OID)
    json_idxs = tuple(i for i, oid in enumerate(col_types) if oid in _JSON_OIDS)
    _debug.logic(
        "bulk.copy.coercion",
        columns=len(col_types),
        numeric=len(numeric_idxs),
        json=len(json_idxs),
    )
    if not (numeric_idxs or json_idxs):
        yield from rows
        return
    for row in rows:
        row = list(row)
        for i in numeric_idxs:
            if isinstance(row[i], float):
                row[i] = _Decimal(str(row[i]))
        for i in json_idxs:
            if isinstance(row[i], str):
                row[i] = _Jsonb(row[i], dumps=_dump_json_verbatim)
        yield row


class _BulkAccessMixin:
    def execute_values(
        self: _CursorInternals,
        query: str | _sql.Composable,
        argslist: list[Any],
        template: str | None = None,
        page_size: int = 100,
        fetch: bool = False,
        log_exceptions: bool = True,
    ) -> list[tuple[Any, ...]] | None:
        if isinstance(query, _sql.Composable):
            query = query.as_string(self._obj)
        if page_size <= 0:
            _debug.logic(
                "bulk.execute_values_refused", reason="page_size", page_size=page_size
            )
            raise ValueError(f"execute_values page_size must be >= 1, got {page_size}")
        markers = get_value_marker_positions(query)
        if len(markers) != 1:
            _debug.logic(
                "bulk.execute_values_refused", reason="markers", markers=len(markers)
            )
            raise ValueError(
                f"execute_values requires exactly one '%s' marker in the "
                f"query (for the VALUES list); got {len(markers)}."
            )
        marker_pos = markers[0]
        if not argslist:
            _debug.logic(
                "bulk.execute_values_empty",
                db=getattr(self, "dbname", None),
                fetch=fetch,
            )
            return [] if fetch else None
        self._before_statement()
        results = []
        prefix, suffix = query[:marker_pos], query[marker_pos + 2 :]
        use_pipeline = len(argslist) > page_size and not fetch
        ctx = (
            self.pipeline(log_exceptions=log_exceptions, query=query)
            if use_pipeline
            else _nullcontext()
        )
        ph_by_len: dict[int, str] = {}
        batches = 0  # debuglog
        clamped = 0  # debuglog
        with _debug.perf(
            "bulk.execute_values",
            cr=self,
            db=getattr(self, "dbname", None),
            rows=len(argslist),
            page_size=page_size,
            pipelined=use_pipeline,
            fetch=fetch,
            template=template is not None,
        ) as span:
            with ctx:
                i, n = 0, len(argslist)
                while i < n:
                    placeholders: list[str] = []
                    params: list[Any] = []
                    # A page is `page_size` rows, or fewer when the widest rows
                    # would push one statement past the uint16 bind-parameter
                    # limit; decided per row here, so the rows are walked once.
                    while i < n and len(placeholders) < page_size:
                        row = argslist[i]
                        width = len(row) if isinstance(row, (list, tuple)) else 1
                        if len(params) + width > _MAX_BIND_PARAMS and params:
                            clamped += 1  # debuglog
                            break
                        if isinstance(row, (list, tuple)):
                            if template:
                                placeholders.append(template)
                            elif (ph := ph_by_len.get(len(row))) is not None:
                                placeholders.append(ph)
                            else:
                                ph = "(" + ", ".join(["%s"] * len(row)) + ")"
                                ph_by_len[len(row)] = ph
                                placeholders.append(ph)
                            params.extend(row)
                        else:
                            placeholders.append(template or "(%s)")
                            params.append(row)
                        i += 1
                    full_query = f"{prefix}{', '.join(placeholders)}{suffix}"
                    self.execute(full_query, params, log_exceptions)
                    batches += 1  # debuglog
                    if fetch:
                        results.extend(self.fetchall())
            span.set(fetched=len(results), batches=batches, clamped_pages=clamped)
        return results if fetch else None

    def copy_from(
        self: _CursorInternals,
        table: str,
        columns: list[str],
        rows,
        *,
        returning_ids: bool = False,
        binary: bool = False,
        on_error: str | None = None,
        log_exceptions: bool = True,
    ) -> list[int] | None:
        _check_copy_args(self, table, columns, returning_ids, binary, on_error)
        self._before_statement()

        prepared = self._prepare_copy_rows(table, columns, rows, returning_ids)
        if prepared is None:
            _debug.logic("bulk.copy.empty", table=table, returning_ids=returning_ids)
            return [] if returning_ids else None
        columns, rows, ids = prepared

        col_types = self._get_column_type_oids(table, columns) if binary else None
        if col_types is not None and not self._is_binary_copy_worthwhile(col_types):
            binary = False
            col_types = None
        _debug.logic(
            "bulk.copy.strategy",
            table=table,
            columns=len(columns),
            binary=binary,
            returning_ids=returning_ids,
            on_error=on_error,
        )

        copy_stmt = _prepare_copy_statement(table, columns, binary, on_error)
        write_rows = _coerce_rows(rows, col_types) if col_types else rows

        def render_copy_statement() -> str:
            return copy_stmt.as_string(obj)

        hooks = getattr(self._thread, "query_hooks", None)
        start = real_time() if hooks else 0.0
        obj = self._obj
        debug = _logger.isEnabledFor(logging.DEBUG)
        t0 = monotonic()
        counts = False
        row_count = 0
        with _debug.perf(
            "bulk.copy", db=getattr(self, "dbname", None), table=table, binary=binary
        ) as span:
            try:
                with obj.copy(copy_stmt) as copy:
                    if col_types:
                        copy.set_types(col_types)
                    for row in write_rows:
                        try:
                            copy.write_row(row)
                        except Exception as e:
                            if binary:
                                _add_binary_types_note(e, table, columns)
                            raise
                        row_count += 1
                counts = True
            except Exception as e:
                counts = self._statement_failed(
                    e,
                    render_copy_statement,
                    label="COPY",
                    log_exceptions=log_exceptions,
                    prepared=False,
                )
                raise
            finally:
                delay = monotonic() - t0
                self._statement_done(
                    delay,
                    counts=counts,
                    count=row_count,
                    query=render_copy_statement,
                    label="COPY",
                    hooks=hooks,
                    start=start,
                    debug=debug,
                )
                span.set(rows=row_count)

        if debug:
            self._record_sql_log("into", table, delay)

        return ids

    def _prepare_copy_rows(
        self: _CursorInternals,
        table: str,
        columns: list[str],
        rows,
        returning_ids: bool,
    ) -> tuple[list[str], Any, list[int] | None] | None:
        if returning_ids:
            if not hasattr(rows, "__len__"):
                rows = list(rows)
            count = len(rows)
            if count == 0:
                return None
            ids = self._preallocate_copy_ids(table, count)
            return (
                ["id", *columns],
                [(id_, *row) for id_, row in zip(ids, rows, strict=True)],
                ids,
            )
        if hasattr(rows, "__len__"):
            if len(rows) == 0:
                return None
        else:
            # Peeled rather than materialised: this branch exists to stream,
            # and a generator has no length to test before the round trip.
            iterator = iter(rows)
            first = next(iterator, _NO_ROWS)
            if first is _NO_ROWS:
                return None
            rows = chain((first,), iterator)
            _debug.logic("bulk.copy.streamed", table=table, columns=len(columns))
        return columns, rows, None

    def _preallocate_copy_ids(
        self: _CursorInternals, table: str, count: int
    ) -> list[int]:
        self.execute(
            SQL(
                "SELECT nextval(%s::regclass) FROM generate_series(1, %s)",
                self._get_id_sequence(table),
                count,
            )
        )
        _debug.perf.count("bulk.ids_preallocated", table=table, count=count)
        return [row[0] for row in self.fetchall()]

    def _lock_table_for_bulk(self: _CursorInternals, table: str) -> None:
        cache = self._schema_cache
        if cache.is_locked(table):
            _debug.logic("bulk.lock_ledger_hit", table=table)
            return
        self.execute(
            _sql.SQL("LOCK TABLE {} IN ROW EXCLUSIVE MODE").format(
                _get_table_identifier(table)
            )
        )
        self._mark_table_locked(table)
        _debug.lifecycle("bulk.table_locked", table=table)

    def _get_id_sequence(self: _CursorInternals, table: str) -> str:
        cache = self._schema_cache
        seq_name = cache.get_id_sequence(table)
        if seq_name is not None:
            _debug.perf.count("bulk.id_sequence_cached", table=table, sequence=seq_name)
            return seq_name
        ident = _get_table_identifier(table).as_string(self._cnx)
        self.execute(SQL("SELECT pg_get_serial_sequence(%s, 'id')", ident))
        row = self.fetchone()
        assert row is not None, "pg_get_serial_sequence returned no row"
        (seq_name,) = row
        via = "pg_get_serial_sequence"  # debuglog
        if seq_name is None:
            self.execute(
                SQL(
                    """SELECT s.oid::regclass::text
                FROM pg_attrdef ad
                JOIN pg_attribute a ON a.attrelid = ad.adrelid
                    AND a.attnum = ad.adnum
                JOIN pg_depend d ON d.objid = ad.oid
                    AND d.classid = 'pg_attrdef'::regclass
                    AND d.refclassid = 'pg_class'::regclass
                JOIN pg_class s ON s.oid = d.refobjid
                    AND s.relkind = 'S'
                WHERE ad.adrelid = %s::regclass AND a.attname = 'id'
                LIMIT 1""",
                    ident,
                )
            )
            row = self.fetchone()
            if not row or not row[0]:
                _debug.logic("bulk.id_sequence_missing", table=table)
                raise ValueError(f"No serial sequence found for {table}.id")
            seq_name = row[0]
            via = "pg_depend"  # debuglog
        cache.set_id_sequence(table, seq_name)
        _debug.perf.count(
            "bulk.id_sequence_resolved", table=table, sequence=seq_name, via=via
        )
        return seq_name

    def _is_binary_copy_worthwhile(self: _CursorInternals, oids: list[int]) -> bool:
        if not self._can_dump_binary(oids):
            _debug.logic(
                "bulk.copy.binary_refused", reason="no_dumper", columns=len(oids)
            )
            return False
        numeric = sum(1 for oid in oids if oid == _NUMERIC_OID)
        worthwhile = numeric <= len(oids) * _BINARY_NUMERIC_MAX_FRACTION
        if _debug.logic.enabled and not worthwhile:
            _debug.logic(
                "bulk.copy.binary_refused",
                reason="numeric_fraction",
                numeric=numeric,
                columns=len(oids),
                max_fraction=_BINARY_NUMERIC_MAX_FRACTION,
            )
        return worthwhile

    def _can_dump_binary(self: _CursorInternals, oids: list[int]) -> bool:
        try:
            _Transformer(self._cnx).set_dumper_types(oids, _pq.Format.BINARY)
        except _errors.Error:
            _debug.logic("bulk.copy.no_binary_dumper", oids=len(oids))
            _logger.debug(
                "copy_from: no binary dumper for type oid(s) %s; using text COPY",
                oids,
            )
            return False
        return True

    def _get_column_type_oids(
        self: _CursorInternals, table: str, columns: list[str]
    ) -> list[int]:
        cache = self._schema_cache
        types = cache.get_column_types(table, columns)
        if _debug.perf.enabled and types is not None:
            _debug.perf.count(
                "bulk.column_types_cached", table=table, columns=len(columns)
            )
        if types is None:
            self._lock_table_for_bulk(table)
            self.execute(
                SQL(
                    """WITH RECURSIVE resolved AS (
                        SELECT a.attname::text AS name, a.atttypid AS type_oid,
                               t.typtype, t.typbasetype, 0 AS depth
                          FROM pg_attribute a
                          JOIN pg_type t ON t.oid = a.atttypid
                         WHERE a.attrelid = %s::regclass
                           AND a.attnum > 0 AND NOT a.attisdropped
                           AND a.attname = ANY(%s)
                        UNION ALL
                        SELECT r.name, b.oid, b.typtype, b.typbasetype, r.depth + 1
                          FROM resolved r
                          JOIN pg_type b ON b.oid = r.typbasetype
                         WHERE r.typtype = 'd' AND r.depth < 16
                    )
                    SELECT DISTINCT ON (name)
                           name,
                           CASE WHEN typtype = 'e' THEN %s::oid ELSE type_oid END
                      FROM resolved
                     ORDER BY name, depth DESC""",
                    _get_table_identifier(table).as_string(self._cnx),
                    list(columns),
                    _TEXT_OID,
                )
            )
            type_map = dict(self.fetchall())
            missing = [col for col in columns if col not in type_map]
            if missing:
                _debug.logic(
                    "bulk.copy.columns_missing",
                    table=table,
                    missing=len(missing),
                    columns=len(columns),
                )
                raise ValueError(
                    f"copy_from: column(s) {missing} not found in table "
                    f"{table!r} (current_schema)"
                )
            types = [type_map[col] for col in columns]
            cache.set_column_types(table, columns, types)
            _debug.perf.count(
                "bulk.column_types_resolved", table=table, columns=len(columns)
            )
        return types
