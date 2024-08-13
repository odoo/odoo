import typing


class NewId:
    """ Pseudo-ids for new records, encapsulating an optional origin id (actual
        record id) and an optional reference (any value).
    """
    __slots__ = 'origin', 'ref' , '__hash'

    def __init__(self, origin=None, ref=None):
        self.origin = origin
        self.ref = ref
        self.__hash = None

    def __bool__(self):
        return False

    def __eq__(self, other):
        return isinstance(other, NewId) and (
            (self.origin and other.origin and self.origin == other.origin)
            or (self.ref and other.ref and self.ref == other.ref)
        )

    def __hash__(self):
        if self.__hash is None:
            self.__hash = hash(self.origin or self.ref or id(self))
        return self.__hash

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


IdType: typing.TypeAlias = int | NewId
