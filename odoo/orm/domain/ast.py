import collections
import contextlib
import datetime
import decimal
import enum
import functools
import itertools
import logging
import operator
import types
import typing
import warnings

from odoo.exceptions import UserError
from odoo.libs.collections import FrozenOrderedSet
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, OrderedSet, Query, classproperty, frozendict

from .._recordset import is_recordset
from ..parsing import parse_field_expr
from ..primitives import COLLECTION_TYPES, NewId
from .constants import (
    ACCEPTED_CONDITION_OPERATORS,
    FALSE_LEAF,
    INTERNAL_CONDITION_OPERATORS,
    INVERSE_INEQUALITY,
    INVERSE_OPERATOR,
    NEGATIVE_CONDITION_OPERATORS,
    STANDARD_CONDITION_OPERATORS,
    SUBDOMAIN_OPERATORS,
    SUBDOMAIN_OR_IN_OPERATORS,
    TRUE_LEAF,
)

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from ..fields import Field
    from ..models import BaseModel

    M = typing.TypeVar("M", bound=BaseModel)

_logger = logging.getLogger("odoo.domains")
_debug = DebugLog(__name__)


def _parse_prefix_domain(arg, internal: bool) -> Domain:
    stack: list[Domain] = []
    items = list(reversed(arg))
    total = len(items)
    index = 0
    try:
        while index < total:
            item = items[index]
            if isinstance(item, (tuple, list)) and len(item) == 3:
                stack.append(_leaf_to_domain(item, internal))
                index += 1
            elif item in (DomainAnd.OPERATOR, DomainOr.OPERATOR):
                cls = DomainAnd if item == DomainAnd.OPERATOR else DomainOr
                run = index
                while run < total and items[run] == item:
                    run += 1
                operands = [stack.pop() for _ in range(run - index + 1)]
                stack.append(cls.apply(operands))
                index = run
            elif item == DomainNot.OPERATOR:
                stack.append(~stack.pop())
                index += 1
            elif isinstance(item, Domain):
                stack.append(item)
                index += 1
            else:
                raise ValueError(f"Domain() invalid item in domain: {item!r}")
        if len(stack) == 1:
            return stack[0]
        return Domain.AND(reversed(stack))
    except IndexError:
        raise ValueError(f"Domain() malformed domain {arg!r}") from None


class OptimizationLevel(enum.IntEnum):
    NONE = 0
    BASIC = enum.auto()
    DYNAMIC_VALUES = enum.auto()
    FULL = enum.auto()

    @functools.cached_property
    def next_level(self) -> OptimizationLevel:
        if self is OptimizationLevel.FULL:
            raise ValueError("FULL level is the last one")
        return OptimizationLevel(int(self) + 1)


MAX_OPTIMIZE_ITERATIONS = 1000

MAX_DOMAIN_NESTING = 100


def _is_comparand_equal(left: typing.Any, right: typing.Any) -> bool:
    if left.__class__ in (list, tuple, set, frozenset, OrderedSet, FrozenOrderedSet):
        if len(left) != len(right):
            return False
        try:
            return {(type(v), v) for v in left} == {(type(v), v) for v in right}
        except TypeError:
            return left == right
    return left == right


def _thaw_comparand(operator: str, value: typing.Any) -> typing.Any:
    if isinstance(value, Domain):
        return list(value)
    if not isinstance(value, COLLECTION_TYPES):
        return value
    if operator not in SUBDOMAIN_OPERATORS:
        return list(value)
    return [_thaw_condition(item) for item in value]


def _thaw_condition(item: typing.Any) -> typing.Any:
    if isinstance(item, tuple) and len(item) == 3 and isinstance(item[0], str):
        field_expr, operator, value = item
        return (field_expr, operator, _thaw_comparand(operator, value))
    return item


def _freeze_comparand(value: typing.Any, path: set[int] | None = None) -> typing.Any:
    if not isinstance(value, (list, tuple, set, frozenset, dict, OrderedSet)):
        return value
    if path is None:
        path = set()
    marker = id(value)
    if marker in path:
        raise ValueError("Cyclic domain operand")
    if len(path) >= MAX_DOMAIN_NESTING:
        raise ValueError("Domain nesting too deep to freeze")
    path.add(marker)
    try:
        if isinstance(value, dict):
            return frozendict(
                (key, _freeze_comparand(item, path)) for key, item in value.items()
            )
        items = (_freeze_comparand(item, path) for item in value)
        if isinstance(value, OrderedSet):
            return FrozenOrderedSet(items)
        if isinstance(value, (set, frozenset)):
            return frozenset(items)
        return tuple(items)
    finally:
        path.remove(marker)


class DomainOptimizationError(ValueError):
    pass


@contextlib.contextmanager
def _recursion_error_as_value_error():
    try:
        yield
    except RecursionError:
        _debug.logic("domain.optimize.recursion_exhausted")
        raise ValueError(
            "Domain nesting too deep to optimize: combined n-ary and 'any' "
            "nesting exhausts the evaluation stack"
        ) from None


def _check_depth(depth: int) -> int:
    if depth > MAX_DOMAIN_NESTING:
        raise ValueError(
            f"Domain nesting too deep (>{MAX_DOMAIN_NESTING} levels); refusing "
            f"to build it to avoid a RecursionError during evaluation"
        )
    return depth


def _check_subdomain_nesting(value: object, max_depth: int) -> None:
    stack: list[tuple[object, int]] = [(value, 1)]
    while stack:
        node, depth = stack.pop()
        if depth > max_depth:
            raise ValueError(
                f"Domain nesting too deep (>{max_depth} levels); refusing to "
                f"build it to avoid a RecursionError during evaluation"
            )
        if not isinstance(node, (list, tuple)):
            continue
        child_depth = depth + 1
        stack.extend(
            (item[2], child_depth)
            for item in node
            if isinstance(item, (list, tuple))
            and len(item) == 3
            and isinstance(item[1], str)
            and item[1].lower() in SUBDOMAIN_OPERATORS
            and isinstance(item[2], (list, tuple))
        )


