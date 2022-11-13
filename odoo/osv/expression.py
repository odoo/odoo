# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Domain expression processing

The main duty of this module is to compile a domain expression into a
SQL query. A lot of things should be documented here, but as a first
step in the right direction, some tests in test_expression.py
might give you some additional information.

The domain represents an first-order logic expression.
Each term, is composed of a field name, operator and a value.
Most of fields contain values which you can test, for example,
('total', '>', '100'). Relations behave a little bit differently,
with the distinction between many2one field and the others.
The many2one field behaves as a value and you can enter a path to
test a particular value such as ('partner_id.name', 'ilike', 'test') meaning
match records that have a partner with a 'test' name.

    D('total', '>', 100) & D('partner_id.note', 'ilike', 'test')

For x2many fields, the default behaviour is to test the existence of a
record matching the proposition, however, in order to combine multiple
conditions on the same object or to test non-existence, quantifiers are
necessary.
They are exists ('any') and not exists ('none') to quantify related objects.
An alias forall ('all') is implemented as 'none (not domain)'.

    # exists tag which has a name like test
    D('tag_ids', 'any', D('name', 'like', 'test'))

    # all high-value orders are signed (all are low-value or signed)
    D('order_ids', 'all', D('total', '<', 1000) | D('state', '=', 'sale'))

Note that a path is translated into 'any' terms.
Optimizations are implemented to simplify conditions and group
predicates to send a smaller (and simpler) query to the database.
The same mechanism can be used to provide new operators as long as you
can transform them into a standard domain.

    D('a.b', '=', 1).optimize() == D('a', 'any', D('b', '=', 1))
    (~D('a', '=', False)).optimize() == D('a', '!=', False)

For legacy reasons, a domain can be represented as regular Python data
structures in reversed polish notation. At the first
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
operator can be used, and thus the right operand should be a list.

Note: the non-uniform syntax could have been more uniform, but this
would hide an important limitation of the domain syntax. Say that the
term representation was ['=', 'company_id.name', 'OpenERP']. Used in a
complete domain, this would look like::

    ['!', ['=', 'company_id.name', 'OpenERP']]

and you would be tempted to believe something like this would be
possible::

    ['!', ['=', 'company_id.name', ['&', ..., ...]]]

That is, a domain could be a valid operand. But this is not the
case. A domain is really limited to a two-level nature, and can not
take a recursive form: a domain is not a valid second-level operand.

Unaccent - Accent-insensitive search

OpenERP will use the SQL function 'unaccent' when available for the
'ilike' and 'not ilike' operators, and enabled in the configuration.
Normally the 'unaccent' function is obtained from `the PostgreSQL
'unaccent' contrib module
<http://developer.postgresql.org/pgdocs/postgres/unaccent.html>`_.

.. todo: The following explanation should be moved in some external
         installation guide

The steps to install the module might differ on specific PostgreSQL
versions.  We give here some instruction for PostgreSQL 9.x on a
Ubuntu system.

Ubuntu doesn't come yet with PostgreSQL 9.x, so an alternative package
source is used. We use Martin Pitt's PPA available at
`ppa:pitti/postgresql
<https://launchpad.net/~pitti/+archive/postgresql>`_.

.. code-block:: sh

    > sudo add-apt-repository ppa:pitti/postgresql
    > sudo apt-get update

Once the package list is up-to-date, you have to install PostgreSQL
9.0 and its contrib modules.

.. code-block:: sh

    > sudo apt-get install postgresql-9.0 postgresql-contrib-9.0

When you want to enable unaccent on some database:

.. code-block:: sh

    > psql9 <database> -f /usr/share/postgresql/9.0/contrib/unaccent.sql

Here :program:`psql9` is an alias for the newly installed PostgreSQL
9.0 tool, together with the correct port if necessary (for instance if
PostgreSQL 8.4 is running on 5432). (Other aliases can be used for
createdb and dropdb.)

.. code-block:: sh

    > alias psql9='/usr/lib/postgresql/9.0/bin/psql -p 5433'

You can check unaccent is working:

.. code-block:: sh

    > psql9 <database> -c"select unaccent('hélène')"

Finally, to instruct OpenERP to really use the unaccent function, you have to
start the server specifying the ``--unaccent`` flag.

"""
import collections
import fnmatch
import logging
import operator as pyop
import traceback
import unicodedata
import warnings
from abc import ABC, abstractmethod
from datetime import date, datetime, time, timedelta
from typing import Iterable

from psycopg2.sql import SQL, Composable

import odoo
from odoo.tools import Query, sql

# Domain operators.
NOT_OPERATOR = '!'
OR_OPERATOR = '|'
AND_OPERATOR = '&'
DOMAIN_OPERATORS = {NOT_OPERATOR, OR_OPERATOR, AND_OPERATOR}

# List of available term operators.
TERM_OPERATORS = set()
# A subset of the above operators, with a 'negative' semantic. When the
# expressions 'in NEGATIVE_TERM_OPERATORS' or 'not in NEGATIVE_TERM_OPERATORS' are used in the code
# below, this doesn't necessarily mean that any of those NEGATIVE_TERM_OPERATORS is
# legal in the processed term.
NEGATIVE_TERM_OPERATORS = set()
# Negation of domain expressions
TERM_OPERATORS_NEGATION = dict()


def _add_term_operator(operator, negation=None, negative_negation=True):
    """Add a new operator"""
    if not isinstance(operator, str) or not operator:
        raise ValueError('Term operator is invalid: %r' % operator)
    TERM_OPERATORS.add(operator)
    if isinstance(negation, str):
        TERM_OPERATORS.add(negation)
        TERM_OPERATORS_NEGATION[operator] = negation
        TERM_OPERATORS_NEGATION[negation] = operator
        if negative_negation:
            NEGATIVE_TERM_OPERATORS.add(negation)


# OPERATORS
# 'in' encodes equality test against a list of values.
# The result is True if one of the values matches.
# Note that a null value is encoded as False.
_add_term_operator('in', 'not in')
# Inequalities
# Note that the negations are not entirely correct;
# we transform (not (a <= b)) into (a > b)
# XXX but it should be (a > b or a is null)
_add_term_operator('<=', '>', False)
_add_term_operator('>=', '<', False)
# String comparison against a str
# 'i' for case-insensitive (and accent-insensitive)
# '=' for not wrapping arround any prefix or suffix match
_add_term_operator('like', 'not like')
_add_term_operator('ilike', 'not ilike')
_add_term_operator('=like')
_add_term_operator('=ilike')
# inselect operator for backwards compatibility, but, it's deprecated
# because it should never have been exposed and is no longer used internally
# value is tuple(sql, values)
# XXX 'inselect' operator should be removed
_add_term_operator('inselect', 'not inselect')
# Quantifiers work for relational fields only, the value is a Domain or Query.
# The result is True when one of the related objects matches the domain.
_add_term_operator('any', 'none')  # all is added later

# List of standard term operators used during query generation.
# All terms added later are optimized and translated into the following terms,
# only these will be used to generate the SQL expressions.
# Note that even '=' is encoded as a 'in'.
STANDARD_TERM_OPERATORS = TERM_OPERATORS.copy()


# This is the way the True and False leaves are encoded in the polish notation.
TRUE_LEAF = (1, '=', 1)
FALSE_LEAF = (0, '=', 1)

_logger = logging.getLogger(__name__)


# --------------------------------------------------
# Domain definition and manipulation
# --------------------------------------------------

class Domain(ABC):
    """Representation of a domain as an object, allow for nomalization and
    comination.

    Don't use the domain classes directly, always use D().
    """
    field = None  # ease checks whether the domain is concerning a field

    def __and__(self, other):
        """D & D"""
        return DomainAnd([self, D(other)])

    def __or__(self, other):
        """D | D"""
        return DomainOr([self, D(other)])

    def __invert__(self):
        """~D"""
        return DomainNot(self)

    def optimize_not(self, model=None):
        """Shortcut for (~D).optimize(model)"""
        return (~self).optimize(model)

    def __add__(self, other):
        """D + [...]

        For backward-compatibility of domain composition.
        Concatenate as lists.
        If we have two domains, equivalent to '&'.
        """
        if isinstance(other, Domain):
            return self & other
        if not isinstance(other, list):
            raise ValueError('Can concatenate only lists')
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
        empty domain is True, an empty domain is TRUE_DOMAIN"""
        return TRUE_DOMAIN != self

    @abstractmethod
    def __eq__(self, other):
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
        return str(list(self))

    def const(self):
        """Constant value or None"""
        return None

    def optimize(self, model=None):
        """Perform optimizations of the node given a model to resolve the fields

        The model can be optionally given to validate fields against it and to
        perform additional type-dependent optimizations.
        A context variable `optimize_execute` can be set on the model to disable
        optimizations that depend on querying the database or using Query objects
        which reference the database cursor.
        """
        return self

    def _execution_mode(self, model):
        """Check the `optimize_execute` context on the model"""
        return bool(model is not None and model.env.context.get('optimize_execute'))

    @abstractmethod
    def _build_query(self, builder) -> None:
        """Build the where_clause and the where_params (must be optimized with field)"""
        raise NotImplementedError

    @abstractmethod
    def filtered_model(self, model, ids: set) -> set:
        """Implementation for filtered domain (must be optimized)"""
        raise NotImplementedError

    def transform_domain(self, function, model=None):
        """Run a function to map to all the nodes and return the result

        :param function: (Domain, model) -> Optional(Domain)
        """
        result = function(self, model)
        return result if result is not None else self

    def collect_domain(self, function, model=None):
        """Visit each node an map a function to it

        :param function: (Domain, model) -> Any
        """
        result = []
        def visit(node, model):
            result.append(function(node, model))
        self.transform_domain(visit, model)
        return result


