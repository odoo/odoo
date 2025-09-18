__all__ = ["Collector", "Reverse", "ReversedIterable", "StackMap"]

from collections.abc import Iterable, Iterator, MutableMapping, Reversible


class Collector[K, T](dict[K, tuple[T, ...]]):
    """A mapping from keys to tuples.

    This implements a relation, and can be seen as a space optimization
    for ``defaultdict(tuple)``.
    """

    __slots__ = ()

    def __getitem__(self, key: K) -> tuple[T, ...]:
        return self.get(key, ())

    def __setitem__(self, key: K, val: Iterable[T]):
        val = tuple(val)
        if val:
            super().__setitem__(key, val)
        else:
            super().pop(key, None)

    def add(self, key: K, val: T):
        vals = self[key]
        if val not in vals:
            self[key] = vals + (val,)

    def discard_keys_and_values(self, excludes) -> None:
        for key in excludes:
            self.pop(key, None)
        for key, vals in list(self.items()):
            self[key] = tuple(val for val in vals if val not in excludes)


class StackMap[K, T](MutableMapping[K, T]):
    """A stack of mappings behaving as a single mapping.

    Used to implement nested scopes. The lookups search the stack from
    top to bottom, and returns the first value found. Mutable operations
    modify the topmost mapping only.
    """

    __slots__ = ["_maps"]

    def __init__(self, m: MutableMapping[K, T] | None = None):
        self._maps = [] if m is None else [m]

    def __getitem__(self, key: K) -> T:
        for mapping in reversed(self._maps):
            try:
                return mapping[key]
            except KeyError:
                pass
        raise KeyError(key)

    def __setitem__(self, key: K, val: T):
        self._maps[-1][key] = val

    def __delitem__(self, key: K):
        del self._maps[-1][key]

    def __iter__(self) -> Iterator[K]:
        return iter({key for mapping in self._maps for key in mapping})

    def __len__(self) -> int:
        return sum(1 for key in self)

    def __str__(self) -> str:
        return f"<StackMap {self._maps}>"

    def pushmap(self, m: MutableMapping[K, T] | None = None):
        self._maps.append({} if m is None else m)

    def popmap(self) -> MutableMapping[K, T]:
        return self._maps.pop()


class ReversedIterable[T](Reversible[T]):
    """An iterable implementing the reversal of another iterable."""

    __slots__ = ["iterable"]

    def __init__(self, iterable: Reversible[T]):
        self.iterable = iterable

    def __iter__(self):
        return reversed(self.iterable)

    def __reversed__(self):
        return iter(self.iterable)


class Reverse:
    """Wraps a value and reverses its ordering.

    Useful in key functions when mixing ascending and descending sort
    on non-numeric data as the ``reverse`` parameter can not do
    piecemeal reordering.
    """

    __slots__ = ["val"]

    def __init__(self, val):
        self.val = val

    def __eq__(self, other):
        return self.val == other.val

    def __ne__(self, other):
        return self.val != other.val

    def __ge__(self, other):
        return self.val <= other.val

    def __gt__(self, other):
        return self.val < other.val

    def __le__(self, other):
        return self.val >= other.val

    def __lt__(self, other):
        return self.val > other.val