if typing.TYPE_CHECKING:
    ConditionOptimization = Callable[["DomainCondition", "BaseModel"], "Domain"]
    MergeOptimization = Callable[
        [type["DomainNary"], list["Domain"], "BaseModel"], list["Domain"]
    ]

_OPTIMIZATIONS_FOR: dict[OptimizationLevel, dict[str, list]] = {
    level: collections.defaultdict(list)
    for level in OptimizationLevel
    if level != OptimizationLevel.NONE
}
_OPTIMIZATION_KEY_KIND: dict[str, str] = {}
_MERGE_OPTIMIZATIONS: list = []


_CONSTANT_TIEBREAK: tuple[int, typing.Any] = (2, "")


def _get_nary_value_tiebreak(value: typing.Any) -> tuple[int, typing.Any]:
    if isinstance(value, str):
        return (0, value)
    if isinstance(value, (int, float)):
        return (1, value)
    if isinstance(value, datetime.datetime):
        return (3, value)
    if isinstance(value, datetime.date):
        return (4, value)
    if isinstance(value, decimal.Decimal):
        return (5, value)
    return _CONSTANT_TIEBREAK


def _get_nary_subtree_tiebreak(domain: Domain) -> tuple[int, typing.Any]:
    return (2, repr(list(domain)))


def _get_nary_sort_key(
    domain: Domain,
) -> tuple[str, str, str, tuple[int, typing.Any]]:
    if isinstance(domain, DomainCondition):
        op = domain.operator
        positive_op = NEGATIVE_CONDITION_OPERATORS.get(op, op)
        if positive_op == "in":
            order = "0in"
        elif positive_op == "any":
            order = "1any"
        elif positive_op == "any!":
            order = "2any"
        elif positive_op.endswith("like") or positive_op == "=~":
            order = "like"
        else:
            order = positive_op
        return domain.field_expr, order, op, _get_nary_value_tiebreak(domain.value)
    elif hasattr(domain, "OPERATOR") and isinstance(domain.OPERATOR, str):
        return "~", "", domain.OPERATOR, _get_nary_subtree_tiebreak(domain)
    else:
        return "~", "~", domain.__class__.__name__, _get_nary_subtree_tiebreak(domain)


def _leaf_to_domain(item: tuple | list, internal: bool) -> Domain:
    if not isinstance(item[1], str):
        raise ValueError(f"Domain() invalid item in domain: {item!r}")
    op = item[1].lower()
    if internal:
        if op in SUBDOMAIN_OPERATORS and isinstance(item[2], (list, tuple)):
            item = (item[0], item[1], Domain(item[2], internal=True))
    elif op in INTERNAL_CONDITION_OPERATORS:
        raise ValueError(f"Domain() invalid item in domain: {item!r}")
    return Domain(*item)


