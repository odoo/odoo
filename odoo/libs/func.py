import functools
import operator
from collections import deque
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import types

__all__ = [
    "Callbacks",
    "classproperty",
    "conditional",
    "frame_codeinfo",
    "lazy",
    "lazy_classproperty",
    "locked",
    "reset_cached_properties",
    "synchronized",
]


class Callbacks:
    __slots__ = ("_funcs", "data")

    def __init__(self) -> None:
        self._funcs: deque[Callable[[], object]] = deque()
        self.data: dict[Any, Any] = {}

    def add(self, func: Callable[[], object]) -> None:
        self._funcs.append(func)

    def run(self) -> None:
        while self._funcs:
            func = self._funcs.popleft()
            func()
        self.clear()

    def clear(self) -> None:
        self._funcs.clear()
        self.data.clear()

    def __len__(self) -> int:
        return len(self._funcs)


def reset_cached_properties(obj: object) -> None:
    cls = type(obj)
    obj_dict = vars(obj)
    for name in list(obj_dict):
        if isinstance(getattr(cls, name, None), functools.cached_property):
            del obj_dict[name]


def conditional[T](condition: Any, decorator: Callable[[T], T]) -> Callable[[T], T]:
    if condition:
        return decorator
    else:
        return lambda fn: fn


def synchronized(
    lock_attr: str = "_lock",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:

    def synchronized_lock(func: Callable[..., Any], /) -> Callable[..., Any]:
        @functools.wraps(func)
        def locked(inst: Any, *args: Any, **kwargs: Any) -> Any:
            with getattr(inst, lock_attr):
                return func(inst, *args, **kwargs)

        return locked

    return synchronized_lock


locked = synchronized()


def frame_codeinfo(
    fframe: types.FrameType | None,
    back: int = 0,
) -> tuple[str | None, int | str]:
    try:
        if not fframe:
            return "<unknown>", ""
        for _i in range(back):
            fframe = fframe.f_back
            if fframe is None:
                return "<unknown>", ""
        fname = fframe.f_code.co_filename or "<builtin>"
        lineno = fframe.f_lineno or ""
        return fname, lineno
    except Exception:
        return "<unknown>", ""


class classproperty[T]:
    def __init__(self, fget: Callable[[Any], T]) -> None:
        self.fget = classmethod(fget)

    def __get__(self, cls: Any, owner: type | None = None, /) -> T:
        return self.fget.__get__(None, owner)()

    @property
    def __doc__(self) -> str | None:  # type: ignore[override]
        return self.fget.__doc__


class lazy_classproperty[T](classproperty[T]):
    def __init__(self, fget: Callable[[Any], T]) -> None:
        super().__init__(fget)
        self._cache: dict[type | None, T] = {}

    def __get__(self, cls: Any, owner: type | None = None, /) -> T:
        if owner not in self._cache:
            self._cache[owner] = super().__get__(cls, owner)
        return self._cache[owner]


class lazy:
    __slots__ = ("_args", "_cached_value", "_func", "_kwargs")

    def __init__(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        object.__setattr__(self, "_func", func)
        object.__setattr__(self, "_args", args)
        object.__setattr__(self, "_kwargs", kwargs)

    @property
    def _value(self) -> Any:
        if self._func is not None:
            value = self._func(*self._args, **self._kwargs)
            object.__setattr__(self, "_cached_value", value)
            object.__setattr__(self, "_args", None)
            object.__setattr__(self, "_kwargs", None)
            object.__setattr__(self, "_func", None)
        return self._cached_value

    def __getattr__(self, name: str) -> Any:
        if name in lazy.__slots__:
            raise AttributeError(name)
        return getattr(self._value, name)

    def __reduce__(self) -> tuple[Any, tuple[Any]]:
        return (_reconstruct_lazy, (self._value,))

    def __setattr__(self, name: str, value: Any) -> None:
        return setattr(self._value, name, value)

    def __delattr__(self, name: str) -> None:
        return delattr(self._value, name)

    def __repr__(self) -> str:
        return repr(self._value) if self._func is None else object.__repr__(self)

    def __str__(self) -> str:
        return str(self._value)

    def __bytes__(self) -> bytes:
        return bytes(self._value)

    def __format__(self, format_spec: str) -> str:
        return format(self._value, format_spec)

    def __lt__(self, other: Any) -> Any:
        return other > self._value

    def __le__(self, other: Any) -> Any:
        return other >= self._value

    def __eq__(self, other: object) -> Any:
        return other == self._value

    def __ne__(self, other: object) -> Any:
        return other != self._value

    def __gt__(self, other: Any) -> Any:
        return other < self._value

    def __ge__(self, other: Any) -> Any:
        return other <= self._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __bool__(self) -> bool:
        return bool(self._value)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._value(*args, **kwargs)

    def __len__(self) -> int:
        return len(self._value)

    def __getitem__(self, key: Any) -> Any:
        return self._value[key]

    def __missing__(self, key: Any) -> Any:
        return self._value.__missing__(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        self._value[key] = value

    def __delitem__(self, key: Any) -> None:
        del self._value[key]

    def __iter__(self) -> Any:
        return iter(self._value)

    def __next__(self) -> Any:
        return next(self._value)

    def __reversed__(self) -> Any:
        return reversed(self._value)

    def __contains__(self, key: Any) -> bool:
        return key in self._value

    def __add__(self, other: Any) -> Any:
        return operator.add(self._value, other)

    def __sub__(self, other: Any) -> Any:
        return operator.sub(self._value, other)

    def __mul__(self, other: Any) -> Any:
        return operator.mul(self._value, other)

    def __matmul__(self, other: Any) -> Any:
        return operator.matmul(self._value, other)

    def __truediv__(self, other: Any) -> Any:
        return operator.truediv(self._value, other)

    def __floordiv__(self, other: Any) -> Any:
        return operator.floordiv(self._value, other)

    def __mod__(self, other: Any) -> Any:
        return operator.mod(self._value, other)

    def __divmod__(self, other: Any) -> Any:
        return divmod(self._value, other)

    def __pow__(self, other: Any, modulo: Any = None) -> Any:
        if modulo is None:
            return self._value**other
        return pow(self._value, other, modulo)

    def __lshift__(self, other: Any) -> Any:
        return operator.lshift(self._value, other)

    def __rshift__(self, other: Any) -> Any:
        return operator.rshift(self._value, other)

    def __and__(self, other: Any) -> Any:
        return operator.and_(self._value, other)

    def __xor__(self, other: Any) -> Any:
        return operator.xor(self._value, other)

    def __or__(self, other: Any) -> Any:
        return operator.or_(self._value, other)

    def __radd__(self, other: Any) -> Any:
        return operator.add(other, self._value)

    def __rsub__(self, other: Any) -> Any:
        return operator.sub(other, self._value)

    def __rmul__(self, other: Any) -> Any:
        return operator.mul(other, self._value)

    def __rmatmul__(self, other: Any) -> Any:
        return operator.matmul(other, self._value)

    def __rtruediv__(self, other: Any) -> Any:
        return operator.truediv(other, self._value)

    def __rfloordiv__(self, other: Any) -> Any:
        return operator.floordiv(other, self._value)

    def __rmod__(self, other: Any) -> Any:
        return operator.mod(other, self._value)

    def __rdivmod__(self, other: Any) -> Any:
        return divmod(other, self._value)

    def __rpow__(self, other: Any) -> Any:
        return other**self._value

    def __rlshift__(self, other: Any) -> Any:
        return operator.lshift(other, self._value)

    def __rrshift__(self, other: Any) -> Any:
        return operator.rshift(other, self._value)

    def __rand__(self, other: Any) -> Any:
        return operator.and_(other, self._value)

    def __rxor__(self, other: Any) -> Any:
        return operator.xor(other, self._value)

    def __ror__(self, other: Any) -> Any:
        return operator.or_(other, self._value)

    def __iadd__(self, other: Any) -> Any:
        return operator.iadd(self._value, other)

    def __isub__(self, other: Any) -> Any:
        return operator.isub(self._value, other)

    def __imul__(self, other: Any) -> Any:
        return operator.imul(self._value, other)

    def __imatmul__(self, other: Any) -> Any:
        return operator.imatmul(self._value, other)

    def __itruediv__(self, other: Any) -> Any:
        return operator.itruediv(self._value, other)

    def __ifloordiv__(self, other: Any) -> Any:
        return operator.ifloordiv(self._value, other)

    def __imod__(self, other: Any) -> Any:
        return operator.imod(self._value, other)

    def __ipow__(self, other: Any) -> Any:  # type: ignore[misc]
        return operator.ipow(self._value, other)

    def __ilshift__(self, other: Any) -> Any:
        return operator.ilshift(self._value, other)

    def __irshift__(self, other: Any) -> Any:
        return operator.irshift(self._value, other)

    def __iand__(self, other: Any) -> Any:
        return operator.iand(self._value, other)

    def __ixor__(self, other: Any) -> Any:
        return operator.ixor(self._value, other)

    def __ior__(self, other: Any) -> Any:
        return operator.ior(self._value, other)

    def __neg__(self) -> Any:
        return self._value.__neg__()

    def __pos__(self) -> Any:
        return self._value.__pos__()

    def __abs__(self) -> Any:
        return self._value.__abs__()

    def __invert__(self) -> Any:
        return self._value.__invert__()

    def __complex__(self) -> complex:
        return complex(self._value)

    def __int__(self) -> int:
        return int(self._value)

    def __float__(self) -> float:
        return float(self._value)

    def __index__(self) -> int:
        return self._value.__index__()

    def __round__(self, ndigits: Any = None) -> Any:
        return round(self._value, ndigits)

    def __trunc__(self) -> Any:
        return self._value.__trunc__()

    def __floor__(self) -> Any:
        return self._value.__floor__()

    def __ceil__(self) -> Any:
        return self._value.__ceil__()

    def __enter__(self) -> Any:
        return self._value.__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> Any:
        return self._value.__exit__(exc_type, exc_value, traceback)

    def __await__(self) -> Any:
        return self._value.__await__()

    def __aiter__(self) -> Any:
        return self._value.__aiter__()

    def __anext__(self) -> Any:
        return self._value.__anext__()

    def __aenter__(self) -> Any:
        return self._value.__aenter__()

    def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> Any:
        return self._value.__aexit__(exc_type, exc_value, traceback)


def _reconstruct_lazy(value: Any) -> lazy:
    obj = lazy.__new__(lazy)
    object.__setattr__(obj, "_func", None)
    object.__setattr__(obj, "_args", None)
    object.__setattr__(obj, "_kwargs", None)
    object.__setattr__(obj, "_cached_value", value)
    return obj