class DomainConst(Domain, BaseException, ABC):
    """Constant domain: True/False"""
    def __eq__(self, other):
        return isinstance(other, type(self))

    def const(self):
        return self.value


class DomainTrue(DomainConst):
    """Domain: True"""
    value = True

    def __and__(self, other):
        return D(other)

    def __or__(self, other):
        return self

    def __invert__(self):
        return FALSE_DOMAIN

    def __iter__(self):
        yield TRUE_LEAF

    def _build_query(self, builder):
        builder.build_clause.append('TRUE')

    def filtered_model(self, model, ids):
        return ids


class DomainFalse(DomainConst):
    """Domain: False"""
    value = False

    def __and__(self, other):
        return self

    def __or__(self, other):
        return D(other)

    def __invert__(self):
        return TRUE_DOMAIN

    def __iter__(self):
        yield FALSE_LEAF

    def _build_query(self, builder):
        builder.build_clause.append('FALSE')

    def filtered_model(self, model, ids):
        return set()


TRUE_DOMAIN = DomainTrue()
FALSE_DOMAIN = DomainFalse()


class DomainNot(Domain):
    """Negation domain, contains a single child"""
    operator = NOT_OPERATOR

    def __init__(self, child: Domain):
        self.child = child

    def __invert__(self):
        return self.child

    def __iter__(self):
        yield NOT_OPERATOR
        yield from self.child

    def optimize(self, model=None):
        """Optimization step.

        Push down the operator as much as possible.
        """
        child = self.child
        # not not
        if isinstance(child, DomainNot):
            return child.child.optimize(model)
        # and/or push down
        # not (a or b)  <=>  (not a and not b)
        # not (a and b)  <=>  (not a or not b)
        if isinstance(child, DomainBinary):
            return child.optimize_not(model)
        # first optimize the child
        # check constant and operator negation
        child = child.optimize(model)
        if isinstance(child, DomainConst):
            return ~child
        if isinstance(child, DomainLeaf):
            neg_op = TERM_OPERATORS_NEGATION.get(child.operator)
            if neg_op:
                return DomainLeaf(child.field, neg_op, child.value)
        if child is self.child:
            return self
        return DomainNot(child)

    def __eq__(self, other):
        if not isinstance(other, DomainNot):
            return False
        return self.child == other.child

    def _build_query(self, builder):
        builder.build_clause.append('NOT (')
        self.child._build_query(builder)
        builder.build_clause.append(')')

    def filtered_model(self, model, ids):
        return ids - self.child.filtered_model(model, ids)

    def transform_domain(self, function, model=None):
        child = self.child.transform_domain(function, model)
        if child is not self.child:
            return super(DomainNot, DomainNot(child)).transform_domain(function, model)
        return super().transform_domain(function, model)


class DomainBinary(Domain, ABC):
    """Domain for a binary operator: AND or OR with multiple children"""
    operator: str = ''
    operator_sql: str = ' ??? '
    zero: DomainConst = FALSE_DOMAIN  # default for lint checks

    def __init__(self, children: Iterable[Domain], optimal=(False, '')):
        """Create the domain with conditions

        During initialization, do a quick children optimization to
        flatten the list and remove constants.

        To speed up optimize() calls, we keep self._optimal for binary operators
        which is a tuple(int, str):
        (0, '') (unoptimized), (1, '') (optimized without model)
        (1, 'name') (optimized), (2, 'name') (optimized and executed parts)
        """
        try:
            if optimal != (False, '') and isinstance(children, list):
                self.children = children
            else:
                self.children = list(self._optimize_children(children))
        except DomainConst as c:
            self.children = [c]
        self._optimal = optimal

    @abstractmethod
    def __invert__(self):
        raise NotImplementedError

    def __iter__(self):
        if not self.children:
            yield from self.zero
            return
        yield from [self.operator] * (len(self.children) - 1)
        for c in self.children:
            yield from c

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.optimize().children == other.optimize().children

    def optimize(self, model=None):
        """Optimization step.

        If the return type is a binary domain, there are multiple children.

        Optimize all children with the given model.
        Run the registered optimizations, if all children are optimal, stop.
        """
        if model is None:
            optimal_result = (1, '')
        else:
            optimal_result = (2 if self._execution_mode(model) else 1, model._name)
            if self._optimal[1] and self._optimal[1] != optimal_result[1]:
                _logger.warning(
                    "Optimizing with different models %s and %s",
                    self._optimal[1], optimal_result[1],
                )
        if optimal_result <= self._optimal:
            # already optimized
            return self
        # optimize children
        children = self.children
        optimal_child = set()
        try:
            children = list(self._optimize_children(c.optimize(model) for c in children))
            while True:
                if len(children) < 2 or model is None:
                    break
                cla = type(self)
                optimal_child.update(id(c) for c in children)
                for opt in _BINARY_OPTIMIZATIONS:
                    children = opt(cla, children, model)
                optimized = True
                for i, c in enumerate(children):
                    # children are not hashable, check identity instead
                    if id(c) in optimal_child:
                        continue
                    children[i] = c.optimize(model)
                    optimized = False
                if optimized:
                    break
                children = list(self._optimize_children(children))
        except DomainConst as c:
            return c
        # return the result
        len_children = len(children)
        if len_children == 0:
            return self.zero
        if len_children == 1:
            return children[0]
        return type(self)(children, optimal_result)

    @classmethod
    def _optimize_children(cls, children):
        """Yield all children (flattened).

        If we have the same type, just copy the children.
        If we have a constant: if it's the zero, ignore it;
        otherwise raise ~zero.
        """
        for c in children:
            if isinstance(c, cls):
                yield from c.children
            elif isinstance(c, DomainConst):
                if c.const() == cls.zero.const():
                    continue
                raise ~cls.zero
            else:
                yield c

    def _build_query(self, builder):
        assert self.children, "No children, optimize() probably not executed"
        clause = builder.build_clause
        clause.append('(')
        it_children = iter(self.children)
        next(it_children)._build_query(builder)
        for c in it_children:
            clause.append(self.operator_sql)
            c._build_query(builder)
        clause.append(')')

    def transform_domain(self, function, model=None):
        new_children = []
        changed_child = False
        for c in self.children:
            nc = c.transform_domain(function, model)
            if nc is None or nc is c:
                new_children.append(c)
            else:
                new_children.append(nc)
                changed_child = True
        if changed_child:
            return super(DomainBinary, type(self)(new_children)).transform_domain(function, model)
        return super().transform_domain(function, model)


class DomainAnd(DomainBinary):
    """Domain: AND with multiple children"""
    operator = AND_OPERATOR
    operator_sql = " AND "
    zero = TRUE_DOMAIN

    def __invert__(self):
        return DomainOr(~c for c in self.children)

    def filtered_model(self, model, ids):
        if not self.children:
            return self.zero.filtered_model(model, ids)
        ids = set(ids)
        for c in self.children:
            if not ids:
                break
            ids &= c.filtered_model(model, ids)
        return ids


class DomainOr(DomainBinary):
    """Domain: OR with multiple children"""
    operator = OR_OPERATOR
    operator_sql = " OR "
    zero = FALSE_DOMAIN

    def __invert__(self):
        return DomainAnd(~c for c in self.children)

    def filtered_model(self, model, ids):
        if not self.children:
            return self.zero.filtered_model(model, ids)
        remaining = set(ids)
        ids = set()
        for c in self.children:
            cids = c.filtered_model(model, remaining)
            if cids:
                ids |= cids
                remaining -= cids
                if not remaining:
                    break
        return ids


