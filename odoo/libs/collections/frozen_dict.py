__all__ = ["freehash", "frozendict"]

from collections.abc import Iterable, Mapping
from typing import Any


def freehash(arg: Any) -> int:
    """Compute a hash for any object, including unhashable ones.

    For unhashable objects (dicts, lists, etc.), attempts to convert
    them to a hashable form (frozendict, frozenset).
    """
    try:
        return hash(arg)
    except Exception:
        if isinstance(arg, Mapping):
            return hash(frozendict(arg))
        elif isinstance(arg, Iterable):
            return hash(frozenset(freehash(item) for item in arg))
        else:
            return id(arg)


class frozendict[K, T](dict[K, T]):
    """An implementation of an immutable dictionary."""

    __slots__ = ("_hash",)

    def __delitem__(self, key):
        raise NotImplementedError("'__delitem__' not supported on frozendict")

    def __setitem__(self, key, val):
        raise NotImplementedError("'__setitem__' not supported on frozendict")

    def clear(self):
        raise NotImplementedError("'clear' not supported on frozendict")

    def pop(self, key, default=None):
        raise NotImplementedError("'pop' not supported on frozendict")

    def popitem(self):
        raise NotImplementedError("'popitem' not supported on frozendict")

    def setdefault(self, key, default=None):
        raise NotImplementedError("'setdefault' not supported on frozendict")

    def update(self, *args, **kwargs):
        raise NotImplementedError("'update' not supported on frozendict")

    def __hash__(self) -> int:  # type: ignore
        try:
            return self._hash  # type: ignore[has-type]
        except AttributeError:
            h = hash(frozenset((key, freehash(val)) for key, val in self.items()))
            object.__setattr__(self, "_hash", h)
            return h