class Domain:
    __slots__ = ("_depth", "_opt")
    _depth: int
    _opt: tuple[OptimizationLevel, str | None]

    @property
    def _opt_level(self) -> OptimizationLevel:
        return self._opt[0]

    @property
    def _opt_model_name(self) -> str | None:
        return self._opt[1]

    def __new__(cls, *args: object, internal: bool = False) -> Domain:  # noqa: PYI034  can return an existing Domain, _TRUE_DOMAIN, _FALSE_DOMAIN or a DomainCondition, not always an instance of cls, so Self would be wrong
        if len(args) > 1:
            if isinstance(field_expr := args[0], str):
                _first, operator, value = args
                return DomainCondition(
                    field_expr, typing.cast("str", operator), value
                ).normalize()
            if args == TRUE_LEAF:
                return _TRUE_DOMAIN
            if args == FALSE_LEAF:
                return _FALSE_DOMAIN
            raise TypeError(f"Domain() invalid arguments: {args!r}")

        arg = args[0]
        if isinstance(arg, Domain):
            return arg
        if arg is True or arg in ([], ()):
            return _TRUE_DOMAIN
        if arg is False:
            return _FALSE_DOMAIN
        if arg is NotImplemented:
            raise NotImplementedError

        if not isinstance(arg, (list, tuple)):
            raise TypeError(f"Domain() invalid argument type for domain: {arg!r}")
        if internal:
            _check_subdomain_nesting(arg, MAX_DOMAIN_NESTING)
        if len(arg) == 1:
            item = arg[0]
            if isinstance(item, (tuple, list)) and len(item) == 3:
                return _leaf_to_domain(item, internal)
            if isinstance(item, Domain):
                return item
        return _parse_prefix_domain(arg, internal)

    @classproperty
    def TRUE(self) -> Domain:
        return _TRUE_DOMAIN

    @classproperty
    def FALSE(self) -> Domain:
        return _FALSE_DOMAIN

    NEGATIVE_OPERATORS = types.MappingProxyType(NEGATIVE_CONDITION_OPERATORS)

    @staticmethod
    def custom(
        *,
        to_sql: Callable[[BaseModel, str, Query], SQL],
        predicate: Callable[[BaseModel], bool] | None = None,
    ) -> DomainCustom:
        return DomainCustom(to_sql, predicate)

    @staticmethod
    def AND(items: Iterable[object]) -> Domain:
        return DomainAnd.apply(Domain(item) for item in items)

    @staticmethod
    def OR(items: Iterable[object]) -> Domain:
        return DomainOr.apply(Domain(item) for item in items)

    def __setattr__(self, name: str, value: object) -> None:
        msg = "Domain objects are immutable"
        raise TypeError(msg)

    def __delattr__(self, name: str) -> None:
        msg = "Domain objects are immutable"
        raise TypeError(msg)

    def __and__(self, other: object) -> Domain:
        if isinstance(other, Domain):
            if isinstance(other, DomainBool):
                return self if other.value else other
            return DomainAnd.apply([self, other])
        return NotImplemented

    def __or__(self, other: object) -> Domain:
        if isinstance(other, Domain):
            if isinstance(other, DomainBool):
                return other if other.value else self
            return DomainOr.apply([self, other])
        return NotImplemented

    def __invert__(self) -> Domain:
        return DomainNot(self)

    def _negate(self, model: BaseModel) -> Domain:
        return ~self

    def __add__(self, other: object) -> Domain | list[object]:
        if isinstance(other, Domain):
            warnings.warn(
                "Domain + Domain is deprecated, use Domain & Domain (AND) "
                "or Domain | Domain (OR) instead",
                DeprecationWarning,
                stacklevel=2,
            )
            return self & other
        if not isinstance(other, list):
            msg = "Domain() can concatenate only lists"
            raise TypeError(msg)
        warnings.warn(
            "Domain + list is deprecated, convert the list to a Domain first",
            DeprecationWarning,
            stacklevel=2,
        )
        return list(self) + other

    def __radd__(self, other: list[object]) -> list[object]:
        warnings.warn(
            "list + Domain is deprecated, convert the list to a Domain first",
            DeprecationWarning,
            stacklevel=2,
        )
        return other + list(self)

    def __bool__(self) -> bool:
        return not self.is_true()

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError

    def __iter__(self) -> typing.Iterator[object]:
        yield from ()
        raise NotImplementedError

    def __reversed__(self) -> typing.Iterator[object]:
        return reversed(list(self))

    def __repr__(self) -> str:
        return repr(list(self))

    def is_true(self) -> bool:
        return False

    def is_false(self) -> bool:
        return False

    def iter_conditions(self) -> typing.Iterator[DomainCondition]:
        yield from ()

    def map_conditions(self, function: Callable[[DomainCondition], Domain]) -> Domain:
        return self

    def check(self, model: BaseModel) -> None:
        with _recursion_error_as_value_error():
            self._optimize(model, OptimizationLevel.FULL)

    def _as_predicate(self, records: M) -> Callable[[M], bool]:
        raise NotImplementedError

    def _predicate_optimized(self, records: BaseModel) -> Domain | None:
        opt_level, opt_model = self._opt
        if opt_level >= OptimizationLevel.DYNAMIC_VALUES and (
            opt_model is None or opt_model == records._name
        ):
            return None
        with _recursion_error_as_value_error():
            return self._optimize(records, OptimizationLevel.DYNAMIC_VALUES)

    def optimize(self, model: BaseModel) -> Domain:
        with _recursion_error_as_value_error():
            return self._optimize(model, OptimizationLevel.BASIC)

    def optimize_full(self, model: BaseModel) -> Domain:
        with _recursion_error_as_value_error():
            return self._optimize(model, OptimizationLevel.FULL)

    @typing.final
    def _optimize(self, model: BaseModel, level: OptimizationLevel) -> Domain:
        model_name = model._name
        opt_level, opt_model = self._opt
        if opt_model == model_name and opt_level >= level:
            return self
        if opt_model is not None and opt_model != model_name:
            _debug.logic(
                "domain.optimize.model_changed",
                model=model_name,
                previous_model=opt_model,
            )
            domain = self._reset_opt_copy()
        else:
            domain = self
        count = 0
        while domain._opt[0] < level:
            if (count := count + 1) > MAX_OPTIMIZE_ITERATIONS:
                raise DomainOptimizationError(
                    f"Domain.optimize did not converge for model "
                    f"{model_name!r} after {MAX_OPTIMIZE_ITERATIONS} iterations. "
                    f"This is an optimizer defect, not a malformed domain: two "
                    f"registered optimizations are most likely rewriting each "
                    f"other. Domain: {self!r}"
                )
            next_level = domain._opt[0].next_level
            previous, domain = domain, domain._optimize_step(model, next_level)
            if domain == previous and domain._opt[0] < next_level:
                object.__setattr__(domain, "_opt", (next_level, model_name))
        if _debug.perf.enabled and count > 4:
            _debug.perf.count(
                "domain.optimize.iterations",
                model=model_name,
                level=level.name,
                iterations=count,
                conditions=sum(1 for _condition in domain.iter_conditions()),
                head=next(
                    (condition.field_expr for condition in domain.iter_conditions()),
                    None,
                ),
            )
        return domain

    def _reset_opt_copy(self) -> Domain:
        source = getattr(self, "_predicate_fallback", None) or self
        missing = object()
        clone = object.__new__(type(source))
        for klass in type(source).__mro__:
            for slot in getattr(klass, "__slots__", ()):
                if slot in ("_opt", "_field_instance", "_predicate_fallback"):
                    continue
                value = getattr(source, slot, missing)
                if value is not missing:
                    object.__setattr__(clone, slot, value)
        object.__setattr__(clone, "_opt", (OptimizationLevel.NONE, None))
        if hasattr(source, "_field_instance"):
            object.__setattr__(clone, "_field_instance", None)
        return clone

    def _optimize_step(self, model: BaseModel, level: OptimizationLevel) -> Domain:
        return self

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        raise NotImplementedError


