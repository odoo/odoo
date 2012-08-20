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

""" Fields:
      - simple
      - relations (one2many, many2one, many2many)
      - function

    Fields Attributes:
        * _classic_read: is a classic sql fields
        * _type   : field type
        * readonly
        * required
        * size
"""

import base64
import datetime as DT
import logging
import pytz
import re
import xmlrpclib
from psycopg2 import Binary

import openerp
import openerp.tools as tools
from openerp.tools.translate import _
from openerp.tools import float_round, float_repr
import simplejson
from openerp.tools.html_sanitize import html_sanitize

_logger = logging.getLogger(__name__)

def _symbol_set(symb):
    if symb is None or symb == False:
        return None
    elif isinstance(symb, unicode):
        return symb.encode('utf-8')
    return str(symb)


class _column(object):
    """ Base of all fields, a database column

        An instance of this object is a *description* of a database column. It will
        not hold any data, but only provide the methods to manipulate data of an
        ORM record or even prepare/update the database to hold such a field of data.
    """
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

    # used to hide a certain field type in the list of field types
    _deprecated = False

    def __init__(self, string='unknown', required=False, readonly=False, domain=None, context=None, states=None, priority=0, change_default=False, size=None, ondelete=None, translate=False, select=False, manual=False, **args):
        """

        The 'manual' keyword argument specifies if the field is a custom one.
        It corresponds to the 'state' column in ir_model_fields.

        """
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
        self.ondelete = ondelete.lower() if ondelete else None # defaults to 'set null' in ORM
        self.translate = translate
        self._domain = domain
        self._context = context
        self.write = False
        self.read = False
        self.view_load = 0
        self.select = select
        self.manual = manual
        self.selectable = True
        self.group_operator = args.get('group_operator', False)
        self.groups = False  # CSV list of ext IDs of groups that can access this field
        self.deprecated = False # Optional deprecation warning
        for a in args:
            if args[a]:
                setattr(self, a, args[a])
 
    def restart(self):
        pass

    def set(self, cr, obj, id, name, value, user=None, context=None):
        cr.execute('update '+obj._table+' set '+name+'='+self._symbol_set[0]+' where id=%s', (self._symbol_set[1](value), id))

    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        raise Exception(_('undefined get method !'))

    def search(self, cr, obj, args, name, value, offset=0, limit=None, uid=None, context=None):
        ids = obj.search(cr, uid, args+self._domain+[(name, 'ilike', value)], offset, limit, context=context)
        res = obj.read(cr, uid, ids, [name], context=context)
        return [x[name] for x in res]

    def as_display_name(self, cr, uid, obj, value, context=None):
        """Converts a field value to a suitable string representation for a record,
           e.g. when this field is used as ``rec_name``.

           :param obj: the ``BaseModel`` instance this column belongs to 
           :param value: a proper value as returned by :py:meth:`~openerp.orm.osv.BaseModel.read`
                         for this column
        """
        # delegated to class method, so a column type A can delegate
        # to a column type B. 
        return self._as_display_name(self, cr, uid, obj, value, context=None)

    @classmethod
    def _as_display_name(cls, field, cr, uid, obj, value, context=None):
        # This needs to be a class method, in case a column type A as to delegate
        # to a column type B.
        return tools.ustr(value)

# ---------------------------------------------------------
# Simple fields
# ---------------------------------------------------------
class boolean(_column):
    _type = 'boolean'
    _symbol_c = '%s'
    _symbol_f = lambda x: x and 'True' or 'False'
    _symbol_set = (_symbol_c, _symbol_f)

    def __init__(self, string='unknown', required=False, **args):
        super(boolean, self).__init__(string=string, required=required, **args)
        if required:
            _logger.debug(
                "required=True is deprecated: making a boolean field"
                " `required` has no effect, as NULL values are "
                "automatically turned into False.")

class integer(_column):
    _type = 'integer'
    _symbol_c = '%s'
    _symbol_f = lambda x: int(x or 0)
    _symbol_set = (_symbol_c, _symbol_f)
    _symbol_get = lambda self,x: x or 0

    def __init__(self, string='unknown', required=False, **args):
        super(integer, self).__init__(string=string, required=required, **args)

class reference(_column):
    _type = 'reference'
    _classic_read = False # post-process to handle missing target

    def __init__(self, string, selection, size, **args):
        _column.__init__(self, string=string, size=size, selection=selection, **args)

    def get(self, cr, obj, ids, name, uid=None, context=None, values=None):
        result = {}
        # copy initial values fetched previously.
        for value in values:
            result[value['id']] = value[name]
            if value[name]:
                model, res_id = value[name].split(',')
                if not obj.pool.get(model).exists(cr, uid, [int(res_id)], context=context):
                    result[value['id']] = False
        return result

    @classmethod
    def _as_display_name(cls, field, cr, uid, obj, value, context=None):
        if value:
            # reference fields have a 'model,id'-like value, that we need to convert
            # to a real name
            model_name, res_id = value.split(',')
            model = obj.pool.get(model_name)
            if model and res_id:
                return model.name_get(cr, uid, [int(res_id)], context=context)[0][1]
        return tools.ustr(value)

