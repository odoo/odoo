from __future__ import annotations

import functools
import json
import logging
import os
import re
import typing
import zoneinfo
from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, date, datetime
from datetime import timedelta as _timedelta
from decimal import Decimal
from itertools import batched, product

from psycopg import errors as pgerrors
from psycopg.errors import (
    ForeignKeyViolation,
    InvalidTextRepresentation,
    NotNullViolation,
    NumericValueOutOfRange,
    UniqueViolation,
    UntranslatableCharacter,
)
from psycopg.types.json import Json, Jsonb, JsonDumper

from odoo.exceptions import LockError, UserError
from odoo.libs.accel import fast_clone
from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import _OrmProfile
from odoo.tools import SQL, OrderedSet, Query, human_size, partition
from odoo.tools.translate import _

from ..components.storage import NamedSequence
from ..models.table_objects import Constraint
from ..primitives import (
    MODULE_UNINSTALL_FLAG,
    SQL_DEFAULT,
    UPDATE_BATCH_SIZE,
    NewId,
)
from ._search_flush import flush_search_dependencies

if typing.TYPE_CHECKING:
    from ..components.storage import DictBackend
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
        return human_size(len(value))
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


class InMemorySequenceStore:
    __slots__ = ("storage",)

    def __init__(self, storage: DictBackend):
        self.storage = storage

    def create(self, env, name: str, *, increment: int, start: int) -> None:
        self.storage._named_sequences[name] = NamedSequence(increment, max(start, 1))

    def drop(self, env, names: typing.Collection[str]) -> None:
        for name in names:
            self.storage._named_sequences.pop(name, None)

    def alter(
        self,
        env,
        name: str,
        *,
        increment: int | None = None,
        restart: int | None = None,
    ) -> None:
        sequence = self.storage._named_sequences.get(name)
        if sequence is None:
            return
        if increment is not None:
            sequence.increment = increment
        if restart is not None:
            sequence.last_value = max(restart, 1)
            sequence.is_called = False

    def next_values(self, env, name: str, count: int) -> list[int]:
        return self.storage._named_sequences[name].next_values(count)

    def peek(self, env, names: typing.Collection[str]) -> dict[str, int]:
        sequences = self.storage._named_sequences
        return {name: sequences[name].peek() for name in names if name in sequences}


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
    ) -> int: ...

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

    def scan(self, model: BaseModel, column: str) -> list[tuple[int, typing.Any]]: ...


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
    ) -> int:
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

    def scan(self, model: BaseModel, column: str) -> list[tuple[int, typing.Any]]:
        # every row holding a value in the column, by id, as stored
        return model.env.execute_query(
            SQL(
                "SELECT id, %s FROM %s WHERE %s IS NOT NULL ORDER BY id",
                SQL.identifier(column),
                SQL.identifier(model._table),
                SQL.identifier(column),
            )
        )


class InMemoryColumnStore:
    __slots__ = ("storage",)

    def __init__(self, storage: DictBackend):
        self.storage = storage

    def read(
        self, model: BaseModel, column: str, ids: typing.Collection[int]
    ) -> dict[int, typing.Any]:
        rows = self.storage.get_rows(model._table, list(ids))
        return {id_: row.get(column) for id_, row in rows.items()}

    def write(
        self,
        model: BaseModel,
        column: str,
        rows: typing.Collection[tuple[int, typing.Any]],
    ) -> None:
        self.storage.update_rows(
            model._table, [(id_, {column: _unwrap_json(value)}) for id_, value in rows]
        )

    def fetch_and_add(
        self, model: BaseModel, column: str, record_id: int, delta: int
    ) -> int:
        row = self.storage.get_row(model._table, record_id) or {}
        value = row.get(column) or 0
        self.storage.update_rows(model._table, [(record_id, {column: value + delta})])
        return value

    def try_write(
        self, model: BaseModel, column: str, record_id: int, value: typing.Any
    ) -> bool:
        self.storage.update_rows(model._table, [(record_id, {column: value})])
        return True

    def merge_json(
        self,
        model: BaseModel,
        column: str,
        record_id: int,
        fallback: dict[str, typing.Any],
        value: dict[str, typing.Any],
    ) -> int:
        row = self.storage.get_row(model._table, record_id)
        if row is None:
            return 0
        stored = _unwrap_json(row.get(column)) or {}
        merged = {
            key: item
            for key, item in {
                **_unwrap_json(fallback),
                **stored,
                **_unwrap_json(value),
            }.items()
            if item is not None
        }
        self.storage.update_rows(model._table, [(record_id, {column: merged or None})])
        return 1

    def scan(self, model: BaseModel, column: str) -> list[tuple[int, typing.Any]]:
        storage = self.storage
        return [
            (row_id, _unwrap_json(row[column]))
            for row_id in sorted(storage.get_table_ids(model._table))
            if (row := storage.get_row(model._table, row_id)) is not None
            and row.get(column) is not None
        ]


@typing.runtime_checkable
class StorageBackend(typing.Protocol):
    sequences: SequenceStore
    columns: ColumnStore

    supports_column_scan: bool

    supports_recursive_queries: bool

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

    def get_existing_ids(
        self, model: BaseModel, ids: typing.Iterable[int]
    ) -> set[int]: ...

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