class DomainBool(Domain):
    __slots__ = ("value",)
    value: bool

    _SQL_TRUE = SQL("TRUE")
    _SQL_FALSE = SQL("FALSE")

    def __new__(cls, value: bool):
        self = object.__new__(cls)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "_depth", 1)
        object.__setattr__(self, "_opt", (OptimizationLevel.FULL, None))
        return self

    def __eq__(self, other: object) -> bool:
        return self is other

    def __hash__(self) -> int:
        return hash(self.value)

    def is_true(self) -> bool:
        return self.value

    def is_false(self) -> bool:
        return not self.value

    def __invert__(self) -> DomainBool:
        return _FALSE_DOMAIN if self.value else _TRUE_DOMAIN

    def __and__(self, other: object) -> Domain:
        if isinstance(other, Domain):
            return other if self.value else self
        return NotImplemented

    def __or__(self, other: object) -> Domain:
        if isinstance(other, Domain):
            return self if self.value else other
        return NotImplemented

    def __iter__(self) -> typing.Iterator[tuple[int, str, int]]:
        yield TRUE_LEAF if self.value else FALSE_LEAF

    def _as_predicate(self, records: BaseModel) -> Callable[[BaseModel], bool]:
        return lambda _: self.value

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        return self._SQL_TRUE if self.value else self._SQL_FALSE


_TRUE_DOMAIN = DomainBool(True)
_FALSE_DOMAIN = DomainBool(False)


class DomainNot(Domain):
    OPERATOR = "!"

    __slots__ = ("_hash", "child")
    _hash: int
    child: Domain

    def __new__(cls, child: Domain):
        self = object.__new__(cls)
        object.__setattr__(self, "child", child)
        object.__setattr__(self, "_depth", _check_depth(child._depth + 1))
        object.__setattr__(self, "_opt", (OptimizationLevel.NONE, None))
        return self

    def __invert__(self) -> Domain:
        return self.child

    def __iter__(self) -> typing.Iterator[object]:
        yield self.OPERATOR
        yield from self.child

    def iter_conditions(self) -> typing.Iterator[DomainCondition]:
        yield from self.child.iter_conditions()

    def map_conditions(self, function: Callable[[DomainCondition], Domain]) -> Domain:
        return ~(self.child.map_conditions(function))

    def _optimize_step(self, model: BaseModel, level: OptimizationLevel) -> Domain:
        return self.child._optimize(model, level)._negate(model)

    def __eq__(self, other: object) -> bool:
        return self is other or (
            isinstance(other, DomainNot) and self.child == other.child
        )

    def __hash__(self) -> int:
        try:
            return self._hash
        except AttributeError:
            h = ~hash(self.child)
            object.__setattr__(self, "_hash", h)
            return h

    def _as_predicate(self, records: BaseModel) -> Callable[[BaseModel], bool]:
        predicate = self.child._as_predicate(records)
        return lambda rec: not predicate(rec)

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        condition = self.child._to_sql(model, alias, query)
        return SQL("(%s) IS NOT TRUE", condition)


class DomainNary(Domain):
    OPERATOR: str
    OPERATOR_SQL: SQL = SQL(" ??? ")
    ZERO: DomainBool = _FALSE_DOMAIN

    __slots__ = ("_hash", "children")
    _hash: int
    children: tuple[Domain, ...]

    def __new__(cls, children: tuple[Domain, ...]):
        if len(children) < 2:
            raise ValueError(
                f"DomainNary requires at least 2 children, got {len(children)}"
            )
        self = object.__new__(cls)
        object.__setattr__(self, "children", children)
        object.__setattr__(
            self,
            "_depth",
            _check_depth(1 + max(child._depth for child in children)),
        )
        object.__setattr__(self, "_opt", (OptimizationLevel.NONE, None))
        return self

    @classmethod
    def apply(cls, items: Iterable[Domain]) -> Domain:
        children = cls._flatten(items)
        if len(children) == 1:
            return children[0]
        return cls(tuple(children))

    @classmethod
    def _flatten(cls, children: Iterable[Domain]) -> list[Domain]:
        result: list[Domain] = []
        for child in children:
            if isinstance(child, DomainBool):
                if child != cls.ZERO:
                    return [child]
            elif isinstance(child, cls):
                result.extend(child.children)
            else:
                result.append(child)
        return result or [cls.ZERO]

    def __iter__(self) -> typing.Iterator[object]:
        yield from itertools.repeat(self.OPERATOR, len(self.children) - 1)
        for child in self.children:
            yield from child

    def __eq__(self, other: object) -> bool:
        return self is other or (
            isinstance(other, DomainNary)
            and self.OPERATOR == other.OPERATOR
            and self.children == other.children
        )

    def __hash__(self) -> int:
        try:
            return self._hash
        except AttributeError:
            h = hash(self.OPERATOR) ^ hash(self.children)
            object.__setattr__(self, "_hash", h)
            return h

    @classproperty
    def INVERSE(self) -> type[DomainNary]:
        raise NotImplementedError

    def __invert__(self) -> DomainNary:
        return self.INVERSE(tuple(~child for child in self.children))

    def _negate(self, model: BaseModel) -> DomainNary:
        return self.INVERSE(tuple(child._negate(model) for child in self.children))

    def iter_conditions(self) -> typing.Iterator[DomainCondition]:
        for child in self.children:
            yield from child.iter_conditions()

    def map_conditions(self, function: Callable[[DomainCondition], Domain]) -> Domain:
        return self.apply(child.map_conditions(function) for child in self.children)

    def _optimize_step(self, model: BaseModel, level: OptimizationLevel) -> Domain:
        children = self._flatten(
            child._optimize(model, level) for child in self.children
        )
        if len(children) > 1:
            children.sort(key=_get_nary_sort_key)
            cls = type(self)
            present_ops = {
                c.operator for c in children if isinstance(c, DomainCondition)
            }
            for merge in _MERGE_OPTIMIZATIONS:
                gate = merge._match_operators
                if gate is not None and gate.isdisjoint(present_ops):
                    continue
                merged = merge(cls, children, model)
                if merged is not children:
                    if _debug.logic.enabled:
                        _debug.logic(
                            "domain.nary.merged",
                            model=model._name,
                            kind=cls.__name__,
                            merge=getattr(merge, "__name__", type(merge).__name__),
                            before=len(children),
                            after=len(merged),
                        )
                    present_ops = {
                        c.operator for c in merged if isinstance(c, DomainCondition)
                    }
                children = merged
            if len(self.children) == len(children) and all(
                map(operator.is_, self.children, children, strict=True)
            ):
                return self
        return self.apply(children)

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        return SQL(
            "(%s)",
            self.OPERATOR_SQL.join(
                c._to_sql(model, alias, query) for c in self.children
            ),
        )


