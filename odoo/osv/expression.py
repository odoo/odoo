# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Domain expression processing

The main duty of this module is to compile a domain expression into a
SQL query. A lot of things should be documented here, but as a first
step in the right direction, some tests in test_expression.py
might give you some additional information.

For legacy reasons, a domain uses an inconsistent two-levels abstract
syntax (domains are regular Python data structures). At the first
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
import collections.abc
import json
import logging
import reprlib
import traceback
from datetime import date, datetime, time

import psycopg2.sql

import odoo.modules
from odoo.models import BaseModel, check_property_field_value_name
from odoo.tools import (
    pycompat, pattern_to_translated_trigram_pattern, value_to_translated_trigram_pattern,
    Query, SQL,
)


# Domain operators.
NOT_OPERATOR = '!'
OR_OPERATOR = '|'
AND_OPERATOR = '&'
DOMAIN_OPERATORS = (NOT_OPERATOR, OR_OPERATOR, AND_OPERATOR)

# List of available term operators. It is also possible to use the '<>'
# operator, which is strictly the same as '!='; the later should be preferred
# for consistency. This list doesn't contain '<>' as it is simplified to '!='
# by the normalize_operator() function (so later part of the code deals with
# only one representation).
# Internals (i.e. not available to the user) 'inselect' and 'not inselect'
# operators are also used. In this case its right operand has the form (subselect, params).
TERM_OPERATORS = ('=', '!=', '<=', '<', '>', '>=', '=?', '=like', '=ilike',
                  'like', 'not like', 'ilike', 'not ilike', 'in', 'not in',
                  'child_of', 'parent_of', 'any', 'not any')

# A subset of the above operators, with a 'negative' semantic. When the
# expressions 'in NEGATIVE_TERM_OPERATORS' or 'not in NEGATIVE_TERM_OPERATORS' are used in the code
# below, this doesn't necessarily mean that any of those NEGATIVE_TERM_OPERATORS is
# legal in the processed term.
NEGATIVE_TERM_OPERATORS = ('!=', 'not like', 'not ilike', 'not in')

# Negation of domain expressions
DOMAIN_OPERATORS_NEGATION = {
    AND_OPERATOR: OR_OPERATOR,
    OR_OPERATOR: AND_OPERATOR,
}
TERM_OPERATORS_NEGATION = {
    '<': '>=',
    '>': '<=',
    '<=': '>',
    '>=': '<',
    '=': '!=',
    '!=': '=',
    'in': 'not in',
    'like': 'not like',
    'ilike': 'not ilike',
    'not in': 'in',
    'not like': 'like',
    'not ilike': 'ilike',
    'any': 'not any',
    'not any': 'any',
}
ANY_IN = {'any': 'in', 'not any': 'not in'}

TRUE_LEAF = (1, '=', 1)
FALSE_LEAF = (0, '=', 1)

TRUE_DOMAIN = [TRUE_LEAF]
FALSE_DOMAIN = [FALSE_LEAF]

SQL_OPERATORS = {
    '=': SQL('='),
    '!=': SQL('!='),
    '<=': SQL('<='),
    '<': SQL('<'),
    '>': SQL('>'),
    '>=': SQL('>='),
    'in': SQL('IN'),
    'not in': SQL('NOT IN'),
    '=like': SQL('LIKE'),
    '=ilike': SQL('ILIKE'),
    'like': SQL('LIKE'),
    'ilike': SQL('ILIKE'),
    'not like': SQL('NOT LIKE'),
    'not ilike': SQL('NOT ILIKE'),
}

_logger = logging.getLogger(__name__)


# --------------------------------------------------
# Generic domain manipulation
# --------------------------------------------------

def normalize_domain(domain):
    """Returns a normalized version of ``domain_expr``, where all implicit '&' operators
       have been made explicit. One property of normalized domain expressions is that they
       can be easily combined together as if they were single domain components.
    """
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
            if len(token) == 3 and token[1] in ('any', 'not any'):
                token = (token[0], token[1], normalize_domain(token[2]))
            else:
                token = tuple(token)
        else:
            expected += op_arity.get(token, 0) - 1
        result.append(token)
    if expected:
        raise ValueError(f'Domain {domain} is syntactically not correct.')
    return result


def is_false(model, domain):
    """ Return whether ``domain`` is logically equivalent to false. """
    # use three-valued logic: -1 is false, 0 is unknown, +1 is true
    stack = []
    for token in reversed(normalize_domain(domain)):
        if token == '&':
            stack.append(min(stack.pop(), stack.pop()))
        elif token == '|':
            stack.append(max(stack.pop(), stack.pop()))
        elif token == '!':
            stack.append(-stack.pop())
        elif token == TRUE_LEAF:
            stack.append(+1)
        elif token == FALSE_LEAF:
            stack.append(-1)
        elif token[1] == 'in' and not (isinstance(token[2], Query) or token[2]):
            stack.append(-1)
        elif token[1] == 'not in' and not (isinstance(token[2], Query) or token[2]):
            stack.append(+1)
        else:
            stack.append(0)
    return stack.pop() == -1


def combine(operator, unit, zero, domains):
    """Returns a new domain expression where all domain components from ``domains``
       have been added together using the binary operator ``operator``.

       It is guaranteed to return a normalized domain.

       :param operator:
       :param unit: the identity element of the domains "set" with regard to the operation
                    performed by ``operator``, i.e the domain component ``i`` which, when
                    combined with any domain ``x`` via ``operator``, yields ``x``.
                    E.g. [(1,'=',1)] is the typical unit for AND_OPERATOR: adding it
                    to any domain component gives the same domain.
       :param zero: the absorbing element of the domains "set" with regard to the operation
                    performed by ``operator``, i.e the domain component ``z`` which, when
                    combined with any domain ``x`` via ``operator``, yields ``z``.
                    E.g. [(1,'=',1)] is the typical zero for OR_OPERATOR: as soon as
                    you see it in a domain component the resulting domain is the zero.
       :param domains: a list of normalized domains.
    """
    result = []
    count = 0
    if domains == [unit]:
        return unit
    for domain in domains:
        if domain == unit:
            continue
        if domain == zero:
            return zero
        if domain:
            result += normalize_domain(domain)
            count += 1
    result = [operator] * (count - 1) + result
    return result or unit


def AND(domains):
    """AND([D1,D2,...]) returns a domain representing D1 and D2 and ... """
    return combine(AND_OPERATOR, [TRUE_LEAF], [FALSE_LEAF], domains)


