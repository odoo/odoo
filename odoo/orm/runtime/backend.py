from __future__ import annotations

import json
import logging
import os
import typing
from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime
from datetime import timedelta as _timedelta
from decimal import Decimal
from itertools import batched

from psycopg.errors import (
    InvalidTextRepresentation,
    NumericValueOutOfRange,
    UntranslatableCharacter,
)
from psycopg.types.json import Json, Jsonb, JsonDumper

from odoo.exceptions import LockError, UserError
from odoo.libs.accel import fast_clone
from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import _OrmProfile
from odoo.tools import SQL, OrderedSet, Query, partition
from odoo.tools.translate import _

from ..components.storage import NamedSequence
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

COPY_THRESHOLD = int(os.environ.get("ODOO_COPY_THRESHOLD", "10"))
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
            model._table, [(id_, {column: value}) for id_, value in rows]
        )


@typing.runtime_checkable
class StorageBackend(typing.Protocol):
    sequences: SequenceStore
    columns: ColumnStore

    supports_record_rules: bool

    supports_column_scan: bool

    supports_recursive_queries: bool

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
        query.order = model._order_to_sql(order, query) or SQL.identifier(
            model._table, "id"
        )

    if limit is not None and limit is not False:
        query.limit = 1 if limit is True else limit
    if offset is not None and offset is not False:
        query.offset = 1 if offset is True else offset

    prof.stop("query")
    prof.report(_orm_read, "_search %s", model._name)
    return query


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


class PostgresBackend:
    sequences: SequenceStore = PostgresSequenceStore()
    columns: ColumnStore = PostgresColumnStore()

    supports_record_rules: bool = True

    supports_column_scan: bool = True

    supports_recursive_queries: bool = True

    __slots__ = ()

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
                sql = model._field_to_sql(model._table, field.name, query)
                if field.is_binary and (
                    context.get("bin_size") or context.get("bin_size_" + field.name)
                ):
                    sql = SQL("pg_size_pretty(length(%s)::bigint)", sql)
                elif not field.translate:
                    to_flush = (f for f in sql.to_flush if f != field)
                    sql = SQL("%s", sql, to_flush=to_flush)
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


_TRUNCATE_GRANULARITY = {
    "year": lambda d: d.replace(month=1, day=1),
    "quarter": lambda d: d.replace(month=3 * ((d.month - 1) // 3) + 1, day=1),
    "month": lambda d: d.replace(day=1),
    "week": lambda d: d - _timedelta(days=d.weekday()),
    "day": lambda d: d,
}


def _truncate(value: typing.Any, granularity: str) -> typing.Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.replace(hour=0, minute=0, second=0, microsecond=0)
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
        self.groupby = [self._groupby_reader(spec) for spec in groupby]
        self.aggregates = [self._aggregate_reader(spec) for spec in aggregates]

    def _unsupported(self, what: str) -> typing.NoReturn:
        raise NotImplementedError(
            f"InMemoryBackend.read_group_rows on {self.model._name}: {what} is not "
            "supported in memory; use a DB-backed TransactionCase"
        )

    def _groupby_reader(self, spec: str):
        from ..parsing import parse_read_group_spec

        fname, seq_fnames, granularity = parse_read_group_spec(spec)
        field = self.model._fields[fname]
        if seq_fnames or field.is_properties or field.is_many2many:
            self._unsupported(f"groupby {spec!r}")

        def read(record):
            value = record[fname]
            if field.is_many2one:
                return value.id or None
            if field.is_temporal:
                return _truncate(value or None, granularity or "day")
            if field.is_boolean:
                return bool(value)
            if field.is_text:
                return value or None
            return value if value is not False else None

        return read

    def _aggregate_reader(self, spec: str):
        from ..parsing import parse_read_group_spec

        if spec == "__count":
            return len
        fname, _property, func = parse_read_group_spec(spec)
        field = self.model._fields[fname]

        def raw(record):
            value = record[fname]
            if field.relational:
                return value.id or None if field.is_many2one else list(value.ids)
            return None if value is False and not field.is_boolean else value

        def values(records):
            return [raw(record) for record in records]

        def present(records):
            return [v for v in values(records) if v is not None]

        readers = {
            "count": lambda records: len(present(records)),
            "count_distinct": lambda records: len(set(present(records))),
            "sum": lambda records: sum(present(records)) if present(records) else None,
            "avg": lambda records: (
                sum(present(records)) / len(present(records))
                if present(records)
                else None
            ),
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
        if having:
            self._unsupported("having")
        groups: dict[tuple, list] = {}
        for record in self.records:
            key = tuple(read(record) for read in self.groupby)
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
        rows.sort(key=lambda row: self._sort_key(row, order))
        if self.groupby:
            rows = rows[offset:]
            if limit is not None:
                rows = rows[:limit]
        return rows

    def _sort_key(self, row: tuple, order: str | None):
        if order:
            self._unsupported(f"order {order!r}")
        # SQL orders by the groupby terms ascending, nulls last
        return tuple((value is None, value) for value in row[: len(self.groupby)])


class InMemoryBackend:
    supports_record_rules: bool = False

    supports_column_scan: bool = False

    supports_recursive_queries: bool = False

    __slots__ = ("columns", "sequences", "storage")

    def __init__(self, storage: DictBackend):
        self.storage = storage
        self.sequences: SequenceStore = InMemorySequenceStore(storage)
        self.columns: ColumnStore = InMemoryColumnStore(storage)

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
        for record_id in record_ids:
            row = self.storage.get_row(model._table, record_id)
            if row is not None:
                for field in column_fields:
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
        self.storage.remove_rows(model._table, list(sub_ids))

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