def _fetch_term(model: BaseModel, field: Field, query: Query) -> SQL:
    # the memo is keyed by field alone: a _field_to_sql override that answers
    # the bare identifier under one environment and an expression under
    # another would be served the identifier from the second call on, so an
    # override customises a column in every environment or in none
    if field.translate:
        return _fetch_translated_term(model, field, query)
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


def _fetch_translated_term(model: BaseModel, field: Field, query: Query) -> SQL:
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

    supports_column_scan: bool = True

    supports_recursive_queries: bool = True

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
                    sql = _fetch_term(model, field, query)
                sql_terms.append(sql)

            rows = env.execute_query(query.select(*sql_terms))
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

            for field, values in zip(column_fields, column_values, strict=True):
                if field.is_stored_computed:
                    field._clear_dead_pending(fetched)
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
                parent=SQL.identifier(parent_field),
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
            parent=SQL.identifier(model._table, parent_field),
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

        if many2one_fields and not all(
            isinstance(id_, int) and id_ > 0 for id_ in sub_ids
        ):
            raise TypeError(
                f"_unlink_process_batch: sub_ids must be positive ints, got {sub_ids!r}"
            )
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

_UNIQUE_DEFINITION = re.compile(r"^\s*unique\s*\(([^)]*)\)\s*$", re.IGNORECASE)


def _check_table_constraints(storage, model: BaseModel, rows: list[dict]) -> None:
    # what the table refuses on PostgreSQL: a NULL in a NOT NULL column and a
    # duplicate under a unique constraint (NULLs distinct, as SQL treats them)
    registry = model.env.registry
    not_null = [
        field.name
        for field in model._fields.values()
        if field.name != "id" and field in registry.not_null_fields
    ]
    for row in rows:
        for name in not_null:
            if name in row and row[name] is None:
                raise NotNullViolation(
                    f'null value in column "{name}" of relation '
                    f'"{model._table}" violates not-null constraint'
                )
    uniques = [
        (obj.get_full_name(model), tuple(c.strip() for c in match[1].split(",")))
        for obj in model._table_objects.values()
        if isinstance(obj, Constraint)
        and (match := _UNIQUE_DEFINITION.match(obj.get_definition(registry)))
    ]
    if not uniques:
        return
    existing = [
        stored
        for row_id in storage.get_table_ids(model._table)
        if (stored := storage.get_row(model._table, row_id)) is not None
    ]
    for conname, columns in uniques:
        seen: set[tuple] = set()
        for row in rows:
            key = tuple(row.get(column) for column in columns)
            if any(value is None for value in key):
                continue
            if key in seen or any(
                stored.get("id") != row.get("id")
                and tuple(stored.get(column) for column in columns) == key
                for stored in existing
            ):
                raise UniqueViolation(
                    f'duplicate key value violates unique constraint "{conname}"'
                )
            seen.add(key)


@functools.cache
def _python_timezone_names() -> frozenset[str]:
    return frozenset(zoneinfo.available_timezones())


class _MultiValued(list):
    __slots__ = ()


