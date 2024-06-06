# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Domain expression processing

The domain represents a first-order logic expression.
The main duty of this module is to represent filter conditions on models
and ease rewriting them.
A lot of things should be documented here, but as a first
step in the right direction, some tests in test_expression.py
might give you some additional information.

For legacy reasons, a domain uses an inconsistent two-levels abstract
syntax (domains were a regular Python data structures). At the first
level, a domain is an expression made of terms (sometimes called
leaves) and (domain) operators used in prefix notation. The available
operators at this level are '!', '&', and '|'. '!' is a unary 'not',
'&' is a binary 'and', and '|' is a binary 'or'.  For instance, here
is a possible domain. (<term> stands for an arbitrary term, more on
this later.)::

    ['&', '!', <term1>, '|', <term2>, <term3>]

It is equivalent to this pseudo code using infix notation::

    (not <term1>) and (<term2> or <term3>)

The second level of syntax deals with the term representation. A term
is a triple of the form (left, operator, right). That is, a term uses
an infix notation, and the available operators, and possible left and
right operands differ with those of the previous level. Here is a
possible term::

    ('company_id.name', '=', 'OpenERP')

The left and right operand don't have the same possible values. The
left operand is field name (related to the model for which the domain
applies).  Actually, the field name can use the dot-notation to
traverse relationships.  The right operand is a Python value whose
type should match the used operator and field type. In the above
example, a string is used because the name field of a company has type
string, and because we use the '=' operator. When appropriate, a 'in'
operator can be used, and thus the right operand should be a collection.
"""
from __future__ import annotations

import collections
import logging
import traceback
import warnings
from abc import ABC, abstractmethod
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Callable, overload

from odoo.tools import SQL, Query, str2bool

if TYPE_CHECKING:
    from odoo.models import BaseModel


_logger = logging.getLogger(__name__)


STANDARD_TERM_OPERATORS = frozenset([
    'any', 'not any',
    'in', 'not in',
    '<', '>', '<=', '>=',
    'like', 'not like',
    'ilike', 'not ilike',
    '=like', '=ilike',
    # TODO "not =like"?
])
"""List of standard term operators.

- `any` works for relational fields and `id` to check if a record *exists*
  that verifies the condition
  - if value is SQL or Query, bypass record rules
  - if auto_join is set on the field, bypass record rules
  - if value is a domain for a many2one (or `id`),
    _search using active_test=False
  - if value is a domain for a x2many,
    _search using the context from the field
- `in` where value is a collection of values
  - the collection is transformed into a set
  - False indicates that the value is *not set*
  - for relational fields
    - if int, bypass record rules
    - if str, search the field by name
- `<`, `>`, ... inequality check, similar behaviour to `in` with a single value
- `=like` compare to a string using SQL like semantics
- `=ilike` compare to a string after applying `unaccent` of both field and value
- `like`, `ilike` behave like the preceding methods, but add a *contain*
  semantic (wildcard around the value)
