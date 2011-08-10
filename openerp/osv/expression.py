#!/usr/bin/env python
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

import logging

from openerp.tools import flatten, reverse_enumerate
import fields

#.apidoc title: Domain Expressions

NOT_OPERATOR = '!'
OR_OPERATOR = '|'
AND_OPERATOR = '&'

# This doesn't contain <> as it is simpified to != by normalize_operator().
OPS = ('=', '!=', '<=', '<', '>', '>=', '=?', '=like', '=ilike', 'like', 'not like', 'ilike', 'not ilike', 'in', 'not in', 'child_of')
NEGATIVE_OPS = ('!=', 'not like', 'not ilike', 'not in')

TRUE_LEAF = (1, '=', 1)
FALSE_LEAF = (0, '=', 1)

TRUE_DOMAIN = [TRUE_LEAF]
FALSE_DOMAIN = [FALSE_LEAF]

_logger = logging.getLogger('expression')

def normalize(domain):
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
            result[0:0] = ['&']             # put an extra '&' in front
            expected = 1
        result.append(token)
        if isinstance(token, (list, tuple)): # domain term
            expected -= 1
        else:
            expected += op_arity.get(token, 0) - 1
    assert expected == 0
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
    """ AND([D1,D2,...]) returns a domain representing D1 and D2 and ... """
    return combine(AND_OPERATOR, TRUE_DOMAIN, FALSE_DOMAIN, domains)

def OR(domains):
    """ OR([D1,D2,...]) returns a domain representing D1 or D2 or ... """
    return combine(OR_OPERATOR, FALSE_DOMAIN, TRUE_DOMAIN, domains)

def is_operator(element):
    return isinstance(element, (str, unicode)) and element in [AND_OPERATOR, OR_OPERATOR, NOT_OPERATOR]

# TODO change the share wizard to use this function.
def is_leaf(element, internal=False):
    INTERNAL_OPS = OPS + ('inselect',)
    return (isinstance(element, tuple) or isinstance(element, list)) \
       and len(element) == 3 \
       and (((not internal) and element[1] in OPS + ('<>',)) \
            or (internal and element[1] in INTERNAL_OPS + ('<>',)))

def normalize_leaf(left, operator, right):
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

def distribute_not(domain):
    """ Distribute the '!' operator on a normalized domain.
    """
    def negate(leaf):
        left, operator, right = leaf
        mapping = {
            '<': '>=',
            '>': '<=',
            '<=': '>',
            '>=': '<',
            '=': '!=',
            '!=': '=',
        }
        if operator in ('in', 'like', 'ilike'):
            operator = 'not ' + operator
            return [(left, operator, right)]
        if operator in ('not in', 'not like', 'not ilike'):
            operator = operator[4:]
            return [(left, operator, right)]
        if operator in mapping:
            operator = mapping[operator]
            return [(left, operator, right)]
        return ['!', (left, operator, right)]
    def distribute(domain):
        if is_leaf(domain[0]):
            return negate(domain[0]), domain[1:]
        if domain[0] == '&':
            done1, todo1 = distribute(domain[1:])
            done2, todo2 = distribute(todo1)
            return ['|'] + done1 + done2, todo2
        if domain[0] == '|':
            done1, todo1 = distribute(domain[1:])
            done2, todo2 = distribute(todo1)
            return ['&'] + done1 + done2, todo2
    if not domain:
        return []
    if domain[0] != '!':
        return [domain[0]] + distribute_not(domain[1:])
    if domain[0] == '!':
        done, todo = distribute(domain[1:])
        return done + distribute_not(todo)

def select_from_where(cr, s, f, w, ids, op):
    # todo: merge into parent query as sub-query
    res = []
    if ids:
        if op in ['<','>','>=','<=']:
            cr.execute('SELECT "%s" FROM "%s" WHERE "%s" %s %%s' % \
                (s, f, w, op), (ids[0],)) # TODO shouldn't this be min/max(ids) ?
            res = [r[0] for r in cr.fetchall()]
        else: # TODO op is supposed to be 'in'? It is called with child_of...
            for i in range(0, len(ids), cr.IN_MAX):
                subids = ids[i:i+cr.IN_MAX]
                cr.execute('SELECT "%s" FROM "%s" WHERE "%s" IN %%s' % \
                    (s, f, w), (tuple(subids),))
                res.extend([r[0] for r in cr.fetchall()])
    return res

