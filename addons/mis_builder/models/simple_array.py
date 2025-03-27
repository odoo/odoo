# Copyright 2014 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
""" A trivial immutable array that supports basic arithmetic operations.

>>> a = SimpleArray((1.0, 2.0, 3.0))
>>> b = SimpleArray((4.0, 5.0, 6.0))
>>> t  = (4.0, 5.0, 6.0)
>>> +a
SimpleArray((1.0, 2.0, 3.0))
>>> -a
SimpleArray((-1.0, -2.0, -3.0))
>>> a + b
SimpleArray((5.0, 7.0, 9.0))
>>> b + a
SimpleArray((5.0, 7.0, 9.0))
>>> a + t
SimpleArray((5.0, 7.0, 9.0))
>>> t + a
SimpleArray((5.0, 7.0, 9.0))
>>> a - b
SimpleArray((-3.0, -3.0, -3.0))
>>> a - t
SimpleArray((-3.0, -3.0, -3.0))
>>> t - a
SimpleArray((3.0, 3.0, 3.0))
>>> a * b
SimpleArray((4.0, 10.0, 18.0))
>>> b * a
SimpleArray((4.0, 10.0, 18.0))
>>> a * t
SimpleArray((4.0, 10.0, 18.0))
>>> t * a
SimpleArray((4.0, 10.0, 18.0))
>>> a / b
SimpleArray((0.25, 0.4, 0.5))
>>> b / a
SimpleArray((4.0, 2.5, 2.0))
>>> a / t
SimpleArray((0.25, 0.4, 0.5))
>>> t / a
SimpleArray((4.0, 2.5, 2.0))
>>> b / 2
SimpleArray((2.0, 2.5, 3.0))
>>> 2 * b
SimpleArray((8.0, 10.0, 12.0))
>>> 1 - b
SimpleArray((-3.0, -4.0, -5.0))
>>> b += 2 ; b
SimpleArray((6.0, 7.0, 8.0))
>>> a / ((1.0, 0.0, 1.0))
SimpleArray((1.0, DataError('#DIV/0'), 3.0))
>>> a / 0.0
SimpleArray((DataError('#DIV/0'), DataError('#DIV/0'), DataError('#DIV/0')))
>>> a * ((1.0, 'a', 1.0))
SimpleArray((1.0, DataError('#ERR'), 3.0))
>>> 6.0 / a
SimpleArray((6.0, 3.0, 2.0))
>>> Vector = named_simple_array('Vector', ('x', 'y'))
>>> p1 = Vector((1, 2))
>>> print(p1.x, p1.y, p1)
1 2 Vector((1, 2))
>>> p2 = Vector((2, 3))
>>> print(p2.x, p2.y, p2)
2 3 Vector((2, 3))
>>> p3 = p1 + p2
>>> print(p3.x, p3.y, p3)
3 5 Vector((3, 5))
>>> p4 = (4, 5) + p2
>>> print(p4.x, p4.y, p4)
6 8 Vector((6, 8))
>>> p1 * 2
Vector((2, 4))
>>> 2 * p1
Vector((2, 4))
>>> p1 - 1
Vector((0, 1))
>>> 1 - p1
Vector((0, -1))
>>> p1 / 2.0
Vector((0.5, 1.0))
>>> v = 2.0 / p1
>>> print(v.x, v.y, v)
2.0 1.0 Vector((2.0, 1.0))
"""

import itertools
import operator
import traceback

from .data_error import DataError

__all__ = ["SimpleArray", "named_simple_array"]


class SimpleArray(tuple):
    def _op(self, op, other):
        def _o2(x, y):
            try:
                return op(x, y)
            except ZeroDivisionError:
                return DataError("#DIV/0", traceback.format_exc())
            except Exception:
                return DataError("#ERR", traceback.format_exc())

        if isinstance(other, tuple):
            if len(other) != len(self):
                raise TypeError("tuples must have same length for %s" % op)
            return self.__class__(map(_o2, self, other))
        else:
            return self.__class__(_o2(z, other) for z in self)

    def _cast(self, other):
        if isinstance(other, self.__class__):
            return other
        elif isinstance(other, tuple):
            return self.__class__(other)
        else:
            # other is a scalar
            return self.__class__(itertools.repeat(other, len(self)))

    def __add__(self, other):
        return self._op(operator.add, other)

    __radd__ = __add__

    def __pos__(self):
        return self.__class__(map(operator.pos, self))

    def __neg__(self):
        return self.__class__(map(operator.neg, self))

    def __sub__(self, other):
        return self._op(operator.sub, other)

    def __rsub__(self, other):
        return self._cast(other)._op(operator.sub, self)

    def __mul__(self, other):
        return self._op(operator.mul, other)

    __rmul__ = __mul__

    def __div__(self, other):
        return self._op(operator.div, other)

    def __floordiv__(self, other):
        return self._op(operator.floordiv, other)

    def __truediv__(self, other):
        return self._op(operator.truediv, other)

    def __rdiv__(self, other):
        return self._cast(other)._op(operator.div, self)

    def __rfloordiv__(self, other):
        return self._cast(other)._op(operator.floordiv, self)

    def __rtruediv__(self, other):
        return self._cast(other)._op(operator.truediv, self)

    def __repr__(self):
        return f"{self.__class__.__name__}({tuple.__repr__(self)})"


def named_simple_array(typename, field_names):
    """Return a subclass of SimpleArray, with named properties.

    This method is to SimpleArray what namedtuple is to tuple.
    It's less sophisticated than namedtuple so some namedtuple
    advanced use cases may not work, but it's good enough for
    our needs in mis_builder, ie referring to subkpi values
    by name.
    """
    props = {
        field_name: property(operator.itemgetter(i))
        for i, field_name in enumerate(field_names)
    }
    return type(typename, (SimpleArray,), props)


if __name__ == "__main__":  # pragma: no cover
    import doctest

    doctest.testmod()
