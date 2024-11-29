import collections
import threading
import typing
from collections.abc import Iterable, Iterator, MutableMapping

from .func import locked

__all__ = ['LRU']

K = typing.TypeVar('K')
V = typing.TypeVar('V')


class LRU(MutableMapping[K, V], typing.Generic[K, V]):
    """
    Implementation of a length-limited O(1) LRU map.

    Original Copyright 2003 Josiah Carlson, later rebuilt on OrderedDict and added typing.
    """
    def __init__(self, count: int, pairs: Iterable[tuple[K, V]] = ()):
        self._lock = threading.RLock()
        self.count = max(count, 1)
        self.d: collections.OrderedDict[K, V] = collections.OrderedDict()
        for key, value in pairs:
            self[key] = value

    @locked
    def __contains__(self, obj: K) -> bool:
        return obj in self.d

    @locked
    def __getitem__(self, obj: K) -> V:
        a = self.d[obj]
        self.d.move_to_end(obj, last=False)
        return a

    @locked
    def __setitem__(self, obj: K, val: V):
        self.d[obj] = val
        self.d.move_to_end(obj, last=False)
        while len(self.d) > self.count:
            self.d.popitem(last=True)

    @locked
    def __delitem__(self, obj: K):
        del self.d[obj]

    @locked
    def __len__(self) -> int:
        return len(self.d)

    @locked
    def __iter__(self) -> Iterator[K]:
        return iter(self.d)

    @locked
    def pop(self, key: K) -> V:
        return self.d.pop(key)

    @locked
    def clear(self):
        self.d.clear()
