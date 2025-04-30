import threading
import typing
from collections.abc import Iterable, Iterator, MutableMapping

from .misc import SENTINEL

__all__ = ['LRU']

K = typing.TypeVar('K')
V = typing.TypeVar('V')


class LRU(MutableMapping[K, V], typing.Generic[K, V]):
    """
    Implementation of a length-limited LRU map.

    The mapping is thread-safe, and internally uses a lock to avoid concurrency
    issues. However, access operations like ``lru[key]`` are fast and
    lock-free.
    """

    __slots__ = ('_count', '_lock', '_ordering', '_values')

    def __init__(self, count: int, pairs: Iterable[tuple[K, V]] = ()):
        assert count > 0, "LRU needs a positive count"
        self._count = count
        self._lock = threading.RLock()
        self._values: dict[K, V] = {}
        #
        # The dict self._values contains the LRU items, while self._ordering
        # only keeps track of their order, the most recently used ones being
        # last. For performance reasons, we only use the lock when modifying
        # the LRU, while reading it is lock-free (and thus faster).
        #
        # This strategy may result in inconsistencies between self._values and
        # self._ordering. Indeed, concurrently accessed keys may be missing
        # from self._ordering, but will eventually be added. This could result
        # in keys being added back in self._ordering after their actual removal
        # from the LRU. This results in the following invariant:
        #
        #     self._values <= self._ordering | "keys being accessed"
        #
        self._ordering: dict[K, None] = {}

        # Initialize
        for key, value in pairs:
            self[key] = value

    @property
    def count(self) -> int:
        return self._count

    def __contains__(self, key: object) -> bool:
        return key in self._values

    def __getitem__(self, key: K) -> V:
        val = self._values[key]
        # move key at the last position in self._ordering
        self._ordering[key] = self._ordering.pop(key, None)
        return val

    def __setitem__(self, key: K, val: V):
        values = self._values
        ordering = self._ordering
        with self._lock:
            values[key] = val
            ordering[key] = ordering.pop(key, None)
            while True:
                # if we have too many keys in ordering, filter them out
                if len(ordering) > len(values):
                    # (copy to avoid concurrent changes on ordering)
                    for k in ordering.copy():
                        if k not in values:
                            ordering.pop(k, None)
                # check if we have too many keys
                if len(values) <= self._count:
                    break
                # if so, pop the least recently used
                try:
                    # have a default in case of concurrent accesses
                    key = next(iter(ordering), key)
                except RuntimeError:
                    # ordering modified during iteration, retry
                    continue
                values.pop(key, None)
                ordering.pop(key, None)

    def __delitem__(self, key: K):
        self.pop(key)

    def __len__(self) -> int:
        return len(self._values)

    def __iter__(self) -> Iterator[K]:
        return iter(self.snapshot)

    @property
    def snapshot(self) -> dict[K, V]:
        """ Return a copy of the LRU (ordered according to LRU first). """
        with self._lock:
            values = self._values
            # build result in expected order (copy self._ordering to avoid concurrent changes)
            result = {
                key: val
                for key in self._ordering.copy()
                if (val := values.get(key, SENTINEL)) is not SENTINEL
            }
            if len(result) < len(values):
                # keys in value were missing from self._ordering, add them
                result.update(values)
        return result

    def pop(self, key: K, /, default=SENTINEL) -> V:
        with self._lock:
            self._ordering.pop(key, None)
            if default is SENTINEL:
                return self._values.pop(key)
            return self._values.pop(key, default)

    def clear(self):
        with self._lock:
            self._ordering.clear()
            self._values.clear()