class char(_column):
    _type = 'char'

    def __init__(self, string="unknown", size=None, **args):
        _column.__init__(self, string=string, size=size or None, **args)
        self._symbol_set = (self._symbol_c, self._symbol_set_char)

    # takes a string (encoded in utf8) and returns a string (encoded in utf8)
    def _symbol_set_char(self, symb):
        #TODO:
        # * we need to remove the "symb==False" from the next line BUT
        #   for now too many things rely on this broken behavior
        # * the symb==None test should be common to all data types
        if symb is None or symb == False:
            return None

        # we need to convert the string to a unicode object to be able
        # to evaluate its length (and possibly truncate it) reliably
        u_symb = tools.ustr(symb)

        return u_symb[:self.size].encode('utf8')


class text(_column):
    _type = 'text'

class html(text):
    _type = 'html'
    _symbol_c = '%s'
    def _symbol_f(x):
        return html_sanitize(x)
        
    _symbol_set = (_symbol_c, _symbol_f)

import __builtin__

class float(_column):
    _type = 'float'
    _symbol_c = '%s'
    _symbol_f = lambda x: __builtin__.float(x or 0.0)
    _symbol_set = (_symbol_c, _symbol_f)
    _symbol_get = lambda self,x: x or 0.0

    def __init__(self, string='unknown', digits=None, digits_compute=None, required=False, **args):
        _column.__init__(self, string=string, required=required, **args)
        self.digits = digits
        # synopsis: digits_compute(cr) ->  (precision, scale)
        self.digits_compute = digits_compute

    def digits_change(self, cr):
        if self.digits_compute:
            self.digits = self.digits_compute(cr)
        if self.digits:
            precision, scale = self.digits
            self._symbol_set = ('%s', lambda x: float_repr(float_round(__builtin__.float(x or 0.0),
                                                                       precision_digits=scale),
                                                           precision_digits=scale))

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

    @staticmethod
    def context_today(model, cr, uid, context=None, timestamp=None):
        """Returns the current date as seen in the client's timezone
           in a format fit for date fields.
           This method may be passed as value to initialize _defaults.

           :param Model model: model (osv) for which the date value is being
                               computed - technical field, currently ignored,
                               automatically passed when used in _defaults.
           :param datetime timestamp: optional datetime value to use instead of
                                      the current date and time (must be a
                                      datetime, regular dates can't be converted
                                      between timezones.)
           :param dict context: the 'tz' key in the context should give the
                                name of the User/Client timezone (otherwise
                                UTC is used)
           :rtype: str 
        """
        today = timestamp or DT.datetime.now()
        context_today = None
        if context and context.get('tz'):
            try:
                utc = pytz.timezone('UTC')
                context_tz = pytz.timezone(context['tz'])
                utc_today = utc.localize(today, is_dst=False) # UTC = no DST
                context_today = utc_today.astimezone(context_tz)
            except Exception:
                _logger.debug("failed to compute context/client-specific today date, "
                              "using the UTC value for `today`",
                              exc_info=True)
        return (context_today or today).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)

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

    @staticmethod
    def context_timestamp(cr, uid, timestamp, context=None):
        """Returns the given timestamp converted to the client's timezone.
           This method is *not* meant for use as a _defaults initializer,
           because datetime fields are automatically converted upon
           display on client side. For _defaults you :meth:`fields.datetime.now`
           should be used instead.

           :param datetime timestamp: naive datetime value (expressed in UTC)
                                      to be converted to the client timezone
           :param dict context: the 'tz' key in the context should give the
                                name of the User/Client timezone (otherwise
                                UTC is used)
           :rtype: datetime
           :return: timestamp converted to timezone-aware datetime in context
                    timezone
        """
        assert isinstance(timestamp, DT.datetime), 'Datetime instance expected'
        if context and context.get('tz'):
            try:
                utc = pytz.timezone('UTC')
                context_tz = pytz.timezone(context['tz'])
                utc_timestamp = utc.localize(timestamp, is_dst=False) # UTC = no DST
                return utc_timestamp.astimezone(context_tz)
            except Exception:
                _logger.debug("failed to compute context/client-specific timestamp, "
                              "using the UTC value",
                              exc_info=True)
        return timestamp

