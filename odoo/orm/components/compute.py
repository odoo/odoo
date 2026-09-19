from collections import defaultdict
from typing import TYPE_CHECKING, Any

from odoo.libs.debug_log import DebugLog

from ._protocols import FieldKey

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

_debug = DebugLog(__name__)


class _ScopeStack[F: FieldKey = FieldKey]:
    __slots__ = ("_maps",)

    def __init__(self) -> None:
        self._maps: list[dict[F, frozenset[Any]]] = []

    def get(
        self, key: F, default: frozenset[Any] | None = None
    ) -> frozenset[Any] | None:
        maps = self._maps
        i = len(maps)
        while i:
            i -= 1
            m = maps[i]
            if key in m:
                return m[key]
        return default

    def push_map(self, m: dict[F, frozenset[Any]] | None = None) -> None:
        self._maps.append(m if m is not None else {})

    def pop_map(self) -> dict[F, frozenset[Any]]:
        return self._maps.pop()

    def __setitem__(self, key: F, value: frozenset[Any]) -> None:
        self._maps[-1][key] = value

    def __len__(self) -> int:
        return len(self._maps)

    def has_any_protected(self) -> bool:
        return any(ids for m in self._maps for ids in m.values())


class ComputeEngine[F: FieldKey = FieldKey]:
    __slots__ = ("_pending", "_protected")

    def __init__(self, pending_factory: type | None = None) -> None:
        self._pending: defaultdict[F, set[Any]] = defaultdict(pending_factory or set)
        self._protected: _ScopeStack[F] = _ScopeStack()

    @property
    def pending(self) -> defaultdict[F, set[Any]]:
        return self._pending

    @staticmethod
    def _keys(field: F) -> tuple[F, ...]:
        # a value done or protected is a fact of the row, which every model
        # of a table-inheritance tree reads through its own field; a pending
        # one is scheduled on the model the trigger names, which owns the rows
        # it will compute
        return (field, *getattr(field, "tree_siblings", ()))

    def schedule(self, field: F, ids: Iterable[Any]) -> None:
        existing = self._pending.get(field)
        if existing is None:
            ids = list(ids)
            if not ids:
                return
            existing = self._pending[field]
        existing.update(ids)

    def is_pending_in_tree(self, field: F, record_id: Any) -> bool:
        return any(record_id in self._pending.get(key, ()) for key in self._keys(field))

    def mark_done(self, field: F, ids: Iterable[Any]) -> None:
        ids = list(ids)
        for key in self._keys(field):
            pending = self._pending.get(key)
            if pending is None:
                continue
            pending.difference_update(ids)
            if not pending:
                del self._pending[key]

    def is_pending(self, field: F, record_id: Any) -> bool:
        return record_id in self._pending.get(field, ())

    def get_pending_ids(self, field: F) -> set[Any] | tuple[()]:
        return self._pending.get(field, ())

    def get_pending_fields(self) -> Collection[F]:
        return tuple(self._pending)

    def has_pending(self) -> bool:
        return bool(self._pending)

    def has_pending_field(self, field: F) -> bool:
        return field in self._pending

    def get_pending_fields_with_real_ids(self) -> list[F]:
        return [field for field, ids in self._pending.items() if any(ids)]

    def discard_field(self, field: F) -> None:
        discarded = self._pending.pop(field, None)
        if _debug.lifecycle.enabled and discarded:
            _debug.lifecycle(
                "compute.pending_discarded",
                field=str(field),
                records=len(discarded),
            )

    def is_protected(self, field: F, record_id: Any) -> bool:
        return record_id in (self._protected.get(field) or ())

    def get_protected_ids(self, field: F) -> frozenset[Any]:
        return self._protected.get(field) or frozenset()

    def has_any_protected(self) -> bool:
        return self._protected.has_any_protected()

    def push_protection(self) -> None:
        self._protected.push_map()

    def pop_protection(self) -> dict[F, frozenset[Any]]:
        return self._protected.pop_map()

    def protect(self, field: F, ids: frozenset[Any]) -> None:
        for key in self._keys(field):
            existing = self._protected.get(key)
            self._protected[key] = existing.union(ids) if existing else ids

    def clear(self) -> None:
        if _debug.lifecycle.enabled and self._pending:
            _debug.lifecycle(
                "compute.pending_cleared",
                fields=len(self._pending),
                records=sum(len(ids) for ids in self._pending.values()),
            )
        self._pending.clear()

    def __repr__(self) -> str:
        n_fields = len(self._pending)
        n_entries = sum(len(ids) for ids in self._pending.values())
        n_scopes = len(self._protected)
        return f"<ComputeEngine pending={n_fields}f/{n_entries}e scopes={n_scopes}>"