class DomainAnd(DomainNary):
    __slots__ = ()
    OPERATOR = "&"
    OPERATOR_SQL = SQL(" AND ")
    ZERO = _TRUE_DOMAIN

    @classproperty
    def INVERSE(self) -> type[DomainNary]:
        return DomainOr

    def __and__(self, other: object) -> Domain:
        if isinstance(other, DomainAnd):
            return DomainAnd(self.children + other.children)
        return super().__and__(other)

    def _as_predicate(self, records: BaseModel) -> Callable[[BaseModel], bool]:
        if (optimized := self._predicate_optimized(records)) is not None:
            return optimized._as_predicate(records)
        predicates = tuple(child._as_predicate(records) for child in self.children)

        def and_predicate(record: BaseModel) -> bool:
            return all(pred(record) for pred in predicates)

        return and_predicate


class DomainOr(DomainNary):
    __slots__ = ()
    OPERATOR = "|"
    OPERATOR_SQL = SQL(" OR ")
    ZERO = _FALSE_DOMAIN

    @classproperty
    def INVERSE(self) -> type[DomainNary]:
        return DomainAnd

    def __or__(self, other: object) -> Domain:
        if isinstance(other, DomainOr):
            return DomainOr(self.children + other.children)
        return super().__or__(other)

    def _as_predicate(self, records: BaseModel) -> Callable[[BaseModel], bool]:
        if (optimized := self._predicate_optimized(records)) is not None:
            return optimized._as_predicate(records)
        predicates = tuple(child._as_predicate(records) for child in self.children)

        def or_predicate(record: BaseModel) -> bool:
            return any(pred(record) for pred in predicates)

        return or_predicate


class DomainCustom(Domain):
    __slots__ = ("_filtered", "_sql")

    _filtered: Callable[[BaseModel], bool] | None
    _sql: Callable[[BaseModel, str, Query], SQL]

    def __new__(
        cls,
        sql: Callable[[BaseModel, str, Query], SQL],
        filtered: Callable[[BaseModel], bool] | None = None,
    ):
        self = object.__new__(cls)
        object.__setattr__(self, "_sql", sql)
        object.__setattr__(self, "_filtered", filtered)
        object.__setattr__(self, "_depth", 1)
        object.__setattr__(self, "_opt", (OptimizationLevel.FULL, None))
        return self

    def _as_predicate(self, records: BaseModel) -> Callable[[BaseModel], bool]:
        if self._filtered is not None:
            return self._filtered
        _debug.logic(
            "domain.custom.predicate_via_search",
            model=records._name,
            records=len(records),
        )
        query = records._search(
            DomainCondition("id", "in", records.ids) & self, order="id"
        )
        return DomainCondition("id", "any", query)._as_predicate(records)

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, DomainCustom)
            and self._sql == other._sql
            and self._filtered == other._filtered
        )

    def __hash__(self) -> int:
        return hash(self._sql) ^ hash(self._filtered)

    def __iter__(self) -> typing.Iterator[object]:
        yield ("<custom_sql>", "", "")

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        return self._sql(model, alias, query)


def _defines_the_condition(field: Field, su: bool) -> bool:
    # a search method answers the condition instead of the field's value. A
    # related or inherited field's generic search is the path rewrite, whose
    # sub-select a record rule may narrow for a user but never for the
    # superuser: as the superuser the in-memory read through the path answers
    # the same, unless the path ends on a field with a search method of its own
    search = field.search
    if not search:
        return False
    if getattr(search, "__func__", None) is not _search_related_function():
        return True
    if not su:
        return True
    target = field.related_field
    return _defines_the_condition(target, su) if target is not None else False


@functools.cache
def _search_related_function():
    from ..fields.base import Field as _Field

    return _Field._search_related


def ids_selected_without_query(domain: Domain) -> OrderedSet | None:
    if domain.is_false():
        return OrderedSet()
    if (
        isinstance(domain, DomainCondition)
        and domain.field_expr == "id"
        and domain.operator == "in"
        and isinstance(
            domain.value, (list, tuple, set, frozenset, OrderedSet, FrozenOrderedSet)
        )
        and all(isinstance(id_, int) for id_ in domain.value)
    ):
        return OrderedSet(domain.value)
    return None


def _ids_matched_without_query(domain: Domain, universe: frozenset) -> set | None:
    if domain.is_false():
        return set()
    if isinstance(domain, DomainCondition):
        if domain.field_expr != "id" or not isinstance(
            domain.value, (list, tuple, set, frozenset, OrderedSet, FrozenOrderedSet)
        ):
            return None
        if domain.operator == "in":
            return set(universe.intersection(domain.value))
        return None
    if isinstance(domain, (DomainAnd, DomainOr)):
        parts: list[set] = []
        for child in domain.children:
            part = _ids_matched_without_query(child, universe)
            if part is None:
                return None
            parts.append(part)
        if isinstance(domain, DomainAnd):
            return set(universe.intersection(*parts))
        return set().union(*parts)
    return None


