from __future__ import annotations

import json
import logging
import os
import typing
from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from itertools import batched

from psycopg import errors as pgerrors
from psycopg.errors import (
    InvalidTextRepresentation,
    NumericValueOutOfRange,
    UntranslatableCharacter,
)
from psycopg.types.json import Json, Jsonb, JsonDumper

from odoo.exceptions import LockError, UserError
from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import _OrmProfile
from odoo.libs.sql import pg_size_pretty
from odoo.tools import SQL, OrderedSet, Query, partition
from odoo.tools.translate import _

from ..primitives import (
    MODULE_UNINSTALL_FLAG,
    SQL_DEFAULT,
    UPDATE_BATCH_SIZE,
    NewId,
)

if typing.TYPE_CHECKING:
    from ..domain import Domain
    from ..fields import Field
    from ..models.base import BaseModel

_logger = logging.getLogger("odoo.orm.backend")
_orm_crud = logging.getLogger("odoo.orm.crud")
_orm_read = logging.getLogger("odoo.orm.read")
_debug = DebugLog(__name__)

COPY_THRESHOLD = int(os.environ.get("ODOO_COPY_THRESHOLD", "50"))
COPY_DISABLED = os.environ.get("ODOO_DISABLE_COPY", "").lower() in (
    "1",
    "true",
    "yes",
)

_UNIFORM_UPDATE_TYPES = (
    type(None),
    bool,
    bytes,
    date,
    datetime,
    Decimal,
    float,
    int,
    str,
)

_JSONB_MAX_INTEGER_DIGITS = 131072
_JSONB_MAX_SCALE = 16383


def _unwrap_json(value: typing.Any) -> typing.Any:
    if isinstance(value, (Json, Jsonb)):
        dumped = JsonDumper(type(value)).dump(value)
        if dumped is None:
            raise TypeError(f"{type(value).__name__} dumped to no value")
        return _get_jsonb_storage_value(
            json.loads(
                bytes(dumped),
                parse_float=Decimal,
                parse_constant=_reject_json_constant,
            )
        )
    return value


def _reject_json_constant(value: str) -> typing.NoReturn:
    raise InvalidTextRepresentation(f"Invalid JSON token: {value}")


def _get_jsonb_storage_value(value: typing.Any) -> typing.Any:
    if isinstance(value, str):
        if "\0" in value:
            raise UntranslatableCharacter("JSONB cannot store a NUL character")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as error:
            raise InvalidTextRepresentation("Invalid JSON Unicode surrogate") from error
    elif isinstance(value, Decimal):
        exponent = value.as_tuple().exponent
        assert isinstance(exponent, int)
        if (
            value and value.adjusted() >= _JSONB_MAX_INTEGER_DIGITS
        ) or exponent < -_JSONB_MAX_SCALE:
            raise NumericValueOutOfRange(
                "JSONB number exceeds PostgreSQL numeric range"
            )
        if exponent >= 0:
            return int(value)
        return float(value) if value else 0.0
    elif isinstance(value, list):
        return [_get_jsonb_storage_value(item) for item in value]
    elif isinstance(value, dict):
        return {
            _get_jsonb_storage_value(key): _get_jsonb_storage_value(item)
            for key, item in value.items()
        }
    return value


def _get_column_read_value(field: Field, value: typing.Any, env) -> typing.Any:
    if field.company_dependent:
        company_key = str(env.company.id)
        if value is not None and company_key in value:
            return value[company_key]
        model = env[field.model_name]
        fallback = field.get_company_dependent_fallback(model)
        return field.convert_to_column(field.convert_to_write(fallback, model), model)
    if (
        field.translate
        and isinstance(value, dict)
        and not env.context.get("prefetch_langs")
    ):
        for lang in field.get_translation_fallback_langs(env):
            scalar = value.get(lang)
            if scalar is not None:
                return scalar
        return None
    if (
        field.is_binary
        and value is not None
        and (env.context.get("bin_size") or env.context.get("bin_size_" + field.name))
    ):
        # pg_size_pretty(length(col)) on the SQL path: the size, not the bytes
        return pg_size_pretty(len(value))
    return value


@typing.runtime_checkable
class SequenceStore(typing.Protocol):
    def create(self, env, name: str, *, increment: int, start: int) -> None: ...

    def drop(self, env, names: typing.Collection[str]) -> None: ...

    def alter(
        self,
        env,
        name: str,
        *,
        increment: int | None = None,
        restart: int | None = None,
    ) -> None: ...

    def next_values(self, env, name: str, count: int) -> list[int]: ...

    def peek(self, env, names: typing.Collection[str]) -> dict[str, int]: ...


class PostgresSequenceStore:
    __slots__ = ()

    def create(self, env, name: str, *, increment: int, start: int) -> None:
        _debug.lifecycle(
            "backend.sequence.created", name=name, increment=increment, start=start
        )
        env.cr.execute(
            SQL(
                "CREATE SEQUENCE %s INCREMENT BY %s START WITH %s",
                SQL.identifier(name),
                increment,
                max(start, 1),
            )
        )

    def drop(self, env, names: typing.Collection[str]) -> None:
        if not names:
            return
        _debug.lifecycle("backend.sequence.dropped", sequences=len(names))
        identifiers = SQL(",").join(map(SQL.identifier, names))
        env.cr.execute(SQL("DROP SEQUENCE IF EXISTS %s RESTRICT", identifiers))

    def alter(
        self,
        env,
        name: str,
        *,
        increment: int | None = None,
        restart: int | None = None,
    ) -> None:
        if increment is None and restart is None:
            return
        env.cr.execute(
            "SELECT relname FROM pg_class"
            " WHERE relkind = %s AND relname = %s"
            "   AND relnamespace = current_schema::regnamespace",
            ("S", name),
        )
        if not env.cr.fetchone():
            _debug.logic("backend.sequence.alter_missing", name=name)
            return
        _debug.lifecycle(
            "backend.sequence.altered",
            name=name,
            increment=increment,
            restart=restart,
        )
        env.cr.execute(
            SQL(
                "ALTER SEQUENCE %s%s%s",
                SQL.identifier(name),
                SQL(" INCREMENT BY %s", increment) if increment is not None else SQL(),
                SQL(" RESTART WITH %s", max(restart, 1))
                if restart is not None
                else SQL(),
            )
        )

    def next_values(self, env, name: str, count: int) -> list[int]:
        if count == 1:
            env.cr.execute("SELECT nextval(%s)", [name])
            return [env.cr.fetchone()[0]]
        env.cr.execute("SELECT nextval(%s) FROM generate_series(1, %s)", [name, count])
        return [number for (number,) in env.cr.fetchall()]

    def peek(self, env, names: typing.Collection[str]) -> dict[str, int]:
        if not names:
            return {}
        increments = dict(
            env.execute_query(
                SQL(
                    "SELECT sequencename, increment_by FROM pg_sequences"
                    " WHERE schemaname = current_schema"
                    "   AND sequencename = ANY(%s::name[])",
                    list(names),
                )
            )
        )
        if not increments:
            _debug.logic("backend.sequence.peek_none_found", requested=len(names))
            return {}
        _debug.perf.count(
            "backend.sequence.peek",
            requested=len(names),
            found=len(increments),
        )
        reads = SQL(" UNION ALL ").join(
            SQL(
                "SELECT %s AS name, last_value, is_called FROM %s",
                name,
                SQL.identifier(name),
            )
            for name in increments
        )
        return {
            name: last_value + increments[name] if is_called else last_value
            for name, last_value, is_called in env.execute_query(reads)
        }


