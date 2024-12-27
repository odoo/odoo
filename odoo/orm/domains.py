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
import itertools
import logging
import typing
import warnings
from datetime import date, datetime, time, timedelta

from odoo.tools import SQL, OrderedSet, Query, classproperty, partition, str2bool
from .identifiers import NewId
from .utils import COLLECTION_TYPES

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable
    from odoo.fields import Field
    from odoo.models import BaseModel


_logger = logging.getLogger('odoo.domains')

STANDARD_CONDITION_OPERATORS = frozenset([
    'any', 'not any',
    'in', 'not in',
    '=', '!=',  # TODO translate them into 'in'
    '<', '>', '<=', '>=',
    'like', 'not like',
    'ilike', 'not ilike',
    '=like',
    '=ilike',
    # TODO "not =like"?
])
"""List of standard operators for conditions.
This should be supported in the framework at all levels.

- `any` works for relational fields and `id` to check if a record matches
  the condition
  - if value is SQL or Query, bypass record rules
  - if auto_join is set on the field, bypass record rules
  - if value is a Domain for a many2one (or `id`),
    _search with active_test=False
  - if value is a Domain for a x2many,
    _search on the comodel of the field (with its context)
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
    'not in': 'in',
    'not like': 'like',
    'not ilike': 'ilike',
    '!=': '=',
    '<>': '=',
}
"""A subset of operators with a 'negative' semantic, mapping to the 'positive' operator."""

# negations for operators (used in DomainNot)
_INVERSE_OPERATOR = {
    # from NEGATIVE_CONDITION_OPERATORS
    'not any': 'any',
    'not in': 'in',
    'not like': 'like',
    'not ilike': 'ilike',
    '!=': '=',
    '<>': '=',
    # positive to negative
    'any': 'not any',
    'in': 'not in',
    'like': 'not like',
    'ilike': 'not ilike',
    '=': '!=',
    # inequalities
    '<': '>=',
    '>': '<=',
    '>=': '<',
    '<=': '>',
}
"""Dict to find the inverses of the operators."""

_TRUE_LEAF = (1, '=', 1)
_FALSE_LEAF = (0, '=', 1)


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
    __slots__ = ()

    def __new__(cls, *args):
        """Build a domain AST.

        ```
        Domain([('a', '=', 5), ('b', '=', 8)])
        Domain('a', '=', 5) & Domain('b', '=', 8)
        Domain.AND([Domain('a', '=', 5), *other_domains, Domain.TRUE])
        ```

        If we have one argument, it is a `Domain`, or a list representation, or a bool.
        In case we have multiple ones, there must be 3 of them:
        a field (str), the operator (str) and a value for the condition.
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

        # parse as a list
        # perf: do this inside __new__ to avoid calling function that return
        # a Domain which would call implicitly __init__
        if not isinstance(arg, (list, tuple)):
            raise TypeError(f"Domain() invalid argument type for domain: {arg!r}")
        stack: list[Domain] = []
        try:
            for item in reversed(arg):
                if isinstance(item, (tuple, list)) and len(item) == 3:
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
    def AND(items: Iterable) -> Domain:
        """Build the conjuction of domains: (item1 AND item2 AND ...)"""
        return DomainAnd.apply(items)

    @staticmethod
    def OR(items: Iterable) -> Domain:
        """Build the disjuction of domains: (item1 OR item2 OR ...)"""
        return DomainOr.apply(items)

    def __setattr__(self, name, value):
        if hasattr(self, name):
            raise TypeError("Domain objects are immutable")
        return super().__setattr__(name, value)

    def __and__(self, other):
        """Domain & Domain"""
        if isinstance(other, DomainAnd):
            return other.__rand__(self)
        if isinstance(other, Domain):
            return Domain.AND([self, other])
        return NotImplemented

    def __or__(self, other):
        """Domain | Domain"""
        if isinstance(other, DomainOr):
            return other.__ror__(self)
        if isinstance(other, Domain):
            return Domain.OR([self, other])
        return NotImplemented

    def __invert__(self):
        """~Domain"""
        return DomainNot(self)

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
        self._optimize(model)

    def _optimize(self, model: BaseModel) -> Domain:
        """Perform optimizations of the node given a model to resolve the fields

        You should not use this method directly in business code.
        It is used mostly as a pre-processing before executing SQL.

        The model is used to validate fields and perform additional type-dependent optimizations.
        Some executions may be performed, like executing `search` for non-stored fields.
        """
        return self

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        """Build the SQL to inject into the query.  The domain should be optimized first."""
        raise NotImplementedError