class DomainLeaf(Domain):
    """Leaf domain: field operator value"""

    def __init__(self, field: str, operator: str, value):
        """Init a new leaf (internal init)

        :param field: Field name or field path
        :param operator: A valid operator
        :param value: A value for the comparison
        """
        self.field = field
        self.operator = operator
        self.value = value

    @staticmethod
    def _validate_arguments(left, operator, right):
        """Validate the inputs for the __init__

        :param left: Is a non empty string
        :param operator: Lower-case
        :param right: The value, replaced tuple by list and None by False
        """
        if not isinstance(left, str) or not left:
            raise ValueError('Empty field name in leaf domain')
        if right is None:
            right = False
        rep = (left, operator, right)
        # Rewrites done here to have already a more normalized domain (quick optimizations)
        # Check if the operator is valid
        operator = operator.lower()
        if operator != rep[1]:
            _logger.warning("The domain term %s should have a lower-case operator.", str(rep))
        if operator == '<>':
            # '<>' is an alias for '!='
            operator = '!='
        if operator not in TERM_OPERATORS:
            raise ValueError('Invalid operator in %s' % str(rep))
        # rewrite already most used operators
        # * Query value should be using a relational operator
        # * change '=' into 'in'
        # (x, '=', a) becomes (x, 'in', [a])
        # * change 'in' value
        if isinstance(right, Query):
            if operator not in ('any', 'none', 'in', 'not in'): # XXX show warning (for "in")
                _logger.warning("The domain term %s should use the 'any' or 'none' operator.", str(rep))
            operator = 'none' if operator in NEGATIVE_TERM_OPERATORS else 'any'
        elif operator in ('=', '!='):
            operator = 'in' if operator == '=' else 'not in'
            if isinstance(right, (list, tuple, set)):
                if not right:  # views sometimes use ('user_ids', '!=', []) to indicate the user is set
                    # XXX _logger.warning("The domain term %s should compare with False.", str(rep))
                    right = {False}
                else:
                    _logger.warning("The domain term %s should use the 'in' or 'not in' operator.", str(rep))
                    right = set(right)
            else:
                right = {right}
        elif operator in ('in', 'not in') and not isinstance(right, (list, tuple, set)):
            if left not in {'groups_id', 'user_ids'}:  # XXX show warning, but ('groups_id', 'in', ref(...).id) lot of occurrences
                _logger.warning("The domain term %s should have a list value.", str(rep))
            right = {right}
        return left, operator, right

    @staticmethod
    def _is_set(field, is_set):
        """Build a condition whether 'field is set'"""
        return DomainLeaf(field, 'not in' if is_set else 'in', {False})

    def __iter__(self):
        field, operator, value = self.field, self.operator, self.value
        # display a any [b = x] as a.b = x
        if operator == 'any' and isinstance(value, DomainLeaf):
            field_b, operator, value = next(iter(value))
            yield (f"{field}.{field_b}", operator, value)
            return
        # display a in [b] as a = b
        if operator in ('in', 'not in') and isinstance(value, set) and len(value) == 1:
            operator = '=' if operator == 'in' else '!='
            value = next(iter(value))
        # if the value is a domain or set, change it into a list too
        if isinstance(value, (set, Domain)):
            value = list(value)
        yield (field, operator, value)

    def __eq__(self, other):
        return (
            isinstance(other, DomainLeaf)
            and self.field == other.field
            and self.operator == other.operator
            and self.value == other.value
        )

    def transform_domain(self, function, model=None, optimize_value=True):
        if '.' in self.field:
            return self.optimize().transform_domain(function, model)
        if model is not None and optimize_value and isinstance(self.value, Domain):
            field = model._fields.get(self.field)
            comodel = model.env.get(getattr(field, 'comodel_name', None))
            new_value = self.value.transform_domain(function, comodel)
            if new_value is not self.value:
                return DomainLeaf(self.field, self.operator, new_value).transform_domain(function, model, False)
        return super().transform_domain(function, model)

    def _raise(self, message, *args, error=ValueError):
        """Raise an error message for this leaf"""
        message += ' in leaf (%r, %r, %r)'
        raise error(message % (*args, self.field, self.operator, self.value))

    def __optimize_path(self, path):
        """Transform path into a tree.

        ('a.b', op, v)  =>  ('a', 'any', [('b', op, v)])
        """
        leaf = DomainLeaf(path[-1], self.operator, self.value)
        for name in reversed(path[:-1]):
            leaf = DomainLeaf(name, 'any', leaf)
        return leaf

    def __optimize_leaf(self, model, field):
        """Run leaf optimizations until the type changes or the leaf is optimal."""
        leaf = self
        for opt in _LEAF_OPTIMIZATIONS_BY_OPERATOR[self.operator]:
            leaf = opt(leaf, model)
            if leaf is not self:
                return leaf.optimize(model)
        if model is None:
            return leaf
        for opt in _LEAF_OPTIMIZATIONS_BY_FIELD_TYPE[field.type]:
            leaf = opt(leaf, model)
            if leaf is not self:
                return leaf.optimize(model)
        return leaf

    def optimize(self, model=None):
        """Optimization step.

        With a model, dispatch optimizations according the the operator and
        the type of the field.

        - Decompose *paths* into domains using 'any'.
        - If we have a model, find the field.
        - If the field is *not stored*, run the search function of the field
        - Run generic optimizations.
        - Check the output.
        """
        # optimize path
        if '.' in self.field:
            return self.__optimize_path(self.field.split('.')).optimize(model)

        # generic optimizations if no model selected
        if model is None:
            return self.__optimize_leaf(None, None)

        # get the field (inherited)
        try:
            original_model = model
            field = model._fields[self.field]
            while field and field.inherited:
                model = model.env[field.related_field.model_name]
                field = model._fields[self.field]
        except (IndexError, KeyError):
            self._raise("Invalid field %s.%s", model._name, self.field)

        # handle non-stored fields (replace by queryable/stored items)
        if not field.store:
            if not self._execution_mode(model):
                # just optimize without model during no-execution mode
                return self.optimize()
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
            domain = field.determine_domain(model, operator, value)
            return D(domain).optimize(original_model)

        # optimizations with model
        leaf = self.__optimize_leaf(model, field)
        if leaf is not self:
            return leaf

        if not self._execution_mode(model):
            # skip checks, need to optimize further to get to standard operators
            return self

        # result checks
        operator = self.operator
        if operator not in STANDARD_TERM_OPERATORS:
            self._raise("Not standard operator left")

        # Odoo internals use ('id', 'in', Query), accept it
        if not field.relational and operator in ('any', 'none') and self.field != 'id':
            self._raise("Cannot use any/none with non-relation fields")

        return self

    def _build_query(self, builder):
        field, builder = builder.get_field(self.field)
        assert field, "Optimization should have validated available fields %r" % self
        if not field.store:
            _logger.error("Optimization of domain not executed for query building in %r, %s", self, builder.model._name)
        assert field.store, "Optimization should have kept only stored fields %r" % self

        operator = self.operator
        assert operator in STANDARD_TERM_OPERATORS, \
            "Optimization should have removed the operator %s" % operator
        if neg := (operator in NEGATIVE_TERM_OPERATORS):
            operator = TERM_OPERATORS_NEGATION[operator]

        # Operators: 'any' (subselect), 'in' (equality), inequality, 'like'
        # 'inselect' old internal operator

        value = self.value
        if operator == 'inselect':
            _logger.warning("The operator inselect was an internal implementation.")
            subquery, subparams = self.value
            sql_operator = " NOT IN " if neg else " IN "
            field_alias = builder.quote('id')
            builder.build_clause += [field_alias, sql_operator, '(', subquery, ')']
            builder.build_params += subparams
            return
        if field.name == 'id' and operator == 'any':
            # special-case for queries ('id', 'any', Query)
            # treat id as a many2one in that case
            assert isinstance(value, Query)
            subquery, subparams = value.subselect()
            sql_operator = " NOT IN " if neg else " IN "
            field_alias = builder.quote('id')
            builder.build_clause += [field_alias, sql_operator, '(', subquery, ')']
            builder.build_params += subparams
            return

        if field.relational:
            if operator == 'any':
                return self._build_query_relational(builder, field, neg)
            elif field.type != 'many2one':
                self._raise("Unsupported operator %s for %s", operator, field.type)
        elif operator == 'any':
            self._raise("Unsupported operator any for %s", field.type)

        return self._build_query_scalar(builder, field, operator, neg)

    def _build_query_relational(self, builder, field, neg):
        model = builder.model
        clause = builder.build_clause
        params = builder.build_params

        if field.type == 'many2one':
            comodel = model.env[field.comodel_name]
            if isinstance(self.value, Query):
                value_query = self.value
                domain = None
            elif isinstance(self.value, Domain):
                value_query = None
                domain = self.value
                # handle directly checks on the 'id' field
                # this does not check access permissions
                if domain.const() is True:
                    # ID check: since we have foreign keys, just null check
                    clause += [builder.quote(self.field), " IS NULL" if neg else " IS NOT NULL"]
                    return
                elif (
                    isinstance(domain, DomainLeaf)
                    and domain.field == 'id'
                    and domain.operator not in ('any', 'none')
                ):
                    # ID check: build the query with the operator applied directly on the field
                    domain = DomainLeaf(self.field, domain.operator, domain.value)
                    # inverse the not exists and check null condition
                    if neg:
                        domain = ~domain
                        if not field.required:
                            domain |= DomainLeaf._is_set(self.field, False)
                        domain = domain.optimize()
                    elif not field.required and domain.operator in NEGATIVE_TERM_OPERATORS:
                        if domain.operator == 'not in':
                            domain.value = domain.value | {False}
                        else:
                            domain &= DomainLeaf._is_set(self.field, True)
                    domain._build_query(builder)
                    return
            else:
                self._raise("Invalid value type for 'any'/'none' query")
            # 'any' can be translated into a LEFT JOIN
            # unless we have a value_query, then use the general code
            if field.auto_join and value_query is None:
                # left join table on field = t.id where expr
                # res_partner.state_id = res_partner__state_id.id
                coalias = builder.query.left_join(
                    builder.alias, self.field, comodel._table, 'id', self.field,
                )
                if domain.const() is True:
                    clause += [builder.quote('id', coalias), " IS NOT NULL"]
                else:
                    if neg:
                        domain = domain.optimize_not()
                        clause += ['(', builder.quote('id', coalias), " IS NULL OR "]
                    domain._build_query(_SQLBuildHelper(comodel, coalias, builder))
                    if neg:
                        clause.append(')')
                return
            # in a many2one, it will often be faster to check existence
            sql_operator = " IN "
            if neg:
                if value_query is None:
                    domain = domain.optimize_not()
                else:
                    sql_operator = " NOT IN "
            # 'any' can be translated as IN
            # field in (select id from comodel where expr)
            if value_query is not None:
                assert domain is None
                query = value_query
            else:
                query = comodel._where_expression_calc(
                    domain, active_test=False, flush_fields=["id"]).query
            subquery, subparams = query.subselect()
            if neg:
                clause.append('(')
            field_alias = builder.quote(self.field)
            clause += [field_alias, sql_operator, '(', subquery, ')']
            params += subparams
            if neg:
                if not field.required:
                    clause += [" OR ", field_alias, " IS NULL"]
                clause.append(')')

        elif field.type == 'one2many':
            comodel = model.env[field.comodel_name].with_context(**field.context).with_context(optimize_execute=True)
            assert field.inverse_name, "one2many must have an inverse name"
            domain = D(field.get_domain_list(model))
            value_query = None
            if isinstance(self.value, Query):
                value_query = self.value
            else:
                domain &= self.value
            domain = domain.optimize()  # for const check
            # build the query by adding the domain
            if field.auto_join:
                # bypass access rules
                query = expression(domain, comodel).query
            else:
                query = comodel._where_expression_calc(domain, flush_fields=["id"]).query
            # make sure the field is in the query
            cobuilder = _SQLBuildHelper(comodel, next(iter(query._tables)), builder)
            cobuilder.query = query
            inverse_field, cobuilder = cobuilder.get_field(field.inverse_name)
            inverse_column = cobuilder.quote(field.inverse_name)
            # (!) value_query may be cached, so don't change it
            if value_query is not None:
                if not query.where_clause and not query._joins and cobuilder.alias in value_query._tables:
                    query = value_query
                else:
                    subquery, subparams = value_query.subselect()
                    query.add_where(cobuilder.quote('id') + ' IN (' + subquery + ')', subparams)
            if neg:
                # not exists (select 1 from query q where q.inverse is not null and q.inverse = parent.id)
                subquery, subparams = query.subselect(inverse_column + " AS id")
                clause += [
                    "NOT EXISTS (SELECT 1 FROM (",
                    subquery,
                    ") sub WHERE sub.id IS NOT NULL and sub.id = ",
                    builder.quote('id'),
                    ")",
                ]
            else:
                # in (query where inverse is not null)
                subquery, subparams = query.subselect(inverse_column)
                clause += [builder.quote('id'), " IN (", subquery]
                if not inverse_field.required:
                    clause += [" AND ", inverse_column, " IS NOT NULL"]
                clause.append(")")
            params += subparams

        elif getattr(field, 'auto_join', None) and field.type not in ('many2one', 'one2many'):
            self._raise("auto_join attribute not supported", error=NotImplementedError)

        elif field.type == 'many2many':
            rel_table, rel_id1, rel_id2 = field.relation, field.column1, field.column2
            comodel = model.env[field.comodel_name].with_context(**field.context).with_context(optimize_execute=True)
            query = Query(model.env.cr, rel_table, rel_table)
            domain = D(field.get_domain_list(model))
            value_query = None
            if isinstance(self.value, Query):
                value_query = self.value
            else:
                domain &= self.value
            domain = domain.optimize()  # for const check
            # add the constraint to the query
            if value_query is not None:
                coquery = value_query
                expression(domain, comodel, query=coquery)
            elif domain.const() is not True:
                coquery = comodel._where_expression_calc(
                    domain, active_test=False, flush_fields=["id"]).query
                if comodel.env.su and isinstance(domain, DomainLeaf) and domain.field == 'id' and len(coquery.where_clause) == 1:
                    # ID check: apply the operator directly on rel_id2
                    where = coquery.where_clause[0]
                    where = where.replace(builder.quote("id", comodel._table), builder.quote(rel_id2, rel_table))
                    query.add_where(where, coquery.where_clause_params)
                    coquery = None
            else:
                coquery = None
            if coquery is not None and coquery.where_clause:
                subquery, subparams = coquery.subselect()
                query.add_where(
                    builder.quote(rel_id2, rel_table)
                    + ' IN (' + subquery + ')',
                    subparams,
                )
            # make an EXIST query, with the bridge table
            query.add_where(
                builder.quote(rel_id1, rel_table)
                + ' = ' + builder.quote('id'))
            subquery, subparams = query.subselect("1")
            if neg:
                clause.append('NOT ')
            clause += ['EXISTS (', subquery, ')']
            params += subparams

    def _build_query_scalar(self, builder, field, operator, neg):
        field_alias = builder.quote(self.field)
        value = self.value

        model = builder.model
        clause = builder.build_clause
        params = builder.build_params

        # ---------------------------------------------------------------------
        # Type-specialized generation

        if field.type == 'boolean':
            assert operator == 'in' and len(value) == 1, \
                "boolean only supports comparison with 1 constant (True or False)"
            if bool(value == {True}) != neg:
                clause += [field_alias]
            else:
                clause += ["(", field_alias, " IS NULL OR ", field_alias, " = false)"]
            return
        if field.type == 'binary' and field.attachment:
            # only existence check is possible for attachments
            assert operator == 'in' and value == {False}, \
                "binary attachment field, can only check the existence"
            # build a simple subquery
            subselect = "SELECT res_id FROM ir_attachment WHERE res_model=%s AND res_field=%s"
            sql_operator = " IN " if not neg else " NOT IN "
            clause += [builder.quote('id'), sql_operator, "(", subselect, ")"]
            params += [model._name, self.field]
            return

        # values used to build (left sql_operator right)
        sql_left = field_alias
        to_column = lambda v: field.convert_to_column(v, model, validate=False)
        clause.append('(')

        # ---------------------------------------------------------------------
        # Translated fields

        if field.translate and value and (
            # we have at least one string
            isinstance(value, str)
            or (isinstance(value, set) and any(isinstance(v, str) for v in value))
        ):
            lang = model.env.lang or 'en_US'
            to_column = lambda v: field.convert_to_column(v, model, validate=False).adapted[lang]
            if (
                not neg
                and builder._has_trigram
                and field.index == 'trigram'
            ):
                # speed up searching using a trigram index index (only for =, like, ilike)
                if operator == 'in' and len(value) == 1:
                    single_value = next((v for v in value if v), None)
                else:
                    single_value = None
                if single_value:  # check for only one value
                    pattern_value = sql.value_to_translated_trigram_pattern(single_value)
                    pattern_operator = 'like'
                elif operator.endswith('like'):
                    assert isinstance(value, str), 'Like only matches str'
                    pattern_value = sql.pattern_to_translated_trigram_pattern(value)
                    pattern_operator = operator.lstrip('=')
                else:
                    pattern_value = '%'
                if pattern_value != '%':
                    unaccent = builder._unaccent(field)
                    clause += [
                        unaccent(f"jsonb_path_query_array({field_alias}, '$.*')::text"),
                        ' ', pattern_operator, ' ', unaccent("%s"), " AND "
                    ]
                    params.append(pattern_value)

            if lang == 'en_US':
                sql_left = f"{field_alias}->>'en_US'"
            else:
                sql_left = f"COALESCE({field_alias}->>'{lang}', {field_alias}->>'en_US')"
            # let the operators work with the adapted values

        # ---------------------------------------------------------------------

        # string matching
        if operator.endswith('like'):
            assert field.type != 'binary', "Cannot use like with binary fields"
            need_wildcard = not operator.startswith('=')
            sql_operator = self.operator.lstrip('=').upper()
            unaccent = builder._unaccent(field)
            value = value or ''
            null_check = neg if value else need_wildcard

            clause += [unaccent(sql_left + '::text'), ' ', sql_operator, ' ', unaccent("%s")]
            used_value = str(value)
            if need_wildcard:
                used_value = f"%{used_value}%"
            params += [used_value]
        # equalities
        elif operator == 'in':
            # a null check is handled separately if False is in value
            # the remaining values are checked here
            assert isinstance(value, set) and value, "Invalid value for 'in', must be a set: %r" % value
            if null_check := (False in value):
                # should keep/add the value 0 for comparisons
                value_count = len(value)
                value = {v for v in value if v is not False}
                if value_count != len(value) and field.type in ('integer', 'float', 'monetary'):
                    value.add(0)
            clause.append(sql_left)
            if len(value) == 0:
                null_check = neg  # skip adding constraint later
                if neg:
                    clause.append(" IS NOT NULL")
                else:
                    clause.append(" IS NULL")
            elif len(value) == 1:
                clause.append(' <> %s' if neg else ' = %s')
                params += [to_column(v) for v in value]
            else:
                if neg:
                    clause.append(' NOT')
                clause.append(' IN %s')
                params += [tuple(to_column(v) for v in value)]
            # null check handling
            if null_check != neg:
                clause += [" OR ", field_alias, " IS NULL"]
            null_check = False
        # inequalities and simple operators
        else:
            null_check = value and neg
            sql_operator = self.operator
            clause += [sql_left, ' ', sql_operator, ' %s']
            params.append(to_column(value))
        # null check and end
        if null_check:
            if neg:
                clause += [" OR ", field_alias, " IS NULL"]
            else:
                clause += [" AND ", field_alias, " IS NOT NULL"]
        clause.append(')')

    def filtered_model(self, model, ids):
        """Filter id set of a model

        The domain must be optimized before calling this function.
        """
        # not optimized enough, call model optimizations now
        if self.operator not in STANDARD_TERM_OPERATORS:
            model = model.with_context(optimize_execute=True, active_test=False)
            return self.optimize(model).filtered_model(model, ids)

        # get the model with ids
        model = model.browse(ids) if len(ids) != len(model) else model
        neg = self.operator in NEGATIVE_TERM_OPERATORS
        operator = TERM_OPERATORS_NEGATION[self.operator] if neg else self.operator

        # get the path and field
        field_name = self.field
        try:
            field = model._fields[field_name]
        except KeyError:
            self._raise("Invalid field %s", field_name)
        value = self.value

        if operator == 'inselect':
            _logger.warning("The operator inselect was an internal implementation, used in filtering.")
            subquery, subparams = value
            cr = model.env.cr
            cr.execute(subquery, subparams)
            value = set(r[0] for r in cr.fetchall())
            operator = 'in'

        if field.relational:
            # search related fields
            comodel = model[field_name]
            if operator == 'any':
                if isinstance(value, Query):
                    coids = set(value)
                else:
                    coids = set(comodel.filtered_domain(D(value).optimize())._ids)
                func = lambda inst: inst._origin.id in coids
            elif isinstance(value, int) or (
                operator == 'in' and all(isinstance(v, int) for v in value)
            ):
                # simple comparison for the ID
                cofunc = self._get_filter_operator_function(operator, value)
                func = lambda inst: cofunc(inst._origin.id)
            elif isinstance(value, str) or (
                operator == 'in' and any(isinstance(v, str) for v in value)
            ):
                # instead of a name_search, filter on display_name
                cofunc = self._get_filter_operator_function(operator, value or '')
                func = lambda inst: cofunc(inst.display_name)
                if cofunc(False):
                    func = any
            else:
                self._raise("Invalid operator for relative field")
            if value is not False and field.type.endswith('2many'):
                # check each instance, except when checking existence
                single_func = func
                if single_func(comodel.browse()):
                    func = lambda inst: not inst or any(single_func(v) for v in inst)
                else:
                    func = lambda inst: any(single_func(v) for v in inst)
        else:
            # search scalar fields
            if field.type == 'date':
                leaf = _optimize_type_date(self, model)
                operator, value = leaf.operator, leaf.value
                if neg:
                    operator = TERM_OPERATORS_NEGATION[operator]
            elif field.type == 'datetime':
                leaf = _optimize_type_datetime(self, model)
                operator, value = leaf.operator, leaf.value
                if neg:
                    operator = TERM_OPERATORS_NEGATION[operator]
            elif not value and field.type in ('integer', 'monetary', 'float'):
                value = 0
            func = self._get_filter_operator_function(operator, value)
        return set(
            r.id
            for r in model
            if bool(func(r[field_name])) != neg
        )

    def _get_filter_operator_function(self, operator, value):
        if value is False:
            operator = 'in'
            value = {False}
        if operator == 'in':
            if not isinstance(value, set):
                self._raise("Optimization not done, expecting a set")
            if not value:
                return lambda _: False
            if value == {False}:
                return lambda data: not data
            return lambda data: data in value
        if operator.endswith('like'):
            if not value and not operator.startswith('='):
                return lambda _: True
            unaccent = unaccent_python
            if 'i' in operator:
                data_case = lambda v: unaccent(v or "").lower()
                value_esc = unaccent(value).lower()
            else:
                data_case = lambda v: unaccent(v or "")
                value_esc = unaccent(value)
            if not operator.startswith('='):
                value_esc = "%" + value_esc + "%"
            value_esc = value_esc.replace('_', '?').replace('%', '*').replace('[', '?')
            return lambda data: fnmatch.fnmatchcase(data_case(data), value_esc)
        op = {'<': pyop.lt, '>': pyop.gt, '<=': pyop.le, '>=': pyop.ge}.get(operator)
        if op:
            def check(data):
                try:
                    if data is False:
                        return False
                    return op(data, value)
                except Exception:
                    # ignoring error, type mismatch
                    return False
            return check
        if operator in NEGATIVE_TERM_OPERATORS:
            nfunc = self._get_filter_operator_function(TERM_OPERATORS_NEGATION[operator], value)
            return lambda v: not nfunc(v)
        self._raise("Invalid operator")