def select_distinct_from_where_not_null(cr, s, f):
    cr.execute('SELECT distinct("%s") FROM "%s" where "%s" is not null' % (s, f, s))
    return [r[0] for r in cr.fetchall()]

class expression(object):
    """
    parse a domain expression
    use a real polish notation
    leafs are still in a ('foo', '=', 'bar') format
    For more info: http://christophe-simonis-at-tiny.blogspot.com/2008/08/new-new-domain-notation.html
    """

    def __init__(self, cr, uid, exp, table, context):
        self.__field_tables = {}  # used to store the table to use for the sql generation. key = index of the leaf
        self.__all_tables = set()
        self.__joins = []
        self.__main_table = None # 'root' table. set by parse()
        # assign self.__exp with the normalized, parsed domain.
        self.parse(cr, uid, distribute_not(normalize(exp)), table, context)

    # TODO used only for osv_memory
    @property
    def exp(self):
        return self.__exp[:]

    def parse(self, cr, uid, exp, table, context):
        """ transform the leafs of the expression """
        self.__exp = exp

        def child_of_domain(left, right, table, parent=None, prefix=''):
            ids = right
            if table._parent_store and (not table.pool._init):
# TODO: Improve where joins are implemented for many with '.', replace by:
# doms += ['&',(prefix+'.parent_left','<',o.parent_right),(prefix+'.parent_left','>=',o.parent_left)]
                doms = []
                for o in table.browse(cr, uid, ids, context=context):
                    if doms:
                        doms.insert(0, OR_OPERATOR)
                    doms += [AND_OPERATOR, ('parent_left', '<', o.parent_right), ('parent_left', '>=', o.parent_left)]
                if prefix:
                    return [(left, 'in', table.search(cr, uid, doms, context=context))]
                return doms
            else:
                def rg(ids, table, parent):
                    if not ids:
                        return []
                    ids2 = table.search(cr, uid, [(parent, 'in', ids)], context=context)
                    return ids + rg(ids2, table, parent)
                return [(left, 'in', rg(ids, table, parent or table._parent_name))]

        # TODO rename this function as it is not strictly for 'child_of', but also for 'in'...
        def child_of_right_to_ids(value, operator, field_obj):
            """ Normalize a single id, or a string, or a list of ids to a list of ids.
            """
            if isinstance(value, basestring):
                return [x[0] for x in field_obj.name_search(cr, uid, value, [], operator, context=context, limit=None)]
            elif isinstance(value, (int, long)):
                return [value]
            else:
                return list(value)

        self.__main_table = table
        self.__all_tables.add(table)

        i = -1
        while i + 1<len(self.__exp):
            i += 1
            e = self.__exp[i]
            if is_operator(e) or e == TRUE_LEAF or e == FALSE_LEAF:
                continue

            # check if the expression is valid
            if not is_leaf(e):
                raise ValueError('Bad domain expression: %r, %r is not a valid term.' % (exp, e))

            # normalize the leaf's operator
            e = normalize_leaf(*e)
            self.__exp[i] = e
            left, operator, right = e

            working_table = table # The table containing the field (the name provided in the left operand)
            fargs = left.split('.', 1)

            # If the field is _inherits'd, search for the working_table,
            # and extract the field.
            if fargs[0] in table._inherit_fields:
                while True:
                    field = working_table._columns.get(fargs[0])
                    if field:
                        self.__field_tables[i] = working_table
                        break
                    next_table = working_table.pool.get(working_table._inherit_fields[fargs[0]][0])
                    if next_table not in self.__all_tables:
                        self.__joins.append('%s.%s=%s.%s' % (next_table._table, 'id', working_table._table, working_table._inherits[next_table._name]))
                        self.__all_tables.add(next_table)
                    working_table = next_table
            # Or (try to) directly extract the field.
            else:
                field = working_table._columns.get(fargs[0])

            if not field:
                if left == 'id' and operator == 'child_of':
                    ids2 = child_of_right_to_ids(right, 'ilike', table)
                    dom = child_of_domain(left, ids2, working_table)
                    self.__exp = self.__exp[:i] + dom + self.__exp[i+1:]
                continue

            field_obj = table.pool.get(field._obj)
            if len(fargs) > 1:
                if field._type == 'many2one':
                    right = field_obj.search(cr, uid, [(fargs[1], operator, right)], context=context)
                    self.__exp[i] = (fargs[0], 'in', right)
                # Making search easier when there is a left operand as field.o2m or field.m2m
                if field._type in ['many2many', 'one2many']:
                    right = field_obj.search(cr, uid, [(fargs[1], operator, right)], context=context)
                    right1 = table.search(cr, uid, [(fargs[0], 'in', right)], context=context)
                    self.__exp[i] = ('id', 'in', right1)

                if not isinstance(field, fields.property):
                    continue

            if field._properties and not field.store:
                # this is a function field that is not stored
                if not field._fnct_search:
                    # the function field doesn't provide a search function and doesn't store
                    # values in the database, so we must ignore it : we generate a dummy leaf
                    self.__exp[i] = TRUE_LEAF
                else:
                    subexp = field.search(cr, uid, table, left, [self.__exp[i]], context=context)
                    if not subexp:
                        self.__exp[i] = TRUE_LEAF
                    else:
                        # we assume that the expression is valid
                        # we create a dummy leaf for forcing the parsing of the resulting expression
                        self.__exp[i] = AND_OPERATOR
                        self.__exp.insert(i + 1, TRUE_LEAF)
                        for j, se in enumerate(subexp):
                            self.__exp.insert(i + 2 + j, se)
            # else, the value of the field is store in the database, so we search on it

            elif field._type == 'one2many':
                # Applying recursivity on field(one2many)
                if operator == 'child_of':
                    if field._obj != working_table._name:
                        ids2 = child_of_right_to_ids(right, 'ilike', field_obj)
                        dom = child_of_domain(left, ids2, field_obj, prefix=field._obj)
                    else:
                        ids2 = child_of_right_to_ids(right, 'ilike', field_obj)
                        dom = child_of_domain('id', ids2, working_table, parent=left)
                    self.__exp = self.__exp[:i] + dom + self.__exp[i+1:]

                else:
                    call_null = True

                    if right is not False:
                        if isinstance(right, basestring):
                            ids2 = [x[0] for x in field_obj.name_search(cr, uid, right, [], operator, context=context, limit=None)]
                            if ids2:
                                operator = 'in'
                        else:
                            if not isinstance(right, list):
                                ids2 = [right]
                            else:
                                ids2 = right
                        if not ids2:
                            if operator in ['like','ilike','in','=']:
                                #no result found with given search criteria
                                call_null = False
                                self.__exp[i] = FALSE_LEAF
                        else:
                            call_null = False
                            o2m_op = 'not in' if operator in NEGATIVE_OPS else 'in'
                            self.__exp[i] = ('id', o2m_op, select_from_where(cr, field._fields_id, field_obj._table, 'id', ids2, operator))

                    if call_null:
                        o2m_op = 'in' if operator in NEGATIVE_OPS else 'not in'
                        self.__exp[i] = ('id', o2m_op, select_distinct_from_where_not_null(cr, field._fields_id, field_obj._table))

            elif field._type == 'many2many':
                #FIXME
                if operator == 'child_of':
                    def _rec_convert(ids):
                        if field_obj == table:
                            return ids
                        return select_from_where(cr, field._id1, field._rel, field._id2, ids, operator)

                    ids2 = child_of_right_to_ids(right, 'ilike', field_obj)
                    dom = child_of_domain('id', ids2, field_obj)
                    ids2 = field_obj.search(cr, uid, dom, context=context)
                    self.__exp[i] = ('id', 'in', _rec_convert(ids2))
                else:
                    call_null_m2m = True
                    if right is not False:
                        if isinstance(right, basestring):
                            res_ids = [x[0] for x in field_obj.name_search(cr, uid, right, [], operator, context=context)]
                            if res_ids:
                                operator = 'in'
                        else:
                            if not isinstance(right, list):
                                res_ids = [right]
                            else:
                                res_ids = right
                        if not res_ids:
                            if operator in ['like','ilike','in','=']:
                                #no result found with given search criteria
                                call_null_m2m = False
                                self.__exp[i] = FALSE_LEAF
                            else:
                                operator = 'in' # operator changed because ids are directly related to main object
                        else:
                            call_null_m2m = False
                            m2m_op = 'not in' if operator in NEGATIVE_OPS else 'in'
                            self.__exp[i] = ('id', m2m_op, select_from_where(cr, field._id1, field._rel, field._id2, res_ids, operator) or [0])

                    if call_null_m2m:
                        m2m_op = 'in' if operator in NEGATIVE_OPS else 'not in'
                        self.__exp[i] = ('id', m2m_op, select_distinct_from_where_not_null(cr, field._id1, field._rel))

            elif field._type == 'many2one':
                if operator == 'child_of':
                    ids2 = child_of_right_to_ids(right, 'ilike', field_obj)
                    if field._obj != working_table._name:
                        dom = child_of_domain(left, ids2, field_obj, prefix=field._obj)
                    else:
                        dom = child_of_domain('id', ids2, working_table, parent=left)
                    self.__exp = self.__exp[:i] + dom + self.__exp[i+1:]
                else:
                    def _get_expression(field_obj, cr, uid, left, right, operator, context=None):
                        if context is None:
                            context = {}
                        c = context.copy()
                        c['active_test'] = False
                        #Special treatment to ill-formed domains
                        operator = ( operator in ['<','>','<=','>='] ) and 'in' or operator

                        dict_op = {'not in':'!=','in':'=','=':'in','!=':'not in'}
                        if isinstance(right, tuple):
                            right = list(right)
                        if (not isinstance(right, list)) and operator in ['not in','in']:
                            operator = dict_op[operator]
                        elif isinstance(right, list) and operator in ['!=','=']: #for domain (FIELD,'=',['value1','value2'])
                            operator = dict_op[operator]
                        res_ids = [x[0] for x in field_obj.name_search(cr, uid, right, [], operator, limit=None, context=c)]
                        if operator in NEGATIVE_OPS:
                            res_ids.append(False) # TODO this should not be appended if False was in 'right'
                        return (left, 'in', res_ids)

                    m2o_str = False
                    if right:
                        if isinstance(right, basestring): # and not isinstance(field, fields.related):
                            m2o_str = True
                        elif isinstance(right, (list, tuple)):
                            m2o_str = True
                            for ele in right:
                                if not isinstance(ele, basestring):
                                    m2o_str = False
                                    break
                        if m2o_str:
                            self.__exp[i] = _get_expression(field_obj, cr, uid, left, right, operator, context=context)
                    elif right == []:
                        pass # Handled by __leaf_to_sql().
                    else: # right is False
                        pass # Handled by __leaf_to_sql().

            else:
                # other field type
                # add the time part to datetime field when it's not there:
                if field._type == 'datetime' and self.__exp[i][2] and len(self.__exp[i][2]) == 10:

                    self.__exp[i] = list(self.__exp[i])

                    if operator in ('>', '>='):
                        self.__exp[i][2] += ' 00:00:00'
                    elif operator in ('<', '<='):
                        self.__exp[i][2] += ' 23:59:59'

                    self.__exp[i] = tuple(self.__exp[i])

                if field.translate:
                    if operator in ('like', 'ilike', 'not like', 'not ilike'):
                        right = '%%%s%%' % right

                    operator = operator == '=like' and 'like' or operator

                    query1 = '( SELECT res_id'          \
                             '    FROM ir_translation'  \
                             '   WHERE name = %s'       \
                             '     AND lang = %s'       \
                             '     AND type = %s'
                    instr = ' %s'
                    #Covering in,not in operators with operands (%s,%s) ,etc.
                    if operator in ['in','not in']:
                        instr = ','.join(['%s'] * len(right))
                        query1 += '     AND value ' + operator +  ' ' +" (" + instr + ")"   \
                             ') UNION ('                \
                             '  SELECT id'              \
                             '    FROM "' + working_table._table + '"'       \
                             '   WHERE "' + left + '" ' + operator + ' ' +" (" + instr + "))"
                    else:
                        query1 += '     AND value ' + operator + instr +   \
                             ') UNION ('                \
                             '  SELECT id'              \
                             '    FROM "' + working_table._table + '"'       \
                             '   WHERE "' + left + '" ' + operator + instr + ")"

                    query2 = [working_table._name + ',' + left,
                              context.get('lang', False) or 'en_US',
                              'model',
                              right,
                              right,
                             ]

                    self.__exp[i] = ('id', 'inselect', (query1, query2))

    def __leaf_to_sql(self, leaf, table):
        left, operator, right = leaf

        if leaf == TRUE_LEAF:
            query = 'TRUE'
            params = []

        elif leaf == FALSE_LEAF:
            query = 'FALSE'
            params = []

        elif operator == 'inselect':
            query = '(%s.%s in (%s))' % (table._table, left, right[0])
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
                query = '(%s.%s IS %s)' % (table._table, left, r)
                params = []
            elif isinstance(right, (list, tuple)):
                params = right[:]
                check_nulls = False
                for i in range(len(params))[::-1]:
                    if params[i] == False:
                        check_nulls = True
                        del params[i]

                if params:
                    if left == 'id':
                        instr = ','.join(['%s'] * len(params))
                    else:
                        instr = ','.join([table._columns[left]._symbol_set[0]] * len(params))
                    query = '(%s.%s %s (%s))' % (table._table, left, operator, instr)
                else:
                    # The case for (left, 'in', []) or (left, 'not in', []).
                    query = 'FALSE' if operator == 'in' else 'TRUE'

                if check_nulls and operator == 'in':
                    query = '(%s OR %s.%s IS NULL)' % (query, table._table, left)
                elif not check_nulls and operator == 'not in':
                    query = '(%s OR %s.%s IS NULL)' % (query, table._table, left)
                elif check_nulls and operator == 'not in':
                    query = '(%s AND %s.%s IS NOT NULL)' % (query, table._table, left) # needed only for TRUE.
            else: # Must not happen.
                pass

        elif right == False and (left in table._columns) and table._columns[left]._type=="boolean" and (operator == '='):
            query = '(%s.%s IS NULL or %s.%s = false )' % (table._table, left, table._table, left)
            params = []

        elif (right is False or right is None) and (operator == '='):
            query = '%s.%s IS NULL ' % (table._table, left)
            params = []

        elif right == False and (left in table._columns) and table._columns[left]._type=="boolean" and (operator == '!='):
            query = '(%s.%s IS NOT NULL and %s.%s != false)' % (table._table, left, table._table, left)
            params = []

        elif (right is False or right is None) and (operator == '!='):
            query = '%s.%s IS NOT NULL' % (table._table, left)
            params = []

        elif (operator == '=?'):
            if (right is False or right is None):
                query = 'TRUE'
                params = []
            elif left in table._columns:
                format = table._columns[left]._symbol_set[0]
                query = '(%s.%s = %s)' % (table._table, left, format)
                params = table._columns[left]._symbol_set[1](right)
            else:
                query = "(%s.%s = '%%s')" % (table._table, left)
                params = right

        elif left == 'id':
            query = '%s.id %s %%s' % (table._table, operator)
            params = right

        else:
            like = operator in ('like', 'ilike', 'not like', 'not ilike')

            op = {'=like':'like','=ilike':'ilike'}.get(operator, operator)
            if left in table._columns:
                format = like and '%s' or table._columns[left]._symbol_set[0]
                query = '(%s.%s %s %s)' % (table._table, left, op, format)
            else:
                query = "(%s.%s %s '%s')" % (table._table, left, op, right)

            add_null = False
            if like:
                if isinstance(right, str):
                    str_utf8 = right
                elif isinstance(right, unicode):
                    str_utf8 = right.encode('utf-8')
                else:
                    str_utf8 = str(right)
                params = '%%%s%%' % str_utf8
                add_null = not str_utf8
            elif left in table._columns:
                params = table._columns[left]._symbol_set[1](right)

            if add_null:
                query = '(%s OR %s.%s IS NULL)' % (query, table._table, left)

        if isinstance(params, basestring):
            params = [params]
        return (query, params)


    def to_sql(self):
        stack = []
        params = []
        # Process the domain from right to left, using a stack, to generate a SQL expression.
        for i, e in reverse_enumerate(self.__exp):
            if is_leaf(e, internal=True):
                table = self.__field_tables.get(i, self.__main_table)
                q, p = self.__leaf_to_sql(e, table)
                params.insert(0, p)
                stack.append(q)
            else:
                if e == NOT_OPERATOR:
                    stack.append('(NOT (%s))' % (stack.pop(),))
                else:
                    ops = {AND_OPERATOR: ' AND ', OR_OPERATOR: ' OR '}
                    q1 = stack.pop()
                    q2 = stack.pop()
                    stack.append('(%s %s %s)' % (q1, ops[e], q2,))

        assert len(stack) == 1
        query = stack[0]
        joins = ' AND '.join(self.__joins)
        if joins:
            query = '(%s) AND %s' % (joins, query)
        return (query, flatten(params))

    def get_tables(self):
        return ['"%s"' % t._table for t in self.__all_tables]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

