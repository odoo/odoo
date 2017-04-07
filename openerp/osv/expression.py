# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

""" Domain expression processing

The main duty of this module is to compile a domain expression into a
SQL query. A lot of things should be documented here, but as a first
step in the right direction, some tests in test_osv_expression.yml
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

import logging
import traceback
from zlib import crc32

import openerp.modules
from . import fields
from .. import SUPERUSER_ID
from ..models import MAGIC_COLUMNS, BaseModel
import openerp.tools as tools


# Domain operators.
NOT_OPERATOR = '!'
OR_OPERATOR = '|'
AND_OPERATOR = '&'
DOMAIN_OPERATORS = (NOT_OPERATOR, OR_OPERATOR, AND_OPERATOR)

# List of available term operators. It is also possible to use the '<>'
# operator, which is strictly the same as '!='; the later should be prefered
# for consistency. This list doesn't contain '<>' as it is simpified to '!='
# by the normalize_operator() function (so later part of the code deals with
# only one representation).
# Internals (i.e. not available to the user) 'inselect' and 'not inselect'
# operators are also used. In this case its right operand has the form (subselect, params).
TERM_OPERATORS = ('=', '!=', '<=', '<', '>', '>=', '=?', '=like', '=ilike',
                  'like', 'not like', 'ilike', 'not ilike', 'in', 'not in',
                  'child_of')

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
}

TRUE_LEAF = (1, '=', 1)
FALSE_LEAF = (0, '=', 1)

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
    assert isinstance(domain, (list, tuple)), "Domains to normalize must have a 'domain' form: a list or tuple of domain components"
    if not domain:
        return TRUE_DOMAIN
    result = []
    expected = 1                            # expected number of expressions
    op_arity = {NOT_OPERATOR: 1, AND_OPERATOR: 2, OR_OPERATOR: 2}
    for token in domain:
        if expected == 0:                   # more than expected, like in [A, B]
            result[0:0] = [AND_OPERATOR]             # put an extra '&' in front
            expected = 1
        result.append(token)
        if isinstance(token, (list, tuple)):  # domain term
            expected -= 1
        else:
            expected += op_arity.get(token, 0) - 1
    assert expected == 0, 'This domain is syntactically not correct: %s' % (domain)
    return result


def combine(operator, unit, zero, domains):
    """Returns a new domain expression where all domain components from ``domains``
       have been added together using the binary operator ``operator``. The given
       domains must be normalized.

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
        if domain == unit:
            continue
        if domain == zero:
            return zero
        if domain:
            result += domain
            count += 1
    result = [operator] * (count - 1) + result
    return result


def AND(domains):
    """AND([D1,D2,...]) returns a domain representing D1 and D2 and ... """
    return combine(AND_OPERATOR, TRUE_DOMAIN, FALSE_DOMAIN, domains)


def OR(domains):
    """OR([D1,D2,...]) returns a domain representing D1 or D2 or ... """
    return combine(OR_OPERATOR, FALSE_DOMAIN, TRUE_DOMAIN, domains)


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


# --------------------------------------------------
# Generic leaf manipulation
# --------------------------------------------------

def _quote(to_quote):
    if '"' not in to_quote:
        return '"%s"' % to_quote
    return to_quote


def generate_table_alias(src_table_alias, joined_tables=[]):
    """ Generate a standard table alias name. An alias is generated as following:
        - the base is the source table name (that can already be an alias)
        - then, each joined table is added in the alias using a 'link field name'
          that is used to render unique aliases for a given path
        - returns a tuple composed of the alias, and the full table alias to be
          added in a from condition with quoting done
        Examples:
        - src_table_alias='res_users', join_tables=[]:
            alias = ('res_users','"res_users"')
        - src_model='res_users', join_tables=[(res.partner, 'parent_id')]
            alias = ('res_users__parent_id', '"res_partner" as "res_users__parent_id"')

        :param model src_table_alias: model source of the alias
        :param list joined_tables: list of tuples
                                   (dst_model, link_field)

        :return tuple: (table_alias, alias statement for from clause with quotes added)
    """
    alias = src_table_alias
    if not joined_tables:
        return '%s' % alias, '%s' % _quote(alias)
    for link in joined_tables:
        alias += '__' + link[1]
    # Use an alternate alias scheme if length exceeds the PostgreSQL limit
    # of 63 characters.
    if len(alias) >= 64:
        # We have to fit a crc32 hash and one underscore
        # into a 63 character alias. The remaining space we can use to add
        # a human readable prefix.
        alias_hash = hex(crc32(alias))[2:]
        ALIAS_PREFIX_LENGTH = 63 - len(alias_hash) - 1
        alias = "%s_%s" % (
            alias[:ALIAS_PREFIX_LENGTH], alias_hash)
    return '%s' % alias, '%s as %s' % (_quote(joined_tables[-1][0]), _quote(alias))