def OR(domains):
    """OR([D1,D2,...]) returns a domain representing D1 or D2 or ... """
    return combine(OR_OPERATOR, [FALSE_LEAF], [TRUE_LEAF], domains)


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

    # This is an iterative version of a recursive function that split domain
    # into subdomains, processes them and combine the results. The "stack" below
    # represents the recursive calls to be done.
    result = []
    stack = [False]

    for token in domain:
        negate = stack.pop()
        # negate tells whether the subdomain starting with token must be negated
        if is_leaf(token):
            if negate:
                left, operator, right = token
                if operator in TERM_OPERATORS_NEGATION:
                    if token in (TRUE_LEAF, FALSE_LEAF):
                        result.append(FALSE_LEAF if token == TRUE_LEAF else TRUE_LEAF)
                    else:
                        result.append((left, TERM_OPERATORS_NEGATION[operator], right))
                else:
                    result.append(NOT_OPERATOR)
                    result.append(token)
            else:
                result.append(token)
        elif token == NOT_OPERATOR:
            stack.append(not negate)
        elif token in DOMAIN_OPERATORS_NEGATION:
            result.append(DOMAIN_OPERATORS_NEGATION[token] if negate else token)
            stack.append(negate)
            stack.append(negate)
        else:
            result.append(token)

    return result


def _anyfy_leaves(domain, model):
    """ Return the domain where all conditions on field sequences have been
    transformed into 'any' conditions.
    """
    result = []
    for item in domain:
        if is_operator(item):
            result.append(item)
            continue

        left, operator, right = item = tuple(item)
        if is_boolean(item):
            result.append(item)
            continue

        path = left.split('.', 1)
        field = model._fields.get(path[0])
        if not field:
            raise ValueError(f"Invalid field {model._name}.{path[0]} in leaf {item}")
        if len(path) > 1 and field.relational:  # skip properties
            subdomain = [(path[1], operator, right)]
            comodel = model.env[field.comodel_name]
            result.append((path[0], 'any', _anyfy_leaves(subdomain, comodel)))
        elif operator in ('any', 'not any'):
            comodel = model.env[field.comodel_name]
            result.append((left, operator, _anyfy_leaves(right, comodel)))
        else:
            result.append(item)

    return result


def _tree_from_domain(domain):
    """ Return the domain as a tree, with the following structure::

        <tree> ::= ('?', <boolean>)
                |  ('!', <tree>)
                |  ('&', <tree>, <tree>, ...)
                |  ('|', <tree>, <tree>, ...)
                |  (<comparator>, <fname>, <value>)

    By construction, AND (``&``) and OR (``|``) nodes are n-ary and have at
    least two children.  Moreover, AND nodes (respectively OR nodes) do not have
    AND nodes (resp. OR nodes) in their children.
    """
    stack = []
    for item in reversed(domain):
        if item == '!':
            stack.append(_tree_not(stack.pop()))
        elif item == '&':
            stack.append(_tree_and((stack.pop(), stack.pop())))
        elif item == '|':
            stack.append(_tree_or((stack.pop(), stack.pop())))
        elif item == TRUE_LEAF:
            stack.append(('?', True))
        elif item == FALSE_LEAF:
            stack.append(('?', False))
        else:
            lhs, comparator, rhs = item
            if comparator in ('any', 'not any'):
                rhs = _tree_from_domain(rhs)
            stack.append((comparator, lhs, rhs))
    return _tree_and(reversed(stack))


def _tree_not(tree):
    """ Negate a tree node. """
    if tree[0] == '?':
        return ('?', not tree[1])
    if tree[0] == '!':
        return tree[1]
    if tree[0] == '&':
        return ('|', *(_tree_not(item) for item in tree[1:]))
    if tree[0] == '|':
        return ('&', *(_tree_not(item) for item in tree[1:]))
    if tree[0] in TERM_OPERATORS_NEGATION:
        return (TERM_OPERATORS_NEGATION[tree[0]], tree[1], tree[2])
    return ('!', tree)


def _tree_and(trees):
    """ Return the tree given by AND-ing all the given trees. """
    children = []
    for tree in trees:
        if tree == ('?', True):
            pass
        elif tree == ('?', False):
            return tree
        elif tree[0] == '&':
            children.extend(tree[1:])
        else:
            children.append(tree)
    if not children:
        return ('?', True)
    if len(children) == 1:
        return children[0]
    return ('&', *children)


def _tree_or(trees):
    """ Return the tree given by OR-ing all the given trees. """
    children = []
    for tree in trees:
        if tree == ('?', True):
            return tree
        elif tree == ('?', False):
            pass
        elif tree[0] == '|':
            children.extend(tree[1:])
        else:
            children.append(tree)
    if not children:
        return ('?', False)
    if len(children) == 1:
        return children[0]
    return ('|', *children)


def _tree_combine_anies(tree, model):
    """ Return the tree given by recursively merging 'any' and 'not any' nodes,
    according to the following logical equivalences:

     * (fname ANY dom1) OR (fname ANY dom2) == (fname ANY (dom1 OR dom2))

     * (fname NOT ANY dom1) AND (fname NOT ANY dom2) == (fname NOT ANY (dom1 OR dom2))

    We also merge 'any' and 'not any' nodes according to the following logical
    equivalences *for many2one fields only*:

     * (fname NOT ANY dom1) OR (fname NOT ANY dom2) == (fname NOT ANY (dom1 AND dom2))

     * (fname ANY dom1) AND (fname ANY dom2) == (fname ANY (dom1 AND dom2))

    """

    # first proceed recursively on subtrees
    if tree[0] == '!':
        tree = _tree_not(_tree_combine_anies(tree[1], model))
    elif tree[0] == '&':
        temp = [_tree_combine_anies(subtree, model) for subtree in tree[1:]]
        tree = _tree_and(temp)
    elif tree[0] == '|':
        temp = [_tree_combine_anies(subtree, model) for subtree in tree[1:]]
        tree = _tree_or(temp)

    # proceed recursively on subdomains
    if tree[0] == 'any':
        field = model._fields[tree[1]]
        comodel = model.env[field.comodel_name]
        return ('any', tree[1], _tree_combine_anies(tree[2], comodel))

    if tree[0] == 'not any':
        field = model._fields[tree[1]]
        comodel = model.env[field.comodel_name]
        return ('not any', tree[1], _tree_combine_anies(tree[2], comodel))

    if tree[0] not in ('&', '|'):
        return tree

    # tree is either an '&' or an '|' tree; group leaves using 'any' or 'not any'
    children = []
    any_children = collections.defaultdict(list)
    not_any_children = collections.defaultdict(list)
    for subtree in tree[1:]:
        if subtree[0] == 'any':
            any_children[subtree[1]].append(subtree[2])
        elif subtree[0] == 'not any':
            not_any_children[subtree[1]].append(subtree[2])
        else:
            children.append(subtree)

    if tree[0] == '&':
        # merge subdomains where possible
        for fname, subtrees in any_children.items():
            field = model._fields[fname]
            comodel = model.env[field.comodel_name]
            if field.type == 'many2one' and len(subtrees) > 1:
                # (fname ANY dom1) AND (fname ANY dom2) == (fname ANY (dom1 AND dom2))
                children.append(('any', fname, _tree_combine_anies(_tree_and(subtrees), comodel)))
            else:
                for subtree in subtrees:
                    children.append(('any', fname, _tree_combine_anies(subtree, comodel)))

        for fname, subtrees in not_any_children.items():
            # (fname NOT ANY dom1) AND (fname NOT ANY dom2) == (fname NOT ANY (dom1 OR dom2))
            field = model._fields[fname]
            comodel = model.env[field.comodel_name]
            children.append(('not any', fname, _tree_combine_anies(_tree_or(subtrees), comodel)))

        return _tree_and(children)

    else:
        # merge subdomains where possible
        for fname, subtrees in any_children.items():
            # (fname ANY dom1) OR (fname ANY dom2) == (fname ANY (dom1 OR dom2))
            field = model._fields[fname]
            comodel = model.env[field.comodel_name]
            children.append(('any', fname, _tree_combine_anies(_tree_or(subtrees), comodel)))

        for fname, subtrees in not_any_children.items():
            field = model._fields[fname]
            comodel = model.env[field.comodel_name]
            if field.type == 'many2one' and len(subtrees) > 1:
                # (fname NOT ANY dom1) OR (fname NOT ANY dom2) == (fname NOT ANY (dom1 AND dom2))
                children.append(('not any', fname, _tree_combine_anies(_tree_and(subtrees), comodel)))
            else:
                for subtree in subtrees:
                    children.append(('not any', fname, _tree_combine_anies(subtree, comodel)))

        return _tree_or(children)


