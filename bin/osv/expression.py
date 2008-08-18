#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from tools import flatten, reverse_enumerate


class expression(object):
    """
    parse a domain expression
    use a real polish notation
    leafs are still in a ('foo', '=', 'bar') format
    For more info: http://christophe-simonis-at-tiny.blogspot.com/2008/08/new-new-domain-notation.html 
    """

    def _is_operator(self, element):
        return isinstance(element, str) \
           and element in ['&', '|', '!']

    def _is_leaf(self, element, internal=False):
        return (isinstance(element, tuple) or isinstance(element, list)) \
           and len(element) == 3 \
           and element[1] in ('=', '!=', '<>', '<=', '<', '>', '>=', '=like', 'like', 'not like', 'ilike', 'not ilike', 'in', 'not in', 'child_of') \
           and ((not internal) or element[1] in ('inselect',))

    def __execute_recursive_in(self, cr, s, f, w, ids):
        res = []
        for i in range(0, len(ids), cr.IN_MAX):
            subids = ids[i:i+cr.IN_MAX]
            cr.execute('SELECT "%s"'    \
                       '  FROM "%s"'    \
                       ' WHERE "%s" in (%s)' % (s, f, w, ','.join(['%d']*len(subids))),
                       subids)
            res.extend([r[0] for r in cr.fetchall()])
        return res


    def __init__(self, exp):
        # check if the expression is valid
        if not reduce(lambda acc, val: acc and (self._is_operator(val) or self._is_leaf(val)), exp, True):
            raise ValueError('Bad domain expression: %r' % (exp,))
        self.__exp = exp
        self.__tables = {}  # used to store the table to use for the sql generation. key = index of the leaf
        self.__joins = []
        self.__main_table = None # 'root' table. set by parse()
        self.__DUMMY_LEAF = (1, '=', 1) # a dummy leaf that must not be parsed or sql generated


    def parse(self, cr, uid, table, context):
        """ transform the leafs of the expression """
        if not self.__exp:
            return self

        def _rec_get(ids, table, parent, left='id', prefix=''):
            if table._parent_store and (not table.pool._init):