"""
TERM_OPERATORS = {
    '=', '!=',
    '=?',
    'child_of', 'parent_of',
} | STANDARD_TERM_OPERATORS
"""
List of available term operators.
The non-standard operators can be reduced to standard operators by using the
optimization function. See the respective optimization functions for the
details.
"""

NEGATIVE_TERM_OPERATORS = {
    op: op[4:]
    for op in TERM_OPERATORS
    if op.startswith('not ')
} | {'!=': '='}
"""A subset of operators with a 'negative' semantic, mapping to the 'positive' operator."""

# negations for operators (used in DomainNot)
_TERM_OPERATORS_NEGATION = {
    '<': '>=',
    '>': '<=',
} | NEGATIVE_TERM_OPERATORS
_TERM_OPERATORS_NEGATION |= {
    op_pos: op_neg
    for op_neg, op_pos in _TERM_OPERATORS_NEGATION.items()
}

_TRUE_LEAF = (1, '=', 1)
_FALSE_LEAF = (0, '=', 1)


# --------------------------------------------------
# Domain definition and manipulation
# --------------------------------------------------

class Domain(ABC):
    """Representation of a domain as an object, allow for nomalization and
    comination.

    Don't use the domain classes directly, always use `D()`.
    """
    field = None  # ease checks whether the domain is concerning a field

    def __and__(self, other):
        """Domain & Domain"""
        if isinstance(other, DomainAnd):
            return other & self
        return DomainAnd.new(self, D(other))

    def __or__(self, other):
        """Domain | Domain"""
        if isinstance(other, DomainOr):
            return other | self
        return DomainOr.new(self, D(other))

    def __invert__(self):
        """~Domain"""
        return DomainNot(self)

    def __add__(self, other):
        """Domain + [...]

        For backward-compatibility of domain composition.
        Concatenate as lists.
        If we have two domains, equivalent to '&'.
        """
        if isinstance(other, Domain):
            return self & other
        if not isinstance(other, list):
            raise TypeError('Domain() can concatenate only lists')
        return list(self) + other

    def __rand__(self, other):
        """Commutative definition of *and*"""
        return self.__and__(other)

    def __ror__(self, other):
        """Commutative definition of *or*"""
        return self.__or__(other)

    def __radd__(self, other):
        """Commutative definition of *+*"""
        # special case, where we prepend "not"
        if other == ['!']:
            return ~self
        # we are pre-pending, return a list
        # because the result may not be normalized
        return other + list(self)

    def __bool__(self):
        """For backward-compatibility, the domain [] was False, indicating an
        empty domain is False, an empty domain is DomainTrue"""
        return self.const() is not True

    @abstractmethod
    def __eq__(self, other):
        raise NotImplementedError

    @abstractmethod
    def __hash__(self):
        raise NotImplementedError

    @abstractmethod
    def __iter__(self):
        """For-backward compatibility, return the polish-notation domain list"""
        yield
        raise NotImplementedError

    def __reversed__(self):
        """For-backward compatibility, reversed iter"""
        return reversed(list(self))

    def __repr__(self) -> str:
        # return representation of the object as the old-style list
        return repr(list(self))

    def const(self) -> bool | None:
        """Constant value or None"""
        return None

    def _optimize(self, model: BaseModel) -> Domain:
        """Perform optimizations of the node given a model to resolve the fields

        The model is used to validate fields and perform additional type-dependent optimizations.
        Some executions may be performed, like executing `search` for non-stored fields.
        """
        return self

    @abstractmethod
    def _build_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        """Build the where_clause and the where_params (must be optimized with field)"""
        raise NotImplementedError


class DomainConst(Domain, BaseException, ABC):
    """Constant domain: True/False

    You can raise it to break loops easier.
    """
    VALUE: bool

    def __eq__(self, other):
        return isinstance(other, DomainConst) and self.const() == other.const()

    def __hash__(self):
        return hash(self.VALUE)

    def const(self):
        return self.VALUE


class DomainTrue(DomainConst):
    """Domain: True"""
    VALUE = True

    def __and__(self, other):
        return D(other)

    def __or__(self, other):
        return self

    def __invert__(self):
        return FALSE_DOMAIN

    def __iter__(self):
        yield _TRUE_LEAF

    def _build_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        return SQL("TRUE")


class DomainFalse(DomainConst):
    """Domain: False"""
    VALUE = False

    def __and__(self, other):
        return self

    def __or__(self, other):
        return D(other)

    def __invert__(self):
        return TRUE_DOMAIN

    def __iter__(self):
        yield _FALSE_LEAF

    def _build_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        return SQL("FALSE")


TRUE_DOMAIN = DomainTrue()
FALSE_DOMAIN = DomainFalse()


class DomainNot(Domain):
    """Negation domain, contains a single child"""
    OPERATOR = '!'

    __slots__ = ('child',)
    child: Domain

    def __init__(self, child: Domain):
        self.child = child

    def __invert__(self):
        return self.child

    def __iter__(self):
        yield self.OPERATOR
        yield from self.child

    def _optimize(self, model: BaseModel) -> Domain:
        """Optimization step.

        Push down the operator as much as possible.
        """
        child = self.child
        # not not a  <=>  a
        if isinstance(child, DomainNot):
            child = child.child
            return child._optimize(model)
        # and/or push down
        # not (a or b)  <=>  (not a and not b)
        # not (a and b)  <=>  (not a or not b)
        if isinstance(child, DomainNary):
            # implemented in nary
            child = ~child
            return child._optimize(model)
        # first optimize the child
        # check constant and operator negation
        result = ~(child._optimize(model))
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

    def _build_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        condition = self.child._build_sql(model, alias, query)
        return SQL("NOT (%s)", condition)


class DomainNary(Domain, ABC):
    """Domain for a nary operator: AND or OR with multiple children"""
    OPERATOR: str
    OPERATOR_SQL: SQL = SQL(' ??? ')
    ZERO: DomainConst = FALSE_DOMAIN  # default for lint checks

    __slots__ = ('children', '_model_optimized')
    children: list[Domain]
    _model_optimized: str

    def __init__(self, children: list[Domain], _model_name: str = ''):
        """Create the domain with conditions

        To speed up `_optimize()` calls, we keep `self._model_optimized`
        for binary operators when the optimization was done.
        """
        self.children = children
        self._model_optimized = _model_name

    @classmethod
    def new(cls, *items) -> Domain:
        try:
            children = list(cls._simplify_children(D(item) for item in items))
            return cls(children).unwrap()
        except DomainConst as c:
            return c

    def unwrap(self) -> Domain:
        """Return a simplified domain in case the children are empty or contain
        only a single element.

        You can use this after creating a new instance.
        """
        children = self.children
        len_children = len(children)
        if len_children == 0:
            return self.ZERO
        if len_children == 1:
            return children[0]
        return self

    @classmethod
    def _simplify_children(cls, children):
        """Yield all children (flattened for same domain type).

        If we have the same type, just copy the children.
        If we have a constant: if it's the zero, ignore it;
        otherwise raise ~zero.
        """
        for c in children:
            if isinstance(c, cls):
                # same class, flatten
                yield from c.children
            elif isinstance(c, DomainConst):
                if c.const() == cls.ZERO.const():
                    continue
                raise ~cls.ZERO
            else:
                yield c

    def __iter__(self):
        if not self.children:
            yield from self.ZERO
            return
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

    @abstractmethod
    def __invert__(self):
        raise NotImplementedError

    def _optimize(self, model: BaseModel) -> Domain:
        """Optimization step.

        If the return type is a binary domain, there are multiple children.

        Optimize all children with the given model.
        Run the registered optimizations, if all children are optimal, stop.
        """
        # check if already optimized
        if self._model_optimized:
            if model._name != self._model_optimized:
                _logger.warning(
                    "Optimizing with different models %s and %s",
                    self._model_optimized, model._name,
                )
            return self
        # optimize children
        cls = type(self)  # used for optimizations and rebuilding
        children = self.children
        optimal_children: set[int] = set()  # check children identity instead of hash
        try:
            children = list(self._simplify_children(c._optimize(model) for c in children))
            while True:
                if len(children) < 2:
                    break
                optimal_children.update(id(c) for c in children)
                for opt in _NARY_OPTIMIZATIONS:
                    children = opt(cls, children, model)
                optimized = True
                for i, child in enumerate(children):
                    if id(child) in optimal_children:
                        continue
                    children[i] = child._optimize(model)
                    optimized = False
                if optimized:
                    break
                children = list(self._simplify_children(children))
        except DomainConst as c:
            return c
        # return the result a as simple node
        len_children = len(children)
        if len_children == 0:
            return self.ZERO
        if len_children == 1:
            return children[0]
        return cls(children, _model_name=model._name)

    def _build_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        assert self.children, "No children, optimize() probably not executed"
        return SQL("(%s)", self.OPERATOR_SQL.join(
            c._build_sql(model, alias, query) for c in self.children
        ))

    @classmethod
    def build_sql(cls, *items: SQL) -> SQL:
        """Build the SQL value combining the given items"""
        if not items:
            return SQL(str(cls.ZERO.VALUE).upper())
        if len(items) == 1:
            return items[0]
        return SQL("(%s)", cls.OPERATOR_SQL.join(items))


class DomainAnd(DomainNary):
    """Domain: AND with multiple children"""
    OPERATOR = '&'
    OPERATOR_SQL = SQL(" AND ")
    ZERO = TRUE_DOMAIN

    def __invert__(self):
        return DomainOr([~c for c in self.children])

    def __and__(self, other):
        # simple optimization to append children
        if isinstance(other, DomainAnd):
            return DomainAnd(self.children + other.children)
        if isinstance(other, Domain) and not isinstance(other, (DomainConst, DomainNary)):
            return DomainAnd(self.children + [other])
        return super().__and__(other)


class DomainOr(DomainNary):
    """Domain: OR with multiple children"""
    OPERATOR = '|'
    OPERATOR_SQL = SQL(" OR ")
    ZERO = FALSE_DOMAIN

    def __invert__(self):
        return DomainAnd([~c for c in self.children])

    def __or__(self, other):
        # simple optimization to append children
        if isinstance(other, DomainOr):
            return DomainOr(self.children + other.children)
        if isinstance(other, Domain) and not isinstance(other, (DomainConst, DomainNary)):
            return DomainOr(self.children + [other])
        return super().__or__(other)


class DomainField(Domain):
    """Leaf field domain: (field, operator, value)

    A field (or expression) is compared to a value. The list of supported
    operators are described in TERM_OPERATORS.
    """
    __slots__ = ('field', 'operator', 'value')
    field: str
    operator: str
    # value can have multiple types

    def __init__(self, field: str, operator: str, value):
        """Init a new leaf (internal init)

        :param field: Field name or field path
        :param operator: A valid operator
        :param value: A value for the comparison
        """
        self.field = field
        self.operator = operator
        self.value = value

    @classmethod
    def new(cls, field_name, operator, value) -> DomainField:
        """Validate the inputs and create a domain

        :param field_name: Field name, whic is a non empty string
        :param operator: Operator
        :param value: The value
        """
        if value is None:
            value = False
        rep = (field_name, operator, value)
        if not isinstance(field_name, str) or not field_name:
            raise TypeError(f"Empty field name in leaf {rep!r}")
        # Rewrites done here to have already a more normalized domain (quick optimizations)
        # Check if the operator is valid
        operator = operator.lower()
        if operator != rep[1]:
            warnings.warn(f"The domain term {rep!r} should have a lower-case operator", DeprecationWarning)
        if operator == '<>':
            warnings.warn("Operator '<>' is deprecated, use '!=' directly", DeprecationWarning)
            operator = '!='
        if operator not in TERM_OPERATORS:
            raise ValueError(f"Invalid operator in {rep!r}")
        # check already the consistency for domain manipulation
        # - NewId value (not supported)
        # - Query and Domain values should be using a relational operator
        # - replace '=' with 'in'
        #   (x, '=', a) becomes (x, 'in', {a})
        # - check that 'in' contains a collection
        from odoo.models import NewId  # don't import at top-level to avoid circular imports
        if isinstance(value, NewId):
            _logger.warning("Domains don't support NewId, provide origin instead, for leaf %r", rep, exc_info=True)
            value = value.origin or -1  # extract origin or use a dummy id
        if isinstance(value, SQL) and operator not in ('any', 'not any', 'in', 'not in'):
            # accept SQL object in the right part for simple operators
            # use case: compare 2 fields
            # TODO we should remove support for SQL in the domain value
            pass
        elif isinstance(value, (Domain, Query, SQL)):
            if operator not in ('any', 'not any', 'in', 'not in'):
                warnings.warn(f"The domain term {rep!r} should use the 'any' or 'not any' operator.", DeprecationWarning)
            operator = 'not any' if operator in NEGATIVE_TERM_OPERATORS else 'any'
        elif operator in ('any', 'not any'):
            # parse the value as a domain
            value = D(value)
        elif operator in ('=', '!='):
            operator = 'in' if operator == '=' else 'not in'
            if isinstance(value, (list, tuple, set)):
                if not value:  # views sometimes use ('user_ids', '!=', []) to indicate the user is set
                    # TODO _logger.warning("The domain term %s should compare with False.", rep)
                    value = {False}
                else:
                    # TODO _logger.warning("The domain term %s should use the 'in' or 'not in' operator.", rep)
                    value = set(value)
            else:
                value = {value}
        elif operator in ('in', 'not in') and not isinstance(value, (list, tuple, set)):
            # TODO show warning, except occurrences like ('groups_id', 'in', ref(...).id)
            if field_name not in {'groups_id', 'user_ids'}:
                pass  # TODO _logger.warning("The domain term %s should have a list value.", rep)
            value = {value}
        return DomainField(field_name, operator, value)

    @classmethod
    def _is_set(cls, field, is_set):
        """Build a condition whether 'field is set'"""
        return cls(field, 'not in' if is_set else 'in', {False})

    def __invert__(self):
        # can we just update the operator?
        if neg_op := _TERM_OPERATORS_NEGATION.get(self.operator):
            return DomainField(self.field, neg_op, self.value)
        return super().__invert__()

    def __iter__(self):
        field, operator, value = self.field, self.operator, self.value
        # display a any [b op x] as a.b op x
        if operator == 'any' and isinstance(value, DomainField):
            field_b, operator, value = next(iter(value))
            yield (f"{field}.{field_b}", operator, value)
            return
        # display a in [b] as a = b
        if operator in ('in', 'not in') and isinstance(value, set) and len(value) == 1:
            operator = '=' if operator == 'in' else '!='
            value = next(iter(value))
        # if the value is a domain or set, change it into a list
        if isinstance(value, (set, Domain)):
            value = list(value)
        yield (field, operator, value)

    def __eq__(self, other):
        return (
            isinstance(other, DomainField)
            and self.field == other.field
            and self.operator == other.operator
            and self.value == other.value
        )

    def __hash__(self):
        return hash(self.field) ^ hash(self.operator) ^ hash(self.value)

    def _raise(self, message, *args, error=ValueError):
        """Raise an error message for this leaf"""
        message += ' in leaf (%r, %r, %r)'
        raise error(message % (*args, self.field, self.operator, self.value))

    def __get_field(self, model):
        """Get the field with correct exception"""
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

    def _optimize(self, model: BaseModel) -> Domain:
        """Optimization step.

        With a model, dispatch optimizations according the the operator and
        the type of the field.

        - Validate the field.
        - Decompose *paths* into domains using 'any'.
        - If the field is *not stored*, run the search function of the field.
        - Run optimizations.
        - Check the output.
        """
        # optimize path
        field, property_name = self.__get_field(model)
        if property_name and field.relational:
            sub_domain = DomainField(property_name, self.operator, self.value)
            return DomainField(field.name, 'any', sub_domain)._optimize(model)

        # resolve inherited fields
        if field.inherited:
            parent_model = model.env[field.related_field.model_name]
            parent_fname = model._inherits[parent_model._name]
            parent_domain = self._optimize(parent_model)
            return DomainField(parent_fname, 'any', parent_domain)

        # handle non-stored fields (replace by queryable/stored items)
        if not field.store:
            if property_name:
                # just hope _condition_to_sql handles this expression
                return self
            # find the implementation of search and execute it
            if not field.search:
                _logger.error("Non-stored field %s cannot be searched.", field)
                if _logger.isEnabledFor(logging.DEBUG):
                    _logger.debug(''.join(traceback.format_stack()))
                return TRUE_DOMAIN
            operator, value = self.operator, self.value
            if operator in ('in', 'not in') and len(value) == 1:
                # a lot of implementations expect '=' or '!=' operators
                operator = '=' if operator == 'in' else '!='
                value = next(iter(value))
            computed_domain = field.determine_domain(model, operator, value)
            # rewrite 'inselect' with 'any' which can be used internally
            # TODO remove 'inselect' usages
            computed_domain = list(computed_domain)
            for i, leaf in enumerate(computed_domain):
                if len(leaf) == 3 and leaf[1] in ('inselect', 'not inselect'):
                    # TODO warnings.warn("'inselect' operator is deprecated, use 'any' instead", DeprecationWarning)
                    operator = leaf[1].replace('inselect', 'any')
                    value = leaf[2]
                    if isinstance(value, (tuple, list)) and len(value) == 2:
                        value = SQL(value[0], *value[1])  # pylint: disable=sql-injection
                    computed_domain[i] = (leaf[0], operator, value)
            return D(computed_domain)._optimize(model)

        # optimizations with model
        leaf = self
        for opt in _LEAF_OPTIMIZATIONS_BY_OPERATOR[leaf.operator]:
            leaf = opt(leaf, model)
            if leaf is not self:
                return leaf._optimize(model)
        for opt in _LEAF_OPTIMIZATIONS_BY_FIELD_TYPE[field.type]:
            leaf = opt(leaf, model)
            if leaf is not self:
                return leaf._optimize(model)

        # run checks
        operator = self.operator
        if operator not in STANDARD_TERM_OPERATORS:
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

    def _build_sql(self, model: BaseModel, alias: str, query: Query) -> SQL:
        field, operator, value = self.field, self.operator, self.value
        if operator in ('in', 'not in') and isinstance(value, set) and len(value) == 1:
            # use "=" for backwards compatbility when building the condition
            operator = '=' if operator == 'in' else '!='
            value = next(iter(value))
        return model._condition_to_sql(alias, field, operator, value, query)


# --------------------------------------------------
# Optimizations
# --------------------------------------------------

_NARY_OPTIMIZATIONS = list()
_LEAF_OPTIMIZATIONS_BY_FIELD_TYPE = collections.defaultdict(list)
_LEAF_OPTIMIZATIONS_BY_OPERATOR = collections.defaultdict(list)


def register_nary_optimization():
    """Register an optimization for (cls, children, model)
    These are called when there are multiple children and the model is set.
    """
    def register(optimization):
        _NARY_OPTIMIZATIONS.append(optimization)
        return optimization
    return register


def _optimize_binary_sort_key(domain: Domain) -> tuple[str, str]:
    """Sorting key for conditions used for pair optimizations"""
    # group the same field and same operator together
    if isinstance(domain, DomainField):
        order = domain.operator
        order = NEGATIVE_TERM_OPERATORS.get(order, order)
        order_prefix = {
            'in': 0,
            'any': 1,
        }.get(order, 9)
        order = f"{order_prefix}{order}:{type(domain.value)}"
        return domain.field, order
    else:
        # '~' > any letter in python
        return '~', str(type(domain))


@register_nary_optimization()
def _optimize_binary_sort(cls, children, model):
    """Sort conditions in order to apply pair optimization"""
    return sorted(children, key=_optimize_binary_sort_key)


def register_binary_pair_optimization():
    """Apply optimization to adjacent children (the list is mutated).
    Expected function is (cls, model, a, b) -> Optional[Domain]
    Both children are replaced if result is not None
    """
    def register(optimization: Callable[[type, BaseModel, Domain, Domain], Domain | None]):
        def nary_optimization(cls: type, children: list[Domain], model: BaseModel):
            assert isinstance(children, list)
            if not children:
                raise cls.ZERO
            # after the children have been sorted by first optimization,
            # check if index-1 and index can be merged
            index = 1
            previous = children[0]
            while index < len(children):
                this = children[index]
                merged = optimization(cls, model, previous, this)
                if merged is not None:
                    previous = merged
                    children[index - 1 : index + 1] = [merged]
                else:
                    previous = this
                    index += 1
            return children
        return register_nary_optimization()(nary_optimization)
    return register


def register_leaf_optimization(operator):
    """Register an operator optimization for (leaf, model)"""
    assert operator, "Missing operator to register"
    if isinstance(operator, list):
        operators = operator
    else:
        operators = [operator]

    def register(optimization: Callable[[DomainField, BaseModel], Domain]):
        for operator in operators:
            _LEAF_OPTIMIZATIONS_BY_OPERATOR[operator].append(optimization)
        return optimization
    return register


def register_leaf_optimization_type(field_type):
    """Register a type optimization for (leaf, model)"""
    if isinstance(field_type, list):
        field_types = field_type
    else:
        field_types = [field_type]

    def register(optimization: Callable[[DomainField, BaseModel], Domain]):
        for field_type in field_types:
            _LEAF_OPTIMIZATIONS_BY_FIELD_TYPE[field_type].append(optimization)
        return optimization
    return register


@register_leaf_optimization(operator='=?')
def _operator_equal_if_value(leaf, _):
    """a =? b  <=>  not b or a = b"""
    if not leaf.value:
        return TRUE_DOMAIN
    return DomainField(leaf.field, 'in', {leaf.value})


@register_leaf_optimization(operator='<>')
def _operator_different(leaf, _):
    """a <> b  =>  a != b"""
    # already a rewrite-rule
    warnings.warn("Operator '<>' is deprecated, use '!=' directly", DeprecationWarning)
    return DomainField(leaf.field, '!=', leaf.value)


@register_leaf_optimization(operator='==')
def _operator_equals(leaf, _):
    """a == b  =>  a = b"""
    # rewrite-rule
    warnings.warn("Operator '==' is deprecated, use '=' directly", DeprecationWarning)
    return DomainField(leaf.field, '=', leaf.value)


@register_leaf_optimization(operator='=')
def _operator_equal_as_in(leaf, _):
    """a = b  <=>  a in [b]"""
    value = leaf.value
    if not isinstance(value, (list, tuple, set)) and not value:
        value = False
    return DomainField(leaf.field, 'in', {value})


@register_leaf_optimization(operator='!=')
def _operator_nequal_as_not_in(leaf, _):
    """a != b  <=>  a not in [b]"""
    value = leaf.value
    if not isinstance(value, (list, tuple, set)) and not value:
        value = False
    return DomainField(leaf.field, 'not in', {value})


@register_leaf_optimization(['any', 'not any'])
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


@register_leaf_optimization(['in', 'not in'])
def _optimize_in_set(leaf, _):
    """Make sure the value is a set()"""
    value = leaf.value
    # isinstance(value, Query) already handled during building
    if not value:
        # empty, return a boolean
        return D(leaf.operator == 'not in')
    if isinstance(value, set):
        return leaf
    if isinstance(value, (list, tuple)):
        return DomainField(leaf.field, leaf.operator, set(value))
    leaf._raise("Not a list of values, use the '=' or '!=' operator")


@register_leaf_optimization(['any', 'not any'])
def _optimize_any_domain(leaf, model):
    """Make sure the value is an optimized domain (or Query or SQL)"""
    value = leaf.value
    if isinstance(value, (Query, SQL)):
        return leaf
    # get the model to optimize with
    field = model._fields[leaf.field]
    comodel = model.env[field.comodel_name]
    domain = D(value)._optimize(comodel)
    # const if the domain is empty, the result is a constant
    # if the domain is True, we keep it as is
    if domain.const() is False:
        return D(leaf.operator == 'not any')
    # if unchanged, return the leaf
    if domain is value:
        return leaf
    return DomainField(leaf.field, leaf.operator, domain)


@register_leaf_optimization([op for op in TERM_OPERATORS if op.endswith('like')])
def _optimize_like_str(leaf, model):
    """Validate value for pattern matching, must be a str"""
    value = leaf.value
    if not value:
        if leaf.operator.startswith('='):
            return FALSE_DOMAIN
        # relational and non-relation fields behave differently
        result = leaf.operator not in NEGATIVE_TERM_OPERATORS
        if model._fields[leaf.field].relational:
            return DomainField._is_set(leaf.field, result)
        return D(result)
    if isinstance(value, (str, SQL)):
        # accept both str and SQL
        return leaf
    return DomainField(leaf.field, leaf.operator, str(value))


@register_leaf_optimization_type(['many2one', 'one2many', 'many2many'])
def _optimize_relational_name_search(leaf, model):
    """Execute _name_search by using _value_to_ids for relational values
    when we have str values."""
    operator = leaf.operator
    value = leaf.value
    if not (
        operator.endswith('like')
        or (
            operator in ('in', 'not in')
            and isinstance(value, set) and any(isinstance(v, str) for v in value)
        )
    ):
        return leaf
    # rel_field ilike "search"
    # rel_field in {"ok", "test"}
    field = model._fields[leaf.field]
    comodel = model.env[field.comodel_name]
    if field.type == 'many2one':
        # for many2one, search also the archived records
        comodel = comodel.with_context(active_test=False)
    if neg_operator := NEGATIVE_TERM_OPERATORS.get(operator):
        operator = neg_operator
        positive = False
    else:
        positive = True
    value = _value_to_ids(value, comodel, operator)
    if not isinstance(value, (Query, SQL, Domain)):
        # access rules are already checked by the name_search,
        # we can just return the values
        return DomainField(leaf.field, 'in' if positive else 'not in', set(value))
    return DomainField(leaf.field, 'any' if positive else 'not any', value)


@register_leaf_optimization_type('boolean')
def _optimize_in_boolean(leaf, model):
    """b in [True, False]  =>  True"""
    value = leaf.value
    if leaf.operator not in ('in', 'not in') or not isinstance(value, set):
        return leaf
    if not all(isinstance(v, bool) for v in value):
        if any(isinstance(v, str) for v in value):
            _logger.warning("Comparing boolean with a string in %s", leaf)
        value = {
            str2bool(v.lower(), False) if isinstance(v, str) else bool(v)
            for v in value
        }
    # tautology is simplified to a boolean
    if value == {False, True}:
        return D(leaf.operator == 'in')
    if value is leaf.value:
        return leaf
    return DomainField(leaf.field, leaf.operator, value)


def _value_to_date(value):
    # check datetime first, because it's a subclass of date
    if isinstance(value, SQL):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date) or value is False:
        return value
    if isinstance(value, str):
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
    if isinstance(value, (list, tuple, set)):
        return {_value_to_date(v) for v in value}
    raise ValueError('Failed to cast %r into a date' % value)


@register_leaf_optimization_type('date')
def _optimize_type_date(leaf, _):
    """Make sure we have a date type in the value"""
    if leaf.operator.endswith('like') or "." in leaf.field:
        return leaf
    value = _value_to_date(leaf.value)
    if value == leaf.value:
        return leaf
    return DomainField(leaf.field, leaf.operator, value)


def _value_to_datetime(value):
    if isinstance(value, SQL):
        return value, False
    if isinstance(value, datetime) or value is False:
        return value, False
    if isinstance(value, str):
        return datetime.fromisoformat(value), len(value) == 10
    if isinstance(value, date):
        return datetime.combine(value, time.min), True
    if isinstance(value, (list, tuple, set)):
        value, is_day = zip(*(_value_to_datetime(v) for v in value))
        return set(value), any(is_day)
    raise ValueError('Failed to cast %r into a datetime' % value)


@register_leaf_optimization_type('datetime')
def _optimize_type_datetime(leaf, _):
    """Make sure we have a datetime type in the value"""
    if leaf.operator.endswith('like') or "." in leaf.field:
        return leaf
    value, is_day = _value_to_datetime(leaf.value)
    if value == leaf.value:
        assert not is_day
        return leaf
    operator = leaf.operator
    if is_day and operator == '>':
        try:
            value += timedelta(1)
        except OverflowError:
            # higher than max, not possible
            return FALSE_DOMAIN
        operator = '>='
    elif is_day and operator == '<=':
        try:
            value += timedelta(1)
        except OverflowError:
            # lower than max, just check if field is set
            return DomainField._is_set(leaf.field, True)
        operator = '<'
    return DomainField(leaf.field, operator, value)


@register_leaf_optimization_type('binary')
def _optimize_type_binary_attachment(leaf, model):
    field = model._fields[leaf.field]
    operator = leaf.operator
    if field.attachment and not (operator in ('in', 'not in') and leaf.value == {False}):
        try:
            leaf._raise('Binary field stored in attachment, accepts only existence check; skipping domain')
        except ValueError:
            # log with stacktrace
            _logger.exception()
        return TRUE_DOMAIN
    if operator.endswith('like'):
        leaf._raise('Cannot use like operators with binary fields', error=NotImplementedError)
    return leaf


def _value_to_ids(value, comodel: BaseModel, operator_str='ilike') -> set[int] | Query | SQL | Domain:
    """For relational fields, transform a value into a set of ids, query or domain."""
    if isinstance(value, (Query, SQL, Domain)):
        return value
    if isinstance(value, set):
        # simple case: already a set of ids
        if all(isinstance(i, int) and i for i in value):
            return value
        # just a single value (probably a string)
        if len(value) == 1:
            value = next(iter(value))
    if isinstance(value, str):
        return _value_to_ids(comodel._name_search(value, [], operator=operator_str), comodel, operator_str)
    if isinstance(value, int) and value:
        return {value}
    if isinstance(value, (list, tuple, set)):
        if len(value) == 1:
            return _value_to_ids(next(iter(value)), comodel, operator_str)
        # get the ids for each value
        return {i for v in value for i in _value_to_ids(v, comodel, operator_str)}
    return set()


def _operator_child_of_domain(left, ids, comodel, parent=None):
    """ Return a domain implementing the child_of operator for [(left,child_of,ids)],
        either as a range using the parent_path tree lookup field
        (when available), or as an expanded [(left,in,child_ids)] """
    comodel = comodel.sudo().browse(ids)
    parent = parent or comodel._parent_name
    if comodel._parent_store and parent == comodel._parent_name:
        domain = DomainOr([
            DomainField('parent_path', '=like', rec.parent_path + '%')
            for rec in comodel
        ]).unwrap()
        if left != 'id':
            domain = DomainField(left, 'any', domain)
    else:
        # recursively retrieve all children nodes with sudo(); the
        # filtering of forbidden records is done by the rest of the
        # domain
        child_ids = set()
        while comodel:
            child_ids.update(comodel._ids)
            query = comodel._search(DomainField(parent, 'in', set(comodel.ids)))
            new_ids = set(query.get_result_ids()) - child_ids
            comodel = comodel.browse(new_ids)
        domain = DomainField(left, 'in', child_ids)
    return domain


def _operator_parent_of_domain(left, ids, comodel, parent=None):
    """ Return a domain implementing the parent_of operator for [(left,parent_of,ids)],
        either as a range using the parent_path tree lookup field
        (when available), or as an expanded [(left,in,parent_ids)] """
    comodel = comodel.sudo().browse(ids)
    parent = parent or comodel._parent_name
    if comodel._parent_store and parent == comodel._parent_name:
        parent_ids = {
            int(label)
            for rec in comodel
            for label in rec.parent_path.split('/')[:-1]
        }
        domain = DomainField(left, 'in', parent_ids)
    else:
        # recursively retrieve all parent nodes with sudo() to avoid
        # access rights errors; the filtering of forbidden records is
        # done by the rest of the domain
        parent_ids = set()
        while comodel:
            parent_ids.update(comodel._ids)
            comodel = comodel[parent].filtered(lambda p: p.id not in parent_ids)
        domain = DomainField(left, 'in', parent_ids)
    return domain


@register_leaf_optimization(['parent_of', 'child_of'])
def _operator_hierarchy(leaf, model):
    """Transform a hierarchy operator into an 'in' ids"""
    if leaf.operator == 'parent_of':
        hierarchy = _operator_parent_of_domain
    else:
        hierarchy = _operator_child_of_domain
    value = leaf.value
    if value is False:
        _logger.warning('Using %s with False value, the result will be empty', leaf.operator)
    field = model._fields[leaf.field]
    if leaf.field == 'id':
        comodel = model
    else:
        comodel = model.env[field.comodel_name]
    ids2 = _value_to_ids(value, comodel)
    if isinstance(ids2, Domain):
        ids2 = comodel._search(ids2).get_result_ids()
    if not ids2:
        return FALSE_DOMAIN
    if comodel._name == model._name:
        # same model, when set, use the field as the parent relation
        parent = None if leaf.field == 'id' else leaf.field
        result = hierarchy('id', ids2, model, parent)
    else:
        result = hierarchy(leaf.field, ids2, comodel)
    return result


@register_binary_pair_optimization()
def _optimize_same_leaves(cls, model, a, b):
    return a if a == b else None


@register_binary_pair_optimization()
def _optimize_merge_set_conditions(cls, model, a, b):
    """Merge 'in' conditions.
    Combine the 'in' and 'not in' conditions to a single set of values.
    For example:
    a in {1} or a in {2}  <=>  a in {1, 2}
    a in {1, 2} and a not in {2, 5}  =>  a in {2}
    """
    if not (
        a.field
        and a.field == b.field
        and {a.operator, b.operator} <= {'in', 'not in'}
        and isinstance(value_a := a.value, set)
        and isinstance(value_b := b.value, set)
        # cannot merge conditions for x2many fields
        and (field := model._fields.get(a.field))
        and not field.type.endswith('2many')
    ):
        return None
    z = cls.ZERO.const()
    # different operators, take the more restricting one
    if a.operator != b.operator:
        if (a.operator == 'in') != z:
            a, b = b, a
            value_a, value_b = value_b, value_a
        value = value_a - value_b
        if not value:
            return ~cls.ZERO
        return DomainField(a.field, a.operator, value)
    # same operator, intersect or union of values
    if (a.operator == 'in') == z:
        value = value_a & value_b
        if not value:
            return ~cls.ZERO
    else:
        value = value_a | value_b
    return DomainField(a.field, a.operator, value)


@register_binary_pair_optimization()
def _optimize_merge_many2one(cls, model, a, b):
    """Since we have optimized children, we can look at many2one fields
    and merge the 'any' conditions.
    This will lead to a smaller number of sub-queries which are equivalent.

    For example:

    a.f = 8 and a.g = 5  <=>  a any (f = 8 and g = 5)
    a.f = 1 or a not any g = 5 => a not any (not(f = 1) or g = 5)
    ...
    """
    if not (
        a.field
        and a.field == b.field
        and a.operator in ('any', 'not any')
        and a.operator == b.operator
        and isinstance(a.value, Domain)
        and isinstance(b.value, Domain)
        and (field := model._fields.get(a.field))
        and field.type == 'many2one'
        and (comodel := model.env.get(field.comodel_name))
    ):
        return None
    # transformation where (a, b) are conditions on a many2one:
    # any a and any b => any (a and b)
    # any a or any b => any (a or b)
    # not any a and not any b => not any (a or b)
    # not any a or not any b => not any (a and b)
    operator = a.operator
    change_cls = operator == 'not any'
    # inverse the condition when the operator changes while class does not
    av, bv = a.value, b.value
    value = cls([av, bv])
    if change_cls:
        value = ~value
    return DomainField(a.field, operator, value._optimize(comodel))


@register_binary_pair_optimization()
def _optimize_merge_x2many(cls, model, a, b):
    """Since we have optimized children, we can look at x2many fields
    and merge some of the 'any' conditions.
    This will lead to a smaller number of sub-queries which are equivalent.

    For example:

    a.f = 8 or a.g = 5  <=>  a any (f = 8 or g = 5)
    a not any f = 1 and a not any g = 5  <=>  a not any (f = 1 or g = 5)

    Note that the following cannot be optimized as multiple instances can
    satisfy conditions:

    a.f = 8 and a.g = 5
    a.f = 1 and a not any g = 5
    """
    if not (
        a.field
        and a.field == b.field
        and a.operator in {'any', 'not any'}
        and a.operator == b.operator
        and cls.ZERO.const() == (a.operator == 'not any')
        and isinstance(a.value, Domain)
        and isinstance(b.value, Domain)
        and (field := model._fields.get(a.field))
        and field.type.endswith('2many')
        and (comodel := model.env.get(field.comodel_name))
    ):
        return None
    operator = a.operator
    if operator == 'not any':
        cls = DomainAnd if cls == DomainOr else DomainOr
    value = cls([a.value, b.value])._optimize(comodel)
    return DomainField(a.field, operator, value)


# --------------------------------------------------
# Domain builder
# --------------------------------------------------


def _factory(domain=None, operator=None, value=None, /) -> Domain:
    """The factory for domains.

    :param domain: A Domain, or a list representation, or a bool, or str (field)
    :param operator: When set, the domain is a str and the value should be set
    :param value: The value for the operator
    """
    # if operator, build a leaf
    if operator is not None:
        if isinstance(domain, str):
            return DomainField.new(domain, operator, value)
        # special cases like True/False leaves
        # just match against known leaves
        if (domain, operator, value) == _FALSE_LEAF:
            return FALSE_DOMAIN
        if (domain, operator, value) == _TRUE_LEAF:
            return TRUE_DOMAIN
        raise TypeError(f"D() invalid arguments: {(domain, operator, value)!r}")
    # already a domain?
    if isinstance(domain, Domain):
        return domain
    # just a leaf-expression?
    if isinstance(domain, tuple) and len(domain) == 3 and isinstance(domain[1], str):
        return _factory(*domain)
    # a constant?
    if domain is True or domain == [] or domain is None:
        return TRUE_DOMAIN
    if domain is False:
        return FALSE_DOMAIN
    # parse the argument, it must be a list or a tuple
    if not isinstance(domain, (list, tuple)):
        raise TypeError(f"D() invalid argument type for domain: {domain!r}")
    stack: list[Domain] = []
    try:
        for d in reversed(domain):
            if isinstance(d, (tuple, list)) and len(d) == 3:
                stack.append(_factory(*d))
            elif d == DomainAnd.OPERATOR:
                stack.append(stack.pop() & stack.pop())
            elif d == DomainOr.OPERATOR:
                stack.append(stack.pop() | stack.pop())
            elif d == DomainNot.OPERATOR:
                stack.append(~stack.pop())
            else:
                raise ValueError(f"D() invalid item in domain: {d!r}")
        # keep the order and simplify already
        if len(stack) == 1:
            return stack[0]
        return DomainAnd.new(*reversed(stack))
    except IndexError:
        raise ValueError("D() malformed domain")


class _DomainFactory:
    AND = staticmethod(DomainAnd.new)
    OR = staticmethod(DomainOr.new)
    TRUE = TRUE_DOMAIN
    FALSE = FALSE_DOMAIN

    @overload
    def __call__(self, domain: str, operator: str, value, /) -> DomainField:
        """Create a leaf that compares a field with a value"""
        ...

    @overload
    def __call__(self, domain: bool, /) -> DomainConst:
        """Return TRUE or FALSE domain"""
        ...

    @overload
    def __call__(self, domain: list | tuple, /) -> Domain:
        ...

    @overload
    def __call__(self, domain: Domain, /) -> Domain:
        """Return the domain"""
        ...

    def __call__(self, domain=None, operator=None, value=None, /) -> Domain:
        """Domain builder

        The built domain is normalized, but not yet optimized.

        ```
        D([('a', '=', 5), ('b', '=', 8)])
        D('a', '=', 5) & ('b', '=', 8)
        D.AND(D('a', '=', 5), *other_conditions, D.TRUE)
        ```

        :param domain: A Domain, or a list representation, or a bool, or str (field)
        :param operator: When set, the domain is a str and the value should be set
        :param value: The value for the operator
        """
        return _factory(domain, operator, value)


D = _DomainFactory()
"""The domain builder instance"""
