"""Domain AST (Abstract Syntax Tree) classes.

This module contains the Domain class hierarchy:
- Domain: Base class and factory for domain expressions
- DomainBool: Constant domains (TRUE, FALSE)
- DomainNot: Negation domain
- DomainNary: Base for n-ary operators
- DomainAnd: Conjunction (AND)
- DomainOr: Disjunction (OR)
- DomainCustom: Custom SQL domain
- DomainCondition: Field condition (field, operator, value)

Also contains:
- OptimizationLevel: Enum for optimization stages
- Optimization registries used by the optimization functions
"""

import collections
import enum
import functools
import itertools
import logging
import operator
import types
import typing
import warnings
from collections.abc import Callable, Iterable

from odoo.exceptions import UserError
from odoo.tools import SQL, OrderedSet, Query, classproperty

from ..parsing import parse_field_expr
from ..primitives import COLLECTION_TYPES, NewId
from .constants import (
    CONDITION_OPERATORS,
    FALSE_LEAF,
    INTERNAL_CONDITION_OPERATORS,
    INVERSE_INEQUALITY,
    INVERSE_OPERATOR,
    NEGATIVE_CONDITION_OPERATORS,
    STANDARD_CONDITION_OPERATORS,
    SUBDOMAIN_OPERATORS,
    TRUE_LEAF,
)

if typing.TYPE_CHECKING:
    from collections.abc import Collection

    from ..fields import Field
    from ..models import BaseModel

    M = typing.TypeVar("M", bound=BaseModel)

_logger = logging.getLogger("odoo.domains")


class OptimizationLevel(enum.IntEnum):
    """Indicator whether the domain was optimized."""

    NONE = 0
    BASIC = enum.auto()
    DYNAMIC_VALUES = enum.auto()
    FULL = enum.auto()

    @functools.cached_property
    def next_level(self):
        assert self is not OptimizationLevel.FULL, "FULL level is the last one"
        return OptimizationLevel(int(self) + 1)


MAX_OPTIMIZE_ITERATIONS = 1000

# Types for optimization functions
ANY_TYPES = (typing.ForwardRef("Domain"), Query, SQL)

if typing.TYPE_CHECKING:
    ConditionOptimization = Callable[["DomainCondition", "BaseModel"], "Domain"]
    MergeOptimization = Callable[
        [type["DomainNary"], list["Domain"], "BaseModel"], list["Domain"]
    ]

# Optimization registries - populated by optimization functions in optimizations.py
_OPTIMIZATIONS_FOR: dict[OptimizationLevel, dict[str, list]] = {
    level: collections.defaultdict(list)
    for level in OptimizationLevel
    if level != OptimizationLevel.NONE
}
_MERGE_OPTIMIZATIONS: list = []


def _optimize_nary_sort_key(domain: Domain) -> tuple[str, str, str]:
    """Sorting key for nary domains so that similar operators are grouped together.

    1. Field name (non-simple conditions are sorted at the end)
    2. Operator type (equality, inequality, existence, string comparison, other)
    3. Operator

    Sorting allows to have the same optimized domain for equivalent conditions.
    For debugging, it eases to find conditions on fields.
    The generated SQL will be ordered by field name so that database caching
    can be applied more frequently.
    """
    if isinstance(domain, DomainCondition):
        # group the same field and same operator together
        op = domain.operator
        positive_op = NEGATIVE_CONDITION_OPERATORS.get(op, op)
        if positive_op == "in":
            order = "0in"
        elif positive_op == "any":
            order = "1any"
        elif positive_op == "any!":
            order = "2any"
        elif positive_op.endswith("like"):
            order = "like"
        else:
            order = positive_op
        return domain.field_expr, order, op
    elif hasattr(domain, "OPERATOR") and isinstance(domain.OPERATOR, str):
        # in python; '~' > any letter
        return "~", "", domain.OPERATOR
    else:
        return "~", "~", domain.__class__.__name__


# --------------------------------------------------
# Domain definition and manipulation
# --------------------------------------------------


