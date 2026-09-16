import typing
import warnings
from itertools import batched
from typing import Self

from odoo.libs.accel import origin_ids as _origin_ids
from odoo.libs.debug_log import DebugLog
from odoo.tools import OrderedSet
from odoo.tools.misc import ReversedIterable

from ... import decorators as api
from ...primitives import PREFETCH_MAX
from ._model_stubs import _ModelStubs

if typing.TYPE_CHECKING:
    from collections.abc import Iterator, Reversible

    from ..._typing import BaseModel, IdType
    from ...runtime import Environment

_debug = DebugLog(__name__)


class IterationMixin(_ModelStubs):
    __slots__ = ()

    def __init__(
        self,
        env: Environment,
        ids: tuple[IdType, ...],
        prefetch_ids: Reversible[IdType],
    ):
        self.env = env
        self._ids = ids
        self._prefetch_ids = prefetch_ids

    @classmethod
    def _spawn(
        cls,
        env: Environment,
        ids: tuple[IdType, ...],
        prefetch_ids: Reversible[IdType],
    ) -> Self:
        record = object.__new__(cls)
        record.env = env
        record._ids = ids
        record._prefetch_ids = prefetch_ids
        return record

    @api.private
    def browse(self, ids: int | typing.Iterable[IdType] = ()) -> Self:
        id_tuple: tuple[IdType, ...]
        if not ids:
            id_tuple = ()
        elif ids.__class__ is int:
            id_tuple = (typing.cast("IdType", ids),)
        elif ids.__class__ is tuple:
            id_tuple = typing.cast("tuple[IdType, ...]", ids)
        else:
            id_tuple = tuple(typing.cast("typing.Iterable[IdType]", ids))
        return self._spawn(self.env, id_tuple, id_tuple)

    @property
    def ids(self) -> list[int]:
        if all(self._ids):
            return list(self._ids)
        return list(_origin_ids(self._ids))

    def _narrow(self, ids: typing.Iterable[IdType]) -> Self:
        return self._spawn(self.env, tuple(ids), self._prefetch_ids)

    @property
    def _new_records(self) -> Self:
        return self.browse([id_ for id_ in self._ids if not id_])

    def __bool__(self) -> bool:
        return bool(self._ids)

    def __len__(self) -> int:
        return len(self._ids)

    def __iter__(self) -> Iterator[Self]:
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
            _debug.perf.count(
                "iteration.prefetch_batched",
                model=self._name,
                records=size,
                batch=PREFETCH_MAX,
            )
            for sub_ids in batched(ids, PREFETCH_MAX, strict=False):
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

    # __iter__ repeated with the ids reversed, on purpose: the ORM's hottest
    # loop, and a shared spawning generator reached through `yield from` costs
    # 7-12 % on 5, 50 and 5,000 records (measured 2026-09-15)
    def __reversed__(self) -> Iterator[Self]:
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
            _debug.perf.count(
                "iteration.prefetch_batched",
                model=self._name,
                records=size,
                batch=PREFETCH_MAX,
                reversed=True,
            )
            for sub_ids in batched(reversed(ids), PREFETCH_MAX, strict=False):
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
        try:
            if self._name == item._name:
                return len(item) == 1 and item.id in self._ids
            raise TypeError(f"inconsistent models in: {item} in {self}")
        except AttributeError:
            if isinstance(item, str):
                return item in self._fields
            raise TypeError(
                f"unsupported operand types in: {item!r} in {self}"
            ) from None

    @api.private
    def index(self, item, start: int = 0, stop: int | None = None) -> int:
        try:
            if self._name != item._name:
                raise TypeError(f"inconsistent models in: {item}.index({self})")
        except AttributeError:
            raise TypeError(
                f"unsupported operand types in: {item!r}.index({self})"
            ) from None
        if len(item) != 1:
            raise ValueError(f"index requires a singleton, got {len(item)} records")
        target = item.id
        ids = self._ids
        n = len(ids)
        if start < 0:
            start = max(0, n + start)
        else:
            start = min(start, n)
        if stop is None:
            stop = n
        elif stop < 0:
            stop = max(0, n + stop)
        else:
            stop = min(stop, n)
        for i in range(start, stop):
            if ids[i] == target:
                return i
        raise ValueError(f"{item} is not in recordset")

    @api.private
    def count(self, item) -> int:
        try:
            if self._name != item._name:
                raise TypeError(f"inconsistent models in: {item}.count({self})")
        except AttributeError:
            raise TypeError(
                f"unsupported operand types in: {item!r}.count({self})"
            ) from None
        if len(item) != 1:
            raise ValueError(f"count requires a singleton, got {len(item)} records")
        target = item.id
        return sum(1 for id_ in self._ids if id_ == target)

    def __add__(self, other) -> Self:
        return self.concat(other)

    @api.private
    def concat(self, *args: Self) -> Self:
        ids = list(self._ids)
        for arg in args:
            try:
                if arg._name != self._name:
                    raise TypeError(f"inconsistent models in: {self} + {arg}")
                ids.extend(arg._ids)
            except AttributeError:
                raise TypeError(
                    f"unsupported operand types in: {self} + {arg!r}"
                ) from None
        return self.browse(ids)

    def __sub__(self, other) -> Self:
        try:
            if self._name != other._name:
                raise TypeError(f"inconsistent models in: {self} - {other}")
            if not other._ids or not self._ids:
                return self
            other_ids = set(other._ids)
            return self._narrow(id_ for id_ in self._ids if id_ not in other_ids)
        except AttributeError:
            raise TypeError(
                f"unsupported operand types in: {self} - {other!r}"
            ) from None

    def __and__(self, other) -> Self:
        try:
            if self._name != other._name:
                raise TypeError(f"inconsistent models in: {self} & {other}")
            if not self._ids or not other._ids:
                return self.browse()
            other_ids = set(other._ids)
            return self._narrow(
                OrderedSet(id_ for id_ in self._ids if id_ in other_ids)
            )
        except AttributeError:
            raise TypeError(
                f"unsupported operand types in: {self} & {other!r}"
            ) from None

    def __or__(self, other) -> Self:
        return self.union(other)

    @api.private
    def union(self, *args: Self) -> Self:
        if len(args) == 1:
            arg = args[0]
            try:
                if arg._name != self._name:
                    raise TypeError(f"inconsistent models in: {self} | {arg}")
            except AttributeError:
                raise TypeError(
                    f"unsupported operand types in: {self} | {arg!r}"
                ) from None
            if not arg._ids:
                if len(self._ids) == len(set(self._ids)):
                    return self
                return self.browse(OrderedSet(self._ids))
            if not self._ids:
                return self.browse(OrderedSet(arg._ids))
            return self.browse(OrderedSet(self._ids + arg._ids))

        ids = list(self._ids)
        for arg in args:
            try:
                if arg._name != self._name:
                    raise TypeError(f"inconsistent models in: {self} | {arg}")
                ids.extend(arg._ids)
            except AttributeError:
                raise TypeError(
                    f"unsupported operand types in: {self} | {arg!r}"
                ) from None
        return self.browse(OrderedSet(ids))

    def __eq__(self, other: object) -> bool:
        peer: typing.Any = other
        try:
            if self._name != peer._name:
                return False
            s_ids = self._ids
            o_ids = peer._ids
            if s_ids is o_ids or s_ids == o_ids:
                return True
            return set(s_ids) == set(o_ids)
        except AttributeError:
            if peer:
                _debug.logic(
                    "iteration.eq_unsupported_operand",
                    model=self._name,
                    other_type=type(peer).__name__,
                )
                warnings.warn(
                    f"unsupported operand type(s) for \"==\": '{self._name}()' == '{peer!r}'",
                    stacklevel=2,
                )
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        peer: typing.Any = other
        try:
            if self._name == peer._name:
                return set(self._ids) < set(peer._ids)
        except AttributeError:
            pass
        return NotImplemented

    def __le__(self, other: object) -> bool:
        peer: typing.Any = other
        try:
            if self._name == peer._name:
                if not self or self in peer:
                    return True
                return set(self._ids) <= set(peer._ids)
        except AttributeError:
            pass
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        peer: typing.Any = other
        try:
            if self._name == peer._name:
                return set(self._ids) > set(peer._ids)
        except AttributeError:
            pass
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        peer: typing.Any = other
        try:
            if self._name == peer._name:
                if not peer or peer in self:
                    return True
                return set(self._ids) >= set(peer._ids)
        except AttributeError:
            pass
        return NotImplemented

    def __int__(self) -> int:
        return self.id or 0

    def __repr__(self) -> str:
        return f"{self._name}{self._ids!r}"

    def __hash__(self) -> int:
        return hash((self._name, frozenset(self._ids)))

    def __deepcopy__(self, memo: dict) -> Self:
        return self

    @typing.overload
    def __getitem__(self, key: int | slice) -> Self: ...

    @typing.overload
    def __getitem__(self, key: str) -> typing.Any: ...

    def __getitem__(self, key: int | slice | str) -> Self | typing.Any:
        if isinstance(key, str):
            return self._fields[key].__get__(self)
        elif isinstance(key, slice):
            ids = self._ids[key]
            return self._spawn(self.env, ids, ids)
        else:
            ids = (self._ids[key],)
            return self._spawn(self.env, ids, self._prefetch_ids)

    def __setitem__(self, key: str, value: typing.Any):
        return self._fields[key].__set__(typing.cast("BaseModel", self), value)