def get_alias_from_query(from_query):
    """ :param string from_query: is something like :
        - '"res_partner"' OR
        - '"res_partner" as "res_users__partner_id"''
    """
    from_splitted = from_query.split(' as ')
    if len(from_splitted) > 1:
        return from_splitted[0].replace('"', ''), from_splitted[1].replace('"', '')
    else:
        return from_splitted[0].replace('"', ''), from_splitted[0].replace('"', '')


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
    return isinstance(element, basestring) and element in DOMAIN_OPERATORS


def is_leaf(element, internal=False):
    """ Test whether an object is a valid domain term:
        - is a list or tuple
        - with 3 elements
        - second element if a valid op

        :param tuple element: a leaf in form (left, operator, right)
        :param boolean internal: allow or not the 'inselect' internal operator
            in the term. This should be always left to False.

        Note: OLD TODO change the share wizard to use this function.
    """
    INTERNAL_OPS = TERM_OPERATORS + ('<>',)
    if internal:
        INTERNAL_OPS += ('inselect', 'not inselect')
    return (isinstance(element, tuple) or isinstance(element, list)) \
        and len(element) == 3 \
        and element[1] in INTERNAL_OPS \
        and ((isinstance(element[0], basestring) and element[0])
             or tuple(element) in (TRUE_LEAF, FALSE_LEAF))


# --------------------------------------------------
# SQL utils
# --------------------------------------------------

def select_from_where(cr, select_field, from_table, where_field, where_ids, where_operator):
    # todo: merge into parent query as sub-query
    res = []
    if where_ids:
        if where_operator in ['<', '>', '>=', '<=']:
            cr.execute('SELECT "%s" FROM "%s" WHERE "%s" %s %%s' % \
                (select_field, from_table, where_field, where_operator),
                (where_ids[0],))  # TODO shouldn't this be min/max(where_ids) ?
            res = [r[0] for r in cr.fetchall()]
        else:  # TODO where_operator is supposed to be 'in'? It is called with child_of...
            for i in range(0, len(where_ids), cr.IN_MAX):
                subids = where_ids[i:i + cr.IN_MAX]
                cr.execute('SELECT "%s" FROM "%s" WHERE "%s" IN %%s' % \
                    (select_field, from_table, where_field), (tuple(subids),))
                res.extend([r[0] for r in cr.fetchall()])
    return res


def select_distinct_from_where_not_null(cr, select_field, from_table):
    cr.execute('SELECT distinct("%s") FROM "%s" where "%s" is not null' % (select_field, from_table, select_field))
    return [r[0] for r in cr.fetchall()]

def get_unaccent_wrapper(cr):
    if openerp.modules.registry.RegistryManager.get(cr.dbname).has_unaccent:
        return lambda x: "unaccent(%s)" % (x,)
    return lambda x: x

# --------------------------------------------------
# ExtendedLeaf class for managing leafs and contexts
# -------------------------------------------------