class Domain:
    """Representation of a domain as an AST."""

    # Domain is an abstract class (ABC), but not marked as such
    # because we overwrite __new__ so typechecking for abstractmethod is incorrect.
    # We do this so that we can use the Domain as both a factory for multiple
    # types of domains, while still having `isinstance` working for it.
    __slots__ = ("_opt_level",)
    _opt_level: OptimizationLevel

    def __new__(cls, *args, internal: bool = False):
        """Build a domain AST.

        ```
        Domain([('a', '=', 5), ('b', '=', 8)])
        Domain('a', '=', 5) & Domain('b', '=', 8)
        Domain.AND([Domain('a', '=', 5), *other_domains, Domain.TRUE])
        ```

        If we have one argument, it is a `Domain`, or a list representation, or a bool.
        In case we have multiple ones, there must be 3 of them:
        a field (str), the operator (str) and a value for the condition.

        By default, the special operators ``'any!'`` and ``'not any!'`` are
        allowed in domain conditions (``Domain('a', 'any!', dom)``) but not in
        domain lists (``Domain([('a', 'any!', dom)])``).
        """
        if len(args) > 1:
            if isinstance(args[0], str):
                return DomainCondition(*args).checked()
            # special cases like True/False constants
            if args == TRUE_LEAF:
                return _TRUE_DOMAIN
            if args == FALSE_LEAF:
                return _FALSE_DOMAIN
            raise TypeError(f"Domain() invalid arguments: {args!r}")

        arg = args[0]
        if isinstance(arg, Domain):
            return arg
        if arg is True or arg == []:
            return _TRUE_DOMAIN
        if arg is False:
            return _FALSE_DOMAIN
        if arg is NotImplemented:
            raise NotImplementedError

        # parse as a list
        # perf: do this inside __new__ to avoid calling function that return
        # a Domain which would call implicitly __init__
        if not isinstance(arg, (list, tuple)):
            raise TypeError(f"Domain() invalid argument type for domain: {arg!r}")
        # Fast path: single-condition domain [('field', 'op', value)]
        # This is the most common pattern and avoids the stack/reverse overhead.
        if len(arg) == 1:
            item = arg[0]
            if isinstance(item, (tuple, list)) and len(item) == 3:
                if internal:
                    # Parse subdomain values for any/any!/not any/not any! operators
                    if item[1] in SUBDOMAIN_OPERATORS and isinstance(
                        item[2], (list, tuple)
                    ):
                        item = (
                            item[0],
                            item[1],
                            Domain(item[2], internal=True),
                        )
                elif item[1] in INTERNAL_CONDITION_OPERATORS:
                    raise ValueError(f"Domain() invalid item in domain: {item!r}")
                return Domain(*item)
            if isinstance(item, Domain):
                return item
        stack: list[Domain] = []
        try:
            for item in reversed(arg):
                if isinstance(item, (tuple, list)) and len(item) == 3:
                    if internal:
                        # process subdomains when processing internal operators
                        if item[1] in SUBDOMAIN_OPERATORS and isinstance(
                            item[2], (list, tuple)
                        ):
                            item = (
                                item[0],
                                item[1],
                                Domain(item[2], internal=True),
                            )
                    elif item[1] in INTERNAL_CONDITION_OPERATORS:
                        # internal operators are not accepted
                        raise ValueError(f"Domain() invalid item in domain: {item!r}")
                    stack.append(Domain(*item))
                elif item == DomainAnd.OPERATOR:
                    stack.append(stack.pop() & stack.pop())
                elif item == DomainOr.OPERATOR:
                    stack.append(stack.pop() | stack.pop())
                elif item == DomainNot.OPERATOR:
                    stack.append(~stack.pop())
                elif isinstance(item, Domain):
                    stack.append(item)
                else:
                    raise ValueError(f"Domain() invalid item in domain: {item!r}")
            # keep the order and simplify already
            if len(stack) == 1:
                return stack[0]
            return Domain.AND(reversed(stack))
        except IndexError:
            raise ValueError(f"Domain() malformed domain {arg!r}")

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
        """Create a custom domain.

        :param to_sql: callable(model, alias, query) that returns the SQL
        :param predicate: callable(record) that checks whether a record is kept
                          when filtering
        """
        return DomainCustom(to_sql, predicate)

    @staticmethod
    def AND(items: Iterable) -> Domain:
        """Build the conjuction of domains: (item1 AND item2 AND ...)"""
        return DomainAnd.apply(Domain(item) for item in items)

    @staticmethod
    def OR(items: Iterable) -> Domain:
        """Build the disjuction of domains: (item1 OR item2 OR ...)"""
        return DomainOr.apply(Domain(item) for item in items)

    def __setattr__(self, name, value):
        raise TypeError("Domain objects are immutable")

    def __delattr__(self, name):
        raise TypeError("Domain objects are immutable")

    def __and__(self, other):
        """Domain & Domain"""
        if isinstance(other, Domain):
            # Fast path: absorbing element / identity shortcuts
            if isinstance(other, DomainBool):
                return self if other.value else other
            return DomainAnd.apply([self, other])
        return NotImplemented

    def __or__(self, other):
        """Domain | Domain"""
        if isinstance(other, Domain):
            # Fast path: absorbing element / identity shortcuts
            if isinstance(other, DomainBool):
                return other if other.value else self
            return DomainOr.apply([self, other])
        return NotImplemented

    def __invert__(self):
        """~Domain"""
        return DomainNot(self)

    def _negate(self, model: BaseModel) -> Domain:
        """Apply (propagate) negation onto this domain."""
        return ~self

    def __add__(self, other):
        """Domain + [...]

        For backward-compatibility of domain composition.
        Concatenate as lists.
        If we have two domains, equivalent to '&'.
        """
        # DEPRECATED: Use Domain & Domain for conjunction, not Domain + Domain.
        # Combining Domain with a raw list is fragile because the list may
        # not be normalized.  Kept for backward compatibility.
        if isinstance(other, Domain):
            warnings.warn(
                "Domain + Domain is deprecated, use Domain & Domain (AND) "
                "or Domain | Domain (OR) instead",
                DeprecationWarning,
                stacklevel=2,
            )
            return self & other
        if not isinstance(other, list):
            raise TypeError("Domain() can concatenate only lists")
        warnings.warn(
            "Domain + list is deprecated, convert the list to a Domain first",
            DeprecationWarning,
            stacklevel=2,
        )
        return list(self) + other

    def __radd__(self, other):
        """Commutative definition of *+*"""
        # DEPRECATED: Use Domain & Domain for conjunction, not list + Domain.
        warnings.warn(
            "list + Domain is deprecated, convert the list to a Domain first",
            DeprecationWarning,
            stacklevel=2,
        )
        # we are pre-pending, return a list
        # because the result may not be normalized
        return other + list(self)

    def __bool__(self):
        """Indicate that the domain is not true.

        For backward-compatibility, only the domain [] was False. Which means
        that the TRUE domain is falsy and others are truthy.
        """
        # DEPRECATED: Use is_true() / is_false() instead of bool().
        # The semantics are confusing: TRUE domain is falsy, others are truthy.
        # Not enabling the warning yet — too many callers in core still use
        # ``if domain:`` patterns.  Enable once callers are migrated.
        # warnings.warn(
        #     "bool(Domain) is deprecated, use domain.is_true() or domain.is_false()",
        #     DeprecationWarning,
        #     stacklevel=2,
        # )
        return not self.is_true()

    def __eq__(self, other):
        raise NotImplementedError

    def __hash__(self):
        raise NotImplementedError

    def __iter__(self):
        """For-backward compatibility, return the polish-notation domain list"""
        yield from ()
        raise NotImplementedError

    def __reversed__(self):
        """For-backward compatibility, reversed iter"""
        return reversed(list(self))

    def __repr__(self) -> str:
        # return representation of the object as the old-style list
        return repr(list(self))

    def is_true(self) -> bool:
        """Return whether self is TRUE"""
        return False

    def is_false(self) -> bool:
        """Return whether self is FALSE"""
        return False

    def iter_conditions(self) -> Iterable[DomainCondition]:
        """Yield simple conditions of the domain"""
        yield from ()

    def map_conditions(self, function: Callable[[DomainCondition], Domain]) -> Domain:
        """Map a function to each condition and return the combined result"""
        return self

    def validate(self, model: BaseModel) -> None:
        """Validates that the current domain is correct or raises an exception"""
        # just execute the optimization code that goes through all the fields
        self._optimize(model, OptimizationLevel.FULL)

    def _as_predicate(self, records: M) -> Callable[[M], bool]:
        """Return a predicate function from the domain (bound to records).
        The predicate function return whether its argument (a single record)
        satisfies the domain.

        This is used to implement ``Model.filtered_domain``.
        """
        raise NotImplementedError

    def optimize(self, model: BaseModel) -> Domain:
        """Perform optimizations of the node given a model.

        It is a pre-processing step to rewrite the domain into a logically
        equivalent domain that is a more canonical representation of the
        predicate. Multiple conditions can be merged together.

        It applies basic optimizations only. Those are transaction-independent;
        they only depend on the model's fields definitions. No model-specific
        override is used, and the resulting domain may be reused in another
        transaction without semantic impact.
        The model's fields are used to validate conditions and apply
        type-dependent optimizations. This optimization level may be useful to
        simplify a domain that is sent to the client-side, thereby reducing its
        payload/complexity.
        """
        return self._optimize(model, OptimizationLevel.BASIC)

    def optimize_full(self, model: BaseModel) -> Domain:
        """Perform optimizations of the node given a model.

        Basic and advanced optimizations are applied.
        Advanced optimizations may rely on model specific overrides
        (search methods of fields, etc.) and the semantic equivalence is only
        guaranteed at the given point in a transaction. We resolve inherited
        and non-stored fields (using their search method) to transform the
        conditions.
        """
        return self._optimize(model, OptimizationLevel.FULL)

    @typing.final
    def _optimize(self, model: BaseModel, level: OptimizationLevel) -> Domain:
        """Perform optimizations of the node given a model.

        Reach a fixed-point by applying the optimizations for the next level
        on the node until we reach a stable node at the given level.
        """
        domain, previous, count = self, None, 0
        while domain._opt_level < level:
            if (count := count + 1) > MAX_OPTIMIZE_ITERATIONS:
                raise RecursionError("Domain.optimize: too many loops")
            next_level = domain._opt_level.next_level
            previous, domain = domain, domain._optimize_step(model, next_level)
            # set the optimization level if necessary (unlike DomainBool, for instance)
            if domain == previous and domain._opt_level < next_level:
                object.__setattr__(domain, "_opt_level", next_level)
        return domain

    def _optimize_step(self, model: BaseModel, level: OptimizationLevel) -> Domain:
        """Implementation of domain for one level of optimizations."""
        return self

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        """Build the SQL to inject into the query.  The domain should be optimized first."""
        raise NotImplementedError