class binary(_column):
    _type = 'binary'
    _symbol_c = '%s'

    # Binary values may be byte strings (python 2.6 byte array), but
    # the legacy OpenERP convention is to transfer and store binaries
    # as base64-encoded strings. The base64 string may be provided as a
    # unicode in some circumstances, hence the str() cast in symbol_f.
    # This str coercion will only work for pure ASCII unicode strings,
    # on purpose - non base64 data must be passed as a 8bit byte strings.
    _symbol_f = lambda symb: symb and Binary(str(symb)) or None

    _symbol_set = (_symbol_c, _symbol_f)
    _symbol_get = lambda self, x: x and str(x)

    _classic_read = False
    _prefetch = False

    def __init__(self, string='unknown', filters=None, **args):
        _column.__init__(self, string=string, **args)
        self.filters = filters

    def get(self, cr, obj, ids, name, user=None, context=None, values=None):
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

    
    @classmethod
    def _as_display_name(cls, field, cr, uid, obj, value, context=None):
        return value[1] if isinstance(value, tuple) else tools.ustr(value) 


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

        dom = self._domain
        if isinstance(self._domain, type(lambda: None)):
            dom = self._domain(obj)
        ids2 = obj.pool.get(self._obj).search(cr, user, dom + [(self._fields_id, 'in', ids)], limit=self._limit, context=context)
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
                reverse_rel = obj._all_columns.get(self._fields_id)
                assert reverse_rel, 'Trying to unlink the content of a o2m but the pointed model does not have a m2o'
                # if the model has on delete cascade, just delete the row
                if reverse_rel.column.ondelete == "cascade":
                    obj.unlink(cr, user, [act[1]], context=context)
                else:
                    cr.execute('update '+_table+' set '+self._fields_id+'=null where id=%s', (act[1],))
            elif act[0] == 4:
                # Must use write() to recompute parent_store structure if needed
                obj.write(cr, user, [act[1]], {self._fields_id:id}, context=context or {})
            elif act[0] == 5:
                reverse_rel = obj._all_columns.get(self._fields_id)
                assert reverse_rel, 'Trying to unlink the content of a o2m but the pointed model does not have a m2o'
                # if the o2m has a static domain we must respect it when unlinking
                dom = self._domain
                if isinstance(self._domain, type(lambda: None)):
                    dom = self._domain(obj)
                extra_domain = dom or []
                ids_to_unlink = obj.search(cr, user, [(self._fields_id,'=',id)] + extra_domain, context=context)
                # If the model has cascade deletion, we delete the rows because it is the intended behavior,
                # otherwise we only nullify the reverse foreign key column.
                if reverse_rel.column.ondelete == "cascade":
                    obj.unlink(cr, user, ids_to_unlink, context=context)
                else:
                    obj.write(cr, user, ids_to_unlink, {self._fields_id: False}, context=context)
            elif act[0] == 6:
                # Must use write() to recompute parent_store structure if needed
                obj.write(cr, user, act[2], {self._fields_id:id}, context=context or {})
                ids2 = act[2] or [0]
                cr.execute('select id from '+_table+' where '+self._fields_id+'=%s and id <> ALL (%s)', (id,ids2))
                ids3 = map(lambda x:x[0], cr.fetchall())
                obj.write(cr, user, ids3, {self._fields_id:False}, context=context or {})
        return result

    def search(self, cr, obj, args, name, value, offset=0, limit=None, uid=None, operator='like', context=None):
        dom = self._domain
        if isinstance(self._domain, type(lambda: None)):
            dom = self._domain(obj)
        return obj.pool.get(self._obj).name_search(cr, uid, value, dom, operator, context=context,limit=limit)

    
    @classmethod
    def _as_display_name(cls, field, cr, uid, obj, value, context=None):
        raise NotImplementedError('One2Many columns should not be used as record name (_rec_name)') 

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
    """Encapsulates the logic of a many-to-many bidirectional relationship, handling the
       low-level details of the intermediary relationship table transparently.
       A many-to-many relationship is always symmetrical, and can be declared and accessed
       from either endpoint model.
       If ``rel`` (relationship table name), ``id1`` (source foreign key column name)
       or id2 (destination foreign key column name) are not specified, the system will
       provide default values. This will by default only allow one single symmetrical
       many-to-many relationship between the source and destination model.
       For multiple many-to-many relationship between the same models and for
       relationships where source and destination models are the same, ``rel``, ``id1``
       and ``id2`` should be specified explicitly.

       :param str obj: destination model
       :param str rel: optional name of the intermediary relationship table. If not specified,
                       a canonical name will be derived based on the alphabetically-ordered
                       model names of the source and destination (in the form: ``amodel_bmodel_rel``).
                       Automatic naming is not possible when the source and destination are
                       the same, for obvious ambiguity reasons.
       :param str id1: optional name for the column holding the foreign key to the current
                       model in the relationship table. If not specified, a canonical name
                       will be derived based on the model name (in the form: `src_model_id`).
       :param str id2: optional name for the column holding the foreign key to the destination
                       model in the relationship table. If not specified, a canonical name
                       will be derived based on the model name (in the form: `dest_model_id`)
       :param str string: field label
    """
    _classic_read = False
    _classic_write = False
    _prefetch = False
    _type = 'many2many'

    def __init__(self, obj, rel=None, id1=None, id2=None, string='unknown', limit=None, **args):
        """
        """
        _column.__init__(self, string=string, **args)
        self._obj = obj
        if rel and '.' in rel:
            raise Exception(_('The second argument of the many2many field %s must be a SQL table !'\
                'You used %s, which is not a valid SQL table name.')% (string,rel))
        self._rel = rel
        self._id1 = id1
        self._id2 = id2
        self._limit = limit

    def _sql_names(self, source_model):
        """Return the SQL names defining the structure of the m2m relationship table

            :return: (m2m_table, local_col, dest_col) where m2m_table is the table name,
                     local_col is the name of the column holding the current model's FK, and
                     dest_col is the name of the column holding the destination model's FK, and
        """
        tbl, col1, col2 = self._rel, self._id1, self._id2
        if not all((tbl, col1, col2)):
            # the default table name is based on the stable alphabetical order of tables
            dest_model = source_model.pool.get(self._obj)
            tables = tuple(sorted([source_model._table, dest_model._table]))
            if not tbl:
                assert tables[0] != tables[1], 'Implicit/Canonical naming of m2m relationship table '\
                                               'is not possible when source and destination models are '\
                                               'the same'
                tbl = '%s_%s_rel' % tables
            if not col1:
                col1 = '%s_id' % source_model._table
            if not col2:
                col2 = '%s_id' % dest_model._table
        return (tbl, col1, col2)

    def _get_query_and_where_params(self, cr, model, ids, values, where_params):
        """ Extracted from ``get`` to facilitate fine-tuning of the generated
            query. """
        query = 'SELECT %(rel)s.%(id2)s, %(rel)s.%(id1)s \
                   FROM %(rel)s, %(from_c)s \
                  WHERE %(rel)s.%(id1)s IN %%s \
                    AND %(rel)s.%(id2)s = %(tbl)s.id \
                 %(where_c)s  \
                 %(order_by)s \
                 %(limit)s \
                 OFFSET %(offset)d' \
                 % values
        return query, where_params

    def get(self, cr, model, ids, name, user=None, offset=0, context=None, values=None):
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
            _logger.warning(
                "Specifying offset at a many2many.get() is deprecated and may"
                " produce unpredictable results.")
        obj = model.pool.get(self._obj)
        rel, id1, id2 = self._sql_names(model)

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

        query, where_params = self._get_query_and_where_params(cr, model, ids, {'rel': rel,
               'from_c': from_c,
               'tbl': obj._table,
               'id1': id1,
               'id2': id2,
               'where_c': where_c,
               'limit': limit_str,
               'order_by': order_by,
               'offset': offset,
                }, where_params)

        cr.execute(query, [tuple(ids),] + where_params)
        for r in cr.fetchall():
            res[r[1]].append(r[0])
        return res

    def set(self, cr, model, id, name, values, user=None, context=None):
        if not context:
            context = {}
        if not values:
            return
        rel, id1, id2 = self._sql_names(model)
        obj = model.pool.get(self._obj)
        for act in values:
            if not (isinstance(act, list) or isinstance(act, tuple)) or not act:
                continue
            if act[0] == 0:
                idnew = obj.create(cr, user, act[2], context=context)
                cr.execute('insert into '+rel+' ('+id1+','+id2+') values (%s,%s)', (id, idnew))
            elif act[0] == 1:
                obj.write(cr, user, [act[1]], act[2], context=context)
            elif act[0] == 2:
                obj.unlink(cr, user, [act[1]], context=context)
            elif act[0] == 3:
                cr.execute('delete from '+rel+' where ' + id1 + '=%s and '+ id2 + '=%s', (id, act[1]))
            elif act[0] == 4:
                # following queries are in the same transaction - so should be relatively safe
                cr.execute('SELECT 1 FROM '+rel+' WHERE '+id1+' = %s and '+id2+' = %s', (id, act[1]))
                if not cr.fetchone():
                    cr.execute('insert into '+rel+' ('+id1+','+id2+') values (%s,%s)', (id, act[1]))
            elif act[0] == 5:
                cr.execute('delete from '+rel+' where ' + id1 + ' = %s', (id,))
            elif act[0] == 6:

                d1, d2,tables = obj.pool.get('ir.rule').domain_get(cr, user, obj._name, context=context)
                if d1:
                    d1 = ' and ' + ' and '.join(d1)
                else:
                    d1 = ''
                cr.execute('delete from '+rel+' where '+id1+'=%s AND '+id2+' IN (SELECT '+rel+'.'+id2+' FROM '+rel+', '+','.join(tables)+' WHERE '+rel+'.'+id1+'=%s AND '+rel+'.'+id2+' = '+obj._table+'.id '+ d1 +')', [id, id]+d2)

                for act_nbr in act[2]:
                    cr.execute('insert into '+rel+' ('+id1+','+id2+') values (%s, %s)', (id, act_nbr))

    #
    # TODO: use a name_search
    #
    def search(self, cr, obj, args, name, value, offset=0, limit=None, uid=None, operator='like', context=None):
        return obj.pool.get(self._obj).search(cr, uid, args+self._domain+[('name', operator, value)], offset, limit, context=context)

    @classmethod
    def _as_display_name(cls, field, cr, uid, obj, value, context=None):
        raise NotImplementedError('Many2Many columns should not be used as record name (_rec_name)') 


