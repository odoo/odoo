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
- nary operator: AND, OR
- unary operator: NOT
- boolean constant: TRUE, FALSE
- (simple) condition: (expression, operator, value)

Leaves are triplets of `(expression, operator, value)`.
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
import operator as py_operator
import traceback
import typing
import warnings
from collections.abc import Set as AbstractSet
from datetime import date, datetime, time, timedelta

import odoo.models
from odoo.tools import SQL, OrderedSet, Query, classproperty, partition, str2bool

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable, Iterator
    from odoo.fields import Field
    from odoo.models import BaseModel


_logger = logging.getLogger(__name__)
COLLECTION_TYPES = (AbstractSet, list, tuple)

STANDARD_CONDITION_OPERATORS = frozenset([
    'any', 'not any',
    'in', 'not in',
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
    _search with the context from the field
- `in` for equality checks where the given value is a collection of values
  - the collection is transformed into OrderedSet
  - False value indicates that the value is *not set*
  - for relational fields
    - if int, bypass record rules
    - if str, search the field by name
  - the value should have the type of the field
  - SQL type is always accepted
- `<`, `>`, ... inequality checks, similar behaviour to `in` with a single value
- string pattern comparison
  - `=like` case-sensitive compare to a string using SQL like semantics
  - `=ilike` case-insensitive with `unaccent` comparison to a string
  - `like`, `ilike` behave like the preceding methods, but add a wildcards
    around the value
"""
CONDITION_OPERATORS = set(STANDARD_CONDITION_OPERATORS)  # modifiable
"""
List of available operators for conditions.
The non-standard operators can be reduced to standard operators by using the
optimization function. See the respective optimization functions for the
details.
"""

NEGATIVE_CONDITION_OPERATORS = {
    op: op[4:]
    for op in CONDITION_OPERATORS
    if op.startswith('not ')
} | {'!=': '='}
"""A subset of operators with a 'negative' semantic, mapping to the 'positive' operator."""

# negations for operators (used in DomainNot)
_INVERSE_OPERATOR = {
    '<': '>=',
    '>': '<=',
} | NEGATIVE_CONDITION_OPERATORS
_INVERSE_OPERATOR |= {
    op_pos: op_neg
    for op_neg, op_pos in _INVERSE_OPERATOR.items()
}

_TRUE_LEAF = (1, '=', 1)
_FALSE_LEAF = (0, '=', 1)


# --------------------------------------------------
# Domain definition and manipulation
# --------------------------------------------------

class Domain:
    """Representation of a domain as an AST.
    """
    # Domain is an abstract class (ABC), but not marked as such
    # because we overwrite __new__ so typechecking for abstractmethod is incorrect

    field: str | None = None  # ease checks whether the domain is concerning a field

    def __new__(cls, *args):
        """Build a normalized domain.

        ```
        Domain([('a', '=', 5), ('b', '=', 8)])
        Domain('a', '=', 5) & Domain('b', '=', 8)
        Domain.AND(D('a', '=', 5), *other_conditions, Domain.TRUE)
        ```

        :param arg: A Domain, or a list representation, or a bool, or str (field)
        :param operator: When set, the domain is a str and the value should be set
        :param value: The value for the operator
        """
        if cls is not Domain:
            # if class is different, just call __init__
            # this way we don't need to redefine __new__ in subclasses
            domain = super().__new__(cls)
            domain.__init__(*args)  # type: ignore
            return domain
        arg = args[0]
        if len(args) > 1:
            if isinstance(arg, str):
                return DomainCondition.new(*args)
            # special cases like True/False constants
            if args == _TRUE_LEAF:
                return _TRUE_DOMAIN
            if args == _FALSE_LEAF:
                return _FALSE_DOMAIN
            raise TypeError(f"Domain() invalid arguments: {args!r}")
        # already a domain?
        if isinstance(arg, Domain):
            return arg
        # handle old-style tuple for condition
        if isinstance(arg, tuple) and len(arg) == 3 and isinstance(arg[1], str):
            return Domain(*arg)
        # a constant?
        if arg is True or arg == []:
            return _TRUE_DOMAIN
        if arg is False:
            return _FALSE_DOMAIN
        # parse as a list
        if not isinstance(arg, (list, tuple)):
            raise TypeError(f"Domain() invalid argument type for domain: {arg!r}")
        return Domain._from_list(arg)

    @staticmethod
    def _from_list(domain: list | tuple) -> Domain:
        """Parse a list to build a Domain"""
        stack: list[Domain] = []
        try:
            for d in reversed(domain):
                if isinstance(d, (tuple, list)) and len(d) == 3:
                    stack.append(Domain(*d))
                elif d == DomainAnd.OPERATOR:
                    stack.append(stack.pop() & stack.pop())
                elif d == DomainOr.OPERATOR:
                    stack.append(stack.pop() | stack.pop())
                elif d == DomainNot.OPERATOR:
                    stack.append(~stack.pop())
                else:
                    raise ValueError(f"Domain() invalid item in domain: {d!r}")
            # keep the order and simplify already
            if len(stack) == 1:
                return stack[0]
            return DomainAnd.new(reversed(stack))
        except IndexError:
            raise ValueError("Domain() malformed domain")

    @classproperty
    def TRUE(cls) -> DomainBool:
        return _TRUE_DOMAIN

    @classproperty
    def FALSE(cls) -> DomainBool:
        return _FALSE_DOMAIN

    @staticmethod
    def AND(*items) -> Domain:
        """Build an intersection of domains: (item1 AND item2 AND ...)"""
        return DomainAnd.new(items)

    @staticmethod
    def OR(*items) -> Domain:
        """Build a union of domains: (item1 OR item2 OR ...)"""
        return DomainOr.new(items)

    def __and__(self, other):
        """Domain & Domain"""
        if isinstance(other, DomainAnd):
            return other.__rand__(self)
        if isinstance(other, Domain):
            return DomainAnd.new([self, other])
        return NotImplemented

    def __or__(self, other):
        """Domain | Domain"""
        if isinstance(other, DomainOr):
            return other.__ror__(self)
        if isinstance(other, Domain):
            return DomainOr.new([self, other])
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
        # special case, where we prepend "not"
        if other == ['!']:
            return ~self
        # we are pre-pending, return a list
        # because the result may not be normalized
        return other + list(self)

    def __bool__(self):
        """For backward-compatibility, the domain [] was False, indicating an
        empty domain is False, an empty domain is TRUE"""
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
        """Check if self is TRUE"""
        return False

    def is_false(self) -> bool:
        """Check if self is FALSE"""
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
        self.optimize(model)

    def optimize(self, model: BaseModel) -> Domain:
        """Perform optimizations of the node given a model to resolve the fields

        You should not use this method directly in business code.
        It is used mostly as a pre-processing before executing SQL.

        The model is used to validate fields and perform additional type-dependent optimizations.
        Some executions may be performed, like executing `search` for non-stored fields.
        """
        return self

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        """Build the where_clause and the where_params (must be optimized with field)"""
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
        if self.__value:
            yield _TRUE_LEAF
        else:
            yield _FALSE_LEAF

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
        child = self.child.map_conditions(function)
        if child is self.child:
            return self
        return ~child

    def optimize(self, model: BaseModel) -> Domain:
        """Optimization step.

        Push down the operator as much as possible.
        """
        child = self.child
        # not not a  <=>  a
        if isinstance(child, DomainNot):
            child = child.child
            return child.optimize(model)
        # and/or push down
        # not (a or b)  <=>  (not a and not b)
        # not (a and b)  <=>  (not a or not b)
        if isinstance(child, DomainNary):
            # implemented in nary
            child = ~child
            return child.optimize(model)
        # first optimize the child
        # check constant and operator negation
        result = ~(child.optimize(model))
        if isinstance(result, DomainNot) and result.child is child:
            return self
        return result

    def __eq__(self, other):
        return (
            isinstance(other, DomainNot)
            and self.child == other.child
        )

    def __hash__(self):
        return ~hash(self.child)

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        condition = self.child._to_sql(model, alias, query)
        return SQL("(%s) IS NOT TRUE", condition)


class DomainNary(Domain):
    """Domain for a nary operator: AND or OR with multiple children"""
    OPERATOR: str
    OPERATOR_SQL: SQL = SQL(" ??? ")
    OPERATOR_PY: Callable
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
    def new(cls, items: Iterable) -> Domain:
        children = cls._simplify_children(Domain(item) for item in items)
        if isinstance(children, Domain):
            return children
        return cls(children)

    @classmethod
    def _simplify_children(cls, children: Iterable[Domain]) -> list[Domain] | Domain:
        """Return the list of children (flattened for same domain type) or a Domain.

        If we have the same type, just copy the children (flatten the domain).
        If we have a constant: if it's the zero, ignore it;
        otherwise return ~zero directly.
        The result will contain a list of at least 2 domains or a Domain.
        """
        result: list[Domain] = []
        for c in children:
            if isinstance(c, cls):
                # same class, flatten
                result.extend(c.children)
            elif isinstance(c, DomainBool):
                if c.value == cls.ZERO.value:
                    continue
                return ~cls.ZERO
            else:
                result.append(c)
        len_result = len(result)
        if len_result == 0:
            return cls.ZERO
        if len_result == 1:
            return result[0]
        return result

    def __iter__(self):
        for _ in range(len(self.children) - 1):
            yield self.OPERATOR
        for c in self.children:
            yield from c

    def __eq__(self, other):
        return (
            isinstance(other, DomainNary)
            and self.OPERATOR == other.OPERATOR
            and self.children == other.children
        )

    def __hash__(self):
        return hash(self.OPERATOR) ^ hash(tuple(self.children))

    @classmethod
    def inverse_nary(cls):
        """Return the inversed nary type, AND/OR"""
        raise NotImplementedError

    def __invert__(self):
        cls = self.inverse_nary()
        return cls([~c for c in self.children])

    def iter_conditions(self):
        for child in self.children:
            yield from child.iter_conditions()

    def map_conditions(self, function) -> Domain:
        updated = False
        new_children: list[Domain] = []
        for child in self.children:
            new_child = child.map_conditions(function)
            if new_child is child:
                new_children.append(child)
            else:
                new_children.append(new_child)
                updated = True
        if updated:
            return self.new(new_children)
        return self

    def optimize(self, model: BaseModel) -> Domain:
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
        children: Iterator[Domain] | Iterable[Domain] | Domain = (c.optimize(model) for c in self.children)
        while True:
            children = self._simplify_children(children)
            if isinstance(children, Domain):
                return children
            children.sort(key=_optimize_nary_sort_key)
            children_previous = children
            for merge_optimization in _LEAF_MERGE_OPTIMIZATIONS:
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
            c._to_sql(model, alias, query) for c in self.children
        ))


class DomainAnd(DomainNary):
    """Domain: AND with multiple children"""
    OPERATOR = '&'
    OPERATOR_SQL = SQL(" AND ")
    OPERATOR_PY = py_operator.and_
    ZERO = _TRUE_DOMAIN

    @classmethod
    def inverse_nary(cls):
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
    OPERATOR = '|'
    OPERATOR_SQL = SQL(" OR ")
    OPERATOR_PY = py_operator.or_
    ZERO = _FALSE_DOMAIN

    @classmethod
    def inverse_nary(cls):
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
    """Leaf field domain: (field, operator, value)

    A field (or expression) is compared to a value. The list of supported
    operators are described in CONDITION_OPERATORS.
    """
    __slots__ = ('field', 'operator', 'value')
    field: str
    operator: str
    value: typing.Any

    def __new__(cls, field: str, operator: str, value, /):
        """Init a new simple condition (internal init)

        :param field: Field name or field path
        :param operator: A valid operator
        :param value: A value for the comparison
        """
        self = object.__new__(cls)
        self.field = field
        self.operator = operator
        self.value = value
        return self

    @classmethod
    def new(cls, field_name, operator, value) -> DomainCondition:
        """Validate the inputs and create a domain

        :param field_name: Field name, whic is a non empty string
        :param operator: Operator
        :param value: The value
        """
        if value is None:
            value = False
        rep = (field_name, operator, value)
        if not isinstance(field_name, str) or not field_name:
            raise TypeError(f"Empty field name in condition {rep!r}")
        # Rewrites done here to have already a more normalized domain.
        # This allows for some common optimizations and to show warnings when building the domain.
        operator = operator.lower()
        if operator != rep[1]:
            warnings.warn(f"The domain condition {rep!r} should have a lower-case operator", DeprecationWarning)
        if operator == '<>':
            warnings.warn("Operator '<>' is deprecated, use '!=' directly", DeprecationWarning)
            operator = '!='
        if operator not in CONDITION_OPERATORS:
            raise ValueError(f"Invalid operator in {rep!r}")
        # check already the consistency for domain manipulation
        # - NewId is not a value
        # - Query and Domain values should be using a relational operator
        # - replace '=' with 'in'
        #   (x, '=', a) becomes (x, 'in', {a})
        # - check that 'in' contains a collection
        if isinstance(value, odoo.models.NewId):
            _logger.warning("Domains don't support NewId, use .ids instead, for %r", rep)
            return DomainCondition(field_name, 'not in' if operator in NEGATIVE_CONDITION_OPERATORS else 'in', [])
        if isinstance(value, odoo.models.BaseModel):
            _logger.warning("The domain condition %r should not have a value which is a model", rep)
            value = value.ids
        if isinstance(value, SQL) and operator not in ('any', 'not any', 'in', 'not in'):
            # accept SQL object in the right part for simple operators
            # use case: compare 2 fields
            # TODO we should remove support for SQL in the domain value
            pass
        elif isinstance(value, (Domain, Query, SQL)):
            if operator not in ('any', 'not any', 'in', 'not in'):
                _logger.warning("The domain condition %r should use the 'any' or 'not any' operator.", rep)
            operator = 'not any' if operator in NEGATIVE_CONDITION_OPERATORS else 'any'
        elif operator in ('any', 'not any'):
            # parse the value as a domain
            value = Domain(value)
        elif operator in ('=', '!='):
            operator = 'in' if operator == '=' else 'not in'
            if isinstance(value, COLLECTION_TYPES):
                # TODO make a warning or equality against a collection
                if not value:  # views sometimes use ('user_ids', '!=', []) to indicate the user is set
                    _logger.debug("The domain condition %s should compare with False.", rep)
                    value = OrderedSet([False])
                else:
                    _logger.debug("The domain condition %s should use the 'in' or 'not in' operator.", rep)
                    value = OrderedSet(value)
            else:
                value = OrderedSet([value])
        elif operator in ('in', 'not in') and not isinstance(value, COLLECTION_TYPES):
            # TODO show warning, except occurrences like ('groups_id', 'in', ref(...).id) too many of them
            if field_name not in {'groups_id', 'user_ids'}:
                _logger.debug("The domain condition %s should have a list value.", rep)
            value = OrderedSet([value])
        return DomainCondition(field_name, operator, value)

    def __invert__(self):
        # can we just update the operator?
        # do it only for simple fields (not expressions)
        # TODO inversing inequality should consider null values (do when creating optimization for inequalities)
        if "." not in self.field and (neg_op := _INVERSE_OPERATOR.get(self.operator)):
            return DomainCondition(self.field, neg_op, self.value)
        return super().__invert__()

    def __iter__(self):
        field, operator, value = self.field, self.operator, self.value
        # display a any [b op x] as a.b op x
        if operator == 'any' and isinstance(value, DomainCondition):
            field_b, operator, value = next(iter(value))
            yield (f"{field}.{field_b}", operator, value)
            return
        # display a in [b] as a = b
        if operator in ('in', 'not in') and isinstance(value, COLLECTION_TYPES) and len(value) == 1:
            operator = '=' if operator == 'in' else '!='
            value = next(iter(value))
        # if the value is a domain or set, change it into a list
        if isinstance(value, (*COLLECTION_TYPES, Domain)):
            value = list(value)
        yield (field, operator, value)

    def __eq__(self, other):
        return (
            isinstance(other, DomainCondition)
            and self.field == other.field
            and self.operator == other.operator
            and self.value == other.value
        )

    def __hash__(self):
        return hash(self.field) ^ hash(self.operator) ^ hash(self.value)

    def iter_conditions(self):
        yield self

    def map_conditions(self, function) -> Domain:
        result = function(self)
        assert isinstance(result, Domain), "result of map_conditions is not a Domain"
        return result

    def _raise(self, message, *args, error=ValueError) -> typing.NoReturn:
        """Raise an error message for this condition"""
        message += ' in condition (%r, %r, %r)'
        raise error(message % (*args, self.field, self.operator, self.value))

    def __get_field(self, model: BaseModel) -> tuple[Field, str]:
        """Get the field or raise an exception"""
        fname = self.field
        if '.' in fname:
            fname, property_name = fname.split('.', 1)
        else:
            property_name = ''
        try:
            field = model._fields[fname]
        except KeyError:
            self._raise("Invalid field %s.%s", model._name, fname)
        if property_name and not field.relational and field.type not in ('date', 'datetime', 'properties'):
            self._raise("Invalid field property on %s", field.type)
        return field, property_name

    def optimize(self, model: BaseModel) -> Domain:
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
        field, property_name = self.__get_field(model)
        if property_name and field.relational:
            sub_domain = DomainCondition(property_name, self.operator, self.value)
            return DomainCondition(field.name, 'any', sub_domain).optimize(model)

        # resolve inherited fields
        if field.inherited:
            parent_model = model.env[field.related_field.model_name]
            parent_fname = model._inherits[parent_model._name]
            parent_domain = self.optimize(parent_model)
            return DomainCondition(parent_fname, 'any', parent_domain)

        # handle non-stored fields (replace by searchable/stored items)
        if not field.store:
            if property_name:
                # just hope _condition_to_sql handles this expression
                return self
            # find the implementation of search and execute it
            if not field.search:
                _logger.error("Non-stored field %s cannot be searched.", field)
                if _logger.isEnabledFor(logging.DEBUG):
                    _logger.debug(''.join(traceback.format_stack()))
                return _TRUE_DOMAIN
            operator, value = self.operator, self.value
            if operator in ('in', 'not in') and len(value) == 1:
                # a lot of implementations expect '=' or '!=' operators
                operator = '=' if operator == 'in' else '!='
                value = next(iter(value))
            computed_domain = field.determine_domain(model, operator, value)
            return Domain(computed_domain).optimize(model)

        # optimizations based on operator and on field type
        for opt in _LEAF_OPTIMIZATIONS_BY_OPERATOR[self.operator]:
            dom = opt(self, model)
            if dom is not self:
                return dom.optimize(model)
        for opt in _LEAF_OPTIMIZATIONS_BY_FIELD_TYPE[field.type]:
            dom = opt(self, model)
            if dom is not self:
                return dom.optimize(model)

        # asserts after optimization
        operator = self.operator
        if operator not in STANDARD_CONDITION_OPERATORS:
            self._raise("Not standard operator left")

        if (
            not field.relational
            and operator in ('any', 'not any')
            and field.name != 'id'  # can use 'id'
            # # Odoo internals use ('xxx', 'any', Query), check only Domain
            and (not field.store or isinstance(self.value, Domain))
        ):
            self._raise("Cannot use 'any' with non-relational fields")

        return self

    def _to_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        field_expr, operator, value = self.field, self.operator, self.value
        return model._condition_to_sql(alias, field_expr, operator, value, query)


# --------------------------------------------------
# Optimizations: registration
# --------------------------------------------------

_LEAF_MERGE_OPTIMIZATIONS: list[Callable[[type[DomainNary], BaseModel, Iterable[Domain]], Iterable[Domain]]] = list()
_LEAF_OPTIMIZATIONS_BY_FIELD_TYPE: collections.defaultdict[str, list[Callable[[DomainCondition, BaseModel], Domain]]] = collections.defaultdict(list)
_LEAF_OPTIMIZATIONS_BY_OPERATOR: collections.defaultdict[str, list[Callable[[DomainCondition, BaseModel], Domain]]] = collections.defaultdict(list)


def _optimize_nary_sort_key(domain: Domain) -> tuple[str, str, str]:
    """Sorting key for nary domains so that similar operators are grouped together.

    1. Field name (non-simple conditions are sorted at the end)
    2. Operator type (equality, inequality, existance, string comparison, other)
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
        elif positive_op.endswith('like'):
            order = "like"
        else:
            order = positive_op
        return domain.field, order, operator
    else:
        # in python; '~' > any letter
        assert hasattr(domain, 'OPERATOR') and isinstance(domain.OPERATOR, str)
        return '~', '', domain.OPERATOR


def nary_optimization(*, operators: Collection[str], field_condition: Callable[[Field], bool] | None = None):
    """Register an optimization to a list of children of an nary domain.

    The function `(cls: type[DomainNary], model: BaseModel, conditions: list[DomainCondition]) -> Iterable[Domain]`
    can be registered for some operators or some fields.
    It returns the list of *optimized* domains.
    If you register without any operators, all the domain children will be
    passed at once.

    Note that you always need to optimize both AND and OR domains. It is always
    possible because if you can optimize `a & b` then you can optimize `a | b`
    because it is optimizing `~(~a & ~b)`. Since operators can be nagated,
    all implementations of optimizations are implemented in a mirrored way:
    `(optimize AND) if some_condition == cls.ZERO.value else (optimize OR)`.

    The optimization of nary domains starts by optimizing the children,
    then sorts them by (field, operator_type, operator) where operator type
    groups similar operators together.

    NOTE: if you want to merge different operator types, register for
    `operator=CONDITION_OPERATORS` and find conditions that you want to merge.
    """
    def register(optimization: Callable[[type[DomainNary], BaseModel, list[DomainCondition]], Iterable[Domain]]):
        def optimizer(cls, model, conditions: Iterable[Domain]):
            for (field_name, apply_operator), conds in itertools.groupby(
                conditions, lambda c: (c.field, True) if c.field and c.operator in operators else ('', False)  # type: ignore
            ):
                if (
                    apply_operator
                    and (not field_condition or (
                        (field := model._fields.get(field_name)) and field_condition(field)
                    ))
                    and len(conds := list(conds)) > 1  # type: ignore
                ):
                    yield from optimization(cls, model, conds)  # type: ignore
                else:
                    yield from conds
        _LEAF_MERGE_OPTIMIZATIONS.append(optimizer)
        return optimization

    def register_generic(optimization: Callable[[type[DomainNary], BaseModel, Iterable[Domain]], Iterable[Domain]]):
        _LEAF_MERGE_OPTIMIZATIONS.append(optimization)
        return optimization

    if operators:
        return register
    else:
        assert not field_condition, "field_condition not supported without operators"
        return register_generic


def operator_optimization(operator: str | list[str]):
    """Register a condition operator optimization for (condition, model)"""
    assert operator, "Missing operator to register"
    if isinstance(operator, list):
        operators = operator
    else:
        operators = [operator]
    CONDITION_OPERATORS.update(operators)

    def register(optimization: Callable[[DomainCondition, BaseModel], Domain]):
        for operator in operators:
            _LEAF_OPTIMIZATIONS_BY_OPERATOR[operator].append(optimization)
        return optimization
    return register


def field_type_optimization(field_type: str | list[str]):
    """Register a condition optimization by field type for (condition, model)"""
    if isinstance(field_type, list):
        field_types = field_type
    else:
        field_types = [field_type]

    def register(optimization: Callable[[DomainCondition, BaseModel], Domain]):
        for field_type in field_types:
            _LEAF_OPTIMIZATIONS_BY_FIELD_TYPE[field_type].append(optimization)
        return optimization
    return register


# --------------------------------------------------
# Optimizations: conditions
# --------------------------------------------------


def _value_to_ids(
    value: typing.Any,
    comodel: BaseModel,
    operator: str,
    search_domain: Domain = Domain.TRUE,
) -> OrderedSet[int] | Query | SQL:
    """For relational fields, transform a value into a set of ids or query."""
    if isinstance(value, (Query, SQL)):
        return value
    if isinstance(value, int):
        return OrderedSet((value,)) if value else OrderedSet()
    # make a collection of names
    if isinstance(value, str):
        value = (value,)
    elif not isinstance(value, COLLECTION_TYPES):
        raise TypeError(f"Invalid argument to get ids from {comodel._name}: {value!r}")
    # split by type
    int_values, values = partition(lambda v: isinstance(v, int), value)
    if not values:
        # only int, return an OrderedSet
        return value if isinstance(value, OrderedSet) else OrderedSet(value)
    # search using the display_name
    if operator == 'in':
        domain = Domain('display_name', 'in', values)
    else:
        domain = DomainOr.new(
            Domain('display_name', operator, v)
            for v in values
        )
    if int_values:
        domain |= Domain('id', 'in', int_values)
    domain &= search_domain
    return comodel._search(domain)


@operator_optimization(operator='=?')
def _operator_equal_if_value(leaf, _):
    """a =? b  <=>  not b or a = b"""
    if not leaf.value:
        return _TRUE_DOMAIN
    return DomainCondition(leaf.field, 'in', OrderedSet([leaf.value]))


@operator_optimization(operator='<>')
def _operator_different(leaf, _):
    """a <> b  =>  a != b"""
    # already a rewrite-rule
    warnings.warn("Operator '<>' is deprecated, use '!=' directly", DeprecationWarning)
    return DomainCondition(leaf.field, '!=', leaf.value)


@operator_optimization(operator='==')
def _operator_equals(leaf, _):
    """a == b  =>  a = b"""
    # rewrite-rule
    warnings.warn("Operator '==' is deprecated, use '=' directly", DeprecationWarning)
    return DomainCondition(leaf.field, '=', leaf.value)


@operator_optimization(operator='=')
def _operator_equal_as_in(leaf, _):
    """a = b  <=>  a in [b]"""
    value = leaf.value
    if not isinstance(value, COLLECTION_TYPES) and not value:
        value = False
    return DomainCondition(leaf.field, 'in', [value])


@operator_optimization(operator='!=')
def _operator_nequal_as_not_in(leaf, _):
    """a != b  <=>  a not in [b]"""
    value = leaf.value
    if not isinstance(value, COLLECTION_TYPES) and not value:
        value = False
    return DomainCondition(leaf.field, 'not in', [value])


@operator_optimization(['any', 'not any'])
def _optimize_id_any_condition(leaf, _):
    """ Any condition on 'id'

    id ANY domain  <=>  domain
    id NOT ANY domain  <=>  ~domain
    """
    if leaf.field == 'id' and isinstance(domain := leaf.value, Domain):
        if leaf.operator == 'not any':
            domain = ~domain
        return domain
    return leaf


@operator_optimization(['in', 'not in'])
def _optimize_in_set(leaf, _):
    """Make sure the value is a OrderedSet()"""
    value = leaf.value
    # isinstance(value, (Query, SQL)) already handled during building
    if not value:
        # empty, return a boolean
        return Domain(leaf.operator == 'not in')
    if isinstance(value, OrderedSet):
        return leaf
    if isinstance(value, COLLECTION_TYPES):
        return DomainCondition(leaf.field, leaf.operator, OrderedSet(value))
    leaf._raise("Not a list of values, use the '=' or '!=' operator")


@operator_optimization(['any', 'not any'])
def _optimize_any_domain(leaf, model):
    """Make sure the value is an optimized domain (or Query or SQL)"""
    value = leaf.value
    if isinstance(value, (Query, SQL)):
        return leaf
    # get the model to optimize with
    try:
        field = model._fields[leaf.field]
        comodel = model.env[field.comodel_name]
    except KeyError:
        raise ValueError(f"Cannot determine the relation for {leaf.field}")
    domain = Domain(value).optimize(comodel)
    # const if the domain is empty, the result is a constant
    # if the domain is True, we keep it as is
    if domain.is_false():
        return Domain(leaf.operator == 'not any')
    # if unchanged, return the leaf
    if domain is value:
        return leaf
    return DomainCondition(leaf.field, leaf.operator, domain)


@operator_optimization([op for op in CONDITION_OPERATORS if op.endswith('like')])
def _optimize_like_str(leaf, model):
    """Validate value for pattern matching, must be a str"""
    value = leaf.value
    if not value:
        # =like matches only empty string (inverse the condition)
        result = (leaf.operator not in NEGATIVE_CONDITION_OPERATORS) != ('=' in leaf.operator)
        # relational and non-relation fields behave differently
        if model._fields[leaf.field].relational or '=' in leaf.operator:
            return DomainCondition(leaf.field, 'not in' if result else 'in', OrderedSet([False]))
        return Domain(result)
    if isinstance(value, (str, SQL)):
        # accept both str and SQL
        return leaf
    return DomainCondition(leaf.field, leaf.operator, str(value))


@field_type_optimization(['many2one', 'one2many', 'many2many'])
def _optimize_relational_name_search(leaf, model):
    """Search using display_name; see _value_to_ids."""
    operator = leaf.operator
    value = leaf.value
    # Handle only: like operator, equality with str values
    if not (
        operator.endswith('like')
        or (
            operator in ('in', 'not in')
            and isinstance(value, COLLECTION_TYPES)
            and any(isinstance(v, str) for v in value)
        )
    ):
        return leaf
    # operator
    positive_operator = NEGATIVE_CONDITION_OPERATORS.get(operator, operator)
    positive = operator == positive_operator
    # get the comodel
    field = model._fields[leaf.field]
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
    return DomainCondition(leaf.field, any_operator, value)


@field_type_optimization('boolean')
def _optimize_in_boolean(leaf, model):
    """b in [True, False]  =>  True"""
    value = leaf.value
    if leaf.operator not in ('in', 'not in') or not isinstance(value, COLLECTION_TYPES):
        return leaf
    if not all(isinstance(v, bool) for v in value):
        if any(isinstance(v, str) for v in value):
            # TODO make a warning
            _logger.debug("Comparing boolean with a string in %s", leaf)
        value = OrderedSet(
            str2bool(v.lower(), False) if isinstance(v, str) else bool(v)
            for v in value
        )
    if value == {False, True}:
        # tautology is simplified to a boolean
        # note that this optimization removes fields (like active) from the domain
        return Domain(leaf.operator == 'in')
    if value is leaf.value:
        return leaf
    return DomainCondition(leaf.field, leaf.operator, value)


def _value_to_date(value):
    # check datetime first, because it's a subclass of date
    if isinstance(value, SQL):
        return value
    if isinstance(value, datetime):
        return value.date()
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
        return datetime.fromisoformat(value).date()
    if isinstance(value, COLLECTION_TYPES):
        return OrderedSet(_value_to_date(v) for v in value)
    raise ValueError('Failed to cast %r into a date' % value)


@field_type_optimization('date')
def _optimize_type_date(leaf, _):
    """Make sure we have a date type in the value"""
    if leaf.operator.endswith('like') or "." in leaf.field:
        return leaf
    operator = leaf.operator
    value = _value_to_date(leaf.value)
    if value is False and operator[0] in ('<', '>'):
        # comparison to False results in an empty domain
        return _FALSE_DOMAIN
    if value == leaf.value:
        return leaf
    return DomainCondition(leaf.field, operator, value)


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
    raise ValueError('Failed to cast %r into a datetime' % value)


@field_type_optimization('datetime')
def _optimize_type_datetime(leaf, _):
    """Make sure we have a datetime type in the value"""
    if leaf.operator.endswith('like') or "." in leaf.field:
        return leaf
    operator = leaf.operator
    value, is_day = _value_to_datetime(leaf.value)
    if value is False and operator[0] in ('<', '>'):
        # comparison to False results in an empty domain
        # TODO we should raise an error, but it's currently used
        return _FALSE_DOMAIN
    if value == leaf.value:
        assert not is_day
        return leaf

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
            return DomainCondition(leaf.field, 'not in', OrderedSet([False]))
        operator = '<'

    return DomainCondition(leaf.field, operator, value)


@field_type_optimization('binary')
def _optimize_type_binary_attachment(leaf, model):
    field = model._fields[leaf.field]
    operator = leaf.operator
    if field.attachment and not (operator in ('in', 'not in') and leaf.value == {False}):
        try:
            leaf._raise('Binary field stored in attachment, accepts only existence check; skipping domain')
        except ValueError:
            # log with stacktrace
            _logger.exception("Invalid operator for a binary field")
        return _TRUE_DOMAIN
    if operator.endswith('like'):
        leaf._raise('Cannot use like operators with binary fields', error=NotImplementedError)
    return leaf


def _operator_child_of_domain(comodel, parent):
    """Return a set of ids or a domain to find all children of given model"""
    if comodel._parent_store and parent == comodel._parent_name:
        domain = DomainOr.new(
            DomainCondition('parent_path', '=like', rec.parent_path + '%')
            for rec in comodel
        )
        return domain
    else:
        # recursively retrieve all children nodes with sudo(); the
        # filtering of forbidden records is done by the rest of the
        # domain
        child_ids = OrderedSet()
        while comodel:
            child_ids.update(comodel._ids)
            query = comodel._search(DomainCondition(parent, 'in', OrderedSet(comodel.ids)))
            new_ids = OrderedSet(query.get_result_ids()) - child_ids
            comodel = comodel.browse(new_ids)
    return child_ids


def _operator_parent_of_domain(comodel, parent):
    """Return a set of ids or a domain to find all parents of given model"""
    if comodel._parent_store and parent == comodel._parent_name:
        parent_ids = OrderedSet(
            int(label)
            for rec in comodel
            for label in rec.parent_path.split('/')[:-1]
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


@operator_optimization(['parent_of', 'child_of'])
def _operator_hierarchy(leaf, model):
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
    if leaf.operator == 'parent_of':
        hierarchy = _operator_parent_of_domain
    else:
        hierarchy = _operator_child_of_domain
    value = leaf.value
    if value is False:
        _logger.warning('Using %s with False value, the result will be empty', leaf.operator)
    # Get:
    # - field: used in the resulting domain)
    # - parent (str | None): field name to find parent in the hierarchy
    # - comodel_sudo: used to resolve the hierarchy
    # - comodel: used to search for ids based on the value
    field = model._fields[leaf.field]
    if field.type == 'many2one':
        comodel = model.env[field.comodel_name].with_context(active_test=False)
    elif field.type in ('one2many', 'many2many'):
        comodel = model.env[field.comodel_name].with_context(**field.context)
    elif field.name == 'id':
        comodel = model
    else:
        leaf._raise(f"Cannot execute {leaf.operator} for {field}, works only for relational fields")
    comodel_sudo = comodel.sudo().with_context(active_test=False)
    parent = comodel._parent_name
    if comodel._name == model._name:
        if leaf.field != 'id':
            parent = leaf.field
        if field.type == 'many2one':
            field = model._fields['id']
    # Get the initial ids and bind them to comodel_sudo before resolving the hierarchy
    coids = _value_to_ids(value, comodel, 'in')
    if field.type == 'many2many' or isinstance(coids, SQL):
        # always search for many2many
        coids = comodel.search(Domain('id', 'in', coids)).ids
    if not coids:
        return _FALSE_DOMAIN
    result = hierarchy(comodel_sudo.browse(coids), parent)
    # Format the resulting domain
    if isinstance(result, Domain):
        if field.name == 'id':
            return result
        return DomainCondition(field.name, 'any', result)
    return DomainCondition(field.name, 'in', result)


# --------------------------------------------------
# Optimizations: nary
# --------------------------------------------------


@nary_optimization(operators=('in', 'not in'), field_condition=lambda f: not f.type.endswith('2many'))
def _optimize_merge_set_conditions(cls: type[DomainNary], model, conditions):
    """Merge equality conditions.

    Combine the 'in' and 'not in' conditions to a single set of values.
    Do no touch x2many fields which have a different semantic.

    Examples:

        a in {1} or a in {2}  <=>  a in {1, 2}
        a in {1, 2} and a not in {2, 5}  =>  a in {2}
    """
    assert isinstance(conditions, list)
    assert all(isinstance(cond.value, OrderedSet) for cond in conditions)
    set_in: OrderedSet | None = None
    set_not_in: OrderedSet | None = None
    zero = cls.ZERO.value
    # build the sets for 'in' and 'not in' conditions
    for cond in conditions:
        value = cond.value
        if cond.operator == 'in':
            if set_in is None:
                set_in = OrderedSet(value)
                continue
            current_set = set_in
        else:
            if set_not_in is None:
                set_not_in = OrderedSet(value)
                continue
            current_set = set_not_in
        if (cond.operator == 'in') == zero:
            current_set &= value
        else:
            current_set |= value
    # build the result
    if zero:
        # set_in and set_not_in
        set_dominating, set_other, op = set_in, set_not_in, 'in'
    else:
        # set_in or set_not_in
        set_dominating, set_other, op = set_not_in, set_in, 'not in'
    if set_dominating is not None:
        if set_other is not None:
            set_dominating -= set_other
        result_condition = DomainCondition(cond.field, op, set_dominating)
    else:
        op = 'not in' if op == 'in' else 'in'
        result_condition = DomainCondition(cond.field, op, set_other)
    return [result_condition.optimize(model)]


@nary_optimization(operators=('any',), field_condition=lambda f: f.type == 'many2one')
def _optimize_merge_many2one_any(cls, model, conditions):
    """Merge domains of 'any' conditions for many2one fields.

    This will lead to a smaller number of sub-queries which are equivalent.
    Example:

        a.f = 8 and a.g = 5  <=>  a any (f = 8 and g = 5)
    """
    merge_conditions, other_conditions = partition(lambda c: isinstance(c.value, Domain), conditions)
    if len(merge_conditions) < 2:
        return conditions
    field = merge_conditions[0].field
    sub_domains = [c.value for c in merge_conditions]
    return [DomainCondition(field, 'any', cls(sub_domains)).optimize(model), *other_conditions]


@nary_optimization(operators=('not any',), field_condition=lambda f: f.type == 'many2one')
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
    field = merge_conditions[0].field
    sub_domains = [c.value for c in merge_conditions]
    cls = cls.inverse_nary()
    return [DomainCondition(field, 'not any', cls(sub_domains)).optimize(model), *other_conditions]


@nary_optimization(operators=('any',), field_condition=lambda f: f.type.endswith('2many'))
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


@nary_optimization(operators=('not any',), field_condition=lambda f: f.type.endswith('2many'))
def _optimize_merge_x2many_not_any(cls, model, conditions):
    """Merge domains of 'not any' conditions for x2many fields.

    This will lead to a smaller number of sub-queries which are equivalent.
    Example:

        a not any f = 1 and a not any g = 5  <=>  a not any (f = 1 or g = 5)
    """
    if cls is DomainOr:
        return conditions
    return _optimize_merge_many2one_not_any(cls, model, conditions)


@nary_optimization(operators=())
def _optimize_same_conditions(cls, model, conditions: Iterable[Domain]):
    """Merge (adjactent) conditions that are the same.

    Quick optimization for some conditions, just compare if we have the same
    condition twice.
    """
    # just check the adjacent conditions for simple domains
    # TODO replace this by:
    # 1. optimize inequalities
    # 2. optimize like with same prefixes
    # 3. remove this function as equalities and existance is already covered
    for a, b in itertools.pairwise(itertools.chain([None], conditions)):
        if a == b:
            continue
        yield b