class DomainBool(Domain):
    """Constant domain: True/False

    It is NOT considered as a condition and these constants are removed
    from nary domains.
    """

    __slots__ = ("value",)
    value: bool

    # Pre-built SQL constants — avoids SQL() allocation on every _to_sql call
    _SQL_TRUE = SQL("TRUE")
    _SQL_FALSE = SQL("FALSE")

    def __new__(cls, value: bool):
        """Create a constant domain."""
        self = object.__new__(cls)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "_opt_level", OptimizationLevel.FULL)
        return self

    def __eq__(self, other):
        return self is other  # because this class has two instances only

    def __hash__(self):
        return hash(self.value)

    def is_true(self) -> bool:
        return self.value

    def is_false(self) -> bool:
        return not self.value

    def __invert__(self):
        return _FALSE_DOMAIN if self.value else _TRUE_DOMAIN

    def __and__(self, other):
        if isinstance(other, Domain):
            return other if self.value else self
        return NotImplemented

    def __or__(self, other):
        if isinstance(other, Domain):
            return self if self.value else other
        return NotImplemented

    def __iter__(self):
        yield TRUE_LEAF if self.value else FALSE_LEAF

    def _as_predicate(self, records):
        return lambda _: self.value

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        return self._SQL_TRUE if self.value else self._SQL_FALSE