def get_nice_size(value):
    size = 0
    if isinstance(value, (int,long)):
        size = value
    elif value: # this is supposed to be a string
        size = len(value)
    return tools.human_size(size)

# See http://www.w3.org/TR/2000/REC-xml-20001006#NT-Char
# and http://bugs.python.org/issue10066
invalid_xml_low_bytes = re.compile(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]')

def sanitize_binary_value(value):
    # binary fields should be 7-bit ASCII base64-encoded data,
    # but we do additional sanity checks to make sure the values
    # are not something else that won't pass via XML-RPC
    if isinstance(value, (xmlrpclib.Binary, tuple, list, dict)):
        # these builtin types are meant to pass untouched
        return value

    # Handle invalid bytes values that will cause problems
    # for XML-RPC. See for more info:
    #  - http://bugs.python.org/issue10066
    #  - http://www.w3.org/TR/2000/REC-xml-20001006#NT-Char

    # Coercing to unicode would normally allow it to properly pass via
    # XML-RPC, transparently encoded as UTF-8 by xmlrpclib.
    # (this works for _any_ byte values, thanks to the fallback
    #  to latin-1 passthrough encoding when decoding to unicode)
    value = tools.ustr(value)

    # Due to Python bug #10066 this could still yield invalid XML
    # bytes, specifically in the low byte range, that will crash
    # the decoding side: [\x00-\x08\x0b-\x0c\x0e-\x1f]
    # So check for low bytes values, and if any, perform
    # base64 encoding - not very smart or useful, but this is
    # our last resort to avoid crashing the request.
    if invalid_xml_low_bytes.search(value):
        # b64-encode after restoring the pure bytes with latin-1
        # passthrough encoding
        value = base64.b64encode(value.encode('latin-1'))

    return value


