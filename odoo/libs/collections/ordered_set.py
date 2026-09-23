__all__ = ["FrozenOrderedSet", "LastOrderedSet", "OrderedSet"]

import itertools
from collections.abc import (
    Iterable,
    Iterator,
    Mapping,
    MutableSet,
)
from collections.abc import (
    Set as AbstractSet,
)
from functools import reduce
from types import MappingProxyType
from typing import Self, override


class FrozenOrderedSet[T](AbstractSet[T]):
    __slots__ = ("_map",)
    _map: Mapping[T, None]

    def __init__(self, elems: Iterable[T] = ()) -> None:
        object.__setattr__(self, "_map", MappingProxyType(dict.fromkeys(elems)))

    def __setattr__(self, name: str, value: object) -> None:
        raise TypeError("FrozenOrderedSet is immutable")

    def __delattr__(self, name: str) -> None:
        raise TypeError("FrozenOrderedSet is immutable")

    def __contains__(self, elem: object) -> bool:
        return elem in self._map

    def __iter__(self) -> Iterator[T]:
        return iter(self._map)

    def __len__(self) -> int:
        return len(self._map)

    def __and__(self, other: Iterable[T]) -> Self:  # type: ignore[override]
        if not isinstance(other, Iterable):
            return NotImplemented
        members = other if isinstance(other, (AbstractSet, Mapping)) else set(other)
        return type(self)(elem for elem in self if elem in members)

    __rand__ = __and__

    def __hash__(self) -> int:
        return hash(frozenset(self._map))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self)!r})"

    def __reduce__(self) -> tuple[type[Self], tuple[tuple[T, ...]]]:
        return type(self), (tuple(self),)


class OrderedSet[T](MutableSet[T]):
    __slots__ = ["_map"]

    def __init__(self, elems: Iterable[T] = ()) -> None:
        self._map: dict[T, None] = dict.fromkeys(elems)

    def __contains__(self, elem: object) -> bool:
        return elem in self._map

    def __iter__(self) -> Iterator[T]:
        return iter(self._map)

    def __len__(self) -> int:
        return len(self._map)

    def add(self, elem: T) -> None:
        self._map[elem] = None

    def discard(self, elem: T) -> None:
        self._map.pop(elem, None)

    def update(self, elems: Iterable[T]) -> None:
        self._map.update(zip(elems, itertools.repeat(None)))

    def difference_update(self, elems: Iterable[T]) -> None:
        _pop = self._map.pop
        for elem in elems:
            _pop(elem, None)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self)!r})"

    def __and__(self, other: Iterable[T]) -> OrderedSet[T]:  # type: ignore[override]
        if not isinstance(other, Iterable):
            return NotImplemented
        members = other if isinstance(other, (AbstractSet, Mapping)) else set(other)
        return type(self)(elem for elem in self if elem in members)

    __rand__ = __and__

    def intersection(self, *others: Iterable[T]) -> OrderedSet[T]:
        if not others:
            return self.copy()
        intersect = OrderedSet.__and__
        return reduce(intersect, others, self)

    def copy(self) -> Self:
        instance = object.__new__(type(self))
        instance._map = self._map.copy()
        return instance


class LastOrderedSet[T](OrderedSet[T]):
    __slots__ = ()

    @override
    def add(self, elem: T) -> None:
        self.discard(elem)
        super().add(elem)

    def update(self, elems: Iterable[T]) -> None:
        for elem in elems:
            self.add(elem)