class DomainBool(Domain):
    """Constant domain: True/False

    It is NOT considered as a condition and these constants are removed
    from nary domains.
    """
    __slots__ = ("__value",)
    __value: bool

    def __new__(cls, value: bool):
        """Create a constant domain."""
        self = object.__new__(cls)
        self.__value = value
        return self

    def __eq__(self, other):
        return isinstance(other, DomainBool) and self.__value == other.__value

    def __hash__(self):
        return hash(self.__value)

    @property
    def value(self) -> bool:
        return self.__value

    def is_true(self) -> bool:
        return self.__value

    def is_false(self) -> bool:
        return not self.__value

    def __invert__(self):
        return _FALSE_DOMAIN if self.__value else _TRUE_DOMAIN

    def __and__(self, other):
        if isinstance(other, Domain):
            return other if self.__value else self
        return NotImplemented

    def __or__(self, other):
        if isinstance(other, Domain):
            return self if self.__value else other
        return NotImplemented

    def __iter__(self):
        yield _TRUE_LEAF if self.__value else _FALSE_LEAF

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        return SQL("TRUE") if self.__value else SQL("FALSE")


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

    def _optimize(self, model: BaseModel) -> Domain:
        """Optimization step.

        Push down the operator as much as possible.
        """
        child = self.child
        # and/or push down
        # not not a  <=>  a
        # not (a or b)  <=>  (not a and not b)
        # not (a and b)  <=>  (not a or not b)
        if isinstance(child, (DomainNary, DomainNot)):
            # invert implemented in the child domain
            return (~child)._optimize(model)
        # first optimize the child
        # check constant and operator negation
        result = ~(child._optimize(model))
        if isinstance(result, DomainNot) and result.child is child:
            return self
        return result

    def __eq__(self, other):
        return isinstance(other, DomainNot) and self.child == other.child

    def __hash__(self):
        return ~hash(self.child)

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        condition = self.child._to_sql(model, alias, query)
        return SQL("(%s) IS NOT TRUE", condition)


class DomainNary(Domain):
    """Domain for a nary operator: AND or OR with multiple children"""
    OPERATOR: str
    OPERATOR_SQL: SQL = SQL(" ??? ")
    ZERO: DomainBool = _FALSE_DOMAIN  # default for lint checks

    __slots__ = ('_model_optimized', 'children')
    children: list[Domain]
    # to speed up optimizations, we keep the last optimized model
    _model_optimized: str

    def __new__(cls, children: list[Domain], _model_name: str = ''):
        """Create the n-ary domain with at least 2 conditions."""
        assert len(children) >= 2
        self = object.__new__(cls)
        self.children = children
        self._model_optimized = _model_name
        return self

    @classmethod
    def apply(cls, items: Iterable) -> Domain:
        """Return the result of combining AND/OR to a collection of domains."""
        children = cls._flatten(Domain(item) for item in items)
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
        return (
            isinstance(other, DomainNary)
            and self.OPERATOR == other.OPERATOR
            and self.children == other.children
        )

    def __hash__(self):
        return hash(self.OPERATOR) ^ hash(tuple(self.children))

    @classproperty
    def INVERSE(cls) -> typing.Type[DomainNary]:
        """Return the inverted nary type, AND/OR"""
        raise NotImplementedError

    def __invert__(self):
        return self.INVERSE([~child for child in self.children])

    def iter_conditions(self):
        for child in self.children:
            yield from child.iter_conditions()

    def map_conditions(self, function) -> Domain:
        return self.apply(child.map_conditions(function) for child in self.children)

    def _optimize(self, model: BaseModel) -> Domain:
        """Optimization step.

        Optimize all children with the given model.
        Run the registered optimizations until a fixed point is found.
        See :function:`nary_optimization` for details.
        """
        # check if already optimized
        if self._model_optimized:
            if model._name == self._model_optimized:
                return self
            _logger.warning(
                "Optimizing with different models %s and %s",
                self._model_optimized, model._name,
            )
        assert isinstance(self, DomainNary)
        cls = type(self)  # cls used for optimizations and rebuilding
        # optimize children
        children: Iterable[Domain] | Domain = (c._optimize(model) for c in self.children)
        while True:
            children = self._flatten(children)
            if len(children) == 1:
                return children[0]
            children.sort(key=_optimize_nary_sort_key)
            children_previous = children
            for merge_optimization in _CONDITION_MERGE_OPTIMIZATIONS:
                # group by field_name and whether to apply the function to the operator
                # we have already sorted by field name, operator type, operator
                children = merge_optimization(cls, model, children)
                # persist children to ease debugging
                if _logger.isEnabledFor(logging.DEBUG):
                    children = list(children)
            children = list(children)
            if len(children) == len(children_previous):
                # optimized
                return cls(children, model._name or '')

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        assert self.children, "No children, optimize() probably not executed"
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
    def INVERSE(cls) -> typing.Type[DomainNary]:
        return DomainOr

    def __and__(self, other):
        # simple optimization to append children
        if isinstance(other, DomainAnd):
            return DomainAnd(self.children + other.children)
        if isinstance(other, Domain) and not isinstance(other, DomainBool):
            return DomainAnd([*self.children, other])
        return super().__and__(other)

    def __rand__(self, other):
        if isinstance(other, Domain) and not isinstance(other, DomainBool):
            return DomainAnd([other, *self.children])
        return NotImplemented


