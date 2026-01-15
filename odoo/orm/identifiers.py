import functools
import typing


@functools.total_ordering
class NewId:
    """ Pseudo-ids for new records, encapsulating an optional origin id (actual
        record id) and an optional reference (any value).
    """
    __slots__ = ('origin', 'ref', '__hash')  # noqa: RUF023

    def __init__(self, origin=None, ref=None):
        self.origin = origin
        self.ref = ref
        self.__hash = hash(origin or ref or id(self))

    def __bool__(self):
        return False

    def __eq__(self, other):
        return isinstance(other, NewId) and (
            (self.origin and other.origin and self.origin == other.origin)
            or (self.ref and other.ref and self.ref == other.ref)
        )

    def __hash__(self):
        return self.__hash

    def __lt__(self, other):
        if isinstance(other, NewId):
            other = other.origin
            if other is None:
                return other > self.origin if self.origin else False
        if isinstance(other, int):
            return bool(self.origin) and self.origin < other
        return NotImplemented

    def __repr__(self):
        return (
            "<NewId origin=%r>" % self.origin if self.origin else
            "<NewId ref=%r>" % self.ref if self.ref else
            "<NewId 0x%x>" % id(self)
        )

    def __str__(self):
        if self.origin or self.ref:
            id_part = repr(self.origin or self.ref)
        else:
            id_part = hex(id(self))
        return "NewId_%s" % id_part


# By default, in the ORM we initialize it as an int, but any type should work.
# However, and some parts of the ORM may assume it is an integer.
# Non-exhaustive list: relational fields, references, hierarchies, etc.
IdType: typing.TypeAlias = int | NewId | str