# singletons, available though Domain.TRUE and Domain.FALSE
_TRUE_DOMAIN = DomainBool(True)
_FALSE_DOMAIN = DomainBool(False)


class DomainNot(Domain):
    """Negation domain, contains a single child"""

    OPERATOR = "!"

    __slots__ = ("child",)
    child: Domain

    def __new__(cls, child: Domain):
        """Create a domain which is the inverse of the child."""
        self = object.__new__(cls)
        object.__setattr__(self, "child", child)
        object.__setattr__(self, "_opt_level", OptimizationLevel.NONE)
        return self

    def __invert__(self):
        return self.child

    def __iter__(self):
        yield self.OPERATOR
        yield from self.child

    def iter_conditions(self):
        yield from self.child.iter_conditions()

    def map_conditions(self, function) -> Domain:
        return ~(self.child.map_conditions(function))

    def _optimize_step(self, model: BaseModel, level: OptimizationLevel) -> Domain:
        return self.child._optimize(model, level)._negate(model)

    def __eq__(self, other):
        return self is other or (
            isinstance(other, DomainNot) and self.child == other.child
        )

    def __hash__(self):
        return ~hash(self.child)

    def _as_predicate(self, records):
        predicate = self.child._as_predicate(records)
        return lambda rec: not predicate(rec)

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        condition = self.child._to_sql(model, alias, query)
        return SQL("(%s) IS NOT TRUE", condition)


