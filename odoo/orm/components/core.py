from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, cast

from odoo.libs.debug_log import DebugLog

from ._protocols import FieldKey
from .cache import _MISSING, FieldCache
from .compute import ComputeEngine
from .recompute import RecomputeScheduler

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping

_debug = DebugLog(__name__)


class OrmCore[F: FieldKey = FieldKey]:
    __slots__ = ("_cache", "_engine")

    def __init__(
        self,
        cache: FieldCache[F] | None = None,
        engine: ComputeEngine[F] | None = None,
    ) -> None:
        self._cache: FieldCache[F] = (
            cache if cache is not None else cast("FieldCache[F]", FieldCache())
        )
        self._engine: ComputeEngine[F] = (
            engine if engine is not None else cast("ComputeEngine[F]", ComputeEngine())
        )

    def get_value(self, field: F, record_id: Any, default: Any = _MISSING) -> Any:
        if default is _MISSING:
            return self._cache.get_value(field, record_id)
        return self._cache.get_value(field, record_id, default)

    def set_value(self, field: F, record_id: Any, value: Any) -> None:
        self._cache.set_value(field, record_id, value)

    def get_field_data(self, field: F) -> dict[Any, Any]:
        return self._cache.get_field_data(field)

    def get_field_data_or_none(self, field: F) -> dict[Any, Any] | None:
        return self._cache.get_field_data_or_none(field)

    def get_context_data(self, field: F, key: tuple) -> dict[Any, Any]:
        return self._cache.get_context_data(field, key)

    def get_context_data_or_none(self, field: F, key: tuple) -> dict[Any, Any] | None:
        return self._cache.get_context_data_or_none(field, key)

    def invalidate(
        self,
        field: F,
        ids: Iterable[Any] | None = None,
        *,
        keep_dirty: bool = False,
    ) -> None:
        self._cache.invalidate(field, ids, keep_dirty=keep_dirty)

    def has_any_cached(self, field: F) -> bool:
        return self._cache.has_any_cached(field)

    def has_any_context_cached(self, field: F) -> bool:
        return self._cache.has_any_context_cached(field)

    def get_cached_ids(self, field: F) -> Mapping[Any, Any]:
        return self._cache.get_cached_ids(field)

    def get_context_cached_ids(self, field: F) -> Mapping[Any, Any]:
        return self._cache.get_context_cached_ids(field)

    def iter_context_caches(self, field: F) -> Iterable[tuple[tuple, dict[Any, Any]]]:
        return self._cache.iter_context_caches(field)

    def iter_cached_fields(self) -> Iterator[F]:
        return self._cache.iter_cached_fields()

    def mark_dirty(self, field: F, ids: Iterable[Any]) -> None:
        self._cache.mark_dirty(field, ids)

    def get_dirty(self, field: F) -> set[Any] | None:
        return self._cache.get_dirty(field)

    def pop_dirty(self, field: F) -> set[Any] | None:
        return self._cache.pop_dirty(field)

    def pop_dirty_for_model(self, model_name: str) -> dict[F, set[Any]]:
        return self._cache.pop_dirty_for_model(model_name)

    def has_dirty_field(self, field: F) -> bool:
        return self._cache.has_dirty_field(field)

    def is_any_dirty(self) -> bool:
        return self._cache.is_any_dirty()

    def get_pending_write(
        self, fields: Iterable[F], ids: Iterable[Any] | None
    ) -> tuple[F, list[Any]] | None:
        if isinstance(ids, Iterator):
            ids = tuple(ids)
        for field in fields:
            dirty_ids = self._cache.get_dirty(field)
            if not dirty_ids:
                continue
            if ids is None:
                _debug.logic(
                    "core.pending_write_found",
                    field=str(field),
                    dirty=len(dirty_ids),
                    scoped=False,
                )
                return field, sorted(dirty_ids)
            overlap = sorted(dirty_ids.intersection(ids))
            if overlap:
                _debug.logic(
                    "core.pending_write_found",
                    field=str(field),
                    dirty=len(overlap),
                    scoped=True,
                )
                return field, overlap
        return None

    def add_patch(self, field: F, record_id: Any, new_id: Any) -> None:
        self._cache.add_patch(field, record_id, new_id)

    def get_patches(self, field: F) -> dict[Any, list[Any]] | None:
        return self._cache.get_patches(field)

    def iter_field_items(self) -> Iterator[tuple[F, dict[Any, Any]]]:
        return self._cache.iter_field_items()

    def schedule(self, field: F, ids: Iterable[Any]) -> None:
        self._engine.schedule(field, ids)

    def new_scheduler(self, *, inline: bool = False) -> RecomputeScheduler:
        return RecomputeScheduler(
            cast("ComputeEngine[FieldKey]", self._engine),
            marked=self._engine.pending,
            schedule_inline=inline,
            set_factory=cast("type | None", self._engine.pending.default_factory),
        )

    def mark_done(self, field: F, ids: Iterable[Any]) -> None:
        self._engine.mark_done(field, ids)

    def is_pending(self, field: F, record_id: Any) -> bool:
        return self._engine.is_pending(field, record_id)

    def is_pending_in_tree(self, field: F, record_id: Any) -> bool:
        return self._engine.is_pending_in_tree(field, record_id)

    def has_pending_field(self, field: F) -> bool:
        return self._engine.has_pending_field(field)

    def has_pending(self) -> bool:
        return self._engine.has_pending()

    def get_pending_ids(self, field: F) -> set[Any] | tuple[()]:
        return self._engine.get_pending_ids(field)

    def get_pending_fields(self) -> Collection[F]:
        return self._engine.get_pending_fields()

    def discard_field(self, field: F) -> None:
        self._engine.discard_field(field)

    def is_protected(self, field: F, record_id: Any) -> bool:
        return self._engine.is_protected(field, record_id)

    def get_protected_ids(self, field: F) -> frozenset[Any]:
        return self._engine.get_protected_ids(field)

    def has_any_protected(self) -> bool:
        return self._engine.has_any_protected()

    def push_protection(self) -> None:
        self._engine.push_protection()

    def pop_protection(self) -> dict[F, frozenset[Any]]:
        return self._engine.pop_protection()

    def protect(self, field: F, ids: frozenset[Any]) -> None:
        self._engine.protect(field, ids)

    def clear_cache(self) -> None:
        self._cache.clear()

    def __repr__(self) -> str:
        return f"<OrmCore {self._cache!r} {self._engine!r}>"
