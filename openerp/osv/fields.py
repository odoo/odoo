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

# . Fields:
#      - simple
#      - relations (one2many, many2one, many2many)
#      - function
#
# Fields Attributes:
#   _classic_read: is a classic sql fields
#   _type   : field type
#   readonly
#   required
#   size
#
import datetime as DT
import string
import sys
import warnings
import xmlrpclib
from psycopg2 import Binary

import openerp.netsvc as netsvc
import openerp.tools as tools
from openerp.tools.translate import _

def _symbol_set(symb):
    if symb == None or symb == False:
        return None
    elif isinstance(symb, unicode):
        return symb.encode('utf-8')
    return str(symb)


class _column(object):
    _classic_read = True
    _classic_write = True
    _prefetch = True
    _properties = False
    _type = 'unknown'
    _obj = None
    _multi = False
    _symbol_c = '%s'
    _symbol_f = _symbol_set
    _symbol_set = (_symbol_c, _symbol_f)
    _symbol_get = None

    def __init__(self, string='unknown', required=False, readonly=False, domain=None, context=None, states=None, priority=0, change_default=False, size=None, ondelete="set null", translate=False, select=False, **args):
        if domain is None:
            domain = []
        if context is None:
            context = {}
        self.states = states or {}
        self.string = string
        self.readonly = readonly
        self.required = required
        self.size = size
        self.help = args.get('help', '')
        self.priority = priority
        self.change_default = change_default
        self.ondelete = ondelete
        self.translate = translate
        self._domain = domain
        self._context = context
        self.write = False
        self.read = False
        self.view_load = 0
        self.select = select
        self.selectable = True
        self.group_operator = args.get('group_operator', False)
        for a in args:
            if args[a]:
                setattr(self, a, args[a])

    def restart(self):
        pass

    def set(self, cr, obj, id, name, value, user=None, context=None):
        cr.execute('update '+obj._table+' set '+name+'='+self._symbol_set[0]+' where id=%s', (self._symbol_set[1](value), id))

    def set_memory(self, cr, obj, id, name, value, user=None, context=None):
        raise Exception(_('Not implemented set_memory method !'))

    def get_memory(self, cr, obj, ids, name, user=None, context=None, values=None):
        raise Exception(_('Not implemented get_memory method !'))

    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        raise Exception(_('undefined get method !'))

    def search(self, cr, obj, args, name, value, offset=0, limit=None, uid=None, context=None):
        ids = obj.search(cr, uid, args+self._domain+[(name, 'ilike', value)], offset, limit, context=context)
        res = obj.read(cr, uid, ids, [name], context=context)
        return [x[name] for x in res]

    def search_memory(self, cr, obj, args, name, value, offset=0, limit=None, uid=None, context=None):
        raise Exception(_('Not implemented search_memory method !'))


# ---------------------------------------------------------
# Simple fields
# ---------------------------------------------------------
class boolean(_column):
    _type = 'boolean'
    _symbol_c = '%s'
    _symbol_f = lambda x: x and 'True' or 'False'
    _symbol_set = (_symbol_c, _symbol_f)

class integer(_column):
    _type = 'integer'
    _symbol_c = '%s'
    _symbol_f = lambda x: int(x or 0)
    _symbol_set = (_symbol_c, _symbol_f)
    _symbol_get = lambda self,x: x or 0

class integer_big(_column):
    _type = 'integer_big'
    # do not reference the _symbol_* of integer class, as that would possibly
    # unbind the lambda functions
    _symbol_c = '%s'
    _symbol_f = lambda x: int(x or 0)
    _symbol_set = (_symbol_c, _symbol_f)
    _symbol_get = lambda self,x: x or 0

class reference(_column):
    _type = 'reference'
    def __init__(self, string, selection, size, **args):
        _column.__init__(self, string=string, size=size, selection=selection, **args)


class char(_column):
    _type = 'char'

    def __init__(self, string, size, **args):
        _column.__init__(self, string=string, size=size, **args)
        self._symbol_set = (self._symbol_c, self._symbol_set_char)

    # takes a string (encoded in utf8) and returns a string (encoded in utf8)
    def _symbol_set_char(self, symb):
        #TODO:
        # * we need to remove the "symb==False" from the next line BUT
        #   for now too many things rely on this broken behavior
        # * the symb==None test should be common to all data types
        if symb == None or symb == False:
            return None

        # we need to convert the string to a unicode object to be able
        # to evaluate its length (and possibly truncate it) reliably
        u_symb = tools.ustr(symb)

        return u_symb[:self.size].encode('utf8')


class text(_column):
    _type = 'text'

import __builtin__

