__all__ = ["LastOrderedSet", "OrderedSet"]

import itertools
from collections.abc import Iterable, MutableSet
from functools import reduce


class OrderedSet[T](MutableSet[T]):
    """A set collection that remembers the elements first insertion order."""

    __slots__ = ["_map"]

    def __init__(self, elems: Iterable[T] = ()):
        self._map: dict[T, None] = dict.fromkeys(elems)

    def __contains__(self, elem):
        return elem in self._map

    def __iter__(self):
        return iter(self._map)

    def __len__(self):
        return len(self._map)

    def add(self, elem):
        self._map[elem] = None

    def discard(self, elem):
        self._map.pop(elem, None)

    def update(self, elems):
        self._map.update(zip(elems, itertools.repeat(None)))

    def difference_update(self, elems):
        # inline discard to avoid method dispatch per element
        _pop = self._map.pop
        for elem in elems:
            _pop(elem, None)

    def __repr__(self):
        return f"{type(self).__name__}({list(self)!r})"

    def intersection(self, *others):
        return reduce(OrderedSet.__and__, others, self)

    def copy(self):
        """Return a shallow copy of the set.

        Uses ``object.__new__`` + ``dict.copy()`` instead of iterating
        ``self`` to avoid triggering Python-level callbacks (e.g. GC
        ``__del__`` / WeakSet ``_remove``) that can mutate ``_map`` while
        it is being read.  This matters when an ``OrderedSet`` is used as
        the backing store for a ``weakref.WeakSet``: Python 3.14 changed
        ``WeakSet.__iter__`` to call ``self.data.copy()`` before iteration,
        and the GC can fire ``_remove`` callbacks during a Python-level
        iteration of ``_map``, raising
        ``RuntimeError: dictionary changed size during iteration``.
        """
        instance = object.__new__(type(self))
        instance._map = self._map.copy()
        return instance


class LastOrderedSet[T](OrderedSet[T]):
    """A set collection that remembers the elements last insertion order."""

    def add(self, elem):
        self.discard(elem)
        super().add(elem)
