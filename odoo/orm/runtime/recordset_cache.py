import contextlib
import logging
import typing
from pprint import pformat

from odoo.exceptions import CacheMiss
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import pg_size_pretty
from odoo.tools import SQL, OrderedSet, Query
from odoo.tools.misc import PENDING, SENTINEL

if typing.TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Iterator, MutableMapping

    from .._typing import BaseModel, Field
    from ..primitives import IdType
    from .transaction import Transaction

_logger = logging.getLogger("odoo.api")
_debug = DebugLog(__name__)


class CacheInvalidError(AssertionError):
    pass


class Cache:
    """The recordset-level view of the field cache.

    It is not a second cache: the storage is the transaction's `OrmCore`, and
    every method here is a recordset-shaped question answered against it --
    `get_values(records, field)` where the core stores `field -> {id: value}`.
    The two levels exist because the core is Odoo-agnostic and keyed by ids,
    while this one speaks recordsets, contexts and `Field` objects.
    """

    __slots__ = ("transaction",)

    def __init__(self, transaction: Transaction):
        self.transaction = transaction

    def __repr__(self) -> str:
        data: dict[Field, dict] = {}
        core = self.transaction.core
        for field in sorted(core.iter_cached_fields(), key=str):
            dirty_ids = core.get_dirty(field) or ()

            def entries(values, dirty_ids=dirty_ids, field=field):
                return {
                    Starred(id_) if id_ in dirty_ids else id_: (
                        "<binary>" if field.is_binary else val
                    )
                    for id_, val in values.items()
                }

            if field in self.transaction.registry.field_depends_context:
                data[field] = {
                    key: entries(key_cache)
                    for key, key_cache in core.iter_context_caches(field)
                }
            else:
                data[field] = entries(core.get_field_data_or_none(field) or {})
        return repr(data)

    def _get_field_cache(
        self, model: BaseModel, field: Field
    ) -> MutableMapping[IdType, typing.Any]:
        return field._get_cache(model.env)

    def contains(self, record: BaseModel, field: Field) -> bool:
        return record.id in self._get_field_cache(record, field)

    def get(self, record: BaseModel, field: Field, default=SENTINEL):
        try:
            field_cache = self._get_field_cache(record, field)
            return field_cache[record._ids[0]]
        except KeyError, IndexError:
            if default is SENTINEL:
                raise CacheMiss(record, field) from None
            return default

    def set(
        self,
        record: BaseModel,
        field: Field,
        value: typing.Any,
        dirty: bool = False,
    ) -> None:
        field._update_cache(record, value, dirty=dirty)

    def update(
        self,
        records: BaseModel,
        field: Field,
        values: Iterable,
        dirty: bool = False,
    ) -> None:
        if dirty:
            for record, value in zip(records, values, strict=False):
                field._update_cache(record, value, dirty=True)
            return
        field._update_cache_items(records.env, zip(records._ids, values, strict=False))

    def update_raw(
        self,
        records: BaseModel,
        field: Field,
        values: Iterable,
        dirty: bool = False,
    ) -> None:
        if not dirty and (
            found := self.transaction.core.get_pending_write((field,), records._ids)
        ):
            _field, overlap = found
            _logger.warning(
                "Cache.update_raw overwrote %s on records %s, which held a "
                "pending write that is now lost. Flush those records first, or "
                "pass dirty=True to declare that this value supersedes the "
                "pending one.",
                field,
                overlap[:10],
            )
        field_cache = self._get_field_cache(records, field)
        field_cache.update(zip(records._ids, values, strict=False))
        if field.is_column and dirty:
            self.transaction.core.mark_dirty(
                field, [id_ for id_ in records._ids if id_]
            )

    def remove(self, record: BaseModel, field: Field) -> None:
        if record.id in (self.transaction.core.get_dirty(field) or ()):
            raise ValueError(
                f"Cannot remove cache entry for dirty field "
                f"{field!r} on record {record}: pending write would be lost"
            )
        try:
            field_cache = self._get_field_cache(record, field)
            del field_cache[record._ids[0]]
        except KeyError:
            pass

    def get_values(self, records: BaseModel, field: Field) -> Iterator[typing.Any]:
        field_cache = self._get_field_cache(records, field)
        for record_id in records._ids:
            with contextlib.suppress(KeyError):
                yield field_cache[record_id]

    def get_fields(self, record: BaseModel) -> Iterator[Field]:
        for name, field in record._fields.items():
            if name != "id" and record.id in self._get_field_cache(record, field):
                yield field

    def get_records(
        self, model: BaseModel, field: Field, all_contexts: bool = False
    ) -> BaseModel:
        ids: Iterable
        if all_contexts and field in model.pool.field_depends_context:
            ids = OrderedSet(self.transaction.core.get_context_cached_ids(field))
        else:
            ids = self._get_field_cache(model, field)
        return model.browse(ids)

    def get_missing_ids(self, records: BaseModel, field: Field) -> Iterator[IdType]:
        return field._iter_cache_missing_ids(records)

    def invalidate(
        self,
        spec: Collection[tuple[Field, Collection[IdType] | None]] | None = None,
    ) -> None:
        if spec is None:
            self.transaction.invalidate_field_data()
            return
        spec = list(spec)
        env = next(iter(self.transaction.envs), None)
        if env is None:
            _logger.debug(
                "Cache.invalidate: skipped %d entries — no environments left "
                "in transaction (all GC'd)",
                len(spec),
            )
            return
        core = self.transaction.core
        for field, ids in spec:
            if (found := core.get_pending_write((field,), ids)) is not None:
                _field, overlap = found
                raise ValueError(
                    f"Cache.invalidate: refusing to drop {field} on records "
                    f"{overlap[:10]}; they hold a pending write that would be "
                    f"silently lost.  Flush those records first."
                )
        _debug.lifecycle(
            "recordset_cache.invalidate",
            fields=len(spec),
            whole_fields=sum(1 for _field, ids in spec if ids is None),
        )
        for field, ids in spec:
            field._invalidate_cache(env, ids)

    def clear(self):
        _debug.lifecycle("recordset_cache.clear")
        self.transaction.core.clear_cache()

    def check(self, env, *, raise_on_invalid: bool = True) -> list[tuple]:
        depends_context = env.registry.field_depends_context
        core = self.transaction.core
        invalids = []

        def process(model: BaseModel, field: Field, field_cache):
            dirty_ids = core.get_dirty(field) or ()
            _pending = PENDING
            ids = [
                id_
                for id_ in field_cache
                if id_ and id_ not in dirty_ids and field_cache[id_] is not _pending
            ]
            if not ids:
                return

            bin_size = field.is_binary and (
                model.env.context.get("bin_size")
                or model.env.context.get("bin_size_" + field.name)
            )
            if model._table_query is None:
                # the stored column as either backend holds it
                rows = env.backend.columns.read(model, field.name, ids).items()
                if bin_size:
                    rows = [
                        (id_, None if value is None else pg_size_pretty(len(value)))
                        for id_, value in rows
                    ]
            else:
                query = Query(env, model._table, model._table_sql)
                sql_id = SQL.identifier(model._table, "id")
                sql_field = model._field_to_sql(model._table, field.name, query)
                if bin_size:
                    sql_field = SQL("pg_size_pretty(length(%s)::bigint)", sql_field)
                query.add_where(SQL("%s = ANY(%s)", sql_id, list(ids)))
                env.cr.execute(query.select(sql_id, sql_field))
                rows = env.cr.fetchall()

            for id_, value in rows:
                cached = field_cache[id_]
                if value == cached or (not value and not cached):
                    continue
                invalids.append(
                    (
                        model.browse((id_,)),
                        field,
                        {"cached": cached, "fetched": value},
                    )
                )

        checked = 0  # debuglog
        with _debug.perf("recordset_cache.check", cr=env.cr) as span:
            for field in list(core.iter_cached_fields()):
                if (
                    not field.store
                    or not field.column_type
                    or field.translate
                    or field.company_dependent
                ):
                    continue

                checked += 1  # debuglog
                model = env[field.model_name]
                if field in depends_context:
                    for context_keys, inner_cache in core.iter_context_caches(field):
                        context = dict(
                            zip(depends_context[field], context_keys, strict=True)
                        )
                        if "company" in context:
                            context["allowed_company_ids"] = [context.pop("company")]
                        process(model.with_context(context), field, inner_cache)
                elif (field_cache := core.get_field_data_or_none(field)) is not None:
                    process(model, field, field_cache)
            span.set(fields=checked, invalid=len(invalids))

        if invalids:
            _logger.warning("Invalid cache: %s", pformat(invalids))
            if raise_on_invalid:
                raise CacheInvalidError(
                    f"Cache does not match the database:\n{pformat(invalids)}"
                )
        return invalids


class Starred:
    __slots__ = ["value"]

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"{self.value!r}*"