class float(_column):
    _type = 'float'
    _symbol_c = '%s'
    _symbol_f = lambda x: __builtin__.float(x or 0.0)
    _symbol_set = (_symbol_c, _symbol_f)
    _symbol_get = lambda self,x: x or 0.0

    def __init__(self, string='unknown', digits=None, digits_compute=None, **args):
        _column.__init__(self, string=string, **args)
        self.digits = digits
        self.digits_compute = digits_compute


    def digits_change(self, cr):
        if self.digits_compute:
            t = self.digits_compute(cr)
            self._symbol_set=('%s', lambda x: ('%.'+str(t[1])+'f') % (__builtin__.float(x or 0.0),))
            self.digits = t

class date(_column):
    _type = 'date'
    @staticmethod
    def today(*args):
        """ Returns the current date in a format fit for being a
        default value to a ``date`` field.

        This method should be provided as is to the _defaults dict, it
        should not be called.
        """
        return DT.date.today().strftime(
            tools.DEFAULT_SERVER_DATE_FORMAT)

class datetime(_column):
    _type = 'datetime'
    @staticmethod
    def now(*args):
        """ Returns the current datetime in a format fit for being a
        default value to a ``datetime`` field.

        This method should be provided as is to the _defaults dict, it
        should not be called.
        """
        return DT.datetime.now().strftime(
            tools.DEFAULT_SERVER_DATETIME_FORMAT)

class time(_column):
    _type = 'time'
    @staticmethod
    def now( *args):
        """ Returns the current time in a format fit for being a
        default value to a ``time`` field.

        This method should be proivided as is to the _defaults dict,
        it should not be called.
        """
        return DT.datetime.now().strftime(
            tools.DEFAULT_SERVER_TIME_FORMAT)

class binary(_column):
    _type = 'binary'
    _symbol_c = '%s'
    _symbol_f = lambda symb: symb and Binary(symb) or None
    _symbol_set = (_symbol_c, _symbol_f)
    _symbol_get = lambda self, x: x and str(x)

    _classic_read = False
    _prefetch = False

    def __init__(self, string='unknown', filters=None, **args):
        _column.__init__(self, string=string, **args)
        self.filters = filters

    def get_memory(self, cr, obj, ids, name, user=None, context=None, values=None):
        if not context:
            context = {}
        if not values:
            values = []
        res = {}
        for i in ids:
            val = None
            for v in values:
                if v['id'] == i:
                    val = v[name]
                    break

            # If client is requesting only the size of the field, we return it instead
            # of the content. Presumably a separate request will be done to read the actual
            # content if it's needed at some point.
            # TODO: after 6.0 we should consider returning a dict with size and content instead of
            #       having an implicit convention for the value
            if val and context.get('bin_size_%s' % name, context.get('bin_size')):
                res[i] = tools.human_size(long(val))
            else:
                res[i] = val
        return res

    get = get_memory


class selection(_column):
    _type = 'selection'

    def __init__(self, selection, string='unknown', **args):
        _column.__init__(self, string=string, **args)
        self.selection = selection

# ---------------------------------------------------------
# Relationals fields
# ---------------------------------------------------------

#
# Values: (0, 0,  { fields })    create
#         (1, ID, { fields })    update
#         (2, ID)                remove (delete)
#         (3, ID)                unlink one (target id or target of relation)
#         (4, ID)                link
#         (5)                    unlink all (only valid for one2many)
#
#CHECKME: dans la pratique c'est quoi la syntaxe utilisee pour le 5? (5) ou (5, 0)?
class one2one(_column):
    _classic_read = False
    _classic_write = True
    _type = 'one2one'

    def __init__(self, obj, string='unknown', **args):
        warnings.warn("The one2one field doesn't work anymore", DeprecationWarning)
        _column.__init__(self, string=string, **args)
        self._obj = obj

    def set(self, cr, obj_src, id, field, act, user=None, context=None):
        if not context:
            context = {}
        obj = obj_src.pool.get(self._obj)
        self._table = obj_src.pool.get(self._obj)._table
        if act[0] == 0:
            id_new = obj.create(cr, user, act[1])
            cr.execute('update '+obj_src._table+' set '+field+'=%s where id=%s', (id_new, id))
        else:
            cr.execute('select '+field+' from '+obj_src._table+' where id=%s', (act[0],))
            id = cr.fetchone()[0]
            obj.write(cr, user, [id], act[1], context=context)

    def search(self, cr, obj, args, name, value, offset=0, limit=None, uid=None, context=None):
        return obj.pool.get(self._obj).search(cr, uid, args+self._domain+[('name', 'like', value)], offset, limit, context=context)


