# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Domain expression processing

The domain represents a first-order logical expression.
The main duty of this module is to represent filter conditions on models
and ease rewriting them.
A lot of things should be documented here, but as a first
step in the right direction, some tests in test_expression.py
might give you some additional information.

The `Domain` is represented as an AST which is a predicate using boolean
operators.
- n-ary operators: AND, OR
- unary operator: NOT
- boolean constants: TRUE, FALSE
- (simple) conditions: (expression, operator, value)

Conditions are triplets of `(expression, operator, value)`.
`expression` is usually a field name. It can be an expression that uses the
dot-notation to traverse relationships or accesses properties of the field.
The traversal of relationships is equivalent to using the `any` operator.
`operator` in one of the CONDITION_OPERATORS, the detailed description of what
is possible is documented there.
`value` is a Python value which should be supported by the operator.


For legacy reasons, a domain uses an inconsistent two-levels abstract
syntax (domains were a regular Python data structures). At the first
level, a domain is an expression made of conditions and domain operators
used in prefix notation. The available operators at this level are
'!', '&', and '|'. '!' is a unary 'not', '&' is a binary 'and',
and '|' is a binary 'or'.
For instance, here is a possible domain. (<cond> stands for an arbitrary
condition, more on this later.):

    ['&', '!', <cond>, '|', <cond2>, <cond3>]

It is equivalent to this pseudo code using infix notation::

    (not <cond1>) and (<cond2> or <cond3>)

The second level of syntax deals with the condition representation. A condition
is a triple of the form (left, operator, right). That is, a condition uses
an infix notation, and the available operators, and possible left and
right operands differ with those of the previous level. Here is a
possible condition:

    ('company_id.name', '=', 'Odoo')
"""
from __future__ import annotations

import collections
import enum
import functools
import itertools
import logging
import operator
import pytz
import typing
import warnings
from datetime import date, datetime, time, timedelta, timezone

from odoo.exceptions import UserError
from odoo.tools import SQL, OrderedSet, Query, classproperty, partition, str2bool
from odoo.tools.date_utils import parse_date, parse_iso_date
from .identifiers import NewId
from .utils import COLLECTION_TYPES, parse_field_expr

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable
    from .fields import Field
    from .models import BaseModel

    M = typing.TypeVar('M', bound=BaseModel)


_logger = logging.getLogger('odoo.domains')

STANDARD_CONDITION_OPERATORS = frozenset([
    'any', 'not any',
    'any!', 'not any!',
    'in', 'not in',
    '<', '>', '<=', '>=',
    'like', 'not like',
    'ilike', 'not ilike',
    '=like', 'not =like',
    '=ilike', 'not =ilike',
])
"""List of standard operators for conditions.
This should be supported in the framework at all levels.

- `any` works for relational fields and `id` to check if a record matches
  the condition
  - if value is SQL or Query, see `any!`
  - if bypass_search_access is set on the field, see `any!`
  - if value is a Domain for a many2one (or `id`),
    _search with active_test=False
  - if value is a Domain for a x2many,
    _search on the comodel of the field (with its context)
- `any!` works like `any` but bypass adding record rules on the comodel
- `in` for equality checks where the given value is a collection of values
  - the collection is transformed into OrderedSet
  - False value indicates that the value is *not set*
  - for relational fields
    - if int, bypass record rules
    - if str, search using display_name of the model
  - the value should have the type of the field
  - SQL type is always accepted
- `<`, `>`, ... inequality checks, similar behaviour to `in` with a single value
- string pattern comparison
  - `=like` case-sensitive compare to a string using SQL like semantics
  - `=ilike` case-insensitive with `unaccent` comparison to a string
  - `like`, `ilike` behave like the preceding methods, but add a wildcards
    around the value