# ---------------------------------------------------------
# Function fields
# ---------------------------------------------------------
class function(_column):
    """
    A field whose value is computed by a function (rather
    than being read from the database).

    :param fnct: the callable that will compute the field value.
    :param arg: arbitrary value to be passed to ``fnct`` when computing the value.
    :param fnct_inv: the callable that will allow writing values in that field
                     (if not provided, the field is read-only).
    :param fnct_inv_arg: arbitrary value to be passed to ``fnct_inv`` when
                         writing a value.
    :param str type: type of the field simulated by the function field
    :param fnct_search: the callable that allows searching on the field
                        (if not provided, search will not return any result).
    :param store: store computed value in database
                  (see :ref:`The *store* parameter <field-function-store>`).
    :type store: True or dict specifying triggers for field computation
    :param multi: name of batch for batch computation of function fields.
                  All fields with the same batch name will be computed by
                  a single function call. This changes the signature of the
                  ``fnct`` callable.

    .. _field-function-fnct: The ``fnct`` parameter

    .. rubric:: The ``fnct`` parameter

    The callable implementing the function field must have the following signature:

    .. function:: fnct(model, cr, uid, ids, field_name(s), arg, context)

        Implements the function field.

        :param orm model: model to which the field belongs (should be ``self`` for
                          a model method)
        :param field_name(s): name of the field to compute, or if ``multi`` is provided,
                              list of field names to compute.
        :type field_name(s): str | [str]
        :param arg: arbitrary value passed when declaring the function field
        :rtype: dict
        :return: mapping of ``ids`` to computed values, or if multi is provided,
                 to a map of field_names to computed values

    The values in the returned dictionary must be of the type specified by the type
    argument in the field declaration.

    Here is an example with a simple function ``char`` function field::

        # declarations
        def compute(self, cr, uid, ids, field_name, arg, context):
            result = {}
            # ...
            return result
        _columns['my_char'] = fields.function(compute, type='char', size=50)

        # when called with ``ids=[1,2,3]``, ``compute`` could return:
        {
            1: 'foo',
            2: 'bar',
            3: False # null values should be returned explicitly too
        }

    If ``multi`` is set, then ``field_name`` is replaced by ``field_names``: a list
    of the field names that should be computed. Each value in the returned
    dictionary must then be a dictionary mapping field names to values.

    Here is an example where two function fields (``name`` and ``age``)
    are both computed by a single function field::

        # declarations
        def compute(self, cr, uid, ids, field_names, arg, context):
            result = {}
            # ...
            return result
        _columns['name'] = fields.function(compute_person_data, type='char',\
                                           size=50, multi='person_data')
        _columns[''age'] = fields.function(compute_person_data, type='integer',\
                                           multi='person_data')

        # when called with ``ids=[1,2,3]``, ``compute_person_data`` could return:
        {
            1: {'name': 'Bob', 'age': 23},
            2: {'name': 'Sally', 'age': 19},
            3: {'name': 'unknown', 'age': False}
        }

    .. _field-function-fnct-inv:

    .. rubric:: The ``fnct_inv`` parameter

    This callable implements the write operation for the function field
    and must have the following signature:

    .. function:: fnct_inv(model, cr, uid, id, field_name, field_value, fnct_inv_arg, context)

        Callable that implements the ``write`` operation for the function field.

        :param orm model: model to which the field belongs (should be ``self`` for
                          a model method)
        :param int id: the identifier of the object to write on
        :param str field_name: name of the field to set
        :param fnct_inv_arg: arbitrary value passed when declaring the function field
        :return: True

    When writing values for a function field, the ``multi`` parameter is ignored.

    .. _field-function-fnct-search:

    .. rubric:: The ``fnct_search`` parameter

    This callable implements the search operation for the function field
    and must have the following signature:

    .. function:: fnct_search(model, cr, uid, model_again, field_name, criterion, context)

        Callable that implements the ``search`` operation for the function field by expanding
        a search criterion based on the function field into a new domain based only on
        columns that are stored in the database.

        :param orm model: model to which the field belongs (should be ``self`` for
                          a model method)
        :param orm model_again: same value as ``model`` (seriously! this is for backwards
                                compatibility)
        :param str field_name: name of the field to search on
        :param list criterion: domain component specifying the search criterion on the field.
        :rtype: list
        :return: domain to use instead of ``criterion`` when performing the search.
                 This new domain must be based only on columns stored in the database, as it
                 will be used directly without any translation.

        The returned value must be a domain, that is, a list of the form [(field_name, operator, operand)].
        The most generic way to implement ``fnct_search`` is to directly search for the records that
        match the given ``criterion``, and return their ``ids`` wrapped in a domain, such as
        ``[('id','in',[1,3,5])]``.

    .. _field-function-store:

    .. rubric:: The ``store`` parameter

    The ``store`` parameter allows caching the result of the field computation in the
    database, and defining the triggers that will invalidate that cache and force a
    recomputation of the function field.
    When not provided, the field is computed every time its value is read.
    The value of ``store`` may be either ``True`` (to recompute the field value whenever
    any field in the same record is modified), or a dictionary specifying a more
    flexible set of recomputation triggers.

    A trigger specification is a dictionary that maps the names of the models that
    will trigger the computation, to a tuple describing the trigger rule, in the
    following form::

        store = {
            'trigger_model': (mapping_function,
                              ['trigger_field1', 'trigger_field2'],
                              priority),
        }

    A trigger rule is defined by a 3-item tuple where:

        * The ``mapping_function`` is defined as follows:

            .. function:: mapping_function(trigger_model, cr, uid, trigger_ids, context)

                Callable that maps record ids of a trigger model to ids of the
                corresponding records in the source model (whose field values
                need to be recomputed).

                :param orm model: trigger_model
                :param list trigger_ids: ids of the records of trigger_model that were
                                         modified
                :rtype: list
                :return: list of ids of the source model whose function field values
                         need to be recomputed

        * The second item is a list of the fields who should act as triggers for
          the computation. If an empty list is given, all fields will act as triggers.
        * The last item is the priority, used to order the triggers when processing them
          after any write operation on a model that has function field triggers. The
          default priority is 10.

    In fact, setting store = True is the same as using the following trigger dict::

        store = {
              'model_itself': (lambda self, cr, uid, ids, context: ids,
                               [],
                               10)
        }

    """
    _classic_read = False
    _classic_write = False
    _prefetch = False
    _type = 'function'
    _properties = True