class many2one(_column):
    _classic_read = False
    _classic_write = True
    _type = 'many2one'
    _symbol_c = '%s'
    _symbol_f = lambda x: x or None
    _symbol_set = (_symbol_c, _symbol_f)

    def __init__(self, obj, string='unknown', **args):
        _column.__init__(self, string=string, **args)
        self._obj = obj

    def set_memory(self, cr, obj, id, field, values, user=None, context=None):
        obj.datas.setdefault(id, {})
        obj.datas[id][field] = values

    def get_memory(self, cr, obj, ids, name, user=None, context=None, values=None):
        result = {}
        for id in ids:
            result[id] = obj.datas[id].get(name, False)

        # build a dictionary of the form {'id_of_distant_resource': name_of_distant_resource}
        # we use uid=1 because the visibility of a many2one field value (just id and name)
        # must be the access right of the parent form and not the linked object itself.
        obj = obj.pool.get(self._obj)
        records = dict(obj.name_get(cr, 1,
                                    list(set([x for x in result.values() if x and isinstance(x, (int,long))])),
                                    context=context))
        for id in ids:
            if result[id] in records:
                result[id] = (result[id], records[result[id]])
            else:
                result[id] = False

        return result

    def get(self, cr, obj, ids, name, user=None, context=None, values=None):
        if context is None:
            context = {}
        if values is None:
            values = {}

        res = {}
        for r in values:
            res[r['id']] = r[name]
        for id in ids:
            res.setdefault(id, '')
        obj = obj.pool.get(self._obj)

        # build a dictionary of the form {'id_of_distant_resource': name_of_distant_resource}
        # we use uid=1 because the visibility of a many2one field value (just id and name)
        # must be the access right of the parent form and not the linked object itself.
        records = dict(obj.name_get(cr, 1,
                                    list(set([x for x in res.values() if isinstance(x, (int,long))])),
                                    context=context))
        for id in res:
            if res[id] in records:
                res[id] = (res[id], records[res[id]])
            else:
                res[id] = False
        return res

    def set(self, cr, obj_src, id, field, values, user=None, context=None):
        if not context:
            context = {}
        obj = obj_src.pool.get(self._obj)
        self._table = obj_src.pool.get(self._obj)._table
        if type(values) == type([]):
            for act in values:
                if act[0] == 0:
                    id_new = obj.create(cr, act[2])
                    cr.execute('update '+obj_src._table+' set '+field+'=%s where id=%s', (id_new, id))
                elif act[0] == 1:
                    obj.write(cr, [act[1]], act[2], context=context)
                elif act[0] == 2:
                    cr.execute('delete from '+self._table+' where id=%s', (act[1],))
                elif act[0] == 3 or act[0] == 5:
                    cr.execute('update '+obj_src._table+' set '+field+'=null where id=%s', (id,))
                elif act[0] == 4:
                    cr.execute('update '+obj_src._table+' set '+field+'=%s where id=%s', (act[1], id))
        else:
            if values:
                cr.execute('update '+obj_src._table+' set '+field+'=%s where id=%s', (values, id))
            else:
                cr.execute('update '+obj_src._table+' set '+field+'=null where id=%s', (id,))

    def search(self, cr, obj, args, name, value, offset=0, limit=None, uid=None, context=None):
        return obj.pool.get(self._obj).search(cr, uid, args+self._domain+[('name', 'like', value)], offset, limit, context=context)


