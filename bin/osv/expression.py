#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from tools import flatten

class expression(object):
    """
    parse a domain expression
    examples:

    >>> e = [('foo', '=', 'bar')]
    >>> expression(e).parse().to_sql()
    'foo = bar'
    >>> e = [('id', 'in', [1,2,3])]
    >>> expression(e).parse().to_sql()
    'id in (1, 2, 3)'
    >>> e = [('field', '=', 'value'), ('field', '<>', 'value')]
    >>> expression(e).parse().to_sql()
    '( field = value AND field <> value )'
    >>> e = [('&', ('field', '<', 'value'), ('field', '>', 'value'))]
    >>> expression(e).parse().to_sql()
    '( field < value AND field > value )'
    >>> e = [('|', ('field', '=', 'value'), ('field', '=', 'value'))]
    >>> expression(e).parse().to_sql()
    '( field = value OR field = value )'
    >>> e = [('&', ('field1', '=', 'value'), ('field2', '=', 'value'), ('|', ('field3', '<>', 'value'), ('field4', '=', 'value')))]
    >>> expression(e).parse().to_sql()
    '( field1 = value AND field2 = value AND ( field3 <> value OR field4 = value ) )'
    >>> e = [('&', ('|', ('a', '=', '1'), ('b', '=', '2')), ('|', ('c', '=', '3'), ('d', '=', '4')))]
    >>> expression(e).parse().to_sql()
    '( ( a = 1 OR b = 2 ) AND ( c = 3 OR d = 4 ) )'
    >>> e = [('|', (('a', '=', '1'), ('b', '=', '2')), (('c', '=', '3'), ('d', '=', '4')))]
    >>> expression(e).parse().to_sql()
    '( ( a = 1 AND b = 2 ) OR ( c = 3 AND d = 4 ) )'
    >>> expression(e).parse().get_tables()
    []
    >>> expression('fail').parse().to_sql()
    Traceback (most recent call last):
    ...
    ValueError: Bad expression: 'fail'
    >>> e = [('fail', 'is', 'True')]
    >>> expression(e).parse().to_sql()
    Traceback (most recent call last):
    ...
    ValueError: Bad expression: ('&', ('fail', 'is', 'True'))
    """

    def _is_operator(self, element):
        return isinstance(element, str) \
           and element in ['&','|']

    def _is_leaf(self, element):
        return isinstance(element, tuple) \
           and len(element) == 3 \
           and element[1] in ('=', '<>', '<=', '<', '>', '>=', '=like', 'like', 'not like', 'ilike', 'not ilike', 'in', 'not in', 'child_of') 

    def _is_expression(self, element):
        return isinstance(element, tuple) \
           and len(element) > 2 \
           and self._is_operator(element[0])

    
    def __execute_recursive_in(self, cr, s, f, w, ids):
        ID_MAX = 1000
        res = []
        for i in range(0, len(ids), ID_MAX):
            subids = ids[i:i+ID_MAX]
            cr.execute('SELECT "%s"'    \
                       '  FROM "%s"'    \
                       ' WHERE "%s" in (%s)' % (s, f, w, ','.join(['%d']*len(subids))),
                       subids)
            res.extend([r[0] for r in cr.fetchall()])
        return res


    def __init__(self, exp):
        if exp and isinstance(exp, tuple):
            if not self._is_leaf(exp) and not self._is_operator(exp[0]):
                exp = list(exp)
        if exp and isinstance(exp, list):
            if len(exp) == 1 and self._is_leaf(exp[0]):
                exp = exp[0]
            else:
                if not self._is_operator(exp[0][0]):
                    exp.insert(0, '&')
                    exp = tuple(exp)
                else:
                    exp = exp[0]

        self.__exp = exp
        self.__operator = '&'
        self.__children = []

        self.__tables = []
        self.__joins = []
        self.__table = None

        self.__left, self.__right = None, None
        if self._is_leaf(self.__exp):
            self.__left, self.__operator, self.__right = self.__exp
            if isinstance(self.__right, list):
                self.__right = tuple(self.__right)
        elif exp and not self._is_expression(self.__exp):
            raise ValueError, 'Bad expression: %r' % (self.__exp,)

    def parse(self, cr, uid, table, context):

        def _rec_get(ids, table, parent):
            if not ids:
                return []
            ids2 = table.search(cr, uid, [(parent, 'in', ids)], context=context)
            return ids + _rec_get(ids2, table, parent)
        
        if not self.__exp:
            return self

        if self._is_leaf(self.__exp):
            self.__table = table
            self.__tables.append(self.__table._table)
            if self.__left in table._inherit_fields:
                self.__table = table.pool.get(table._inherit_fields[self.__left][0])
                if self.__table._table not in self.__tables:
                    self.__tables.append(self.__table._table)
                    self.__joins.append('%s.%s' % (table._table, table._inherits[self.__table._name]))
            fargs = self.__left.split('.', 1)
            field = self.__table._columns.get(fargs[0], False)
            if not field:
                if self.__left == 'id' and self.__operator == 'child_of':
                    self.__right += _rec_get(self.__right, self.__table, self.__table._parent_name)
                    self.__operator = 'in'
                return self
            if len(fargs) > 1:
                if field._type == 'many2one':
                    self.__left = fargs[0]
                    self.__right = table.pool.get(field._obj).search(cr, uid, [(fargs[1], self.__operator, self.__right)], context=context)
                    self.__operator = 'in'
                return self
            
            field_obj = table.pool.get(field._obj)
            if field._properties:
                # this is a function field
                if not field._fnct_search and not field.store:
                    # the function field doesn't provide a search function and doesn't store values in the database, so we must ignore it : we generate a dummy leaf
                    self.__left, self__operator, self.__right = 1, '=', 1
                    self.__exp = '' # force to generate an empty sql expression
                else:
                    # we need to replace this leaf to a '&' expression
                    # we clone ourself...
                    import copy
                    newexp = copy.copy(self)
                    self.__table = None
                    self.__tables, self.__joins = [], []
                    self.__children = []
                    
                    if field._fnct_search:
                        subexp = field.search(cr, uid, table, self.__left, [self.__exp])
                        self.__children.append(expression(subexp).parse(cr, uid, table, context))
                    if field.store:
                        self.__children.append(newexp)

                    self.__left, self.__right = None, None
                    self.__operator = '&'
                    self.__exp = ('&',) + tuple( [tuple(e.__exp) for e in self.__children] )

            elif field._type == 'one2many':
                if isinstance(self.__right, basestring):
                    ids2 = [x[0] for x in field_obj.name_search(cr, uid, self.__right, [], self.__operator)]
                else:
                    ids2 = self.__right
                if not ids2:
                    self.__left, self.__operator, self.__right = 'id', '=', '0'
                else:
                    self.__left, self.__operator, self.__right = 'id', 'in', self.__execute_recursive_in(cr, field._fields_id, field_obj._table, 'id', ids2)

            elif field._type == 'many2many':
                #FIXME
                if self.__operator == 'child_of':
                    if isinstance(self.__right, basestring):
                        ids2 = [x[0] for x in field_obj.name_search(cr, uid, self.__right, [], 'like')]
                    else:
                        ids2 = self.__right
                   
                    def _rec_convert(ids):
                        if field_obj == table:
                            return ids
                        return self.__execute_recursive_in(cr, field._id1, field._rel, field._id2, ids)
                    
                    self.__left, self.__operator, self.__right = 'id', 'in', _rec_convert(ids2 + _rec_get(ids2, field_obj, self.__table._parent_name))
                else:
                    if isinstance(self.__right, basestring):
                        res_ids = [x[0] for x in field_obj.name_search(cr, uid, self.__right, [], self.__operator)]
                    else:
                        res_ids = self.__right
                    self.__left, self.__operator, self.__right = 'id', 'in', self.__execute_recursive_in(cr, field._id1, field._rel, field._id2, res_ids) or [0]
            elif field._type == 'many2one':
                if self.__operator == 'child_of':
                    if isinstance(self.__right, basestring):
                        ids2 = [x[0] for x in field_obj.search_name(cr, uid, self.__right, [], 'like')]
                    else:
                        ids2 = list(self.__right)
                        
                    self.__operator = 'in'
                    if field._obj <> self.__table._name:
                        self.__right = ids2 + _rec_get(ids2, field_obj, self.__table._parent_name)
                    else:
                        self.__right = ids2 + _rec_get(ids2, self.__table, self.__left)
                        self.__left = 'id'
                else:
                    if isinstance(self.__right, basestring):
                        res_ids = field_obj.name_search(cr, uid, self.__right, [], self.__operator)
                        self.__operator = 'in'
                        self.__right = map(lambda x: x[0], res_ids)
            else: 
                # other field type
                if field.translate:
                    if self.__operator in ('like', 'ilike', 'not like', 'not ilike'):
                        self.__right = '%%%s%%' % self.__right

                    query1 = '( SELECT res_id'          \
                             '    FROM ir_translation'  \
                             '   WHERE name = %s'       \
                             '     AND lang = %s'       \
                             '     AND type = %s'       \
                             '     AND value ' + self.__operator + ' %s'    \
                             ') UNION ('                \
                             '  SELECT id'              \
                             '    FROM "' + self.__table._table + '"'       \
                             '   WHERE "' + self.__left + '" ' + self.__operator + ' %s' \
                             ')'
                    query2 = [self.__table._name + ',' + self.__left,
                              context.get('lang', False) or 'en_US',
                              'model',
                              self.__right,
                              self.__right,
                             ]

                    self.__left = 'id'
                    self.__operator = 'inselect'
                    self.__right = (query1, query2,)


        elif self._is_expression(self.__exp):
            self.__operator = self.__exp[0]

            for element in self.__exp[1:]:
                if not self._is_operator(element):
                    self.__children.append(expression(element).parse(cr, uid, table, context))
        return self

    def to_sql(self):
        if not self.__exp:
            return ('', [])
        elif self._is_leaf(self.__exp):
            if self.__operator == 'inselect':
                query = '(%s.%s in (%s))' % (self.__table._table, self.__left, self.__right[0])
                params = self.__right[1]
            elif self.__operator in ['in', 'not in']:
                params = self.__right[:]
                len_before = len(params)
                for i in range(len_before)[::-1]:
                    if params[i] == False:
                        del params[i]

                len_after = len(params)
                check_nulls = len_after <> len_before
                query = '(1=0)'
                
                if len_after:
                    if self.__left == 'id':
                        instr = ','.join(['%d'] * len_after)
                    else:
                        instr = ','.join([self.__table._columns[self.__left]._symbol_set[0]] * len_after)

                    query = '(%s.%s %s (%s))' % (self.__table._table, self.__left, self.__operator, instr)

                if check_nulls:
                    query = '(%s OR %s IS NULL)' % (query, self.__left)
            else:
                params = []
                if self.__right is False and self.__operator == '=':
                    query = '%s IS NULL' % self.__left
                elif self.__right is False and self.__operator == '<>':
                    query = '%s IS NOT NULL' % self.__left
                else:
                    if self.__left == 'id':
                        query = '%s.id %s %%s' % (self.__table._table, self.__operator)
                        params = self.__right
                    else:
                        like = self.__operator in ('like', 'ilike', 'not like', 'not ilike')

                        op = self.__operator == '=like' and 'like' or self.__operator
                        if self.__left in self.__table._columns:
                            format = like and '%s' or self.__table._columns[self.__left]._symbol_set[0]
                            query = '(%s.%s %s %s)' % (self.__table._table, self.__left, op, format)
                        else:
                            query = "(%s.%s %s '%s')" % (self.__table._table, self.__left, op, self.__right)
 
                        add_null = False
                        if like:
                            if isinstance(self.__right, str):
                                str_utf8 = self.__right
                            elif isinstance(self.__right, unicode):
                                str_utf8 = self.__right.encode('utf-8')
                            else:
                                str_utf8 = str(self.__right)
                            params = '%%%s%%' % str_utf8
                            add_null = not str_utf8
                        elif self.__left in self.__table._columns:
                            params = self.__table._columns[self.__left]._symbol_set[1](self.__right)

                        if add_null:
                            query = '(%s OR %s IS NULL)' % (query, self.__left)

            joins = ' AND '.join(map(lambda j: '%s.id = %s' % (self.__table._table, j), self.__joins))
            if joins:
                query = '(%s AND (%s))' % (joins, query)
            if isinstance(params, basestring):
                params = [params]
            return (query, params)

        else:
            children = [child.to_sql() for child in self.__children]
            params = flatten([child[1] for child in children])
            query = "( %s )" % (" %s " % {'&' : 'AND', '|' : 'OR' }[self.__operator]).join([child[0] for child in children if child[0]])
            return (query, params)

    def __get_tables(self):
        return self.__tables + [child.__get_tables() for child in self.__children]
    
    def get_tables(self):
        return [ '"%s"' % t for t in set(flatten(self.__get_tables()))]

    #def 

if __name__ == '__main__':
    pass
    #import doctest
    #doctest.testmod()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