class DomainNary(Domain):
    """Domain for a nary operator: AND or OR with multiple children"""

    OPERATOR: str
    OPERATOR_SQL: SQL = SQL(" ??? ")
    ZERO: DomainBool = _FALSE_DOMAIN  # default for lint checks

    __slots__ = ("children",)
    children: tuple[Domain, ...]

    def __new__(cls, children: tuple[Domain, ...]):
        """Create the n-ary domain with at least 2 conditions."""
        assert len(children) >= 2
        self = object.__new__(cls)
        object.__setattr__(self, "children", children)
        object.__setattr__(self, "_opt_level", OptimizationLevel.NONE)
        return self

    @classmethod
    def apply(cls, items: Iterable[Domain]) -> Domain:
        """Return the result of combining AND/OR to a collection of domains."""
        children = cls._flatten(items)
        if len(children) == 1:
            return children[0]
        return cls(tuple(children))

    @classmethod
    def _flatten(cls, children: Iterable[Domain]) -> list[Domain]:
        """Return an equivalent list of domains with respect to the boolean
        operation of the class (AND/OR).  Boolean subdomains are simplified,
        and subdomains of the same class are flattened into the list.
        The returned list is never empty.
        """
        result: list[Domain] = []
        for child in children:
            if isinstance(child, DomainBool):
                if child != cls.ZERO:
                    return [child]
            elif isinstance(child, cls):
                result.extend(child.children)  # same class, flatten
            else:
                result.append(child)
        return result or [cls.ZERO]

    def __iter__(self):
        yield from itertools.repeat(self.OPERATOR, len(self.children) - 1)
        for child in self.children:
            yield from child

    def __eq__(self, other):
        return self is other or (
            isinstance(other, DomainNary)
            and self.OPERATOR == other.OPERATOR
            and self.children == other.children
        )

    def __hash__(self):
        return hash(self.OPERATOR) ^ hash(self.children)

    @classproperty
    def INVERSE(self) -> type[DomainNary]:
        """Return the inverted nary type, AND/OR"""
        raise NotImplementedError

    def __invert__(self):
        return self.INVERSE(tuple(~child for child in self.children))

    def _negate(self, model):
        return self.INVERSE(tuple(child._negate(model) for child in self.children))

    def iter_conditions(self):
        for child in self.children:
            yield from child.iter_conditions()

    def map_conditions(self, function) -> Domain:
        return self.apply(child.map_conditions(function) for child in self.children)

    def _optimize_step(self, model: BaseModel, level: OptimizationLevel) -> Domain:
        # optimize children
        children = self._flatten(
            child._optimize(model, level) for child in self.children
        )
        size = len(children)
        if size > 1:
            # sort children in order to ease their grouping by field and operator
            children.sort(key=_optimize_nary_sort_key)
            # run optimizations until some merge happens
            cls = type(self)
            for merge in _MERGE_OPTIMIZATIONS:
                children = merge(cls, children, model)
                if len(children) < size:
                    break
            else:
                # if no change, skip creation of a new object
                if len(self.children) == len(children) and all(
                    map(operator.is_, self.children, children, strict=False)
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
    """Domain: AND with multiple children"""

    __slots__ = ()
    OPERATOR = "&"
    OPERATOR_SQL = SQL(" AND ")
    ZERO = _TRUE_DOMAIN

    @classproperty
    def INVERSE(self) -> type[DomainNary]:
        return DomainOr

    def __and__(self, other):
        # simple optimization to append children
        if isinstance(other, DomainAnd):
            return DomainAnd(self.children + other.children)
        return super().__and__(other)

    def _as_predicate(self, records):
        predicates = tuple(child._as_predicate(records) for child in self.children)

        def and_predicate(record):
            return all(pred(record) for pred in predicates)

        return and_predicate


class DomainOr(DomainNary):
    """Domain: OR with multiple children"""

    __slots__ = ()
    OPERATOR = "|"
    OPERATOR_SQL = SQL(" OR ")
    ZERO = _FALSE_DOMAIN

    @classproperty
    def INVERSE(self) -> type[DomainNary]:
        return DomainAnd

    def __or__(self, other):
        # simple optimization to append children
        if isinstance(other, DomainOr):
            return DomainOr(self.children + other.children)
        return super().__or__(other)

    def _as_predicate(self, records):
        predicates = tuple(child._as_predicate(records) for child in self.children)

        def or_predicate(record):
            return any(pred(record) for pred in predicates)

        return or_predicate


class DomainCustom(Domain):
    """Domain condition that generates directly SQL and possibly a ``filtered`` predicate."""

    __slots__ = ("_filtered", "_sql")

    _filtered: Callable[[BaseModel], bool] | None
    _sql: Callable[[BaseModel, str, Query], SQL]

    def __new__(
        cls,
        sql: Callable[[BaseModel, str, Query], SQL],
        filtered: Callable[[BaseModel], bool] | None = None,
    ):
        """Create a new domain.

        :param to_sql: callable(model, alias, query) that implements ``_to_sql``
                       which is used to generate the query for searching
        :param predicate: callable(record) that checks whether a record is kept
                          when filtering (``Model.filtered``)
        """
        self = object.__new__(cls)
        object.__setattr__(self, "_sql", sql)
        object.__setattr__(self, "_filtered", filtered)
        object.__setattr__(self, "_opt_level", OptimizationLevel.FULL)
        return self

    def _as_predicate(self, records):
        if self._filtered is not None:
            return self._filtered
        # by default, run the SQL query
        query = records._search(
            DomainCondition("id", "in", records.ids) & self, order="id"
        )
        return DomainCondition("id", "any", query)._as_predicate(records)

    def __eq__(self, other):
        return (
            isinstance(other, DomainCustom)
            and self._sql == other._sql
            and self._filtered == other._filtered
        )

    def __hash__(self):
        return hash(self._sql) ^ hash(self._filtered)

    def __iter__(self):
        yield from ()
        raise NotImplementedError

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        return self._sql(model, alias, query)


class DomainCondition(Domain):
    """Domain condition on field: (field, operator, value)

    A field (or expression) is compared to a value. The list of supported
    operators are described in CONDITION_OPERATORS.
    """

    __slots__ = ("_field_instance", "field_expr", "operator", "value")
    _field_instance: Field | None  # mutable cached property
    field_expr: str
    operator: str
    value: typing.Any

    def __new__(cls, field_expr: str, operator: str, value):
        """Init a new simple condition (internal init)

        :param field_expr: Field name or field path
        :param operator: A valid operator
        :param value: A value for the comparison
        """
        self = object.__new__(cls)
        object.__setattr__(self, "field_expr", field_expr)
        object.__setattr__(self, "operator", operator)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "_field_instance", None)
        object.__setattr__(self, "_opt_level", OptimizationLevel.NONE)
        return self

    def checked(self) -> DomainCondition:
        """Validate `self` and return it if correct, otherwise raise an exception."""
        if not isinstance(self.field_expr, str) or not self.field_expr:
            self._raise("Empty field name", error=TypeError)
        op = self.operator.lower()
        if op != self.operator:
            warnings.warn(
                f"Deprecated since 19.0, the domain condition {(self.field_expr, self.operator, self.value)!r} should have a lower-case operator",
                DeprecationWarning, stacklevel=2,
            )
            return DomainCondition(self.field_expr, op, self.value).checked()
        if op not in CONDITION_OPERATORS:
            self._raise("Invalid operator")
        # check already the consistency for domain manipulation
        # these are common mistakes and optimizations, do them here to avoid recreating the domain
        # - NewId is not a value
        # - records are not accepted, use values
        # - Query and Domain values should be using a relational operator
        from ..models import BaseModel

        value = self.value
        if value is None:
            value = False
        elif isinstance(value, NewId):
            _logger.warning(
                "Domains don't support NewId, use .ids instead, for %r",
                (self.field_expr, self.operator, self.value),
            )
            op = "not in" if op in NEGATIVE_CONDITION_OPERATORS else "in"
            value = []
        elif isinstance(value, BaseModel):
            _logger.warning(
                "The domain condition %r should not have a value which is a model",
                (self.field_expr, self.operator, self.value),
            )
            value = value.ids
        elif isinstance(value, (Domain, Query, SQL)) and op not in (
            "any",
            "not any",
            "any!",
            "not any!",
            "in",
            "not in",
        ):
            # accept SQL object in the right part for simple operators
            # use case: compare 2 fields
            _logger.warning(
                "The domain condition %r should use the 'any' or 'not any' operator.",
                (self.field_expr, self.operator, self.value),
            )
        if value is not self.value:
            return DomainCondition(self.field_expr, op, value)
        return self

    def __invert__(self):
        # do it only for simple fields (not expressions)
        # inequalities are handled in _negate()
        if "." not in self.field_expr and (
            neg_op := INVERSE_OPERATOR.get(self.operator)
        ):
            return DomainCondition(self.field_expr, neg_op, self.value)
        return super().__invert__()

    def _negate(self, model):
        # inverse of the operators is handled by construction
        # except for inequalities for which we must know the field's type
        if neg_op := INVERSE_INEQUALITY.get(self.operator):
            # Inverse and add a self "or field is null"
            # when the field does not have a falsy value.
            # Having a falsy value is handled correctly in the SQL generation.
            condition = DomainCondition(self.field_expr, neg_op, self.value)
            if self._field(model).falsy_value is None:
                is_null = DomainCondition(self.field_expr, "in", OrderedSet([False]))
                condition = is_null | condition
            return condition

        return super()._negate(model)

    def __iter__(self):
        field_expr, op, value = self.field_expr, self.operator, self.value
        # if the value is a domain or set, change it into a list
        if isinstance(value, (*COLLECTION_TYPES, Domain)):
            value = list(value)
        yield (field_expr, op, value)

    def __eq__(self, other):
        return self is other or (
            isinstance(other, DomainCondition)
            and self.field_expr == other.field_expr
            and self.operator == other.operator
            # we want stricter equality than this: `OrderedSet([x]) == {x}`
            # to ensure that optimizations always return OrderedSet values
            and self.value.__class__ is other.value.__class__
            and self.value == other.value
        )

    def __hash__(self):
        return hash(self.field_expr) ^ hash(self.operator) ^ hash(self.value)

    def iter_conditions(self):
        yield self

    def map_conditions(self, function) -> Domain:
        result = function(self)
        assert isinstance(result, Domain), "result of map_conditions is not a Domain"
        return result

    def _raise(self, message: str, *args, error=ValueError) -> typing.NoReturn:
        """Raise an error message for this condition"""
        message += " in condition (%r, %r, %r)"
        raise error(message % (*args, self.field_expr, self.operator, self.value))

    def _field(self, model: BaseModel) -> Field:
        """Cached Field instance for the expression."""
        field = self._field_instance  # type: ignore[arg-type]
        if field is None or field.model_name != model._name:
            field, _ = self.__get_field(model)
        return field

    def __get_field(self, model: BaseModel) -> tuple[Field, str]:
        """Get the field or raise an exception"""
        field_name, property_name = parse_field_expr(self.field_expr)
        try:
            field = model._fields[field_name]
        except KeyError:
            self._raise("Invalid field %s.%s", model._name, field_name)
        # cache field value, with this hack to bypass immutability
        object.__setattr__(self, "_field_instance", field)
        return field, property_name or ""

    def _optimize_step(self, model: BaseModel, level: OptimizationLevel) -> Domain:
        """Optimization step.

        Apply some generic optimizations and then dispatch optimizations
        according to the operator and the type of the field.
        Optimize recursively until a fixed point is found.

        - Validate the field.
        - Decompose *paths* into domains using 'any'.
        - If the field is *not stored*, run the search function of the field.
        - Run optimizations.
        - Check the output.
        """
        assert (
            level is self._opt_level.next_level
        ), f"Trying to skip optimization level after {self._opt_level}"

        if level == OptimizationLevel.BASIC:
            # optimize path
            field, property_name = self.__get_field(model)
            if property_name and field.relational:
                sub_domain = DomainCondition(property_name, self.operator, self.value)
                return DomainCondition(field.name, "any", sub_domain)
        else:
            field = self._field(model)

        if level == OptimizationLevel.FULL:
            # resolve inherited fields
            # inherits implies both Field.delegate=True and Field.bypass_search_access=True
            # so no additional permissions will be added by the 'any' operator below
            if field.inherited:
                assert field.related
                parent_fname = field.related.split(".")[0]
                parent_domain = DomainCondition(
                    self.field_expr, self.operator, self.value
                )
                return DomainCondition(parent_fname, "any", parent_domain)

            # handle searchable fields
            if field.search and field.name == self.field_expr:
                domain = self._optimize_field_search_method(model)
                # The domain is optimized so that value data types are comparable.
                # Only simple optimization to avoid endless recursion.
                domain = domain.optimize(model)
                if domain != self:
                    return domain

        # apply optimizations of the level for operator and type
        optimizations = _OPTIMIZATIONS_FOR[level]
        for opt in optimizations.get(self.operator, ()):
            domain = opt(self, model)
            if domain != self:
                return domain
        for opt in optimizations.get(field.type, ()):
            domain = opt(self, model)
            if domain != self:
                return domain

        # final checks
        if (
            self.operator not in STANDARD_CONDITION_OPERATORS
            and level == OptimizationLevel.FULL
        ):
            self._raise("Not standard operator left")

        return self

    def _optimize_field_search_method(self, model: BaseModel) -> Domain:
        field = self._field(model)
        op, value = self.operator, self.value
        # use the `Field.search` function
        original_exception = None
        try:
            computed_domain = field.determine_domain(model, op, value)
        except (NotImplementedError, UserError) as e:
            computed_domain = NotImplemented
            original_exception = e
        else:
            if computed_domain is not NotImplemented:
                return Domain(computed_domain, internal=True)
        # try with the positive operator
        if original_exception is None and (inversed_op := INVERSE_OPERATOR.get(op)):
            computed_domain = field.determine_domain(model, inversed_op, value)
            if computed_domain is not NotImplemented:
                return ~Domain(computed_domain, internal=True)
        # compatibility for any!
        try:
            if op in ("any!", "not any!"):
                # Not strictly equivalent! If a search is executed, it will be done using sudo.
                computed_domain = DomainCondition(
                    self.field_expr, op.rstrip("!"), value
                )
                computed_domain = computed_domain._optimize_field_search_method(
                    model.sudo()
                )
                _logger.warning("Field %s should implement any! operator", field)
                return computed_domain
        except (NotImplementedError, UserError) as e:
            if original_exception is None:
                original_exception = e
        # backward compatibility to implement only '=' or '!='
        try:
            if op == "in":
                return Domain.OR(
                    Domain(field.determine_domain(model, "=", v), internal=True)
                    for v in value
                )
            elif op == "not in":
                return Domain.AND(
                    Domain(field.determine_domain(model, "!=", v), internal=True)
                    for v in value
                )
        except (NotImplementedError, UserError) as e:
            if original_exception is None:
                original_exception = e
        # raise the error
        if original_exception:
            raise original_exception
        raise UserError(
            model.env._(
                "Unsupported operator on %(field_label)s %(model_label)s in %(domain)s",
                domain=repr(self),
                field_label=self._field(model).get_description(model.env, ["string"])[
                    "string"
                ],
                model_label=f"{model.env['ir.model']._get(model._name).name!r} ({model._name})",
            )
        )

    def _as_predicate(self, records):
        if not records:
            return lambda _: False

        if self._opt_level < OptimizationLevel.DYNAMIC_VALUES:
            return self._optimize(
                records, OptimizationLevel.DYNAMIC_VALUES
            )._as_predicate(records)

        op = self.operator
        if op in ("child_of", "parent_of"):
            # Hierarchy operators need full optimization (parent_path expansion)
            # before they can become a predicate.  A specialized in-memory
            # implementation could avoid the SQL round-trip, but hierarchy
            # traversal is rare in predicate contexts — not worth optimizing.
            return self._optimize(records, OptimizationLevel.FULL)._as_predicate(
                records
            )

        assert op in STANDARD_CONDITION_OPERATORS, "Expecting a sub-set of operators"
        field_expr, value = self.field_expr, self.value
        positive_operator = NEGATIVE_CONDITION_OPERATORS.get(op, op)

        if isinstance(value, SQL):
            # transform into an Query value
            if positive_operator == op:
                condition = self
                op = "any!"
            else:
                condition = ~self
                op = "not any!"
            positive_operator = "any!"
            field_expr = "id"
            value = records.with_context(active_test=False)._search(
                DomainCondition("id", "in", OrderedSet(records.ids)) & condition
            )
            assert isinstance(value, Query)

        if isinstance(value, Query):
            # rebuild a domain with an 'in' values
            if positive_operator not in ("in", "any", "any!"):
                self._raise(
                    "Cannot filter using Query without the 'any' or 'in' operator"
                )
            if positive_operator != "in":
                op = "in" if positive_operator == op else "not in"
                positive_operator = "in"
            value = set(value.get_result_ids())
            return DomainCondition(field_expr, op, value)._as_predicate(records)

        field = self._field(records)
        if field_expr == "display_name":
            # when searching by name, ignore AccessError
            field_expr = "display_name.no_error"
        elif field_expr == "id":
            # for new records, compare to their origin
            field_expr = "id.origin"

        func = field.filter_function(records, field_expr, positive_operator, value)
        return func if positive_operator == op else lambda rec: not func(rec)

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        field_expr, op, value = self.field_expr, self.operator, self.value
        assert (
            op in STANDARD_CONDITION_OPERATORS
        ), f"Invalid operator {op!r} for SQL in domain term {(field_expr, op, value)!r}"
        assert (
            self._opt_level >= OptimizationLevel.FULL
        ), f"Must fully optimize before generating the query {(field_expr, op, value)}"

        field = self._field(model)
        model._check_field_access(field, "read")
        return field.condition_to_sql(field_expr, op, value, model, alias, query)


# Update ANY_TYPES now that Domain is defined
ANY_TYPES = (Domain, Query, SQL)

__all__ = [
    "ANY_TYPES",
    "MAX_OPTIMIZE_ITERATIONS",
    "_FALSE_DOMAIN",
    "_MERGE_OPTIMIZATIONS",
    "_OPTIMIZATIONS_FOR",
    # Singletons
    "_TRUE_DOMAIN",
    # Domain classes
    "Domain",
    "DomainAnd",
    "DomainBool",
    "DomainCondition",
    "DomainCustom",
    "DomainNary",
    "DomainNot",
    "DomainOr",
    # Optimization infrastructure
    "OptimizationLevel",
    "_optimize_nary_sort_key",
]
