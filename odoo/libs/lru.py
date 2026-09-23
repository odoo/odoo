import threading
import typing
from collections import OrderedDict
from collections.abc import (
    Callable,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    MutableMapping,
    ValuesView,
)

from .iteration.sentinel import SENTINEL

__all__ = ["LRU"]


class LRU[K, V](MutableMapping[K, V]):
    __slots__ = ("_count", "_generation", "_lock", "_map", "_on_evict")

    def __init__(
        self,
        count: int,
        pairs: Iterable[tuple[K, V]] = (),
        *,
        on_evict: Callable[[K, V], None] | None = None,
    ) -> None:
        if count <= 0:
            raise ValueError(f"LRU count must be positive, got {count!r}")
        self._count = count
        self._generation = 0
        self._lock = threading.RLock()
        self._map: OrderedDict[K, V] = OrderedDict()
        self._on_evict = on_evict

        for key, value in pairs:
            self[key] = value

    @property
    def count(self) -> int:
        return self._count

    @count.setter
    def count(self, count: int) -> None:
        if count <= 0:
            raise ValueError(f"LRU count must be positive, got {count!r}")
        with self._lock:
            self._count = count
            self._trim()

    def _trim(self) -> None:
        map_ = self._map
        count = self._count
        on_evict = self._on_evict
        while len(map_) > count:
            key, value = map_.popitem(last=False)
            if on_evict is not None:
                on_evict(key, value)

    def _store_locked(self, key: K, value: V) -> None:
        map_ = self._map
        existing = key in map_
        map_[key] = value
        if existing:
            map_.move_to_end(key)
        else:
            self._trim()

    def __contains__(self, key: object) -> bool:
        return key in self._map

    def __getitem__(self, key: K) -> V:
        value = self._map[key]
        try:  # noqa: SIM105  contextlib.suppress costs a context manager per read
            self._map.move_to_end(key)
        except KeyError:
            pass
        return value

    def __setitem__(self, key: K, value: V) -> None:
        with self._lock:
            self._store_locked(key, value)

    def __delitem__(self, key: K) -> None:
        self.pop(key)

    def __len__(self) -> int:
        return len(self._map)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"(count={self._count}, size={len(self._map)}, gen={self._generation})"
        )

    def __iter__(self) -> Iterator[K]:
        return iter(self.snapshot)

    @property
    def snapshot(self) -> dict[K, V]:
        with self._lock:
            return dict(self._map)

    def keys(self) -> KeysView[K]:  # type: ignore[override]
        return self.snapshot.keys()

    def values(self) -> ValuesView[V]:  # type: ignore[override]
        return self.snapshot.values()

    def items(self) -> ItemsView[K, V]:  # type: ignore[override]
        return self.snapshot.items()

    def copy(self) -> dict[K, V]:
        return self.snapshot

    @typing.overload
    def pop(self, key: K, /) -> V: ...
    @typing.overload
    def pop(self, key: K, /, default: V) -> V: ...
    @typing.overload
    def pop[T](self, key: K, /, default: T) -> V | T: ...

    def pop(self, key: K, /, default: typing.Any = SENTINEL) -> typing.Any:
        with self._lock:
            if default is SENTINEL:
                return self._map.pop(key)
            return self._map.pop(key, default)

    def clear(self) -> None:
        with self._lock:
            self._generation += 1
            self._map.clear()

    def set_if_generation(self, key: K, value: V, expected_generation: int) -> bool:
        with self._lock:
            if self._generation != expected_generation:
                return False
            self._store_locked(key, value)
            return True

    @property
    def generation(self) -> int:
        return self._generation