# --------------------------------------------------
# Optimizations
# --------------------------------------------------

_BINARY_OPTIMIZATIONS = list()
_LEAF_OPTIMIZATIONS_BY_FIELD_TYPE = collections.defaultdict(list)
_LEAF_OPTIMIZATIONS_BY_OPERATOR = collections.defaultdict(list)


def register_binary_optimization():
    """Register an optimization for (cls, children, model)
    These are called when there are multiple children and the model is set.
    """
    def register(optimization):
        _BINARY_OPTIMIZATIONS.append(optimization)
        return optimization
    return register

def register_binary_pair_optimization():
    """Apply optimization to adjacent children using (cls, model, a, b) -> Optional[Domain]

    Both children are replaced if result is not None
    """
    def register(optimization):
        def binary_optimization(cls, children, model):
            # the children argument is always a list
            if not children:
                raise cls.zero
            # check if j-1 and j can be merged
            # domain_ok, indicates if j-1 has the right type
            j = 1
            previous = children[0]
            while j < len(children):
                this = children[j]
                merged = optimization(cls, model, previous, this)
                if merged is not None:
                    previous = merged
                    children[j - 1 : j + 1] = [merged]
                else:
                    previous = this
                    j += 1
            return children
        return register_binary_optimization()(binary_optimization)
    return register