class ExtendedLeaf(object):
    """ Class wrapping a domain leaf, and giving some services and management
        features on it. In particular it managed join contexts to be able to
        construct queries through multiple models.
    """

    # --------------------------------------------------
    # Join / Context manipulation
    #   running examples:
    #   - res_users.name, like, foo: name is on res_partner, not on res_users
    #   - res_partner.bank_ids.name, like, foo: bank_ids is a one2many with _auto_join
    #   - res_partner.state_id.name, like, foo: state_id is a many2one with _auto_join
    # A join:
    #   - link between src_table and dst_table, using src_field and dst_field
    #       i.e.: inherits: res_users.partner_id = res_partner.id
    #       i.e.: one2many: res_partner.id = res_partner_bank.partner_id
    #       i.e.: many2one: res_partner.state_id = res_country_state.id
    #   - done in the context of a field
    #       i.e.: inherits: 'partner_id'
    #       i.e.: one2many: 'bank_ids'
    #       i.e.: many2one: 'state_id'
    #   - table names use aliases: initial table followed by the context field
    #     names, joined using a '__'
    #       i.e.: inherits: res_partner as res_users__partner_id
    #       i.e.: one2many: res_partner_bank as res_partner__bank_ids
    #       i.e.: many2one: res_country_state as res_partner__state_id
    #   - join condition use aliases
    #       i.e.: inherits: res_users.partner_id = res_users__partner_id.id
    #       i.e.: one2many: res_partner.id = res_partner__bank_ids.parr_id
    #       i.e.: many2one: res_partner.state_id = res_partner__state_id.id
    # Variables explanation:
    #   - src_table: working table before the join
    #       -> res_users, res_partner, res_partner
    #   - dst_table: working table after the join
    #       -> res_partner, res_partner_bank, res_country_state
    #   - src_table_link_name: field name used to link the src table, not
    #     necessarily a field (because 'id' is not a field instance)
    #       i.e.: inherits: 'partner_id', found in the inherits of the current table
    #       i.e.: one2many: 'id', not a field
    #       i.e.: many2one: 'state_id', the current field name
    #   - dst_table_link_name: field name used to link the dst table, not
    #     necessarily a field (because 'id' is not a field instance)
    #       i.e.: inherits: 'id', not a field
    #       i.e.: one2many: 'partner_id', _fields_id of the current field
    #       i.e.: many2one: 'id', not a field
    #   - context_field_name: field name used as a context to make the alias
    #       i.e.: inherits: 'partner_id': found in the inherits of the current table
    #       i.e.: one2many: 'bank_ids': current field name
    #       i.e.: many2one: 'state_id': current field name
    # --------------------------------------------------

    def __init__(self, leaf, model, join_context=None, internal=False):
        """ Initialize the ExtendedLeaf

            :attr [string, tuple] leaf: operator or tuple-formatted domain
                expression
            :attr obj model: current working model
            :attr list _models: list of chained models, updated when
                adding joins
            :attr list join_context: list of join contexts. This is a list of
                tuples like ``(lhs, table, lhs_col, col, link)``

                where

                lhs
                    source (left hand) model
                model
                    destination (right hand) model
                lhs_col
                    source model column for join condition
                col
                    destination model column for join condition
                link
                    link column between source and destination model
                    that is not necessarily (but generally) a real column used
                    in the condition (i.e. in many2one); this link is used to
                    compute aliases
        """
        assert isinstance(model, BaseModel), 'Invalid leaf creation without table'
        self.join_context = join_context or []
        self.leaf = leaf
        # normalize the leaf's operator
        self.normalize_leaf()
        # set working variables; handle the context stack and previous tables
        self.model = model
        self._models = []
        for item in self.join_context:
            self._models.append(item[0])
        self._models.append(model)
        # check validity
        self.check_leaf(internal)

    def __str__(self):
        return '<osv.ExtendedLeaf: %s on %s (ctx: %s)>' % (str(self.leaf), self.model._table, ','.join(self._get_context_debug()))

    def generate_alias(self):
        links = [(context[1]._table, context[4]) for context in self.join_context]
        alias, alias_statement = generate_table_alias(self._models[0]._table, links)
        return alias

    def add_join_context(self, model, lhs_col, table_col, link):
        """ See above comments for more details. A join context is a tuple like:
                ``(lhs, model, lhs_col, col, link)``

            After adding the join, the model of the current leaf is updated.
        """
        self.join_context.append((self.model, model, lhs_col, table_col, link))
        self._models.append(model)
        self.model = model

    def get_join_conditions(self):
        conditions = []
        alias = self._models[0]._table
        for context in self.join_context:
            previous_alias = alias
            alias += '__' + context[4]
            conditions.append('"%s"."%s"="%s"."%s"' % (previous_alias, context[2], alias, context[3]))
        return conditions

    def get_tables(self):
        tables = set()
        links = []
        for context in self.join_context:
            links.append((context[1]._table, context[4]))
            alias, alias_statement = generate_table_alias(self._models[0]._table, links)
            tables.add(alias_statement)
        return tables

    def _get_context_debug(self):
        names = ['"%s"."%s"="%s"."%s" (%s)' % (item[0]._table, item[2], item[1]._table, item[3], item[4]) for item in self.join_context]
        return names

    # --------------------------------------------------
    # Leaf manipulation
    # --------------------------------------------------

    def check_leaf(self, internal=False):
        """ Leaf validity rules:
            - a valid leaf is an operator or a leaf
            - a valid leaf has a field objects unless
                - it is not a tuple
                - it is an inherited field
                - left is id, operator is 'child_of'
                - left is in MAGIC_COLUMNS
        """
        if not is_operator(self.leaf) and not is_leaf(self.leaf, internal):
            raise ValueError("Invalid leaf %s" % str(self.leaf))

    def is_operator(self):
        return is_operator(self.leaf)

    def is_true_leaf(self):
        return self.leaf == TRUE_LEAF

    def is_false_leaf(self):
        return self.leaf == FALSE_LEAF

    def is_leaf(self, internal=False):
        return is_leaf(self.leaf, internal=internal)

    def normalize_leaf(self):
        self.leaf = normalize_leaf(self.leaf)
        return True

def create_substitution_leaf(leaf, new_elements, new_model=None, internal=False):
    """ From a leaf, create a new leaf (based on the new_elements tuple
        and new_model), that will have the same join context. Used to
        insert equivalent leafs in the processing stack. """
    if new_model is None:
        new_model = leaf.model
    new_join_context = [tuple(context) for context in leaf.join_context]
    new_leaf = ExtendedLeaf(new_elements, new_model, join_context=new_join_context, internal=internal)
    return new_leaf

