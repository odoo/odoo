# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

import typing
from decorator import decorator
from inspect import Parameter, getsourcefile, signature

from ..required import lazy


__all__ = [
    'classproperty',
    'conditional',
    'lazy',
    'lazy_classproperty',
    'lazy_property',
    'synchronized',
]

T = typing.TypeVar("T")
P = typing.ParamSpec("P")

if typing.TYPE_CHECKING:
    from collections.abc import Callable


class lazy_property(typing.Generic[T]):
    """ Decorator for a lazy property of an object, i.e., an object attribute
        that is determined by the result of a method call evaluated once. To
        reevaluate the property, simply delete the attribute on the object, and
        get it again.
    """
    def __init__(self, fget: Callable[[typing.Any], T]):
        assert not fget.__name__.startswith('__'),\
            "lazy_property does not support mangled names"
        self.fget = fget

    @typing.overload
    def __get__(self, obj: None, cls: typing.Any, /) -> typing.Any: ...
    @typing.overload
    def __get__(self, obj: object, cls: typing.Any, /) -> T: ...

    def __get__(self, obj, cls, /):
        if obj is None:
            return self
        value = self.fget(obj)
        setattr(obj, self.fget.__name__, value)
        return value

    @property
    def __doc__(self):
        return self.fget.__doc__

    @staticmethod
    def reset_all(obj) -> None:
        """ Reset all lazy properties on the instance `obj`. """
        cls = type(obj)
        obj_dict = vars(obj)
        for name in list(obj_dict):
            if isinstance(getattr(cls, name, None), lazy_property):
                obj_dict.pop(name)


def conditional(condition: typing.Any, decorator: Callable[[T], T]) -> Callable[[T], T]:
    """ Decorator for a conditionally applied decorator.

        Example::

           @conditional(get_config('use_cache'), ormcache)
           def fn():
               pass
    """
    if condition:
        return decorator
    else:
        return lambda fn: fn


def filter_kwargs(func: Callable, kwargs: dict[str, typing.Any]) -> dict[str, typing.Any]:
    """ Filter the given keyword arguments to only return the kwargs
        that binds to the function's signature.
    """
    leftovers = set(kwargs)
    for p in signature(func).parameters.values():
        if p.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY):
            leftovers.discard(p.name)
        elif p.kind == Parameter.VAR_KEYWORD:  # **kwargs
            leftovers.clear()
            break

    if not leftovers:
        return kwargs

    return {key: kwargs[key] for key in kwargs if key not in leftovers}


def synchronized(lock_attr: str = '_lock') -> Callable[[Callable[P, T]], Callable[P, T]]:
    @decorator
    def locked(func, inst, *args, **kwargs):
        with getattr(inst, lock_attr):
            return func(inst, *args, **kwargs)
    return locked


locked = synchronized()


def frame_codeinfo(fframe, back=0):
    """ Return a (filename, line) pair for a previous frame .
        @return (filename, lineno) where lineno is either int or string==''
    """
    try:
        if not fframe:
            return "<unknown>", ''
        for _i in range(back):
            fframe = fframe.f_back
        try:
            fname = getsourcefile(fframe)
        except TypeError:
            fname = '<builtin>'
        lineno = fframe.f_lineno or ''
        return fname, lineno
    except Exception:
        return "<unknown>", ''


class classproperty(typing.Generic[T]):
    def __init__(self, fget: Callable[[typing.Any], T]) -> None:
        self.fget = classmethod(fget)

    def __get__(self, cls, owner: type | None = None, /) -> T:
        return self.fget.__get__(None, owner)()

    @property
    def __doc__(self):
        return self.fget.__doc__


class lazy_classproperty(classproperty[T], typing.Generic[T]):
    """ Similar to :class:`lazy_property`, but for classes. """
    def __get__(self, cls, owner: type | None = None, /) -> T:
        val = super().__get__(cls, owner)
        setattr(owner, self.fget.__name__, val)
        return val