def register_leaf_optimization(operator, *, negative_operator=None):
    """Register an operator optimization for (leaf, model)"""
    assert operator, "Missing operator to register"
    if isinstance(operator, list):
        operators = operator
        assert negative_operator is None
        for operator in operators:
            _add_term_operator(operator)
    else:
        operators = [operator]
        _add_term_operator(operator, negative_operator)
    def register(optimization):
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
    def register(optimization):
        for field_type in field_types:
            _LEAF_OPTIMIZATIONS_BY_FIELD_TYPE[field_type].append(optimization)
        return optimization
    return register


@register_leaf_optimization(operator='all')
def _operator_all(leaf, model):
    """Quantifier reduction:
    \\exists == any, none == not any,
    \\forall == all; implemented as not any with inversed domain"""
    return DomainLeaf(leaf.field, 'none', D(leaf.value).optimize_not(model))


@register_leaf_optimization(operator='=?')
def _operator_equal_if_value(leaf, _):
    """a =? b  <=>  not b or a = b"""
    if not leaf.value:
        return TRUE_DOMAIN
    return DomainLeaf(leaf.field, 'in', {leaf.value})


@register_leaf_optimization(operator='<>')
def _operator_different(leaf, _):
    """a <> b  =>  a != b"""
    # rewrite-rule
    # XXX _logger.warning("Use '!=' instead of '<>' in domain %s", leaf)
    return DomainLeaf(leaf.field, '!=', leaf.value)


