__all__ = ["freehash", "frozendict"]

from collections.abc import Iterable, Mapping
from typing import Any, NoReturn


def freehash(arg: Any) -> int:
    return _freehash(arg, set())


def _freehash(arg: Any, path: set[int]) -> int:
    if isinstance(arg, frozendict):
        cached = getattr(arg, "_hash", None)
        if cached is not None:
            return cached
    else:
        try:
            return hash(arg)
        except TypeError:
            pass
    marker = id(arg)
    if marker in path:
        # A value met again on its own path closes a cycle. Equal structures close it at the
        # same point, so a constant keeps them hashing equal.
        return 0
    path.add(marker)
    try:
        if isinstance(arg, Mapping):
            return hash(
                frozenset(
                    (key, hash(val) if type(val) in _SCALARS else _freehash(val, path))
                    for key, val in arg.items()
                )
            )
        if isinstance(arg, Iterable):
            return hash(
                frozenset(
                    hash(item) if type(item) in _SCALARS else _freehash(item, path)
                    for item in arg
                )
            )
        return id(arg)
    finally:
        path.discard(marker)


# the values a context mostly holds; hashed in place instead of through a call
_SCALARS = frozenset({str, int, bool, float, type(None), bytes})


class frozendict[K, T](dict[K, T]):
    __slots__ = ("_hash",)

    _hash: int

    def __delitem__(self, key: K) -> NoReturn:
        msg = "'__delitem__' not supported on frozendict"
        raise NotImplementedError(msg)

    def __setitem__(self, key: K, val: T) -> NoReturn:
        msg = "'__setitem__' not supported on frozendict"
        raise NotImplementedError(msg)

    def clear(self) -> NoReturn:
        msg = "'clear' not supported on frozendict"
        raise NotImplementedError(msg)

    def pop(self, key: K, default: T | None = None) -> NoReturn:  # type: ignore[override]
        msg = "'pop' not supported on frozendict"
        raise NotImplementedError(msg)

    def popitem(self) -> NoReturn:
        msg = "'popitem' not supported on frozendict"
        raise NotImplementedError(msg)

    def setdefault(self, key: K, default: T | None = None) -> NoReturn:
        msg = "'setdefault' not supported on frozendict"
        raise NotImplementedError(msg)

    def update(self, *args: Any, **kwargs: Any) -> NoReturn:
        msg = "'update' not supported on frozendict"
        raise NotImplementedError(msg)

    def __ior__(self, other: Any) -> NoReturn:  # type: ignore[misc]
        msg = "'|=' not supported on frozendict"
        raise NotImplementedError(msg)

    def __reduce__(self) -> tuple[Any, tuple[type, dict[K, T]]]:
        return (_rebuild_frozendict, (type(self), dict(self)))

    def __hash__(self) -> int:  # type: ignore[override]
        try:
            return self._hash
        except AttributeError:
            h = _freehash(self, set())
            object.__setattr__(self, "_hash", h)
            return h


def _rebuild_frozendict[K, T](cls: type, items: dict[K, T]) -> Any:
    obj: dict[K, T] = dict.__new__(cls)
    dict.update(obj, items)
    return obj
