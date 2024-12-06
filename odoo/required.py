from collections.abc import Mapping
from datetime import date, datetime
import json as json_
import markupsafe
import re
import typing


K = typing.TypeVar('K')
T = typing.TypeVar('T')


class lazy(object):
    """ A proxy to the (memoized) result of a lazy evaluation:

    .. code-block::

        foo = lazy(func, arg)           # func(arg) is not called yet
        bar = foo + 1                   # eval func(arg) and add 1
        baz = foo + 2                   # use result of func(arg) and add 2
    """
    __slots__ = ['_func', '_args', '_kwargs', '_cached_value']

    def __init__(self, func, *args, **kwargs):
        # bypass own __setattr__
        object.__setattr__(self, '_func', func)
        object.__setattr__(self, '_args', args)
        object.__setattr__(self, '_kwargs', kwargs)

    @property
    def _value(self):
        if self._func is not None:
            value = self._func(*self._args, **self._kwargs)
            object.__setattr__(self, '_func', None)
            object.__setattr__(self, '_args', None)
            object.__setattr__(self, '_kwargs', None)
            object.__setattr__(self, '_cached_value', value)
        return self._cached_value

    def __getattr__(self, name): return getattr(self._value, name)
    def __setattr__(self, name, value): return setattr(self._value, name, value)
    def __delattr__(self, name): return delattr(self._value, name)

    def __repr__(self):
        return repr(self._value) if self._func is None else object.__repr__(self)
    def __str__(self): return str(self._value)
    def __bytes__(self): return bytes(self._value)
    def __format__(self, format_spec): return format(self._value, format_spec)

    def __lt__(self, other): return other > self._value
    def __le__(self, other): return other >= self._value
    def __eq__(self, other): return other == self._value
    def __ne__(self, other): return other != self._value
    def __gt__(self, other): return other < self._value
    def __ge__(self, other): return other <= self._value

    def __hash__(self): return hash(self._value)
    def __bool__(self): return bool(self._value)

    def __call__(self, *args, **kwargs): return self._value(*args, **kwargs)

    def __len__(self): return len(self._value)
    def __getitem__(self, key): return self._value[key]
    def __missing__(self, key): return self._value.__missing__(key)
    def __setitem__(self, key, value): self._value[key] = value
    def __delitem__(self, key): del self._value[key]
    def __iter__(self): return iter(self._value)
    def __reversed__(self): return reversed(self._value)
    def __contains__(self, key): return key in self._value

    def __add__(self, other): return self._value.__add__(other)
    def __sub__(self, other): return self._value.__sub__(other)
    def __mul__(self, other): return self._value.__mul__(other)
    def __matmul__(self, other): return self._value.__matmul__(other)
    def __truediv__(self, other): return self._value.__truediv__(other)
    def __floordiv__(self, other): return self._value.__floordiv__(other)
    def __mod__(self, other): return self._value.__mod__(other)
    def __divmod__(self, other): return self._value.__divmod__(other)
    def __pow__(self, other): return self._value.__pow__(other)
    def __lshift__(self, other): return self._value.__lshift__(other)
    def __rshift__(self, other): return self._value.__rshift__(other)
    def __and__(self, other): return self._value.__and__(other)
    def __xor__(self, other): return self._value.__xor__(other)
    def __or__(self, other): return self._value.__or__(other)

    def __radd__(self, other): return self._value.__radd__(other)
    def __rsub__(self, other): return self._value.__rsub__(other)
    def __rmul__(self, other): return self._value.__rmul__(other)
    def __rmatmul__(self, other): return self._value.__rmatmul__(other)
    def __rtruediv__(self, other): return self._value.__rtruediv__(other)
    def __rfloordiv__(self, other): return self._value.__rfloordiv__(other)
    def __rmod__(self, other): return self._value.__rmod__(other)
    def __rdivmod__(self, other): return self._value.__rdivmod__(other)
    def __rpow__(self, other): return self._value.__rpow__(other)
    def __rlshift__(self, other): return self._value.__rlshift__(other)
    def __rrshift__(self, other): return self._value.__rrshift__(other)
    def __rand__(self, other): return self._value.__rand__(other)
    def __rxor__(self, other): return self._value.__rxor__(other)
    def __ror__(self, other): return self._value.__ror__(other)

    def __iadd__(self, other): return self._value.__iadd__(other)
    def __isub__(self, other): return self._value.__isub__(other)
    def __imul__(self, other): return self._value.__imul__(other)
    def __imatmul__(self, other): return self._value.__imatmul__(other)
    def __itruediv__(self, other): return self._value.__itruediv__(other)
    def __ifloordiv__(self, other): return self._value.__ifloordiv__(other)
    def __imod__(self, other): return self._value.__imod__(other)
    def __ipow__(self, other): return self._value.__ipow__(other)
    def __ilshift__(self, other): return self._value.__ilshift__(other)
    def __irshift__(self, other): return self._value.__irshift__(other)
    def __iand__(self, other): return self._value.__iand__(other)
    def __ixor__(self, other): return self._value.__ixor__(other)
    def __ior__(self, other): return self._value.__ior__(other)

    def __neg__(self): return self._value.__neg__()
    def __pos__(self): return self._value.__pos__()
    def __abs__(self): return self._value.__abs__()
    def __invert__(self): return self._value.__invert__()

    def __complex__(self): return complex(self._value)
    def __int__(self): return int(self._value)
    def __float__(self): return float(self._value)

    def __index__(self): return self._value.__index__()

    def __round__(self): return self._value.__round__()
    def __trunc__(self): return self._value.__trunc__()
    def __floor__(self): return self._value.__floor__()
    def __ceil__(self): return self._value.__ceil__()

    def __enter__(self): return self._value.__enter__()
    def __exit__(self, exc_type, exc_value, traceback):
        return self._value.__exit__(exc_type, exc_value, traceback)

    def __await__(self): return self._value.__await__()
    def __aiter__(self): return self._value.__aiter__()
    def __anext__(self): return self._value.__anext__()
    def __aenter__(self): return self._value.__aenter__()
    def __aexit__(self, exc_type, exc_value, traceback):
        return self._value.__aexit__(exc_type, exc_value, traceback)


