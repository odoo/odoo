"""
Iteration and record set operations mixin for BaseModel.

This module contains methods for iterating over recordsets, combining them,
and performing set operations (union, intersection, difference).
"""

import typing
import warnings
from collections.abc import Iterator, Reversible
from itertools import batched
from typing import Self

from odoo.libs.constants import PREFETCH_MAX
from odoo.tools import OrderedSet
from odoo.tools.misc import ReversedIterable

from ... import decorators as api
from ..._typing import IdType
from ...primitives import NewId

if typing.TYPE_CHECKING:
    from ...runtime import Environment


class IterationMixin:
    """Mixin providing iteration and set operations for recordsets.

    This mixin contains methods for:
    - Iterating over records (__iter__, __reversed__)
    - Set operations (union, intersection, difference)
    - Comparison operators
    - Container operations (__contains__, __len__, __bool__)
    - Item access (__getitem__, __setitem__)
    """

    __slots__ = ()

    #
    # Instance creation
    #
    # An instance represents an ordered collection of records in a given
    # execution environment. The instance object refers to the environment, and
    # the records themselves are represented by their cache dictionary. The 'id'
    # of each record is found in its corresponding cache dictionary.
    #
    # This design has the following advantages:
    #  - cache access is direct and thus fast;
    #  - one can consider records without an 'id' (see new records);
    #  - the global cache is only an index to "resolve" a record 'id'.
    #

    def __init__(
        self,
        env: Environment,
        ids: tuple[IdType, ...],
        prefetch_ids: Reversible[IdType],
    ):
        """Create a recordset instance.

        :param env: an environment
        :param ids: a tuple of record ids
        :param prefetch_ids: a reversible iterable of record ids (for prefetching)
        """
        self.env = env
        self._ids = ids
        self._prefetch_ids = prefetch_ids

    @api.private
    def browse(self, ids: int | typing.Iterable[IdType] = ()) -> Self:
        """Return a recordset for the ids provided as parameter in the current
        environment.

        .. code-block:: python

            self.browse([7, 18, 12])
            res.partner(7, 18, 12)
        """
        if not ids:
            ids = ()
        elif ids.__class__ is int:
            ids = (ids,)
        elif ids.__class__ is not tuple:
            ids = tuple(ids)
        # Inline object creation — avoids __init__ dispatch overhead.
        rs = object.__new__(self.__class__)
        rs.env = self.env
        rs._ids = ids
        rs._prefetch_ids = ids
        return rs

    #
    # Internal properties, for manipulating the instance's implementation
    #

    @property
    def ids(self) -> list[int]:
        """Return the list of actual record ids corresponding to ``self``."""
        from ...helpers import _origin_ids

        if all(self._ids):
            return list(self._ids)  # already real records
        return list(_origin_ids(self._ids))

    #
    # "Dunder" methods
    #

    def __bool__(self) -> bool:
        """Test whether ``self`` is nonempty."""
        return bool(self._ids)  # fast version of bool(self._ids)

    def __len__(self) -> int:
        """Return the size of ``self``."""
        return len(self._ids)

    def __iter__(self) -> Iterator[Self]:
        """Return an iterator over ``self``."""
        ids = self._ids
        size = len(ids)
        if size <= 1:
            # detect and handle small recordsets (single `1f`)
            # early return if no records and avoid allocation if we have a one
            if size == 1:
                yield self
            return
        # Inline object creation — bypass type.__call__ dispatch chain
        # (type.__call__ → __new__ → __init__) for ~30% faster iteration.
        _new = object.__new__
        cls = self.__class__
        env = self.env
        prefetch_ids = self._prefetch_ids
        if size > PREFETCH_MAX and prefetch_ids is ids:
            for sub_ids in batched(ids, PREFETCH_MAX):
                for id_ in sub_ids:
                    rs = _new(cls)
                    rs.env = env
                    rs._ids = (id_,)
                    rs._prefetch_ids = sub_ids
                    yield rs
        else:
            for id_ in ids:
                rs = _new(cls)
                rs.env = env
                rs._ids = (id_,)
                rs._prefetch_ids = prefetch_ids
                yield rs

    def __reversed__(self) -> Iterator[Self]:
        """Return an reversed iterator over ``self``."""
        # same as __iter__ but reversed
        ids = self._ids
        size = len(ids)
        if size <= 1:
            if size == 1:
                yield self
            return
        _new = object.__new__
        cls = self.__class__
        env = self.env
        prefetch_ids = self._prefetch_ids
        if size > PREFETCH_MAX and prefetch_ids is ids:
            for sub_ids in batched(reversed(ids), PREFETCH_MAX):
                for id_ in sub_ids:
                    rs = _new(cls)
                    rs.env = env
                    rs._ids = (id_,)
                    rs._prefetch_ids = sub_ids
                    yield rs
        else:
            prefetch_ids = ReversedIterable(prefetch_ids)
            for id_ in reversed(ids):
                rs = _new(cls)
                rs.env = env
                rs._ids = (id_,)
                rs._prefetch_ids = prefetch_ids
                yield rs

    def __contains__(self, item) -> bool:
        """Test whether ``item`` (record or field name) is an element of ``self``.

        In the first case, the test is fully equivalent to::

            any(item == record for record in self)

        In the second case, we check whether the model has a field named
        ``item``.
        """
        try:
            if self._name == item._name:
                return len(item) == 1 and item.id in self._ids
            raise TypeError(f"inconsistent models in: {item} in {self}")
        except AttributeError:
            if isinstance(item, str):
                return item in self._fields
            raise TypeError(f"unsupported operand types in: {item!r} in {self}")

    def __add__(self, other) -> Self:
        """Return the concatenation of two recordsets."""
        return self.concat(other)

    @api.private
    def concat(self, *args: Self) -> Self:
        """Return the concatenation of ``self`` with all the arguments (in
        linear time complexity).
        """
        ids = list(self._ids)
        for arg in args:
            try:
                if arg._name != self._name:
                    raise TypeError(f"inconsistent models in: {self} + {arg}")
                ids.extend(arg._ids)
            except AttributeError:
                raise TypeError(f"unsupported operand types in: {self} + {arg!r}")
        return self.browse(ids)

    def __sub__(self, other) -> Self:
        """Return the recordset of all the records in ``self`` that are not in
        ``other``. Note that recordset order is preserved.
        """
        try:
            if self._name != other._name:
                raise TypeError(f"inconsistent models in: {self} - {other}")
            # fast paths: empty operands avoid set creation
            if not other._ids or not self._ids:
                return self
            other_ids = set(other._ids)
            return self.browse(id_ for id_ in self._ids if id_ not in other_ids)
        except AttributeError:
            raise TypeError(f"unsupported operand types in: {self} - {other!r}")

    def __and__(self, other) -> Self:
        """Return the intersection of two recordsets.
        Note that first occurrence order is preserved.
        """
        try:
            if self._name != other._name:
                raise TypeError(f"inconsistent models in: {self} & {other}")
            # fast paths: empty operands
            if not self._ids or not other._ids:
                return self.browse()
            other_ids = set(other._ids)
            return self.browse(OrderedSet(id_ for id_ in self._ids if id_ in other_ids))
        except AttributeError:
            raise TypeError(f"unsupported operand types in: {self} & {other!r}")

    def __or__(self, other) -> Self:
        """Return the union of two recordsets.
        Note that first occurrence order is preserved.
        """
        return self.union(other)

    @api.private
    def union(self, *args: Self) -> Self:
        """Return the union of ``self`` with all the arguments (in linear time
        complexity, with first occurrence order preserved).
        """
        # fast path: single argument union (the common case for `self | other`)
        if len(args) == 1:
            arg = args[0]
            try:
                if arg._name != self._name:
                    raise TypeError(f"inconsistent models in: {self} | {arg}")
            except AttributeError:
                raise TypeError(f"unsupported operand types in: {self} | {arg!r}")
            if not arg._ids:
                return self
            if not self._ids:
                # Must use self.browse() to preserve self's env; returning
                # arg directly would leak arg's env (e.g. different company
                # context), breaking company-dependent field resolution.
                return self.browse(arg._ids)
            return self.browse(OrderedSet(self._ids + arg._ids))

        ids = list(self._ids)
        for arg in args:
            try:
                if arg._name != self._name:
                    raise TypeError(f"inconsistent models in: {self} | {arg}")
                ids.extend(arg._ids)
            except AttributeError:
                raise TypeError(f"unsupported operand types in: {self} | {arg!r}")
        return self.browse(OrderedSet(ids))

    def __eq__(self, other):
        """Test whether two recordsets are equivalent (up to reordering)."""
        try:
            if self._name != other._name:
                return False
            s_ids = self._ids
            o_ids = other._ids
            # fast paths: identity, equal tuples, singletons
            if s_ids is o_ids or s_ids == o_ids:
                return True
            # different lengths → cannot be equal (avoids O(n) set creation)
            if len(s_ids) != len(o_ids):
                return False
            return set(s_ids) == set(o_ids)
        except AttributeError:
            if other:
                warnings.warn(
                    f"unsupported operand type(s) for \"==\": '{self._name}()' == '{other!r}'",
                    stacklevel=2,
                )
        return NotImplemented

    def __lt__(self, other):
        try:
            if self._name == other._name:
                # proper subset requires strictly fewer elements
                if len(self._ids) >= len(other._ids):
                    return False
                return set(self._ids) < set(other._ids)
        except AttributeError:
            pass
        return NotImplemented

    def __le__(self, other):
        try:
            if self._name == other._name:
                # these are much cheaper checks than a proper subset check, so
                # optimise for checking if a null or singleton are subsets of a
                # recordset
                if not self or self in other:
                    return True
                return set(self._ids) <= set(other._ids)
        except AttributeError:
            pass
        return NotImplemented

    def __gt__(self, other):
        try:
            if self._name == other._name:
                # proper superset requires strictly more elements
                if len(self._ids) <= len(other._ids):
                    return False
                return set(self._ids) > set(other._ids)
        except AttributeError:
            pass
        return NotImplemented

    def __ge__(self, other):
        try:
            if self._name == other._name:
                if not other or other in self:
                    return True
                return set(self._ids) >= set(other._ids)
        except AttributeError:
            pass
        return NotImplemented

    def __int__(self) -> int:
        return self.id or 0

    def __repr__(self):
        return f"{self._name}{self._ids!r}"

    def __hash__(self):
        return hash((self._name, frozenset(self._ids)))

    def __deepcopy__(self, memo):
        return self

    @typing.overload
    def __getitem__(self, key: int | slice) -> Self: ...

    @typing.overload
    def __getitem__(self, key: str) -> typing.Any: ...

    def __getitem__(self, key):
        """If ``key`` is an integer or a slice, return the corresponding record
        selection as an instance (attached to ``self.env``).
        Otherwise read the field ``key`` of the first record in ``self``.

        Examples::

            inst = model.search(dom)    # inst is a recordset
            r4 = inst[3]                # fourth record in inst
            rs = inst[10:20]            # subset of inst
            nm = rs['name']             # name of first record in inst
        """
        if isinstance(key, str):
            # important: one must call the field's getter
            return self._fields[key].__get__(self)
        elif isinstance(key, slice):
            ids = self._ids[key]
            rs = object.__new__(self.__class__)
            rs.env = self.env
            rs._ids = ids
            rs._prefetch_ids = ids
            return rs
        else:
            ids = (self._ids[key],)
            rs = object.__new__(self.__class__)
            rs.env = self.env
            rs._ids = ids
            rs._prefetch_ids = ids
            return rs

    def __setitem__(self, key: str, value: typing.Any):
        """Assign the field ``key`` to ``value`` in record ``self``."""
        # important: one must call the field's setter
        return self._fields[key].__set__(self, value)