class DomainOr(DomainNary):
    """Domain: OR with multiple children"""
    __slots__ = ()
    OPERATOR = '|'
    OPERATOR_SQL = SQL(" OR ")
    ZERO = _FALSE_DOMAIN

    @classproperty
    def INVERSE(cls) -> typing.Type[DomainNary]:
        return DomainAnd

    def __or__(self, other):
        # simple optimization to append children
        if isinstance(other, DomainOr):
            return DomainOr(self.children + other.children)
        if isinstance(other, Domain) and not isinstance(other, DomainBool):
            return DomainOr([*self.children, other])
        return super().__or__(other)

    def __ror__(self, other):
        if isinstance(other, Domain) and not isinstance(other, DomainBool):
            return DomainOr([other, *self.children])
        return NotImplemented


class DomainCondition(Domain):
    """Domain condition on field: (field, operator, value)

    A field (or expression) is compared to a value. The list of supported
    operators are described in CONDITION_OPERATORS.
    """
    __slots__ = ('_field_descriptor', 'field_expr', 'operator', 'value')
    _field_descriptor: Field | None  # mutable cached property
    field_expr: str
    operator: str
    value: typing.Any

    def __new__(cls, field_expr: str, operator: str, value, /):
        """Init a new simple condition (internal init)

        :param field_expr: Field name or field path
        :param operator: A valid operator
        :param value: A value for the comparison
        """
        self = object.__new__(cls)
        self.field_expr = field_expr
        self.operator = operator
        self.value = value
        self._field_descriptor = None
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
        value = self.value
        if value is None:
            value = False
        elif isinstance(value, NewId):
            _logger.warning("Domains don't support NewId, use .ids instead, for %r", (self.field_expr, self.operator, self.value))
            operator = 'not in' if operator in NEGATIVE_CONDITION_OPERATORS else 'in'
            value = []
        elif isinstance(value, _models.BaseModel):
            _logger.warning("The domain condition %r should not have a value which is a model", (self.field_expr, self.operator, self.value))
            value = value.ids
        elif isinstance(value, (Domain, Query)) and operator not in ('any', 'not any', 'in', 'not in'):
            # accept SQL object in the right part for simple operators
            # use case: compare 2 fields
            # TODO we should remove support for SQL for these other operators, add DomainSQLCondition
            _logger.warning("The domain condition %r should use the 'any' or 'not any' operator.", (self.field_expr, self.operator, self.value))
        if value is not self.value:
            return DomainCondition(self.field_expr, operator, value)
        return self

    def __invert__(self):
        # do it only for simple fields (not expressions)
        # TODO inverting inequality should consider null values (do when creating optimization for inequalities)
        if "." not in self.field_expr and (neg_op := _INVERSE_OPERATOR.get(self.operator)):
            return DomainCondition(self.field_expr, neg_op, self.value)
        return super().__invert__()

    def __iter__(self):
        field_expr, operator, value = self.field_expr, self.operator, self.value
        # if the value is a domain or set, change it into a list
        if isinstance(value, (*COLLECTION_TYPES, Domain)):
            value = list(value)
        yield (field_expr, operator, value)

    def __eq__(self, other):
        return (
            isinstance(other, DomainCondition)
            and self.field_expr == other.field_expr
            and self.operator == other.operator
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

    def _field(self) -> Field:
        """Cached Field instance for the expression. Set during optimization."""
        # not a @property because of typing thinking we want to call __get__
        if self._field_descriptor is None:  # type: ignore[arg-type]
            self._raise("Unknown field")
        return self._field_descriptor  # type: ignore[arg-type]

    def __get_field(self, model: BaseModel) -> tuple[Field, str]:
        """Get the field or raise an exception"""
        field_name, *props = self.field_expr.split('.', 1)
        try:
            field = model._fields[field_name]
        except KeyError:
            self._raise("Invalid field %s.%s", model._name, field_name)
        return field, (props[0] if props else '')

    def _optimize(self, model: BaseModel) -> Domain:
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
        # optimize path
        field = self._field_descriptor   # type: ignore[arg-type]
        if field is None or field.model_name != model._name:
            field, property_name = self.__get_field(model)
            if property_name and field.relational:
                sub_domain = DomainCondition(property_name, self.operator, self.value)
                return DomainCondition(field.name, 'any', sub_domain)._optimize(model)
            # cache field value, with this hack to bypass immutability
            object.__setattr__(self, '_field_descriptor', field)

        # resolve inherited fields
        # inherits implies both Field.delegate=True and Field.auto_join=True
        # so no additional permissions will be added by the 'any' operator below
        if field.inherited:
            related_field: Field = field.related_field  # type: ignore
            assert related_field.model_name, f"No co-model for inherited field {field!r}"
            parent_model = model.env[related_field.model_name]
            parent_fname = model._inherits[parent_model._name]
            parent_domain = self._optimize(parent_model)
            return DomainCondition(parent_fname, 'any', parent_domain)

        # handle non-stored fields (replace by searchable/stored items)
        if not field.store and self.field_expr == field.name:
            # find the implementation of search and execute it
            if not field.search:
                _logger.error("Non-stored field %s cannot be searched.", field, stack_info=_logger.isEnabledFor(logging.DEBUG))
                return _TRUE_DOMAIN
            computed_domain = field.determine_domain(model, self.operator, self.value)
            return Domain(computed_domain)._optimize(model)

        # optimizations based on operator
        for opt in _CONDITION_OPTIMIZATIONS_BY_OPERATOR[self.operator]:
            dom = opt(self, model)
            if dom is not self:
                return dom._optimize(model)

        if not field.store:
            # just hope _condition_to_sql handles this expression that has a property
            return self

        # optimizations based on field type
        for opt in _CONDITION_OPTIMIZATIONS_BY_FIELD_TYPE[field.type]:
            dom = opt(self, model)
            if dom is not self:
                return dom._optimize(model)

        # asserts after optimization
        operator = self.operator
        if operator not in STANDARD_CONDITION_OPERATORS:
            self._raise("Not standard operator left")

        if (
            not field.relational
            and operator in ('any', 'not any')
            and field.name != 'id'  # can use 'id'
            # Odoo internals use ('xxx', 'any', Query), check only Domain
            and (not field.store or isinstance(self.value, Domain))
        ):
            self._raise("Cannot use 'any' with non-relational fields")

        return self

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        return model._condition_to_sql(alias, self.field_expr, self.operator, self.value, query)


# --------------------------------------------------
# Optimizations: registration
# --------------------------------------------------

ANY_TYPES = (Domain, Query, SQL)

_CONDITION_OPTIMIZATIONS_BY_OPERATOR: dict[str, list[Callable[[DomainCondition, BaseModel], Domain]]] = collections.defaultdict(list)
_CONDITION_OPTIMIZATIONS_BY_FIELD_TYPE: dict[str, list[Callable[[DomainCondition, BaseModel], Domain]]] = collections.defaultdict(list)
_CONDITION_MERGE_OPTIMIZATIONS: list[Callable[[type[DomainNary], BaseModel, Iterable[Domain]], Iterable[Domain]]] = list()


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
        elif positive_op == '=':
            order = "0eq"
        elif positive_op == 'any':
            order = "1any"
        elif positive_op.endswith('like'):
            order = "like"
        else:
            order = positive_op
        return domain.field_expr, order, operator
    else:
        # in python; '~' > any letter
        assert hasattr(domain, 'OPERATOR') and isinstance(domain.OPERATOR, str)
        return '~', '', domain.OPERATOR


def nary_optimization(optimization: Callable[[type[DomainNary], BaseModel, Iterable[Domain]], Iterable[Domain]]):
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
    _CONDITION_MERGE_OPTIMIZATIONS.append(optimization)
    return optimization


def nary_condition_optimization(*, operators: Collection[str], field_condition: Callable[[Field], bool] | None = None):
    """Register an optimization for condition children of an nary domain.

    The function will take a list of domain conditions of the same field and
    returns *optimized* domains.

    This is a adapter function that uses `nary_optimization`.

    NOTE: if you want to merge different operators, register for
    `operator=CONDITION_OPERATORS` and find conditions that you want to merge.
    """
    def register(optimization: Callable[[type[DomainNary], BaseModel, list[DomainCondition]], Iterable[Domain]]):
        @nary_optimization
        def optimizer(cls, model, conditions: Iterable[Domain]):
            for (field_expr, apply_operator), conds in itertools.groupby(
                conditions, lambda c: (c.field_expr, True) if isinstance(c, DomainCondition) and c.operator in operators else ('', False)
            ):
                if (
                    apply_operator
                    and (field_condition is None or (
                        (field := model._fields.get(field_expr)) is not None and field_condition(field)
                    ))
                ):
                    list_conds: list[DomainCondition] = list(conds)  # type: ignore[arg-type]
                    if len(list_conds) > 1:
                        yield from optimization(cls, model, list_conds)
                    else:
                        yield from list_conds
                else:
                    yield from conds
        return optimization
    return register


def operator_optimization(operators: Collection[str]):
    """Register a condition operator optimization for (condition, model)"""
    assert operators, "Missing operator to register"
    CONDITION_OPERATORS.update(operators)

    def register(optimization: Callable[[DomainCondition, BaseModel], Domain]):
        for operator in operators:
            _CONDITION_OPTIMIZATIONS_BY_OPERATOR[operator].append(optimization)
        return optimization
    return register


def field_type_optimization(field_types: Collection[str]):
    """Register a condition optimization by field type for (condition, model)"""

    def register(optimization: Callable[[DomainCondition, BaseModel], Domain]):
        for field_type in field_types:
            _CONDITION_OPTIMIZATIONS_BY_FIELD_TYPE[field_type].append(optimization)
        return optimization
    return register


# --------------------------------------------------
# Optimizations: conditions
# --------------------------------------------------


def _value_to_ids(
    value: typing.Any,
    model: BaseModel,
    operator: str,
    extra_domain: Domain = Domain.TRUE,  # when searching using display_name
) -> OrderedSet[int] | Query | SQL:
    """For relational fields, transform a value into a set of ids or query."""
    if isinstance(value, ANY_TYPES):
        if isinstance(value, Domain):
            return model._search(value)
        return value
    if isinstance(value, int):
        return OrderedSet((value,)) if value else OrderedSet()
    # make a collection of names
    if isinstance(value, str):
        value = (value,)
    elif not isinstance(value, COLLECTION_TYPES):
        raise TypeError(f"Invalid argument to get ids from {model._name}: {value!r}")
    # split by type
    int_values, values = partition(lambda v: isinstance(v, int), value)
    if not values:
        # only int, return an OrderedSet
        return value if isinstance(value, OrderedSet) else OrderedSet(value)
    # search using the display_name
    if operator == 'in':
        domain: Domain = DomainCondition('display_name', 'in', OrderedSet(values))
    else:
        domain = Domain.OR(
            Domain('display_name', operator, v)
            for v in values
        )
    if int_values:
        domain |= DomainCondition('id', 'in', OrderedSet(int_values))
    domain &= extra_domain
    return model._search(domain)


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
    else:
        return condition
    return DomainCondition(condition.field_expr, operator, value)


@operator_optimization(['any', 'not any'])
def _optimize_id_any_condition(condition, _):
    """ Any condition on 'id'

    id ANY domain  <=>  domain
    id NOT ANY domain  <=>  ~domain
    """
    if condition.field_expr == 'id' and isinstance(domain := condition.value, Domain):
        if condition.operator == 'not any':
            domain = ~domain
        return domain
    return condition


@operator_optimization(['in', 'not in'])
def _optimize_in_list(condition, _):
    """Make sure the value is a collection or use 'any' operator"""
    value = condition.value
    if isinstance(value, ANY_TYPES):
        return DomainCondition(condition.field_expr, 'any' if condition.operator == 'in' else 'not any', value)
    if not value:
        # empty, return a boolean
        return _FALSE_DOMAIN if condition.operator == 'in' else _TRUE_DOMAIN
    if not isinstance(value, COLLECTION_TYPES):
        # TODO show warning, note that condition.field_expr in ('groups_id', 'user_ids') gives a lot of them
        _logger.debug("The domain condition %r should have a list value.", condition)
        value = [value]
    if value is condition.value:
        return condition
    return DomainCondition(condition.field_expr, condition.operator, OrderedSet(value))


@operator_optimization(['any', 'not any'])
def _optimize_any_domain(condition, model):
    """Make sure the value is an optimized domain (or Query or SQL)"""
    value = condition.value
    if not isinstance(value, Domain) and isinstance(value, ANY_TYPES):
        return condition
    # get the model to optimize with
    try:
        field = condition._field()
        comodel = model.env[field.comodel_name]
    except KeyError:
        raise ValueError(f"Cannot determine the relation for {condition.field_expr!r}")
    domain = Domain(value)._optimize(comodel)
    # const if the domain is empty, the result is a constant
    # if the domain is True, we keep it as is
    if domain.is_false():
        return Domain(condition.operator == 'not any')
    # if unchanged, return the condition
    if domain is value:
        return condition
    return DomainCondition(condition.field_expr, condition.operator, domain)


@operator_optimization([op for op in CONDITION_OPERATORS if op.endswith('like')])
def _optimize_like_str(condition, model):
    """Validate value for pattern matching, must be a str"""
    value = condition.value
    if not value:
        # =like matches only empty string (inverse the condition)
        result = (condition.operator in NEGATIVE_CONDITION_OPERATORS) == ('=' in condition.operator)
        # relational and non-relation fields behave differently
        if condition._field().relational or '=' in condition.operator:
            return DomainCondition(condition.field_expr, '!=' if result else '=', False)
        return Domain(result)
    if isinstance(value, (str, SQL)):
        # accept both str and SQL
        return condition
    if '=' in condition.operator:
        condition._raise("The pattern to match must be a string", error=TypeError)
    return DomainCondition(condition.field_expr, condition.operator, str(value))


@field_type_optimization(['many2one', 'one2many', 'many2many'])
def _optimize_relational_name_search(condition, model):
    """Search using display_name; see _value_to_ids."""
    operator = condition.operator
    value = condition.value
    # Handle only: like operator, equality with str values
    if not (
        operator.endswith('like')
        or (
            operator in ('in', 'not in')
            and isinstance(value, COLLECTION_TYPES)
            and any(isinstance(v, str) for v in value)
        )
        or (
            operator in ('=', '!=')
            and isinstance(value, str)
        )
    ):
        return condition
    # operator
    positive_operator = NEGATIVE_CONDITION_OPERATORS.get(operator, operator)
    positive = operator == positive_operator
    # get the comodel
    field = condition._field()
    comodel = model.env[field.comodel_name]
    # access rules will be checked by the _search method (in _value_to_ids),
    # we can just return the values if we have a list of ids
    if field.type == 'many2one':
        # for many2one, search also the archived records
        comodel = comodel.with_context(active_test=False)
        value = _value_to_ids(value, comodel, positive_operator)
    else:
        comodel = comodel.with_context(**field.context)
        additional_domain = Domain(field.get_domain_list(model))
        value = _value_to_ids(value, comodel, positive_operator, additional_domain)
    if isinstance(value, OrderedSet):
        any_operator = 'in' if positive else 'not in'
    else:
        any_operator = 'any' if positive else 'not any'
    return DomainCondition(condition.field_expr, any_operator, value)


@field_type_optimization(['boolean'])
def _optimize_in_boolean(condition, model):
    """b in [True, False]  =>  True"""
    value = condition.value
    operator = condition.operator
    if operator in ('=', '!='):
        if isinstance(value, bool):
            return condition
        operator = 'in' if operator == '=' else 'not in'
        value = [value]
    if operator not in ('in', 'not in') or not isinstance(value, COLLECTION_TYPES):
        return condition
    if not all(isinstance(v, bool) for v in value):
        if any(isinstance(v, str) for v in value):
            # TODO make a warning
            _logger.debug("Comparing boolean with a string in %s", condition)
        value = {
            str2bool(v.lower(), False) if isinstance(v, str) else bool(v)
            for v in value
        }
    if set(value) == {False, True}:
        # tautology is simplified to a boolean
        # note that this optimization removes fields (like active) from the domain
        return Domain(operator == 'in')
    if value is condition.value:
        return condition
    return DomainCondition(condition.field_expr, operator, value)


def _value_to_date(value, inside_day=lambda dt: dt.date()):
    # check datetime first, because it's a subclass of date
    if isinstance(value, SQL):
        return value
    if isinstance(value, datetime):
        if value.time() == time.min:
            return value.date()
        return inside_day(value)
    if isinstance(value, date) or value is False:
        return value
    if isinstance(value, str):
        # TODO can we use fields.Date.to_date? same for datetime
        if len(value) == 10:
            return date.fromisoformat(value)
        if len(value) < 10:
            # TODO deprecate or raise error
            # probably the value is missing zeroes
            try:
                parts = value.split('-')
                return date(*[int(part) for part in parts])
            except (ValueError, TypeError):
                raise ValueError(f"Invalid isoformat string {value!r}")
        return _value_to_date(datetime.fromisoformat(value), inside_day=inside_day)
    if isinstance(value, COLLECTION_TYPES):
        return OrderedSet(_value_to_date(v, inside_day=inside_day) for v in value)
    raise ValueError(f'Failed to cast {value!r} into a date')


@field_type_optimization(['date'])
def _optimize_type_date(condition, _):
    """Make sure we have a date type in the value"""
    if condition.operator.endswith('like') or "." in condition.field_expr:
        return condition
    operator = condition.operator

    def inside_day(dt: datetime):
        # when comparing to a date inside a day, update the operator
        nonlocal operator
        match operator:
            case '<':
                operator = '<='
            case '>=':
                operator = '>'
            case '<=' | '>':
                pass
            case _:
                return None  # filter out the value
        return dt.date()

    value = _value_to_date(condition.value, inside_day=inside_day)
    if isinstance(value, OrderedSet):
        value.discard(None)
    elif value is None:
        return Domain(operator in NEGATIVE_CONDITION_OPERATORS)
    if value is False and operator[0] in ('<', '>'):
        # comparison to False results in an empty domain
        return _FALSE_DOMAIN
    if value == condition.value:
        return condition
    return DomainCondition(condition.field_expr, operator, value)


def _value_to_datetime(value):
    if isinstance(value, SQL):
        return value, False
    if isinstance(value, datetime) or value is False:
        return value, False
    if isinstance(value, str):
        return datetime.fromisoformat(value), len(value) == 10
    if isinstance(value, date):
        return datetime.combine(value, time.min), True
    if isinstance(value, COLLECTION_TYPES):
        value, is_day = zip(*(_value_to_datetime(v) for v in value))
        return OrderedSet(value), any(is_day)
    raise ValueError(f'Failed to cast {value!r} into a datetime')


@field_type_optimization(['datetime'])
def _optimize_type_datetime(condition, _):
    """Make sure we have a datetime type in the value"""
    if condition.operator.endswith('like') or "." in condition.field_expr:
        return condition
    operator = condition.operator
    value, is_day = _value_to_datetime(condition.value)
    if value is False and operator[0] in ('<', '>'):
        # comparison to False results in an empty domain
        return _FALSE_DOMAIN
    if value == condition.value:
        assert not is_day
        return condition

    # if we get a day we may need to add 1 depending on the operator
    if is_day and operator == '>':
        try:
            value += timedelta(1)
        except OverflowError:
            # higher than max, not possible
            return _FALSE_DOMAIN
        operator = '>='
    elif is_day and operator == '<=':
        try:
            value += timedelta(1)
        except OverflowError:
            # lower than max, just check if field is set
            return DomainCondition(condition.field_expr, '!=', False)
        operator = '<'

    return DomainCondition(condition.field_expr, operator, value)


@field_type_optimization(['binary'])
def _optimize_type_binary_attachment(condition, model):
    field = condition._field()
    operator = condition.operator
    value = condition.value
    if operator in ('=', '!='):
        operator = 'in' if operator == '=' else 'not in'
        value = [value]
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


@operator_optimization(['parent_of', 'child_of'])
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
        _logger.warning('Using %s with False value, the result will be empty', condition.operator)
    # Get:
    # - field: used in the resulting domain)
    # - parent (str | None): field name to find parent in the hierarchy
    # - comodel_sudo: used to resolve the hierarchy
    # - comodel: used to search for ids based on the value
    field = condition._field()
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
    coids = _value_to_ids(value, comodel, 'in')
    if field.type == 'many2many' or isinstance(coids, (SQL, Query)):
        # always search for many2many
        coids = comodel.search(Domain('id', 'in', coids), order='id').ids
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


@nary_condition_optimization(operators=('any',), field_condition=lambda f: f.type == 'many2one')
def _optimize_merge_many2one_any(cls, model, conditions):
    """Merge domains of 'any' conditions for many2one fields.

    This will lead to a smaller number of sub-queries which are equivalent.
    Example:

        a.f = 8 and a.g = 5  <=>  a any (f = 8 and g = 5)
    """
    merge_conditions, other_conditions = partition(lambda c: isinstance(c.value, Domain), conditions)
    if len(merge_conditions) < 2:
        return conditions
    field_expr = merge_conditions[0].field_expr
    sub_domain = cls([c.value for c in merge_conditions])
    return [DomainCondition(field_expr, 'any', sub_domain)._optimize(model), *other_conditions]


@nary_condition_optimization(operators=('not any',), field_condition=lambda f: f.type == 'many2one')
def _optimize_merge_many2one_not_any(cls, model, conditions):
    """Merge domains of 'not any' conditions for many2one fields.

    This will lead to a smaller number of sub-queries which are equivalent.
    Example:

        a not any f = 1 or a not any g = 5 => a not any (f = 1 and g = 5)
        a not any f = 1 and a not any g = 5 => a not any (f = 1 or g = 5)
    """
    merge_conditions, other_conditions = partition(lambda c: isinstance(c.value, Domain), conditions)
    if len(merge_conditions) < 2:
        return conditions
    field_expr = merge_conditions[0].field_expr
    sub_domain = cls.INVERSE([c.value for c in merge_conditions])
    return [DomainCondition(field_expr, 'not any', sub_domain)._optimize(model), *other_conditions]


@nary_condition_optimization(operators=('any',), field_condition=lambda f: f.type.endswith('2many'))
def _optimize_merge_x2many_any(cls, model, conditions):
    """Merge domains of 'any' conditions for x2many fields.

    This will lead to a smaller number of sub-queries which are equivalent.
    Example:

        a.f = 8 or a.g = 5  <=>  a any (f = 8 or g = 5)

    Note that the following cannot be optimized as multiple instances can
    satisfy conditions:

        a.f = 8 and a.g = 5
    """
    if cls is DomainAnd:
        return conditions
    return _optimize_merge_many2one_any(cls, model, conditions)


@nary_condition_optimization(operators=('not any',), field_condition=lambda f: f.type.endswith('2many'))
def _optimize_merge_x2many_not_any(cls, model, conditions):
    """Merge domains of 'not any' conditions for x2many fields.

    This will lead to a smaller number of sub-queries which are equivalent.
    Example:

        a not any f = 1 and a not any g = 5  <=>  a not any (f = 1 or g = 5)
    """
    if cls is DomainOr:
        return conditions
    return _optimize_merge_many2one_not_any(cls, model, conditions)


@nary_optimization
def _optimize_same_conditions(cls, model, conditions: Iterable[Domain]):
    """Merge (adjacent) conditions that are the same.

    Quick optimization for some conditions, just compare if we have the same
    condition twice.
    """
    # just check the adjacent conditions for simple domains
    # TODO replace this by:
    # 1. optimize inequalities
    # 2. optimize like with same prefixes
    # 3. remove this function as equalities and existence is already covered
    for a, b in itertools.pairwise(itertools.chain([None], conditions)):
        if a == b:
            continue
        yield b


# forward-reference to models
# it is used in the constructor for warnings
from . import models as _models  # noqa: E402