@register_leaf_optimization(operator='==')
def _operator_equals(leaf, _):
    """a == b  =>  a = b"""
    # rewrite-rule
    # XXX _logger.warning("Use '=' instead of '==' in domain %s", leaf)
    return DomainLeaf(leaf.field, '=', leaf.value)


@register_leaf_optimization(operator='=', negative_operator='!=')
def _operator_equal_as_in(leaf, _):
    """a = b  <=>  a in [b]"""
    value = leaf.value
    if isinstance(value, (list, set)) and not value:
        value = False
    return DomainLeaf(leaf.field, 'in', {value})


@register_leaf_optimization(operator='!=')
def _operator_nequal_as_not_in(leaf, _):
    """a != b  <=>  a not in [b]"""
    value = leaf.value
    if isinstance(value, (list, set)) and not value:
        value = False
    return DomainLeaf(leaf.field, 'not in', {value})


@register_leaf_optimization(['<', '>', '<=', '>='])
def _optimize_inequality(leaf, _):
    """a > [1, 2]  =>  a > 2;  a > nothing  =>  False"""
    value = leaf.value
    if value is False:
        return FALSE_DOMAIN
    if isinstance(value, (list, tuple, set)):
        if False in value:
            value = set(value) - {False}
        if not value:
            return FALSE_DOMAIN
        op = max if '>' in leaf.operator else min
        return DomainLeaf(leaf.field, leaf.operator, op(value))
    return leaf


@register_leaf_optimization('ref')
def _operator_ref(leaf, model):
    """a ref b  <=>  a = ref(b)"""
    if not leaf._execution_mode(model):
        # cannot optimize without a model
        return leaf
    obj = model.env.ref(leaf.value)
    return DomainLeaf(leaf.field, 'in', {obj.id})


@register_leaf_optimization(['in', 'not in'])
def _optimize_operator_in_set(leaf, _):
    """Make sure the value is a set()"""
    value = leaf.value
    # isinstance(value, Query) already handled
    if not value:
        # empty, return a boolean
        return D(leaf.operator in NEGATIVE_TERM_OPERATORS)
    if isinstance(value, set):
        return leaf
    if isinstance(value, (list, tuple)):
        return DomainLeaf(leaf.field, leaf.operator, set(value))
    leaf._raise("Not a list of values, use the '=' or '!=' operator")


@register_leaf_optimization(['any', 'none'])
def _optimize_operator_any_domain_query(leaf, model):
    """Make sure the value is a domain (optimized) or Query"""
    value = leaf.value
    if isinstance(value, Query):
        return leaf
    # get the model to optimize with
    if model is not None:
        field = model._fields[leaf.field]
        comodel = model.env[field.comodel_name]
    else:
        comodel = None
    domain = D(value).optimize(comodel)
    # const if the domain is empty, the result is a constant
    # if the domain is True, we keep it as is
    if domain.const() is False:
        return D(leaf.operator == 'none')
    # if unchanged, return the leaf
    if domain is value:
        return leaf
    return DomainLeaf(leaf.field, leaf.operator, domain)


@register_leaf_optimization([op for op in TERM_OPERATORS if op.endswith('like')])
def _optimize_like_str(leaf, model):
    """Validate value for pattern matching, must be a str"""
    value = leaf.value
    if not value:
        if leaf.operator.startswith('='):
            return FALSE_DOMAIN
        if model is None:
            return leaf
        # relational and non-relation fields behave differently
        if model._fields[leaf.field].relational:
            return DomainLeaf._is_set(leaf.field, leaf.operator not in NEGATIVE_TERM_OPERATORS)
        return D(leaf.operator not in NEGATIVE_TERM_OPERATORS)
    if not isinstance(value, str):
        return DomainLeaf(leaf.field, leaf.operator, str(value))
    return leaf


@register_leaf_optimization_type(['many2one', 'one2many', 'many2many'])
def _rewrite_relational_string_search(leaf, model):
    """Execute _name_search by using _value_to_ids for relational values
    when we have str values."""
    operator = leaf.operator
    value = leaf.value
    if not (
        operator.endswith('like') or (
            isinstance(value, set) and any(isinstance(v, str) for v in value)
        )
    ) or not leaf._execution_mode(model):
        return leaf
    # rel_field ilike "search"
    # rel_field in {"ok", "test"}
    field = model._fields[leaf.field]
    comodel = model.env[field.comodel_name]
    neg = operator in NEGATIVE_TERM_OPERATORS
    if neg:
        operator = TERM_OPERATORS_NEGATION[operator]
    value = _value_to_ids(value, comodel, operator)
    if not (isinstance(value, Query) or isinstance(value, Domain)):
        value = DomainLeaf('id', 'in', set(value))
    operator = 'none' if neg else 'any'
    return DomainLeaf(leaf.field, operator, value)


@register_leaf_optimization_type(['one2many', 'many2many', 'many2one'])
def _optimize_operator_relation(leaf, _):
    """For the query generation, use any/none.

    (a 'in' {1, False}) <=> (a none ('id' not in {1}))
    (a 'in' {1}) <=> (a any ('id' in {1}))
    (a 'not in' {1, False}) <=> (a any ('id' not in {1}))
    (a 'not in' {1}) <=> (a none ('id' in {1}))
    """
    # like operator already handled
    operator = leaf.operator
    if operator in ('any', 'none') or operator not in STANDARD_TERM_OPERATORS:
        return leaf
    value = leaf.value
    if operator not in ('in', 'not in'):
        # handle other operators
        field_op = 'any'
        if operator in NEGATIVE_TERM_OPERATORS:
            operator = TERM_OPERATORS_NEGATION[operator]
            field_op = 'none'
        return DomainLeaf(leaf.field, field_op, DomainLeaf('id', operator, leaf.value))
    # operator in, not in
    assert isinstance(value, set), "the value should be a set after optimization of 'in'"
    operator = 'none' if (operator == 'in') == (False in value) else 'any'
    if False in value:
        value = value - {False}
        subdomain = DomainLeaf('id', 'not in', value).optimize()
    else:
        subdomain = DomainLeaf('id', 'in', value)
    return DomainLeaf(leaf.field, operator, subdomain)


@register_leaf_optimization_type('boolean')
def _optimize_in_boolean(leaf, model):
    """b in [True, False] <=> True"""
    value = leaf.value
    if leaf.operator not in ('in', 'not in') or not isinstance(value, set):
        return leaf
    if not all(isinstance(v, bool) for v in value):
        if any(isinstance(v, str) for v in value):
            _logger.warning("Comparing boolean with a string in %s", leaf)
        value = {
            v.lower() in ('true', 't', '1') if isinstance(v, str) else bool(v)
            for v in value
        }
    # tautology is simplified to a boolean unless it's the active flag
    if value == {False, True} and (leaf.field != model._active_name or leaf._execution_mode(model)):
        return D(leaf.operator == 'in')
    if value is leaf.value:
        return leaf
    return DomainLeaf(leaf.field, leaf.operator, value)


def _value_to_date(value):
    # check datetime first, because it's a subclass of date
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date) or value is False:
        return value
    if isinstance(value, str):
        if len(value) == 10:
            return date.fromisoformat(value)
        return datetime.fromisoformat(value).date()
    if isinstance(value, (list, tuple, set)):
        return {_value_to_date(v) for v in value}
    raise ValueError('Failed to cast %r into a date' % value)


@register_leaf_optimization_type('date')
def _optimize_type_date(leaf, _):
    """Make sure we have a date type in the value"""
    if leaf.operator.endswith('like'):
        return leaf
    value = _value_to_date(leaf.value)
    if value == leaf.value:
        return leaf
    return DomainLeaf(leaf.field, leaf.operator, value)


def _value_to_datetime(value):
    if isinstance(value, datetime) or value is False:
        return value, False
    if isinstance(value, str):
        return datetime.fromisoformat(value), len(value) == 10
    if isinstance(value, date):
        return datetime.combine(value, time.min), True
    if isinstance(value, (list, tuple, set)):
        value, is_day = zip(*list(_value_to_datetime(v) for v in value))
        return set(value), any(is_day)
    raise ValueError('Failed to cast %r into a datetime' % value)


@register_leaf_optimization_type('datetime')
def _optimize_type_datetime(leaf, _):
    """Make sure we have a datetime type in the value"""
    if leaf.operator.endswith('like'):
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
            return DomainLeaf._is_set(leaf.field, True)
        operator = '<'
    return DomainLeaf(leaf.field, operator, value)


@register_leaf_optimization_type('binary')
def _optimize_type_binary_attachment(leaf, model):
    if model is None:
        return leaf
    field = model._fields[leaf.field]
    operator = leaf.operator
    if field.attachment and not (operator in ('in', 'not in') and leaf.value == {False}):
        try:
            leaf._raise('Binary field stored in attachment, accepts only existence check; skipping domain')
        except ValueError as e:
            _logger.error(e, exc_info=True)
        return TRUE_DOMAIN
    if operator.endswith('like'):
        leaf._raise('Cannot use like operators with binary fields', error=NotImplementedError)
    return leaf


