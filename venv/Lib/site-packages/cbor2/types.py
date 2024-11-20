from collections import namedtuple
from collections.abc import Mapping
from functools import total_ordering
from reprlib import recursive_repr


class CBORError(Exception):
    "Base class for errors that occur during CBOR encoding or decoding."


class CBOREncodeError(CBORError):
    "Raised for exceptions occurring during CBOR encoding."


class CBOREncodeTypeError(CBOREncodeError, TypeError):
    "Raised when attempting to encode a type that cannot be serialized."


class CBOREncodeValueError(CBOREncodeError, ValueError):
    "Raised when the CBOR encoder encounters an invalid value."


class CBORDecodeError(CBORError):
    "Raised for exceptions occurring during CBOR decoding."


class CBORDecodeValueError(CBORDecodeError, ValueError):
    "Raised when the CBOR stream being decoded contains an invalid value."


class CBORDecodeEOF(CBORDecodeError, EOFError):
    "Raised when decoding unexpectedly reaches EOF."


@total_ordering
class CBORTag:
    """
    Represents a CBOR semantic tag.

    :param int tag: tag number
    :param value: encapsulated value (any object)
    """

    __slots__ = 'tag', 'value'

    def __init__(self, tag, value):
        if not isinstance(tag, int) or tag not in range(2**64):
            raise TypeError('CBORTag tags must be positive integers less than 2**64')
        self.tag = tag
        self.value = value

    def __eq__(self, other):
        if isinstance(other, CBORTag):
            return (self.tag, self.value) == (other.tag, other.value)
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, CBORTag):
            return (self.tag, self.value) <= (other.tag, other.value)
        return NotImplemented

    @recursive_repr()
    def __repr__(self):
        return 'CBORTag({self.tag}, {self.value!r})'.format(self=self)


class CBORSimpleValue(namedtuple('CBORSimpleValue', ['value'])):
    """
    Represents a CBOR "simple value".

    :param int value: the value (0-255)
    """

    __slots__ = ()
    __hash__ = namedtuple.__hash__

    def __new__(cls, value):
        if value < 0 or value > 255:
            raise TypeError('simple value out of range (0..255)')
        return super(CBORSimpleValue, cls).__new__(cls, value)

    def __eq__(self, other):
        if isinstance(other, int):
            return self.value == other
        return super(CBORSimpleValue, self).__eq__(other)

    def __ne__(self, other):
        if isinstance(other, int):
            return self.value != other
        return super(CBORSimpleValue, self).__ne__(other)

    def __lt__(self, other):
        if isinstance(other, int):
            return self.value < other
        return super(CBORSimpleValue, self).__lt__(other)

    def __le__(self, other):
        if isinstance(other, int):
            return self.value <= other
        return super(CBORSimpleValue, self).__le__(other)

    def __ge__(self, other):
        if isinstance(other, int):
            return self.value >= other
        return super(CBORSimpleValue, self).__ge__(other)

    def __gt__(self, other):
        if isinstance(other, int):
            return self.value > other
        return super(CBORSimpleValue, self).__gt__(other)


class FrozenDict(Mapping):
    """
    A hashable, immutable mapping type.

    The arguments to ``FrozenDict`` are processed just like those to ``dict``.
    """

    def __init__(self, *args, **kwargs):
        self._d = dict(*args, **kwargs)
        self._hash = None

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __getitem__(self, key):
        return self._d[key]

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self._d)

    def __hash__(self):
        if self._hash is None:
            self._hash = hash((frozenset(self), frozenset(self.values())))
        return self._hash


class UndefinedType:
    __slots__ = ()

    def __new__(cls):
        try:
            return undefined
        except NameError:
            return super(UndefinedType, cls).__new__(cls)

    def __repr__(self):
        return "undefined"

    def __bool__(self):
        return False
    __nonzero__ = __bool__  # Py2.7 compat


class BreakMarkerType:
    __slots__ = ()

    def __new__(cls):
        try:
            return break_marker
        except NameError:
            return super(BreakMarkerType, cls).__new__(cls)

    def __repr__(self):
        return "break_marker"

    def __bool__(self):
        return True
    __nonzero__ = __bool__  # Py2.7 compat


#: Represents the "undefined" value.
undefined = UndefinedType()
break_marker = BreakMarkerType()
