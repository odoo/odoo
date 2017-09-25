# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

__all__ = ['synchronized', 'lazy_classproperty', 'lazy_property',
           'classproperty', 'conditional']

from functools import wraps
from inspect import getsourcefile


class lazy_property(object):
    """ Decorator for a lazy property of an object, i.e., an object attribute
        that is determined by the result of a method call evaluated once. To
        reevaluate the property, simply delete the attribute on the object, and
        get it again.
    """
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = self.fget(obj)
        setattr(obj, self.fget.__name__, value)
        return value

    @property
    def __doc__(self):
        return self.fget.__doc__

    @staticmethod
    def reset_all(obj):
        """ Reset all lazy properties on the instance `obj`. """
        cls = type(obj)
        obj_dict = vars(obj)
        for name in list(obj_dict):
            if isinstance(getattr(cls, name, None), lazy_property):
                obj_dict.pop(name)

class lazy_classproperty(lazy_property):
    """ Similar to :class:`lazy_property`, but for classes. """
    def __get__(self, obj, cls):
        val = self.fget(cls)
        setattr(cls, self.fget.__name__, val)
        return val

def conditional(condition, decorator):
    """ Decorator for a conditionally applied decorator.

        Example:

           @conditional(get_config('use_cache'), ormcache)
           def fn():
               pass
    """
    if condition:
        return decorator
    else:
        return lambda fn: fn

def synchronized(lock_attr='_lock'):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            lock = getattr(self, lock_attr)
            try:
                lock.acquire()
                return func(self, *args, **kwargs)
            finally:
                lock.release()
        return wrapper
    return decorator

def frame_codeinfo(fframe, back=0):
    """ Return a (filename, line) pair for a previous frame .
        @return (filename, lineno) where lineno is either int or string==''
    """
    
    try:
        if not fframe:
            return "<unknown>", ''
        for i in range(back):
            fframe = fframe.f_back
        try:
            fname = getsourcefile(fframe)
        except TypeError:
            fname = '<builtin>'
        lineno = fframe.f_lineno or ''
        return fname, lineno
    except Exception:
        return "<unknown>", ''

def compose(a, b):
    """ Composes the callables ``a`` and ``b``. ``compose(a, b)(*args)`` is
    equivalent to ``a(b(*args))``.

    Can be used as a decorator by partially applying ``a``::

         @partial(compose, a)
         def b():
            ...
    """
    @wraps(b)
    def wrapper(*args, **kwargs):
        return a(b(*args, **kwargs))
    return wrapper


class _ClassProperty(property):
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()

def classproperty(func):
    return _ClassProperty(classmethod(func))
