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

Odoo will use the SQL function 'unaccent' when available for the
'ilike', 'not ilike' and '=ilike' operators, and enabled in the configuration.

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
import logging
import warnings

import odoo.orm.domains as orm_domains
import odoo.modules
from odoo.tools import Query, SQL

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
TERM_OPERATORS = set(orm_domains.CONDITION_OPERATORS)

# A subset of the above operators, with a 'negative' semantic. When the
# expressions 'in NEGATIVE_TERM_OPERATORS' or 'not in NEGATIVE_TERM_OPERATORS' are used in the code
# below, this doesn't necessarily mean that any of those NEGATIVE_TERM_OPERATORS is
# legal in the processed term.
NEGATIVE_TERM_OPERATORS = set(orm_domains.NEGATIVE_CONDITION_OPERATORS)

# Negation of domain expressions
TERM_OPERATORS_NEGATION = orm_domains._INVERSE_OPERATOR

TRUE_LEAF = orm_domains._TRUE_LEAF
FALSE_LEAF = orm_domains._FALSE_LEAF

TRUE_DOMAIN = [TRUE_LEAF]
FALSE_DOMAIN = [FALSE_LEAF]

_logger = logging.getLogger(__name__)


# --------------------------------------------------
# Generic domain manipulation
# --------------------------------------------------

def normalize_domain(domain):
    """Returns a normalized version of ``domain_expr``, where all implicit '&' operators
       have been made explicit. One property of normalized domain expressions is that they
       can be easily combined together as if they were single domain components.
    """
    # TODO deprecate use Domain()
    if isinstance(domain, orm_domains.Domain):
        # already normalized
        return list(domain)
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
            if len(token) == 3 and token[1] in ('any', 'not any') and not isinstance(token[2], (Query, SQL)):
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
    warnings.warn("Use Domain().is_false()", DeprecationWarning)
    return orm_domains.Domain(domain).is_false()


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
    for domain in domains:
        domain = normalize_domain(domain)
        if domain == unit:
            continue
        if domain == zero:
            return zero
        result += domain
        count += 1
    result = [operator] * (count - 1) + result
    return result or unit


def AND(domains):
    """AND([D1,D2,...]) returns a domain representing D1 and D2 and ... """
    # TODO deprecate and use Domain.AND(domains)
    # (note: used in migrations)
    return combine(AND_OPERATOR, [TRUE_LEAF], [FALSE_LEAF], domains)


def OR(domains):
    """OR([D1,D2,...]) returns a domain representing D1 or D2 or ... """
    # TODO deprecate and use Domain.OR(domains)
    return combine(OR_OPERATOR, [FALSE_LEAF], [TRUE_LEAF], domains)


def distribute_not(domain):
    """ Distribute any '!' domain operators found inside a normalized domain.

    Because we don't use SQL semantic for processing a 'left not in right'
    query (i.e. our 'not in' is not simply translated to a SQL 'not in'),
    it means that a '! left in right' can not be simply processed
    by model._condition_to_sql by first emitting code for 'left in right' then wrapping
    the result with 'not (...)', as it would result in a 'not in' at the SQL
    level.

    This function is thus responsible for pushing any '!' domain operators
    inside the terms themselves. For example::

         ['!','&',('user_id','=',4),('partner_id','in',[1,2])]
            will be turned into:
         ['|',('user_id','!=',4),('partner_id','not in',[1,2])]

    """
    # TODO warnings.warn("Use Domain() instead of distribute_not()", DeprecationWarning)
    return list(orm_domains.Domain(domain))


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
            raise ValueError(f"Invalid field {path[0]!r} on {model._name} in leaf {item}")
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
    if tree[0] == '=?':
        # already update operator '=?' here, so that '!' is distributed correctly
        assert len(tree) == 3
        if tree[2]:
            tree = ('=', tree[1], tree[2])
        else:
            return ('?', False)
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

    # TODO deprecate
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
    # TODO deprecate
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
    # TODO deprecate
    return isinstance(element, str) and element in DOMAIN_OPERATORS


def is_leaf(element):
    """ Test whether an object is a valid domain term:

        - is a list or tuple
        - with 3 elements
        - second element if a valid op

        :param tuple element: a leaf in form (left, operator, right)

        Note: OLD TODO change the share wizard to use this function.
    """
    # TODO deprecate
    INTERNAL_OPS = TERM_OPERATORS | {'<>'}
    return (isinstance(element, tuple) or isinstance(element, list)) \
        and len(element) == 3 \
        and element[1] in INTERNAL_OPS \
        and ((isinstance(element[0], str) and element[0])
             or tuple(element) in (TRUE_LEAF, FALSE_LEAF))


def is_boolean(element):
    # TODO deprecate
    return element == TRUE_LEAF or element == FALSE_LEAF


def check_leaf(element):
    # TODO deprecate
    if not is_operator(element) and not is_leaf(element):
        raise ValueError("Invalid leaf %s" % str(element))


# --------------------------------------------------
# SQL utils
# --------------------------------------------------

def get_unaccent_wrapper(cr):
    warnings.warn(
        "Since 18.0, deprecated method, use env.registry.unaccent instead",
        DeprecationWarning, stacklevel=2,
    )
    return odoo.modules.registry.Registry(cr.dbname).unaccent


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
        warnings.warn("Since 19.0, expression() is deprecated, use Domain or _where_calc instead", DeprecationWarning)
        self._unaccent = model.pool.unaccent
        self._has_trigram = model.pool.has_trigram
        self.root_model = model
        self.root_alias = alias or model._table

        # normalize and prepare the expression for parsing
        domain = orm_domains.Domain(domain)
        domain = domain._optimize(self.root_model)
        self.expression = domain

        # this object handles all the joins
        if query is None:
            query = Query(self.root_model, self.root_alias, self.root_model._table_sql)
        self.query = query

        # parse the domain expression
        self.result = result = domain._to_sql(self.root_model, self.root_alias, query)
        query.add_where(result)

    # ----------------------------------------
    # Parsing
    # ----------------------------------------

    def parse(self):
        raise NotImplementedError