@typing.runtime_checkable
class ColumnStore(typing.Protocol):
    def read(
        self, model: BaseModel, column: str, ids: typing.Collection[int]
    ) -> dict[int, typing.Any]: ...

    def write(
        self,
        model: BaseModel,
        column: str,
        rows: typing.Collection[tuple[int, typing.Any]],
    ) -> None: ...

    def fetch_and_add(
        self, model: BaseModel, column: str, record_id: int, delta: int
    ) -> int | None: ...

    def try_write(
        self, model: BaseModel, column: str, record_id: int, value: typing.Any
    ) -> bool: ...

    def merge_json(
        self,
        model: BaseModel,
        column: str,
        record_id: int,
        fallback: dict[str, typing.Any],
        value: dict[str, typing.Any],
    ) -> int: ...

    def get_column_values(
        self, model: BaseModel, column: str
    ) -> list[tuple[int, typing.Any]]: ...


class PostgresColumnStore:
    __slots__ = ()

    def read(
        self, model: BaseModel, column: str, ids: typing.Collection[int]
    ) -> dict[int, typing.Any]:
        if not ids:
            return {}
        rows = model.env.execute_query(
            SQL(
                "SELECT id, %s FROM %s WHERE id = ANY(%s)",
                SQL.identifier(column),
                SQL.identifier(model._table),
                list(ids),
            )
        )
        return dict(rows)

    def write(
        self,
        model: BaseModel,
        column: str,
        rows: typing.Collection[tuple[int, typing.Any]],
    ) -> None:
        if not rows:
            return
        table = SQL.identifier(model._table).code
        column_sql = SQL.identifier(column).code
        model.env.cr.executemany(  # noqa: E8501  both names are SQL.identifier().code; executemany takes no SQL params
            f"UPDATE {table} SET {column_sql} = %s WHERE id = %s",
            [(value, id_) for id_, value in rows],
        )

    def fetch_and_add(
        self, model: BaseModel, column: str, record_id: int, delta: int
    ) -> int | None:
        # the row is locked for the statement, so two callers never take the same
        # value: NOWAIT surfaces the contention instead of queueing behind it
        table = SQL.identifier(model._table)
        column_sql = SQL.identifier(column)
        [value] = model.env.execute_query(
            SQL(
                "WITH locked AS (SELECT %s AS value FROM %s WHERE id = %s FOR UPDATE NOWAIT) "
                "UPDATE %s t SET %s = t.%s + %s FROM locked WHERE t.id = %s "
                "RETURNING locked.value",
                column_sql,
                table,
                record_id,
                table,
                column_sql,
                column_sql,
                delta,
                record_id,
            )
        )[0]
        return value

    def try_write(
        self, model: BaseModel, column: str, record_id: int, value: typing.Any
    ) -> bool:
        # a value the table refuses (a unique or exclusion constraint) is an
        # answer, not an error: the caller picks the next candidate
        cr = model.env.cr
        with cr.savepoint(flush=False) as savepoint:
            try:
                cr.execute(
                    SQL(
                        "UPDATE %s SET %s = %s WHERE id = %s",
                        SQL.identifier(model._table),
                        SQL.identifier(column),
                        value,
                        record_id,
                    ),
                    log_exceptions=False,
                )
            except pgerrors.ExclusionViolation, pgerrors.UniqueViolation:
                savepoint.rollback()
                return False
        return True

    def merge_json(
        self,
        model: BaseModel,
        column: str,
        record_id: int,
        fallback: dict[str, typing.Any],
        value: dict[str, typing.Any],
    ) -> int:
        # fallback under the stored object under the new value; a null entry
        # deletes its key and an object left empty becomes NULL
        cr = model.env.cr
        cr.execute(
            SQL(
                "UPDATE %(table)s SET %(column)s = NULLIF(jsonb_strip_nulls("
                "%(fallback)s || COALESCE(%(column)s, '{}'::jsonb) || %(value)s"
                "), '{}'::jsonb) WHERE id = %(id)s",
                table=SQL.identifier(model._table),
                column=SQL.identifier(column),
                fallback=Jsonb(fallback),
                value=Jsonb(value),
                id=record_id,
            )
        )
        return cr.rowcount

    def get_column_values(
        self, model: BaseModel, column: str
    ) -> list[tuple[int, typing.Any]]:
        # every row holding a value in the column, by id, as stored
        return model.env.execute_query(
            SQL(
                "SELECT id, %s FROM %s WHERE %s IS NOT NULL ORDER BY id",
                SQL.identifier(column),
                SQL.identifier(model._table),
                SQL.identifier(column),
            )
        )