def _optimize_b_sort_key(domain):
    # group the same field and same operator together
    if isinstance(domain, DomainLeaf):
        order = domain.operator
        if order in NEGATIVE_TERM_OPERATORS:
            order = TERM_OPERATORS_NEGATION.get(order, order)
        order += ':' + str(type(domain.value))
        return domain.field, order
    else:
        # '~' > any letter in python
        return '~', str(type(domain))


@register_binary_optimization()
def _optimize_b_sort(cls, children, model):
    """Sort conditions in order to apply pair optimization"""
    return sorted(children, key=_optimize_b_sort_key)


@register_binary_pair_optimization()
def _optimize_merge_set_conditions(cls, model, a, b):
    """Merge 'in' conditions.

    Combine the 'in' and 'not in' conditions to a single set of values.

    For example:
    a in {1} and a in {2}  <=>  a in {1, 2}
    a in {1, 2} and a not in {2, 5}  =>  a in {2}
    """
    if not (
        a.field
        and a.field == b.field
        and {a.operator, b.operator} <= {'in', 'not in'}
        and isinstance(value_a := a.value, set)
        and isinstance(value_b := b.value, set)
    ):
        return None
    if model._fields[a.field].type.endswith('2many'):
        # cannot merge conditions for x2many fields
        return None
    z = cls.zero.const()
    # different operators, take the more restricting one
    if a.operator != b.operator:
        if (a.operator == 'in') != z:
            a, b = b, a
            value_a, value_b = value_b, value_a
        value = value_a - value_b
        if not value:
            # empty set
            return ~cls.zero
        return DomainLeaf(a.field, a.operator, value)
    # same operator, intersect or union of values
    if (a.operator == 'in') == z:
        value = value_a & value_b
        if not value:
            # empty set, negation of zero
            return ~cls.zero
    else:
        value = value_a | value_b
    return DomainLeaf(a.field, a.operator, value)

@register_binary_pair_optimization()
def _optimize_merge_many2one(cls, model, a, b):
    """Since we have optimized children, we can look at many2one fields
    and merge the 'any' conditions.
    This will lead to a smaller number of sub-queries.

    For example:
    a.f = 8 and a.g = 5  <=>  a any (f = 8 and g = 5)
    a.f = 1 or a none a.g = 5 => a none (not(f = 1) or g = 5)
    """
    if not (
        a.field
        and a.field == b.field
        and {a.operator, b.operator} <= {'any', 'none'}
        and isinstance(a.value, Domain)
        and isinstance(b.value, Domain)
    ):
        return None
    if (field := model._fields[a.field]).type != 'many2one':
        return None
    if (comodel := model.env.get(field.comodel_name)) is None:
        return None
    # transformation where (a, b) are conditions on a many2one:
    # exists a and exists b => exists (a and b)
    # exists a or exists b => exists (a or b)
    # exists a and not exists b => exists (a and not b)
    # exists a or not exists b => not exists (not a and b)
    # not exists a and not exists b => not exists (a or b)
    # not exists a or not exists b => not exists (a and b)
    operator_dominating = 'any' if cls.zero.const() else 'none'
    operator = a.operator if operator_dominating == a.operator else b.operator
    change_cls = operator == 'none'
    # inverse the condition when the operator changes while class does not
    av, bv = a.value, b.value
    if (a.operator != operator) != change_cls:
        av = ~av
    if (b.operator != operator) != change_cls:
        bv = ~bv
    value = cls([av, bv])
    if change_cls:
        value = ~value
    return DomainLeaf(a.field, operator, value.optimize(comodel))


@register_binary_pair_optimization()
def _optimize_merge_x2many(cls, model, a, b):
    """Since we have optimized children, we can look at x2many fields
    and sometime merge the 'any' conditions.
    This will lead to a smaller number of sub-queries.

    For example:
    a.f = 8 and a.g = 5  (not optimizable, 2 different instances may satisfy conditions)
    a.f = 8 or a.g = 5  <=>  a any (f = 8 or g = 5)
    a.f = 1 and a none g = 5 (not optimizable)
    a none f = 1 and a none g = 5  <=>  a none (f = 1 or g = 5)
    """
    if not (
        a.field
        and a.field == b.field
        and a.operator in {'any', 'none'}
        and a.operator == b.operator
        and cls.zero.const() == (a.operator == 'none')
        and isinstance(a.value, Domain)
        and isinstance(b.value, Domain)
    ):
        return None
    if (field := model._fields[a.field]).type.endswith('2many'):
        return None
    if (comodel := model.env.get(field.comodel_name)) is None:
        return None
    operator = a.operator
    if operator == 'none':
        cls = DomainAnd if cls == DomainOr else DomainOr
    value = cls([a.value, b.value]).optimize(comodel)
    return DomainLeaf(a.field, operator, value)

# --------------------------------------------------
# Domain for subqueries and hierarchies
# --------------------------------------------------

def _value_to_ids(value, comodel, operator_str='ilike'):
    """For relational fields, transform a value into a set of ids, query or domain."""
    if isinstance(value, set):
        # simple case: already a set of ids
        if all(isinstance(i, int) and i for i in value):
            return value
        # just a single value (probably a string)
        if len(value) == 1:
            value = next(iter(value))
    if isinstance(value, str):
        # XXX _name_search could return a domain in the future
        # or we could search on display_name
        return comodel._name_search(value, [], operator_str, limit=None)
    if isinstance(value, int) and value:
        return {value}
    if isinstance(value, (list, tuple, set)):
        if len(value) == 1:
            return _value_to_ids(next(iter(value)), comodel, operator_str)
        # get the ids for each value
        return set(i for v in value for i in _value_to_ids(v, comodel, operator_str))
    return set()


def _operator_child_of_domain(left, ids, comodel, parent=None):
    """ Return a domain implementing the child_of operator for [(left,child_of,ids)],
        either as a range using the parent_path tree lookup field
        (when available), or as an expanded [(left,in,child_ids)] """
    comodel = comodel.sudo().browse(ids)
    parent = parent or comodel._parent_name
    if comodel._parent_store and parent == comodel._parent_name:
        domain = DomainOr([
            DomainLeaf('parent_path', '=like', rec.parent_path + '%')
            for rec in comodel
        ])
        if left != 'id':
            domain = DomainLeaf(left, 'any', domain)
    else:
        # recursively retrieve all children nodes with sudo(); the
        # filtering of forbidden records is done by the rest of the
        # domain
        child_ids = set()
        while comodel:
            child_ids.update(comodel._ids)
            comodel = comodel.search([(parent, 'in', comodel.ids)], order='id')
        domain = DomainLeaf(left, 'in', child_ids)
    return domain


def _operator_parent_of_domain(left, ids, comodel, parent=None):
    """ Return a domain implementing the parent_of operator for [(left,parent_of,ids)],
        either as a range using the parent_path tree lookup field
        (when available), or as an expanded [(left,in,parent_ids)] """
    comodel = comodel.sudo().browse(ids)
    parent = parent or comodel._parent_name
    if comodel._parent_store and parent == comodel._parent_name:
        parent_ids = [
            int(label)
            for rec in comodel
            for label in rec.parent_path.split('/')[:-1]
        ]
        domain = DomainLeaf(left, 'in', parent_ids)
    else:
        # recursively retrieve all parent nodes with sudo() to avoid
        # access rights errors; the filtering of forbidden records is
        # done by the rest of the domain
        parent_ids = set()
        while comodel:
            parent_ids.update(comodel._ids)
            comodel = comodel[parent]
        domain = DomainLeaf(left, 'in', parent_ids)
    return domain


@register_leaf_optimization(['parent_of', 'child_of'])
def _operator_hierarchy(leaf, model):
    """Transform a hierarchy operator into an 'in' ids"""
    if not leaf._execution_mode(model):
        # not optimized without execution mode
        return leaf
    if leaf.operator == 'parent_of':
        hierarchy = _operator_parent_of_domain
    else:
        hierarchy = _operator_child_of_domain
    value = leaf.value
    field = model._fields[leaf.field]
    if leaf.field == 'id':
        comodel = model
        parent = None
    else:
        comodel = model.env[field.comodel_name]
        parent = leaf.field
    if value is False:
        _logger.warning('Using %s with False value, the result will be empty', leaf.operator)
    ids2 = _value_to_ids(value, comodel)
    if isinstance(ids2, Domain):
        ids2 = comodel.search(ids2, order='id').ids
    if not ids2:
        return FALSE_DOMAIN
    if comodel._name == model._name:
        result = hierarchy('id', ids2, model, parent)
    else:
        result = hierarchy(leaf.field, ids2, comodel)
    if not model.env.su and field.type == 'many2one' and isinstance(result, DomainLeaf) and result.operator == 'in':
        # for many2one, check what is accessible because this check is bypassed in _build_domain
        accessible_ids = set(comodel.search(DomainLeaf('id', 'in', result.value))._ids)
        result = DomainLeaf(result.field, 'in', accessible_ids)
    return result