# date_part() for the number granularities, a double precision as PostgreSQL
# answers it; its dow runs Sunday 0 .. Saturday 6 and its week is the ISO week
_DATE_PART = {
    "year_number": lambda d: float(d.year),
    "quarter_number": lambda d: float((d.month - 1) // 3 + 1),
    "month_number": lambda d: float(d.month),
    "iso_week_number": lambda d: float(d.isocalendar()[1]),
    "day_of_year": lambda d: float(d.timetuple().tm_yday),
    "day_of_month": lambda d: float(d.day),
    "day_of_week": lambda d: float((d.weekday() + 1) % 7),
    "hour_number": lambda d: float(d.hour),
    "minute_number": lambda d: float(d.minute),
    "second_number": lambda d: float(d.second),
}


_TRUNCATE_GRANULARITY = {
    "year": lambda d: d.replace(month=1, day=1),
    "quarter": lambda d: d.replace(month=3 * ((d.month - 1) // 3) + 1, day=1),
    "month": lambda d: d.replace(day=1),
    "day": lambda d: d,
}


def _truncate(
    value: typing.Any,
    granularity: str,
    first_week_day: int = 0,
    tz: zoneinfo.ZoneInfo | None = None,
) -> typing.Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        if tz is not None:
            # timezone(tz, timezone('UTC', col)): the stored UTC instant as
            # the local wall-clock time, without an offset
            value = value.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        if granularity == "hour":
            return value.replace(minute=0, second=0, microsecond=0)
        if granularity in _DATE_PART:
            return _DATE_PART[granularity](value)
        value = value.replace(hour=0, minute=0, second=0, microsecond=0)
    if granularity in _DATE_PART:
        if granularity in ("hour_number", "minute_number", "second_number"):
            return 0.0
        return _DATE_PART[granularity](value)
    if granularity == "week":
        # the language's first week day, 0 Monday .. 6 Sunday, as the SQL
        # path shifts date_trunc('week') by it
        return value - _timedelta(days=(value.weekday() - first_week_day) % 7)
    try:
        return _TRUNCATE_GRANULARITY[granularity](value)
    except KeyError:
        raise NotImplementedError(
            f"InMemoryBackend.read_group_rows: granularity {granularity!r} is not "
            "supported in memory"
        ) from None


class _InMemoryReadGroup:
    """read_group over the dict storage: one row per group, raw values shaped as
    the SQL rows are (a many2one is its id, a date is truncated, text NULLIF'd)."""

    def __init__(self, model, domain, groupby, aggregates):
        self.model = model
        # the compiled query carries a GROUP BY meant for SQL; the in-memory search
        # answers the domain itself
        self.records = model.browse(model._search(domain).get_result_ids())
        self.groupby_specs = list(groupby)
        self.aggregate_specs = list(aggregates)
        self.groupby = [self._groupby_reader(spec) for spec in groupby]
        self.aggregates = [self._aggregate_reader(spec) for spec in aggregates]

    def _unsupported(self, what: str) -> typing.NoReturn:
        raise NotImplementedError(
            f"InMemoryBackend.read_group_rows on {self.model._name}: {what} is not "
            "supported in memory; use a DB-backed TransactionCase"
        )

    def _groupby_reader(self, spec: str, model: BaseModel | None = None):
        from ..parsing import parse_read_group_spec

        model = self.model if model is None else model
        fname, seq_fnames, granularity = parse_read_group_spec(spec)
        field = model._fields[fname]
        if field.is_properties:
            return self._property_reader(model, field, seq_fnames, granularity, spec)
        if field.is_many2many:
            return self._many2many_reader(model, field, spec)
        if seq_fnames:
            return self._many2one_path_reader(
                model, fname, field, seq_fnames, granularity, spec
            )

        first_week_day = 0
        tz = None
        if field.is_temporal and granularity == "week":
            from odoo.tools import get_lang

            first_week_day = int(get_lang(model.env).week_start) - 1
        if field.is_datetime and (tz_name := model.env.context.get("tz")):
            try:
                tz = zoneinfo.ZoneInfo(tz_name)
            except zoneinfo.ZoneInfoNotFoundError, ValueError:
                # the SQL path groups in UTC when the server does not know the zone
                tz = None

        def read(record):
            value = record[fname]
            if field.is_many2one:
                return value.id or None
            if field.is_temporal:
                return _truncate(
                    value or None, granularity or "day", first_week_day, tz
                )
            if field.is_boolean:
                return bool(value)
            if field.is_text:
                return value or None
            return value if value is not False else None

        return read

    def _many2many_reader(self, model, field, spec):
        # the relation rows whose comodel side the user may see under the
        # field's domain, as the LEFT JOIN's IN (subselect) keeps
        if not field.store:
            raise ValueError(f"Group by non-stored many2many field: {spec!r}")
        comodel = model.env[field.comodel_name].with_context(**field.context)
        allowed = set(
            comodel._search(
                field.get_comodel_domain(model),
                bypass_access=field.bypass_search_access,
            ).get_result_ids()
        )

        def read(record):
            ids = [id_ for id_ in record[field.name]._ids if id_ in allowed]
            return _MultiValued(ids or [None])

        return read

    def _property_reader(self, model, field, property_name, granularity, spec):
        # the SQL path groups by the property's raw json value shaped by its
        # definition type; a collection property and html stay refused
        if not property_name:
            self._unsupported(f"groupby {spec!r}")
        definition = model.get_property_definition(f"{field.name}.{property_name}")
        property_type = definition.get("type")
        if property_type in ("tags", "many2many"):
            self._unsupported(f"groupby {spec!r} ({property_type} property)")
        if property_type == "html":
            raise UserError(_("Grouping by HTML properties is not supported."))
        options = {option[0] for option in definition.get("selection") or ()}
        comodel = None
        if property_type == "many2one" and definition.get("comodel"):
            comodel = (
                model.env[definition["comodel"]].sudo().with_context(active_test=False)
            )
        first_week_day = 0
        if granularity == "week":
            from odoo.tools import get_lang

            first_week_day = int(get_lang(model.env).week_start) - 1

        def read(record):
            values = record[field.name]
            raw = (values._values or {}).get(property_name)
            if property_type == "selection":
                return raw if raw in options else None
            if property_type == "many2one":
                if not isinstance(raw, int) or isinstance(raw, bool) or comodel is None:
                    return None
                return raw if comodel.browse(raw).exists() else None
            if property_type in ("date", "datetime"):
                if not isinstance(raw, str):
                    return None
                parsed = (
                    date.fromisoformat(raw[:10])
                    if property_type == "date"
                    else datetime.fromisoformat(raw)
                )
                return _truncate(parsed, granularity or "day", first_week_day)
            if property_type == "boolean":
                return bool(raw)
            if raw is None or raw is False:
                return None
            return raw

        return read

    def _many2one_path_reader(self, model, fname, field, seq_fnames, granularity, spec):
        # the SQL path LEFT JOINs the comodel under the user's record rules
        # and groups by the rest of the spec on the joined row
        if not field.is_many2one:
            raise ValueError(
                f"Only many2one path is accepted for the {spec!r} groupby spec"
            )
        env = model.env
        comodel = env[field.comodel_name]
        rules = None
        if not env.su:
            sec_domain = env.registry.access_policy.record_domain(
                env, comodel._name, "read"
            )
            if not sec_domain.is_true():
                rules = sec_domain
        rest = f"{seq_fnames}:{granularity}" if granularity else seq_fnames
        read_rest = self._groupby_reader(rest, comodel)

        def read(record):
            corecord = record[fname]
            if not corecord:
                return None
            if rules is not None and not (
                corecord.sudo().with_context(active_test=False).filtered_domain(rules)
            ):
                return None
            return read_rest(corecord)

        return read

    def _aggregate_reader(self, spec: str):
        from ..parsing import parse_read_group_spec

        if spec == "__count":
            return len
        fname, _property, func = parse_read_group_spec(spec)
        field = self.model._fields[fname]
        if not field.column_type:
            raise ValueError(f"Cannot convert {field} to SQL because it is not stored")

        def raw(record):
            value = record[fname]
            if field.relational:
                return value.id or None if field.is_many2one else list(value.ids)
            return None if value is False and not field.is_boolean else value

        def values(records):
            return [raw(record) for record in records]

        def present(records):
            return [v for v in values(records) if v is not None]

        if field.column_type and field.column_type[0] == "numeric":
            # a numeric column holds the decimal the float spells, and SUM
            # is exact: 0.1 + 0.2 answers 0.3, not the double's 0.30000000000000004
            def total(present_values):
                return float(sum(Decimal(repr(v)) for v in present_values))

            def mean(present_values):
                exact = sum(Decimal(repr(v)) for v in present_values)
                return float(exact / len(present_values))
        else:
            total = sum

            def mean(present_values):
                return sum(present_values) / len(present_values)

        readers = {
            "count": lambda records: len(present(records)),
            "count_distinct": lambda records: len(set(present(records))),
            "sum": lambda records: (
                total(present(records)) if present(records) else None
            ),
            "avg": lambda records: mean(present(records)) if present(records) else None,
            "max": lambda records: max(present(records), default=None),
            "min": lambda records: min(present(records), default=None),
            "bool_and": lambda records: (
                all(present(records)) if present(records) else None
            ),
            "bool_or": lambda records: (
                any(present(records)) if present(records) else None
            ),
            "array_agg": lambda records: values(records) or None,
            "array_agg_distinct": lambda records: (
                list(dict.fromkeys(values(records))) or None
            ),
            "recordset": lambda records: (
                [
                    id_
                    for record in records
                    for id_ in (record.ids if fname == "id" else record[fname].ids)
                ]
                or None
            ),
        }
        if func not in readers:
            self._unsupported(f"aggregate {spec!r}")
        return readers[func]

    def rows(self, having, order, limit, offset) -> list[tuple]:
        groups: dict[tuple, list] = {}
        for record in self.records:
            # a many2many term yields one key per related row, as the
            # relation LEFT JOIN yields one row per pair (or one NULL row)
            for key in product(
                *(
                    value if isinstance(value, _MultiValued) else (value,)
                    for value in (read(record) for read in self.groupby)
                )
            ):
                groups.setdefault(key, []).append(record)
        if not self.groupby:
            groups = {(): list(self.records)}
        rows = [
            (
                *key,
                *(
                    aggregate(self.model.browse([r.id for r in members]))
                    for aggregate in self.aggregates
                ),
            )
            for key, members in groups.items()
        ]
        if having:
            keep = self._having_predicate(having)
            rows = [row for row in rows if keep(row) is True]
        self._sort(rows, order)
        if self.groupby:
            rows = rows[offset:]
            if limit is not None:
                rows = rows[:limit]
        return rows

    def _having_predicate(self, having: list):
        # the SQL path's polish-notation walk, with three-valued comparisons:
        # a NULL on either side answers None and the row is not kept
        import operator as pyoperator

        specs = [*self.groupby_specs, *self.aggregate_specs]
        compare = {
            "=": pyoperator.eq,
            "!=": pyoperator.ne,
            "<": pyoperator.lt,
            "<=": pyoperator.le,
            ">": pyoperator.gt,
            ">=": pyoperator.ge,
        }

        def condition(item):
            left, op, right = item
            if left not in specs:
                raise ValueError(
                    f"Invalid having clause {item!r}: {left!r} is neither an "
                    "aggregate nor a groupby of this read_group"
                )
            index = specs.index(left)
            if op in ("in", "not in"):
                values = (
                    tuple(right) if isinstance(right, (list, set, frozenset)) else right
                )
                if isinstance(values, tuple) and not values:
                    return lambda row: op == "not in"
                return lambda row: (
                    None
                    if row[index] is None
                    else (row[index] in values) == (op == "in")
                )
            if op not in compare:
                raise ValueError(
                    f"Invalid having clause {item!r}: supported comparators are "
                    "('in', 'not in', '<', '>', '<=', '>=', '=', '!=')"
                )
            test = compare[op]
            return lambda row: (
                None if row[index] is None or right is None else test(row[index], right)
            )

        def negate(pred):
            return lambda row: None if (v := pred(row)) is None else not v

        def both(a, b):
            def pred(row):
                x, y = a(row), b(row)
                if x is False or y is False:
                    return False
                return None if x is None or y is None else True

            return pred

        def either(a, b):
            def pred(row):
                x, y = a(row), b(row)
                if x is True or y is True:
                    return True
                return None if x is None or y is None else False

            return pred

        stack: list = []
        try:
            for item in reversed(having):
                if item == "!":
                    stack.append(negate(stack.pop()))
                elif item == "&":
                    stack.append(both(stack.pop(), stack.pop()))
                elif item == "|":
                    stack.append(either(stack.pop(), stack.pop()))
                elif isinstance(item, (list, tuple)) and len(item) == 3:
                    stack.append(condition(item))
                else:
                    raise ValueError(
                        f"Invalid having clause {item!r}: it should be a domain-like clause"
                    )
            while len(stack) > 1:
                stack.append(both(stack.pop(), stack.pop()))
            [predicate] = stack
        except IndexError:
            raise ValueError(f"Invalid having clause {having!r}") from None
        return predicate

    def _sort(self, rows: list[tuple], order: str | None) -> None:
        # one stable pass per term, last term first, so the first term wins;
        # PostgreSQL puts NULLs last ascending and first descending
        for index, rank, desc, nulls_first in reversed(self._order_terms(rows, order)):
            # a NULL sorts first when its flag is the largest in the direction
            # of the pass: None-is-True ascending puts it last, descending first
            null_is_true = nulls_first == desc

            def key(row, index=index, rank=rank, null_is_true=null_is_true):
                value = row[index]
                if value is not None and rank is not None:
                    value = rank(value)
                if isinstance(value, list):
                    self._unsupported("ordering by an array aggregate")
                return (value is None if null_is_true else value is not None, value)

            rows.sort(key=key, reverse=desc)

    def _day_of_week_rank(self, spec: str):
        from ..parsing import parse_read_group_spec

        if parse_read_group_spec(spec)[2] != "day_of_week":
            return None
        from odoo.tools import get_lang

        # mod(7 - week_start + dow, 7): the language's first day sorts first
        week_start = int(get_lang(self.model.env).week_start)
        return lambda dow: (7 - week_start + dow) % 7

    def _order_terms(self, rows: list[tuple], order: str | None) -> list[tuple]:
        from ..parsing import parse_read_group_spec, regex_order_part_read_group

        if not order:
            # SQL orders by the groupby terms as they are, ascending -- a
            # day_of_week term through the week-start shift, as its ORDER BY does
            return [
                (index, self._day_of_week_rank(spec), False, False)
                for index, spec in enumerate(self.groupby_specs)
            ]
        terms = []
        for order_part in order.split(","):
            match = regex_order_part_read_group.fullmatch(order_part)
            if not match:
                raise ValueError(f"Invalid order {order!r} for _read_group()")
            term = match["term"]
            desc = (match["direction"] or "asc").lower() == "desc"
            nulls = (match["nulls"] or "").lower()
            nulls_first = nulls == "nulls first" if nulls else desc
            rank = None
            if term in self.groupby_specs:
                index = self.groupby_specs.index(term)
                fname, seq_fnames, _granularity = parse_read_group_spec(term)
                rank = self._day_of_week_rank(term)
                field = self.model._fields[fname]
                # a path spec groups by the comodel's field, which sorts as is
                if field.is_many2one and not seq_fnames:
                    comodel = self.model.env[field.comodel_name]
                    if comodel._order != "id":
                        ids = [row[index] for row in rows if row[index] is not None]
                        ordered = comodel.browse(ids).sorted(key=comodel._order)
                        positions = {
                            id_: position for position, id_ in enumerate(ordered._ids)
                        }
                        rank = positions.__getitem__
            elif term in self.aggregate_specs:
                index = len(self.groupby) + self.aggregate_specs.index(term)
            else:
                self._unsupported(f"order {order_part.strip()!r}")
            terms.append((index, rank, desc, nulls_first))
        return terms


class _ForeignKeyPlan:
    __slots__ = ("backend", "m2m_rows", "nulls", "registry", "rows")

    def __init__(self, backend, registry) -> None:
        self.backend = backend
        self.registry = registry
        self.rows: dict[str, set[int]] = {}
        self.nulls: dict[str, list[tuple[int, dict]]] = {}
        self.m2m_rows: dict[str, set[int]] = {}

    def delete(self, model: BaseModel, ids: set[int]) -> None:
        storage = self.backend.storage
        seen = self.rows.setdefault(model._table, set())
        ids = ids.difference(seen)
        if not ids:
            return
        seen.update(ids)
        for field in model._fields.values():
            if field.is_many2many and field.store and field.relation and field.column1:
                self._drop_m2m_rows(field.relation, field.column1, ids)
        for field in self.registry.fields_by_comodel.get(model._name, ()):
            if not field.store:
                continue
            if field.is_many2many:
                if field.relation and field.column2:
                    self._drop_m2m_rows(field.relation, field.column2, ids)
                continue
            if not field.is_many2one or field.company_dependent:
                continue
            referrer = model.env[field.model_name]
            if referrer._abstract or not referrer._table:
                continue
            table = referrer._table
            hit = [
                row_id
                for row_id in storage.get_table_ids(table)
                if (row := storage.get_row(table, row_id))
                and row.get(field.name) in ids
                and row_id not in self.rows.get(table, ())
            ]
            if not hit:
                continue
            _debug.logic(
                "backend.memory.foreign_key",
                model=model._name,
                referrer=f"{field.model_name}.{field.name}",
                action=field.ondelete,
                rows=len(hit),
            )
            if field.ondelete == "cascade":
                self.delete(referrer, set(hit))
            elif field.ondelete == "restrict":
                raise ForeignKeyViolation(
                    f"update or delete on table {model._table!r} violates foreign "
                    f"key constraint on table {table!r}: key still referenced by "
                    f"{field.model_name}.{field.name}"
                )
            else:
                self.nulls.setdefault(table, []).extend(
                    (row_id, {field.name: None}) for row_id in hit
                )

    def _drop_m2m_rows(self, relation: str, column: str, ids: set[int]) -> None:
        self.m2m_rows.setdefault(relation, set()).update(
            row_id
            for row_id, row in self.backend._iter_m2m_rows(relation)
            if row.get(column) in ids
        )

    def apply(self, storage) -> None:
        for table, updates in self.nulls.items():
            storage.update_rows(table, updates)
        for relation, row_ids in self.m2m_rows.items():
            storage.remove_rows(relation, list(row_ids))
        for table, ids in self.rows.items():
            storage.remove_rows(table, list(ids))


class InMemoryBackend:
    supports_column_scan: bool = False

    supports_recursive_queries: bool = False

    __slots__ = ("columns", "sequences", "storage")

    def __init__(self, storage: DictBackend):
        self.storage = storage
        self.sequences: SequenceStore = InMemorySequenceStore(storage)
        self.columns: ColumnStore = InMemoryColumnStore(storage)

    def timezone_names(self, env) -> frozenset[str]:
        return _python_timezone_names()

    def create_rows(
        self,
        model: BaseModel,
        stored_list: list[dict[str, typing.Any]],
        columns: list[str],
        col_fields: list[Field],
    ) -> list[int]:
        row_dicts: list[dict[str, typing.Any]] = []
        new_ids: list[int] = []
        for stored in stored_list:
            new_id = self.storage.allocate_next_id(model._table)
            row_dict: dict[str, typing.Any] = {"id": new_id}
            for fname, field in zip(columns, col_fields, strict=True):
                if fname in stored:
                    row_dict[fname] = _unwrap_json(
                        field.convert_to_column_insert(stored[fname], model, stored)
                    )
            row_dicts.append(row_dict)
            new_ids.append(new_id)
        _check_table_constraints(self.storage, model, row_dicts)
        self.storage.put_rows(model._table, row_dicts)
        _debug.pipeline(
            "backend.memory.rows_created",
            model=model._name,
            rows=len(row_dicts),
            columns=len(columns),
        )
        return new_ids

    def update_rows(
        self, model: BaseModel, fnames: tuple[str, ...], rows: list[tuple]
    ) -> None:
        fields_map = model._fields
        updates = []
        for row in rows:
            id_ = row[0]
            values: dict[str, typing.Any] = {}
            for fname, value in zip(fnames, row[1:], strict=True):
                value = _unwrap_json(value)
                field = fields_map.get(fname)
                if (
                    value is not None
                    and field is not None
                    and (field.translate is True or field.company_dependent)
                    and isinstance(value, dict)
                ):
                    old_row = self.storage.get_row(model._table, id_)
                    old = old_row.get(fname) if old_row else None
                    if field.translate is True and not isinstance(old, dict):
                        old = {"en_US": next(iter(value.values()))}
                    if isinstance(old, dict):
                        value = {**old, **value}
                values[fname] = value
            updates.append((id_, values))
        _check_table_constraints(
            self.storage,
            model,
            [
                {**(self.storage.get_row(model._table, id_) or {}), **values}
                for id_, values in updates
            ],
        )
        self.storage.update_rows(model._table, updates)

    def fetch(
        self,
        model: BaseModel,
        query: Query,
        column_fields: typing.Iterable[Field],
        other_fields: typing.Iterable[Field],
    ) -> BaseModel:
        column_fields = list(column_fields)
        result_ids = query._ids
        if result_ids is None:
            result_ids = tuple(self.storage.get_table_ids(model._table))
            _debug.logic(
                "backend.memory.fetch_whole_table",
                model=model._name,
                rows=len(result_ids),
            )
        elif column_fields:
            existing = self.storage.get_existing_ids(model._table, list(result_ids))
            result_ids = tuple(id_ for id_ in result_ids if id_ in existing)

        if not result_ids:
            _debug.logic("backend.memory.fetch_nothing", model=model._name)
            return model.browse()

        fetched = model.browse(result_ids)
        self._load_column_cache(model, result_ids, column_fields, fetched)

        if fetched:
            for field in other_fields:
                field.read(fetched)
        return fetched

    def _load_column_cache(
        self,
        model: BaseModel,
        record_ids: typing.Sequence[int],
        column_fields: list[Field],
        records: BaseModel,
    ) -> None:
        if not column_fields:
            return
        env = model.env
        _fdc = env._field_depends_context
        field_caches: dict = {}
        for field in column_fields:
            if field not in _fdc:
                field_caches[field] = env.core.get_field_data(field)
            else:
                try:
                    field_caches[field] = field._get_cache(env)
                except (KeyError, AttributeError, TypeError) as e:
                    _logger.debug(
                        "DictBackend cache load skipped %s.%s: %s",
                        model._name,
                        field.name,
                        e,
                    )
                    field_caches[field] = env.core.get_field_data(field)
        prefetch_langs = bool(env.context.get("prefetch_langs"))
        for record_id in record_ids:
            row = self.storage.get_row(model._table, record_id)
            if row is not None:
                for field in column_fields:
                    if field.translate and prefetch_langs:
                        # the whole translation object, spread over the
                        # language caches the way the SQL read is inserted
                        field._insert_cache(
                            model.browse((record_id,)),
                            [_unwrap_json(row.get(field.name))],
                        )
                        continue
                    value = _get_column_read_value(field, row.get(field.name), env)
                    fc = field_caches[field]
                    fc.setdefault(
                        record_id,
                        fast_clone(value)
                        if field.type == "json"
                        else field.convert_to_cache(value, records),
                    )

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
        searched_fnames = flush_search_dependencies(model, domain, order)
        all_ids = self.storage.get_table_ids(model._table)
        all_records = model.browse(all_ids)

        fields = model._fields
        self._load_column_cache(
            model,
            all_ids,
            [
                field
                for fname in searched_fnames.get(model._name, ())
                if (field := fields[fname]).column_type
            ],
            all_records,
        )

        if not domain.is_true():
            matching = all_records.filtered_domain(domain)
        else:
            matching = all_records

        if check_access:
            sec_domain = model.env.registry.access_policy.record_domain(
                model.env, model._name, "read"
            )
            if not sec_domain.is_true():
                _debug.logic(
                    "backend.memory.rules_applied", model=model._name, uid=model.env.uid
                )
                allowed = (
                    matching.sudo()
                    .with_context(active_test=False)
                    .filtered_domain(sec_domain)
                )
                matching = model.browse(allowed._ids)

        if order:
            matching = matching.sorted(key=order)

        ids = matching._ids
        if offset:
            ids = ids[offset:]
        if limit is not None and limit is not False:
            ids = ids[:limit]

        _debug.pipeline(
            "backend.memory.search",
            model=model._name,
            scanned=len(all_ids),
            matched=len(matching),
            returned=len(ids),
            ordered=bool(order),
            check_access=check_access,
        )
        query = Query(model.env, model._table, model._table_sql)
        query._ids = tuple(ids)
        return query

    def as_query(self, model: BaseModel, ordered: bool = True) -> Query:
        query = Query(model.env, model._table, model._table_sql)
        query._ids = tuple(model._ids)
        return query

    def ancestors(
        self, model: BaseModel, parent_field: str, ids: typing.Collection[int]
    ) -> list[tuple[int, int | None]]:
        rows: dict[int, int | None] = {}
        frontier = list(ids)
        while frontier:
            next_frontier = []
            for id_ in frontier:
                if id_ in rows:
                    continue
                row = self.storage.get_row(model._table, id_)
                if row is None:
                    continue
                parent_id = row.get(parent_field) or None
                rows[id_] = parent_id
                if parent_id and parent_id not in rows:
                    next_frontier.append(parent_id)
            frontier = next_frontier
        return list(rows.items())

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
        from ..domain import Domain

        found: OrderedSet[int] = OrderedSet(
            model._search(domain & Domain("id", "in", list(root_ids))).get_result_ids()
        )
        frontier = list(found)
        while frontier:
            parents = model.browse(frontier)
            children = model.browse(
                model._search(
                    domain & step_domain & Domain(parent_field, "in", frontier)
                ).get_result_ids()
            )
            parent_values = {
                parent.id: tuple(parent[column] or "" for column in same_columns)
                for parent in parents
            }
            frontier = [
                typing.cast("int", child.id)
                for child in children
                if child.id not in found
                and tuple(child[column] or "" for column in same_columns)
                == parent_values[child[parent_field].id]
            ]
            found.update(frontier)
        return self.as_query(model.browse(list(found)), ordered=False)

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
        return _InMemoryReadGroup(model, domain, groupby, aggregates).rows(
            having, order, limit, offset
        )

    def get_existing_ids(self, model: BaseModel, ids: typing.Iterable[int]) -> set[int]:
        return set(self.storage.get_existing_ids(model._table, list(ids)))

    def lock_for_update(
        self, model: BaseModel, *, allow_referencing: bool = False
    ) -> None:
        ids = {id_ for id_ in model._ids if id_}
        if not ids:
            return
        if len(self.storage.get_existing_ids(model._table, list(ids))) != len(ids):
            raise LockError(model.env._("Cannot grab a lock on records"))

    def try_lock_for_update(
        self,
        model: BaseModel,
        *,
        allow_referencing: bool = False,
        limit: int | None = None,
    ) -> BaseModel:
        new_ids, real = partition(lambda i: isinstance(i, NewId), model._ids)
        lockable = self.storage.get_existing_ids(model._table, real) | set(new_ids)
        locked = [i for i in model._ids if i in lockable]
        if limit is not None:
            locked = locked[:limit]
        return model.browse(locked)

    def unlink_rows(self, model: BaseModel, sub_ids: tuple[int, ...]) -> None:
        # what the database's foreign keys do on DELETE -- cascade through,
        # null out or refuse the referencing many2one columns, and drop the
        # rows of every many2many relation table naming the ids -- planned
        # in full first, so a refusal deep in a cascade deletes nothing
        plan = _ForeignKeyPlan(self, model.env.registry)
        plan.delete(model, set(sub_ids))
        plan.apply(self.storage)

    def _iter_m2m_rows(self, relation: str):
        for row_id in self.storage.get_table_ids(relation):
            row = self.storage.get_row(relation, row_id)
            if row is not None:
                yield row_id, row

    def _read_m2m_pairs(
        self,
        model: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        ids: typing.Collection[int],
    ) -> list[tuple[int, int]]:
        wanted = set(ids)
        return [
            (row[column1], row[column2])
            for _row_id, row in self._iter_m2m_rows(relation)
            if row.get(column1) in wanted
        ]

    def set_parent_paths(
        self, model: BaseModel, ids: typing.Sequence[int]
    ) -> list[tuple[int, str]]:
        table, parent_column = model._table, model._parent_name
        updated: list[tuple[int, str]] = []
        for id_ in ids:
            row = self.storage.get_row(table, id_)
            if row is None:
                continue
            parent_row = (
                self.storage.get_row(table, row[parent_column])
                if row.get(parent_column)
                else None
            )
            prefix = (parent_row or {}).get("parent_path") or ""
            updated.append((id_, f"{prefix}{id_}/"))
        self.storage.update_rows(
            table, [(id_, {"parent_path": path}) for id_, path in updated]
        )
        return updated

    def records_with_parent_changed(
        self, model: BaseModel, parent_to_ids: dict[typing.Any, list[int]]
    ) -> list[int]:
        table, parent_column = model._table, model._parent_name
        changed: list[int] = []
        for parent_id, ids in parent_to_ids.items():
            for id_ in ids:
                row = self.storage.get_row(table, id_)
                if row is None:
                    continue
                stored = row.get(parent_column) or None
                if (stored != parent_id) if parent_id else (stored is not None):
                    changed.append(id_)
        return sorted(changed)

    def move_parent_paths(
        self, model: BaseModel, ids: typing.Sequence[int], prefix: str
    ) -> dict[int, str]:
        table = model._table
        moved: dict[int, str] = {}
        for node_id in ids:
            node = self.storage.get_row(table, node_id)
            node_path = (node or {}).get("parent_path")
            if not node_path:
                continue
            cut = len(node_path) - len(f"{node_id}/")
            for child_id in self.storage.get_table_ids(table):
                child = self.storage.get_row(table, child_id)
                child_path = (child or {}).get("parent_path") or ""
                if child_path.startswith(node_path):
                    moved[child_id] = f"{prefix}{child_path[cut:]}"
        self.storage.update_rows(
            table, [(id_, {"parent_path": path}) for id_, path in moved.items()]
        )
        return moved

    def read_m2m_groups(
        self,
        records: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        query: Query,
    ) -> dict[int, list[int]]:
        position = {id2: index for index, id2 in enumerate(query.get_result_ids())}
        group: dict[int, list[int]] = defaultdict(list)
        for id1, id2 in self._read_m2m_pairs(
            records, relation, column1, column2, records.ids
        ):
            if id2 in position:
                group[id1].append(id2)
        for ids2 in group.values():
            ids2.sort(key=position.__getitem__)
        return group

    def link_m2m_pairs(
        self,
        model: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        pairs: typing.Iterable[tuple[int, int]],
    ) -> None:
        existing: set[tuple] = {
            (row.get(column1), row.get(column2))
            for _row_id, row in self._iter_m2m_rows(relation)
        }
        to_insert = []
        for pair in pairs:
            key = tuple(pair)
            if key not in existing:
                existing.add(key)
                to_insert.append(key)
        if to_insert:
            self.storage.insert_rows(relation, [column1, column2], to_insert)

    def unlink_m2m_pairs(
        self,
        model: BaseModel,
        relation: str,
        column1: str,
        column2: str,
        pairs: typing.Iterable[tuple[int, int]],
    ) -> None:
        doomed = {tuple(pair) for pair in pairs}
        row_ids = [
            row_id
            for row_id, row in self._iter_m2m_rows(relation)
            if (row.get(column1), row.get(column2)) in doomed
        ]
        if row_ids:
            self.storage.remove_rows(relation, row_ids)