class expression(object):
    """ Parse a domain expression
        Use a real polish notation
        Leafs are still in a ('foo', '=', 'bar') format
        For more info: http://christophe-simonis-at-tiny.blogspot.com/2008/08/new-new-domain-notation.html
    """

    def __init__(self, cr, uid, exp, table, context):
        """ Initialize expression object and automatically parse the expression
            right after initialization.

            :param exp: expression (using domain ('foo', '=', 'bar' format))
            :param table: root model

            :attr list result: list that will hold the result of the parsing
                as a list of ExtendedLeaf
            :attr list joins: list of join conditions, such as
                (res_country_state."id" = res_partner."state_id")
            :attr root_model: base model for the query
            :attr list expression: the domain expression, that will be normalized
                and prepared
        """
        self._unaccent = get_unaccent_wrapper(cr)
        self.joins = []
        self.root_model = table

        # normalize and prepare the expression for parsing
        self.expression = distribute_not(normalize_domain(exp))

        # parse the domain expression
        self.parse(cr, uid, context=context)

    # ----------------------------------------
    # Leafs management
    # ----------------------------------------

    def get_tables(self):
        """ Returns the list of tables for SQL queries, like select from ... """
        tables = []
        for leaf in self.result:
            for table in leaf.get_tables():
                if table not in tables:
                    tables.append(table)
        table_name = _quote(self.root_model._table)
        if table_name not in tables:
            tables.append(table_name)
        return tables

    # ----------------------------------------
    # Parsing
    # ----------------------------------------

    def parse(self, cr, uid, context):
        """ Transform the leaves of the expression

            The principle is to pop elements from a leaf stack one at a time.
            Each leaf is processed. The processing is a if/elif list of various
            cases that appear in the leafs (many2one, function fields, ...).
            Two things can happen as a processing result:
            - the leaf has been modified and/or new leafs have to be introduced
              in the expression; they are pushed into the leaf stack, to be
              processed right after
            - the leaf is added to the result

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

        def to_ids(value, comodel, context=None, limit=None):
            """ Normalize a single id or name, or a list of those, into a list of ids
                :param {int,long,basestring,list,tuple} value:
                    if int, long -> return [value]
                    if basestring, convert it into a list of basestrings, then
                    if list of basestring ->
                        perform a name_search on comodel for each name
                        return the list of related ids
            """
            names = []
            if isinstance(value, basestring):
                names = [value]
            elif value and isinstance(value, (tuple, list)) and all(isinstance(item, basestring) for item in value):
                names = value
            elif isinstance(value, (int, long)):
                return [value]
            if names:
                name_get_list = [name_get[0] for name in names for name_get in comodel.name_search(cr, uid, name, [], 'ilike', context=context, limit=limit)]
                return list(set(name_get_list))
            return list(value)

        def child_of_domain(left, ids, left_model, parent=None, prefix='', context=None):
            """ Return a domain implementing the child_of operator for [(left,child_of,ids)],
                either as a range using the parent_left/right tree lookup fields
                (when available), or as an expanded [(left,in,child_ids)] """
            if not ids:
                return FALSE_DOMAIN
            if left_model._parent_store and (not left_model.pool._init):
                # TODO: Improve where joins are implemented for many with '.', replace by:
                # doms += ['&',(prefix+'.parent_left','<',o.parent_right),(prefix+'.parent_left','>=',o.parent_left)]
                doms = []
                for o in left_model.browse(cr, uid, ids, context=context):
                    if doms:
                        doms.insert(0, OR_OPERATOR)
                    doms += [AND_OPERATOR, ('parent_left', '<', o.parent_right), ('parent_left', '>=', o.parent_left)]
                if prefix:
                    return [(left, 'in', left_model.search(cr, uid, doms, context=context))]
                return doms
            else:
                def recursive_children(ids, model, parent_field):
                    if not ids:
                        return []
                    ids2 = model.search(cr, uid, [(parent_field, 'in', ids)], context=context)
                    return ids + recursive_children(ids2, model, parent_field)
                return [(left, 'in', recursive_children(ids, left_model, parent or left_model._parent_name))]

        def pop():
            """ Pop a leaf to process. """
            return self.stack.pop()

        def push(leaf):
            """ Push a leaf to be processed right after. """
            self.stack.append(leaf)

        def push_result(leaf):
            """ Push a leaf to the results. This leaf has been fully processed
                and validated. """
            self.result.append(leaf)

        self.result = []
        self.stack = [ExtendedLeaf(leaf, self.root_model) for leaf in self.expression]
        # process from right to left; expression is from left to right
        self.stack.reverse()

        while self.stack:
            # Get the next leaf to process
            leaf = pop()

            # Get working variables
            if leaf.is_operator():
                left, operator, right = leaf.leaf, None, None
            elif leaf.is_true_leaf() or leaf.is_false_leaf():
                # because we consider left as a string
                left, operator, right = ('%s' % leaf.leaf[0], leaf.leaf[1], leaf.leaf[2])
            else:
                left, operator, right = leaf.leaf
            path = left.split('.', 1)

            model = leaf.model
            field = model._fields.get(path[0])
            column = model._columns.get(path[0])
            comodel = model.pool.get(getattr(field, 'comodel_name', None))

            # ----------------------------------------
            # SIMPLE CASE
            # 1. leaf is an operator
            # 2. leaf is a true/false leaf
            # -> add directly to result
            # ----------------------------------------

            if leaf.is_operator() or leaf.is_true_leaf() or leaf.is_false_leaf():
                push_result(leaf)

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

            elif not column and path[0] in model._inherit_fields:
                # comments about inherits'd fields
                #  { 'field_name': ('parent_model', 'm2o_field_to_reach_parent',
                #                    field_column_obj, origina_parent_model), ... }
                next_model = model.pool[model._inherit_fields[path[0]][0]]
                leaf.add_join_context(next_model, model._inherits[next_model._name], 'id', model._inherits[next_model._name])
                push(leaf)

            elif left == 'id' and operator == 'child_of':
                ids2 = to_ids(right, model, context)
                dom = child_of_domain(left, ids2, model)
                for dom_leaf in reversed(dom):
                    new_leaf = create_substitution_leaf(leaf, dom_leaf, model)
                    push(new_leaf)

            elif not column and path[0] in MAGIC_COLUMNS:
                push_result(leaf)

            elif not field:
                raise ValueError("Invalid field %r in leaf %r" % (left, str(leaf)))

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

            elif len(path) > 1 and column and column._type == 'many2one' and column._auto_join:
                # res_partner.state_id = res_partner__state_id.id
                leaf.add_join_context(comodel, path[0], 'id', path[0])
                push(create_substitution_leaf(leaf, (path[1], operator, right), comodel))

            elif len(path) > 1 and column and column._type == 'one2many' and column._auto_join:
                # res_partner.id = res_partner__bank_ids.partner_id
                leaf.add_join_context(comodel, 'id', column._fields_id, path[0])
                domain = column._domain(model) if callable(column._domain) else column._domain
                push(create_substitution_leaf(leaf, (path[1], operator, right), comodel))
                if domain:
                    domain = normalize_domain(domain)
                    for elem in reversed(domain):
                        push(create_substitution_leaf(leaf, elem, comodel))
                    push(create_substitution_leaf(leaf, AND_OPERATOR, comodel))

            elif len(path) > 1 and column and column._auto_join:
                raise NotImplementedError('_auto_join attribute not supported on many2many column %s' % left)

            elif len(path) > 1 and column and column._type == 'many2one':
                right_ids = comodel.search(cr, uid, [(path[1], operator, right)], context=dict(context, active_test=False))
                leaf.leaf = (path[0], 'in', right_ids)
                push(leaf)

            # Making search easier when there is a left operand as column.o2m or column.m2m
            elif len(path) > 1 and column and column._type in ['many2many', 'one2many']:
                right_ids = comodel.search(cr, uid, [(path[1], operator, right)], context=context)
                leaf.leaf = (path[0], 'in', right_ids)
                push(leaf)

            elif not column:
                # Non-stored field should provide an implementation of search.
                if not field.search:
                    # field does not support search!
                    _logger.error("Non-stored field %s cannot be searched.", field)
                    if _logger.isEnabledFor(logging.DEBUG):
                        _logger.debug(''.join(traceback.format_stack()))
                    # Ignore it: generate a dummy leaf.
                    domain = []
                else:
                    # Let the field generate a domain.
                    if len(path) > 1:
                        right = comodel.search(
                            cr, uid, [(path[1], operator, right)],
                            context=context)
                        operator = 'in'
                    recs = model.browse(cr, uid, [], context=context)
                    domain = field.determine_domain(recs, operator, right)

                if not domain:
                    leaf.leaf = TRUE_LEAF
                    push(leaf)
                else:
                    for elem in reversed(domain):
                        push(create_substitution_leaf(leaf, elem, model))

            # -------------------------------------------------
            # FUNCTION FIELD
            # -> not stored: error if no _fnct_search, otherwise handle the result domain
            # -> stored: management done in the remaining of parsing
            # -------------------------------------------------

            elif isinstance(column, fields.function) and not column.store:
                # this is a function field that is not stored
                if not column._fnct_search:
                    _logger.error(
                        "Field '%s' (%s) can not be searched: "
                        "non-stored function field without fnct_search",
                        column.string, left)
                    # avoid compiling stack trace if not needed
                    if _logger.isEnabledFor(logging.DEBUG):
                        _logger.debug(''.join(traceback.format_stack()))
                    # ignore it: generate a dummy leaf
                    fct_domain = []
                else:
                    fct_domain = column.search(cr, uid, model, left, [leaf.leaf], context=context)

                if not fct_domain:
                    leaf.leaf = TRUE_LEAF
                    push(leaf)
                else:
                    # we assume that the expression is valid
                    # we create a dummy leaf for forcing the parsing of the resulting expression
                    for domain_element in reversed(fct_domain):
                        push(create_substitution_leaf(leaf, domain_element, model))
                    # self.push(create_substitution_leaf(leaf, TRUE_LEAF, model))
                    # self.push(create_substitution_leaf(leaf, AND_OPERATOR, model))

            # -------------------------------------------------
            # RELATIONAL FIELDS
            # -------------------------------------------------

            # Applying recursivity on field(one2many)
            elif column._type == 'one2many' and operator == 'child_of':
                ids2 = to_ids(right, comodel, context)
                if column._obj != model._name:
                    dom = child_of_domain(left, ids2, comodel, prefix=column._obj)
                else:
                    dom = child_of_domain('id', ids2, model, parent=left)
                for dom_leaf in reversed(dom):
                    push(create_substitution_leaf(leaf, dom_leaf, model))

            elif column._type == 'one2many':
                call_null = True

                if right is not False:
                    if isinstance(right, basestring):
                        op = {'!=': '=', 'not like': 'like', 'not ilike': 'ilike'}.get(operator, operator)
                        ids2 = [x[0] for x in comodel.name_search(cr, uid, right, [], op, context=context, limit=None)]
                        if ids2:
                            operator = 'not in' if operator in NEGATIVE_TERM_OPERATORS else 'in'
                    elif isinstance(right, collections.Iterable):
                        ids2 = right
                    else:
                        ids2 = [right]

                    if not ids2:
                        if operator in ['like', 'ilike', 'in', '=']:
                            #no result found with given search criteria
                            call_null = False
                            push(create_substitution_leaf(leaf, FALSE_LEAF, model))
                    else:
                        # determine ids1 <-- column._fields_id --- ids2
                        if comodel._fields[column._fields_id].store:
                            ids1 = select_from_where(cr, column._fields_id, comodel._table, 'id', ids2, operator)
                        else:
                            recs = comodel.browse(cr, SUPERUSER_ID, ids2, {'prefetch_fields': False})
                            ids1 = recs.mapped(column._fields_id).ids
                        if ids1:
                            call_null = False
                            o2m_op = 'not in' if operator in NEGATIVE_TERM_OPERATORS else 'in'
                            push(create_substitution_leaf(leaf, ('id', o2m_op, ids1), model))
                        elif operator in ('like', 'ilike', 'in', '='):
                            # no match found with positive search operator => no result (FALSE_LEAF)
                            call_null = False
                            push(create_substitution_leaf(leaf, FALSE_LEAF, model))

                if call_null:
                    o2m_op = 'in' if operator in NEGATIVE_TERM_OPERATORS else 'not in'
                    # determine ids from column._fields_id
                    if comodel._fields[column._fields_id].store:
                        ids1 = select_distinct_from_where_not_null(cr, column._fields_id, comodel._table)
                    else:
                        ids2 = comodel.search(cr, uid, [(column._fields_id, '!=', False)], context=context)
                        recs = comodel.browse(cr, SUPERUSER_ID, ids2, {'prefetch_fields': False})
                        ids1 = recs.mapped(column._fields_id).ids
                    push(create_substitution_leaf(leaf, ('id', o2m_op, ids1), model))

            elif column._type == 'many2many':
                rel_table, rel_id1, rel_id2 = column._sql_names(model)
                if operator == 'child_of':
                    ids2 = to_ids(right, comodel, context)
                    dom = child_of_domain('id', ids2, comodel)
                    ids2 = comodel.search(cr, uid, dom, context=context)
                    if comodel == model:
                        push(create_substitution_leaf(leaf, ('id', 'in', ids2), model))
                    else:
                        subquery = 'SELECT "%s" FROM "%s" WHERE "%s" IN %%s' % (rel_id1, rel_table, rel_id2)
                        # avoid flattening of argument in to_sql()
                        subquery = cr.mogrify(subquery, [tuple(ids2)])
                        push(create_substitution_leaf(leaf, ('id', 'inselect', (subquery, [])), internal=True))
                else:
                    call_null_m2m = True
                    if right is not False:
                        if isinstance(right, basestring):
                            op = {'!=': '=', 'not like': 'like', 'not ilike': 'ilike'}.get(operator, operator)
                            res_ids = [x[0] for x in comodel.name_search(cr, uid, right, [], op, context=context, limit=None)]
                            if res_ids:
                                operator = 'not in' if operator in NEGATIVE_TERM_OPERATORS else 'in'
                        else:
                            if not isinstance(right, list):
                                res_ids = [right]
                            else:
                                res_ids = right
                        if not res_ids:
                            if operator in ['like', 'ilike', 'in', '=']:
                                #no result found with given search criteria
                                call_null_m2m = False
                                push(create_substitution_leaf(leaf, FALSE_LEAF, model))
                            else:
                                operator = 'in'  # operator changed because ids are directly related to main object
                        else:
                            call_null_m2m = False
                            subop = 'not inselect' if operator in NEGATIVE_TERM_OPERATORS else 'inselect'
                            subquery = 'SELECT "%s" FROM "%s" WHERE "%s" IN %%s' % (rel_id1, rel_table, rel_id2)
                            # avoid flattening of argument in to_sql()
                            subquery = cr.mogrify(subquery, [tuple(filter(None, res_ids))])
                            push(create_substitution_leaf(leaf, ('id', subop, (subquery, [])), internal=True))

                    if call_null_m2m:
                        m2m_op = 'in' if operator in NEGATIVE_TERM_OPERATORS else 'not in'
                        push(create_substitution_leaf(leaf, ('id', m2m_op, select_distinct_from_where_not_null(cr, rel_id1, rel_table)), model))

            elif column._type == 'many2one':
                if operator == 'child_of':
                    ids2 = to_ids(right, comodel, context)
                    if column._obj != model._name:
                        dom = child_of_domain(left, ids2, comodel, prefix=column._obj)
                    else:
                        dom = child_of_domain('id', ids2, model, parent=left)
                    for dom_leaf in reversed(dom):
                        push(create_substitution_leaf(leaf, dom_leaf, model))
                else:
                    def _get_expression(comodel, cr, uid, left, right, operator, context=None):
                        if context is None:
                            context = {}
                        c = context.copy()
                        c['active_test'] = False
                        #Special treatment to ill-formed domains
                        operator = (operator in ['<', '>', '<=', '>=']) and 'in' or operator

                        dict_op = {'not in': '!=', 'in': '=', '=': 'in', '!=': 'not in'}
                        if isinstance(right, tuple):
                            right = list(right)
                        if (not isinstance(right, list)) and operator in ['not in', 'in']:
                            operator = dict_op[operator]
                        elif isinstance(right, list) and operator in ['!=', '=']:  # for domain (FIELD,'=',['value1','value2'])
                            operator = dict_op[operator]
                        res_ids = [x[0] for x in comodel.name_search(cr, uid, right, [], operator, limit=None, context=c)]
                        if operator in NEGATIVE_TERM_OPERATORS:
                            res_ids.append(False)  # TODO this should not be appended if False was in 'right'
                        return left, 'in', res_ids
                    # resolve string-based m2o criterion into IDs
                    if isinstance(right, basestring) or \
                            right and isinstance(right, (tuple, list)) and all(isinstance(item, basestring) for item in right):
                        push(create_substitution_leaf(leaf, _get_expression(comodel, cr, uid, left, right, operator, context=context), model))
                    else:
                        # right == [] or right == False and all other cases are handled by __leaf_to_sql()
                        push_result(leaf)

            # -------------------------------------------------
            # OTHER FIELDS
            # -> datetime fields: manage time part of the datetime
            #    column when it is not there
            # -> manage translatable fields
            # -------------------------------------------------

            else:
                if column._type == 'datetime' and right and len(right) == 10:
                    if operator in ('>', '<='):
                        right += ' 23:59:59'
                    else:
                        right += ' 00:00:00'
                    push(create_substitution_leaf(leaf, (left, operator, right), model))

                elif column.translate and right:
                    need_wildcard = operator in ('like', 'ilike', 'not like', 'not ilike')
                    sql_operator = {'=like': 'like', '=ilike': 'ilike'}.get(operator, operator)
                    if need_wildcard:
                        right = '%%%s%%' % right

                    inselect_operator = 'inselect'
                    if sql_operator in NEGATIVE_TERM_OPERATORS:
                        # negate operator (fix lp:1071710)
                        sql_operator = sql_operator[4:] if sql_operator[:3] == 'not' else '='
                        inselect_operator = 'not inselect'

                    unaccent = self._unaccent if sql_operator.endswith('like') else lambda x: x

                    instr = unaccent('%s')

                    if sql_operator == 'in':
                        # params will be flatten by to_sql() => expand the placeholders
                        instr = '(%s)' % ', '.join(['%s'] * len(right))

                    subselect = """WITH temp_irt_current (id, name) as (
                            SELECT ct.id, coalesce(it.value,ct.{quote_left})
                            FROM {current_table} ct
                            LEFT JOIN ir_translation it ON (it.name = %s and
                                        it.lang = %s and
                                        it.type = %s and
                                        it.res_id = ct.id and
                                        it.value != '')
                            )
                            SELECT id FROM temp_irt_current WHERE {name} {operator} {right} order by name
                            """.format(current_table=model._table, quote_left=_quote(left), name=unaccent('name'),
                                       operator=sql_operator, right=instr)

                    params = (
                        model._name + ',' + left,
                        context.get('lang') or 'en_US',
                        'model',
                        right,
                    )
                    push(create_substitution_leaf(leaf, ('id', inselect_operator, (subselect, params)), model, internal=True))

                else:
                    push_result(leaf)

        # ----------------------------------------
        # END OF PARSING FULL DOMAIN
        # -> generate joins
        # ----------------------------------------

        joins = set()
        for leaf in self.result:
            joins |= set(leaf.get_join_conditions())
        self.joins = list(joins)

    def __leaf_to_sql(self, eleaf):
        model = eleaf.model
        leaf = eleaf.leaf
        left, operator, right = leaf

        # final sanity checks - should never fail
        assert operator in (TERM_OPERATORS + ('inselect', 'not inselect')), \
            "Invalid operator %r in domain term %r" % (operator, leaf)
        assert leaf in (TRUE_LEAF, FALSE_LEAF) or left in model._fields \
            or left in MAGIC_COLUMNS, "Invalid field %r in domain term %r" % (left, leaf)
        assert not isinstance(right, BaseModel), \
            "Invalid value %r in domain term %r" % (right, leaf)

        table_alias = '"%s"' % (eleaf.generate_alias())

        if leaf == TRUE_LEAF:
            query = 'TRUE'
            params = []

        elif leaf == FALSE_LEAF:
            query = 'FALSE'
            params = []

        elif operator == 'inselect':
            query = '(%s."%s" in (%s))' % (table_alias, left, right[0])
            params = right[1]

        elif operator == 'not inselect':
            query = '(%s."%s" not in (%s))' % (table_alias, left, right[0])
            params = right[1]

        elif operator in ['in', 'not in']:
            # Two cases: right is a boolean or a list. The boolean case is an
            # abuse and handled for backward compatibility.
            if isinstance(right, bool):
                _logger.warning("The domain term '%s' should use the '=' or '!=' operator." % (leaf,))
                if operator == 'in':
                    r = 'NOT NULL' if right else 'NULL'
                else:
                    r = 'NULL' if right else 'NOT NULL'
                query = '(%s."%s" IS %s)' % (table_alias, left, r)
                params = []
            elif isinstance(right, (list, tuple)):
                params = list(right)
                check_nulls = False
                for i in range(len(params))[::-1]:
                    if params[i] == False:
                        check_nulls = True
                        del params[i]

                if params:
                    if left == 'id':
                        instr = ','.join(['%s'] * len(params))
                    else:
                        ss = model._columns[left]._symbol_set
                        instr = ','.join([ss[0]] * len(params))
                        params = map(ss[1], params)
                    query = '(%s."%s" %s (%s))' % (table_alias, left, operator, instr)
                else:
                    # The case for (left, 'in', []) or (left, 'not in', []).
                    query = 'FALSE' if operator == 'in' else 'TRUE'

                if check_nulls and operator == 'in':
                    query = '(%s OR %s."%s" IS NULL)' % (query, table_alias, left)
                elif not check_nulls and operator == 'not in':
                    query = '(%s OR %s."%s" IS NULL)' % (query, table_alias, left)
                elif check_nulls and operator == 'not in':
                    query = '(%s AND %s."%s" IS NOT NULL)' % (query, table_alias, left)  # needed only for TRUE.
            else:  # Must not happen
                raise ValueError("Invalid domain term %r" % (leaf,))

        elif (left in model._columns) and model._columns[left]._type == "boolean" and ((operator == '=' and right is False) or (operator == '!=' and right is True)):
            query = '(%s."%s" IS NULL or %s."%s" = false )' % (table_alias, left, table_alias, left)
            params = []

        elif (right is False or right is None) and (operator == '='):
            query = '%s."%s" IS NULL ' % (table_alias, left)
            params = []

        elif (left in model._columns) and model._columns[left]._type == "boolean" and ((operator == '!=' and right is False) or (operator == '==' and right is True)):
            query = '(%s."%s" IS NOT NULL and %s."%s" != false)' % (table_alias, left, table_alias, left)
            params = []

        elif (right is False or right is None) and (operator == '!='):
            query = '%s."%s" IS NOT NULL' % (table_alias, left)
            params = []

        elif operator == '=?':
            if right is False or right is None:
                # '=?' is a short-circuit that makes the term TRUE if right is None or False
                query = 'TRUE'
                params = []
            else:
                # '=?' behaves like '=' in other cases
                query, params = self.__leaf_to_sql(
                    create_substitution_leaf(eleaf, (left, '=', right), model))

        elif left == 'id':
            query = '%s.id %s %%s' % (table_alias, operator)
            params = right

        else:
            need_wildcard = operator in ('like', 'ilike', 'not like', 'not ilike')
            sql_operator = {'=like': 'like', '=ilike': 'ilike'}.get(operator, operator)
            cast = '::text' if  sql_operator.endswith('like') else ''

            if left in model._columns:
                format = need_wildcard and '%s' or model._columns[left]._symbol_set[0]
                unaccent = self._unaccent if sql_operator.endswith('like') else lambda x: x
                column = '%s.%s' % (table_alias, _quote(left))
                query = '(%s %s %s)' % (unaccent(column + cast), sql_operator, unaccent(format))
            elif left in MAGIC_COLUMNS:
                    query = "(%s.\"%s\"%s %s %%s)" % (table_alias, left, cast, sql_operator)
                    params = right
            else:  # Must not happen
                raise ValueError("Invalid field %r in domain term %r" % (left, leaf))

            add_null = False
            if need_wildcard:
                if isinstance(right, str):
                    str_utf8 = right
                elif isinstance(right, unicode):
                    str_utf8 = right.encode('utf-8')
                else:
                    str_utf8 = str(right)
                params = '%%%s%%' % str_utf8
                add_null = not str_utf8
            elif left in model._columns:
                params = model._columns[left]._symbol_set[1](right)

            if add_null:
                query = '(%s OR %s."%s" IS NULL)' % (query, table_alias, left)

        if isinstance(params, basestring):
            params = [params]
        return query, params

    def to_sql(self):
        stack = []
        params = []
        # Process the domain from right to left, using a stack, to generate a SQL expression.
        self.result.reverse()
        for leaf in self.result:
            if leaf.is_leaf(internal=True):
                q, p = self.__leaf_to_sql(leaf)
                params.insert(0, p)
                stack.append(q)
            elif leaf.leaf == NOT_OPERATOR:
                stack.append('(NOT (%s))' % (stack.pop(),))
            else:
                ops = {AND_OPERATOR: ' AND ', OR_OPERATOR: ' OR '}
                q1 = stack.pop()
                q2 = stack.pop()
                stack.append('(%s %s %s)' % (q1, ops[leaf.leaf], q2,))

        assert len(stack) == 1
        query = stack[0]
        joins = ' AND '.join(self.joins)
        if joins:
            query = '(%s) AND %s' % (joins, query)

        return query, tools.flatten(params)