class one2many(_column):
    _classic_read = False
    _classic_write = False
    _prefetch = False
    _type = 'one2many'

    def __init__(self, obj, fields_id, string='unknown', limit=None, **args):
        _column.__init__(self, string=string, **args)
        self._obj = obj
        self._fields_id = fields_id
        self._limit = limit
        #one2many can't be used as condition for defaults
        assert(self.change_default != True)

    def get_memory(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if context is None:
            context = {}
        if self._context:
            context = context.copy()
            context.update(self._context)
        if not values:
            values = {}
        res = {}
        for id in ids:
            res[id] = []
        ids2 = obj.pool.get(self._obj).search(cr, user, [(self._fields_id, 'in', ids)], limit=self._limit, context=context)
        for r in obj.pool.get(self._obj).read(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
            if r[self._fields_id] in res:
                res[r[self._fields_id]].append(r['id'])
        return res

    def set_memory(self, cr, obj, id, field, values, user=None, context=None):
        if not context:
            context = {}
        if self._context:
            context = context.copy()
        context.update(self._context)
        if not values:
            return
        obj = obj.pool.get(self._obj)
        for act in values:
            if act[0] == 0:
                act[2][self._fields_id] = id
                obj.create(cr, user, act[2], context=context)
            elif act[0] == 1:
                obj.write(cr, user, [act[1]], act[2], context=context)
            elif act[0] == 2:
                obj.unlink(cr, user, [act[1]], context=context)
            elif act[0] == 3:
                obj.datas[act[1]][self._fields_id] = False
            elif act[0] == 4:
                obj.datas[act[1]][self._fields_id] = id
            elif act[0] == 5:
                for o in obj.datas.values():
                    if o[self._fields_id] == id:
                        o[self._fields_id] = False
            elif act[0] == 6:
                for id2 in (act[2] or []):
                    obj.datas[id2][self._fields_id] = id

    def search_memory(self, cr, obj, args, name, value, offset=0, limit=None, uid=None, operator='like', context=None):
        raise _('Not Implemented')

    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if context is None:
            context = {}
        if self._context:
            context = context.copy()
        context.update(self._context)
        if values is None:
            values = {}

        res = {}
        for id in ids:
            res[id] = []

        ids2 = obj.pool.get(self._obj).search(cr, user, self._domain + [(self._fields_id, 'in', ids)], limit=self._limit, context=context)
        for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
            if r[self._fields_id] in res:
                res[r[self._fields_id]].append(r['id'])
        return res

    def set(self, cr, obj, id, field, values, user=None, context=None):
        result = []
        if not context:
            context = {}
        if self._context:
            context = context.copy()
        context.update(self._context)
        context['no_store_function'] = True
        if not values:
            return
        _table = obj.pool.get(self._obj)._table
        obj = obj.pool.get(self._obj)
        for act in values:
            if act[0] == 0:
                act[2][self._fields_id] = id
                id_new = obj.create(cr, user, act[2], context=context)
                result += obj._store_get_values(cr, user, [id_new], act[2].keys(), context)
            elif act[0] == 1:
                obj.write(cr, user, [act[1]], act[2], context=context)
            elif act[0] == 2:
                obj.unlink(cr, user, [act[1]], context=context)
            elif act[0] == 3:
                cr.execute('update '+_table+' set '+self._fields_id+'=null where id=%s', (act[1],))
            elif act[0] == 4:
                # Must use write() to recompute parent_store structure if needed
                obj.write(cr, user, [act[1]], {self._fields_id:id}, context=context or {})
            elif act[0] == 5:
                cr.execute('update '+_table+' set '+self._fields_id+'=null where '+self._fields_id+'=%s', (id,))
            elif act[0] == 6:
                # Must use write() to recompute parent_store structure if needed
                obj.write(cr, user, act[2], {self._fields_id:id}, context=context or {})
                ids2 = act[2] or [0]
                cr.execute('select id from '+_table+' where '+self._fields_id+'=%s and id <> ALL (%s)', (id,ids2))
                ids3 = map(lambda x:x[0], cr.fetchall())
                obj.write(cr, user, ids3, {self._fields_id:False}, context=context or {})
        return result

    def search(self, cr, obj, args, name, value, offset=0, limit=None, uid=None, operator='like', context=None):
        return obj.pool.get(self._obj).name_search(cr, uid, value, self._domain, operator, context=context,limit=limit)


#
# Values: (0, 0,  { fields })    create
#         (1, ID, { fields })    update (write fields to ID)
#         (2, ID)                remove (calls unlink on ID, that will also delete the relationship because of the ondelete)
#         (3, ID)                unlink (delete the relationship between the two objects but does not delete ID)
#         (4, ID)                link (add a relationship)
#         (5, ID)                unlink all
#         (6, ?, ids)            set a list of links
#
class many2many(_column):
    _classic_read = False
    _classic_write = False
    _prefetch = False
    _type = 'many2many'
    def __init__(self, obj, rel, id1, id2, string='unknown', limit=None, **args):
        _column.__init__(self, string=string, **args)
        self._obj = obj
        if '.' in rel:
            raise Exception(_('The second argument of the many2many field %s must be a SQL table !'\
                'You used %s, which is not a valid SQL table name.')% (string,rel))
        self._rel = rel
        self._id1 = id1
        self._id2 = id2
        self._limit = limit

    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        if not context:
            context = {}
        if not values:
            values = {}
        res = {}
        if not ids:
            return res
        for id in ids:
            res[id] = []
        if offset:
            warnings.warn("Specifying offset at a many2many.get() may produce unpredictable results.",
                      DeprecationWarning, stacklevel=2)
        obj = obj.pool.get(self._obj)

        # static domains are lists, and are evaluated both here and on client-side, while string
        # domains supposed by dynamic and evaluated on client-side only (thus ignored here)
        # FIXME: make this distinction explicit in API!
        domain = isinstance(self._domain, list) and self._domain or []

        wquery = obj._where_calc(cr, user, domain, context=context)
        obj._apply_ir_rules(cr, user, wquery, 'read', context=context)
        from_c, where_c, where_params = wquery.get_sql()
        if where_c:
            where_c = ' AND ' + where_c

        if offset or self._limit:
            order_by = ' ORDER BY "%s".%s' %(obj._table, obj._order.split(',')[0])
        else:
            order_by = ''

        limit_str = ''
        if self._limit is not None:
            limit_str = ' LIMIT %d' % self._limit

        query = 'SELECT %(rel)s.%(id2)s, %(rel)s.%(id1)s \
                   FROM %(rel)s, %(from_c)s \
                  WHERE %(rel)s.%(id1)s IN %%s \
                    AND %(rel)s.%(id2)s = %(tbl)s.id \
                 %(where_c)s  \
                 %(order_by)s \
                 %(limit)s \
                 OFFSET %(offset)d' \
            % {'rel': self._rel,
               'from_c': from_c,
               'tbl': obj._table,
               'id1': self._id1,
               'id2': self._id2,
               'where_c': where_c,
               'limit': limit_str,
               'order_by': order_by,
               'offset': offset,
              }
        cr.execute(query, [tuple(ids),] + where_params)
        for r in cr.fetchall():
            res[r[1]].append(r[0])
        return res

    def set(self, cr, obj, id, name, values, user=None, context=None):
        if not context:
            context = {}
        if not values:
            return
        obj = obj.pool.get(self._obj)
        for act in values:
            if not (isinstance(act, list) or isinstance(act, tuple)) or not act:
                continue
            if act[0] == 0:
                idnew = obj.create(cr, user, act[2])
                cr.execute('insert into '+self._rel+' ('+self._id1+','+self._id2+') values (%s,%s)', (id, idnew))
            elif act[0] == 1:
                obj.write(cr, user, [act[1]], act[2], context=context)
            elif act[0] == 2:
                obj.unlink(cr, user, [act[1]], context=context)
            elif act[0] == 3:
                cr.execute('delete from '+self._rel+' where ' + self._id1 + '=%s and '+ self._id2 + '=%s', (id, act[1]))
            elif act[0] == 4:
                # following queries are in the same transaction - so should be relatively safe
                cr.execute('SELECT 1 FROM '+self._rel+' WHERE '+self._id1+' = %s and '+self._id2+' = %s', (id, act[1]))
                if not cr.fetchone():
                    cr.execute('insert into '+self._rel+' ('+self._id1+','+self._id2+') values (%s,%s)', (id, act[1]))
            elif act[0] == 5:
                cr.execute('update '+self._rel+' set '+self._id2+'=null where '+self._id2+'=%s', (id,))
            elif act[0] == 6:

                d1, d2,tables = obj.pool.get('ir.rule').domain_get(cr, user, obj._name, context=context)
                if d1:
                    d1 = ' and ' + ' and '.join(d1)
                else:
                    d1 = ''
                cr.execute('delete from '+self._rel+' where '+self._id1+'=%s AND '+self._id2+' IN (SELECT '+self._rel+'.'+self._id2+' FROM '+self._rel+', '+','.join(tables)+' WHERE '+self._rel+'.'+self._id1+'=%s AND '+self._rel+'.'+self._id2+' = '+obj._table+'.id '+ d1 +')', [id, id]+d2)

                for act_nbr in act[2]:
                    cr.execute('insert into '+self._rel+' ('+self._id1+','+self._id2+') values (%s, %s)', (id, act_nbr))

    #
    # TODO: use a name_search
    #
    def search(self, cr, obj, args, name, value, offset=0, limit=None, uid=None, operator='like', context=None):
        return obj.pool.get(self._obj).search(cr, uid, args+self._domain+[('name', operator, value)], offset, limit, context=context)

    def get_memory(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        result = {}
        for id in ids:
            result[id] = obj.datas[id].get(name, [])
        return result

    def set_memory(self, cr, obj, id, name, values, user=None, context=None):
        if not values:
            return
        for act in values:
            # TODO: use constants instead of these magic numbers
            if act[0] == 0:
                raise _('Not Implemented')
            elif act[0] == 1:
                raise _('Not Implemented')
            elif act[0] == 2:
                raise _('Not Implemented')
            elif act[0] == 3:
                raise _('Not Implemented')
            elif act[0] == 4:
                raise _('Not Implemented')
            elif act[0] == 5:
                raise _('Not Implemented')
            elif act[0] == 6:
                obj.datas[id][name] = act[2]


def get_nice_size(a):
    (x,y) = a
    if isinstance(y, (int,long)):
        size = y
    elif y:
        size = len(y)
    else:
        size = 0
    return (x, tools.human_size(size))

def sanitize_binary_value(dict_item):
    # binary fields should be 7-bit ASCII base64-encoded data,
    # but we do additional sanity checks to make sure the values
    # are not something else that won't pass via xmlrpc
    index, value = dict_item
    if isinstance(value, (xmlrpclib.Binary, tuple, list, dict)):
        # these builtin types are meant to pass untouched
        return index, value

    # For all other cases, handle the value as a binary string:
    # it could be a 7-bit ASCII string (e.g base64 data), but also
    # any 8-bit content from files, with byte values that cannot
    # be passed inside XML!
    # See for more info:
    #  - http://bugs.python.org/issue10066
    #  - http://www.w3.org/TR/2000/REC-xml-20001006#NT-Char
    #
    # One solution is to convert the byte-string to unicode,
    # so it gets serialized as utf-8 encoded data (always valid XML)
    # If invalid XML byte values were present, tools.ustr() uses
    # the Latin-1 codec as fallback, which converts any 8-bit
    # byte value, resulting in valid utf-8-encoded bytes
    # in the end:
    #  >>> unicode('\xe1','latin1').encode('utf8') == '\xc3\xa1'
    # Note: when this happens, decoding on the other endpoint
    # is not likely to produce the expected output, but this is
    # just a safety mechanism (in these cases base64 data or
    # xmlrpc.Binary values should be used instead)
    return index, tools.ustr(value)


# ---------------------------------------------------------
# Function fields
# ---------------------------------------------------------
class function(_column):
    _classic_read = False
    _classic_write = False
    _prefetch = False
    _type = 'function'
    _properties = True

#
# multi: compute several fields in one call
#
    def __init__(self, fnct, arg=None, fnct_inv=None, fnct_inv_arg=None, type='float', fnct_search=None, obj=None, method=False, store=False, multi=False, **args):
        _column.__init__(self, **args)
        self._obj = obj
        self._method = method
        self._fnct = fnct
        self._fnct_inv = fnct_inv
        self._arg = arg
        self._multi = multi
        if 'relation' in args:
            self._obj = args['relation']

        self.digits = args.get('digits', (16,2))
        self.digits_compute = args.get('digits_compute', None)

        self._fnct_inv_arg = fnct_inv_arg
        if not fnct_inv:
            self.readonly = 1
        self._type = type
        self._fnct_search = fnct_search
        self.store = store

        if not fnct_search and not store:
            self.selectable = False

        if store:
            if self._type != 'many2one':
                # m2o fields need to return tuples with name_get, not just foreign keys
                self._classic_read = True
            self._classic_write = True
            if type=='binary':
                self._symbol_get=lambda x:x and str(x)

        if type == 'float':
            self._symbol_c = float._symbol_c
            self._symbol_f = float._symbol_f
            self._symbol_set = float._symbol_set

        if type == 'boolean':
            self._symbol_c = boolean._symbol_c
            self._symbol_f = boolean._symbol_f
            self._symbol_set = boolean._symbol_set

        if type in ['integer','integer_big']:
            self._symbol_c = integer._symbol_c
            self._symbol_f = integer._symbol_f
            self._symbol_set = integer._symbol_set

    def digits_change(self, cr):
        if self.digits_compute:
            t = self.digits_compute(cr)
            self._symbol_set=('%s', lambda x: ('%.'+str(t[1])+'f') % (__builtin__.float(x or 0.0),))
            self.digits = t


    def search(self, cr, uid, obj, name, args, context=None):
        if not self._fnct_search:
            #CHECKME: should raise an exception
            return []
        return self._fnct_search(obj, cr, uid, obj, name, args, context=context)

    def get(self, cr, obj, ids, name, user=None, context=None, values=None):
        if context is None:
            context = {}
        if values is None:
            values = {}
        res = {}
        if self._method:
            res = self._fnct(obj, cr, user, ids, name, self._arg, context)
        else:
            res = self._fnct(cr, obj._table, ids, name, self._arg, context)

        if self._type == "many2one" :
            # Filtering only integer/long values if passed
            res_ids = [x for x in res.values() if x and isinstance(x, (int,long))]

            if res_ids:
                obj_model = obj.pool.get(self._obj)
                dict_names = dict(obj_model.name_get(cr, user, res_ids, context))
                for r in res.keys():
                    if res[r] and res[r] in dict_names:
                        res[r] = (res[r], dict_names[res[r]])

        if self._type == 'binary':
            if context.get('bin_size', False):
                # client requests only the size of binary fields
                res = dict(map(get_nice_size, res.items()))
            else:
                res = dict(map(sanitize_binary_value, res.items()))

        if self._type == "integer":
            for r in res.keys():
                # Converting value into string so that it does not affect XML-RPC Limits
                if isinstance(res[r],dict): # To treat integer values with _multi attribute
                    for record in res[r].keys():
                        res[r][record] = str(res[r][record])
                else:
                    res[r] = str(res[r])
        return res
    get_memory = get

    def set(self, cr, obj, id, name, value, user=None, context=None):
        if not context:
            context = {}
        if self._fnct_inv:
            self._fnct_inv(obj, cr, user, id, name, value, self._fnct_inv_arg, context)
    set_memory = set

# ---------------------------------------------------------
# Related fields
# ---------------------------------------------------------

class related(function):

    def _fnct_search(self, tobj, cr, uid, obj=None, name=None, domain=None, context=None):
        self._field_get2(cr, uid, obj, context)
        i = len(self._arg)-1
        sarg = name
        while i>0:
            if type(sarg) in [type([]), type( (1,) )]:
                where = [(self._arg[i], 'in', sarg)]
            else:
                where = [(self._arg[i], '=', sarg)]
            if domain:
                where = map(lambda x: (self._arg[i],x[1], x[2]), domain)
                domain = []
            sarg = obj.pool.get(self._relations[i]['object']).search(cr, uid, where, context=context)
            i -= 1
        return [(self._arg[0], 'in', sarg)]

    def _fnct_write(self,obj,cr, uid, ids, field_name, values, args, context=None):
        self._field_get2(cr, uid, obj, context=context)
        if type(ids) != type([]):
            ids=[ids]
        objlst = obj.browse(cr, uid, ids)
        for data in objlst:
            t_id = data.id
            t_data = data
            for i in range(len(self.arg)):
                if not t_data: break
                field_detail = self._relations[i]
                if not t_data[self.arg[i]]:
                    if self._type not in ('one2many', 'many2many'):
                        t_id = t_data['id']
                    t_data = False
                elif field_detail['type'] in ('one2many', 'many2many'):
                    if self._type != "many2one":
                        t_id = t_data.id
                        t_data = t_data[self.arg[i]][0]
                    else:
                        t_data = False
                else:
                    t_id = t_data['id']
                    t_data = t_data[self.arg[i]]
            else:
                model = obj.pool.get(self._relations[-1]['object'])
                model.write(cr, uid, [t_id], {args[-1]: values}, context=context)

    def _fnct_read(self, obj, cr, uid, ids, field_name, args, context=None):
        self._field_get2(cr, uid, obj, context)
        if not ids: return {}
        relation = obj._name
        if self._type in ('one2many', 'many2many'):
            res = dict([(i, []) for i in ids])
        else:
            res = {}.fromkeys(ids, False)

        objlst = obj.browse(cr, 1, ids, context=context)
        for data in objlst:
            if not data:
                continue
            t_data = data
            relation = obj._name
            for i in range(len(self.arg)):
                field_detail = self._relations[i]
                relation = field_detail['object']
                try:
                    if not t_data[self.arg[i]]:
                        t_data = False
                        break
                except:
                    t_data = False
                    break
                if field_detail['type'] in ('one2many', 'many2many') and i != len(self.arg) - 1:
                    t_data = t_data[self.arg[i]][0]
                elif t_data:
                    t_data = t_data[self.arg[i]]
            if type(t_data) == type(objlst[0]):
                res[data.id] = t_data.id
            elif t_data:
                res[data.id] = t_data
        if self._type=='many2one':
            ids = filter(None, res.values())
            if ids:
                ng = dict(obj.pool.get(self._obj).name_get(cr, 1, ids, context=context))
                for r in res:
                    if res[r]:
                        res[r] = (res[r], ng[res[r]])
        elif self._type in ('one2many', 'many2many'):
            for r in res:
                if res[r]:
                    res[r] = [x.id for x in res[r]]
        return res

    def __init__(self, *arg, **args):
        self.arg = arg
        self._relations = []
        super(related, self).__init__(self._fnct_read, arg, self._fnct_write, fnct_inv_arg=arg, method=True, fnct_search=self._fnct_search, **args)
        if self.store is True:
            # TODO: improve here to change self.store = {...} according to related objects
            pass

    def _field_get2(self, cr, uid, obj, context=None):
        if self._relations:
            return
        obj_name = obj._name
        for i in range(len(self._arg)):
            f = obj.pool.get(obj_name).fields_get(cr, uid, [self._arg[i]], context=context)[self._arg[i]]
            self._relations.append({
                'object': obj_name,
                'type': f['type']

            })
            if f.get('relation',False):
                obj_name = f['relation']
                self._relations[-1]['relation'] = f['relation']

# ---------------------------------------------------------
# Dummy fields
# ---------------------------------------------------------

class dummy(function):
    def _fnct_search(self, tobj, cr, uid, obj=None, name=None, domain=None, context=None):
        return []

    def _fnct_write(self, obj, cr, uid, ids, field_name, values, args, context=None):
        return False

    def _fnct_read(self, obj, cr, uid, ids, field_name, args, context=None):
        return {}

    def __init__(self, *arg, **args):
        self.arg = arg
        self._relations = []
        super(dummy, self).__init__(self._fnct_read, arg, self._fnct_write, fnct_inv_arg=arg, method=True, fnct_search=None, **args)

# ---------------------------------------------------------
# Serialized fields
# ---------------------------------------------------------
class serialized(_column):
    def __init__(self, string='unknown', serialize_func=repr, deserialize_func=eval, type='text', **args):
        self._serialize_func = serialize_func
        self._deserialize_func = deserialize_func
        self._type = type
        self._symbol_set = (self._symbol_c, self._serialize_func)
        self._symbol_get = self._deserialize_func
        super(serialized, self).__init__(string=string, **args)


# TODO: review completly this class for speed improvement
class property(function):

    def _get_default(self, obj, cr, uid, prop_name, context=None):
        return self._get_defaults(obj, cr, uid, [prop_name], context=None)[0][prop_name]

    def _get_defaults(self, obj, cr, uid, prop_name, context=None):
        prop = obj.pool.get('ir.property')
        domain = [('fields_id.model', '=', obj._name), ('fields_id.name','in',prop_name), ('res_id','=',False)]
        ids = prop.search(cr, uid, domain, context=context)
        replaces = {}
        default_value = {}.fromkeys(prop_name, False)
        for prop_rec in prop.browse(cr, uid, ids, context=context):
            if default_value.get(prop_rec.fields_id.name, False):
                continue
            value = prop.get_by_record(cr, uid, prop_rec, context=context) or False
            default_value[prop_rec.fields_id.name] = value
            if value and (prop_rec.type == 'many2one'):
                replaces.setdefault(value._name, {})
                replaces[value._name][value.id] = True
        return default_value, replaces

    def _get_by_id(self, obj, cr, uid, prop_name, ids, context=None):
        prop = obj.pool.get('ir.property')
        vids = [obj._name + ',' + str(oid) for oid in  ids]

        domain = [('fields_id.model', '=', obj._name), ('fields_id.name','in',prop_name)]
        #domain = prop._get_domain(cr, uid, prop_name, obj._name, context)
        if vids:
            domain = [('res_id', 'in', vids)] + domain
        return prop.search(cr, uid, domain, context=context)

    # TODO: to rewrite more clean
    def _fnct_write(self, obj, cr, uid, id, prop_name, id_val, obj_dest, context=None):
        if context is None:
            context = {}

        nids = self._get_by_id(obj, cr, uid, [prop_name], [id], context)
        if nids:
            cr.execute('DELETE FROM ir_property WHERE id IN %s', (tuple(nids),))

        default_val = self._get_default(obj, cr, uid, prop_name, context)

        if id_val is not default_val:
            def_id = self._field_get(cr, uid, obj._name, prop_name)
            company = obj.pool.get('res.company')
            cid = company._company_default_get(cr, uid, obj._name, def_id,
                                               context=context)
            propdef = obj.pool.get('ir.model.fields').browse(cr, uid, def_id,
                                                             context=context)
            prop = obj.pool.get('ir.property')
            return prop.create(cr, uid, {
                'name': propdef.name,
                'value': id_val,
                'res_id': obj._name+','+str(id),
                'company_id': cid,
                'fields_id': def_id,
                'type': self._type,
            }, context=context)
        return False


    def _fnct_read(self, obj, cr, uid, ids, prop_name, obj_dest, context=None):
        properties = obj.pool.get('ir.property')
        domain = [('fields_id.model', '=', obj._name), ('fields_id.name','in',prop_name)]
        domain += [('res_id','in', [obj._name + ',' + str(oid) for oid in  ids])]
        nids = properties.search(cr, uid, domain, context=context)
        default_val,replaces = self._get_defaults(obj, cr, uid, prop_name, context)

        res = {}
        for id in ids:
            res[id] = default_val.copy()

        brs = properties.browse(cr, uid, nids, context=context)
        for prop in brs:
            value = properties.get_by_record(cr, uid, prop, context=context)
            res[prop.res_id.id][prop.fields_id.name] = value or False
            if value and (prop.type == 'many2one'):
                record_exists = obj.pool.get(value._name).exists(cr, uid, value.id)
                if record_exists:
                    replaces.setdefault(value._name, {})
                    replaces[value._name][value.id] = True
                else:
                    res[prop.res_id.id][prop.fields_id.name] = False

        for rep in replaces:
            nids = obj.pool.get(rep).search(cr, uid, [('id','in',replaces[rep].keys())], context=context)
            replaces[rep] = dict(obj.pool.get(rep).name_get(cr, uid, nids, context=context))

        for prop in prop_name:
            for id in ids:
                if res[id][prop] and hasattr(res[id][prop], '_name'):
                    res[id][prop] = (res[id][prop].id , replaces[res[id][prop]._name].get(res[id][prop].id, False))

        return res


    def _field_get(self, cr, uid, model_name, prop):
        if not self.field_id.get(cr.dbname):
            cr.execute('SELECT id \
                    FROM ir_model_fields \
                    WHERE name=%s AND model=%s', (prop, model_name))
            res = cr.fetchone()
            self.field_id[cr.dbname] = res and res[0]
        return self.field_id[cr.dbname]

    def __init__(self, obj_prop, **args):
        # TODO remove obj_prop parameter (use many2one type)
        self.field_id = {}
        function.__init__(self, self._fnct_read, False, self._fnct_write,
                          obj_prop, multi='properties', **args)

    def restart(self):
        self.field_id = {}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