@typing.runtime_checkable
class StorageBackend(typing.Protocol):
    sequences: SequenceStore
    columns: ColumnStore

    def timezone_names(self, env) -> frozenset[str]: ...

    def create_rows(
        self,
        model: BaseModel,
        stored_list: list[dict[str, typing.Any]],
        columns: list[str],
        col_fields: list[Field],
    ) -> list[int]: ...

    def update_rows(
        self, model: BaseModel, fnames: tuple[str, ...], rows: list[tuple]
    ) -> None: ...

    def fetch(
        self,
        model: BaseModel,
        query: Query,
        column_fields: typing.Iterable[Field],
        other_fields: typing.Iterable[Field],
    ) -> BaseModel: ...

    def search(
        self,
        model: BaseModel,
        domain: Domain,
        offset: int,
        limit: int | None,
        order: str | None,
        *,
        check_access: bool = True,
        prof: typing.Any = None,
    ) -> Query: ...

    # The domain as the caller wrote it, before `optimize_full`: a backend
    # that compiles domains itself answers here and the optimisation is
    # skipped; None means "optimise and call search" as before.
    def search_raw(
        self,
        model: BaseModel,
        domain: Domain,
        offset: int,
        limit: int | None,
        order: str | None,
        *,
        check_access: bool = True,
    ) -> Query | None: ...

    def as_query(self, model: BaseModel, ordered: bool = True) -> Query: ...

    def descendants(
        self,
        model: BaseModel,
        parent_field: str,
        root_ids: typing.Collection[int],
        *,
        domain: Domain,
        step_domain: Domain,
        same_columns: typing.Sequence[str] = (),
    ) -> Query: ...

    def ancestors(
        self, model: BaseModel, parent_field: str, ids: typing.Collection[int]
    ) -> list[tuple[int, int | None]]: ...

    def read_group_rows(
        self,
        model: BaseModel,
        select: SQL,
        *,
        domain: Domain,
        query: Query,
        groupby: typing.Sequence[str],
        aggregates: typing.Sequence[str],
        having: typing.Any,
        order: str | None,
        limit: int | None,
        offset: int,
    ) -> list[tuple]: ...

    def read_grouping_sets_rows(
        self,
        model: BaseModel,
        select: SQL,
        *,
        domain: Domain,
        query: Query,
        grouping_sets: typing.Sequence[typing.Sequence[str]],
        groupby_terms: typing.Mapping[str, SQL],
        aggregates: typing.Sequence[str],
        order: str | None,
    ) -> list[tuple]: ...

    def get_existing_ids(
        self, model: BaseModel, ids: typing.Iterable[int]
    ) -> set[int]: ...

    def has_rows_beyond(self, model: BaseModel, count: int) -> bool: ...

    def has_cycle(
        self,
        model: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        ids: typing.Collection[int],
    ) -> bool: ...

    def increment_columns_skip_locked(
        self, model: BaseModel, columns: typing.Sequence[str], ids: typing.Sequence[int]
    ) -> int: ...

    def lock_for_update(
        self, model: BaseModel, *, allow_referencing: bool = False
    ) -> None: ...

    def try_lock_for_update(
        self,
        model: BaseModel,
        *,
        allow_referencing: bool = False,
        limit: int | None = None,
    ) -> BaseModel: ...

    def unlink_rows(self, model: BaseModel, sub_ids: tuple[int, ...]) -> None: ...

    def read_m2m_groups(
        self,
        records: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        query: Query,
    ) -> dict[int, list[int]]: ...

    def count_m2m_groups(
        self,
        records: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        query: Query,
    ) -> dict[int, int]: ...

    def set_parent_paths(
        self, model: BaseModel, ids: typing.Sequence[int]
    ) -> list[tuple[int, str]]: ...

    def records_with_parent_changed(
        self, model: BaseModel, parent_to_ids: dict[typing.Any, list[int]]
    ) -> list[int]: ...

    def move_parent_paths(
        self, model: BaseModel, ids: typing.Sequence[int], prefix: str
    ) -> dict[int, str]: ...

    def link_m2m_pairs(
        self,
        model: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        pairs: typing.Iterable[tuple[int, int]],
    ) -> None: ...

    def unlink_m2m_pairs(
        self,
        model: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        pairs: typing.Iterable[tuple[int, int]],
    ) -> None: ...


def _prepare_postgres_search_query(
    model: BaseModel,
    domain: Domain,
    offset: int,
    limit: int | None,
    order: str | None,
    *,
    check_access: bool = True,
    prof: typing.Any = None,
) -> Query:
    if prof is None:
        prof = _OrmProfile(_orm_read)
    query = Query(model.env, model._table, model._table_sql)
    if not domain.is_true():
        query.add_where(domain._to_sql(model, model._table, query))
    prof.mark("domain")

    if check_access:
        model_sudo = model.sudo().with_context(active_test=False)
        sec_domain = model.env.registry.access_policy.record_domain(
            model.env, model._name, "read"
        )
        sec_domain = sec_domain.optimize_full(model_sudo)
        if sec_domain.is_false():
            _debug.logic(
                "backend.search.rules_deny_all", model=model._name, uid=model.env.uid
            )
            return model.browse()._as_query()
        if not sec_domain.is_true():
            _debug.logic(
                "backend.search.rules_applied", model=model._name, uid=model.env.uid
            )
            query.add_where(sec_domain._to_sql(model_sudo, model._table, query))
    prof.mark("rules")

    if order:
        query.order = _total_order(model, order, model._order_to_sql(order, query))

    if limit is not None and limit is not False:
        query.limit = 1 if limit is True else limit
    if offset is not None and offset is not False:
        query.offset = 1 if offset is True else offset

    prof.stop("query")
    prof.report(_orm_read, "_search %s", model._name)
    return query


def _total_order(model: BaseModel, order: str, order_sql: SQL) -> SQL:
    id_sql = SQL.identifier(model._table, "id")
    if not order_sql:
        return id_sql
    if any(part.split()[:1] == ["id"] for part in order.split(",")):
        return order_sql
    return SQL("%s, %s", order_sql, id_sql)


def _single_table_where(model: BaseModel, domain: Domain) -> SQL | None:
    if domain.is_true():
        return None
    query = model._search(domain)
    if query.from_clause != SQL.identifier(model._table):
        raise ValueError(
            f"descendants({model._name}): the domain must resolve against "
            f"{model._table} alone, the recursive query inlines its WHERE clause "
            f"and cannot carry a join. Got: {query.from_clause}"
        )
    return query.where_clause if query._where_clauses else None