#
# multi: compute several fields in one call
#
    def __init__(self, fnct, arg=None, fnct_inv=None, fnct_inv_arg=None, type='float', fnct_search=None, obj=None, store=False, multi=False, **args):
        _column.__init__(self, **args)
        self._obj = obj
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

        if type == 'integer':
            self._symbol_c = integer._symbol_c
            self._symbol_f = integer._symbol_f
            self._symbol_set = integer._symbol_set

    def digits_change(self, cr):
        if self._type == 'float':
            if self.digits_compute:
                self.digits = self.digits_compute(cr)
            if self.digits:
                precision, scale = self.digits
                self._symbol_set = ('%s', lambda x: float_repr(float_round(__builtin__.float(x or 0.0),
                                                                           precision_digits=scale),
                                                               precision_digits=scale))

    def search(self, cr, uid, obj, name, args, context=None):
        if not self._fnct_search:
            #CHECKME: should raise an exception
            return []
        return self._fnct_search(obj, cr, uid, obj, name, args, context=context)

    def postprocess(self, cr, uid, obj, field, value=None, context=None):
        if context is None:
            context = {}
        result = value
        field_type = obj._columns[field]._type
        if field_type == "many2one":
            # make the result a tuple if it is not already one
            if isinstance(value, (int,long)) and hasattr(obj._columns[field], 'relation'):
                obj_model = obj.pool.get(obj._columns[field].relation)
                dict_names = dict(obj_model.name_get(cr, uid, [value], context))
                result = (value, dict_names[value])

        if field_type == 'binary':
            if context.get('bin_size'):
                # client requests only the size of binary fields
                result = get_nice_size(value)
            elif not context.get('bin_raw'):
                result = sanitize_binary_value(value)

        if field_type == "integer" and value > xmlrpclib.MAXINT:
            # integer/long values greater than 2^31-1 are not supported
            # in pure XMLRPC, so we have to pass them as floats :-(
            # This is not needed for stored fields and non-functional integer
            # fields, as their values are constrained by the database backend
            # to the same 32bits signed int limit.
            result = __builtin__.float(value)
        return result

    def get(self, cr, obj, ids, name, uid=False, context=None, values=None):
        result = self._fnct(obj, cr, uid, ids, name, self._arg, context)
        for id in ids:
            if self._multi and id in result:
                for field, value in result[id].iteritems():
                    if value:
                        result[id][field] = self.postprocess(cr, uid, obj, field, value, context)
            elif result.get(id):
                result[id] = self.postprocess(cr, uid, obj, name, result[id], context)
        return result

    def set(self, cr, obj, id, name, value, user=None, context=None):
        if not context:
            context = {}
        if self._fnct_inv:
            self._fnct_inv(obj, cr, user, id, name, value, self._fnct_inv_arg, context)

    @classmethod
    def _as_display_name(cls, field, cr, uid, obj, value, context=None):
        # Function fields are supposed to emulate a basic field type,
        # so they can delegate to the basic type for record name rendering
        return globals()[field._type]._as_display_name(field, cr, uid, obj, value, context=context)

# ---------------------------------------------------------
# Related fields
# ---------------------------------------------------------

class related(function):
    """Field that points to some data inside another field of the current record.

    Example::

       _columns = {
           'foo_id': fields.many2one('my.foo', 'Foo'),
           'bar': fields.related('foo_id', 'frol', type='char', string='Frol of Foo'),
        }
    """

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
                # name_get as root, as seeing the name of a related
                # object depends on access right of source document,
                # not target, so user may not have access.
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
        super(related, self).__init__(self._fnct_read, arg, self._fnct_write, fnct_inv_arg=arg, fnct_search=self._fnct_search, **args)
        if self.store is True:
            # TODO: improve here to change self.store = {...} according to related objects
            pass

    def _field_get2(self, cr, uid, obj, context=None):
        if self._relations:
            return
        result = []
        obj_name = obj._name
        for i in range(len(self._arg)):
            f = obj.pool.get(obj_name).fields_get(cr, uid, [self._arg[i]], context=context)[self._arg[i]]
            result.append({
                'object': obj_name,
                'type': f['type']

            })
            if f.get('relation',False):
                obj_name = f['relation']
                result[-1]['relation'] = f['relation']
        self._relations = result