# TODO: Improve where joins are implemented for many with '.', replace by:
# doms += ['&',(prefix+'.parent_left','<',o.parent_right),(prefix+'.parent_left','>=',o.parent_left)]
                doms = []
                for o in table.browse(cr, uid, ids, context=context):
                    if doms:
                        doms.insert(0,'|')
                    doms += ['&',('parent_left','<',o.parent_right),('parent_left','>=',o.parent_left)]
                if prefix:
                    return [(left, 'in', table.search(cr, uid, doms, context=context))]
                return doms
            else:
                if not ids:
                    return []
                ids2 = table.search(cr, uid, [(parent, 'in', ids)], context=context)
                return [(prefix+left, 'in', ids2+ids)]

        self.__main_table = table

        i = -1
        while i+1<len(self.__exp):
            i+=1
            e = self.__exp[i]
            if self._is_operator(e) or e == self.__DUMMY_LEAF:
                continue
            left, operator, right = e

            working_table = table
            if left in table._inherit_fields:
                working_table = table.pool.get(table._inherit_fields[left][0])
                if working_table not in self.__tables.values():
                    self.__joins.append('%s.%s' % (table._table, table._inherits[working_table._name]))

            self.__tables[i] = working_table

            fargs = left.split('.', 1)
            field = working_table._columns.get(fargs[0], False)
            if not field:
                if left == 'id' and operator == 'child_of':
                    dom = _rec_get(right, working_table, working_table._parent_name)
                    self.__exp = self.__exp[:i] + dom + self.__exp[i+1:]
                continue

            field_obj = table.pool.get(field._obj)
            if len(fargs) > 1:
                if field._type == 'many2one':
                    right = field_obj.search(cr, uid, [(fargs[1], operator, right)], context=context)
                    self.__exp[i] = (fargs[0], 'in', right)
                continue

            if field._properties:
                # this is a function field
                if not field.store:
                    if not field._fnct_search:
                        # the function field doesn't provide a search function and doesn't store
                        # values in the database, so we must ignore it : we generate a dummy leaf
                        self.__exp[i] = self.__DUMMY_LEAF
                    else:
                        subexp = field.search(cr, uid, table, left, [self.__exp[i]])
                        # we assume that the expression is valid 
                        # we create a dummy leaf for forcing the parsing of the resulting expression
                        self.__exp[i] = '&'
                        self.__exp.insert(i + 1, self.__DUMMY_LEAF)
                        for j, se in enumerate(subexp):
                            self.__exp.insert(i + 2 + j, se)
                
                # else, the value of the field is store in the database, so we search on it


            elif field._type == 'one2many':
                if isinstance(right, basestring):
                    ids2 = [x[0] for x in field_obj.name_search(cr, uid, right, [], operator)]
                else:
                    ids2 = list(right)
                if not ids2:
                    self.__exp[i] = ('id', '=', '0')
                else:
                    self.__exp[i] = ('id', 'in', self.__execute_recursive_in(cr, field._fields_id, field_obj._table, 'id', ids2))

            elif field._type == 'many2many':
                #FIXME
                if operator == 'child_of':
                    if isinstance(right, basestring):
                        ids2 = [x[0] for x in field_obj.name_search(cr, uid, right, [], 'like')]
                    else:
                        ids2 = list(right)

                    def _rec_convert(ids):
                        if field_obj == table:
                            return ids
                        return self.__execute_recursive_in(cr, field._id1, field._rel, field._id2, ids)

                    self.__exp[i] = ('id', 'in', _rec_convert(ids2 + _rec_get(ids2, field_obj, working_table._parent_name)))
                else:
                    if isinstance(right, basestring):
                        res_ids = [x[0] for x in field_obj.name_search(cr, uid, right, [], operator)]
                    else:
                        res_ids = list(right)
                    self.__exp[i] = ('id', 'in', self.__execute_recursive_in(cr, field._id1, field._rel, field._id2, res_ids) or [0])
            elif field._type == 'many2one':
                if operator == 'child_of':
                    if isinstance(right, basestring):
                        ids2 = [x[0] for x in field_obj.search_name(cr, uid, right, [], 'like')]
                    else:
                        ids2 = list(right)

                    self.__operator = 'in'
                    if field._obj != working_table._name:
                        dom = _rec_get(ids2, field_obj, working_table._parent_name, left=left, prefix=left+'.')
                    else:
                        dom = _rec_get(ids2, working_table, left)
                    self.__exp = self.__exp[:i] + dom + self.__exp[i+1:]
                else:
                    if isinstance(right, basestring):
                        res_ids = field_obj.name_search(cr, uid, right, [], operator)
                        right = map(lambda x: x[0], res_ids)
                        self.__exp[i] = (left, 'in', right)
            else:
                # other field type
                if field.translate:
                    if operator in ('like', 'ilike', 'not like', 'not ilike'):
                        right = '%%%s%%' % right

                    query1 = '( SELECT res_id'          \
                             '    FROM ir_translation'  \
                             '   WHERE name = %s'       \
                             '     AND lang = %s'       \
                             '     AND type = %s'       \
                             '     AND value ' + operator + ' %s'    \
                             ') UNION ('                \
                             '  SELECT id'              \
                             '    FROM "' + working_table._table + '"'       \
                             '   WHERE "' + left + '" ' + operator + ' %s' \
                             ')'
                    query2 = [working_table._name + ',' + left,
                              context.get('lang', False) or 'en_US',
                              'model',
                              right,
                              right,
                             ]

                    self.__exp[i] = ('id', 'inselect', (query1, query2))

        return self

    def __leaf_to_sql(self, leaf, table):
        left, operator, right = leaf

        if operator == 'inselect':
            query = '(%s.%s in (%s))' % (table._table, left, right[0])
            params = right[1]
        elif operator in ['in', 'not in']:
            params = right[:]
            len_before = len(params)
            for i in range(len_before)[::-1]:
                if params[i] == False:
                    del params[i]

            len_after = len(params)
            check_nulls = len_after != len_before
            query = '(1=0)'

            if len_after:
                if left == 'id':
                     instr = ','.join(['%d'] * len_after)
                else:
                    instr = ','.join([table._columns[left]._symbol_set[0]] * len_after)
                query = '(%s.%s %s (%s))' % (table._table, left, operator, instr)

            if check_nulls:
                query = '(%s OR %s IS NULL)' % (query, left)
        else:
            params = []
            if right is False and operator == '=':
                query = '%s IS NULL' % left
            elif right is False and operator in ['<>', '!=']:
                query = '%s IS NOT NULL' % left
            else:
                if left == 'id':
                    query = '%s.id %s %%s' % (table._table, operator)
                    params = right
                else:
                    like = operator in ('like', 'ilike', 'not like', 'not ilike')

                    op = operator == '=like' and 'like' or operator
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
                        query = '(%s OR %s IS NULL)' % (query, left)

        if isinstance(params, basestring):
            params = [params]
        return (query, params)


    def to_sql(self):
        stack = []
        params = []
        for i, e in reverse_enumerate(self.__exp):
            if self._is_leaf(e, internal=True):
                table = self.__tables.has_key(i) and self.__tables[i] or self.__main_table
                q, p = self.__leaf_to_sql(e, table)
                params.insert(0, p)
                stack.append(q)
            else:
                if e == '!':
                    stack.append('(NOT (%s))' % (stack.pop(),))
                else:
                    ops = {'&': ' AND ', '|': ' OR '}
                    q1 = stack.pop()
                    q2 = stack.pop()
                    stack.append('(%s %s %s)' % (q1, ops[e], q2,))
        
        query = ' AND '.join(reversed(stack))
        joins = ' AND '.join(map(lambda j: '%s.id = %s' % (self.__main_table._table, j), self.__joins))
        if joins:
            query = '(%s AND (%s))' % (joins, query)
        return (query, flatten(params))

    def get_tables(self):
        return ['"%s"' % t._table for t in set(self.__tables.values())]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