# --------------------------------------------------
# Domain builder
# Generic domain manipulation
# --------------------------------------------------

def D(domain=None, operator=None, value=None) -> Domain:
    """Domain builder

    The built domain is normalized, but not yet optimized.

        D([('a', '=', 5), ('b', '=', 8)])

        D('a', '=', 5) & ('b', '=', 8)

    :param domain: A Domain, or a list representation, or a bool, or str (field)
    :param operator: When set, the domain is a str and the value should be set
    :param value: The value for the operator
    """
    # if operator, build a leaf
    if operator is not None:
        if isinstance(domain, str):
            field, operator, value = DomainLeaf._validate_arguments(domain, operator, value)
            return DomainLeaf(field, operator, value)
        if isinstance(domain, int):
            # special cases like True/False leaves
            if operator == '=':
                return D(domain == value)
            if operator == '!=':
                return D(domain != value)
        raise TypeError('Field name expected in: %r' % ((domain, operator, value),))
    # already a domain?
    if isinstance(domain, Domain):
        return domain
    # just a leaf-expression?
    if isinstance(domain, tuple) and len(domain) == 3:
        return D(*domain)
    # a constant?
    if domain is True or domain == [] or domain is None:
        return TRUE_DOMAIN
    if domain is False:
        return FALSE_DOMAIN
    # it must be a list or a tuple then
    if not isinstance(domain, (list, tuple)):
        raise TypeError('Invalid argument for domain: %r' % domain)
    # parse the list
    stack = []
    for d in reversed(domain):
        if isinstance(d, (tuple, list)) and len(d) == 3:
            stack.append(D(*d))
        elif d == AND_OPERATOR:
            stack.append(DomainAnd([stack.pop(), stack.pop()]))
        elif d == OR_OPERATOR:
            stack.append(DomainOr([stack.pop(), stack.pop()]))
        elif d == NOT_OPERATOR:
            stack.append(DomainNot(stack.pop()))
        else:
            raise ValueError('Invalid item in domain: %r' % (d,))
    # keep the order and simplify already
    if len(stack) == 1:
        return stack[0]
    return DomainAnd(reversed(stack))


def normalize_domain(domain):
    """Returns a normalized version of ``domain_expr``, where all implicit '&' operators
       have been made explicit. One property of normalized domain expressions is that they
       can be easily combined together as if they were single domain components.
    """
    # keeping the original function for now because it's used in tests/common.py for form evaluation
    warnings.warn("normalize_domain() replaced by D() builder", DeprecationWarning)
    if isinstance(domain, Domain):
        domain = list(domain)
    assert isinstance(domain, (list, tuple)), "Domains to normalize must have a 'domain' form: a list or tuple of domain components"
    if not domain:
        return [TRUE_LEAF]
    result = []
    expected = 1                            # expected number of expressions
    op_arity = {NOT_OPERATOR: 1, AND_OPERATOR: 2, OR_OPERATOR: 2}
    for token in domain:
        if expected == 0:                   # more than expected, like in [A, B]
            result[0:0] = [AND_OPERATOR]             # put an extra '&' in front
            expected = 1
        if isinstance(token, (list, tuple)):  # domain term
            expected -= 1
            token = tuple(token)
        else:
            expected += op_arity.get(token, 0) - 1
        result.append(token)
    assert expected == 0, 'This domain is syntactically not correct: %s' % (domain)
    return result


def AND(domains):
    """AND([D1,D2,...]) returns a domain representing D1 and D2 and ... """
    return DomainAnd(D(d) for d in domains)


def OR(domains):
    """OR([D1,D2,...]) returns a domain representing D1 or D2 or ... """
    domains_orig = list(domains)
    domains = [d for d in domains_orig if not (isinstance(d, list) and d == [])]
    if domains != domains_orig:
        # XXX Sometimes this function is used to build a domain using '|' operator
        # a new alernative is to start with FALSE_DOMAIN and use '|='
        # in the previous implementation empty lists were ignored instead of being
        # treated as a domain (which would be TRUE_DOMAIN)
        _logger.debug('The domain OR contains an empty list as argument, is it TRUE_DOMAIN?')
    return DomainOr(D(d) for d in domains)


def distribute_not(domain):
    """ Distribute any '!' domain operators found inside a normalized domain.

    Because we don't use SQL semantic for processing a 'left not in right'
    query (i.e. our 'not in' is not simply translated to a SQL 'not in'),
    it means that a '! left in right' can not be simply processed
    by __leaf_to_sql by first emitting code for 'left in right' then wrapping
    the result with 'not (...)', as it would result in a 'not in' at the SQL
    level.

    This function is thus responsible for pushing any '!' domain operators
    inside the terms themselves. For example::

         ['!','&',('user_id','=',4),('partner_id','in',[1,2])]
            will be turned into:
         ['|',('user_id','!=',4),('partner_id','not in',[1,2])]

    """
    warnings.warn("distribute_not() deprecated, use D().optimize() instead", DeprecationWarning)
    return list(D(domain).optimize())


# --------------------------------------------------
# SQL utils
# --------------------------------------------------

def _quote(to_quote):
    if '"' not in to_quote:
        return '"%s"' % to_quote
    return to_quote

def _unaccent_wrapper(x):
    if isinstance(x, Composable):
        return SQL('unaccent({})').format(x)
    return 'unaccent({})'.format(x)

def get_unaccent_wrapper(cr):
    if odoo.registry(cr.dbname).has_unaccent:
        return _unaccent_wrapper
    return lambda x: x

def unaccent_python(x):
    """Decompose unicode characters and remove modifiers"""
    # reference: https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-normalize-in-a-python-unicode-string
    # https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize
    return ''.join(
        c for c in unicodedata.normalize('NFD', x)
        if unicodedata.category(c) != 'Mn'
    )


class _SQLBuildHelper(object):
    """SQL builder helper"""
    def __init__(self, model, alias, parent):
        self.model = model
        self.alias = alias or model._table
        self.query = parent.query
        self._unaccent_wrapper = (
            getattr(parent, '_unaccent_wrapper', None)
            or get_unaccent_wrapper(model._cr)
        )
        self.build_clause = parent.build_clause
        self.build_params = parent.build_params

    @property
    def _has_trigram(self):
        return self.model.pool.has_trigram

    def _unaccent(self, field):
        if getattr(field, 'unaccent', False):
            return self._unaccent_wrapper
        return lambda x: x

    def _unaccent_python(self, field):
        if getattr(field, 'unaccent', False):
            return unaccent_python
        return lambda x: x

    def quote(self, field_name, alias=None):
        return _quote(alias or self.alias) + "." + _quote(field_name)

    def get_field(self, field_name):
        model, alias = self.model, self.alias
        field = model._fields.get(field_name)
        if not field or not field.inherited:
            return field, self
        while field.inherited:
            parent_model = model.env[field.related_field.model_name]
            parent_fname = model._inherits[parent_model._name]
            parent_alias = self.query.left_join(
                alias, parent_fname, parent_model._table, 'id', parent_fname,
            )
            model, alias = parent_model, parent_alias
            field = model._fields[field_name]
        return field, _SQLBuildHelper(model, alias, self)

    def result(self):
        where_clause = ''.join(self.build_clause)
        return where_clause, self.build_params


class expression(object):
    """ Parse a domain expression
        Use a real polish notation as input and transform into a domain.
        For more info: http://christophe-simonis-at-tiny.blogspot.com/2008/08/new-new-domain-notation.html
    """

    def __init__(self, domain, model, alias=None, query=None):
        """ Initialize expression object and automatically parse the expression
            right after initialization.

            :param domain: expression (using domain ('foo', '=', 'bar') format)
            :param model: root model
            :param alias: alias for the model table if query is provided
            :param query: optional query object holding the final result

            :attr root_model: base model for the query
            :attr expression: the domain to parse, normalized and prepared
            :attr result: the result of the parsing, as a pair (query, params)
            :attr query: Query object holding the final result
        """
        self.root_model = model = model.with_context(optimize_execute=True)
        self.root_alias = alias or model._table

        # this object handles all the joins
        if query is None:
            query = Query(model.env.cr, self.root_alias, model._table_query or model._table)
        self.query = query

        # normalize, optimize the expression and parse
        domain = D(domain).optimize(model)
        self.expression = domain

        # parse the domain expression
        if domain.const() is True:
            return
        try:
            self.build_clause = []
            self.build_params = []
            sql = _SQLBuildHelper(self.root_model, self.root_alias, self)
            domain._build_query(sql)
        except Exception:
            # when debugging always show the error
            _logger.debug("Failed to build the query for %r", domain, exc_info=True)
            raise
        self.result = sql.result()
        self.query.add_where(*self.result)