class DomainCondition(Domain):
    __slots__ = (
        "_field_instance",
        "_hash",
        "_predicate_fallback",
        "field_expr",
        "operator",
        "value",
    )
    _field_instance: Field | None
    _hash: int
    field_expr: str
    operator: str
    value: typing.Any

    def __new__(cls, field_expr: str, operator: str, value: object) -> DomainCondition:  # noqa: PYI034  overrides Domain.__new__, whose return type is deliberately not Self (see its noqa)
        self = object.__new__(cls)
        object.__setattr__(self, "field_expr", field_expr)
        object.__setattr__(self, "operator", operator)
        object.__setattr__(self, "value", _freeze_comparand(value))
        object.__setattr__(
            self,
            "_depth",
            _check_depth(value._depth + 1) if isinstance(value, Domain) else 1,
        )
        object.__setattr__(self, "_field_instance", None)
        object.__setattr__(self, "_opt", (OptimizationLevel.NONE, None))
        return self

    def normalize(self) -> DomainCondition:
        if not isinstance(self.field_expr, str) or not self.field_expr:
            raise self._prepare_condition_error("Empty field name", error=TypeError)
        op = self.operator.lower()
        if op != self.operator:
            _debug.logic(
                "domain.normalize.operator_lowercased",
                field_expr=self.field_expr,
                operator=self.operator,
            )
            warnings.warn(
                f"Deprecated since 19.0, the domain condition {(self.field_expr, self.operator, self.value)!r} should have a lower-case operator",
                DeprecationWarning,
                stacklevel=2,
            )
            return DomainCondition(self.field_expr, op, self.value).normalize()
        if op not in ACCEPTED_CONDITION_OPERATORS:
            raise self._prepare_condition_error("Invalid operator")
        if op in SUBDOMAIN_OPERATORS and isinstance(self.value, (list, tuple)):
            _check_subdomain_nesting(self.value, MAX_DOMAIN_NESTING)
        value = self.value
        if value is None:
            value = False
        elif isinstance(value, NewId):
            _debug.logic(
                "domain.normalize.new_id_dropped",
                field_expr=self.field_expr,
                operator=op,
            )
            _logger.warning(
                "Domains don't support NewId, use .ids instead, for %r",
                (self.field_expr, self.operator, self.value),
            )
            op = "not in" if op in NEGATIVE_CONDITION_OPERATORS else "in"
            value = []
        elif is_recordset(value):
            _debug.logic(
                "domain.normalize.recordset_to_ids",
                field_expr=self.field_expr,
                operator=op,
                model=value._name,
                ids=len(value),
            )
            _logger.warning(
                "The domain condition %r should not have a value which is a model",
                (self.field_expr, self.operator, self.value),
            )
            value = value.ids
        elif isinstance(value, (Domain, Query, SQL)) and op not in (
            SUBDOMAIN_OR_IN_OPERATORS
        ):
            _debug.logic(
                "domain.normalize.subquery_without_any",
                field_expr=self.field_expr,
                operator=op,
                value_type=type(value).__name__,
            )
            _logger.warning(
                "The domain condition %r should use the 'any' or 'not any' operator.",
                (self.field_expr, self.operator, self.value),
            )
        if value is not self.value:
            return DomainCondition(self.field_expr, op, value)
        return self

    def __invert__(self) -> Domain:
        if "." not in self.field_expr and (
            neg_op := INVERSE_OPERATOR.get(self.operator)
        ):
            return DomainCondition(self.field_expr, neg_op, self.value)
        return super().__invert__()

    def _negate(self, model: BaseModel) -> Domain:
        if neg_op := INVERSE_INEQUALITY.get(self.operator):
            condition: Domain = DomainCondition(self.field_expr, neg_op, self.value)
            null_included = self._get_field(model).falsy_value is None
            if null_included:
                is_null = DomainCondition(self.field_expr, "in", OrderedSet([False]))
                condition = is_null | condition
            _debug.logic(
                "domain.negate.inequality",
                model=model._name,
                field_expr=self.field_expr,
                operator=self.operator,
                negated=neg_op,
                null_included=null_included,
            )
            return condition

        return super()._negate(model)

    def __iter__(self) -> typing.Iterator[tuple[str, str, object]]:
        yield (
            self.field_expr,
            self.operator,
            _thaw_comparand(self.operator, self.value),
        )

    def __eq__(self, other: object) -> bool:
        return self is other or (
            isinstance(other, DomainCondition)
            and self.field_expr == other.field_expr
            and self.operator == other.operator
            and self.value.__class__ is other.value.__class__
            and (
                self.value == other.value
                if self.operator in SUBDOMAIN_OPERATORS
                and isinstance(self.value, tuple)
                else _is_comparand_equal(self.value, other.value)
            )
        )

    def __hash__(self) -> int:
        try:
            return self._hash
        except AttributeError:
            pass
        value = self.value
        try:
            if value.__class__ in (
                list,
                tuple,
                set,
                frozenset,
                OrderedSet,
                FrozenOrderedSet,
            ):
                h = hash(
                    (
                        self.field_expr,
                        self.operator,
                        frozenset((type(v), v) for v in value),
                    )
                )
            else:
                h = hash((self.field_expr, self.operator, value))
        except TypeError:
            h = hash((self.field_expr, self.operator))
        object.__setattr__(self, "_hash", h)
        return h

    def iter_conditions(self) -> typing.Iterator[DomainCondition]:
        yield self

    def map_conditions(self, function: Callable[[DomainCondition], Domain]) -> Domain:
        result = function(self)
        assert isinstance(result, Domain), "result of map_conditions is not a Domain"
        return result

    def _prepare_condition_error(
        self, message: str, *args, error=ValueError
    ) -> Exception:
        message += " in condition (%r, %r, %r)"
        return error(message % (*args, self.field_expr, self.operator, self.value))

    def _get_field(self, model: BaseModel) -> Field:
        field = self._field_instance
        if field is None or field.model_name != model._name:
            field, _ = self.__get_field_and_property(model)
        return field

    def __get_field_and_property(self, model: BaseModel) -> tuple[Field, str]:
        field_name, property_name = parse_field_expr(self.field_expr)
        try:
            field = model._fields[field_name]
        except KeyError:
            raise self._prepare_condition_error(
                "Invalid field %s.%s", model._name, field_name
            ) from None
        object.__setattr__(self, "_field_instance", field)
        return field, property_name or ""

    def _optimize_step(self, model: BaseModel, level: OptimizationLevel) -> Domain:
        opt_level = self._opt_level
        if level <= opt_level:
            return self
        if level > opt_level.next_level:
            raise RuntimeError(f"Trying to skip optimization level after {opt_level}")

        if level == OptimizationLevel.BASIC:
            field, property_name = self.__get_field_and_property(model)
            if property_name and field.relational:
                sub_domain = DomainCondition(property_name, self.operator, self.value)
                return DomainCondition(field.name, "any", sub_domain)
        else:
            field = self._get_field(model)

        if level == OptimizationLevel.FULL:
            if field.inherited:
                assert field.related
                parent_fname = field.related.split(".")[0]
                parent_domain = DomainCondition(
                    self.field_expr, self.operator, self.value
                )
                _debug.logic(
                    "domain.condition.inherited_delegated",
                    model=model._name,
                    field=self.field_expr,
                    parent=parent_fname,
                )
                return DomainCondition(parent_fname, "any", parent_domain)

            if field.search and field.name == self.field_expr:
                model._check_field_access(field, "read")
                if field.is_boolean:
                    for opt in _OPTIMIZATIONS_FOR[level].get("boolean", ()):
                        collapsed = opt(self, model)
                        if isinstance(collapsed, DomainBool):
                            return collapsed
                domain = self._optimize_field_search_method(model)
                if domain != self:
                    domain = domain.optimize(model)
                    if domain != self:
                        if _debug.logic.enabled:
                            _debug.logic(
                                "domain.condition.search_method_applied",
                                model=model._name,
                                field=self.field_expr,
                                operator=self.operator,
                                conditions=sum(1 for _c in domain.iter_conditions()),
                            )
                        return domain

        optimizations = _OPTIMIZATIONS_FOR[level]
        for opt in optimizations.get(self.operator, ()):
            domain = opt(self, model)
            if domain != self:
                return domain
        domain = field._optimize_condition(self, model, level)
        if domain != self:
            return domain
        for opt in optimizations.get(field.type, ()):
            domain = opt(self, model)
            if domain != self:
                return domain

        if (
            self.operator not in STANDARD_CONDITION_OPERATORS
            and level == OptimizationLevel.FULL
        ):
            raise self._prepare_condition_error("Not standard operator left")

        return self

    def _optimize_field_search_method(self, model: BaseModel) -> Domain:
        field = self._get_field(model)
        op, value = self.operator, self.value
        original_exception = None
        try:
            computed_domain = field.get_search_domain(model, op, value)
        except (NotImplementedError, UserError) as e:
            computed_domain = NotImplemented
            original_exception = e
        else:
            if computed_domain is not NotImplemented:
                return Domain(computed_domain, internal=True)
        if original_exception is None and (inversed_op := INVERSE_OPERATOR.get(op)):
            computed_domain = field.get_search_domain(model, inversed_op, value)
            if computed_domain is not NotImplemented:
                _debug.logic(
                    "domain.search_method.fallback",
                    model=model._name,
                    field=self.field_expr,
                    operator=op,
                    kind="inverse_operator",
                )
                return ~Domain(computed_domain, internal=True)
        try:
            if op in ("any!", "not any!"):
                computed_domain = DomainCondition(
                    self.field_expr, op.rstrip("!"), value
                )
                computed_domain = computed_domain._optimize_field_search_method(
                    model.sudo()
                )
                _logger.warning("Field %s should implement any! operator", field)
                _debug.logic(
                    "domain.search_method.fallback",
                    model=model._name,
                    field=self.field_expr,
                    operator=op,
                    kind="any_without_bang",
                )
                return computed_domain
        except (NotImplementedError, UserError) as e:
            if original_exception is None:
                original_exception = e
        try:
            if _debug.logic.enabled and op in ("in", "not in"):
                _debug.logic(
                    "domain.search_method.fallback",
                    model=model._name,
                    field=self.field_expr,
                    operator=op,
                    kind="per_value",
                    values=len(value),
                )
            if op == "in":
                return Domain.OR(
                    Domain(field.get_search_domain(model, "=", v), internal=True)
                    for v in value
                )
            elif op == "not in":
                return Domain.AND(
                    Domain(field.get_search_domain(model, "!=", v), internal=True)
                    for v in value
                )
        except (NotImplementedError, UserError) as e:
            if original_exception is None:
                original_exception = e
        if original_exception:
            raise original_exception
        raise UserError(
            model.env._(
                "Unsupported operator on %(field_label)s %(model_label)s in %(domain)s",
                domain=repr(self),
                field_label=self._get_field(model).get_description(
                    model.env, ["string"]
                )["string"],
                model_label=f"{model.env.registry.metaschema.model_description(model.env, model._name)!r} ({model._name})",
            )
        )

    def _is_search_defined(self, records: BaseModel) -> bool:
        field = self._get_field(records)
        if field.name != self.field_expr:
            return False
        return _defines_the_condition(field, records.env.su)

    def _search_defined_predicate(
        self, records: BaseModel
    ) -> Callable[[BaseModel], bool]:
        real_ids = [id_ for id_ in records._ids if id_]
        matched: set = set()
        if real_ids:
            scoped = records.with_context(active_test=False)
            candidates = DomainCondition("id", "in", OrderedSet(real_ids)) & self
            answered = None
            if scoped.env.su:
                with _recursion_error_as_value_error():
                    answered = _ids_matched_without_query(
                        self.optimize_full(scoped), frozenset(real_ids)
                    )
            if answered is None:
                query = scoped._search(candidates)
                matched = set(query.get_result_ids())
            else:
                matched = answered
            _debug.logic(
                "domain.predicate.search_defined_query",
                model=records._name,
                field=self.field_expr,
                operator=self.operator,
                records=len(real_ids),
                matched=len(matched),
            )

        if all(records._ids):
            return lambda rec: rec._ids[0] in matched

        in_memory = self._get_value_predicate(records)
        return lambda rec: rec._ids[0] in matched if rec._ids[0] else in_memory(rec)

    def _as_predicate(self, records: BaseModel) -> Callable[[BaseModel], bool]:
        if not records:
            return lambda _: False

        opt_level, opt_model = self._opt
        if opt_level < OptimizationLevel.DYNAMIC_VALUES or opt_model != records._name:
            with _recursion_error_as_value_error():
                domain = self._optimize(records, OptimizationLevel.DYNAMIC_VALUES)
            return domain._as_predicate(records)

        op = self.operator
        if op in ("child_of", "parent_of"):
            _debug.logic(
                "domain.predicate.hierarchy_expanded",
                model=records._name,
                field_expr=self.field_expr,
                operator=op,
                records=len(records),
            )
            with _recursion_error_as_value_error():
                domain = self._optimize(records, OptimizationLevel.FULL)
            return domain._as_predicate(records)

        # a fully optimized condition already ran its search method, which
        # answered with this very condition (a stored field searching itself):
        # the column answers now, or the in-memory search would loop
        if opt_level < OptimizationLevel.FULL:
            if self._is_search_defined(records):
                return self._search_defined_predicate(records)
            if self._is_related_path(records):
                # the superuser walks the related path in memory: the FULL
                # rewrite is the `any` chain the sub-select would join, and
                # no rule narrows it for the superuser
                with _recursion_error_as_value_error():
                    domain = self._optimize(records, OptimizationLevel.FULL)
                if domain is not self:
                    return domain._as_predicate(records)

        return self._get_value_predicate(records)

    def _is_related_path(self, records: BaseModel) -> bool:
        field = self._get_field(records)
        return (
            field.name == self.field_expr
            and getattr(field.search, "__func__", None) is _search_related_function()
        )

    def _get_value_predicate(self, records: BaseModel) -> Callable[[BaseModel], bool]:
        op = self.operator
        if not all(records._ids):
            fallback = getattr(self, "_predicate_fallback", None)
            if fallback is not None:
                _debug.logic(
                    "domain.predicate.new_records_fallback",
                    model=records._name,
                    field_expr=self.field_expr,
                    operator=op,
                    records=len(records),
                )
                return fallback._as_predicate(records)

        if op not in STANDARD_CONDITION_OPERATORS:
            raise RuntimeError(f"Expecting a sub-set of operators, got {op!r}")
        field_expr, value = self.field_expr, self.value
        positive_operator = NEGATIVE_CONDITION_OPERATORS.get(op, op)

        if isinstance(value, SQL):
            condition: Domain
            if positive_operator == op:
                condition = self
                op = "any!"
            else:
                condition = ~self
                op = "not any!"
            positive_operator = "any!"
            field_expr = "id"
            _debug.logic(
                "domain.predicate.sql_value_via_search",
                model=records._name,
                field_expr=self.field_expr,
                operator=self.operator,
                records=len(records),
            )
            value = records.with_context(active_test=False)._search(
                DomainCondition("id", "in", OrderedSet(records.ids)) & condition
            )
            assert isinstance(value, Query)

        if isinstance(value, Query):
            if positive_operator not in ("in", "any", "any!"):
                raise self._prepare_condition_error(
                    "Cannot filter using Query without the 'any' or 'in' operator"
                )
            if positive_operator != "in":
                op = "in" if positive_operator == op else "not in"
                positive_operator = "in"
            # Run it on the environment of the records being filtered: a rule
            # domain is cached across requests, so a Query inside it may still
            # point at the closed cursor of the request that built it.
            value = set(value.get_result_ids(records.env))
            _debug.logic(
                "domain.predicate.query_resolved",
                model=records._name,
                field=field_expr,
                operator=op,
                ids=len(value),
            )
            return DomainCondition(field_expr, op, value)._as_predicate(records)

        field = self._get_field(records)
        if field_expr == "display_name":
            field_expr = "display_name.no_error"
        elif field_expr == "id":
            field_expr = "id.origin"

        func = field.filter_function(records, field_expr, positive_operator, value)
        return func if positive_operator == op else lambda rec: not func(rec)

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        field_expr, op, value = self.field_expr, self.operator, self.value
        if op not in STANDARD_CONDITION_OPERATORS:
            raise RuntimeError(
                f"Invalid operator {op!r} for SQL in domain term {(field_expr, op, value)!r}"
            )
        if self._opt_level < OptimizationLevel.FULL:
            raise RuntimeError(
                f"Must fully optimize before generating the query {(field_expr, op, value)}"
            )
        if self._opt_model_name not in (None, model._name):
            raise RuntimeError(
                f"Domain optimized for {self._opt_model_name!r} cannot generate "
                f"SQL for {model._name!r} in term {(field_expr, op, value)}"
            )

        field = self._get_field(model)
        model._check_field_access(field, "read")
        return field.condition_to_sql(field_expr, op, value, model, alias, query)


ANY_TYPES = (Domain, Query, SQL)

__all__ = [
    "ANY_TYPES",
    "MAX_OPTIMIZE_ITERATIONS",
    "Domain",
    "DomainAnd",
    "DomainBool",
    "DomainCondition",
    "DomainCustom",
    "DomainNary",
    "DomainNot",
    "DomainOptimizationError",
    "DomainOr",
    "OptimizationLevel",
    "ids_selected_without_query",
]
