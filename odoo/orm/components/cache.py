from collections import ChainMap, defaultdict
from collections.abc import Iterator, Sized
from typing import TYPE_CHECKING, Any

from odoo.libs.debug_log import DebugLog

from ._protocols import FieldKey

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

_MISSING = object()
_REITERABLE = (list, tuple, set, frozenset)

_debug = DebugLog(__name__)


class FieldCache[F: FieldKey = FieldKey]:
    __slots__ = ("_contexts", "_data", "_dirty", "_on_detach", "_patches")

    def __init__(
        self,
        dirty_factory: type | None = None,
        on_detach: Callable[[], None] | None = None,
    ) -> None:
        self._data: defaultdict[F, dict[Any, Any]] = defaultdict(dict)
        self._contexts: defaultdict[F, dict[tuple, dict[Any, Any]]] = defaultdict(dict)
        self._dirty: defaultdict[F, set[Any]] = defaultdict(dirty_factory or set)
        self._patches: defaultdict[F, defaultdict[Any, list[Any]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._on_detach = on_detach

    def get_field_data(self, field: F) -> dict[Any, Any]:
        return self._data[field]

    def get_field_data_or_none(self, field: F) -> dict[Any, Any] | None:
        return self._data.get(field)

    def get_context_data(self, field: F, key: tuple) -> dict[Any, Any]:
        contexts = self._contexts[field]
        sub_cache = contexts.get(key)
        if sub_cache is None:
            sub_cache = contexts[key] = {}
        return sub_cache

    def get_context_data_or_none(self, field: F, key: tuple) -> dict[Any, Any] | None:
        contexts = self._contexts.get(field)
        return None if contexts is None else contexts.get(key)

    def iter_context_caches(self, field: F) -> Iterable[tuple[tuple, dict[Any, Any]]]:
        contexts = self._contexts.get(field)
        return () if contexts is None else contexts.items()

    def set_value(self, field: F, record_id: Any, value: Any) -> None:
        self._data[field][record_id] = value

    def get_value(self, field: F, record_id: Any, default: Any = _MISSING) -> Any:
        field_cache = self._data.get(field)
        if field_cache is not None:
            try:
                return field_cache[record_id]
            except KeyError:
                pass
        if default is _MISSING:
            raise KeyError(record_id)
        return default

    def has_value(self, field: F, record_id: Any) -> bool:
        field_cache = self._data.get(field)
        return field_cache is not None and record_id in field_cache

    def mark_dirty(self, field: F, ids: Iterable[Any]) -> None:
        existing = self._dirty.get(field)
        if existing is None:
            ids = list(ids)
            if not ids:
                return
            existing = self._dirty[field]
        existing.update(ids)

    def get_dirty(self, field: F) -> set[Any] | None:
        return self._dirty.get(field)

    def pop_dirty(self, field: F) -> set[Any] | None:
        return self._dirty.pop(field, None)

    def pop_dirty_for_model(self, model_name: str) -> dict[F, set[Any]]:
        result: dict[Any, set] = {}
        for field in list(self._dirty):
            if getattr(field, "model_name", None) == model_name:
                result[field] = self._dirty.pop(field)
        if _debug.pipeline.enabled and result:
            _debug.pipeline(
                "cache.dirty_popped_for_model",
                model=model_name,
                fields=len(result),
                records=sum(len(ids) for ids in result.values()),
            )
        return result

    def is_any_dirty(self) -> bool:
        return bool(self._dirty)

    def has_dirty_field(self, field: F) -> bool:
        return bool(self._dirty.get(field))

    def iter_dirty_fields(self) -> Iterator[F]:
        return iter(self._dirty)

    def get_dirty_entry_count(self) -> int:
        return sum(len(ids) for ids in self._dirty.values())

    def add_patch(self, field: F, record_id: Any, new_id: Any) -> None:
        self._patches[field][record_id].append(new_id)

    def get_patches(self, field: F) -> dict[Any, list[Any]] | None:
        return self._patches.get(field)

    def invalidate(
        self,
        field: F,
        ids: Iterable[Any] | None = None,
        *,
        keep_dirty: bool = False,
    ) -> None:
        field_cache = self._data.get(field)
        contexts = self._contexts.get(field)
        if not field_cache and not contexts:
            return
        dirty = (self._dirty.get(field) or None) if keep_dirty else None
        if ids is not None:
            if dirty is not None:
                ids = [id_ for id_ in ids if id_ not in dirty]
            elif contexts and type(ids) not in _REITERABLE:
                ids = tuple(ids)
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "cache.field_invalidated",
                field=str(field),
                records=len(ids) if isinstance(ids, Sized) else None,
                whole=ids is None,
                contexts=len(contexts) if contexts else 0,
                kept_dirty=len(dirty) if dirty else 0,
            )
        if field_cache:
            _evict(field_cache, ids, dirty)
        if contexts:
            for sub_cache in contexts.values():
                _evict(sub_cache, ids, dirty)

    def has_any_cached(self, field: F) -> bool:
        return bool(self._data.get(field))

    def has_any_context_cached(self, field: F) -> bool:
        contexts = self._contexts.get(field)
        return contexts is not None and any(contexts.values())

    def get_cached_ids(self, field: F) -> Mapping[Any, Any]:
        return self._data.get(field) or {}

    def get_context_cached_ids(self, field: F) -> Mapping[Any, Any]:
        contexts = self._contexts.get(field)
        return ChainMap(*contexts.values()) if contexts else {}

    def iter_cached_fields(self) -> Iterator[F]:
        return iter(self._data.keys() | self._contexts.keys())

    def invalidate_all(self, *, keep: Callable[[Any], bool] | None = None) -> None:
        if self._on_detach is not None:
            self._on_detach()
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "field_cache.invalidate_all",
                fields=len(self._data.keys() | self._contexts.keys()),
                entries=sum(len(values) for values in self._data.values()),
                dirty_fields=sum(1 for ids in self._dirty.values() if ids),
                dirty_entries=self.get_dirty_entry_count(),
            )
        if not self._dirty and keep is None:
            self._data.clear()
            self._contexts.clear()
            return
        for field in list(self._data):
            dirty_ids = self._dirty.get(field)
            if (dirty_ids or keep) and _retain(self._data[field], dirty_ids, keep):
                continue
            del self._data[field]
        for field in list(self._contexts):
            dirty_ids = self._dirty.get(field)
            contexts = self._contexts[field]
            if dirty_ids or keep:
                for key in [
                    k
                    for k, sub in contexts.items()
                    if not _retain(sub, dirty_ids, keep)
                ]:
                    del contexts[key]
            if not (dirty_ids or keep) or not contexts:
                del self._contexts[field]

    def clear(self) -> None:
        if self._on_detach is not None:
            self._on_detach()
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "field_cache.clear",
                fields=len(self._data.keys() | self._contexts.keys()),
                dirty_entries=self.get_dirty_entry_count(),
                patched_fields=len(self._patches),
            )
        self._data.clear()
        self._contexts.clear()
        self._dirty.clear()
        self._patches.clear()

    def iter_field_items(self) -> Iterator[tuple[F, dict[Any, Any]]]:
        return iter(self._data.items())

    def __repr__(self) -> str:
        n_fields = len(self._data.keys() | self._contexts.keys())
        n_dirty = sum(len(ids) for ids in self._dirty.values())
        return f"<FieldCache fields={n_fields} dirty_entries={n_dirty}>"


def _evict(
    values: dict[Any, Any], ids: Iterable[Any] | None, dirty: set[Any] | None
) -> None:
    if ids is None:
        if dirty is None:
            values.clear()
        else:
            _retain(values, dirty)
        return
    for id_ in ids:
        values.pop(id_, None)


def _retain(
    values: dict[Any, Any],
    ids: set[Any] | None,
    keep: Callable[[Any], bool] | None = None,
) -> bool:
    kept = ids or ()
    for id_ in [k for k in values if k not in kept and (keep is None or not keep(k))]:
        del values[id_]
    return bool(values)