def _tree_as_domain(tree):
    """ Return the domain list represented by the given domain tree. """
    def _flatten(tree):
        if tree[0] == '?':
            yield TRUE_LEAF if tree[1] else FALSE_LEAF
        elif tree[0] == '!':
            yield tree[0]
            yield from _flatten(tree[1])
        elif tree[0] in ('&', '|'):
            yield from tree[0] * (len(tree) - 2)
            for subtree in tree[1:]:
                yield from _flatten(subtree)
        elif tree[0] in ('any', 'not any'):
            yield (tree[1], tree[0], _tree_as_domain(tree[2]))
        else:
            yield (tree[1], tree[0], tree[2])

    return list(_flatten(tree))


def domain_combine_anies(domain, model):
    """ Return a domain equivalent to the given one where 'any' and 'not any'
    conditions have been combined in order to generate less subqueries.
    """
    domain_any = _anyfy_leaves(domain, model)
    tree = _tree_from_domain(domain_any)
    merged_tree = _tree_combine_anies(tree, model)
    new_domain = _tree_as_domain(merged_tree)
    return new_domain


def prettify_domain(domain, pre_indent=0):
    """
    Pretty-format a domain into a string by separating each leaf on a
    separated line and by including some indentation. Works with ``any``
    and ``not any`` too. The domain must be normalized.

    :param list domain: a normalized domain
    :param int pre_indent: (optinal) a starting indentation level
    :return: the domain prettified
    :rtype: str
    """

    # The ``stack`` is a stack of layers, each layer accumulates the
    # ``terms`` (leaves/operators) that share a same indentation
    # level (the depth of the layer inside the stack). ``left_count``
    # tracks how many terms should still appear on each layer before the
    # layer is considered complete.
    #
    # When a layer is completed, it is removed from the stack and
    # commited, i.e. its terms added to the ``commits`` list along with
    # the indentation for those terms.
    #
    # When a new operator is added to the layer terms, the current layer
    # is commited (but not removed from the stack if there are still
    # some terms that must be added) and a new (empty) layer is added on
    # top of the stack.
    #
    # When the domain has been fully iterated, the commits are used to
    # craft the final string. All terms are indented according to their
    # commit indentation level and separated by a new line.

    stack = [{'left_count': 1, 'terms': []}]
    commits = []

    for term in domain:
        top = stack[-1]

        if is_operator(term):
            # when a same operator appears twice in a row, we want to
            # include the second one on the same line as the former one
            if (not top['terms'] and commits
                and (commits[-1]['terms'] or [''])[-1].startswith(repr(term))):
                commits[-1]['terms'][-1] += f", {term!r}"  # hack
                top['left_count'] += 0 if term == NOT_OPERATOR else 1
            else:
                commits.append({
                    'indent': len(stack) - 1,
                    'terms': top['terms'] + [repr(term)]
                })
                top['terms'] = []
                top['left_count'] -= 1
                stack.append({
                    'left_count': 1 if term == NOT_OPERATOR else 2,
                    'terms': [],
                })
                top = stack[-1]
        elif term[1] in ('any', 'not any'):
            top['terms'].append('({!r}, {!r}, {})'.format(
                term[0], term[1], prettify_domain(term[2], pre_indent + len(stack) - 1)))
            top['left_count'] -= 1
        else:
            top['terms'].append(repr(term))
            top['left_count'] -= 1

        if not top['left_count']:
            commits.append({
                'indent': len(stack) - 1,
                'terms': top['terms']
            })
            stack.pop()

    return '[{}]'.format(
        f",\n{'    ' * pre_indent}".join([
            f"{'    ' * commit['indent']}{term}"
            for commit in commits
            for term in commit['terms']
        ])
    )


# --------------------------------------------------
# Generic leaf manipulation
# --------------------------------------------------

def normalize_leaf(element):
    """ Change a term's operator to some canonical form, simplifying later
        processing. """
    if not is_leaf(element):
        return element
    left, operator, right = element
    original = operator
    operator = operator.lower()
    if operator == '<>':
        operator = '!='
    if isinstance(right, bool) and operator in ('in', 'not in'):
        _logger.warning("The domain term '%s' should use the '=' or '!=' operator." % ((left, original, right),))
        operator = '=' if operator == 'in' else '!='
    if isinstance(right, (list, tuple)) and operator in ('=', '!='):
        _logger.warning("The domain term '%s' should use the 'in' or 'not in' operator." % ((left, original, right),))
        operator = 'in' if operator == '=' else 'not in'
    return left, operator, right


def is_operator(element):
    """ Test whether an object is a valid domain operator. """
    return isinstance(element, str) and element in DOMAIN_OPERATORS


def is_leaf(element, internal=False):
    """ Test whether an object is a valid domain term:

        - is a list or tuple
        - with 3 elements
        - second element if a valid op

        :param tuple element: a leaf in form (left, operator, right)
        :param bool internal: allow or not the 'inselect' internal operator
            in the term. This should be always left to False.

        Note: OLD TODO change the share wizard to use this function.
    """
    INTERNAL_OPS = TERM_OPERATORS + ('<>',)
    if internal:
        INTERNAL_OPS += ('inselect', 'not inselect')
    return (isinstance(element, tuple) or isinstance(element, list)) \
        and len(element) == 3 \
        and element[1] in INTERNAL_OPS \
        and ((isinstance(element[0], str) and element[0])
             or tuple(element) in (TRUE_LEAF, FALSE_LEAF))