class sparse(function):   

    def convert_value(self, obj, cr, uid, record, value, read_value, context=None):        
        """
            + For a many2many field, a list of tuples is expected.
              Here is the list of tuple that are accepted, with the corresponding semantics ::

                 (0, 0,  { values })    link to a new record that needs to be created with the given values dictionary
                 (1, ID, { values })    update the linked record with id = ID (write *values* on it)
                 (2, ID)                remove and delete the linked record with id = ID (calls unlink on ID, that will delete the object completely, and the link to it as well)
                 (3, ID)                cut the link to the linked record with id = ID (delete the relationship between the two objects but does not delete the target object itself)
                 (4, ID)                link to existing record with id = ID (adds a relationship)
                 (5)                    unlink all (like using (3,ID) for all linked records)
                 (6, 0, [IDs])          replace the list of linked IDs (like using (5) then (4,ID) for each ID in the list of IDs)

                 Example:
                    [(6, 0, [8, 5, 6, 4])] sets the many2many to ids [8, 5, 6, 4]

            + For a one2many field, a lits of tuples is expected.
              Here is the list of tuple that are accepted, with the corresponding semantics ::

                 (0, 0,  { values })    link to a new record that needs to be created with the given values dictionary
                 (1, ID, { values })    update the linked record with id = ID (write *values* on it)
                 (2, ID)                remove and delete the linked record with id = ID (calls unlink on ID, that will delete the object completely, and the link to it as well)

                 Example:
                    [(0, 0, {'field_name':field_value_record1, ...}), (0, 0, {'field_name':field_value_record2, ...})]
        """

        if self._type == 'many2many':
            assert value[0][0] == 6, 'Unsupported m2m value for sparse field: %s' % value
            return value[0][2]

        elif self._type == 'one2many':
            if not read_value:
                read_value = []
            relation_obj = obj.pool.get(self.relation)
            for vals in value:
                assert vals[0] in (0,1,2), 'Unsupported o2m value for sparse field: %s' % vals
                if vals[0] == 0:
                    read_value.append(relation_obj.create(cr, uid, vals[2], context=context))
                elif vals[0] == 1:
                    relation_obj.write(cr, uid, vals[1], vals[2], context=context)
                elif vals[0] == 2:
                    relation_obj.unlink(cr, uid, vals[1], context=context)
                    read_value.remove(vals[1])
            return read_value
        return value


    def _fnct_write(self,obj,cr, uid, ids, field_name, value, args, context=None):
        if not type(ids) == list:
            ids = [ids]
        records = obj.browse(cr, uid, ids, context=context)
        for record in records:
            # grab serialized value as object - already deserialized
            serialized = getattr(record, self.serialization_field)
            if value is None:
                # simply delete the key to unset it.
                serialized.pop(field_name, None)
            else: 
                serialized[field_name] = self.convert_value(obj, cr, uid, record, value, serialized.get(field_name), context=context)
            obj.write(cr, uid, ids, {self.serialization_field: serialized}, context=context)
        return True

    def _fnct_read(self, obj, cr, uid, ids, field_names, args, context=None):
        results = {}
        records = obj.browse(cr, uid, ids, context=context)
        for record in records:
            # grab serialized value as object - already deserialized
            serialized = getattr(record, self.serialization_field)
            results[record.id] = {}
            for field_name in field_names:
                field_type = obj._columns[field_name]._type
                value = serialized.get(field_name, False)
                if field_type in ('one2many','many2many'):
                    value = value or []
                    if value:
                        # filter out deleted records as superuser
                        relation_obj = obj.pool.get(obj._columns[field_name].relation)
                        value = relation_obj.exists(cr, openerp.SUPERUSER_ID, value)
                if type(value) in (int,long) and field_type == 'many2one':
                    relation_obj = obj.pool.get(obj._columns[field_name].relation)
                    # check for deleted record as superuser
                    if not relation_obj.exists(cr, openerp.SUPERUSER_ID, [value]):
                        value = False
                results[record.id][field_name] = value
        return results

    def __init__(self, serialization_field, **kwargs):
        self.serialization_field = serialization_field
        return super(sparse, self).__init__(self._fnct_read, fnct_inv=self._fnct_write, multi='__sparse_multi', **kwargs)
     


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
        super(dummy, self).__init__(self._fnct_read, arg, self._fnct_write, fnct_inv_arg=arg, fnct_search=None, **args)

# ---------------------------------------------------------
# Serialized fields
# ---------------------------------------------------------

class serialized(_column):
    """ A field able to store an arbitrary python data structure.
    
        Note: only plain components allowed.
    """
    
    def _symbol_set_struct(val):
        return simplejson.dumps(val)

    def _symbol_get_struct(self, val):
        return simplejson.loads(val or '{}')
    
    _prefetch = False
    _type = 'serialized'

    _symbol_c = '%s'
    _symbol_f = _symbol_set_struct
    _symbol_set = (_symbol_c, _symbol_f)
    _symbol_get = _symbol_get_struct