def _get_fetch_term(model: BaseModel, field: Field, query: Query) -> SQL:
    # the memo is keyed by field alone: a _field_to_sql override that answers
    # the bare identifier under one environment and an expression under
    # another would be served the identifier from the second call on, so an
    # override customises a column in every environment or in none
    if field.translate:
        return _get_translated_fetch_term(model, field, query)
    term = field._fetch_term
    if term is not None:
        model._check_field_access(field, "read")
        return term
    column = model._field_to_sql(model._table, field.name, query)
    sql = SQL("%s", column, to_flush=(f for f in column.to_flush if f != field))
    if (
        not sql.params
        and not sql.to_flush
        and sql.code == f'"{model._table}"."{field.name}"'
    ):
        field._fetch_term = sql
        if tuple(column.to_flush) == (field,):
            # the same identifier with the field to flush, for every other
            # place that spells the column against its own table
            field._column_term = column
    return sql


def _get_translated_fetch_term(model: BaseModel, field: Field, query: Query) -> SQL:
    if model.env.context.get("prefetch_langs"):
        return model._field_to_sql(model._table, field.name, query)
    langs = field.get_translation_fallback_langs(model.env)
    terms = field._fetch_terms_by_langs
    term = terms.get(langs) if terms is not None else None
    if term is not None:
        model._check_field_access(field, "read")
        return term
    sql = model._field_to_sql(model._table, field.name, query)
    column = f'"{model._table}"."{field.name}"->>%s'
    expected = (
        column if len(langs) == 1 else f"COALESCE({', '.join([column] * len(langs))})"
    )
    if sql.params == langs and sql.code == expected and tuple(sql.to_flush) == (field,):
        if terms is None:
            terms = field._fetch_terms_by_langs = {}
        terms[langs] = sql
    return sql


