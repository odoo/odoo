import logging
import typing
from collections.abc import Collection, Mapping, Sequence

from odoo.libs.debug_log import DebugLog

from ... import decorators as api
from ...helpers import get_fields_by_name
from ._model_stubs import _ModelStubs

_orm_cache = logging.getLogger("odoo.orm.cache")
_debug = DebugLog(__name__)

if typing.TYPE_CHECKING:
    from ..._typing import IdType
    from ...fields.base import Field


class RecordCache(Mapping):
    __slots__ = ["_record"]

    def __init__(self, record) -> None:
        if len(record) != 1:
            raise ValueError(f"Unexpected RecordCache({record})")
        self._record = record

    def _peek(self, field) -> Mapping | None:
        return field._peek_cache(self._record.env)

    def __contains__(self, name: object) -> bool:
        record = self._record
        field = record._fields.get(name)
        if field is None:
            return False
        cache = self._peek(field)
        return cache is not None and record.id in cache

    def __getitem__(self, name: str) -> object:
        record = self._record
        field = record._fields[name]
        cache = self._peek(field)
        if cache is None:
            raise KeyError(record.id)
        return cache[record.id]

    def __iter__(self) -> typing.Iterator[str]:
        record = self._record
        id_ = record.id
        for name, field in record._fields.items():
            cache = self._peek(field)
            if cache is not None and id_ in cache:
                yield name

    def __len__(self) -> int:
        return sum(1 for name in self)


class CacheMixin(_ModelStubs):
    __slots__ = ()

    @property
    def _cache(self) -> RecordCache:
        return RecordCache(self)

    @api.private
    def invalidate_model(
        self, fnames: Collection[str] | None = None, flush: bool = True
    ) -> None:
        if flush:
            self.flush_model(fnames)
        self._invalidate_cache(fnames, flush=flush)
        _debug.lifecycle(
            "cache.invalidate_model",
            model=self._name,
            fields=None if fnames is None else len(fnames),
            flush=flush,
        )
        if _orm_cache.isEnabledFor(logging.DEBUG):
            _orm_cache.debug("invalidate_model %s: fnames=%s", self._name, fnames)

    @api.private
    def invalidate_recordset(
        self, fnames: Collection[str] | None = None, flush: bool = True
    ) -> None:
        if flush:
            self.flush_recordset(fnames)
        self._invalidate_cache(fnames, self._ids, flush=flush)
        _debug.lifecycle(
            "cache.invalidate_recordset",
            model=self._name,
            records=len(self),
            fields=None if fnames is None else len(fnames),
            flush=flush,
        )
        if _orm_cache.isEnabledFor(logging.DEBUG):
            _orm_cache.debug(
                "invalidate_recordset %s: %d records, fnames=%s",
                self._name,
                len(self),
                fnames,
            )

    def _invalidate_cache(
        self,
        fnames: Collection[str] | None = None,
        ids: Sequence[IdType] | None = None,
        flush: bool = True,
    ) -> None:
        if ids is not None and not ids:
            return

        fields: Collection[Field]
        if fnames is None:
            fields = self._fields.values()
        else:
            fields = get_fields_by_name(self, fnames)

        env = self.env
        if not flush:
            self._check_no_pending_write(fields, ids)

        field_inverses = self.pool.field_inverses
        inverses_invalidated = 0  # debuglog
        for field in fields:
            field._invalidate_cache(env, ids)
            if inverses := field_inverses.get(field):
                for invf in inverses:
                    inverses_invalidated += 1  # debuglog
                    if flush:
                        env[invf.model_name].flush_model([invf.name])
                    invf._invalidate_cache(env, keep_dirty=True)
        if _debug.logic.enabled and inverses_invalidated:
            _debug.logic(
                "cache.inverses_invalidated",
                model=self._name,
                fields=len(fields),
                inverses=inverses_invalidated,
                flushed=flush,
            )

    def _invalidate_table_inheritance_siblings(self, fnames: Collection[str]) -> None:
        env = self.env
        for model_name in env._table_inheritance_tree(self._name):
            sibling = env[model_name]
            shared = [fname for fname in fnames if fname in sibling._fields]
            if shared:
                sibling.browse(self._ids).invalidate_recordset(shared)

    def _evict_x2many_scopes_reading_through(self, fnames: Collection[str]) -> None:
        env = self.env
        for field in env.registry.fields_by_comodel.get(self._name, ()):
            if field.is_x2many and field.store:
                field._evict_user_scopes_reading_through(env, fnames)

    def _check_no_pending_write(
        self, fields: Collection[Field], ids: Sequence[IdType] | None
    ) -> None:
        found = self.env.core.get_pending_write(fields, ids)
        if found is None:
            return
        field, overlap = found
        _debug.logic(
            "cache.invalidate_refused_pending_write",
            model=self._name,
            field=field.name,
            pending=len(overlap),
        )
        raise ValueError(
            f"Refusing to invalidate {field} on records {overlap[:10]} with "
            f"flush=False: they hold a pending write that would be silently "
            f"lost.  Flush first (drop flush=False), restrict the records, "
            f"or discard the write explicitly."
        )