# TODO: review completly this class for speed improvement
class property(function):

    def _get_default(self, obj, cr, uid, prop_name, context=None):
        return self._get_defaults(obj, cr, uid, [prop_name], context=None)[prop_name]

    def _get_defaults(self, obj, cr, uid, prop_names, context=None):
        """Get the default values for ``prop_names´´ property fields (result of ir.property.get() function for res_id = False).

           :param list of string prop_names: list of name of property fields for those we want the default value
           :return: map of property field names to their default value
           :rtype: dict
        """
        prop = obj.pool.get('ir.property')
        res = {}
        for prop_name in prop_names:
            res[prop_name] = prop.get(cr, uid, prop_name, obj._name, context=context)
        return res

    def _get_by_id(self, obj, cr, uid, prop_name, ids, context=None):
        prop = obj.pool.get('ir.property')
        vids = [obj._name + ',' + str(oid) for oid in  ids]

        domain = [('fields_id.model', '=', obj._name), ('fields_id.name', 'in', prop_name)]
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

        property_create = False
        if isinstance(default_val, openerp.osv.orm.browse_record):
            if default_val.id != id_val:
                property_create = True
        elif default_val != id_val:
            property_create = True

        if property_create:
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

    def _fnct_read(self, obj, cr, uid, ids, prop_names, obj_dest, context=None):
        prop = obj.pool.get('ir.property')
        # get the default values (for res_id = False) for the property fields
        default_val = self._get_defaults(obj, cr, uid, prop_names, context)

        # build the dictionary that will be returned
        res = {}
        for id in ids:
            res[id] = default_val.copy()

        for prop_name in prop_names:
            property_field = obj._all_columns.get(prop_name).column
            property_destination_obj = property_field._obj if property_field._type == 'many2one' else False
            # If the property field is a m2o field, we will append the id of the value to name_get_ids
            # in order to make a name_get in batch for all the ids needed.
            name_get_ids = {}
            for id in ids:
                # get the result of ir.property.get() for this res_id and save it in res if it's existing
                obj_reference = obj._name + ',' + str(id)
                value = prop.get(cr, uid, prop_name, obj._name, res_id=obj_reference, context=context)
                if value:
                    res[id][prop_name] = value
                # Check existence as root (as seeing the name of a related
                # object depends on access right of source document,
                # not target, so user may not have access) in order to avoid
                # pointing on an unexisting record.
                if property_destination_obj:
                    if res[id][prop_name] and obj.pool.get(property_destination_obj).exists(cr, 1, res[id][prop_name].id):
                        name_get_ids[id] = res[id][prop_name].id
                    else:
                        res[id][prop_name] = False
            if property_destination_obj:
                # name_get as root (as seeing the name of a related
                # object depends on access right of source document,
                # not target, so user may not have access.)
                name_get_values = dict(obj.pool.get(property_destination_obj).name_get(cr, 1, name_get_ids.values(), context=context))
                # the property field is a m2o, we need to return a tuple with (id, name)
                for k, v in name_get_ids.iteritems():
                    if res[k][prop_name]:
                        res[k][prop_name] = (v , name_get_values.get(v))
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


def field_to_dict(model, cr, user, field, context=None):
    """ Return a dictionary representation of a field.

    The string, help, and selection attributes (if any) are untranslated.  This
    representation is the one returned by fields_get() (fields_get() will do
    the translation).

    """

    res = {'type': field._type}
    # This additional attributes for M2M and function field is added
    # because we need to display tooltip with this additional information
    # when client is started in debug mode.
    if isinstance(field, function):
        res['function'] = field._fnct and field._fnct.func_name or False
    #    res['store'] = field.store
    #    if isinstance(field.store, dict):
    #        res['store'] = str(field.store)
        res['fnct_search'] = field._fnct_search and field._fnct_search.func_name or False
        res['fnct_inv'] = field._fnct_inv and field._fnct_inv.func_name or False
        res['fnct_inv_arg'] = field._fnct_inv_arg or False
        res['func_obj'] = field._obj or False
    if isinstance(field, many2many):
        (table, col1, col2) = field._sql_names(model)
        res['related_columns'] = [col1, col2]
        res['third_table'] = table
    for arg in ('string', 'readonly', 'states', 'size', 'required', 'group_operator',
            'change_default', 'translate', 'help', 'select', 'selectable', 'groups'):
        if getattr(field, arg):
            res[arg] = getattr(field, arg)
    for arg in ('digits', 'invisible', 'filters'):
        if getattr(field, arg, None):
            res[arg] = getattr(field, arg)

    if field.string:
        res['string'] = field.string
    if field.help:
        res['help'] = field.help

    if hasattr(field, 'selection'):
        if isinstance(field.selection, (tuple, list)):
            res['selection'] = field.selection
        else:
            # call the 'dynamic selection' function
            res['selection'] = field.selection(model, cr, user, context)
    if res['type'] in ('one2many', 'many2many', 'many2one'):
        res['relation'] = field._obj
        dom = field._domain
        if isinstance(field._domain, type(lambda: None)):
            dom = field._domain(model)
        res['domain'] = field._domain
        res['context'] = field._context

    if isinstance(field, one2many):
        res['relation_field'] = field._fields_id

    return res


class column_info(object):
    """Struct containing details about an osv column, either one local to
       its model, or one inherited via _inherits.

       :attr name: name of the column
       :attr column: column instance, subclass of osv.fields._column
       :attr parent_model: if the column is inherited, name of the model
                           that contains it, None for local columns.
       :attr parent_column: the name of the column containing the m2o
                            relationship to the parent model that contains
                            this column, None for local columns.
       :attr original_parent: if the column is inherited, name of the original
                            parent model that contains it i.e in case of multilevel
                            inheritence, None for local columns.
    """
    def __init__(self, name, column, parent_model=None, parent_column=None, original_parent=None):
        self.name = name
        self.column = column
        self.parent_model = parent_model
        self.parent_column = parent_column
        self.original_parent = original_parent

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