class PostgresBackend:
    sequences: SequenceStore = PostgresSequenceStore()
    columns: ColumnStore = PostgresColumnStore()

    __slots__ = ()

    def timezone_names(self, env) -> frozenset[str]:
        # the names the server's timezone() accepts, once per database
        names = _sql_timezone_names.get(env.cr.dbname)
        if names is None:
            with _debug.perf("backend.timezones_loaded", cr=env.cr) as span:
                env.cr.execute("SELECT name FROM pg_timezone_names")
                names = frozenset(name for [name] in env.cr.fetchall())
                span.set(timezones=len(names))
            _sql_timezone_names[env.cr.dbname] = names
        return names

    def create_rows(
        self,
        model: BaseModel,
        stored_list: list[dict[str, typing.Any]],
        columns: list[str],
        col_fields: list[Field],
    ) -> list[int]:
        cr = model.env.cr
        ids: list[int] = []
        use_copy = (
            not COPY_DISABLED
            and col_fields
            and len(stored_list) >= COPY_THRESHOLD
            and not cr.in_pipeline
        )
        _debug.logic(
            "backend.create_rows.strategy",
            model=model._name,
            strategy="copy" if use_copy else "insert",
            rows=len(stored_list),
            columns=len(columns),
            in_pipeline=cr.in_pipeline,
        )
        subprof = _OrmProfile(_orm_crud)

        if use_copy:
            copy_rows = self._prepare_insert_rows(
                model, stored_list, columns, col_fields
            )
            batch_ids = cr.copy_from(
                model._table,
                columns,
                copy_rows,
                returning_ids=True,
                binary=True,
            )
            ids.extend(batch_ids)
            subprof.stop()
            subprof.report(
                _orm_crud,
                "_create %s: %d records via COPY (%d columns)",
                model._name,
                len(stored_list),
                len(columns),
            )
        else:
            if col_fields:
                rows: list[tuple] = self._prepare_insert_rows(
                    model, stored_list, columns, col_fields
                )
            else:
                columns = ["id"]
                rows = [(SQL_DEFAULT,) for _ in stored_list]

            cr.execute(
                SQL(
                    'INSERT INTO %s (%s) VALUES %s RETURNING "id"',
                    SQL.identifier(model._table),
                    SQL(", ").join(map(SQL.identifier, columns)),
                    SQL(", ").join(SQL("(%s)", SQL(", ").join(row)) for row in rows),
                )
            )
            ids.extend(id_ for (id_,) in cr.fetchall())
            subprof.stop()
            subprof.report(
                _orm_crud,
                "_create %s: %d records via INSERT (%d columns)",
                model._name,
                len(stored_list),
                len(columns),
            )
        return ids

    @staticmethod
    def _prepare_insert_rows(
        model: BaseModel,
        stored_list: list[dict[str, typing.Any]],
        columns: list[str],
        col_fields: list[Field],
    ) -> list[tuple]:
        return [
            tuple(
                field.convert_to_column_insert(
                    stored[fname], model, stored, validate=not field.is_html
                )
                if fname in stored
                else None
                for fname, field in zip(columns, col_fields, strict=True)
            )
            for stored in stored_list
        ]

    def update_rows(
        self, model: BaseModel, fnames: tuple[str, ...], rows: list[tuple]
    ) -> None:
        if (values := self._resolve_uniform_update_values(rows)) is not None:
            _debug.logic(
                "backend.update_rows.strategy",
                model=model._name,
                strategy="uniform",
                rows=len(rows),
                columns=len(fnames),
            )
            self._update_rows_uniform(model, fnames, [row[0] for row in rows], values)
            return
        _debug.logic(
            "backend.update_rows.strategy",
            model=model._name,
            strategy="values",
            rows=len(rows),
            columns=len(fnames),
            batches=-(-len(rows) // UPDATE_BATCH_SIZE),
        )
        for sub_rows in batched(rows, UPDATE_BATCH_SIZE, strict=False):
            self._update_rows_values(model, fnames, sub_rows)

    @staticmethod
    def _resolve_uniform_update_values(rows: list[tuple]) -> tuple | None:
        if len(rows) < 2:
            return None
        values = rows[0][1:]
        if not all(isinstance(value, _UNIFORM_UPDATE_TYPES) for value in values):
            _debug.logic(
                "backend.update_rows.uniform_rejected",
                rows=len(rows),
                reason="value_type",
            )
            return None
        if any(row[1:] != values for row in rows):
            _debug.logic(
                "backend.update_rows.uniform_rejected",
                rows=len(rows),
                reason="values_differ",
            )
            return None
        return values

    @staticmethod
    def _update_assignments(
        model: BaseModel,
        fnames: tuple[str, ...],
        value_sql: Callable[[int, str, SQL, SQL], SQL],
    ) -> tuple[list[SQL], list[SQL]]:
        columns = []
        assignments = []
        for index, fname in enumerate(fnames):
            field = model._fields[fname]
            column_type = field.column_type
            if not field.is_column or column_type is None:
                raise RuntimeError(
                    f"_execute_update: {field} is not a stored column field"
                )
            column = SQL.identifier(fname)
            cast = SQL(column_type[1])  # noqa: E8501  from the field declaration
            expr = value_sql(index, fname, column, cast)
            if field.translate is True:
                _debug.logic(
                    "backend.update_rows.translated_merge",
                    model=model._name,
                    field=fname,
                )
                expr = SQL(
                    """CASE WHEN %(expr)s IS NULL THEN NULL ELSE
                        COALESCE(%(table)s.%(column)s, jsonb_build_object(
                            'en_US', jsonb_path_query_first(%(expr)s, '$.*')
                        )) || %(expr)s
                    END""",
                    table=SQL.identifier(model._table),
                    column=column,
                    expr=expr,
                )
            if field.company_dependent:
                fallbacks = model.env.registry.metaschema.field_column_fallbacks(
                    model.env, model._name, fname
                )
                _debug.logic(
                    "backend.update_rows.company_dependent_merge",
                    model=model._name,
                    field=fname,
                )
                expr = SQL(
                    """(SELECT jsonb_object_agg(d.key, d.value)
                    FROM jsonb_each(COALESCE(%(table)s.%(column)s, '{}'::jsonb) || %(expr)s) d
                    JOIN jsonb_each(%(fallbacks)s) f
                    ON d.key = f.key AND d.value != f.value)""",
                    table=SQL.identifier(model._table),
                    column=column,
                    expr=expr,
                    fallbacks=fallbacks,
                )
            columns.append(column)
            assignments.append(SQL("%s = %s", column, expr))
        return columns, assignments

    def _update_rows_values(
        self,
        model: BaseModel,
        fnames: tuple[str, ...],
        rows: tuple[tuple, ...] | list[tuple],
    ) -> None:
        columns, assignments = self._update_assignments(
            model,
            fnames,
            lambda _index, _fname, column, cast: SQL('"__tmp".%s::%s', column, cast),
        )
        model.env.cr.execute(
            SQL(
                """ UPDATE %(table)s
                SET %(assignments)s
                FROM (VALUES %(values)s) AS "__tmp"("id", %(columns)s)
                WHERE %(table)s."id" = "__tmp"."id"
            """,
                table=SQL.identifier(model._table),
                assignments=SQL(", ").join(assignments),
                values=SQL(", ").join(rows),
                columns=SQL(", ").join(columns),
            )
        )

    def _update_rows_uniform(
        self, model: BaseModel, fnames: tuple[str, ...], ids: list[int], values: tuple
    ) -> None:
        _columns, assignments = self._update_assignments(
            model,
            fnames,
            lambda index, _fname, _column, cast: SQL("%s::%s", values[index], cast),
        )
        model.env.cr.execute(
            SQL(
                """UPDATE %(table)s SET %(assignments)s WHERE "id" = ANY(%(ids)s)""",
                table=SQL.identifier(model._table),
                assignments=SQL(", ").join(assignments),
                ids=ids,
            )
        )

    def fetch(
        self,
        model: BaseModel,
        query: Query,
        column_fields: typing.Iterable[Field],
        other_fields: typing.Iterable[Field],
    ) -> BaseModel:
        prof = _OrmProfile(_orm_read)
        env = model.env
        context = env.context
        column_fields = OrderedSet(column_fields)
        other_fields = OrderedSet(other_fields)

        if column_fields:
            sql_terms = [SQL.identifier(model._table, "id")]
            for field in column_fields:
                if field.is_binary and (
                    context.get("bin_size") or context.get("bin_size_" + field.name)
                ):
                    sql = SQL(
                        "pg_size_pretty(length(%s)::bigint)",
                        model._field_to_sql(model._table, field.name, query),
                    )
                else:
                    sql = _get_fetch_term(model, field, query)
                sql_terms.append(sql)

            # this SELECT reads these rows and no other: their dirty values
            # are written here, and the query then flushes only what else it
            # reads. A pending compute is not flushed by a fetch: the row's
            # value stays pending and is computed when it is read
            select = query.select(*sql_terms)
            if model._ids:
                # a fetch of known rows: their dirty values are written here,
                # and the query then flushes only what else it reads. A
                # search_fetch keeps its flush: the WHERE reads every row
                model._flush_if_dirty(column_fields)
                fetched_columns = set(column_fields)
                select = select.with_to_flush(
                    [f for f in select.to_flush if f not in fetched_columns]
                )
            rows = env.execute_query(select)
            prof.mark("sql")

            if not rows:
                _debug.logic(
                    "backend.fetch.no_rows",
                    model=model._name,
                    columns=len(column_fields),
                )
                return model.browse()

            column_values = zip(*rows, strict=False)
            ids = next(column_values)
            fetched = model.browse(ids)

            core = env.core
            for field, values in zip(column_fields, column_values, strict=True):
                if field.is_stored_computed:
                    field._clear_dead_pending(fetched)
                    # a row whose compute is pending keeps it: the table holds
                    # the value before the change, not after it
                    members = (field, *field.tree_siblings)
                    if any(core.has_pending_field(member) for member in members):
                        keep = [
                            i
                            for i, id_ in enumerate(fetched._ids)
                            if not core.is_pending_in_tree(field, id_)
                        ]
                        if len(keep) != len(fetched):
                            field._insert_cache(
                                fetched.browse([fetched._ids[i] for i in keep]),
                                [values[i] for i in keep],
                            )
                            continue
                field._insert_cache(fetched, values)
            prof.mark("cache")
        else:
            _debug.logic(
                "backend.fetch.no_columns",
                model=model._name,
                other=len(other_fields),
            )
            fetched = model.browse(query)
            prof.mark("sql")
            prof.mark("cache")

        if fetched:
            for field in other_fields:
                field.read(fetched)

        prof.stop("other")
        prof.report(
            _orm_read,
            "_fetch_query %s: %d col + %d other fields -> %d rows",
            model._name,
            len(column_fields),
            len(other_fields),
            len(fetched),
        )

        return fetched

    def search(
        self,
        model: BaseModel,
        domain: Domain,
        offset: int,
        limit: int | None,
        order: str | None,
        *,
        check_access: bool = True,
        prof: typing.Any = None,
    ) -> Query:
        return _prepare_postgres_search_query(
            model, domain, offset, limit, order, check_access=check_access, prof=prof
        )

    def search_raw(
        self,
        model: BaseModel,
        domain: Domain,
        offset: int,
        limit: int | None,
        order: str | None,
        *,
        check_access: bool = True,
    ) -> Query | None:
        return None

    def as_query(self, model: BaseModel, ordered: bool = True) -> Query:
        query = Query(model.env, model._table, model._table_sql)
        query.set_result_ids(model._ids, ordered)
        return query

    def ancestors(
        self, model: BaseModel, parent_field: str, ids: typing.Collection[int]
    ) -> list[tuple[int, int | None]]:
        if not ids:
            return []
        return model.env.execute_query(
            SQL(
                """
                WITH RECURSIVE ancestry AS (
                    SELECT id, %(parent)s AS parent_id FROM %(table)s WHERE id IN %(ids)s
                UNION
                    SELECT parent.id, parent.%(parent)s
                    FROM %(table)s parent
                    INNER JOIN ancestry child ON child.parent_id = parent.id
                )
                SELECT id, parent_id FROM ancestry
                """,
                table=SQL.identifier(model._table),
                # the closure reads the column: a pending write has to reach it
                parent=SQL.identifier(
                    parent_field, to_flush=model._fields[parent_field]
                ),
                ids=tuple(ids),
            )
        )

    def descendants(
        self,
        model: BaseModel,
        parent_field: str,
        root_ids: typing.Collection[int],
        *,
        domain: Domain,
        step_domain: Domain,
        same_columns: typing.Sequence[str] = (),
    ) -> Query:
        table = SQL.identifier(model._table)
        base_where = _single_table_where(model, domain)
        step_where = _single_table_where(model, domain & step_domain)
        columns = SQL(", ").join(
            SQL(", %s", SQL.identifier(model._table, column)) for column in same_columns
        )
        same = SQL("").join(
            SQL(
                " AND COALESCE(%s::text, '') = COALESCE(parent.%s::text, '')",
                SQL.identifier(model._table, column),
                SQL.identifier(column),
            )
            for column in same_columns
        )
        closure = SQL(
            """WITH RECURSIVE closure AS (
                SELECT %(id)s%(columns)s FROM %(table)s
                WHERE %(id)s = ANY(%(roots)s)%(base_where)s
            UNION
                SELECT %(id)s%(columns)s FROM %(table)s
                JOIN closure parent ON parent.id = %(parent)s
                WHERE TRUE%(step_where)s%(same)s
            )
            SELECT id FROM closure""",
            id=SQL.identifier(model._table, "id"),
            columns=columns,
            table=table,
            roots=list(root_ids),
            base_where=SQL(" AND (%s)", base_where) if base_where else SQL(),
            # the closure reads the column: a pending write has to reach it
            parent=SQL.identifier(
                model._table, parent_field, to_flush=model._fields[parent_field]
            ),
            step_where=SQL(" AND (%s)", step_where) if step_where else SQL(),
            same=same,
        )
        query = Query(model.env, model._table, model._table_sql)
        query.add_where(SQL("%s IN (%s)", SQL.identifier(model._table, "id"), closure))
        return query

    def read_group_rows(
        self,
        model: BaseModel,
        select: SQL,
        *,
        domain: Domain,
        query: Query,
        groupby: typing.Sequence[str],
        aggregates: typing.Sequence[str],
        having: typing.Any,
        order: str | None,
        limit: int | None,
        offset: int,
    ) -> list[tuple]:
        return model.env.execute_query(select)

    def read_grouping_sets_rows(
        self,
        model: BaseModel,
        select: SQL,
        *,
        domain: Domain,
        query: Query,
        grouping_sets: typing.Sequence[typing.Sequence[str]],
        groupby_terms: typing.Mapping[str, SQL],
        aggregates: typing.Sequence[str],
        order: str | None,
    ) -> list[tuple]:
        return model.env.execute_query(select)

    def get_existing_ids(self, model: BaseModel, ids: typing.Iterable[int]) -> set[int]:
        ids = list(ids)
        query = Query(model.env, model._table, model._table_sql)
        query.add_where(SQL("%s = ANY(%s)", SQL.identifier(model._table, "id"), ids))
        existing = {id_ for [id_] in model.env.execute_query(query.select())}
        _debug.perf.count(
            "backend.existing_ids",
            model=model._name,
            requested=len(ids),
            existing=len(existing),
        )
        return existing

    def has_rows_beyond(self, model: BaseModel, count: int) -> bool:
        cr = model.env.cr
        cr.execute(
            SQL(
                "SELECT 1 FROM %s OFFSET %s LIMIT 1",
                SQL.identifier(model._table),
                count,
            )
        )
        return cr.fetchone() is not None

    def has_cycle(
        self,
        model: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        ids: typing.Collection[int],
    ) -> bool:
        cr = model.env.cr
        cr.execute(
            SQL(
                """
            WITH RECURSIVE __reachability AS (
                SELECT %(col1)s AS source, %(col2)s AS destination
                FROM %(rel)s
                WHERE %(col1)s IN %(ids)s AND %(col2)s IS NOT NULL
            UNION
                SELECT r.source, t.%(col2)s
                FROM __reachability r
                JOIN %(rel)s t ON r.destination = t.%(col1)s AND t.%(col2)s IS NOT NULL
            )
            SELECT 1 FROM __reachability
            WHERE source = destination
            LIMIT 1
            """,
                ids=tuple(ids),
                rel=SQL.identifier(relation),
                col1=SQL.identifier(column1),
                col2=SQL.identifier(column2),
            )
        )
        return cr.fetchone() is not None

    def increment_columns_skip_locked(
        self, model: BaseModel, columns: typing.Sequence[str], ids: typing.Sequence[int]
    ) -> int:
        cr = model.env.cr
        table = SQL.identifier(model._table)
        cr.execute(
            SQL(
                """
            UPDATE %s
               SET %s
             WHERE id IN (SELECT id FROM %s WHERE id = ANY(%s) FOR UPDATE SKIP LOCKED)
            """,
                table,
                SQL(", ").join(
                    SQL(
                        "%s = COALESCE(%s, 0) + 1",
                        SQL.identifier(column),
                        SQL.identifier(column),
                    )
                    for column in columns
                ),
                table,
                list(ids),
            )
        )
        return cr.rowcount

    @staticmethod
    def _lock_clause(allow_referencing: bool) -> SQL:
        if allow_referencing:
            return SQL("FOR NO KEY UPDATE SKIP LOCKED")
        return SQL("FOR UPDATE SKIP LOCKED")

    def lock_for_update(
        self, model: BaseModel, *, allow_referencing: bool = False
    ) -> None:
        ids = {id_ for id_ in model._ids if id_}
        if not ids:
            return
        query = Query(model.env, model._table, model._table_sql)
        query.add_where(
            SQL("%s = ANY(%s)", SQL.identifier(model._table, "id"), list(ids))
        )
        sql = SQL("%s %s", query.select(), self._lock_clause(allow_referencing))
        rows = model.env.execute_query(sql)
        if len(rows) != len(ids):
            _debug.logic(
                "backend.lock_for_update.contended",
                model=model._name,
                requested=len(ids),
                locked=len(rows),
                allow_referencing=allow_referencing,
            )
            raise LockError(model.env._("Cannot grab a lock on records"))

    def try_lock_for_update(
        self,
        model: BaseModel,
        *,
        allow_referencing: bool = False,
        limit: int | None = None,
    ) -> BaseModel:
        new_ids, ids = partition(lambda i: isinstance(i, NewId), model._ids)
        if limit is not None and len(new_ids) >= limit:
            return model.browse(new_ids[:limit])
        if not ids:
            return model
        if limit is not None:
            query = self.as_query(model.browse(ids), ordered=True)
            query.limit = limit - len(new_ids)
        else:
            query = Query(model.env, model._table, model._table_sql)
            query.add_where(
                SQL("%s = ANY(%s)", SQL.identifier(model._table, "id"), list(ids))
            )
        sql = SQL("%s %s", query.select(), self._lock_clause(allow_referencing))
        real_ids = (id_ for [id_] in model.env.execute_query(sql))
        valid_ids = {*real_ids, *new_ids}
        _debug.perf.count(
            "backend.try_lock_for_update",
            model=model._name,
            requested=len(ids),
            locked=len(valid_ids) - len(new_ids),
            limit=limit,
        )
        return model.browse(i for i in model._ids if i in valid_ids)

    def unlink_rows(self, model: BaseModel, sub_ids: tuple[int, ...]) -> None:
        env = model.env
        cr = env.cr
        records = model.browse(sub_ids)
        if not all(isinstance(id_, int) and id_ > 0 for id_ in sub_ids):
            raise TypeError(
                f"unlink_rows: sub_ids must be positive ints, got {sub_ids!r}"
            )

        cr.execute(
            SQL(
                "DELETE FROM %s WHERE id = ANY(%s)",
                SQL.identifier(model._table),
                list(sub_ids),
            )
        )

        many2one_fields = env.registry.many2one_company_dependents[model._name]
        uninstalling = env.context.get(MODULE_UNINSTALL_FLAG)
        _debug.pipeline(
            "backend.unlink_rows",
            model=model._name,
            rows=len(sub_ids),
            company_dependent_referrers=len(many2one_fields),
            uninstalling=bool(uninstalling),
        )
        if many2one_fields and not uninstalling:
            self._unlink_default_guard(model, sub_ids, many2one_fields)

        for field in many2one_fields:
            referrer = env[field.model_name]
            if field.ondelete == "restrict" and not uninstalling:
                self._unlink_restrict_guard(model, referrer, field, sub_ids)
            else:
                self._unlink_clear_company_dependent(referrer, field, sub_ids)

        env.registry.metaschema.discard_defaults(env, records)

    @staticmethod
    def _unlink_default_guard(
        model: BaseModel, sub_ids: tuple[int, ...], many2one_fields
    ) -> None:
        referencing = model.env.registry.metaschema.default_referencing(
            model.env, many2one_fields, sub_ids
        )
        if referencing is None:
            return
        field, record_id = referencing
        record = model.browse(record_id)
        _debug.logic(
            "backend.unlink.blocked_by_default",
            model=model._name,
            field=f"{field.model_name}.{field.name}",
            record=record.id,
        )
        raise UserError(
            _(
                "Unable to delete %(record)s because it is used as the default value of %(field)s",
                record=record,
                field=field,
            )
        )

    @staticmethod
    def _unlink_restrict_guard(
        model: BaseModel, referrer: BaseModel, field: Field, sub_ids: tuple[int, ...]
    ) -> None:
        if res := model.env.execute_query(
            SQL(
                """
            SELECT id, %(field)s
            FROM %(table)s
            WHERE %(field)s IS NOT NULL
            AND %(field)s @? %(jsonpath)s
            ORDER BY id
            LIMIT 1
            """,
                table=SQL.identifier(referrer._table),
                field=SQL.identifier(field.name),
                jsonpath=f"$.* ? ({' || '.join(f'@ == {id_}' for id_ in sub_ids)})",
            )
        ):
            on_restrict_id, field_json = res[0]
            to_delete_id = next(iter(field_json.values()))
            on_restrict_record = referrer.browse(on_restrict_id)
            to_delete_record = model.browse(to_delete_id)
            _debug.logic(
                "backend.unlink.blocked_by_restrict",
                model=model._name,
                referrer=referrer._name,
                field=field.name,
                record=to_delete_id,
            )
            raise UserError(
                _(
                    "You cannot delete %(to_delete_record)s, as it is used by %(on_restrict_record)s",
                    to_delete_record=to_delete_record,
                    on_restrict_record=on_restrict_record,
                )
            )

    @staticmethod
    def _unlink_clear_company_dependent(
        referrer: BaseModel, field: Field, sub_ids: tuple[int, ...]
    ) -> None:
        affected = referrer.env.execute_query(
            SQL(
                """
            UPDATE %(table)s
            SET %(field)s = (
                SELECT jsonb_object_agg(
                    key,
                    CASE
                        WHEN value::int4 in %(ids)s THEN NULL
                        ELSE value::int4
                    END)
                FROM jsonb_each_text(%(field)s)
            )
            WHERE %(field)s IS NOT NULL
            AND %(field)s @? %(jsonpath)s
            RETURNING id
            """,
                table=SQL.identifier(referrer._table),
                field=SQL.identifier(field.name),
                ids=sub_ids,
                jsonpath=f"$.* ? ({' || '.join(f'@ == {id_}' for id_ in sub_ids)})",
            )
        )
        if affected:
            _debug.logic(
                "backend.unlink.company_dependent_cleared",
                model=referrer._name,
                field=field.name,
                affected=len(affected),
            )
            affected_recs = referrer.browse(row[0] for row in affected)
            affected_recs.modified([field.name])

    def set_parent_paths(
        self, model: BaseModel, ids: typing.Sequence[int]
    ) -> list[tuple[int, str]]:
        return model.env.execute_query(
            SQL(
                """ UPDATE %(table)s node
                SET parent_path=concat((
                        SELECT parent.parent_path
                        FROM %(table)s parent
                        WHERE parent.id=node.%(parent)s
                    ), node.id, '/')
                WHERE node.id IN %(ids)s
                RETURNING node.id, node.parent_path """,
                table=SQL.identifier(model._table),
                parent=SQL.identifier(model._parent_name),
                ids=tuple(ids),
            )
        )

    def records_with_parent_changed(
        self, model: BaseModel, parent_to_ids: dict[typing.Any, list[int]]
    ) -> list[int]:
        sql_parent = SQL.identifier(model._parent_name)
        conditions = []
        for parent_id, ids in parent_to_ids.items():
            if parent_id:
                condition = SQL(
                    "(%s != %s OR %s IS NULL)", sql_parent, parent_id, sql_parent
                )
            else:
                condition = SQL("%s IS NOT NULL", sql_parent)
            conditions.append(SQL('("id" = ANY(%s) AND %s)', list(ids), condition))
        rows = model.env.execute_query(
            SQL(
                "SELECT id FROM %s WHERE %s ORDER BY id",
                SQL.identifier(model._table),
                SQL(" OR ").join(conditions),
            )
        )
        return [row[0] for row in rows]

    def move_parent_paths(
        self, model: BaseModel, ids: typing.Sequence[int], prefix: str
    ) -> dict[int, str]:
        return dict(
            model.env.execute_query(
                SQL(
                    """ UPDATE %(table)s child
                SET parent_path = concat(%(prefix)s::text, substr(child.parent_path,
                        length(node.parent_path) - length(node.id || '/') + 1))
                FROM %(table)s node
                WHERE node.id IN %(ids)s
                AND child.parent_path LIKE concat(node.parent_path, %(wildcard)s::text)
                RETURNING child.id, child.parent_path """,
                    table=SQL.identifier(model._table),
                    prefix=prefix,
                    ids=tuple(ids),
                    wildcard="%",
                )
            )
        )

    def read_m2m_groups(
        self,
        records: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        query: Query,
    ) -> dict[int, list[int]]:
        sql_id1 = SQL.identifier(relation, column1)
        sql_id2 = SQL.identifier(relation, column2)
        query.add_join(
            "JOIN",
            relation,
            None,
            SQL("%s = %s", sql_id2, SQL.identifier(query.table, "id")),
        )
        query.add_where(SQL("%s = ANY(%s)", sql_id1, list(records.ids)))
        group: dict[int, list[int]] = defaultdict(list)
        for id1, id2 in records.env.execute_query(query.select(sql_id1, sql_id2)):
            group[id1].append(id2)
        return group

    def count_m2m_groups(
        self,
        records: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        query: Query,
    ) -> dict[int, int]:
        # one row per record, not one per pair: what a Count field is for
        sql_id1 = SQL.identifier(relation, column1)
        rows = records.env.execute_query(
            SQL(
                "SELECT %s, count(*) FROM %s WHERE %s = ANY(%s) AND %s IN (%s) "
                "GROUP BY %s",
                sql_id1,
                SQL.identifier(relation),
                sql_id1,
                list(records.ids),
                SQL.identifier(relation, column2),
                query.subselect(),
                sql_id1,
            )
        )
        return dict(rows)

    def link_m2m_pairs(
        self,
        model: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        pairs: typing.Iterable[tuple[int, int]],
    ) -> None:
        cr = model.env.cr
        cr.execute(
            SQL(
                "INSERT INTO %s (%s, %s) VALUES %s ON CONFLICT DO NOTHING",
                SQL.identifier(relation),
                SQL.identifier(column1),
                SQL.identifier(column2),
                SQL(", ").join(pairs),
            )
        )
        _debug.perf.count(
            "backend.m2m.linked",
            model=model._name,
            relation=relation,
            inserted=cr.rowcount,
        )

    def unlink_m2m_pairs(
        self,
        model: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        pairs: typing.Iterable[tuple[int, int]],
    ) -> None:
        xs_to_ys: dict[frozenset, set] = defaultdict(set)
        y_to_xs: dict[typing.Any, set] = defaultdict(set)
        for x, y in pairs:
            y_to_xs[y].add(x)
        for y, xs in y_to_xs.items():
            xs_to_ys[frozenset(xs)].add(y)
        cr = model.env.cr
        cr.execute(
            SQL(
                "DELETE FROM %s WHERE %s",
                SQL.identifier(relation),
                SQL(" OR ").join(
                    SQL(
                        "%s = ANY(%s) AND %s = ANY(%s)",
                        SQL.identifier(column1),
                        list(xs),
                        SQL.identifier(column2),
                        list(ys),
                    )
                    for xs, ys in xs_to_ys.items()
                ),
            )
        )
        _debug.perf.count(
            "backend.m2m.unlinked",
            model=model._name,
            relation=relation,
            groups=len(xs_to_ys),
            deleted=cr.rowcount,
        )


POSTGRES_BACKEND = PostgresBackend()


_sql_timezone_names: dict[str, frozenset[str]] = {}