def is_boolean(element):
    return element == TRUE_LEAF or element == FALSE_LEAF


def check_leaf(element, internal=False):
    if not is_operator(element) and not is_leaf(element, internal):
        raise ValueError("Invalid leaf %s" % str(element))


# --------------------------------------------------
# SQL utils
# --------------------------------------------------

def _unaccent_wrapper(x):
    if isinstance(x, SQL):
        return SQL("unaccent(%s)", x)
    if isinstance(x, psycopg2.sql.Composable):
        return psycopg2.sql.SQL('unaccent({})').format(x)
    return 'unaccent({})'.format(x)

def get_unaccent_wrapper(cr):
    if odoo.registry(cr.dbname).has_unaccent:
        return _unaccent_wrapper
    return lambda x: x


class expression(object):
    """ Parse a domain expression
        Use a real polish notation
        Leafs are still in a ('foo', '=', 'bar') format
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
        self._unaccent_wrapper = get_unaccent_wrapper(model._cr)
        self._has_trigram = model.pool.has_trigram
        self.root_model = model
        self.root_alias = alias or model._table

        # normalize and prepare the expression for parsing
        self.expression = domain_combine_anies(domain, model)

        # this object handles all the joins
        self.query = Query(model.env.cr, model._table, model._table_query) if query is None else query

        # parse the domain expression
        self.parse()

    def _unaccent(self, field):
        if getattr(field, 'unaccent', False):
            return self._unaccent_wrapper
        return lambda x: x

    # ----------------------------------------
    # Parsing
    # ----------------------------------------

    def parse(self):
        """ Transform the leaves of the expression

        The principle is to pop elements from a leaf stack one at a time.
        Each leaf is processed. The processing is a if/elif list of various
        cases that appear in the leafs (many2one, function fields, ...).

        Three things can happen as a processing result:

        - the leaf is a logic operator, and updates the result stack
          accordingly;
        - the leaf has been modified and/or new leafs have to be introduced
          in the expression; they are pushed into the leaf stack, to be
          processed right after;
        - the leaf is converted to SQL and added to the result stack

        Example:

        =================== =================== =====================
        step                stack               result_stack
        =================== =================== =====================
                            ['&', A, B]         []
        substitute B        ['&', A, B1]        []
        convert B1 in SQL   ['&', A]            ["B1"]
        substitute A        ['&', '|', A1, A2]  ["B1"]
        convert A2 in SQL   ['&', '|', A1]      ["B1", "A2"]
        convert A1 in SQL   ['&', '|']          ["B1", "A2", "A1"]
        apply operator OR   ['&']               ["B1", "A1 or A2"]
        apply operator AND  []                  ["(A1 or A2) and B1"]
        =================== =================== =====================

        Some internal var explanation:

        :var list path: left operand seen as a sequence of field names
            ("foo.bar" -> ["foo", "bar"])
        :var obj model: model object, model containing the field
            (the name provided in the left operand)
        :var obj field: the field corresponding to `path[0]`
        :var obj column: the column corresponding to `path[0]`
        :var obj comodel: relational model of field (field.comodel)
            (res_partner.bank_ids -> res.partner.bank)
        """
        def to_ids(value, comodel, leaf):
            """ Normalize a single id or name, or a list of those, into a list of ids

            :param comodel:
            :param leaf:
            :param int|str|list|tuple value:

                - if int, long -> return [value]
                - if basestring, convert it into a list of basestrings, then
                - if list of basestring ->

                    - perform a name_search on comodel for each name
                    - return the list of related ids
            """
            names = []
            if isinstance(value, str):
                names = [value]
            elif value and isinstance(value, (tuple, list)) and all(isinstance(item, str) for item in value):
                names = value
            elif isinstance(value, int):
                if not value:
                    # given this nonsensical domain, it is generally cheaper to
                    # interpret False as [], so that "X child_of False" will
                    # match nothing
                    _logger.warning("Unexpected domain [%s], interpreted as False", leaf)
                    return []
                return [value]
            if names:
                return list({
                    rid
                    for name in names
                    for rid in comodel._name_search(name, [], 'ilike')
                })
            return list(value)

        def child_of_domain(left, ids, left_model, parent=None, prefix=''):
            """ Return a domain implementing the child_of operator for [(left,child_of,ids)],
                either as a range using the parent_path tree lookup field
                (when available), or as an expanded [(left,in,child_ids)] """
            if not ids:
                return [FALSE_LEAF]
            left_model_sudo = left_model.sudo().with_context(active_test=False)
            if left_model._parent_store:
                domain = OR([
                    [('parent_path', '=like', rec.parent_path + '%')]
                    for rec in left_model_sudo.browse(ids)
                ])
            else:
                # recursively retrieve all children nodes with sudo(); the
                # filtering of forbidden records is done by the rest of the
                # domain
                parent_name = parent or left_model._parent_name
                if (left_model._name != left_model._fields[parent_name].comodel_name):
                    raise ValueError(f"Invalid parent field: {left_model._fields[parent_name]}")
                child_ids = set()
                records = left_model_sudo.browse(ids)
                while records:
                    child_ids.update(records._ids)
                    records = records.search([(parent_name, 'in', records.ids)], order='id') - records.browse(child_ids)
                domain = [('id', 'in', list(child_ids))]
            if prefix:
                return [(left, 'in', left_model_sudo._search(domain))]
            return domain

        def parent_of_domain(left, ids, left_model, parent=None, prefix=''):
            """ Return a domain implementing the parent_of operator for [(left,parent_of,ids)],
                either as a range using the parent_path tree lookup field
                (when available), or as an expanded [(left,in,parent_ids)] """
            ids = [id for id in ids if id]  # ignore (left, 'parent_of', [False])
            if not ids:
                return [FALSE_LEAF]
            left_model_sudo = left_model.sudo().with_context(active_test=False)
            if left_model._parent_store:
                parent_ids = [
                    int(label)
                    for rec in left_model_sudo.browse(ids)
                    for label in rec.parent_path.split('/')[:-1]
                ]
                domain = [('id', 'in', parent_ids)]
            else:
                # recursively retrieve all parent nodes with sudo() to avoid
                # access rights errors; the filtering of forbidden records is
                # done by the rest of the domain
                parent_name = parent or left_model._parent_name
                parent_ids = set()
                records = left_model_sudo.browse(ids)
                while records:
                    parent_ids.update(records._ids)
                    records = records[parent_name] - records.browse(parent_ids)
                domain = [('id', 'in', list(parent_ids))]
            if prefix:
                return [(left, 'in', left_model_sudo._search(domain))]
            return domain

        HIERARCHY_FUNCS = {'child_of': child_of_domain,
                           'parent_of': parent_of_domain}

        def pop():
            """ Pop a leaf to process. """
            return stack.pop()

        def push(leaf, model, alias, internal=False):
            """ Push a leaf to be processed right after. """
            leaf = normalize_leaf(leaf)
            check_leaf(leaf, internal)
            stack.append((leaf, model, alias))

        def pop_result():
            return result_stack.pop()

        def push_result(sql):
            result_stack.append(sql)

        # process domain from right to left; stack contains domain leaves, in
        # the form: (leaf, corresponding model, corresponding table alias)
        stack = []
        for leaf in self.expression:
            push(leaf, self.root_model, self.root_alias)

        # stack of SQL expressions
        result_stack = []

        while stack:
            # Get the next leaf to process
            leaf, model, alias = pop()

            # ----------------------------------------
            # SIMPLE CASE
            # 1. leaf is an operator
            # 2. leaf is a true/false leaf
            # -> convert and add directly to result
            # ----------------------------------------

            if is_operator(leaf):
                if leaf == NOT_OPERATOR:
                    push_result(SQL("(NOT (%s))", pop_result()))
                elif leaf == AND_OPERATOR:
                    push_result(SQL("(%s AND %s)", pop_result(), pop_result()))
                else:
                    push_result(SQL("(%s OR %s)", pop_result(), pop_result()))
                continue

            if is_boolean(leaf):
                push_result(self.__leaf_to_sql(leaf, model, alias))
                continue

            # Get working variables
            left, operator, right = leaf
            path = left.split('.', 1)

            field = model._fields.get(path[0])
            comodel = model.env.get(getattr(field, 'comodel_name', None))

            # ----------------------------------------
            # FIELD NOT FOUND
            # -> from inherits'd fields -> work on the related model, and add
            #    a join condition
            # -> ('id', 'child_of', '..') -> use a 'to_ids'
            # -> but is one on the _log_access special fields, add directly to
            #    result
            #    TODO: make these fields explicitly available in self.columns instead!
            # -> else: crash
            # ----------------------------------------

            if field.inherited:
                parent_model = model.env[field.related_field.model_name]
                parent_fname = model._inherits[parent_model._name]
                parent_alias = self.query.left_join(
                    alias, parent_fname, parent_model._table, 'id', parent_fname,
                )
                push(leaf, parent_model, parent_alias)

            elif left == 'id' and operator in HIERARCHY_FUNCS:
                ids2 = to_ids(right, model, leaf)
                dom = HIERARCHY_FUNCS[operator](left, ids2, model)
                for dom_leaf in dom:
                    push(dom_leaf, model, alias)

            elif field.type == 'properties':
                if len(path) != 2 and "." in path[1]:
                    raise ValueError(f"Wrong path {path}")
                elif operator not in ('=', '!=', '>', '>=', '<', '<=', 'in', 'not in', 'like', 'ilike', 'not like', 'not ilike'):
                    raise ValueError(f"Wrong search operator {operator!r}")
                property_name = path[1]
                check_property_field_value_name(property_name)

                if (isinstance(right, bool) or right is None) and operator in ('=', '!='):
                    # check for boolean value but also for key existence
                    if right:
                        # inverse the condition
                        right = False
                        operator = '!=' if operator == '=' else '='

                    sql_field = model._field_to_sql(alias, field.name, self.query)
                    sql_operator = SQL_OPERATORS[operator]
                    sql_extra = SQL()
                    if operator == '=':  # property == False
                        sql_extra = SQL(
                            "OR (%s IS NULL) OR NOT (%s ? %s)",
                            sql_field, sql_field, property_name,
                        )

                    push_result(SQL(
                        "((%s -> %s) %s '%s' %s)",
                        sql_field, property_name, sql_operator, right, sql_extra,
                    ))

                else:
                    if operator in ('like', 'ilike', 'not like', 'not ilike'):
                        right = f'%{pycompat.to_text(right)}%'
                        unaccent = self._unaccent(field)
                    else:
                        unaccent = lambda x: x

                    sql_field = model._field_to_sql(alias, field.name, self.query)

                    if operator in ('in', 'not in'):
                        sql_not = SQL('NOT') if operator == 'not in' else SQL()
                        sql_left = SQL("%s -> %s", sql_field, property_name)  # raw value
                        sql_operator = SQL('<@') if isinstance(right, (list, tuple)) else SQL('@>')
                        sql_right = SQL("%s", json.dumps(right))
                        push_result(SQL(
                            "(%s (%s) %s (%s))",
                            sql_not, unaccent(sql_left), sql_operator, unaccent(sql_right),
                        ))

                    elif isinstance(right, str):
                        sql_left = SQL("%s ->> %s", sql_field, property_name)  # JSONified value
                        sql_operator = SQL_OPERATORS[operator]
                        sql_right = SQL("%s", right)
                        push_result(SQL(
                            "((%s) %s (%s))",
                            unaccent(sql_left), sql_operator, unaccent(sql_right),
                        ))

                    else:
                        sql_left = SQL("%s -> %s", sql_field, property_name)  # raw value
                        sql_operator = SQL_OPERATORS[operator]
                        sql_right = SQL("%s", json.dumps(right))
                        push_result(SQL(
                            "((%s) %s (%s))",
                            unaccent(sql_left), sql_operator, unaccent(sql_right),
                        ))

            # ----------------------------------------
            # PATH SPOTTED
            # -> many2one or one2many with _auto_join:
            #    - add a join, then jump into linked column: column.remaining on
            #      src_table is replaced by remaining on dst_table, and set for re-evaluation
            #    - if a domain is defined on the column, add it into evaluation
            #      on the relational table
            # -> many2one, many2many, one2many: replace by an equivalent computed
            #    domain, given by recursively searching on the remaining of the path
            # -> note: hack about columns.property should not be necessary anymore
            #    as after transforming the column, it will go through this loop once again
            # ----------------------------------------

            elif operator in ('any', 'not any') and field.store and field.type == 'many2one' and field.auto_join:
                # res_partner.state_id = res_partner__state_id.id
                coalias = self.query.left_join(
                    alias, field.name, comodel._table, 'id', field.name,
                )

                if operator == 'not any':
                    right = ['|', ('id', '=', False), '!', *right]

                for leaf in right:
                    push(leaf, comodel, coalias)

            elif operator in ('any', 'not any') and field.store and field.type == 'one2many' and field.auto_join:
                # use a subquery bypassing access rules and business logic
                domain = right + field.get_domain_list(model)
                query = comodel.with_context(**field.context)._where_calc(domain)
                sql = query.subselect(
                    comodel._field_to_sql(comodel._table, field.inverse_name, query),
                )
                push(('id', ANY_IN[operator], sql), model, alias)

            elif operator in ('any', 'not any') and field.store and field.auto_join:
                raise NotImplementedError('auto_join attribute not supported on field %s' % field)

            elif operator in ('any', 'not any') and field.store and field.type == 'many2one':
                right_ids = comodel.with_context(active_test=False)._search(right)
                if operator == 'any':
                    push((left, 'in', right_ids), model, alias)
                else:
                    for dom_leaf in ('|', (left, 'not in', right_ids), (left, '=', False)):
                        push(dom_leaf, model, alias)

            # Making search easier when there is a left operand as one2many or many2many
            elif operator in ('any', 'not any') and field.store and field.type in ('many2many', 'one2many'):
                right_ids = comodel.with_context(**field.context)._search(right)
                push((left, ANY_IN[operator], right_ids), model, alias)

            elif not field.store:
                # Non-stored field should provide an implementation of search.
                if not field.search:
                    # field does not support search!
                    _logger.error("Non-stored field %s cannot be searched.", field, exc_info=True)
                    if _logger.isEnabledFor(logging.DEBUG):
                        _logger.debug(''.join(traceback.format_stack()))
                    # Ignore it: generate a dummy leaf.
                    domain = []
                else:
                    # Let the field generate a domain.
                    if len(path) > 1:
                        right = comodel._search([(path[1], operator, right)])
                        operator = 'in'
                    domain = field.determine_domain(model, operator, right)
                    model._flush_search(domain)

                for elem in domain_combine_anies(domain, model):
                    push(elem, model, alias, internal=True)

            # -------------------------------------------------
            # RELATIONAL FIELDS
            # -------------------------------------------------

            # Applying recursivity on field(one2many)
            elif field.type == 'one2many' and operator in HIERARCHY_FUNCS:
                ids2 = to_ids(right, comodel, leaf)
                if field.comodel_name != model._name:
                    dom = HIERARCHY_FUNCS[operator](left, ids2, comodel, prefix=field.comodel_name)
                else:
                    dom = HIERARCHY_FUNCS[operator]('id', ids2, model, parent=left)
                for dom_leaf in dom:
                    push(dom_leaf, model, alias)

            elif field.type == 'one2many':
                domain = field.get_domain_list(model)
                inverse_field = comodel._fields[field.inverse_name]
                inverse_is_int = inverse_field.type in ('integer', 'many2one_reference')
                unwrap_inverse = (lambda ids: ids) if inverse_is_int else (lambda recs: recs.ids)

                if right is not False:
                    # determine ids2 in comodel
                    if isinstance(right, str):
                        op2 = (TERM_OPERATORS_NEGATION[operator]
                               if operator in NEGATIVE_TERM_OPERATORS else operator)
                        ids2 = comodel._name_search(right, domain or [], op2)
                    elif isinstance(right, collections.abc.Iterable):
                        ids2 = right
                    else:
                        ids2 = [right]
                    if inverse_is_int and domain:
                        ids2 = comodel._search([('id', 'in', ids2)] + domain)

                    if inverse_field.store:
                        # In the condition, one must avoid subqueries to return
                        # NULL values, since it makes the IN test NULL instead
                        # of FALSE.  This may discard expected results, as for
                        # instance "id NOT IN (42, NULL)" is never TRUE.
                        sql_in = SQL('NOT IN') if operator in NEGATIVE_TERM_OPERATORS else SQL('IN')
                        if not isinstance(ids2, Query):
                            ids2 = comodel.browse(ids2)._as_query(ordered=False)
                        sql_inverse = comodel._field_to_sql(ids2.table, inverse_field.name, ids2)
                        if not inverse_field.required:
                            ids2.add_where(SQL("%s IS NOT NULL", sql_inverse))
                        push_result(SQL(
                            "(%s %s %s)",
                            SQL.identifier(alias, 'id'),
                            sql_in,
                            ids2.subselect(sql_inverse),
                        ))
                    else:
                        # determine ids1 in model related to ids2
                        recs = comodel.browse(ids2).sudo().with_context(prefetch_fields=False)
                        ids1 = unwrap_inverse(recs.mapped(inverse_field.name))
                        # rewrite condition in terms of ids1
                        op1 = 'not in' if operator in NEGATIVE_TERM_OPERATORS else 'in'
                        push(('id', op1, ids1), model, alias)

                else:
                    if inverse_field.store and not (inverse_is_int and domain):
                        # rewrite condition to match records with/without lines
                        sub_op = 'in' if operator in NEGATIVE_TERM_OPERATORS else 'not in'
                        comodel_domain = [(inverse_field.name, '!=', False)]
                        query = comodel.with_context(active_test=False)._where_calc(comodel_domain)
                        sql_inverse = comodel._field_to_sql(query.table, inverse_field.name, query)
                        sql = query.subselect(sql_inverse)
                        push(('id', sub_op, sql), model, alias)
                    else:
                        comodel_domain = [(inverse_field.name, '!=', False)]
                        if inverse_is_int and domain:
                            comodel_domain += domain
                        recs = comodel.search(comodel_domain, order='id').sudo().with_context(prefetch_fields=False)
                        # determine ids1 = records with lines
                        ids1 = unwrap_inverse(recs.mapped(inverse_field.name))
                        # rewrite condition to match records with/without lines
                        op1 = 'in' if operator in NEGATIVE_TERM_OPERATORS else 'not in'
                        push(('id', op1, ids1), model, alias)

            elif field.type == 'many2many':
                rel_table, rel_id1, rel_id2 = field.relation, field.column1, field.column2

                if operator in HIERARCHY_FUNCS:
                    # determine ids2 in comodel
                    ids2 = to_ids(right, comodel, leaf)
                    domain = HIERARCHY_FUNCS[operator]('id', ids2, comodel)
                    ids2 = comodel._search(domain)

                    # rewrite condition in terms of ids2
                    if comodel == model:
                        push(('id', 'in', ids2), model, alias)
                    else:
                        rel_alias = self.query.make_alias(alias, field.name)
                        push_result(SQL(
                            "EXISTS (SELECT 1 FROM %s AS %s WHERE %s = %s AND %s IN %s)",
                            SQL.identifier(rel_table),
                            SQL.identifier(rel_alias),
                            SQL.identifier(rel_alias, rel_id1),
                            SQL.identifier(alias, 'id'),
                            SQL.identifier(rel_alias, rel_id2),
                            tuple(ids2) or (None,),
                        ))

                elif right is not False:
                    # determine ids2 in comodel
                    if isinstance(right, str):
                        domain = field.get_domain_list(model)
                        op2 = (TERM_OPERATORS_NEGATION[operator]
                               if operator in NEGATIVE_TERM_OPERATORS else operator)
                        ids2 = comodel._name_search(right, domain or [], op2)
                    elif isinstance(right, collections.abc.Iterable):
                        ids2 = right
                    else:
                        ids2 = [right]

                    if isinstance(ids2, Query):
                        # rewrite condition in terms of ids2
                        sql_ids2 = ids2.subselect()
                    else:
                        # rewrite condition in terms of ids2
                        sql_ids2 = SQL("%s", tuple(it for it in ids2 if it) or (None,))

                    if operator in NEGATIVE_TERM_OPERATORS:
                        sql_exists = SQL('NOT EXISTS')
                    else:
                        sql_exists = SQL('EXISTS')

                    rel_alias = self.query.make_alias(alias, field.name)
                    push_result(SQL(
                        "%s (SELECT 1 FROM %s AS %s WHERE %s = %s AND %s IN %s)",
                        sql_exists,
                        SQL.identifier(rel_table),
                        SQL.identifier(rel_alias),
                        SQL.identifier(rel_alias, rel_id1),
                        SQL.identifier(alias, 'id'),
                        SQL.identifier(rel_alias, rel_id2),
                        sql_ids2,
                    ))

                else:
                    # rewrite condition to match records with/without relations
                    if operator in NEGATIVE_TERM_OPERATORS:
                        sql_exists = SQL('EXISTS')
                    else:
                        sql_exists = SQL('NOT EXISTS')
                    rel_alias = self.query.make_alias(alias, field.name)
                    push_result(SQL(
                        "%s (SELECT 1 FROM %s AS %s WHERE %s = %s)",
                        sql_exists,
                        SQL.identifier(rel_table),
                        SQL.identifier(rel_alias),
                        SQL.identifier(rel_alias, rel_id1),
                        SQL.identifier(alias, 'id'),
                    ))

            elif field.type == 'many2one':
                if operator in HIERARCHY_FUNCS:
                    ids2 = to_ids(right, comodel, leaf)
                    if field.comodel_name != model._name:
                        dom = HIERARCHY_FUNCS[operator](left, ids2, comodel, prefix=field.comodel_name)
                    else:
                        dom = HIERARCHY_FUNCS[operator]('id', ids2, model, parent=left)
                    for dom_leaf in dom:
                        push(dom_leaf, model, alias)

                elif (
                    isinstance(right, str)
                    or isinstance(right, (tuple, list)) and right and all(isinstance(item, str) for item in right)
                ):
                    # resolve string-based m2o criterion into IDs subqueries

                    # Special treatment to ill-formed domains
                    operator = 'in' if operator in ('<', '>', '<=', '>=') else operator
                    dict_op = {'not in': '!=', 'in': '=', '=': 'in', '!=': 'not in'}
                    if isinstance(right, tuple):
                        right = list(right)
                    if not isinstance(right, list) and operator in ('not in', 'in'):
                        operator = dict_op[operator]
                    elif isinstance(right, list) and operator in ('!=', '='):  # for domain (FIELD,'=',['value1','value2'])
                        operator = dict_op[operator]
                    res_ids = comodel.with_context(active_test=False)._name_search(right, [], operator)
                    if operator in NEGATIVE_TERM_OPERATORS:
                        for dom_leaf in ('|', (left, 'in', res_ids), (left, '=', False)):
                            push(dom_leaf, model, alias)
                    else:
                        push((left, 'in', res_ids), model, alias)

                else:
                    # right == [] or right == False and all other cases are handled by __leaf_to_sql()
                    push_result(self.__leaf_to_sql(leaf, model, alias))

            # -------------------------------------------------
            # BINARY FIELDS STORED IN ATTACHMENT
            # -> check for null only
            # -------------------------------------------------

            elif field.type == 'binary' and field.attachment:
                if operator in ('=', '!=') and not right:
                    sub_op = 'in' if operator in NEGATIVE_TERM_OPERATORS else 'not in'
                    sql = SQL(
                        "(SELECT res_id FROM ir_attachment WHERE res_model = %s AND res_field = %s)",
                        model._name, left,
                    )
                    push(('id', sub_op, sql), model, alias)
                else:
                    _logger.error("Binary field '%s' stored in attachment: ignore %s %s %s",
                                  field.string, left, operator, reprlib.repr(right))
                    push(TRUE_LEAF, model, alias)

            # -------------------------------------------------
            # OTHER FIELDS
            # -> datetime fields: manage time part of the datetime
            #    column when it is not there
            # -> manage translatable fields
            # -------------------------------------------------

            else:
                if field.type == 'datetime' and right:
                    if isinstance(right, str) and len(right) == 10:
                        if operator in ('>', '<='):
                            right += ' 23:59:59'
                        else:
                            right += ' 00:00:00'
                        push((left, operator, right), model, alias)
                    elif isinstance(right, date) and not isinstance(right, datetime):
                        if operator in ('>', '<='):
                            right = datetime.combine(right, time.max)
                        else:
                            right = datetime.combine(right, time.min)
                        push((left, operator, right), model, alias)
                    else:
                        push_result(self.__leaf_to_sql(leaf, model, alias))

                elif field.translate and isinstance(right, str) and left == field.name:
                    model_raw_trans = model.with_context(prefetch_langs=True)
                    sql_field = model_raw_trans._field_to_sql(alias, field.name, self.query)
                    sql_operator = SQL_OPERATORS[operator]
                    sql_exprs = []

                    need_wildcard = operator in ('like', 'ilike', 'not like', 'not ilike')
                    if not need_wildcard:
                        right = field.convert_to_column(right, model, validate=False).adapted['en_US']

                    if (need_wildcard and not right) or (right and operator in NEGATIVE_TERM_OPERATORS):
                        sql_exprs.append(SQL("%s IS NULL OR", sql_field))

                    if self._has_trigram and field.index == 'trigram' and operator in ('=', 'like', 'ilike', '=like', '=ilike'):
                        # a prefilter using trigram index to speed up '=', 'like', 'ilike'
                        # '!=', '<=', '<', '>', '>=', 'in', 'not in', 'not like', 'not ilike' cannot use this trick
                        if operator == '=':
                            _right = value_to_translated_trigram_pattern(right)
                        else:
                            _right = pattern_to_translated_trigram_pattern(right)

                        if _right != '%':
                            _unaccent = self._unaccent(field)
                            _left = SQL("jsonb_path_query_array(%s, '$.*')::text", sql_field)
                            _sql_operator = SQL('LIKE') if operator == '=' else sql_operator
                            sql_exprs.append(SQL(
                                "%s %s %s AND",
                                _unaccent(_left),
                                _sql_operator,
                                _unaccent(SQL("%s", _right))
                            ))

                    unaccent = self._unaccent(field) if operator.endswith('ilike') else lambda x: x
                    sql_left = model._field_to_sql(alias, field.name, self.query)

                    if need_wildcard:
                        right = f'%{right}%'

                    sql_exprs.append(SQL(
                        "%s %s %s",
                        unaccent(sql_left),
                        sql_operator,
                        unaccent(SQL("%s", right)),
                    ))
                    push_result(SQL("(%s)", SQL(" ").join(sql_exprs)))

                elif field.translate and operator in ['in', 'not in'] and isinstance(right, (list, tuple)) and left == field.name:
                    model_raw_trans = model.with_context(prefetch_langs=True)
                    sql_field = model_raw_trans._field_to_sql(alias, field.name, self.query)
                    sql_operator = SQL_OPERATORS[operator]
                    params = [it for it in right if it is not False and it is not None]
                    check_null = len(params) < len(right)
                    if params:
                        params = [field.convert_to_column(p, model, validate=False).adapted['en_US'] for p in params]
                        langs = field.get_translation_fallback_langs(model.env)
                        sql_left_langs = [SQL("%s->>%s", sql_field, lang) for lang in langs]
                        if len(sql_left_langs) == 1:
                            sql_left = sql_left_langs[0]
                        else:
                            sql_left = SQL('COALESCE(%s)', SQL(', ').join(sql_left_langs))
                        sql = SQL("%s %s %s", sql_left, sql_operator, tuple(params))
                    else:
                        # The case for (left, 'in', []) or (left, 'not in', []).
                        sql = SQL("FALSE") if operator == 'in' else SQL("TRUE")
                    if (operator == 'in' and check_null) or (operator == 'not in' and not check_null):
                        sql = SQL("(%s OR %s IS NULL)", sql, sql_field)
                    elif operator == 'not in' and check_null:
                        sql = SQL("(%s AND %s IS NOT NULL)", sql, sql_field)  # needed only for TRUE.
                    push_result(sql)

                else:
                    push_result(self.__leaf_to_sql(leaf, model, alias))

        # ----------------------------------------
        # END OF PARSING FULL DOMAIN
        # -> put result in self.result and self.query
        # ----------------------------------------

        [self.result] = result_stack
        self.query.add_where(self.result)

    def __leaf_to_sql(self, leaf: tuple, model: BaseModel, alias: str) -> SQL:
        left, operator, right = leaf

        # final sanity checks - should never fail
        assert operator in (TERM_OPERATORS + ('inselect', 'not inselect')), \
            "Invalid operator %r in domain term %r" % (operator, leaf)
        assert leaf in (TRUE_LEAF, FALSE_LEAF) or left in model._fields, \
            "Invalid field %r in domain term %r" % (left, leaf)
        assert not isinstance(right, BaseModel), \
            "Invalid value %r in domain term %r" % (right, leaf)

        if leaf == TRUE_LEAF:
            return SQL("TRUE")

        if leaf == FALSE_LEAF:
            return SQL("FALSE")

        field = model._fields[left]
        sql_field = model._field_to_sql(alias, left, self.query)

        if operator == 'inselect':
            subquery, subparams = right
            return SQL("(%s IN (%s))", sql_field, SQL(subquery, *subparams))

        if operator == 'not inselect':
            subquery, subparams = right
            return SQL("(%s NOT IN (%s))", sql_field, SQL(subquery, *subparams))

        if operator == '=?':
            if right is False or right is None:
                # '=?' is a short-circuit that makes the term TRUE if right is None or False
                return SQL("TRUE")
            else:
                # '=?' behaves like '=' in other cases
                return self.__leaf_to_sql((left, '=', right), model, alias)

        sql_operator = SQL_OPERATORS[operator]

        if operator in ('in', 'not in'):
            # Two cases: right is a boolean or a list. The boolean case is an
            # abuse and handled for backward compatibility.
            if isinstance(right, bool):
                _logger.warning("The domain term '%s' should use the '=' or '!=' operator." % (leaf,))
                if (operator == 'in' and right) or (operator == 'not in' and not right):
                    return SQL("(%s IS NOT NULL)", sql_field)
                else:
                    return SQL("(%s IS NULL)", sql_field)

            elif isinstance(right, SQL):
                return SQL("(%s %s %s)", sql_field, sql_operator, right)

            elif isinstance(right, Query):
                return SQL("(%s %s %s)", sql_field, sql_operator, right.subselect())

            elif isinstance(right, (list, tuple)):
                if field.type == "boolean":
                    params = [it for it in (True, False) if it in right]
                    check_null = False in right
                else:
                    params = [it for it in right if it is not False and it is not None]
                    check_null = len(params) < len(right)

                if params:
                    if left != 'id':
                        params = [field.convert_to_column(p, model, validate=False) for p in params]
                    sql = SQL("(%s %s %s)", sql_field, sql_operator, tuple(params))
                else:
                    # The case for (left, 'in', []) or (left, 'not in', []).
                    sql = SQL("FALSE") if operator == 'in' else SQL("TRUE")

                if (operator == 'in' and check_null) or (operator == 'not in' and not check_null):
                    sql = SQL("(%s OR %s IS NULL)", sql, sql_field)
                elif operator == 'not in' and check_null:
                    sql = SQL("(%s AND %s IS NOT NULL)", sql, sql_field)  # needed only for TRUE
                return sql

            else:  # Must not happen
                raise ValueError(f"Invalid domain term {leaf!r}")

        if field.type == 'boolean' and operator in ('=', '!=') and isinstance(right, bool):
            value = (not right) if operator in NEGATIVE_TERM_OPERATORS else right
            if value:
                return SQL("(%s = TRUE)", sql_field)
            else:
                return SQL("(%s IS NULL OR %s = FALSE)", sql_field, sql_field)

        if operator == '=' and (right is False or right is None):
            return SQL("%s IS NULL", sql_field)

        if operator == '!=' and (right is False or right is None):
            return SQL("%s IS NOT NULL", sql_field)

        # general case
        need_wildcard = operator in ('like', 'ilike', 'not like', 'not ilike')

        if isinstance(right, SQL):
            sql_right = right
        elif need_wildcard:
            sql_right = SQL("%s", f"%{pycompat.to_text(right)}%")
        else:
            sql_right = SQL("%s", field.convert_to_column(right, model, validate=False))

        sql_left = sql_field
        if operator.endswith('like'):
            sql_left = SQL("%s::text", sql_field)
        if operator.endswith('ilike'):
            unaccent = self._unaccent(field)
            sql_left = unaccent(sql_left)
            sql_right = unaccent(sql_right)

        sql = SQL("(%s %s %s)", sql_left, sql_operator, sql_right)

        if (need_wildcard and not right) or (right and operator in NEGATIVE_TERM_OPERATORS):
            sql = SQL("(%s OR %s IS NULL)", sql, sql_field)

        return sql