"""
CONDITION_OPERATORS = set(STANDARD_CONDITION_OPERATORS)  # modifiable (for optimizations only)
"""
List of available operators for conditions.
The non-standard operators can be reduced to standard operators by using the
optimization function. See the respective optimization functions for the
details.
"""

NEGATIVE_CONDITION_OPERATORS = {
    'not any': 'any',
    'not any!': 'any!',
    'not in': 'in',
    'not like': 'like',
    'not ilike': 'ilike',
    'not =like': '=like',
    'not =ilike': '=ilike',
    '!=': '=',
    '<>': '=',
}
"""A subset of operators with a 'negative' semantic, mapping to the 'positive' operator."""

# negations for operators (used in DomainNot)
_INVERSE_OPERATOR = {
    # from NEGATIVE_CONDITION_OPERATORS
    'not any': 'any',
    'not any!': 'any!',
    'not in': 'in',
    'not like': 'like',
    'not ilike': 'ilike',
    'not =like': '=like',
    'not =ilike': '=ilike',
    '!=': '=',
    '<>': '=',
    # positive to negative
    'any': 'not any',
    'any!': 'not any!',
    'in': 'not in',
    'like': 'not like',
    'ilike': 'not ilike',
    '=like': 'not =like',
    '=ilike': 'not =ilike',
    '=': '!=',
}
"""Dict to find the inverses of the operators."""
_INVERSE_INEQUALITY = {
    '<': '>=',
    '>': '<=',
    '>=': '<',
    '<=': '>',
}
""" Dict to find the inverse of inequality operators.
Handled differently because of null values."""

_TRUE_LEAF = (1, '=', 1)
_FALSE_LEAF = (0, '=', 1)


class OptimizationLevel(enum.IntEnum):
    """Indicator whether the domain was optimized."""
    NONE = 0
    BASIC = enum.auto()
    DYNAMIC_VALUES = enum.auto()
    FULL = enum.auto()


MAX_OPTIMIZE_ITERATIONS = 1000


# --------------------------------------------------
# Domain definition and manipulation
# --------------------------------------------------

class Domain:
    """Representation of a domain as an AST.
    """
    # Domain is an abstract class (ABC), but not marked as such
    # because we overwrite __new__ so typechecking for abstractmethod is incorrect.
    # We do this so that we can use the Domain as both a factory for multiple
    # types of domains, while still having `isinstance` working for it.
    __slots__ = ('_opt_level',)
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
            if args == _TRUE_LEAF:
                return _TRUE_DOMAIN
            if args == _FALSE_LEAF:
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
        stack: list[Domain] = []
        try:
            for item in reversed(arg):
                if isinstance(item, (tuple, list)) and len(item) == 3:
                    if internal:
                        # process subdomains when processing internal operators
                        if item[1] in ('any', 'any!', 'not any', 'not any!') and isinstance(item[2], (list, tuple)):
                            item = (item[0], item[1], Domain(item[2], internal=True))
                    elif item[1] in ('any!', 'not any!'):
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
    def TRUE(cls) -> Domain:
        return _TRUE_DOMAIN

    @classproperty
    def FALSE(cls) -> Domain:
        return _FALSE_DOMAIN

    @staticmethod
    def is_negative_operator(operator: str) -> bool:
        return operator in NEGATIVE_CONDITION_OPERATORS

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
        if hasattr(self, name):
            raise TypeError("Domain objects are immutable")
        return super().__setattr__(name, value)

    def __and__(self, other):
        """Domain & Domain"""
        if isinstance(other, Domain):
            return DomainAnd.apply([self, other])
        return NotImplemented

    def __or__(self, other):
        """Domain | Domain"""
        if isinstance(other, Domain):
            return DomainOr.apply([self, other])
        return NotImplemented

    def __invert__(self):
        """~Domain"""
        return DomainNot(self)

    def _negate(self, model: BaseModel) -> Domain:
        """Apply (propagate) negation onto this domain. """
        return ~self

    def __add__(self, other):
        """Domain + [...]

        For backward-compatibility of domain composition.
        Concatenate as lists.
        If we have two domains, equivalent to '&'.
        """
        # TODO deprecate this possibility so that users combine domains correctly
        if isinstance(other, Domain):
            return self & other
        if not isinstance(other, list):
            raise TypeError('Domain() can concatenate only lists')
        return list(self) + other

    def __radd__(self, other):
        """Commutative definition of *+*"""
        # TODO deprecate this possibility so that users combine domains correctly
        # we are pre-pending, return a list
        # because the result may not be normalized
        return other + list(self)

    def __bool__(self):
        """Indicate that the domain is not true.

        For backward-compatibility, only the domain [] was False. Which means
        that the TRUE domain is falsy and others are truthy.
        """
        # TODO deprecate this usage, we have is_true() and is_false()
        # warnings.warn("Do not use bool() on Domain, use is_true() or is_false() instead", DeprecationWarning)
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
            next_level = OptimizationLevel(domain._opt_level + 1)
            previous, domain = domain, domain._optimize_step(model, next_level)
            # set the optimization level if necessary (unlike DomainBool, for instance)
            if domain == previous and domain._opt_level < next_level:
                object.__setattr__(domain, '_opt_level', next_level)  # noqa: PLC2801
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
    __slots__ = ('value',)
    value: bool

    def __new__(cls, value: bool):
        """Create a constant domain."""
        self = object.__new__(cls)
        self.value = value
        self._opt_level = OptimizationLevel.FULL
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
        yield _TRUE_LEAF if self.value else _FALSE_LEAF

    def _as_predicate(self, records):
        return lambda _: self.value

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        return SQL("TRUE") if self.value else SQL("FALSE")


# singletons, available though Domain.TRUE and Domain.FALSE
_TRUE_DOMAIN = DomainBool(True)
_FALSE_DOMAIN = DomainBool(False)


class DomainNot(Domain):
    """Negation domain, contains a single child"""
    OPERATOR = '!'

    __slots__ = ('child',)
    child: Domain

    def __new__(cls, child: Domain):
        """Create a domain which is the inverse of the child."""
        self = object.__new__(cls)
        self.child = child
        self._opt_level = OptimizationLevel.NONE
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
        return self is other or (isinstance(other, DomainNot) and self.child == other.child)

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

    __slots__ = ('children',)
    children: list[Domain]

    def __new__(cls, children: list[Domain]):
        """Create the n-ary domain with at least 2 conditions."""
        assert len(children) >= 2
        self = object.__new__(cls)
        self.children = children
        self._opt_level = OptimizationLevel.NONE
        return self

    @classmethod
    def apply(cls, items: Iterable[Domain]) -> Domain:
        """Return the result of combining AND/OR to a collection of domains."""
        children = cls._flatten(items)
        if len(children) == 1:
            return children[0]
        return cls(children)

    @classmethod
    def _flatten(cls, children: Iterable[Domain]) -> list[Domain]:
        """Return an equivalent list of domains with respect to the boolean
        operation of the class (AND/OR).  Boolean subdomains are simplified,
        and subdomains of the same class are flattened into the list.
        The returned list is never empty.
        """
        result = []
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
        return hash(self.OPERATOR) ^ hash(tuple(self.children))

    @classproperty
    def INVERSE(cls) -> type[DomainNary]:
        """Return the inverted nary type, AND/OR"""
        raise NotImplementedError

    def __invert__(self):
        return self.INVERSE([~child for child in self.children])

    def _negate(self, model):
        return self.INVERSE([child._negate(model) for child in self.children])

    def iter_conditions(self):
        for child in self.children:
            yield from child.iter_conditions()

    def map_conditions(self, function) -> Domain:
        return self.apply(child.map_conditions(function) for child in self.children)

    def _optimize_step(self, model: BaseModel, level: OptimizationLevel) -> Domain:
        # optimize children
        children = self._flatten(child._optimize(model, level) for child in self.children)
        size = len(children)
        if size > 1:
            # sort children in order to ease their grouping by field and operator
            children.sort(key=_optimize_nary_sort_key)
            # run optimizations until some merge happens
            for merge in _MERGE_OPTIMIZATIONS:
                children = list(merge(type(self), children, model))
                if len(children) < size:
                    break
        return self.apply(children)

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        return SQL("(%s)", self.OPERATOR_SQL.join(
            c._to_sql(model, alias, query)
            for c in self.children
        ))


class DomainAnd(DomainNary):
    """Domain: AND with multiple children"""
    __slots__ = ()
    OPERATOR = '&'
    OPERATOR_SQL = SQL(" AND ")
    ZERO = _TRUE_DOMAIN

    @classproperty
    def INVERSE(cls) -> type[DomainNary]:
        return DomainOr

    def __and__(self, other):
        # simple optimization to append children
        if isinstance(other, DomainAnd):
            return DomainAnd(self.children + other.children)
        return super().__and__(other)

    def _as_predicate(self, records):
        # For the sake of performance, the list of predicates is generated
        # lazily with a generator, which is memoized with `itertools.tee`
        all_predicates = (child._as_predicate(records) for child in self.children)

        def and_predicate(record):
            nonlocal all_predicates
            all_predicates, predicates = itertools.tee(all_predicates)
            return all(pred(record) for pred in predicates)

        return and_predicate


class DomainOr(DomainNary):
    """Domain: OR with multiple children"""
    __slots__ = ()
    OPERATOR = '|'
    OPERATOR_SQL = SQL(" OR ")
    ZERO = _FALSE_DOMAIN

    @classproperty
    def INVERSE(cls) -> type[DomainNary]:
        return DomainAnd

    def __or__(self, other):
        # simple optimization to append children
        if isinstance(other, DomainOr):
            return DomainOr(self.children + other.children)
        return super().__or__(other)

    def _as_predicate(self, records):
        # For the sake of performance, the list of predicates is generated
        # lazily with a generator, which is memoized with `itertools.tee`
        all_predicates = (child._as_predicate(records) for child in self.children)

        def or_predicate(record):
            nonlocal all_predicates
            all_predicates, predicates = itertools.tee(all_predicates)
            return any(pred(record) for pred in predicates)

        return or_predicate


class DomainCustom(Domain):
    """Domain condition that generates directly SQL and possibly a ``filtered`` predicate."""
    __slots__ = ('_filtered', '_sql')

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
        self._sql = sql
        self._filtered = filtered
        self._opt_level = OptimizationLevel.FULL
        return self

    def _as_predicate(self, records):
        if self._filtered is not None:
            return self._filtered
        # by default, run the SQL query
        query = records._search(DomainCondition('id', 'in', records.ids) & self, order='id')
        return DomainCondition('id', 'any', query)._as_predicate(records)

    def __eq__(self, other):
        return (
            isinstance(other, DomainCustom)
            and self._sql == other._sql
            and self._filtered == other._filtered
        )

    def __hash__(self):
        return hash(self._sql)

    def __iter__(self):
        yield self

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        return self._sql(model, alias, query)


class DomainCondition(Domain):
    """Domain condition on field: (field, operator, value)

    A field (or expression) is compared to a value. The list of supported
    operators are described in CONDITION_OPERATORS.
    """
    __slots__ = ('_field_instance', 'field_expr', 'operator', 'value')
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
        self.field_expr = field_expr
        self.operator = operator
        self.value = value
        self._field_instance = None
        self._opt_level = OptimizationLevel.NONE
        return self

    def checked(self) -> DomainCondition:
        """Validate `self` and return it if correct, otherwise raise an exception."""
        if not isinstance(self.field_expr, str) or not self.field_expr:
            self._raise("Empty field name", error=TypeError)
        operator = self.operator.lower()
        if operator != self.operator:
            warnings.warn(f"Deprecated since 19.0, the domain condition {(self.field_expr, self.operator, self.value)!r} should have a lower-case operator", DeprecationWarning)
            return DomainCondition(self.field_expr, operator, self.value).checked()
        if operator not in CONDITION_OPERATORS:
            self._raise("Invalid operator")
        # check already the consistency for domain manipulation
        # these are common mistakes and optimizations, do them here to avoid recreating the domain
        # - NewId is not a value
        # - records are not accepted, use values
        # - Query and Domain values should be using a relational operator
        from .models import BaseModel  # noqa: PLC0415
        value = self.value
        if value is None:
            value = False
        elif isinstance(value, NewId):
            _logger.warning("Domains don't support NewId, use .ids instead, for %r", (self.field_expr, self.operator, self.value))
            operator = 'not in' if operator in NEGATIVE_CONDITION_OPERATORS else 'in'
            value = []
        elif isinstance(value, BaseModel):
            _logger.warning("The domain condition %r should not have a value which is a model", (self.field_expr, self.operator, self.value))
            value = value.ids
        elif isinstance(value, (Domain, Query, SQL)) and operator not in ('any', 'not any', 'any!', 'not any!', 'in', 'not in'):
            # accept SQL object in the right part for simple operators
            # use case: compare 2 fields
            _logger.warning("The domain condition %r should use the 'any' or 'not any' operator.", (self.field_expr, self.operator, self.value))
        if value is not self.value:
            return DomainCondition(self.field_expr, operator, value)
        return self

    def __invert__(self):
        # do it only for simple fields (not expressions)
        # inequalities are handled in _negate()
        if "." not in self.field_expr and (neg_op := _INVERSE_OPERATOR.get(self.operator)):
            return DomainCondition(self.field_expr, neg_op, self.value)
        return super().__invert__()

    def _negate(self, model):
        # inverse of the operators is handled by construction
        # except for inequalities for which we must know the field's type
        if neg_op := _INVERSE_INEQUALITY.get(self.operator):
            # Inverse and add a self "or field is null"
            # when the field does not have a falsy value.
            # Having a falsy value is handled correctly in the SQL generation.
            condition = DomainCondition(self.field_expr, neg_op, self.value)
            if self._field(model).falsy_value is None:
                is_null = DomainCondition(self.field_expr, 'in', OrderedSet([False]))
                condition = is_null | condition
            return condition

        return super()._negate(model)

    def __iter__(self):
        field_expr, operator, value = self.field_expr, self.operator, self.value
        # if the value is a domain or set, change it into a list
        if isinstance(value, (*COLLECTION_TYPES, Domain)):
            value = list(value)
        yield (field_expr, operator, value)

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
        message += ' in condition (%r, %r, %r)'
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
        object.__setattr__(self, '_field_instance', field)
        return field, property_name or ''

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
        assert level == self._opt_level + 1, f"Trying to skip optimization level after {self._opt_level}"

        # optimize path
        field, property_name = self.__get_field(model)
        if property_name and field.relational:
            sub_domain = DomainCondition(property_name, self.operator, self.value)
            return DomainCondition(field.name, 'any', sub_domain)

        if level == OptimizationLevel.FULL:
            # resolve inherited fields
            # inherits implies both Field.delegate=True and Field.bypass_search_access=True
            # so no additional permissions will be added by the 'any' operator below
            if field.inherited:
                parent_fname = field.related.split('.')[0]
                parent_domain = DomainCondition(self.field_expr, self.operator, self.value)
                return DomainCondition(parent_fname, 'any', parent_domain)

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
        if self.operator not in STANDARD_CONDITION_OPERATORS and level == OptimizationLevel.FULL:
            self._raise("Not standard operator left")

        return self

    def _optimize_field_search_method(self, model: BaseModel) -> Domain:
        field = self._field(model)
        operator, value = self.operator, self.value
        # use the `Field.search` function
        original_exception = None
        try:
            computed_domain = field.determine_domain(model, operator, value)
        except (NotImplementedError, UserError) as e:
            computed_domain = NotImplemented
            original_exception = e
        else:
            if computed_domain is not NotImplemented:
                return Domain(computed_domain, internal=True)
        # try with the positive operator
        if (
            original_exception is None
            and (inversed_opeator := _INVERSE_OPERATOR.get(operator))
        ):
            computed_domain = field.determine_domain(model, inversed_opeator, value)
            if computed_domain is not NotImplemented:
                return ~Domain(computed_domain, internal=True)
        # compatibility for any!
        try:
            if operator in ('any!', 'not any!'):
                # Not strictly equivalent! If a search is executed, it will be done using sudo.
                computed_domain = DomainCondition(self.field_expr, operator.rstrip('!'), value)
                computed_domain = computed_domain._optimize_field_search_method(model.sudo())
                _logger.warning("Field %s should implement any! operator", field)
                return computed_domain
        except (NotImplementedError, UserError) as e:
            if original_exception is None:
                original_exception = e
        # backward compatibility to implement only '=' or '!='
        try:
            if operator == 'in':
                return Domain.OR(Domain(field.determine_domain(model, '=', v), internal=True) for v in value)
            elif operator == 'not in':
                return Domain.AND(Domain(field.determine_domain(model, '!=', v), internal=True) for v in value)
        except (NotImplementedError, UserError) as e:
            if original_exception is None:
                original_exception = e
        # raise the error
        if original_exception:
            raise original_exception
        raise UserError(model.env._(
            "Unsupported operator on %(field_label)s %(model_label)s in %(domain)s",
            domain=repr(self),
            field_label=self._field(model).get_description(model.env, ['string'])['string'],
            model_label=f"{model.env['ir.model']._get(model._name).name!r} ({model._name})",
        ))

    def _as_predicate(self, records):
        if not records:
            return lambda _: False

        if self._opt_level < OptimizationLevel.DYNAMIC_VALUES:
            return self._optimize(records, OptimizationLevel.DYNAMIC_VALUES)._as_predicate(records)

        operator = self.operator
        if operator in ('child_of', 'parent_of'):
            # TODO have a specific implementation for these
            return self._optimize(records, OptimizationLevel.FULL)._as_predicate(records)

        assert operator in STANDARD_CONDITION_OPERATORS, "Expecting a sub-set of operators"
        field_expr, value = self.field_expr, self.value
        positive_operator = NEGATIVE_CONDITION_OPERATORS.get(operator, operator)

        if isinstance(value, SQL):
            # transform into an Query value
            if positive_operator == operator:
                condition = self
                operator = 'any!'
            else:
                condition = ~self
                operator = 'not any!'
            positive_operator = 'any!'
            field_expr = 'id'
            value = records.with_context(active_test=False)._search(DomainCondition('id', 'in', OrderedSet(records.ids)) & condition)
            assert isinstance(value, Query)

        if isinstance(value, Query):
            # rebuild a domain with an 'in' values
            if positive_operator not in ('in', 'any', 'any!'):
                self._raise("Cannot filter using Query without the 'any' or 'in' operator")
            if positive_operator != 'in':
                operator = 'in' if positive_operator == operator else 'not in'
                positive_operator = 'in'
            value = set(value.get_result_ids())
            return DomainCondition(field_expr, operator, value)._as_predicate(records)

        field = self._field(records)
        if field_expr == 'display_name':
            # when searching by name, ignore AccessError
            field_expr = 'display_name.no_error'
        elif field_expr == 'id':
            # for new records, compare to their origin
            field_expr = 'id.origin'

        func = field.filter_function(records, field_expr, positive_operator, value)
        return func if positive_operator == operator else lambda rec: not func(rec)

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        field_expr, operator, value = self.field_expr, self.operator, self.value
        assert operator in STANDARD_CONDITION_OPERATORS, \
            f"Invalid operator {operator!r} for SQL in domain term {(field_expr, operator, value)!r}"
        assert self._opt_level >= OptimizationLevel.FULL, \
            f"Must fully optimize before generating the query {(field_expr, operator, value)}"

        field = self._field(model)
        model._check_field_access(field, 'read')
        return field.condition_to_sql(field_expr, operator, value, model, alias, query)


# --------------------------------------------------
# Optimizations: registration
# --------------------------------------------------

ANY_TYPES = (Domain, Query, SQL)

if typing.TYPE_CHECKING:
    ConditionOptimization = Callable[[DomainCondition, BaseModel], Domain]
    MergeOptimization = Callable[[type[DomainNary], list[Domain], BaseModel], Iterable[Domain]]

_OPTIMIZATIONS_FOR: dict[OptimizationLevel, dict[str, list[ConditionOptimization]]] = {
    level: collections.defaultdict(list) for level in OptimizationLevel if level != OptimizationLevel.NONE}
_MERGE_OPTIMIZATIONS: list[MergeOptimization] = list()


def operator_optimization(operators: Collection[str], level: OptimizationLevel = OptimizationLevel.BASIC):
    """Register a condition operator optimization for (condition, model)"""
    assert operators, "Missing operator to register"
    CONDITION_OPERATORS.update(operators)

    def register(optimization: ConditionOptimization):
        mapping = _OPTIMIZATIONS_FOR[level]
        for operator in operators:  # noqa: F402
            mapping[operator].append(optimization)
        return optimization

    return register


def field_type_optimization(field_types: Collection[str], level: OptimizationLevel = OptimizationLevel.BASIC):
    """Register a condition optimization by field type for (condition, model)"""
    def register(optimization: ConditionOptimization):
        mapping = _OPTIMIZATIONS_FOR[level]
        for field_type in field_types:
            mapping[field_type].append(optimization)
        return optimization

    return register


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
        operator = domain.operator
        positive_op = NEGATIVE_CONDITION_OPERATORS.get(operator, operator)
        if positive_op == 'in':
            order = "0in"
        elif positive_op == 'any':
            order = "1any"
        elif positive_op == 'any!':
            order = "2any"
        elif positive_op.endswith('like'):
            order = "like"
        else:
            order = positive_op
        return domain.field_expr, order, operator
    elif hasattr(domain, 'OPERATOR') and isinstance(domain.OPERATOR, str):
        # in python; '~' > any letter
        return '~', '', domain.OPERATOR
    else:
        return '~', '~', domain.__class__.__name__


def nary_optimization(optimization: MergeOptimization):
    """Register an optimization to a list of children of an nary domain.

    The function will take an iterable containing optimized children of a
    n-ary domain and returns *optimized* domains.

    Note that you always need to optimize both AND and OR domains. It is always
    possible because if you can optimize `a & b` then you can optimize `a | b`
    because it is optimizing `~(~a & ~b)`. Since operators can be negated,
    all implementations of optimizations are implemented in a mirrored way:
    `(optimize AND) if some_condition == cls.ZERO.value else (optimize OR)`.

    The optimization of nary domains starts by optimizing the children,
    then sorts them by (field, operator_type, operator) where operator type
    groups similar operators together.
    """
    _MERGE_OPTIMIZATIONS.append(optimization)
    return optimization


def nary_condition_optimization(operators: Collection[str], field_types: Collection[str] | None = None):
    """Register an optimization for condition children of an nary domain.

    The function will take a list of domain conditions of the same field and
    returns *optimized* domains.

    This is a adapter function that uses `nary_optimization`.

    NOTE: if you want to merge different operators, register for
    `operator=CONDITION_OPERATORS` and find conditions that you want to merge.
    """
    def grouping_key(domain):
        return domain.field_expr if isinstance(domain, DomainCondition) and domain.operator in operators else None

    def register(optimization: Callable[[type[DomainNary], list[DomainCondition], BaseModel], Iterable[Domain]]):
        @nary_optimization
        def optimizer(cls, domains, model):
            # group domains by field_expr
            for field_expr, doms in itertools.groupby(domains, grouping_key):
                if field_expr:
                    conditions = list(doms)
                    if len(conditions) > 1 and (
                        field_types is None or conditions[0]._field(model).type in field_types
                    ):
                        yield from optimization(cls, conditions, model)
                    else:
                        yield from conditions
                else:
                    yield from doms
        return optimization

    return register


# --------------------------------------------------
# Optimizations: conditions
# --------------------------------------------------


@operator_optimization(['=?'])
def _operator_equal_if_value(condition, _):
    """a =? b  <=>  not b or a = b"""
    if not condition.value:
        return _TRUE_DOMAIN
    return DomainCondition(condition.field_expr, '=', condition.value)


@operator_optimization(['<>'])
def _operator_different(condition, _):
    """a <> b  =>  a != b"""
    # already a rewrite-rule
    warnings.warn("Operator '<>' is deprecated since 19.0, use '!=' directly", DeprecationWarning)
    return DomainCondition(condition.field_expr, '!=', condition.value)


@operator_optimization(['=='])
def _operator_equals(condition, _):
    """a == b  =>  a = b"""
    # rewrite-rule
    warnings.warn("Operator '==' is deprecated since 19.0, use '=' directly", DeprecationWarning)
    return DomainCondition(condition.field_expr, '=', condition.value)


@operator_optimization(['=', '!='])
def _operator_equal_as_in(condition, _):
    """ Equality operators.

    Validation for some types and translate collection into 'in'.
    """
    value = condition.value
    operator = 'in' if condition.operator == '=' else 'not in'
    if isinstance(value, COLLECTION_TYPES):
        # TODO make a warning or equality against a collection
        if not value:  # views sometimes use ('user_ids', '!=', []) to indicate the user is set
            _logger.debug("The domain condition %r should compare with False.", condition)
            value = OrderedSet([False])
        else:
            _logger.debug("The domain condition %r should use the 'in' or 'not in' operator.", condition)
            value = OrderedSet(value)
    elif isinstance(value, SQL):
        # transform '=' SQL("x") into 'in' SQL("(x)")
        value = SQL("(%s)", value)
    else:
        value = OrderedSet((value,))
    return DomainCondition(condition.field_expr, operator, value)


@operator_optimization(['in', 'not in'])
def _optimize_in_set(condition, _model):
    """Make sure the value is an OrderedSet or use 'any' operator"""
    value = condition.value
    if isinstance(value, ANY_TYPES):
        operator = 'any' if condition.operator == 'in' else 'not any'
        return DomainCondition(condition.field_expr, operator, value)
    if not value:
        return _FALSE_DOMAIN if condition.operator == 'in' else _TRUE_DOMAIN
    if not isinstance(value, COLLECTION_TYPES):
        # TODO show warning, note that condition.field_expr in ('group_ids', 'user_ids') gives a lot of them
        _logger.debug("The domain condition %r should have a list value.", condition)
        value = [value]
    return DomainCondition(condition.field_expr, condition.operator, OrderedSet(value))


@operator_optimization(['in', 'not in'])
def _optimize_in_required(condition, model):
    """Remove checks against a null value for required fields."""
    value = condition.value
    field = condition._field(model)
    if (
        field.falsy_value is None
        and (field.required or field.name == 'id')
        and field in model.env.registry.not_null_fields
        # only optimize if there are no NewId's
        and all(model._ids)
    ):
        value = OrderedSet(v for v in value if v is not False)
    if len(value) == len(condition.value):
        return condition
    return DomainCondition(condition.field_expr, condition.operator, value)


@operator_optimization(['any', 'not any', 'any!', 'not any!'])
def _optimize_any_domain(condition, model):
    """Make sure the value is an optimized domain (or Query or SQL)"""
    value = condition.value
    if isinstance(value, ANY_TYPES) and not isinstance(value, Domain):
        if '!' not in condition.operator:
            # update operator to 'any!'
            return DomainCondition(condition.field_expr, condition.operator + '!', condition.value)
        return condition
    domain = Domain(value)
    field = condition._field(model)
    if field.name == 'id':
        # id ANY domain  <=>  domain
        # id NOT ANY domain  <=>  ~domain
        return domain if condition.operator in ('any', 'any!') else ~domain
    # get the model to optimize with
    try:
        comodel = model.env[field.comodel_name]
    except KeyError:
        condition._raise("Cannot determine the comodel relation")
    domain = domain._optimize(comodel, OptimizationLevel.BASIC)
    # const if the domain is empty, the result is a constant
    # if the domain is True, we keep it as is
    if domain.is_false():
        return _FALSE_DOMAIN if condition.operator in ('any', 'any!') else _TRUE_DOMAIN
    return DomainCondition(condition.field_expr, condition.operator, domain)


# register and bind multiple levels later
def _optimize_any_domain_at_level(level: OptimizationLevel, condition, model):
    domain = condition.value
    if not isinstance(domain, Domain):
        return condition
    field = condition._field(model)
    if not field.relational:
        condition._raise("Cannot use 'any' with non-relational fields")
    try:
        comodel = model.env[field.comodel_name]
    except KeyError:
        condition._raise("Cannot determine the comodel relation")
    domain = domain._optimize(comodel, level)
    return DomainCondition(condition.field_expr, condition.operator, domain)


[
    operator_optimization(('any', 'not any', 'any!', 'not any!'), level)(functools.partial(_optimize_any_domain_at_level, level))
    for level in OptimizationLevel
    if level > OptimizationLevel.BASIC
]


@operator_optimization([op for op in CONDITION_OPERATORS if op.endswith('like')])
def _optimize_like_str(condition, model):
    """Validate value for pattern matching, must be a str"""
    value = condition.value
    if not value:
        # =like matches only empty string (inverse the condition)
        result = (condition.operator in NEGATIVE_CONDITION_OPERATORS) == ('=' in condition.operator)
        # relational and non-relation fields behave differently
        if condition._field(model).relational or '=' in condition.operator:
            return DomainCondition(condition.field_expr, '!=' if result else '=', False)
        return Domain(result)
    if isinstance(value, str):
        return condition
    if isinstance(value, SQL):
        warnings.warn("Since 19.0, use Domain.custom(to_sql=lambda model, alias, query: SQL(...))", DeprecationWarning)
        return condition
    if '=' in condition.operator:
        condition._raise("The pattern to match must be a string", error=TypeError)
    return DomainCondition(condition.field_expr, condition.operator, str(value))


@field_type_optimization(['many2one', 'one2many', 'many2many'])
def _optimize_relational_name_search(condition, model):
    """Search relational using `display_name`.

    When a relational field is compared to a string, we actually want to make
    a condition on the `display_name` field.
    Negative conditions are translated into a "not any" for consistency.
    """
    operator = condition.operator
    value = condition.value
    positive_operator = NEGATIVE_CONDITION_OPERATORS.get(operator, operator)
    any_operator = 'any' if positive_operator == operator else 'not any'
    # Handle like operator
    if operator.endswith('like'):
        return DomainCondition(
            condition.field_expr,
            any_operator,
            DomainCondition('display_name', positive_operator, value),
        )
    # Handle inequality as not supported
    if operator[0] in ('<', '>') and isinstance(value, str):
        condition._raise("Inequality not supported for relational field using a string", error=TypeError)
    # Handle equality with str values
    if positive_operator != 'in' or not isinstance(value, COLLECTION_TYPES):
        return condition
    str_values, other_values = partition(lambda v: isinstance(v, str), value)
    if not str_values:
        return condition
    domain = DomainCondition(
        condition.field_expr,
        any_operator,
        DomainCondition('display_name', positive_operator, str_values),
    )
    if other_values:
        if positive_operator == operator:
            domain |= DomainCondition(condition.field_expr, operator, other_values)
        else:
            domain &= DomainCondition(condition.field_expr, operator, other_values)
    return domain


@field_type_optimization(['boolean'])
def _optimize_boolean_in(condition, model):
    """b in boolean_values"""
    value = condition.value
    operator = condition.operator
    if operator not in ('in', 'not in') or not isinstance(value, COLLECTION_TYPES):
        condition._raise("Cannot compare %r to %s which is not a collection of length 1", condition.field_expr, type(value))
    if not all(isinstance(v, bool) for v in value):
        # parse the values
        if any(isinstance(v, str) for v in value):
            # TODO make a warning
            _logger.debug("Comparing boolean with a string in %s", condition)
        value = {
            str2bool(v.lower(), False) if isinstance(v, str) else bool(v)
            for v in value
        }
    if len(value) == 1 and not any(value):
        # when comparing boolean values, always compare to [True] if possible
        # it eases the implementation of search methods
        operator = _INVERSE_OPERATOR[operator]
        value = [True]
    return DomainCondition(condition.field_expr, operator, value)


@field_type_optimization(['boolean'], OptimizationLevel.FULL)
def _optimize_boolean_in_all(condition, model):
    """b in [True, False]  =>  True"""
    if isinstance(condition.value, COLLECTION_TYPES) and set(condition.value) == {False, True}:
        # tautology is simplified to a boolean
        # note that this optimization removes fields (like active) from the domain
        # so we do this only on FULL level to avoid removing it from sub-domains
        return Domain(condition.operator == 'in')
    return condition


def _value_to_date(value, env, iso_only=False):
    # check datetime first, because it's a subclass of date
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date) or value is False:
        return value
    if isinstance(value, str):
        if iso_only:
            try:
                value = parse_iso_date(value)
            except ValueError:
                # check format
                parse_date(value, env)
                return value
        else:
            value = parse_date(value, env)
        return _value_to_date(value, env)
    if isinstance(value, COLLECTION_TYPES):
        return OrderedSet(_value_to_date(v, env=env, iso_only=iso_only) for v in value)
    if isinstance(value, SQL):
        warnings.warn("Since 19.0, use Domain.custom(to_sql=lambda model, alias, query: SQL(...))", DeprecationWarning)
        return value
    raise ValueError(f'Failed to cast {value!r} into a date')


@field_type_optimization(['date'])
def _optimize_type_date(condition, model):
    """Make sure we have a date type in the value"""
    operator = condition.operator
    if (
        operator not in ('in', 'not in', '>', '<', '<=', '>=')
        or "." in condition.field_expr
    ):
        return condition
    value = _value_to_date(condition.value, model.env, iso_only=True)
    if value is False and operator[0] in ('<', '>'):
        # comparison to False results in an empty domain
        return _FALSE_DOMAIN
    return DomainCondition(condition.field_expr, operator, value)


@field_type_optimization(['date'], level=OptimizationLevel.DYNAMIC_VALUES)
def _optimize_type_date_relative(condition, model):
    operator = condition.operator
    if (
        operator not in ('in', 'not in', '>', '<', '<=', '>=')
        or "." in condition.field_expr
        or not isinstance(condition.value, (str, OrderedSet))
    ):
        return condition
    value = _value_to_date(condition.value, model.env)
    return DomainCondition(condition.field_expr, operator, value)


def _value_to_datetime(value, env, iso_only=False):
    """Convert a value(s) to datetime.

    :returns: A tuple containing the converted value and a boolean indicating
              that all input values were dates.
              These are handled differently during rewrites.
    """
    if isinstance(value, datetime):
        if value.tzinfo:
            # cast to a naive datetime
            warnings.warn("Use naive datetimes in domains")
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value, False
    if value is False:
        return False, True
    if isinstance(value, str):
        if iso_only:
            try:
                value = parse_iso_date(value)
            except ValueError:
                # check formatting
                _dt, is_date = _value_to_datetime(parse_date(value, env), env)
                return value, is_date
        else:
            value = parse_date(value, env)
        return _value_to_datetime(value, env)
    if isinstance(value, date):
        tz = env.context.get('tz') or env.user.tz or None
        if value.year == 9999 or value.year == 1:
            # avoid overflow errors, treat as UTC timezone
            tz = None
        elif tz:
            # get the tzinfo (without LMT)
            tz = pytz.timezone(tz).localize(datetime.now()).tzinfo
        value = datetime.combine(value, time.min, tz)
        if tz is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value, True
    if isinstance(value, COLLECTION_TYPES):
        value, is_date = zip(*(_value_to_datetime(v, env=env, iso_only=iso_only) for v in value))
        return OrderedSet(value), all(is_date)
    if isinstance(value, SQL):
        warnings.warn("Since 19.0, use Domain.custom(to_sql=lambda model, alias, query: SQL(...))", DeprecationWarning)
        return value, False
    raise ValueError(f'Failed to cast {value!r} into a datetime')


@field_type_optimization(['datetime'])
def _optimize_type_datetime(condition, model):
    """Make sure we have a datetime type in the value"""
    field_expr = condition.field_expr
    operator = condition.operator
    if (
        operator not in ('in', 'not in', '>', '<', '<=', '>=')
        or "." in field_expr
    ):
        return condition
    value, is_date = _value_to_datetime(condition.value, model.env, iso_only=True)

    # Handle inequality
    if operator[0] in ('<', '>'):
        if value is False:
            return _FALSE_DOMAIN
        if not isinstance(value, datetime):
            return condition
        if value.microsecond:
            assert not is_date, "date don't have microseconds"
            value = value.replace(microsecond=0)
        delta = timedelta(days=1) if is_date else timedelta(seconds=1)
        if operator == '>':
            try:
                value += delta
            except OverflowError:
                # higher than max, not possible
                return _FALSE_DOMAIN
            operator = '>='
        elif operator == '<=':
            try:
                value += delta
            except OverflowError:
                # lower than max, just check if field is set
                return DomainCondition(field_expr, '!=', False)
            operator = '<'

    # Handle equality: compare to the whole second
    if (
        operator in ('in', 'not in')
        and isinstance(value, COLLECTION_TYPES)
        and any(isinstance(v, datetime) for v in value)
    ):
        delta = timedelta(seconds=1)
        domain = DomainOr.apply(
            DomainCondition(field_expr, '>=', v.replace(microsecond=0))
            & DomainCondition(field_expr, '<', v.replace(microsecond=0) + delta)
            if isinstance(v, datetime) else DomainCondition(field_expr, '=', v)
            for v in value
        )
        if operator == 'not in':
            domain = ~domain
        return domain

    return DomainCondition(field_expr, operator, value)


@field_type_optimization(['datetime'], level=OptimizationLevel.DYNAMIC_VALUES)
def _optimize_type_datetime_relative(condition, model):
    operator = condition.operator
    if (
        operator not in ('in', 'not in', '>', '<', '<=', '>=')
        or "." in condition.field_expr
        or not isinstance(condition.value, (str, OrderedSet))
    ):
        return condition
    value, _ = _value_to_datetime(condition.value, model.env)
    return DomainCondition(condition.field_expr, operator, value)


@field_type_optimization(['binary'])
def _optimize_type_binary_attachment(condition, model):
    field = condition._field(model)
    operator = condition.operator
    value = condition.value
    if field.attachment and not (operator in ('in', 'not in') and set(value) == {False}):
        try:
            condition._raise('Binary field stored in attachment, accepts only existence check; skipping domain')
        except ValueError:
            # log with stacktrace
            _logger.exception("Invalid operator for a binary field")
        return _TRUE_DOMAIN
    if operator.endswith('like'):
        condition._raise('Cannot use like operators with binary fields', error=NotImplementedError)
    return condition


@operator_optimization(['parent_of', 'child_of'], OptimizationLevel.FULL)
def _operator_hierarchy(condition, model):
    """Transform a hierarchy operator into a simpler domain.

    ### Semantic of hierarchical operator: `(field, operator, value)`

    `field` is either 'id' to indicate to use the default parent relation (`_parent_name`)
    or it is a field where the comodel is the same as the model.
    The value is used to search a set of `related_records`. We start from the given value,
    which can be ids, a name (for searching by name), etc. Then we follow up the relation;
    forward in case of `parent_of` and backward in case of `child_of`.
    The resulting domain will have 'id' if the field is 'id' or a many2one.

    In the case where the comodel is not the same as the model, the result is equivalent to
    `('field', 'any', ('id', operator, value))`
    """
    if condition.operator == 'parent_of':
        hierarchy = _operator_parent_of_domain
    else:
        hierarchy = _operator_child_of_domain
    value = condition.value
    if value is False:
        return _FALSE_DOMAIN
    # Get:
    # - field: used in the resulting domain)
    # - parent (str | None): field name to find parent in the hierarchy
    # - comodel_sudo: used to resolve the hierarchy
    # - comodel: used to search for ids based on the value
    field = condition._field(model)
    if field.type == 'many2one':
        comodel = model.env[field.comodel_name].with_context(active_test=False)
    elif field.type in ('one2many', 'many2many'):
        comodel = model.env[field.comodel_name].with_context(**field.context)
    elif field.name == 'id':
        comodel = model
    else:
        condition._raise(f"Cannot execute {condition.operator} for {field}, works only for relational fields")
    comodel_sudo = comodel.sudo().with_context(active_test=False)
    parent = comodel._parent_name
    if comodel._name == model._name:
        if condition.field_expr != 'id':
            parent = condition.field_expr
        if field.type == 'many2one':
            field = model._fields['id']
    # Get the initial ids and bind them to comodel_sudo before resolving the hierarchy
    if isinstance(value, (int, str)):
        value = [value]
    elif not isinstance(value, COLLECTION_TYPES):
        condition._raise(f"Value of type {type(value)} is not supported")
    coids, other_values = partition(lambda v: isinstance(v, int), value)
    search_domain = _FALSE_DOMAIN
    if field.type == 'many2many':
        # always search for many2many
        search_domain |= DomainCondition('id', 'in', coids)
        coids = []
    if other_values:
        # search for strings
        search_domain |= Domain.OR(
            Domain('display_name', 'ilike', v)
            for v in other_values
        )
    coids += comodel.search(search_domain, order='id').ids
    if not coids:
        return _FALSE_DOMAIN
    result = hierarchy(comodel_sudo.browse(coids), parent)
    # Format the resulting domain
    if isinstance(result, Domain):
        if field.name == 'id':
            return result
        return DomainCondition(field.name, 'any', result)
    return DomainCondition(field.name, 'in', result)


def _operator_child_of_domain(comodel: BaseModel, parent):
    """Return a set of ids or a domain to find all children of given model"""
    if comodel._parent_store and parent == comodel._parent_name:
        domain = Domain.OR(
            DomainCondition('parent_path', '=like', rec.parent_path + '%')  # type: ignore
            for rec in comodel
        )
        return domain
    else:
        # recursively retrieve all children nodes with sudo(); the
        # filtering of forbidden records is done by the rest of the
        # domain
        child_ids: OrderedSet[int] = OrderedSet()
        while comodel:
            child_ids.update(comodel._ids)
            query = comodel._search(DomainCondition(parent, 'in', OrderedSet(comodel.ids)))
            comodel = comodel.browse(OrderedSet(query.get_result_ids()) - child_ids)
    return child_ids


def _operator_parent_of_domain(comodel: BaseModel, parent):
    """Return a set of ids or a domain to find all parents of given model"""
    parent_ids: OrderedSet[int]
    if comodel._parent_store and parent == comodel._parent_name:
        parent_ids = OrderedSet(
            int(label)
            for rec in comodel
            for label in rec.parent_path.split('/')[:-1]  # type: ignore
        )
    else:
        # recursively retrieve all parent nodes with sudo() to avoid
        # access rights errors; the filtering of forbidden records is
        # done by the rest of the domain
        parent_ids = OrderedSet()
        while comodel:
            parent_ids.update(comodel._ids)
            comodel = comodel[parent].filtered(lambda p: p.id not in parent_ids)
    return parent_ids


# --------------------------------------------------
# Optimizations: nary
# --------------------------------------------------


def _merge_set_conditions(cls: type[DomainNary], conditions):
    """Base function to merge equality conditions.

    Combine the 'in' and 'not in' conditions to a single set of values.

    Examples:

        a in {1} or a in {2}  <=>  a in {1, 2}
        a in {1, 2} and a not in {2, 5}  =>  a in {1}
    """
    assert all(isinstance(cond.value, OrderedSet) for cond in conditions)

    # build the sets for 'in' and 'not in' conditions
    in_sets = [c.value for c in conditions if c.operator == 'in']
    not_in_sets = [c.value for c in conditions if c.operator == 'not in']

    # combine the sets
    field_expr = conditions[0].field_expr
    if cls.OPERATOR == '&':
        if in_sets:
            return [DomainCondition(field_expr, 'in', intersection(in_sets) - union(not_in_sets))]
        else:
            return [DomainCondition(field_expr, 'not in', union(not_in_sets))]
    else:
        if not_in_sets:
            return [DomainCondition(field_expr, 'not in', intersection(not_in_sets) - union(in_sets))]
        else:
            return [DomainCondition(field_expr, 'in', union(in_sets))]


def intersection(sets: list[OrderedSet]) -> OrderedSet:
    """Intersection of a list of OrderedSets"""
    return functools.reduce(operator.and_, sets)


def union(sets: list[OrderedSet]) -> OrderedSet:
    """Union of a list of OrderedSets"""
    return OrderedSet(elem for s in sets for elem in s)


@nary_condition_optimization(operators=('in', 'not in'))
def _optimize_merge_set_conditions_mono_value(cls: type[DomainNary], conditions, model):
    """Merge equality conditions.

    Combine the 'in' and 'not in' conditions to a single set of values.
    Do not touch x2many fields which have a different semantic.

    Examples:

        a in {1} or a in {2}  <=>  a in {1, 2}
        a in {1, 2} and a not in {2, 5}  =>  a in {1}
    """
    field = conditions[0]._field(model)
    if field.type in ('many2many', 'one2many', 'properties'):
        return conditions
    return _merge_set_conditions(cls, conditions)


@nary_condition_optimization(operators=('in',), field_types=['many2many', 'one2many'])
def _optimize_merge_set_conditions_x2many_in(cls: type[DomainNary], conditions, model):
    """Merge domains of 'in' conditions for x2many fields like for 'any' operator.
    """
    if cls is DomainAnd:
        return conditions
    return _merge_set_conditions(cls, conditions)


@nary_condition_optimization(operators=('not in',), field_types=['many2many', 'one2many'])
def _optimize_merge_set_conditions_x2many_not_in(cls: type[DomainNary], conditions, model):
    """Merge domains of 'not in' conditions for x2many fields like for 'not any' operator.
    """
    if cls is DomainOr:
        return conditions
    return _merge_set_conditions(cls, conditions)


@nary_condition_optimization(['any'], ['many2one', 'one2many', 'many2many'])
@nary_condition_optimization(['any!'], ['many2one', 'one2many', 'many2many'])
def _optimize_merge_any(cls, conditions, model):
    """Merge domains of 'any' conditions for relational fields.

    This will lead to a smaller number of sub-queries which are equivalent.
    Example:

        a any (f = 8) or a any (g = 5)  <=>  a any (f = 8 or g = 5)     (for all fields)
        a any (f = 8) and a any (g = 5)  <=>  a any (f = 8 and g = 5)   (for many2one fields only)
    """
    field = conditions[0]._field(model)
    if field.type != 'many2one' and cls is DomainAnd:
        return conditions
    merge_conditions, other_conditions = partition(lambda c: isinstance(c.value, Domain), conditions)
    if len(merge_conditions) < 2:
        return conditions
    base = merge_conditions[0]
    sub_domain = cls([c.value for c in merge_conditions])
    return [DomainCondition(base.field_expr, base.operator, sub_domain), *other_conditions]


@nary_condition_optimization(['not any'], ['many2one', 'one2many', 'many2many'])
@nary_condition_optimization(['not any!'], ['many2one', 'one2many', 'many2many'])
def _optimize_merge_not_any(cls, conditions, model):
    """Merge domains of 'not any' conditions for relational fields.

    This will lead to a smaller number of sub-queries which are equivalent.
    Example:

        a not any (f = 1) or a not any (g = 5) => a not any (f = 1 and g = 5)   (for many2one fields only)
        a not any (f = 1) and a not any (g = 5) => a not any (f = 1 or g = 5)   (for all fields)
    """
    field = conditions[0]._field(model)
    if field.type != 'many2one' and cls is DomainOr:
        return conditions
    merge_conditions, other_conditions = partition(lambda c: isinstance(c.value, Domain), conditions)
    if len(merge_conditions) < 2:
        return conditions
    base = merge_conditions[0]
    sub_domain = cls.INVERSE([c.value for c in merge_conditions])
    return [DomainCondition(base.field_expr, base.operator, sub_domain), *other_conditions]


@nary_optimization
def _optimize_same_conditions(cls, conditions, model):
    """Merge (adjacent) conditions that are the same.

    Quick optimization for some conditions, just compare if we have the same
    condition twice.
    """
    for a, b in itertools.pairwise(itertools.chain([None], conditions)):
        if a == b:
            continue
        yield b