class ReadonlyDict(Mapping[K, T], typing.Generic[K, T]):
    """Helper for an unmodifiable dictionary, not even updatable using `dict.update`.

    This is similar to a `frozendict`, with one drawback and one advantage:

    - `dict.update` works for a `frozendict` but not for a `ReadonlyDict`.
    - `json.dumps` works for a `frozendict` by default but not for a `ReadonlyDict`.

    This comes from the fact `frozendict` inherits from `dict`
    while `ReadonlyDict` inherits from `collections.abc.Mapping`.

    So, depending on your needs,
    whether you absolutely must prevent the dictionary from being updated (e.g., for security reasons)
    or you require it to be supported by `json.dumps`, you can choose either option.

        E.g.
          data = ReadonlyDict({'foo': 'bar'})
          data['baz'] = 'xyz' # raises exception
          data.update({'baz', 'xyz'}) # raises exception
          dict.update(data, {'baz': 'xyz'}) # raises exception
    """
    def __init__(self, data):
        self.__data = dict(data)

    def __getitem__(self, key: K) -> T:
        return self.__data[key]

    def __len__(self):
        return len(self.__data)

    def __iter__(self):
        return iter(self.__data)


JSON_SCRIPTSAFE_MAPPER = {
    '&': r'\u0026',
    '<': r'\u003c',
    '>': r'\u003e',
    '\u2028': r'\u2028',
    '\u2029': r'\u2029'
}


class _ScriptSafe(str):
    def __html__(self):
        # replacement can be done straight in the serialised JSON as the
        # problematic characters are not JSON metacharacters (and can thus
        # only occur in strings)
        return markupsafe.Markup(re.sub(
            r'[<>&\u2028\u2029]',
            lambda m: JSON_SCRIPTSAFE_MAPPER[m[0]],
            self,
        ))


class JSON:

    def loads(self, *args, **kwargs):
        return json_.loads(*args, **kwargs)

    def dumps(self, *args, **kwargs):
        """ JSON used as JS in HTML (script tags) is problematic: <script>
        tags are a special context which only waits for </script> but doesn't
        interpret anything else, this means standard htmlescaping does not
        work (it breaks double quotes, and e.g. `<` will become `&lt;` *in
        the resulting JSON/JS* not just inside the page).

        However, failing to escape embedded json means the json strings could
        contains `</script>` and thus become XSS vector.

        The solution turns out to be very simple: use JSON-level unicode
        escapes for HTML-unsafe characters (e.g. "<" -> "\u003C". This removes
        the XSS issue without breaking the json, and there is no difference to
        the end result once it's been parsed back from JSON. So it will work
        properly even for HTML attributes or raw text.

        Also handle U+2028 and U+2029 the same way just in case as these are
        interpreted as newlines in javascript but not in JSON, which could
        lead to oddities and issues.

        .. warning::

            except inside <script> elements, this should be escaped following
            the normal rules of the containing format

        Cf https://code.djangoproject.com/ticket/17419#comment:27
        """
        return _ScriptSafe(json_.dumps(*args, **kwargs))


scriptsafe = JSON()


def json_default(obj):
    from odoo import fields  # noqa: PLC0415
    if isinstance(obj, datetime):
        return fields.Datetime.to_string(obj)
    if isinstance(obj, date):
        return fields.Date.to_string(obj)
    if isinstance(obj, lazy):
        return obj._value
    if isinstance(obj, ReadonlyDict):
        return dict(obj)
    if isinstance(obj, bytes):
        return obj.decode()
    return str(obj)
