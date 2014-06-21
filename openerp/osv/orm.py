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


"""
  Object relational mapping to database (postgresql) module
     * Hierarchical structure
     * Constraints consistency, validations
     * Object meta Data depends on its status
     * Optimised processing by complex query (multiple actions at once)
     * Default fields value
     * Permissions optimisation
     * Persistant object: DB postgresql
     * Datas conversions
     * Multi-level caching system
     * 2 different inheritancies
     * Fields:
          - classicals (varchar, integer, boolean, ...)
          - relations (one2many, many2one, many2many)
          - functions

"""

import calendar
import collections
import copy
import datetime
import itertools
import logging
import operator
import pickle
import pytz
import re
import simplejson
import time
import traceback
import types

import babel.dates
import dateutil.relativedelta
import psycopg2
from lxml import etree

import fields
import openerp
import openerp.tools as tools
from openerp.tools.config import config
from openerp.tools.misc import CountingStream, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from query import Query

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')

# List of etree._Element subclasses that we choose to ignore when parsing XML.
from openerp.tools import SKIPPED_ELEMENT_TYPES

regex_order = re.compile('^( *([a-z0-9:_]+|"[a-z0-9:_]+")( *desc| *asc)?( *, *|))+$', re.I)
regex_object_name = re.compile(r'^[a-z0-9_.]+$')

AUTOINIT_RECALCULATE_STORED_FIELDS = 1000

def transfer_field_to_modifiers(field, modifiers):
    default_values = {}
    state_exceptions = {}
    for attr in ('invisible', 'readonly', 'required'):
        state_exceptions[attr] = []
        default_values[attr] = bool(field.get(attr))
    for state, modifs in (field.get("states",{})).items():
        for modif in modifs:
            if default_values[modif[0]] != modif[1]:
                state_exceptions[modif[0]].append(state)

    for attr, default_value in default_values.items():
        if state_exceptions[attr]:
            modifiers[attr] = [("state", "not in" if default_value else "in", state_exceptions[attr])]
        else:
            modifiers[attr] = default_value


# Don't deal with groups, it is done by check_group().
# Need the context to evaluate the invisible attribute on tree views.
# For non-tree views, the context shouldn't be given.
def transfer_node_to_modifiers(node, modifiers, context=None, in_tree_view=False):
    if node.get('attrs'):
        modifiers.update(eval(node.get('attrs')))

    if node.get('states'):
        if 'invisible' in modifiers and isinstance(modifiers['invisible'], list):
            # TODO combine with AND or OR, use implicit AND for now.
            modifiers['invisible'].append(('state', 'not in', node.get('states').split(',')))
        else:
            modifiers['invisible'] = [('state', 'not in', node.get('states').split(','))]

    for a in ('invisible', 'readonly', 'required'):
        if node.get(a):
            v = bool(eval(node.get(a), {'context': context or {}}))
            if in_tree_view and a == 'invisible':
                # Invisible in a tree view has a specific meaning, make it a
                # new key in the modifiers attribute.
                modifiers['tree_invisible'] = v
            elif v or (a not in modifiers or not isinstance(modifiers[a], list)):
                # Don't set the attribute to False if a dynamic value was
                # provided (i.e. a domain from attrs or states).
                modifiers[a] = v


def simplify_modifiers(modifiers):
    for a in ('invisible', 'readonly', 'required'):
        if a in modifiers and not modifiers[a]:
            del modifiers[a]


def transfer_modifiers_to_node(modifiers, node):
    if modifiers:
        simplify_modifiers(modifiers)
        node.set('modifiers', simplejson.dumps(modifiers))

def setup_modifiers(node, field=None, context=None, in_tree_view=False):
    """ Processes node attributes and field descriptors to generate
    the ``modifiers`` node attribute and set it on the provided node.

    Alters its first argument in-place.

    :param node: ``field`` node from an OpenERP view
    :type node: lxml.etree._Element
    :param dict field: field descriptor corresponding to the provided node
    :param dict context: execution context used to evaluate node attributes
    :param bool in_tree_view: triggers the ``tree_invisible`` code
                              path (separate from ``invisible``): in
                              tree view there are two levels of
                              invisibility, cell content (a column is
                              present but the cell itself is not
                              displayed) with ``invisible`` and column
                              invisibility (the whole column is
                              hidden) with ``tree_invisible``.
    :returns: nothing
    """
    modifiers = {}
    if field is not None:
        transfer_field_to_modifiers(field, modifiers)
    transfer_node_to_modifiers(
        node, modifiers, context=context, in_tree_view=in_tree_view)
    transfer_modifiers_to_node(modifiers, node)

def test_modifiers(what, expected):
    modifiers = {}
    if isinstance(what, basestring):
        node = etree.fromstring(what)
        transfer_node_to_modifiers(node, modifiers)
        simplify_modifiers(modifiers)
        json = simplejson.dumps(modifiers)
        assert json == expected, "%s != %s" % (json, expected)
    elif isinstance(what, dict):
        transfer_field_to_modifiers(what, modifiers)
        simplify_modifiers(modifiers)
        json = simplejson.dumps(modifiers)
        assert json == expected, "%s != %s" % (json, expected)


# To use this test:
# import openerp
# openerp.osv.orm.modifiers_tests()
def modifiers_tests():
    test_modifiers('<field name="a"/>', '{}')
    test_modifiers('<field name="a" invisible="1"/>', '{"invisible": true}')
    test_modifiers('<field name="a" readonly="1"/>', '{"readonly": true}')
    test_modifiers('<field name="a" required="1"/>', '{"required": true}')
    test_modifiers('<field name="a" invisible="0"/>', '{}')
    test_modifiers('<field name="a" readonly="0"/>', '{}')
    test_modifiers('<field name="a" required="0"/>', '{}')
    test_modifiers('<field name="a" invisible="1" required="1"/>', '{"invisible": true, "required": true}') # TODO order is not guaranteed
    test_modifiers('<field name="a" invisible="1" required="0"/>', '{"invisible": true}')
    test_modifiers('<field name="a" invisible="0" required="1"/>', '{"required": true}')
    test_modifiers("""<field name="a" attrs="{'invisible': [('b', '=', 'c')]}"/>""", '{"invisible": [["b", "=", "c"]]}')

    # The dictionary is supposed to be the result of fields_get().
    test_modifiers({}, '{}')
    test_modifiers({"invisible": True}, '{"invisible": true}')
    test_modifiers({"invisible": False}, '{}')


def check_object_name(name):
    """ Check if the given name is a valid openerp object name.

        The _name attribute in osv and osv_memory object is subject to
        some restrictions. This function returns True or False whether
        the given name is allowed or not.

        TODO: this is an approximation. The goal in this approximation
        is to disallow uppercase characters (in some places, we quote
        table/column names and in other not, which leads to this kind
        of errors:

            psycopg2.ProgrammingError: relation "xxx" does not exist).

        The same restriction should apply to both osv and osv_memory
        objects for consistency.

    """
    if regex_object_name.match(name) is None:
        return False
    return True

def raise_on_invalid_object_name(name):
    if not check_object_name(name):
        msg = "The _name attribute %s is not valid." % name
        _logger.error(msg)
        raise except_orm('ValueError', msg)

POSTGRES_CONFDELTYPES = {
    'RESTRICT': 'r',
    'NO ACTION': 'a',
    'CASCADE': 'c',
    'SET NULL': 'n',
    'SET DEFAULT': 'd',
}

def intersect(la, lb):
    return filter(lambda x: x in lb, la)

def fix_import_export_id_paths(fieldname):
    """
    Fixes the id fields in import and exports, and splits field paths
    on '/'.

    :param str fieldname: name of the field to import/export
    :return: split field name
    :rtype: list of str
    """
    fixed_db_id = re.sub(r'([^/])\.id', r'\1/.id', fieldname)
    fixed_external_id = re.sub(r'([^/]):id', r'\1/id', fixed_db_id)
    return fixed_external_id.split('/')

class except_orm(Exception):
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.args = (name, value)

class BrowseRecordError(Exception):
    pass

class browse_null(object):
    """ Readonly python database object browser
    """

    def __init__(self):
        self.id = False

    def __getitem__(self, name):
        return None

    def __getattr__(self, name):
        return None  # XXX: return self ?

    def __int__(self):
        return False

    def __str__(self):
        return ''

    def __nonzero__(self):
        return False

    def __unicode__(self):
        return u''

    def __iter__(self):
        raise NotImplementedError("Iteration is not allowed on %s" % self)


#
# TODO: execute an object method on browse_record_list
#
class browse_record_list(list):
    """ Collection of browse objects

        Such an instance will be returned when doing a ``browse([ids..])``
        and will be iterable, yielding browse() objects
    """

    def __init__(self, lst, context=None):
        if not context:
            context = {}
        super(browse_record_list, self).__init__(lst)
        self.context = context


class browse_record(object):
    """ An object that behaves like a row of an object's table.
        It has attributes after the columns of the corresponding object.

        Examples::

            uobj = pool.get('res.users')
            user_rec = uobj.browse(cr, uid, 104)
            name = user_rec.name
    """

    def __init__(self, cr, uid, id, table, cache, context=None,
                 list_class=browse_record_list, fields_process=None):
        """
        :param table: the browsed object (inherited from orm)
        :param dict cache: a dictionary of model->field->data to be shared
                           across browse objects, thus reducing the SQL
                           read()s. It can speed up things a lot, but also be
                           disastrous if not discarded after write()/unlink()
                           operations
        :param dict context: dictionary with an optional context
        """
        if fields_process is None:
            fields_process = {}
        if context is None:
            context = {}
        self._list_class = list_class
        self._cr = cr
        self._uid = uid
        self._id = id
        self._table = table # deprecated, use _model!
        self._model = table
        self._table_name = self._table._name
        self.__logger = logging.getLogger('openerp.osv.orm.browse_record.' + self._table_name)
        self._context = context
        self._fields_process = fields_process

        cache.setdefault(table._name, {})
        self._data = cache[table._name]

#        if not (id and isinstance(id, (int, long,))):
#            raise BrowseRecordError(_('Wrong ID for the browse record, got %r, expected an integer.') % (id,))
#        if not table.exists(cr, uid, id, context):
#            raise BrowseRecordError(_('Object %s does not exists') % (self,))

        if id not in self._data:
            self._data[id] = {'id': id}

        self._cache = cache

    def __getitem__(self, name):
        if name == 'id':
            return self._id

        if name not in self._data[self._id]:
            # build the list of fields we will fetch

            # fetch the definition of the field which was asked for
            if name in self._table._columns:
                col = self._table._columns[name]
            elif name in self._table._inherit_fields:
                col = self._table._inherit_fields[name][2]
            elif hasattr(self._table, str(name)):
                attr = getattr(self._table, name)
                if isinstance(attr, (types.MethodType, types.LambdaType, types.FunctionType)):
                    def function_proxy(*args, **kwargs):
                        if 'context' not in kwargs and self._context:
                            kwargs.update(context=self._context)
                        return attr(self._cr, self._uid, [self._id], *args, **kwargs)
                    return function_proxy
                else:
                    return attr
            else:
                error_msg = "Field '%s' does not exist in object '%s'" % (name, self)
                self.__logger.warning(error_msg)
                if self.__logger.isEnabledFor(logging.DEBUG):
                    self.__logger.debug(''.join(traceback.format_stack()))
                raise KeyError(error_msg)

            prefetchable = lambda f: f._classic_write and f._prefetch and not f.groups and not f.deprecated

            # if the field is a classic one or a many2one, we'll fetch all classic and many2one fields
            if prefetchable(col):
                # gen the list of "local" (ie not inherited) fields which are classic or many2one
                field_filter = lambda x: prefetchable(x[1])
                fields_to_fetch = filter(field_filter, self._table._columns.items())
                # gen the list of inherited fields
                inherits = map(lambda x: (x[0], x[1][2]), self._table._inherit_fields.items())
                # complete the field list with the inherited fields which are classic or many2one
                fields_to_fetch += filter(field_filter, inherits)
            # otherwise we fetch only that field
            else:
                fields_to_fetch = [(name, col)]

            ids = filter(lambda id: name not in self._data[id], self._data.keys())
            # read the results
            field_names = map(lambda x: x[0], fields_to_fetch)
            try:
                field_values = self._table.read(self._cr, self._uid, ids, field_names, context=self._context, load="_classic_write")
            except (openerp.exceptions.AccessError, except_orm):
                if len(ids) == 1:
                    raise
                # prefetching attempt failed, perhaps we're violating ACL restrictions involuntarily
                _logger.info('Prefetching attempt for fields %s on %s failed for ids %s, re-trying just for id %s', field_names, self._model._name, ids, self._id)
                ids = [self._id]
                field_values = self._table.read(self._cr, self._uid, ids, field_names, context=self._context, load="_classic_write")

            # TODO: improve this, very slow for reports
            if self._fields_process:
                lang = self._context.get('lang', 'en_US') or 'en_US'
                lang_obj_ids = self.pool.get('res.lang').search(self._cr, self._uid, [('code', '=', lang)])
                if not lang_obj_ids:
                    raise Exception(_('Language with code "%s" is not defined in your system !\nDefine it through the Administration menu.') % (lang,))
                lang_obj = self.pool.get('res.lang').browse(self._cr, self._uid, lang_obj_ids[0])

                for field_name, field_column in fields_to_fetch:
                    if field_column._type in self._fields_process:
                        for result_line in field_values:
                            result_line[field_name] = self._fields_process[field_column._type](result_line[field_name])
                            if result_line[field_name]:
                                result_line[field_name].set_value(self._cr, self._uid, result_line[field_name], self, field_column, lang_obj)

            if not field_values:
                # Where did those ids come from? Perhaps old entries in ir_model_dat?
                _logger.warning("No field_values found for ids %s in %s", ids, self)
                raise KeyError('Field %s not found in %s'%(name, self))
            # create browse records for 'remote' objects
            for result_line in field_values:
                new_data = {}
                for field_name, field_column in fields_to_fetch:
                    if field_column._type == 'many2one':
                        if result_line[field_name]:
                            obj = self._table.pool[field_column._obj]
                            if isinstance(result_line[field_name], (list, tuple)):
                                value = result_line[field_name][0]
                            else:
                                value = result_line[field_name]
                            if value:
                                # FIXME: this happen when a _inherits object
                                #        overwrite a field of it parent. Need
                                #        testing to be sure we got the right
                                #        object and not the parent one.
                                if not isinstance(value, browse_record):
                                    if obj is None:
                                        # In some cases the target model is not available yet, so we must ignore it,
                                        # which is safe in most cases, this value will just be loaded later when needed.
                                        # This situation can be caused by custom fields that connect objects with m2o without
                                        # respecting module dependencies, causing relationships to be connected to soon when
                                        # the target is not loaded yet.
                                        continue
                                    new_data[field_name] = browse_record(self._cr,
                                        self._uid, value, obj, self._cache,
                                        context=self._context,
                                        list_class=self._list_class,
                                        fields_process=self._fields_process)
                                else:
                                    new_data[field_name] = value
                            else:
                                new_data[field_name] = browse_null()
                        else:
                            new_data[field_name] = browse_null()
                    elif field_column._type in ('one2many', 'many2many') and len(result_line[field_name]):
                        new_data[field_name] = self._list_class(
                            (browse_record(self._cr, self._uid, id, self._table.pool.get(field_column._obj),
                                           self._cache, context=self._context, list_class=self._list_class,
                                           fields_process=self._fields_process)
                               for id in result_line[field_name]),
                            context=self._context)
                    elif field_column._type == 'reference':
                        if result_line[field_name]:
                            if isinstance(result_line[field_name], browse_record):
                                new_data[field_name] = result_line[field_name]
                            else:
                                ref_obj, ref_id = result_line[field_name].split(',')
                                ref_id = long(ref_id)
                                if ref_id:
                                    obj = self._table.pool[ref_obj]
                                    new_data[field_name] = browse_record(self._cr, self._uid, ref_id, obj, self._cache, context=self._context, list_class=self._list_class, fields_process=self._fields_process)
                                else:
                                    new_data[field_name] = browse_null()
                        else:
                            new_data[field_name] = browse_null()
                    else:
                        new_data[field_name] = result_line[field_name]
                self._data[result_line['id']].update(new_data)

        if not name in self._data[self._id]:
            # How did this happen? Could be a missing model due to custom fields used too soon, see above.
            self.__logger.error("Fields to fetch: %s, Field values: %s", field_names, field_values)
            self.__logger.error("Cached: %s, Table: %s", self._data[self._id], self._table)
            raise KeyError(_('Unknown attribute %s in %s ') % (name, self))
        return self._data[self._id][name]

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError, e:
            import sys
            exc_info = sys.exc_info()
            raise AttributeError, "Got %r while trying to get attribute %s on a %s record." % (e, name, self._table._name), exc_info[2]

    def __contains__(self, name):
        return (name in self._table._columns) or (name in self._table._inherit_fields) or hasattr(self._table, name)

    def __iter__(self):
        raise NotImplementedError("Iteration is not allowed on %s" % self)

    def __hasattr__(self, name):
        return name in self

    def __int__(self):
        return self._id

    def __str__(self):
        return "browse_record(%s, %s)" % (self._table_name, self._id)

    def __eq__(self, other):
        if not isinstance(other, browse_record):
            return False
        return (self._table_name, self._id) == (other._table_name, other._id)

    def __ne__(self, other):
        if not isinstance(other, browse_record):
            return True
        return (self._table_name, self._id) != (other._table_name, other._id)

    # we need to define __unicode__ even though we've already defined __str__
    # because we have overridden __getattr__
    def __unicode__(self):
        return unicode(str(self))

    def __hash__(self):
        return hash((self._table_name, self._id))

    __repr__ = __str__

    def refresh(self):
        """Force refreshing this browse_record's data and all the data of the
           records that belong to the same cache, by emptying the cache completely,
           preserving only the record identifiers (for prefetching optimizations).
        """
        for model, model_cache in self._cache.iteritems():
            # only preserve the ids of the records that were in the cache
            cached_ids = dict([(i, {'id': i}) for i in model_cache.keys()])
            self._cache[model].clear()
            self._cache[model].update(cached_ids)

def pg_varchar(size=0):
    """ Returns the VARCHAR declaration for the provided size:

    * If no size (or an empty or negative size is provided) return an
      'infinite' VARCHAR
    * Otherwise return a VARCHAR(n)

    :type int size: varchar size, optional
    :rtype: str
    """
    if size:
        if not isinstance(size, int):
            raise TypeError("VARCHAR parameter should be an int, got %s"
                            % type(size))
        if size > 0:
            return 'VARCHAR(%d)' % size
    return 'VARCHAR'

FIELDS_TO_PGTYPES = {
    fields.boolean: 'bool',
    fields.integer: 'int4',
    fields.text: 'text',
    fields.html: 'text',
    fields.date: 'date',
    fields.datetime: 'timestamp',
    fields.binary: 'bytea',
    fields.many2one: 'int4',
    fields.serialized: 'text',
}

def get_pg_type(f, type_override=None):
    """
    :param fields._column f: field to get a Postgres type for
    :param type type_override: use the provided type for dispatching instead of the field's own type
    :returns: (postgres_identification_type, postgres_type_specification)
    :rtype: (str, str)
    """
    field_type = type_override or type(f)

    if field_type in FIELDS_TO_PGTYPES:
        pg_type =  (FIELDS_TO_PGTYPES[field_type], FIELDS_TO_PGTYPES[field_type])
    elif issubclass(field_type, fields.float):
        if f.digits:
            pg_type = ('numeric', 'NUMERIC')
        else:
            pg_type = ('float8', 'DOUBLE PRECISION')
    elif issubclass(field_type, (fields.char, fields.reference)):
        pg_type = ('varchar', pg_varchar(f.size))
    elif issubclass(field_type, fields.selection):
        if (isinstance(f.selection, list) and isinstance(f.selection[0][0], int))\
                or getattr(f, 'size', None) == -1:
            pg_type = ('int4', 'INTEGER')
        else:
            pg_type = ('varchar', pg_varchar(getattr(f, 'size', None)))
    elif issubclass(field_type, fields.function):
        if f._type == 'selection':
            pg_type = ('varchar', pg_varchar())
        else:
            pg_type = get_pg_type(f, getattr(fields, f._type))
    else:
        _logger.warning('%s type not supported!', field_type)
        pg_type = None

    return pg_type


class MetaModel(type):
    """ Metaclass for the Model.

    This class is used as the metaclass for the Model class to discover
    the models defined in a module (i.e. without instanciating them).
    If the automatic discovery is not needed, it is possible to set the
    model's _register attribute to False.

    """

    module_to_models = {}

    def __init__(self, name, bases, attrs):
        if not self._register:
            self._register = True
            super(MetaModel, self).__init__(name, bases, attrs)
            return

        # The (OpenERP) module name can be in the `openerp.addons` namespace
        # or not. For instance module `sale` can be imported as
        # `openerp.addons.sale` (the good way) or `sale` (for backward
        # compatibility).
        module_parts = self.__module__.split('.')
        if len(module_parts) > 2 and module_parts[0] == 'openerp' and \
            module_parts[1] == 'addons':
            module_name = self.__module__.split('.')[2]
        else:
            module_name = self.__module__.split('.')[0]
        if not hasattr(self, '_module'):
            self._module = module_name

        # Remember which models to instanciate for this module.
        if not self._custom:
            self.module_to_models.setdefault(self._module, []).append(self)


# Definition of log access columns, automatically added to models if
# self._log_access is True
LOG_ACCESS_COLUMNS = {
    'create_uid': 'INTEGER REFERENCES res_users ON DELETE SET NULL',
    'create_date': 'TIMESTAMP',
    'write_uid': 'INTEGER REFERENCES res_users ON DELETE SET NULL',
    'write_date': 'TIMESTAMP'
}
# special columns automatically created by the ORM
MAGIC_COLUMNS =  ['id'] + LOG_ACCESS_COLUMNS.keys()

class BaseModel(object):
    """ Base class for OpenERP models.

    OpenERP models are created by inheriting from this class' subclasses:

    * Model: for regular database-persisted models
    * TransientModel: for temporary data, stored in the database but automatically
                      vaccuumed every so often
    * AbstractModel: for abstract super classes meant to be shared by multiple
                     _inheriting classes (usually Models or TransientModels)

    The system will later instantiate the class once per database (on
    which the class' module is installed).

    To create a class that should not be instantiated, the _register class attribute
    may be set to False.
    """
    __metaclass__ = MetaModel
    _auto = True # create database backend
    _register = False # Set to false if the model shouldn't be automatically discovered.
    _name = None
    _columns = {}
    _constraints = []
    _custom = False
    _defaults = {}
    _rec_name = None
    _parent_name = 'parent_id'
    _parent_store = False
    _parent_order = False
    _date_name = 'date'
    _order = 'id'
    _sequence = None
    _description = None
    _needaction = False

    # dict of {field:method}, with method returning the (name_get of records, {id: fold})
    # to include in the _read_group, if grouped on this field
    _group_by_full = {}

    # Transience
    _transient = False # True in a TransientModel

    # structure:
    #  { 'parent_model': 'm2o_field', ... }
    _inherits = {}

    # Mapping from inherits'd field name to triple (m, r, f, n) where m is the
    # model from which it is inherits'd, r is the (local) field towards m, f
    # is the _column object itself, and n is the original (i.e. top-most)
    # parent model.
    # Example:
    #  { 'field_name': ('parent_model', 'm2o_field_to_reach_parent',
    #                   field_column_obj, origina_parent_model), ... }
    _inherit_fields = {}

    # Mapping field name/column_info object
    # This is similar to _inherit_fields but:
    # 1. includes self fields,
    # 2. uses column_info instead of a triple.
    _all_columns = {}

    _table = None
    _log_create = False
    _sql_constraints = []
    _protected = ['read', 'write', 'create', 'default_get', 'perm_read', 'unlink', 'fields_get', 'fields_view_get', 'search', 'name_get', 'distinct_field_get', 'name_search', 'copy', 'import_data', 'search_count', 'exists']

    CONCURRENCY_CHECK_FIELD = '__last_update'

    def log(self, cr, uid, id, message, secondary=False, context=None):
        return _logger.warning("log() is deprecated. Please use OpenChatter notification system instead of the res.log mechanism.")

    def view_init(self, cr, uid, fields_list, context=None):
        """Override this method to do specific things when a view on the object is opened."""
        pass

    def _field_create(self, cr, context=None):
        """ Create entries in ir_model_fields for all the model's fields.

        If necessary, also create an entry in ir_model, and if called from the
        modules loading scheme (by receiving 'module' in the context), also
        create entries in ir_model_data (for the model and the fields).

        - create an entry in ir_model (if there is not already one),
        - create an entry in ir_model_data (if there is not already one, and if
          'module' is in the context),
        - update ir_model_fields with the fields found in _columns
          (TODO there is some redundancy as _columns is updated from
          ir_model_fields in __init__).

        """
        if context is None:
            context = {}
        cr.execute("SELECT id FROM ir_model WHERE model=%s", (self._name,))
        if not cr.rowcount:
            cr.execute('SELECT nextval(%s)', ('ir_model_id_seq',))
            model_id = cr.fetchone()[0]
            cr.execute("INSERT INTO ir_model (id,model, name, info,state) VALUES (%s, %s, %s, %s, %s)", (model_id, self._name, self._description, self.__doc__, 'base'))
        else:
            model_id = cr.fetchone()[0]
        if 'module' in context:
            name_id = 'model_'+self._name.replace('.', '_')
            cr.execute('select * from ir_model_data where name=%s and module=%s', (name_id, context['module']))
            if not cr.rowcount:
                cr.execute("INSERT INTO ir_model_data (name,date_init,date_update,module,model,res_id) VALUES (%s, (now() at time zone 'UTC'), (now() at time zone 'UTC'), %s, %s, %s)", \
                    (name_id, context['module'], 'ir.model', model_id)
                )

        cr.execute("SELECT * FROM ir_model_fields WHERE model=%s", (self._name,))
        cols = {}
        for rec in cr.dictfetchall():
            cols[rec['name']] = rec

        ir_model_fields_obj = self.pool.get('ir.model.fields')

        # sparse field should be created at the end, as it depends on its serialized field already existing
        model_fields = sorted(self._columns.items(), key=lambda x: 1 if x[1]._type == 'sparse' else 0)
        for (k, f) in model_fields:
            vals = {
                'model_id': model_id,
                'model': self._name,
                'name': k,
                'field_description': f.string,
                'ttype': f._type,
                'relation': f._obj or '',
                'select_level': tools.ustr(f.select or 0),
                'readonly': (f.readonly and 1) or 0,
                'required': (f.required and 1) or 0,
                'selectable': (f.selectable and 1) or 0,
                'translate': (f.translate and 1) or 0,
                'relation_field': f._fields_id if isinstance(f, fields.one2many) else '',
                'serialization_field_id': None,
            }
            if getattr(f, 'serialization_field', None):
                # resolve link to serialization_field if specified by name
                serialization_field_id = ir_model_fields_obj.search(cr, SUPERUSER_ID, [('model','=',vals['model']), ('name', '=', f.serialization_field)])
                if not serialization_field_id:
                    raise except_orm(_('Error'), _("Serialization field `%s` not found for sparse field `%s`!") % (f.serialization_field, k))
                vals['serialization_field_id'] = serialization_field_id[0]

            # When its a custom field,it does not contain f.select
            if context.get('field_state', 'base') == 'manual':
                if context.get('field_name', '') == k:
                    vals['select_level'] = context.get('select', '0')
                #setting value to let the problem NOT occur next time
                elif k in cols:
                    vals['select_level'] = cols[k]['select_level']

            if k not in cols:
                cr.execute('select nextval(%s)', ('ir_model_fields_id_seq',))
                id = cr.fetchone()[0]
                vals['id'] = id
                cr.execute("""INSERT INTO ir_model_fields (
                    id, model_id, model, name, field_description, ttype,
                    relation,state,select_level,relation_field, translate, serialization_field_id
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )""", (
                    id, vals['model_id'], vals['model'], vals['name'], vals['field_description'], vals['ttype'],
                     vals['relation'], 'base',
                    vals['select_level'], vals['relation_field'], bool(vals['translate']), vals['serialization_field_id']
                ))
                if 'module' in context:
                    name1 = 'field_' + self._table + '_' + k
                    cr.execute("select name from ir_model_data where name=%s", (name1,))
                    if cr.fetchone():
                        name1 = name1 + "_" + str(id)
                    cr.execute("INSERT INTO ir_model_data (name,date_init,date_update,module,model,res_id) VALUES (%s, (now() at time zone 'UTC'), (now() at time zone 'UTC'), %s, %s, %s)", \
                        (name1, context['module'], 'ir.model.fields', id)
                    )
            else:
                for key, val in vals.items():
                    if cols[k][key] != vals[key]:
                        cr.execute('update ir_model_fields set field_description=%s where model=%s and name=%s', (vals['field_description'], vals['model'], vals['name']))
                        cr.execute("""UPDATE ir_model_fields SET
                            model_id=%s, field_description=%s, ttype=%s, relation=%s,
                            select_level=%s, readonly=%s ,required=%s, selectable=%s, relation_field=%s, translate=%s, serialization_field_id=%s
                        WHERE
                            model=%s AND name=%s""", (
                                vals['model_id'], vals['field_description'], vals['ttype'],
                                vals['relation'],
                                vals['select_level'], bool(vals['readonly']), bool(vals['required']), bool(vals['selectable']), vals['relation_field'], bool(vals['translate']), vals['serialization_field_id'], vals['model'], vals['name']
                            ))
                        break

    #
    # Goal: try to apply inheritance at the instanciation level and
    #       put objects in the pool var
    #
    @classmethod
    def create_instance(cls, pool, cr):
        """ Instanciate a given model.

        This class method instanciates the class of some model (i.e. a class
        deriving from osv or osv_memory). The class might be the class passed
        in argument or, if it inherits from another class, a class constructed
        by combining the two classes.

        The ``attributes`` argument specifies which parent class attributes
        have to be combined.

        TODO: the creation of the combined class is repeated at each call of
        this method. This is probably unnecessary.

        """
        attributes = ['_columns', '_defaults', '_inherits', '_constraints',
            '_sql_constraints']

        parent_names = getattr(cls, '_inherit', None)
        if parent_names:
            if isinstance(parent_names, (str, unicode)):
                name = cls._name or parent_names
                parent_names = [parent_names]
            else:
                name = cls._name
            if not name:
                raise TypeError('_name is mandatory in case of multiple inheritance')

            for parent_name in ((type(parent_names)==list) and parent_names or [parent_names]):
                if parent_name not in pool:
                    raise TypeError('The model "%s" specifies an unexisting parent class "%s"\n'
                        'You may need to add a dependency on the parent class\' module.' % (name, parent_name))
                parent_model = pool[parent_name]
                if not getattr(cls, '_original_module', None) and name == parent_model._name:
                    cls._original_module = parent_model._original_module
                parent_class = parent_model.__class__
                nattr = {}
                for s in attributes:
                    new = copy.copy(getattr(parent_model, s, {}))
                    if s == '_columns':
                        # Don't _inherit custom fields.
                        for c in new.keys():
                            if new[c].manual:
                                del new[c]
                    if hasattr(new, 'update'):
                        new.update(cls.__dict__.get(s, {}))
                    elif s=='_constraints':
                        for c in cls.__dict__.get(s, []):
                            exist = False
                            for c2 in range(len(new)):
                                #For _constraints, we should check field and methods as well
                                if new[c2][2]==c[2] and (new[c2][0] == c[0] \
                                        or getattr(new[c2][0],'__name__', True) == \
                                            getattr(c[0],'__name__', False)):
                                    # If new class defines a constraint with
                                    # same function name, we let it override
                                    # the old one.

                                    new[c2] = c
                                    exist = True
                                    break
                            if not exist:
                                new.append(c)
                    else:
                        new.extend(cls.__dict__.get(s, []))
                    nattr[s] = new

                # Keep links to non-inherited constraints, e.g. useful when exporting translations
                nattr['_local_constraints'] = cls.__dict__.get('_constraints', [])
                nattr['_local_sql_constraints'] = cls.__dict__.get('_sql_constraints', [])

                cls = type(name, (cls, parent_class), dict(nattr, _register=False))
        else:
            cls._local_constraints = getattr(cls, '_constraints', [])
            cls._local_sql_constraints = getattr(cls, '_sql_constraints', [])

        if not getattr(cls, '_original_module', None):
            cls._original_module = cls._module
        obj = object.__new__(cls)

        if hasattr(obj, '_columns'):
            # float fields are registry-dependent (digit attribute). Duplicate them to avoid issues.
            for c, f in obj._columns.items():
                if f._type == 'float':
                    obj._columns[c] = copy.copy(f)

        obj.__init__(pool, cr)
        return obj

    def __new__(cls):
        """Register this model.

        This doesn't create an instance but simply register the model
        as being part of the module where it is defined.

        """


        # Set the module name (e.g. base, sale, accounting, ...) on the class.
        module = cls.__module__.split('.')[0]
        if not hasattr(cls, '_module'):
            cls._module = module

        # Record this class in the list of models to instantiate for this module,
        # managed by the metaclass.
        module_model_list = MetaModel.module_to_models.setdefault(cls._module, [])
        if cls not in module_model_list:
            if not cls._custom:
                module_model_list.append(cls)

        # Since we don't return an instance here, the __init__
        # method won't be called.
        return None

    def __init__(self, pool, cr):
        """ Initialize a model and make it part of the given registry.

        - copy the stored fields' functions in the osv_pool,
        - update the _columns with the fields found in ir_model_fields,
        - ensure there is a many2one for each _inherits'd parent,
        - update the children's _columns,
        - give a chance to each field to initialize itself.

        """
        pool.add(self._name, self)
        self.pool = pool

        if not self._name and not hasattr(self, '_inherit'):
            name = type(self).__name__.split('.')[0]
            msg = "The class %s has to have a _name attribute" % name

            _logger.error(msg)
            raise except_orm('ValueError', msg)

        if not self._description:
            self._description = self._name
        if not self._table:
            self._table = self._name.replace('.', '_')

        if not hasattr(self, '_log_access'):
            # If _log_access is not specified, it is the same value as _auto.
            self._log_access = getattr(self, "_auto", True)

        self._columns = self._columns.copy()
        for store_field in self._columns:
            f = self._columns[store_field]
            if hasattr(f, 'digits_change'):
                f.digits_change(cr)
            def not_this_field(stored_func):
                x, y, z, e, f, l = stored_func
                return x != self._name or y != store_field
            self.pool._store_function[self._name] = filter(not_this_field, self.pool._store_function.get(self._name, []))
            if not isinstance(f, fields.function):
                continue
            if not f.store:
                continue
            sm = f.store
            if sm is True:
                sm = {self._name: (lambda self, cr, uid, ids, c={}: ids, None, f.priority, None)}
            for object, aa in sm.items():
                if len(aa) == 4:
                    (fnct, fields2, order, length) = aa
                elif len(aa) == 3:
                    (fnct, fields2, order) = aa
                    length = None
                else:
                    raise except_orm('Error',
                        ('Invalid function definition %s in object %s !\nYou must use the definition: store={object:(fnct, fields, priority, time length)}.' % (store_field, self._name)))
                self.pool._store_function.setdefault(object, [])
                t = (self._name, store_field, fnct, tuple(fields2) if fields2 else None, order, length)
                if not t in self.pool._store_function[object]:
                    self.pool._store_function[object].append((self._name, store_field, fnct, tuple(fields2) if fields2 else None, order, length))
                    self.pool._store_function[object].sort(lambda x, y: cmp(x[4], y[4]))

        for (key, _, msg) in self._sql_constraints:
            self.pool._sql_error[self._table+'_'+key] = msg

        # Load manual fields

        # Check the query is already done for all modules of if we need to
        # do it ourselves.
        if self.pool.fields_by_model is not None:
            manual_fields = self.pool.fields_by_model.get(self._name, [])
        else:
            cr.execute('SELECT * FROM ir_model_fields WHERE model=%s AND state=%s', (self._name, 'manual'))
            manual_fields = cr.dictfetchall()
        for field in manual_fields:
            if field['name'] in self._columns:
                continue
            attrs = {
                'string': field['field_description'],
                'required': bool(field['required']),
                'readonly': bool(field['readonly']),
                'domain': eval(field['domain']) if field['domain'] else None,
                'size': field['size'] or None,
                'ondelete': field['on_delete'],
                'translate': (field['translate']),
                'manual': True,
                '_prefetch': False,
                #'select': int(field['select_level'])
            }

            if field['serialization_field_id']:
                cr.execute('SELECT name FROM ir_model_fields WHERE id=%s', (field['serialization_field_id'],))
                attrs.update({'serialization_field': cr.fetchone()[0], 'type': field['ttype']})
                if field['ttype'] in ['many2one', 'one2many', 'many2many']:
                    attrs.update({'relation': field['relation']})
                self._columns[field['name']] = fields.sparse(**attrs)
            elif field['ttype'] == 'selection':
                self._columns[field['name']] = fields.selection(eval(field['selection']), **attrs)
            elif field['ttype'] == 'reference':
                self._columns[field['name']] = fields.reference(selection=eval(field['selection']), **attrs)
            elif field['ttype'] == 'many2one':
                self._columns[field['name']] = fields.many2one(field['relation'], **attrs)
            elif field['ttype'] == 'one2many':
                self._columns[field['name']] = fields.one2many(field['relation'], field['relation_field'], **attrs)
            elif field['ttype'] == 'many2many':
                _rel1 = field['relation'].replace('.', '_')
                _rel2 = field['model'].replace('.', '_')
                _rel_name = 'x_%s_%s_%s_rel' % (_rel1, _rel2, field['name'])
                self._columns[field['name']] = fields.many2many(field['relation'], _rel_name, 'id1', 'id2', **attrs)
            else:
                self._columns[field['name']] = getattr(fields, field['ttype'])(**attrs)

        self._inherits_check()
        self._inherits_reload()
        if not self._sequence:
            self._sequence = self._table + '_id_seq'
        for k in self._defaults:
            assert (k in self._columns) or (k in self._inherit_fields), 'Default function defined in %s but field %s does not exist !' % (self._name, k,)
        for f in self._columns:
            self._columns[f].restart()

        # Transience
        if self.is_transient():
            self._transient_check_count = 0
            self._transient_max_count = config.get('osv_memory_count_limit')
            self._transient_max_hours = config.get('osv_memory_age_limit')
            assert self._log_access, "TransientModels must have log_access turned on, "\
                                     "in order to implement their access rights policy"

        # Validate rec_name
        if self._rec_name is not None:
            assert self._rec_name in self._all_columns.keys() + ['id'], "Invalid rec_name %s for model %s" % (self._rec_name, self._name)
        else:
            self._rec_name = 'name'


    def __export_row(self, cr, uid, row, fields, raw_data=False, context=None):
        if context is None:
            context = {}

        def check_type(field_type):
            if field_type == 'float':
                return 0.0
            elif field_type == 'integer':
                return 0
            elif field_type == 'boolean':
                return 'False'
            return ''

        def selection_field(in_field):
            col_obj = self.pool[in_field.keys()[0]]
            if f[i] in col_obj._columns.keys():
                return  col_obj._columns[f[i]]
            elif f[i] in col_obj._inherits.keys():
                selection_field(col_obj._inherits)
            else:
                return False

        def _get_xml_id(self, cr, uid, r):
            model_data = self.pool.get('ir.model.data')
            data_ids = model_data.search(cr, uid, [('model', '=', r._model._name), ('res_id', '=', r['id'])])
            if len(data_ids):
                d = model_data.read(cr, uid, data_ids, ['name', 'module'])[0]
                if d['module']:
                    r = '%s.%s' % (d['module'], d['name'])
                else:
                    r = d['name']
            else:
                postfix = 0
                while True:
                    n = r._model._table+'_'+str(r['id']) + (postfix and ('_'+str(postfix)) or '' )
                    if not model_data.search(cr, uid, [('name', '=', n)]):
                        break
                    postfix += 1
                model_data.create(cr, SUPERUSER_ID, {
                    'name': n,
                    'model': r._model._name,
                    'res_id': r['id'],
                    'module': '__export__',
                })
                r = '__export__.'+n
            return r

        lines = []
        data = map(lambda x: '', range(len(fields)))
        done = []
        for fpos in range(len(fields)):
            f = fields[fpos]
            if f:
                r = row
                i = 0
                while i < len(f):
                    cols = False
                    if f[i] == '.id':
                        r = r['id']
                    elif f[i] == 'id':
                        r = _get_xml_id(self, cr, uid, r)
                    else:
                        r = r[f[i]]
                        # To display external name of selection field when its exported
                        if f[i] in self._columns.keys():
                            cols = self._columns[f[i]]
                        elif f[i] in self._inherit_fields.keys():
                            cols = selection_field(self._inherits)
                        if cols and cols._type == 'selection':
                            sel_list = cols.selection
                            if r and type(sel_list) == type([]):
                                r = [x[1] for x in sel_list if r==x[0]]
                                r = r and r[0] or False
                    if not r:
                        if f[i] in self._columns:
                            r = check_type(self._columns[f[i]]._type)
                        elif f[i] in self._inherit_fields:
                            r = check_type(self._inherit_fields[f[i]][2]._type)
                        data[fpos] = r or False
                        break
                    if isinstance(r, (browse_record_list, list)):
                        first = True
                        fields2 = map(lambda x: (x[:i+1]==f[:i+1] and x[i+1:]) \
                                or [], fields)
                        if fields2 in done:
                            if [x for x in fields2 if x]:
                                break
                        done.append(fields2)
                        if cols and cols._type=='many2many' and len(fields[fpos])>(i+1) and (fields[fpos][i+1]=='id'):
                            data[fpos] = ','.join([_get_xml_id(self, cr, uid, x) for x in r])
                            break

                        for row2 in r:
                            lines2 = row2._model.__export_row(cr, uid, row2, fields2, context=context)
                            if first:
                                for fpos2 in range(len(fields)):
                                    if lines2 and lines2[0][fpos2]:
                                        data[fpos2] = lines2[0][fpos2]
                                if not data[fpos]:
                                    dt = ''
                                    for rr in r:
                                        name_relation = self.pool[rr._table_name]._rec_name
                                        if isinstance(rr[name_relation], browse_record):
                                            rr = rr[name_relation]
                                        rr_name = self.pool[rr._table_name].name_get(cr, uid, [rr.id], context=context)
                                        rr_name = rr_name and rr_name[0] and rr_name[0][1] or ''
                                        dt += tools.ustr(rr_name or '') + ','
                                    data[fpos] = dt[:-1]
                                    break
                                lines += lines2[1:]
                                first = False
                            else:
                                lines += lines2
                        break
                    i += 1

                if i == len(f):
                    if isinstance(r, browse_record):
                        r = self.pool[r._table_name].name_get(cr, uid, [r.id], context=context)
                        r = r and r[0] and r[0][1] or ''
                    if raw_data and cols and cols._type in ('integer', 'boolean', 'float'):
                        data[fpos] = r
                    elif raw_data and cols and cols._type == 'date':
                        data[fpos] = datetime.datetime.strptime(r, tools.DEFAULT_SERVER_DATE_FORMAT).date()
                    elif raw_data and cols and cols._type == 'datetime':
                        data[fpos] = datetime.datetime.strptime(r, tools.DEFAULT_SERVER_DATETIME_FORMAT)
                    else:
                        data[fpos] = tools.ustr(r or '')
        return [data] + lines

    def export_data(self, cr, uid, ids, fields_to_export, raw_data=False, context=None):
        """
        Export fields for selected objects

        :param cr: database cursor
        :param uid: current user id
        :param ids: list of ids
        :param fields_to_export: list of fields
        :param raw_data: True to return value in fields type, False for string values
        :param context: context arguments, like lang, time zone
        :rtype: dictionary with a *datas* matrix

        This method is used when exporting data via client menu

        """
        if context is None:
            context = {}
        cols = self._columns.copy()
        for f in self._inherit_fields:
            cols.update({f: self._inherit_fields[f][2]})
        fields_to_export = map(fix_import_export_id_paths, fields_to_export)
        datas = []
        for row in self.browse(cr, uid, ids, context):
            datas += self.__export_row(cr, uid, row, fields_to_export, raw_data=raw_data, context=context)
        return {'datas': datas}

    def import_data(self, cr, uid, fields, datas, mode='init', current_module='', noupdate=False, context=None, filename=None):
        """
        .. deprecated:: 7.0
            Use :meth:`~load` instead

        Import given data in given module

        This method is used when importing data via client menu.

        Example of fields to import for a sale.order::

            .id,                         (=database_id)
            partner_id,                  (=name_search)
            order_line/.id,              (=database_id)
            order_line/name,
            order_line/product_id/id,    (=xml id)
            order_line/price_unit,
            order_line/product_uom_qty,
            order_line/product_uom/id    (=xml_id)

        This method returns a 4-tuple with the following structure::

            (return_code, errored_resource, error_message, unused)

        * The first item is a return code, it is ``-1`` in case of
          import error, or the last imported row number in case of success
        * The second item contains the record data dict that failed to import
          in case of error, otherwise it's 0
        * The third item contains an error message string in case of error,
          otherwise it's 0
        * The last item is currently unused, with no specific semantics

        :param fields: list of fields to import
        :param datas: data to import
        :param mode: 'init' or 'update' for record creation
        :param current_module: module name
        :param noupdate: flag for record creation
        :param filename: optional file to store partial import state for recovery
        :returns: 4-tuple in the form (return_code, errored_resource, error_message, unused)
        :rtype: (int, dict or 0, str or 0, str or 0)
        """
        context = dict(context) if context is not None else {}
        context['_import_current_module'] = current_module

        fields = map(fix_import_export_id_paths, fields)
        ir_model_data_obj = self.pool.get('ir.model.data')

        def log(m):
            if m['type'] == 'error':
                raise Exception(m['message'])

        if config.get('import_partial') and filename:
            with open(config.get('import_partial'), 'rb') as partial_import_file:
                data = pickle.load(partial_import_file)
                position = data.get(filename, 0)

        position = 0
        try:
            for res_id, xml_id, res, info in self._convert_records(cr, uid,
                            self._extract_records(cr, uid, fields, datas,
                                                  context=context, log=log),
                            context=context, log=log):
                ir_model_data_obj._update(cr, uid, self._name,
                     current_module, res, mode=mode, xml_id=xml_id,
                     noupdate=noupdate, res_id=res_id, context=context)
                position = info.get('rows', {}).get('to', 0) + 1
                if config.get('import_partial') and filename and (not (position%100)):
                    with open(config.get('import_partial'), 'rb') as partial_import:
                        data = pickle.load(partial_import)
                    data[filename] = position
                    with open(config.get('import_partial'), 'wb') as partial_import:
                        pickle.dump(data, partial_import)
                    if context.get('defer_parent_store_computation'):
                        self._parent_store_compute(cr)
                    cr.commit()
        except Exception, e:
            cr.rollback()
            return -1, {}, 'Line %d : %s' % (position + 1, tools.ustr(e)), ''

        if context.get('defer_parent_store_computation'):
            self._parent_store_compute(cr)
        return position, 0, 0, 0

    def load(self, cr, uid, fields, data, context=None):
        """
        Attempts to load the data matrix, and returns a list of ids (or
        ``False`` if there was an error and no id could be generated) and a
        list of messages.

        The ids are those of the records created and saved (in database), in
        the same order they were extracted from the file. They can be passed
        directly to :meth:`~read`

        :param fields: list of fields to import, at the same index as the corresponding data
        :type fields: list(str)
        :param data: row-major matrix of data to import
        :type data: list(list(str))
        :param dict context:
        :returns: {ids: list(int)|False, messages: [Message]}
        """
        cr.execute('SAVEPOINT model_load')
        messages = []

        fields = map(fix_import_export_id_paths, fields)
        ModelData = self.pool['ir.model.data'].clear_caches()

        fg = self.fields_get(cr, uid, context=context)

        mode = 'init'
        current_module = ''
        noupdate = False

        ids = []
        for id, xid, record, info in self._convert_records(cr, uid,
                self._extract_records(cr, uid, fields, data,
                                      context=context, log=messages.append),
                context=context, log=messages.append):
            try:
                cr.execute('SAVEPOINT model_load_save')
            except psycopg2.InternalError, e:
                # broken transaction, exit and hope the source error was
                # already logged
                if not any(message['type'] == 'error' for message in messages):
                    messages.append(dict(info, type='error',message=
                        u"Unknown database error: '%s'" % e))
                break
            try:
                ids.append(ModelData._update(cr, uid, self._name,
                     current_module, record, mode=mode, xml_id=xid,
                     noupdate=noupdate, res_id=id, context=context))
                cr.execute('RELEASE SAVEPOINT model_load_save')
            except psycopg2.Warning, e:
                messages.append(dict(info, type='warning', message=str(e)))
                cr.execute('ROLLBACK TO SAVEPOINT model_load_save')
            except psycopg2.Error, e:
                messages.append(dict(
                    info, type='error',
                    **PGERROR_TO_OE[e.pgcode](self, fg, info, e)))
                # Failed to write, log to messages, rollback savepoint (to
                # avoid broken transaction) and keep going
                cr.execute('ROLLBACK TO SAVEPOINT model_load_save')
        if any(message['type'] == 'error' for message in messages):
            cr.execute('ROLLBACK TO SAVEPOINT model_load')
            ids = False
        return {'ids': ids, 'messages': messages}
    def _extract_records(self, cr, uid, fields_, data,
                         context=None, log=lambda a: None):
        """ Generates record dicts from the data sequence.

        The result is a generator of dicts mapping field names to raw
        (unconverted, unvalidated) values.

        For relational fields, if sub-fields were provided the value will be
        a list of sub-records

        The following sub-fields may be set on the record (by key):
        * None is the name_get for the record (to use with name_create/name_search)
        * "id" is the External ID for the record
        * ".id" is the Database ID for the record
        """
        columns = dict((k, v.column) for k, v in self._all_columns.iteritems())
        # Fake columns to avoid special cases in extractor
        columns[None] = fields.char('rec_name')
        columns['id'] = fields.char('External ID')
        columns['.id'] = fields.integer('Database ID')

        # m2o fields can't be on multiple lines so exclude them from the
        # is_relational field rows filter, but special-case it later on to
        # be handled with relational fields (as it can have subfields)
        is_relational = lambda field: columns[field]._type in ('one2many', 'many2many', 'many2one')
        get_o2m_values = itemgetter_tuple(
            [index for index, field in enumerate(fields_)
                  if columns[field[0]]._type == 'one2many'])
        get_nono2m_values = itemgetter_tuple(
            [index for index, field in enumerate(fields_)
                  if columns[field[0]]._type != 'one2many'])
        # Checks if the provided row has any non-empty non-relational field
        def only_o2m_values(row, f=get_nono2m_values, g=get_o2m_values):
            return any(g(row)) and not any(f(row))

        index = 0
        while True:
            if index >= len(data): return

            row = data[index]
            # copy non-relational fields to record dict
            record = dict((field[0], value)
                for field, value in itertools.izip(fields_, row)
                if not is_relational(field[0]))

            # Get all following rows which have relational values attached to
            # the current record (no non-relational values)
            record_span = itertools.takewhile(
                only_o2m_values, itertools.islice(data, index + 1, None))
            # stitch record row back on for relational fields
            record_span = list(itertools.chain([row], record_span))
            for relfield in set(
                    field[0] for field in fields_
                             if is_relational(field[0])):
                column = columns[relfield]
                # FIXME: how to not use _obj without relying on fields_get?
                Model = self.pool[column._obj]

                # get only cells for this sub-field, should be strictly
                # non-empty, field path [None] is for name_get column
                indices, subfields = zip(*((index, field[1:] or [None])
                                           for index, field in enumerate(fields_)
                                           if field[0] == relfield))

                # return all rows which have at least one value for the
                # subfields of relfield
                relfield_data = filter(any, map(itemgetter_tuple(indices), record_span))
                record[relfield] = [subrecord
                    for subrecord, _subinfo in Model._extract_records(
                        cr, uid, subfields, relfield_data,
                        context=context, log=log)]

            yield record, {'rows': {
                'from': index,
                'to': index + len(record_span) - 1
            }}
            index += len(record_span)
    def _convert_records(self, cr, uid, records,
                         context=None, log=lambda a: None):
        """ Converts records from the source iterable (recursive dicts of
        strings) into forms which can be written to the database (via
        self.create or (ir.model.data)._update)

        :returns: a list of triplets of (id, xid, record)
        :rtype: list((int|None, str|None, dict))
        """
        if context is None: context = {}
        Converter = self.pool['ir.fields.converter']
        columns = dict((k, v.column) for k, v in self._all_columns.iteritems())
        Translation = self.pool['ir.translation']
        field_names = dict(
            (f, (Translation._get_source(cr, uid, self._name + ',' + f, 'field',
                                         context.get('lang'))
                 or column.string))
            for f, column in columns.iteritems())

        convert = Converter.for_model(cr, uid, self, context=context)

        def _log(base, field, exception):
            type = 'warning' if isinstance(exception, Warning) else 'error'
            # logs the logical (not human-readable) field name for automated
            # processing of response, but injects human readable in message
            record = dict(base, type=type, field=field,
                          message=unicode(exception.args[0]) % base)
            if len(exception.args) > 1 and exception.args[1]:
                record.update(exception.args[1])
            log(record)

        stream = CountingStream(records)
        for record, extras in stream:
            dbid = False
            xid = False
            # name_get/name_create
            if None in record: pass
            # xid
            if 'id' in record:
                xid = record['id']
            # dbid
            if '.id' in record:
                try:
                    dbid = int(record['.id'])
                except ValueError:
                    # in case of overridden id column
                    dbid = record['.id']
                if not self.search(cr, uid, [('id', '=', dbid)], context=context):
                    log(dict(extras,
                        type='error',
                        record=stream.index,
                        field='.id',
                        message=_(u"Unknown database identifier '%s'") % dbid))
                    dbid = False

            converted = convert(record, lambda field, err:\
                _log(dict(extras, record=stream.index, field=field_names[field]), field, err))

            yield dbid, xid, converted, dict(extras, record=stream.index)

    def _validate(self, cr, uid, ids, context=None):
        context = context or {}
        lng = context.get('lang')
        trans = self.pool.get('ir.translation')
        error_msgs = []
        for constraint in self._constraints:
            fun, msg, fields = constraint
            try:
                # We don't pass around the context here: validation code
                # must always yield the same results.
                valid = fun(self, cr, uid, ids)
                extra_error = None 
            except Exception, e:
                _logger.debug('Exception while validating constraint', exc_info=True)
                valid = False
                extra_error = tools.ustr(e)
            if not valid:
                # Check presence of __call__ directly instead of using
                # callable() because it will be deprecated as of Python 3.0
                if hasattr(msg, '__call__'):
                    translated_msg = msg(self, cr, uid, ids, context=context)
                    if isinstance(translated_msg, tuple):
                        translated_msg = translated_msg[0] % translated_msg[1]
                else:
                    translated_msg = trans._get_source(cr, uid, self._name, 'constraint', lng, msg)
                if extra_error:
                    translated_msg += "\n\n%s\n%s" % (_('Error details:'), extra_error)
                error_msgs.append(
                        _("The field(s) `%s` failed against a constraint: %s") % (', '.join(fields), translated_msg)
                )
        if error_msgs:
            raise except_orm('ValidateError', '\n'.join(error_msgs))

    def default_get(self, cr, uid, fields_list, context=None):
        """
        Returns default values for the fields in fields_list.

        :param fields_list: list of fields to get the default values for (example ['field1', 'field2',])
        :type fields_list: list
        :param context: optional context dictionary - it may contains keys for specifying certain options
                        like ``context_lang`` (language) or ``context_tz`` (timezone) to alter the results of the call.
                        It may contain keys in the form ``default_XXX`` (where XXX is a field name), to set
                        or override a default value for a field.
                        A special ``bin_size`` boolean flag may also be passed in the context to request the
                        value of all fields.binary columns to be returned as the size of the binary instead of its
                        contents. This can also be selectively overriden by passing a field-specific flag
                        in the form ``bin_size_XXX: True/False`` where ``XXX`` is the name of the field.
                        Note: The ``bin_size_XXX`` form is new in OpenERP v6.0.
        :return: dictionary of the default values (set on the object model class, through user preferences, or in the context)
        """
        # trigger view init hook
        self.view_init(cr, uid, fields_list, context)

        if not context:
            context = {}
        defaults = {}

        # get the default values for the inherited fields
        for t in self._inherits.keys():
            defaults.update(self.pool[t].default_get(cr, uid, fields_list, context))

        # get the default values defined in the object
        for f in fields_list:
            if f in self._defaults:
                if callable(self._defaults[f]):
                    defaults[f] = self._defaults[f](self, cr, uid, context)
                else:
                    defaults[f] = self._defaults[f]

            fld_def = ((f in self._columns) and self._columns[f]) \
                    or ((f in self._inherit_fields) and self._inherit_fields[f][2]) \
                    or False

            if isinstance(fld_def, fields.property):
                property_obj = self.pool.get('ir.property')
                prop_value = property_obj.get(cr, uid, f, self._name, context=context)
                if prop_value:
                    if isinstance(prop_value, (browse_record, browse_null)):
                        defaults[f] = prop_value.id
                    else:
                        defaults[f] = prop_value
                else:
                    if f not in defaults:
                        defaults[f] = False

        # get the default values set by the user and override the default
        # values defined in the object
        ir_values_obj = self.pool.get('ir.values')
        res = ir_values_obj.get(cr, uid, 'default', False, [self._name])
        for id, field, field_value in res:
            if field in fields_list:
                fld_def = (field in self._columns) and self._columns[field] or self._inherit_fields[field][2]
                if fld_def._type == 'many2one':
                    obj = self.pool[fld_def._obj]
                    if not obj.search(cr, uid, [('id', '=', field_value or False)]):
                        continue
                if fld_def._type == 'many2many':
                    obj = self.pool[fld_def._obj]
                    field_value2 = []
                    for i in range(len(field_value or [])):
                        if not obj.search(cr, uid, [('id', '=',
                            field_value[i])]):
                            continue
                        field_value2.append(field_value[i])
                    field_value = field_value2
                if fld_def._type == 'one2many':
                    obj = self.pool[fld_def._obj]
                    field_value2 = []
                    for i in range(len(field_value or [])):
                        field_value2.append({})
                        for field2 in field_value[i]:
                            if field2 in obj._columns.keys() and obj._columns[field2]._type == 'many2one':
                                obj2 = self.pool[obj._columns[field2]._obj]
                                if not obj2.search(cr, uid,
                                        [('id', '=', field_value[i][field2])]):
                                    continue
                            elif field2 in obj._inherit_fields.keys() and obj._inherit_fields[field2][2]._type == 'many2one':
                                obj2 = self.pool[obj._inherit_fields[field2][2]._obj]
                                if not obj2.search(cr, uid,
                                        [('id', '=', field_value[i][field2])]):
                                    continue
                            # TODO add test for many2many and one2many
                            field_value2[i][field2] = field_value[i][field2]
                    field_value = field_value2
                defaults[field] = field_value

        # get the default values from the context
        for key in context or {}:
            if key.startswith('default_') and (key[8:] in fields_list):
                defaults[key[8:]] = context[key]
        return defaults

    def fields_get_keys(self, cr, user, context=None):
        res = self._columns.keys()
        # TODO I believe this loop can be replace by
        # res.extend(self._inherit_fields.key())
        for parent in self._inherits:
            res.extend(self.pool[parent].fields_get_keys(cr, user, context))
        return res

    def _rec_name_fallback(self, cr, uid, context=None):
        rec_name = self._rec_name
        if rec_name not in self._columns:
            rec_name = self._columns.keys()[0] if len(self._columns.keys()) > 0 else "id"
        return rec_name

    #
    # Overload this method if you need a window title which depends on the context
    #
    def view_header_get(self, cr, user, view_id=None, view_type='form', context=None):
        return False

    def user_has_groups(self, cr, uid, groups, context=None):
        """Return true if the user is at least member of one of the groups
           in groups_str. Typically used to resolve ``groups`` attribute
           in view and model definitions.

           :param str groups: comma-separated list of fully-qualified group
                              external IDs, e.g.: ``base.group_user,base.group_system``
           :return: True if the current user is a member of one of the
                    given groups
        """
        return any(self.pool['res.users'].has_group(cr, uid, group_ext_id)
                   for group_ext_id in groups.split(','))

    def _get_default_form_view(self, cr, user, context=None):
        """ Generates a default single-line form view using all fields
        of the current model except the m2m and o2m ones.

        :param cr: database cursor
        :param int user: user id
        :param dict context: connection context
        :returns: a form view as an lxml document
        :rtype: etree._Element
        """
        view = etree.Element('form', string=self._description)
        group = etree.SubElement(view, 'group', col="4")
        # TODO it seems fields_get can be replaced by _all_columns (no need for translation)
        for field, descriptor in self.fields_get(cr, user, context=context).iteritems():
            if descriptor['type'] in ('one2many', 'many2many'):
                continue
            etree.SubElement(group, 'field', name=field)
            if descriptor['type'] == 'text':
                etree.SubElement(group, 'newline')
        return view

    def _get_default_search_view(self, cr, user, context=None):
        """ Generates a single-field search view, based on _rec_name.

        :param cr: database cursor
        :param int user: user id
        :param dict context: connection context
        :returns: a tree view as an lxml document
        :rtype: etree._Element
        """
        view = etree.Element('search', string=self._description)
        etree.SubElement(view, 'field', name=self._rec_name_fallback(cr, user, context))
        return view

    def _get_default_tree_view(self, cr, user, context=None):
        """ Generates a single-field tree view, based on _rec_name.

        :param cr: database cursor
        :param int user: user id
        :param dict context: connection context
        :returns: a tree view as an lxml document
        :rtype: etree._Element
        """
        view = etree.Element('tree', string=self._description)
        etree.SubElement(view, 'field', name=self._rec_name_fallback(cr, user, context))
        return view

    def _get_default_calendar_view(self, cr, user, context=None):
        """ Generates a default calendar view by trying to infer
        calendar fields from a number of pre-set attribute names

        :param cr: database cursor
        :param int user: user id
        :param dict context: connection context
        :returns: a calendar view
        :rtype: etree._Element
        """
        def set_first_of(seq, in_, to):
            """Sets the first value of ``seq`` also found in ``in_`` to
            the ``to`` attribute of the view being closed over.

            Returns whether it's found a suitable value (and set it on
            the attribute) or not
            """
            for item in seq:
                if item in in_:
                    view.set(to, item)
                    return True
            return False

        view = etree.Element('calendar', string=self._description)
        etree.SubElement(view, 'field', name=self._rec_name_fallback(cr, user, context))

        if self._date_name not in self._columns:
            date_found = False
            for dt in ['date', 'date_start', 'x_date', 'x_date_start']:
                if dt in self._columns:
                    self._date_name = dt
                    date_found = True
                    break

            if not date_found:
                raise except_orm(_('Invalid Object Architecture!'), _("Insufficient fields for Calendar View!"))
        view.set('date_start', self._date_name)

        set_first_of(["user_id", "partner_id", "x_user_id", "x_partner_id"],
                     self._columns, 'color')

        if not set_first_of(["date_stop", "date_end", "x_date_stop", "x_date_end"],
                            self._columns, 'date_stop'):
            if not set_first_of(["date_delay", "planned_hours", "x_date_delay", "x_planned_hours"],
                                self._columns, 'date_delay'):
                raise except_orm(
                    _('Invalid Object Architecture!'),
                    _("Insufficient fields to generate a Calendar View for %s, missing a date_stop or a date_delay" % self._name))

        return view

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Get the detailed composition of the requested view like fields, model, view architecture

        :param view_id: id of the view or None
        :param view_type: type of the view to return if view_id is None ('form', tree', ...)
        :param toolbar: true to include contextual actions
        :param submenu: deprecated
        :return: dictionary describing the composition of the requested view (including inherited views and extensions)
        :raise AttributeError:
                            * if the inherited view has unknown position to work with other than 'before', 'after', 'inside', 'replace'
                            * if some tag other than 'position' is found in parent view
        :raise Invalid ArchitectureError: if there is view type other than form, tree, calendar, search etc defined on the structure
        """
        if context is None:
            context = {}
        View = self.pool['ir.ui.view']

        result = {
            'model': self._name,
            'field_parent': False,
        }

        # try to find a view_id if none provided
        if not view_id:
            # <view_type>_view_ref in context can be used to overrride the default view
            view_ref_key = view_type + '_view_ref'
            view_ref = context.get(view_ref_key)
            if view_ref:
                if '.' in view_ref:
                    module, view_ref = view_ref.split('.', 1)
                    cr.execute("SELECT res_id FROM ir_model_data WHERE model='ir.ui.view' AND module=%s AND name=%s", (module, view_ref))
                    view_ref_res = cr.fetchone()
                    if view_ref_res:
                        view_id = view_ref_res[0]
                else:
                    _logger.warning('%r requires a fully-qualified external id (got: %r for model %s). '
                        'Please use the complete `module.view_id` form instead.', view_ref_key, view_ref,
                        self._name)

            if not view_id:
                # otherwise try to find the lowest priority matching ir.ui.view
                view_id = View.default_view(cr, uid, self._name, view_type, context=context)

        # context for post-processing might be overriden
        ctx = context
        if view_id:
            # read the view with inherited views applied
            root_view = View.read_combined(cr, uid, view_id, fields=['id', 'name', 'field_parent', 'type', 'model', 'arch'], context=context)
            result['arch'] = root_view['arch']
            result['name'] = root_view['name']
            result['type'] = root_view['type']
            result['view_id'] = root_view['id']
            result['field_parent'] = root_view['field_parent']
            # override context fro postprocessing
            if root_view.get('model') != self._name:
                ctx = dict(context, base_model_name=root_view.get('model'))
        else:
            # fallback on default views methods if no ir.ui.view could be found
            try:
                get_func = getattr(self, '_get_default_%s_view' % view_type)
                arch_etree = get_func(cr, uid, context)
                result['arch'] = etree.tostring(arch_etree, encoding='utf-8')
                result['type'] = view_type
                result['name'] = 'default'
            except AttributeError:
                raise except_orm(_('Invalid Architecture!'), _("No default view of type '%s' could be found !") % view_type)

        # Apply post processing, groups and modifiers etc...
        xarch, xfields = View.postprocess_and_fields(cr, uid, self._name, etree.fromstring(result['arch']), view_id, context=ctx)
        result['arch'] = xarch
        result['fields'] = xfields

        # Add related action information if aksed
        if toolbar:
            toclean = ('report_sxw_content', 'report_rml_content', 'report_sxw', 'report_rml', 'report_sxw_content_data', 'report_rml_content_data')
            def clean(x):
                x = x[2]
                for key in toclean:
                    x.pop(key, None)
                return x
            ir_values_obj = self.pool.get('ir.values')
            resprint = ir_values_obj.get(cr, uid, 'action', 'client_print_multi', [(self._name, False)], False, context)
            resaction = ir_values_obj.get(cr, uid, 'action', 'client_action_multi', [(self._name, False)], False, context)
            resrelate = ir_values_obj.get(cr, uid, 'action', 'client_action_relate', [(self._name, False)], False, context)
            resaction = [clean(action) for action in resaction if view_type == 'tree' or not action[2].get('multi')]
            resprint = [clean(print_) for print_ in resprint if view_type == 'tree' or not print_[2].get('multi')]
            #When multi="True" set it will display only in More of the list view
            resrelate = [clean(action) for action in resrelate
                         if (action[2].get('multi') and view_type == 'tree') or (not action[2].get('multi') and view_type == 'form')]

            for x in itertools.chain(resprint, resaction, resrelate):
                x['string'] = x['name']

            result['toolbar'] = {
                'print': resprint,
                'action': resaction,
                'relate': resrelate
            }
        return result

    def get_formview_id(self, cr, uid, id, context=None):
        """ Return an view id to open the document with. This method is meant to be
            overridden in addons that want to give specific view ids for example.

            :param int id: id of the document to open
        """
        return False

    def get_formview_action(self, cr, uid, id, context=None):
        """ Return an action to open the document. This method is meant to be
            overridden in addons that want to give specific view ids for example.

            :param int id: id of the document to open
        """
        view_id = self.get_formview_id(cr, uid, id, context=context)
        return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_type': 'form',
                'view_mode': 'form',
                'views': [(view_id, 'form')],
                'target': 'current',
                'res_id': id,
            }

    def _view_look_dom_arch(self, cr, uid, node, view_id, context=None):
        return self.pool['ir.ui.view'].postprocess_and_fields(
            cr, uid, self._name, node, view_id, context=context)

    def search_count(self, cr, user, args, context=None):
        res = self.search(cr, user, args, context=context, count=True)
        if isinstance(res, list):
            return len(res)
        return res

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        """
        Search for records based on a search domain.

        :param cr: database cursor
        :param user: current user id
        :param args: list of tuples specifying the search domain [('field_name', 'operator', value), ...]. Pass an empty list to match all records.
        :param offset: optional number of results to skip in the returned values (default: 0)
        :param limit: optional max number of records to return (default: **None**)
        :param order: optional columns to sort by (default: self._order=id )
        :param context: optional context arguments, like lang, time zone
        :type context: dictionary
        :param count: optional (default: **False**), if **True**, returns only the number of records matching the criteria, not their ids
        :return: id or list of ids of records matching the criteria
        :rtype: integer or list of integers
        :raise AccessError: * if user tries to bypass access rules for read on the requested object.

        **Expressing a search domain (args)**

        Each tuple in the search domain needs to have 3 elements, in the form: **('field_name', 'operator', value)**, where:

            * **field_name** must be a valid name of field of the object model, possibly following many-to-one relationships using dot-notation, e.g 'street' or 'partner_id.country' are valid values.
            * **operator** must be a string with a valid comparison operator from this list: ``=, !=, >, >=, <, <=, like, ilike, in, not in, child_of, parent_left, parent_right``
              The semantics of most of these operators are obvious.
              The ``child_of`` operator will look for records who are children or grand-children of a given record,
              according to the semantics of this model (i.e following the relationship field named by
              ``self._parent_name``, by default ``parent_id``.
            * **value** must be a valid value to compare with the values of **field_name**, depending on its type.

        Domain criteria can be combined using 3 logical operators than can be added between tuples:  '**&**' (logical AND, default), '**|**' (logical OR), '**!**' (logical NOT).
        These are **prefix** operators and the arity of the '**&**' and '**|**' operator is 2, while the arity of the '**!**' is just 1.
        Be very careful about this when you combine them the first time.

        Here is an example of searching for Partners named *ABC* from Belgium and Germany whose language is not english ::

            [('name','=','ABC'),'!',('language.code','=','en_US'),'|',('country_id.code','=','be'),('country_id.code','=','de'))

        The '&' is omitted as it is the default, and of course we could have used '!=' for the language, but what this domain really represents is::

            (name is 'ABC' AND (language is NOT english) AND (country is Belgium OR Germany))

        """
        return self._search(cr, user, args, offset=offset, limit=limit, order=order, context=context, count=count)

    def name_get(self, cr, user, ids, context=None):
        """Returns the preferred display value (text representation) for the records with the
           given ``ids``. By default this will be the value of the ``name`` column, unless
           the model implements a custom behavior.
           Can sometimes be seen as the inverse function of :meth:`~.name_search`, but it is not
           guaranteed to be.

           :rtype: list(tuple)
           :return: list of pairs ``(id,text_repr)`` for all records with the given ``ids``.
        """
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]

        if self._rec_name in self._all_columns:
            rec_name_column = self._all_columns[self._rec_name].column
            return [(r['id'], rec_name_column.as_display_name(cr, user, self, r[self._rec_name], context=context))
                        for r in self.read(cr, user, ids, [self._rec_name],
                                       load='_classic_write', context=context)]
        return [(id, "%s,%s" % (self._name, id)) for id in ids]

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        """Search for records that have a display name matching the given ``name`` pattern if compared
           with the given ``operator``, while also matching the optional search domain (``args``).
           This is used for example to provide suggestions based on a partial value for a relational
           field.
           Sometimes be seen as the inverse function of :meth:`~.name_get`, but it is not
           guaranteed to be.

           This method is equivalent to calling :meth:`~.search` with a search domain based on ``name``
           and then :meth:`~.name_get` on the result of the search.

           :param list args: optional search domain (see :meth:`~.search` for syntax),
                             specifying further restrictions
           :param str operator: domain operator for matching the ``name`` pattern, such as ``'like'``
                                or ``'='``.
           :param int limit: optional max number of records to return
           :rtype: list
           :return: list of pairs ``(id,text_repr)`` for all matching records.
        """
        return self._name_search(cr, user, name, args, operator, context, limit)

    def name_create(self, cr, uid, name, context=None):
        """Creates a new record by calling :meth:`~.create` with only one
           value provided: the name of the new record (``_rec_name`` field).
           The new record will also be initialized with any default values applicable
           to this model, or provided through the context. The usual behavior of
           :meth:`~.create` applies.
           Similarly, this method may raise an exception if the model has multiple
           required fields and some do not have default values.

           :param name: name of the record to create

           :rtype: tuple
           :return: the :meth:`~.name_get` pair value for the newly-created record.
        """
        rec_id = self.create(cr, uid, {self._rec_name: name}, context)
        return self.name_get(cr, uid, [rec_id], context)[0]

    # private implementation of name_search, allows passing a dedicated user for the name_get part to
    # solve some access rights issues
    def _name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100, name_get_uid=None):
        if args is None:
            args = []
        if context is None:
            context = {}
        args = args[:]
        # optimize out the default criterion of ``ilike ''`` that matches everything
        if not (name == '' and operator == 'ilike'):
            args += [(self._rec_name, operator, name)]
        access_rights_uid = name_get_uid or user
        ids = self._search(cr, user, args, limit=limit, context=context, access_rights_uid=access_rights_uid)
        res = self.name_get(cr, access_rights_uid, ids, context)
        return res

    def read_string(self, cr, uid, id, langs, fields=None, context=None):
        res = {}
        res2 = {}
        self.pool.get('ir.translation').check_access_rights(cr, uid, 'read')
        if not fields:
            fields = self._columns.keys() + self._inherit_fields.keys()
        #FIXME: collect all calls to _get_source into one SQL call.
        for lang in langs:
            res[lang] = {'code': lang}
            for f in fields:
                if f in self._columns:
                    res_trans = self.pool.get('ir.translation')._get_source(cr, uid, self._name+','+f, 'field', lang)
                    if res_trans:
                        res[lang][f] = res_trans
                    else:
                        res[lang][f] = self._columns[f].string
        for table in self._inherits:
            cols = intersect(self._inherit_fields.keys(), fields)
            res2 = self.pool[table].read_string(cr, uid, id, langs, cols, context)
        for lang in res2:
            if lang in res:
                res[lang]['code'] = lang
            for f in res2[lang]:
                res[lang][f] = res2[lang][f]
        return res

    def write_string(self, cr, uid, id, langs, vals, context=None):
        self.pool.get('ir.translation').check_access_rights(cr, uid, 'write')
        #FIXME: try to only call the translation in one SQL
        for lang in langs:
            for field in vals:
                if field in self._columns:
                    src = self._columns[field].string
                    self.pool.get('ir.translation')._set_ids(cr, uid, self._name+','+field, 'field', lang, [0], vals[field], src)
        for table in self._inherits:
            cols = intersect(self._inherit_fields.keys(), vals)
            if cols:
                self.pool[table].write_string(cr, uid, id, langs, vals, context)
        return True

    def _add_missing_default_values(self, cr, uid, values, context=None):
        missing_defaults = []
        avoid_tables = [] # avoid overriding inherited values when parent is set
        for tables, parent_field in self._inherits.items():
            if parent_field in values:
                avoid_tables.append(tables)
        for field in self._columns.keys():
            if not field in values:
                missing_defaults.append(field)
        for field in self._inherit_fields.keys():
            if (field not in values) and (self._inherit_fields[field][0] not in avoid_tables):
                missing_defaults.append(field)

        if len(missing_defaults):
            # override defaults with the provided values, never allow the other way around
            defaults = self.default_get(cr, uid, missing_defaults, context)
            for dv in defaults:
                if ((dv in self._columns and self._columns[dv]._type == 'many2many') \
                     or (dv in self._inherit_fields and self._inherit_fields[dv][2]._type == 'many2many')) \
                        and defaults[dv] and isinstance(defaults[dv][0], (int, long)):
                    defaults[dv] = [(6, 0, defaults[dv])]
                if (dv in self._columns and self._columns[dv]._type == 'one2many' \
                    or (dv in self._inherit_fields and self._inherit_fields[dv][2]._type == 'one2many')) \
                        and isinstance(defaults[dv], (list, tuple)) and defaults[dv] and isinstance(defaults[dv][0], dict):
                    defaults[dv] = [(0, 0, x) for x in defaults[dv]]
            defaults.update(values)
            values = defaults
        return values

    def clear_caches(self):
        """ Clear the caches

        This clears the caches associated to methods decorated with
        ``tools.ormcache`` or ``tools.ormcache_multi``.
        """
        try:
            getattr(self, '_ormcache')
            self._ormcache = {}
            self.pool._any_cache_cleared = True
        except AttributeError:
            pass


    def _read_group_fill_results(self, cr, uid, domain, groupby, remaining_groupbys, aggregated_fields,
                                 read_group_result, read_group_order=None, context=None):
        """Helper method for filling in empty groups for all possible values of
           the field being grouped by"""

        # self._group_by_full should map groupable fields to a method that returns
        # a list of all aggregated values that we want to display for this field,
        # in the form of a m2o-like pair (key,label).
        # This is useful to implement kanban views for instance, where all columns
        # should be displayed even if they don't contain any record.

        # Grab the list of all groups that should be displayed, including all present groups
        present_group_ids = [x[groupby][0] for x in read_group_result if x[groupby]]
        all_groups,folded = self._group_by_full[groupby](self, cr, uid, present_group_ids, domain,
                                                  read_group_order=read_group_order,
                                                  access_rights_uid=openerp.SUPERUSER_ID,
                                                  context=context)

        result_template = dict.fromkeys(aggregated_fields, False)
        result_template[groupby + '_count'] = 0
        if remaining_groupbys:
            result_template['__context'] = {'group_by': remaining_groupbys}

        # Merge the left_side (current results as dicts) with the right_side (all
        # possible values as m2o pairs). Both lists are supposed to be using the
        # same ordering, and can be merged in one pass.
        result = []
        known_values = {}
        def append_left(left_side):
            grouped_value = left_side[groupby] and left_side[groupby][0]
            if not grouped_value in known_values:
                result.append(left_side)
                known_values[grouped_value] = left_side
            else:
                count_attr = groupby + '_count'
                known_values[grouped_value].update({count_attr: left_side[count_attr]})
        def append_right(right_side):
            grouped_value = right_side[0]
            if not grouped_value in known_values:
                line = dict(result_template)
                line[groupby] = right_side
                line['__domain'] = [(groupby,'=',grouped_value)] + domain
                result.append(line)
                known_values[grouped_value] = line
        while read_group_result or all_groups:
            left_side = read_group_result[0] if read_group_result else None
            right_side = all_groups[0] if all_groups else None
            assert left_side is None or left_side[groupby] is False \
                 or isinstance(left_side[groupby], (tuple,list)), \
                'M2O-like pair expected, got %r' % left_side[groupby]
            assert right_side is None or isinstance(right_side, (tuple,list)), \
                'M2O-like pair expected, got %r' % right_side
            if left_side is None:
                append_right(all_groups.pop(0))
            elif right_side is None:
                append_left(read_group_result.pop(0))
            elif left_side[groupby] == right_side:
                append_left(read_group_result.pop(0))
                all_groups.pop(0) # discard right_side
            elif not left_side[groupby] or not left_side[groupby][0]:
                # left side == "Undefined" entry, not present on right_side
                append_left(read_group_result.pop(0))
            else:
                append_right(all_groups.pop(0))

        if folded:
            for r in result:
                r['__fold'] = folded.get(r[groupby] and r[groupby][0], False)
        return result

    def _read_group_prepare(self, orderby, aggregated_fields, annotated_groupbys, query):
        """
        Prepares the GROUP BY and ORDER BY terms for the read_group method. Adds the missing JOIN clause
        to the query if order should be computed against m2o field. 
        :param orderby: the orderby definition in the form "%(field)s %(order)s"
        :param aggregated_fields: list of aggregated fields in the query
        :param annotated_groupbys: list of dictionaries returned by _read_group_process_groupby
                These dictionaries contains the qualified name of each groupby
                (fully qualified SQL name for the corresponding field),
                and the (non raw) field name.
        :param osv.Query query: the query under construction
        :return: (groupby_terms, orderby_terms)
        """
        orderby_terms = []
        groupby_terms = [gb['qualified_field'] for gb in annotated_groupbys]
        groupby_fields = [gb['groupby'] for gb in annotated_groupbys]
        if not orderby:
            return groupby_terms, orderby_terms

        self._check_qorder(orderby)
        for order_part in orderby.split(','):
            order_split = order_part.split()
            order_field = order_split[0]
            if order_field in groupby_fields:

                if self._all_columns[order_field.split(':')[0]].column._type == 'many2one':
                    order_clause = self._generate_order_by(order_part, query).replace('ORDER BY ', '')
                    if order_clause:
                        orderby_terms.append(order_clause)
                        groupby_terms += [order_term.split()[0] for order_term in order_clause.split(',')]
                else:
                    order = '"%s" %s' % (order_field, '' if len(order_split) == 1 else order_split[1])
                    orderby_terms.append(order)
            elif order_field in aggregated_fields:
                orderby_terms.append(order_part)
            else:
                # Cannot order by a field that will not appear in the results (needs to be grouped or aggregated)
                _logger.warn('%s: read_group order by `%s` ignored, cannot sort on empty columns (not grouped/aggregated)',
                             self._name, order_part)
        return groupby_terms, orderby_terms

    def _read_group_process_groupby(self, gb, query, context):
        """
            Helper method to collect important information about groupbys: raw
            field name, type, time informations, qualified name, ...
        """
        split = gb.split(':')
        field_type = self._all_columns[split[0]].column._type
        gb_function = split[1] if len(split) == 2 else None
        temporal = field_type in ('date', 'datetime')
        tz_convert = field_type == 'datetime' and context.get('tz') in pytz.all_timezones
        qualified_field = self._inherits_join_calc(split[0], query)
        if temporal:
            display_formats = {
                'day': 'dd MMM YYYY', 
                'week': "'W'w YYYY", 
                'month': 'MMMM YYYY', 
                'quarter': 'QQQ YYYY', 
                'year': 'YYYY'
            }
            time_intervals = {
                'day': dateutil.relativedelta.relativedelta(days=1),
                'week': datetime.timedelta(days=7),
                'month': dateutil.relativedelta.relativedelta(months=1),
                'quarter': dateutil.relativedelta.relativedelta(months=3),
                'year': dateutil.relativedelta.relativedelta(years=1)
            }
            if tz_convert:
                qualified_field = "timezone('%s', timezone('UTC',%s))" % (context.get('tz', 'UTC'), qualified_field)
            qualified_field = "date_trunc('%s', %s)" % (gb_function or 'month', qualified_field)
        if field_type == 'boolean':
            qualified_field = "coalesce(%s,false)" % qualified_field
        return {
            'field': split[0],
            'groupby': gb,
            'type': field_type, 
            'display_format': display_formats[gb_function or 'month'] if temporal else None,
            'interval': time_intervals[gb_function or 'month'] if temporal else None,                
            'tz_convert': tz_convert,
            'qualified_field': qualified_field
        }

    def _read_group_prepare_data(self, key, value, groupby_dict, context):
        """
            Helper method to sanitize the data received by read_group. The None
            values are converted to False, and the date/datetime are formatted,
            and corrected according to the timezones.
        """
        value = False if value is None else value
        gb = groupby_dict.get(key)
        if gb and gb['type'] in ('date', 'datetime') and value:
            if isinstance(value, basestring):
                dt_format = DEFAULT_SERVER_DATETIME_FORMAT if gb['type'] == 'datetime' else DEFAULT_SERVER_DATE_FORMAT
                value = datetime.datetime.strptime(value, dt_format)
            if gb['tz_convert']:
                value =  pytz.timezone(context['tz']).localize(value)
        return value

    def _read_group_get_domain(self, groupby, value):
        """
            Helper method to construct the domain corresponding to a groupby and 
            a given value. This is mostly relevant for date/datetime.
        """
        if groupby['type'] in ('date', 'datetime') and value:
            dt_format = DEFAULT_SERVER_DATETIME_FORMAT if groupby['type'] == 'datetime' else DEFAULT_SERVER_DATE_FORMAT
            domain_dt_begin = value
            domain_dt_end = value + groupby['interval']
            if groupby['tz_convert']:
                domain_dt_begin = domain_dt_begin.astimezone(pytz.utc)
                domain_dt_end = domain_dt_end.astimezone(pytz.utc)
            return [(groupby['field'], '>=', domain_dt_begin.strftime(dt_format)),
                   (groupby['field'], '<', domain_dt_end.strftime(dt_format))]
        if groupby['type'] == 'many2one' and value:
                value = value[0]
        return [(groupby['field'], '=', value)]

    def _read_group_format_result(self, data, annotated_groupbys, groupby, groupby_dict, domain, context):
        """
            Helper method to format the data contained in the dictianary data by 
            adding the domain corresponding to its values, the groupbys in the 
            context and by properly formatting the date/datetime values. 
        """
        domain_group = [dom for gb in annotated_groupbys for dom in self._read_group_get_domain(gb, data[gb['groupby']])]
        for k,v in data.iteritems():
            gb = groupby_dict.get(k)
            if gb and gb['type'] in ('date', 'datetime') and v:
                data[k] = babel.dates.format_date(v, format=gb['display_format'], locale=context.get('lang', 'en_US'))

        data['__domain'] = domain_group + domain 
        if len(groupby) - len(annotated_groupbys) >= 1:
            data['__context'] = { 'group_by': groupby[len(annotated_groupbys):]}
        del data['id']
        return data

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        """
        Get the list of records in list view grouped by the given ``groupby`` fields

        :param cr: database cursor
        :param uid: current user id
        :param domain: list specifying search criteria [['field_name', 'operator', 'value'], ...]
        :param list fields: list of fields present in the list view specified on the object
        :param list groupby: list of groupby descriptions by which the records will be grouped.  
                A groupby description is either a field (then it will be grouped by that field)
                or a string 'field:groupby_function'.  Right now, the only functions supported
                are 'day', 'week', 'month', 'quarter' or 'year', and they only make sense for 
                date/datetime fields.
        :param int offset: optional number of records to skip
        :param int limit: optional max number of records to return
        :param dict context: context arguments, like lang, time zone. 
        :param list orderby: optional ``order by`` specification, for
                             overriding the natural sort ordering of the
                             groups, see also :py:meth:`~osv.osv.osv.search`
                             (supported only for many2one fields currently)
        :param bool lazy: if true, the results are only grouped by the first groupby and the 
                remaining groupbys are put in the __context key.  If false, all the groupbys are
                done in one call.
        :return: list of dictionaries(one dictionary for each record) containing:

                    * the values of fields grouped by the fields in ``groupby`` argument
                    * __domain: list of tuples specifying the search criteria
                    * __context: dictionary with argument like ``groupby``
        :rtype: [{'field_name_1': value, ...]
        :raise AccessError: * if user has no read rights on the requested object
                            * if user tries to bypass access rules for read on the requested object
        """
        if context is None:
            context = {}
        self.check_access_rights(cr, uid, 'read')
        query = self._where_calc(cr, uid, domain, context=context) 
        fields = fields or self._columns.keys()

        groupby = [groupby] if isinstance(groupby, basestring) else groupby
        groupby_list = groupby[:1] if lazy else groupby
        annotated_groupbys = [self._read_group_process_groupby(gb, query, context) 
                                    for gb in groupby_list]
        groupby_fields = [g['field'] for g in annotated_groupbys]
        order = orderby or ','.join([g for g in groupby_list])
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}

        self._apply_ir_rules(cr, uid, query, 'read', context=context)
        for gb in groupby_fields:
            assert gb in fields, "Fields in 'groupby' must appear in the list of fields to read (perhaps it's missing in the list view?)"
            groupby_def = self._columns.get(gb) or (self._inherit_fields.get(gb) and self._inherit_fields.get(gb)[2])
            assert groupby_def and groupby_def._classic_write, "Fields in 'groupby' must be regular database-persisted fields (no function or related fields), or function fields with store=True"
            if not (gb in self._all_columns):
                # Don't allow arbitrary values, as this would be a SQL injection vector!
                raise except_orm(_('Invalid group_by'),
                                 _('Invalid group_by specification: "%s".\nA group_by specification must be a list of valid fields.')%(gb,))

        aggregated_fields = [
            f for f in fields
            if f not in ('id', 'sequence')
            if f not in groupby_fields
            if self._all_columns[f].column._type in ('integer', 'float')
            if getattr(self._all_columns[f].column, '_classic_write')]

        field_formatter = lambda f: (self._all_columns[f].column.group_operator or 'sum', self._inherits_join_calc(f, query), f)
        select_terms = ["%s(%s) AS %s" % field_formatter(f) for f in aggregated_fields]

        for gb in annotated_groupbys:
            select_terms.append('%s as "%s" ' % (gb['qualified_field'], gb['groupby']))

        groupby_terms, orderby_terms = self._read_group_prepare(order, aggregated_fields, annotated_groupbys, query)
        from_clause, where_clause, where_clause_params = query.get_sql()
        if lazy and (len(groupby_fields) >= 2 or not context.get('group_by_no_leaf')):
            count_field = groupby_fields[0] if len(groupby_fields) >= 1 else '_'
        else:
            count_field = '_'

        prefix_terms = lambda prefix, terms: (prefix + " " + ",".join(terms)) if terms else ''
        prefix_term = lambda prefix, term: ('%s %s' % (prefix, term)) if term else ''

        query = """
            SELECT min(%(table)s.id) AS id, count(%(table)s.id) AS %(count_field)s_count %(extra_fields)s
            FROM %(from)s
            %(where)s
            %(groupby)s
            %(orderby)s
            %(limit)s
            %(offset)s
        """ % {
            'table': self._table,
            'count_field': count_field,
            'extra_fields': prefix_terms(',', select_terms),
            'from': from_clause,
            'where': prefix_term('WHERE', where_clause),
            'groupby': prefix_terms('GROUP BY', groupby_terms),
            'orderby': prefix_terms('ORDER BY', orderby_terms),
            'limit': prefix_term('LIMIT', int(limit) if limit else None),
            'offset': prefix_term('OFFSET', int(offset) if limit else None),
        }
        cr.execute(query, where_clause_params)
        fetched_data = cr.dictfetchall()

        if not groupby_fields:
            return fetched_data

        many2onefields = [gb['field'] for gb in annotated_groupbys if gb['type'] == 'many2one']
        if many2onefields:
            data_ids = [r['id'] for r in fetched_data]
            many2onefields = list(set(many2onefields))
            data_dict = {d['id']: d for d in self.read(cr, uid, data_ids, many2onefields, context=context)} 
            for d in fetched_data:
                d.update(data_dict[d['id']])

        data = map(lambda r: {k: self._read_group_prepare_data(k,v, groupby_dict, context) for k,v in r.iteritems()}, fetched_data)
        result = [self._read_group_format_result(d, annotated_groupbys, groupby, groupby_dict, domain, context) for d in data]
        if lazy and groupby_fields[0] in self._group_by_full:
            # Right now, read_group only fill results in lazy mode (by default).
            # If you need to have the empty groups in 'eager' mode, then the
            # method _read_group_fill_results need to be completely reimplemented
            # in a sane way 
            result = self._read_group_fill_results(cr, uid, domain, groupby_fields[0], groupby[len(annotated_groupbys):],
                                                       aggregated_fields, result, read_group_order=order,
                                                       context=context)
        return result

    def _inherits_join_add(self, current_model, parent_model_name, query):
        """
        Add missing table SELECT and JOIN clause to ``query`` for reaching the parent table (no duplicates)
        :param current_model: current model object
        :param parent_model_name: name of the parent model for which the clauses should be added
        :param query: query object on which the JOIN should be added
        """
        inherits_field = current_model._inherits[parent_model_name]
        parent_model = self.pool[parent_model_name]
        parent_alias, parent_alias_statement = query.add_join((current_model._table, parent_model._table, inherits_field, 'id', inherits_field), implicit=True)
        return parent_alias

    def _inherits_join_calc(self, field, query):
        """
        Adds missing table select and join clause(s) to ``query`` for reaching
        the field coming from an '_inherits' parent table (no duplicates).

        :param field: name of inherited field to reach
        :param query: query object on which the JOIN should be added
        :return: qualified name of field, to be used in SELECT clause
        """
        current_table = self
        parent_alias = '"%s"' % current_table._table
        while field in current_table._inherit_fields and not field in current_table._columns:
            parent_model_name = current_table._inherit_fields[field][0]
            parent_table = self.pool[parent_model_name]
            parent_alias = self._inherits_join_add(current_table, parent_model_name, query)
            current_table = parent_table
        return '%s."%s"' % (parent_alias, field)

    def _parent_store_compute(self, cr):
        if not self._parent_store:
            return
        _logger.info('Computing parent left and right for table %s...', self._table)
        def browse_rec(root, pos=0):
            # TODO: set order
            where = self._parent_name+'='+str(root)
            if not root:
                where = self._parent_name+' IS NULL'
            if self._parent_order:
                where += ' order by '+self._parent_order
            cr.execute('SELECT id FROM '+self._table+' WHERE '+where)
            pos2 = pos + 1
            for id in cr.fetchall():
                pos2 = browse_rec(id[0], pos2)
            cr.execute('update '+self._table+' set parent_left=%s, parent_right=%s where id=%s', (pos, pos2, root))
            return pos2 + 1
        query = 'SELECT id FROM '+self._table+' WHERE '+self._parent_name+' IS NULL'
        if self._parent_order:
            query += ' order by ' + self._parent_order
        pos = 0
        cr.execute(query)
        for (root,) in cr.fetchall():
            pos = browse_rec(root, pos)
        return True

    def _update_store(self, cr, f, k):
        _logger.info("storing computed values of fields.function '%s'", k)
        ss = self._columns[k]._symbol_set
        update_query = 'UPDATE "%s" SET "%s"=%s WHERE id=%%s' % (self._table, k, ss[0])
        cr.execute('select id from '+self._table)
        ids_lst = map(lambda x: x[0], cr.fetchall())
        while ids_lst:
            iids = ids_lst[:AUTOINIT_RECALCULATE_STORED_FIELDS]
            ids_lst = ids_lst[AUTOINIT_RECALCULATE_STORED_FIELDS:]
            res = f.get(cr, self, iids, k, SUPERUSER_ID, {})
            for key, val in res.items():
                if f._multi:
                    val = val[k]
                # if val is a many2one, just write the ID
                if type(val) == tuple:
                    val = val[0]
                if val is not False:
                    cr.execute(update_query, (ss[1](val), key))

    def _check_selection_field_value(self, cr, uid, field, value, context=None):
        """Raise except_orm if value is not among the valid values for the selection field"""
        if self._columns[field]._type == 'reference':
            val_model, val_id_str = value.split(',', 1)
            val_id = False
            try:
                val_id = long(val_id_str)
            except ValueError:
                pass
            if not val_id:
                raise except_orm(_('ValidateError'),
                                 _('Invalid value for reference field "%s.%s" (last part must be a non-zero integer): "%s"') % (self._table, field, value))
            val = val_model
        else:
            val = value
        if isinstance(self._columns[field].selection, (tuple, list)):
            if val in dict(self._columns[field].selection):
                return
        elif val in dict(self._columns[field].selection(self, cr, uid, context=context)):
            return
        raise except_orm(_('ValidateError'),
                         _('The value "%s" for the field "%s.%s" is not in the selection') % (value, self._table, field))

    def _check_removed_columns(self, cr, log=False):
        # iterate on the database columns to drop the NOT NULL constraints
        # of fields which were required but have been removed (or will be added by another module)
        columns = [c for c in self._columns if not (isinstance(self._columns[c], fields.function) and not self._columns[c].store)]
        columns += MAGIC_COLUMNS
        cr.execute("SELECT a.attname, a.attnotnull"
                   "  FROM pg_class c, pg_attribute a"
                   " WHERE c.relname=%s"
                   "   AND c.oid=a.attrelid"
                   "   AND a.attisdropped=%s"
                   "   AND pg_catalog.format_type(a.atttypid, a.atttypmod) NOT IN ('cid', 'tid', 'oid', 'xid')"
                   "   AND a.attname NOT IN %s", (self._table, False, tuple(columns))),

        for column in cr.dictfetchall():
            if log:
                _logger.debug("column %s is in the table %s but not in the corresponding object %s",
                              column['attname'], self._table, self._name)
            if column['attnotnull']:
                cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" DROP NOT NULL' % (self._table, column['attname']))
                _schema.debug("Table '%s': column '%s': dropped NOT NULL constraint",
                              self._table, column['attname'])

    def _save_constraint(self, cr, constraint_name, type):
        """
        Record the creation of a constraint for this model, to make it possible
        to delete it later when the module is uninstalled. Type can be either
        'f' or 'u' depending on the constraint being a foreign key or not.
        """
        if not self._module:
            # no need to save constraints for custom models as they're not part
            # of any module
            return
        assert type in ('f', 'u')
        cr.execute("""
            SELECT 1 FROM ir_model_constraint, ir_module_module
            WHERE ir_model_constraint.module=ir_module_module.id
                AND ir_model_constraint.name=%s
                AND ir_module_module.name=%s
            """, (constraint_name, self._module))
        if not cr.rowcount:
            cr.execute("""
                INSERT INTO ir_model_constraint
                    (name, date_init, date_update, module, model, type)
                VALUES (%s, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC',
                    (SELECT id FROM ir_module_module WHERE name=%s),
                    (SELECT id FROM ir_model WHERE model=%s), %s)""",
                    (constraint_name, self._module, self._name, type))

    def _save_relation_table(self, cr, relation_table):
        """
        Record the creation of a many2many for this model, to make it possible
        to delete it later when the module is uninstalled.
        """
        cr.execute("""
            SELECT 1 FROM ir_model_relation, ir_module_module
            WHERE ir_model_relation.module=ir_module_module.id
                AND ir_model_relation.name=%s
                AND ir_module_module.name=%s
            """, (relation_table, self._module))
        if not cr.rowcount:
            cr.execute("""INSERT INTO ir_model_relation (name, date_init, date_update, module, model)
                                 VALUES (%s, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC',
                    (SELECT id FROM ir_module_module WHERE name=%s),
                    (SELECT id FROM ir_model WHERE model=%s))""",
                       (relation_table, self._module, self._name))

    # checked version: for direct m2o starting from `self`
    def _m2o_add_foreign_key_checked(self, source_field, dest_model, ondelete):
        assert self.is_transient() or not dest_model.is_transient(), \
            'Many2One relationships from non-transient Model to TransientModel are forbidden'
        if self.is_transient() and not dest_model.is_transient():
            # TransientModel relationships to regular Models are annoying
            # usually because they could block deletion due to the FKs.
            # So unless stated otherwise we default them to ondelete=cascade.
            ondelete = ondelete or 'cascade'
        fk_def = (self._table, source_field, dest_model._table, ondelete or 'set null')
        self._foreign_keys.add(fk_def)
        _schema.debug("Table '%s': added foreign key '%s' with definition=REFERENCES \"%s\" ON DELETE %s", *fk_def)

    # unchecked version: for custom cases, such as m2m relationships
    def _m2o_add_foreign_key_unchecked(self, source_table, source_field, dest_model, ondelete):
        fk_def = (source_table, source_field, dest_model._table, ondelete or 'set null')
        self._foreign_keys.add(fk_def)
        _schema.debug("Table '%s': added foreign key '%s' with definition=REFERENCES \"%s\" ON DELETE %s", *fk_def)

    def _drop_constraint(self, cr, source_table, constraint_name):
        cr.execute("ALTER TABLE %s DROP CONSTRAINT %s" % (source_table,constraint_name))

    def _m2o_fix_foreign_key(self, cr, source_table, source_field, dest_model, ondelete):
        # Find FK constraint(s) currently established for the m2o field,
        # and see whether they are stale or not
        cr.execute("""SELECT confdeltype as ondelete_rule, conname as constraint_name,
                             cl2.relname as foreign_table
                      FROM pg_constraint as con, pg_class as cl1, pg_class as cl2,
                           pg_attribute as att1, pg_attribute as att2
                      WHERE con.conrelid = cl1.oid
                        AND cl1.relname = %s
                        AND con.confrelid = cl2.oid
                        AND array_lower(con.conkey, 1) = 1
                        AND con.conkey[1] = att1.attnum
                        AND att1.attrelid = cl1.oid
                        AND att1.attname = %s
                        AND array_lower(con.confkey, 1) = 1
                        AND con.confkey[1] = att2.attnum
                        AND att2.attrelid = cl2.oid
                        AND att2.attname = %s
                        AND con.contype = 'f'""", (source_table, source_field, 'id'))
        constraints = cr.dictfetchall()
        if constraints:
            if len(constraints) == 1:
                # Is it the right constraint?
                cons, = constraints
                if cons['ondelete_rule'] != POSTGRES_CONFDELTYPES.get((ondelete or 'set null').upper(), 'a')\
                    or cons['foreign_table'] != dest_model._table:
                    # Wrong FK: drop it and recreate
                    _schema.debug("Table '%s': dropping obsolete FK constraint: '%s'",
                                  source_table, cons['constraint_name'])
                    self._drop_constraint(cr, source_table, cons['constraint_name'])
                else:
                    # it's all good, nothing to do!
                    return
            else:
                # Multiple FKs found for the same field, drop them all, and re-create
                for cons in constraints:
                    _schema.debug("Table '%s': dropping duplicate FK constraints: '%s'",
                                  source_table, cons['constraint_name'])
                    self._drop_constraint(cr, source_table, cons['constraint_name'])

        # (re-)create the FK
        self._m2o_add_foreign_key_checked(source_field, dest_model, ondelete)



    def _auto_init(self, cr, context=None):
        """

        Call _field_create and, unless _auto is False:

        - create the corresponding table in database for the model,
        - possibly add the parent columns in database,
        - possibly add the columns 'create_uid', 'create_date', 'write_uid',
          'write_date' in database if _log_access is True (the default),
        - report on database columns no more existing in _columns,
        - remove no more existing not null constraints,
        - alter existing database columns to match _columns,
        - create database tables to match _columns,
        - add database indices to match _columns,
        - save in self._foreign_keys a list a foreign keys to create (see
          _auto_end).

        """
        self._foreign_keys = set()
        raise_on_invalid_object_name(self._name)
        if context is None:
            context = {}
        store_compute = False
        todo_end = []
        update_custom_fields = context.get('update_custom_fields', False)
        self._field_create(cr, context=context)
        create = not self._table_exist(cr)
        if self._auto:

            if create:
                self._create_table(cr)

            cr.commit()
            if self._parent_store:
                if not self._parent_columns_exist(cr):
                    self._create_parent_columns(cr)
                    store_compute = True

            # Create the create_uid, create_date, write_uid, write_date, columns if desired.
            if self._log_access:
                self._add_log_columns(cr)

            self._check_removed_columns(cr, log=False)

            # iterate on the "object columns"
            column_data = self._select_column_data(cr)

            for k, f in self._columns.iteritems():
                if k in MAGIC_COLUMNS:
                    continue
                # Don't update custom (also called manual) fields
                if f.manual and not update_custom_fields:
                    continue

                if isinstance(f, fields.one2many):
                    self._o2m_raise_on_missing_reference(cr, f)

                elif isinstance(f, fields.many2many):
                    self._m2m_raise_or_create_relation(cr, f)

                else:
                    res = column_data.get(k)

                    # The field is not found as-is in database, try if it
                    # exists with an old name.
                    if not res and hasattr(f, 'oldname'):
                        res = column_data.get(f.oldname)
                        if res:
                            cr.execute('ALTER TABLE "%s" RENAME "%s" TO "%s"' % (self._table, f.oldname, k))
                            res['attname'] = k
                            column_data[k] = res
                            _schema.debug("Table '%s': renamed column '%s' to '%s'",
                                self._table, f.oldname, k)

                    # The field already exists in database. Possibly
                    # change its type, rename it, drop it or change its
                    # constraints.
                    if res:
                        f_pg_type = res['typname']
                        f_pg_size = res['size']
                        f_pg_notnull = res['attnotnull']
                        if isinstance(f, fields.function) and not f.store and\
                                not getattr(f, 'nodrop', False):
                            _logger.info('column %s (%s) converted to a function, removed from table %s',
                                         k, f.string, self._table)
                            cr.execute('ALTER TABLE "%s" DROP COLUMN "%s" CASCADE' % (self._table, k))
                            cr.commit()
                            _schema.debug("Table '%s': dropped column '%s' with cascade",
                                self._table, k)
                            f_obj_type = None
                        else:
                            f_obj_type = get_pg_type(f) and get_pg_type(f)[0]

                        if f_obj_type:
                            ok = False
                            casts = [
                                ('text', 'char', pg_varchar(f.size), '::%s' % pg_varchar(f.size)),
                                ('varchar', 'text', 'TEXT', ''),
                                ('int4', 'float', get_pg_type(f)[1], '::'+get_pg_type(f)[1]),
                                ('date', 'datetime', 'TIMESTAMP', '::TIMESTAMP'),
                                ('timestamp', 'date', 'date', '::date'),
                                ('numeric', 'float', get_pg_type(f)[1], '::'+get_pg_type(f)[1]),
                                ('float8', 'float', get_pg_type(f)[1], '::'+get_pg_type(f)[1]),
                            ]
                            if f_pg_type == 'varchar' and f._type == 'char' and f_pg_size and (f.size is None or f_pg_size < f.size):
                                try:
                                    with cr.savepoint():
                                        cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" TYPE %s' % (self._table, k, pg_varchar(f.size)))
                                except psycopg2.NotSupportedError:
                                    # In place alter table cannot be done because a view is depending of this field.
                                    # Do a manual copy. This will drop the view (that will be recreated later)
                                    cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO temp_change_size' % (self._table, k))
                                    cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, pg_varchar(f.size)))
                                    cr.execute('UPDATE "%s" SET "%s"=temp_change_size::%s' % (self._table, k, pg_varchar(f.size)))
                                    cr.execute('ALTER TABLE "%s" DROP COLUMN temp_change_size CASCADE' % (self._table,))
                                cr.commit()
                                _schema.debug("Table '%s': column '%s' (type varchar) changed size from %s to %s",
                                    self._table, k, f_pg_size or 'unlimited', f.size or 'unlimited')
                            for c in casts:
                                if (f_pg_type==c[0]) and (f._type==c[1]):
                                    if f_pg_type != f_obj_type:
                                        ok = True
                                        cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO __temp_type_cast' % (self._table, k))
                                        cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, c[2]))
                                        cr.execute(('UPDATE "%s" SET "%s"= __temp_type_cast'+c[3]) % (self._table, k))
                                        cr.execute('ALTER TABLE "%s" DROP COLUMN  __temp_type_cast CASCADE' % (self._table,))
                                        cr.commit()
                                        _schema.debug("Table '%s': column '%s' changed type from %s to %s",
                                            self._table, k, c[0], c[1])
                                    break

                            if f_pg_type != f_obj_type:
                                if not ok:
                                    i = 0
                                    while True:
                                        newname = k + '_moved' + str(i)
                                        cr.execute("SELECT count(1) FROM pg_class c,pg_attribute a " \
                                            "WHERE c.relname=%s " \
                                            "AND a.attname=%s " \
                                            "AND c.oid=a.attrelid ", (self._table, newname))
                                        if not cr.fetchone()[0]:
                                            break
                                        i += 1
                                    if f_pg_notnull:
                                        cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" DROP NOT NULL' % (self._table, k))
                                    cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % (self._table, k, newname))
                                    cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, get_pg_type(f)[1]))
                                    cr.execute("COMMENT ON COLUMN %s.\"%s\" IS %%s" % (self._table, k), (f.string,))
                                    _schema.debug("Table '%s': column '%s' has changed type (DB=%s, def=%s), data moved to column %s !",
                                        self._table, k, f_pg_type, f._type, newname)

                            # if the field is required and hasn't got a NOT NULL constraint
                            if f.required and f_pg_notnull == 0:
                                # set the field to the default value if any
                                if k in self._defaults:
                                    if callable(self._defaults[k]):
                                        default = self._defaults[k](self, cr, SUPERUSER_ID, context)
                                    else:
                                        default = self._defaults[k]

                                    if default is not None:
                                        ss = self._columns[k]._symbol_set
                                        query = 'UPDATE "%s" SET "%s"=%s WHERE "%s" is NULL' % (self._table, k, ss[0], k)
                                        cr.execute(query, (ss[1](default),))
                                # add the NOT NULL constraint
                                cr.commit()
                                try:
                                    cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" SET NOT NULL' % (self._table, k), log_exceptions=False)
                                    cr.commit()
                                    _schema.debug("Table '%s': column '%s': added NOT NULL constraint",
                                        self._table, k)
                                except Exception:
                                    msg = "Table '%s': unable to set a NOT NULL constraint on column '%s' !\n"\
                                        "If you want to have it, you should update the records and execute manually:\n"\
                                        "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL"
                                    _schema.warning(msg, self._table, k, self._table, k)
                                cr.commit()
                            elif not f.required and f_pg_notnull == 1:
                                cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" DROP NOT NULL' % (self._table, k))
                                cr.commit()
                                _schema.debug("Table '%s': column '%s': dropped NOT NULL constraint",
                                    self._table, k)
                            # Verify index
                            indexname = '%s_%s_index' % (self._table, k)
                            cr.execute("SELECT indexname FROM pg_indexes WHERE indexname = %s and tablename = %s", (indexname, self._table))
                            res2 = cr.dictfetchall()
                            if not res2 and f.select:
                                cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (self._table, k, self._table, k))
                                cr.commit()
                                if f._type == 'text':
                                    # FIXME: for fields.text columns we should try creating GIN indexes instead (seems most suitable for an ERP context)
                                    msg = "Table '%s': Adding (b-tree) index for %s column '%s'."\
                                        "This is probably useless (does not work for fulltext search) and prevents INSERTs of long texts"\
                                        " because there is a length limit for indexable btree values!\n"\
                                        "Use a search view instead if you simply want to make the field searchable."
                                    _schema.warning(msg, self._table, f._type, k)
                            if res2 and not f.select:
                                cr.execute('DROP INDEX "%s_%s_index"' % (self._table, k))
                                cr.commit()
                                msg = "Table '%s': dropping index for column '%s' of type '%s' as it is not required anymore"
                                _schema.debug(msg, self._table, k, f._type)

                            if isinstance(f, fields.many2one) or (isinstance(f, fields.function) and f._type == 'many2one' and f.store):
                                dest_model = self.pool[f._obj]
                                if dest_model._table != 'ir_actions':
                                    self._m2o_fix_foreign_key(cr, self._table, k, dest_model, f.ondelete)

                    # The field doesn't exist in database. Create it if necessary.
                    else:
                        if not isinstance(f, fields.function) or f.store:
                            # add the missing field
                            cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, get_pg_type(f)[1]))
                            cr.execute("COMMENT ON COLUMN %s.\"%s\" IS %%s" % (self._table, k), (f.string,))
                            _schema.debug("Table '%s': added column '%s' with definition=%s",
                                self._table, k, get_pg_type(f)[1])

                            # initialize it
                            if not create and k in self._defaults:
                                if callable(self._defaults[k]):
                                    default = self._defaults[k](self, cr, SUPERUSER_ID, context)
                                else:
                                    default = self._defaults[k]

                                ss = self._columns[k]._symbol_set
                                query = 'UPDATE "%s" SET "%s"=%s' % (self._table, k, ss[0])
                                cr.execute(query, (ss[1](default),))
                                cr.commit()
                                _logger.debug("Table '%s': setting default value of new column %s", self._table, k)

                            # remember the functions to call for the stored fields
                            if isinstance(f, fields.function):
                                order = 10
                                if f.store is not True: # i.e. if f.store is a dict
                                    order = f.store[f.store.keys()[0]][2]
                                todo_end.append((order, self._update_store, (f, k)))

                            # and add constraints if needed
                            if isinstance(f, fields.many2one) or (isinstance(f, fields.function) and f._type == 'many2one' and f.store):
                                if f._obj not in self.pool:
                                    raise except_orm('Programming Error', 'There is no reference available for %s' % (f._obj,))
                                dest_model = self.pool[f._obj]
                                ref = dest_model._table
                                # ir_actions is inherited so foreign key doesn't work on it
                                if ref != 'ir_actions':
                                    self._m2o_add_foreign_key_checked(k, dest_model, f.ondelete)
                            if f.select:
                                cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (self._table, k, self._table, k))
                            if f.required:
                                try:
                                    cr.commit()
                                    cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" SET NOT NULL' % (self._table, k), log_exceptions=False)
                                    _schema.debug("Table '%s': column '%s': added a NOT NULL constraint",
                                        self._table, k)
                                except Exception:
                                    msg = "WARNING: unable to set column %s of table %s not null !\n"\
                                        "Try to re-run: openerp-server --update=module\n"\
                                        "If it doesn't work, update records and execute manually:\n"\
                                        "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL"
                                    _logger.warning(msg, k, self._table, self._table, k)
                            cr.commit()

        else:
            cr.execute("SELECT relname FROM pg_class WHERE relkind IN ('r','v') AND relname=%s", (self._table,))
            create = not bool(cr.fetchone())

        cr.commit()     # start a new transaction

        if self._auto:
            self._add_sql_constraints(cr)

        if create:
            self._execute_sql(cr)

        if store_compute:
            self._parent_store_compute(cr)
            cr.commit()

        return todo_end

    def _auto_end(self, cr, context=None):
        """ Create the foreign keys recorded by _auto_init. """
        for t, k, r, d in self._foreign_keys:
            cr.execute('ALTER TABLE "%s" ADD FOREIGN KEY ("%s") REFERENCES "%s" ON DELETE %s' % (t, k, r, d))
            self._save_constraint(cr, "%s_%s_fkey" % (t, k), 'f')
        cr.commit()
        del self._foreign_keys


    def _table_exist(self, cr):
        cr.execute("SELECT relname FROM pg_class WHERE relkind IN ('r','v') AND relname=%s", (self._table,))
        return cr.rowcount


    def _create_table(self, cr):
        cr.execute('CREATE TABLE "%s" (id SERIAL NOT NULL, PRIMARY KEY(id))' % (self._table,))
        cr.execute(("COMMENT ON TABLE \"%s\" IS %%s" % self._table), (self._description,))
        _schema.debug("Table '%s': created", self._table)


    def _parent_columns_exist(self, cr):
        cr.execute("""SELECT c.relname
            FROM pg_class c, pg_attribute a
            WHERE c.relname=%s AND a.attname=%s AND c.oid=a.attrelid
            """, (self._table, 'parent_left'))
        return cr.rowcount


    def _create_parent_columns(self, cr):
        cr.execute('ALTER TABLE "%s" ADD COLUMN "parent_left" INTEGER' % (self._table,))
        cr.execute('ALTER TABLE "%s" ADD COLUMN "parent_right" INTEGER' % (self._table,))
        if 'parent_left' not in self._columns:
            _logger.error('create a column parent_left on object %s: fields.integer(\'Left Parent\', select=1)',
                          self._table)
            _schema.debug("Table '%s': added column '%s' with definition=%s",
                self._table, 'parent_left', 'INTEGER')
        elif not self._columns['parent_left'].select:
            _logger.error('parent_left column on object %s must be indexed! Add select=1 to the field definition)',
                          self._table)
        if 'parent_right' not in self._columns:
            _logger.error('create a column parent_right on object %s: fields.integer(\'Right Parent\', select=1)',
                          self._table)
            _schema.debug("Table '%s': added column '%s' with definition=%s",
                self._table, 'parent_right', 'INTEGER')
        elif not self._columns['parent_right'].select:
            _logger.error('parent_right column on object %s must be indexed! Add select=1 to the field definition)',
                          self._table)
        if self._columns[self._parent_name].ondelete not in ('cascade', 'restrict'):
            _logger.error("The column %s on object %s must be set as ondelete='cascade' or 'restrict'",
                          self._parent_name, self._name)

        cr.commit()


    def _add_log_columns(self, cr):
        for field, field_def in LOG_ACCESS_COLUMNS.iteritems():
            cr.execute("""
                SELECT c.relname
                  FROM pg_class c, pg_attribute a
                 WHERE c.relname=%s AND a.attname=%s AND c.oid=a.attrelid
                """, (self._table, field))
            if not cr.rowcount:
                cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, field, field_def))
                cr.commit()
                _schema.debug("Table '%s': added column '%s' with definition=%s",
                    self._table, field, field_def)


    def _select_column_data(self, cr):
        # attlen is the number of bytes necessary to represent the type when
        # the type has a fixed size. If the type has a varying size attlen is
        # -1 and atttypmod is the size limit + 4, or -1 if there is no limit.
        cr.execute("SELECT c.relname,a.attname,a.attlen,a.atttypmod,a.attnotnull,a.atthasdef,t.typname,CASE WHEN a.attlen=-1 THEN (CASE WHEN a.atttypmod=-1 THEN 0 ELSE a.atttypmod-4 END) ELSE a.attlen END as size " \
           "FROM pg_class c,pg_attribute a,pg_type t " \
           "WHERE c.relname=%s " \
           "AND c.oid=a.attrelid " \
           "AND a.atttypid=t.oid", (self._table,))
        return dict(map(lambda x: (x['attname'], x),cr.dictfetchall()))


    def _o2m_raise_on_missing_reference(self, cr, f):
        # TODO this check should be a method on fields.one2many.
        if f._obj in self.pool:
            other = self.pool[f._obj]
            # TODO the condition could use fields_get_keys().
            if f._fields_id not in other._columns.keys():
                if f._fields_id not in other._inherit_fields.keys():
                    raise except_orm('Programming Error', "There is no reference field '%s' found for '%s'" % (f._fields_id, f._obj,))

    def _m2m_raise_or_create_relation(self, cr, f):
        m2m_tbl, col1, col2 = f._sql_names(self)
        self._save_relation_table(cr, m2m_tbl)
        cr.execute("SELECT relname FROM pg_class WHERE relkind IN ('r','v') AND relname=%s", (m2m_tbl,))
        if not cr.dictfetchall():
            if f._obj not in self.pool:
                raise except_orm('Programming Error', 'Many2Many destination model does not exist: `%s`' % (f._obj,))
            dest_model = self.pool[f._obj]
            ref = dest_model._table
            cr.execute('CREATE TABLE "%s" ("%s" INTEGER NOT NULL, "%s" INTEGER NOT NULL, UNIQUE("%s","%s"))' % (m2m_tbl, col1, col2, col1, col2))
            # create foreign key references with ondelete=cascade, unless the targets are SQL views
            cr.execute("SELECT relkind FROM pg_class WHERE relkind IN ('v') AND relname=%s", (ref,))
            if not cr.fetchall():
                self._m2o_add_foreign_key_unchecked(m2m_tbl, col2, dest_model, 'cascade')
            cr.execute("SELECT relkind FROM pg_class WHERE relkind IN ('v') AND relname=%s", (self._table,))
            if not cr.fetchall():
                self._m2o_add_foreign_key_unchecked(m2m_tbl, col1, self, 'cascade')

            cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (m2m_tbl, col1, m2m_tbl, col1))
            cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (m2m_tbl, col2, m2m_tbl, col2))
            cr.execute("COMMENT ON TABLE \"%s\" IS 'RELATION BETWEEN %s AND %s'" % (m2m_tbl, self._table, ref))
            cr.commit()
            _schema.debug("Create table '%s': m2m relation between '%s' and '%s'", m2m_tbl, self._table, ref)


    def _add_sql_constraints(self, cr):
        """

        Modify this model's database table constraints so they match the one in
        _sql_constraints.

        """
        def unify_cons_text(txt):
            return txt.lower().replace(', ',',').replace(' (','(')

        for (key, con, _) in self._sql_constraints:
            conname = '%s_%s' % (self._table, key)

            self._save_constraint(cr, conname, 'u')
            cr.execute("SELECT conname, pg_catalog.pg_get_constraintdef(oid, true) as condef FROM pg_constraint where conname=%s", (conname,))
            existing_constraints = cr.dictfetchall()
            sql_actions = {
                'drop': {
                    'execute': False,
                    'query': 'ALTER TABLE "%s" DROP CONSTRAINT "%s"' % (self._table, conname, ),
                    'msg_ok': "Table '%s': dropped constraint '%s'. Reason: its definition changed from '%%s' to '%s'" % (
                        self._table, conname, con),
                    'msg_err': "Table '%s': unable to drop \'%s\' constraint !" % (self._table, con),
                    'order': 1,
                },
                'add': {
                    'execute': False,
                    'query': 'ALTER TABLE "%s" ADD CONSTRAINT "%s" %s' % (self._table, conname, con,),
                    'msg_ok': "Table '%s': added constraint '%s' with definition=%s" % (self._table, conname, con),
                    'msg_err': "Table '%s': unable to add \'%s\' constraint !\n If you want to have it, you should update the records and execute manually:\n%%s" % (
                        self._table, con),
                    'order': 2,
                },
            }

            if not existing_constraints:
                # constraint does not exists:
                sql_actions['add']['execute'] = True
                sql_actions['add']['msg_err'] = sql_actions['add']['msg_err'] % (sql_actions['add']['query'], )
            elif unify_cons_text(con) not in [unify_cons_text(item['condef']) for item in existing_constraints]:
                # constraint exists but its definition has changed:
                sql_actions['drop']['execute'] = True
                sql_actions['drop']['msg_ok'] = sql_actions['drop']['msg_ok'] % (existing_constraints[0]['condef'].lower(), )
                sql_actions['add']['execute'] = True
                sql_actions['add']['msg_err'] = sql_actions['add']['msg_err'] % (sql_actions['add']['query'], )

            # we need to add the constraint:
            sql_actions = [item for item in sql_actions.values()]
            sql_actions.sort(key=lambda x: x['order'])
            for sql_action in [action for action in sql_actions if action['execute']]:
                try:
                    cr.execute(sql_action['query'])
                    cr.commit()
                    _schema.debug(sql_action['msg_ok'])
                except:
                    _schema.warning(sql_action['msg_err'])
                    cr.rollback()


    def _execute_sql(self, cr):
        """ Execute the SQL code from the _sql attribute (if any)."""
        if hasattr(self, "_sql"):
            for line in self._sql.split(';'):
                line2 = line.replace('\n', '').strip()
                if line2:
                    cr.execute(line2)
                    cr.commit()

    #
    # Update objects that uses this one to update their _inherits fields
    #

    def _inherits_reload_src(self):
        """ Recompute the _inherit_fields mapping on each _inherits'd child model."""
        for obj in self.pool.models.values():
            if self._name in obj._inherits:
                obj._inherits_reload()


    def _inherits_reload(self):
        """ Recompute the _inherit_fields mapping.

        This will also call itself on each inherits'd child model.

        """
        res = {}
        for table in self._inherits:
            other = self.pool[table]
            for col in other._columns.keys():
                res[col] = (table, self._inherits[table], other._columns[col], table)
            for col in other._inherit_fields.keys():
                res[col] = (table, self._inherits[table], other._inherit_fields[col][2], other._inherit_fields[col][3])
        self._inherit_fields = res
        self._all_columns = self._get_column_infos()
        self._inherits_reload_src()


    def _get_column_infos(self):
        """Returns a dict mapping all fields names (direct fields and
           inherited field via _inherits) to a ``column_info`` struct
           giving detailed columns """
        result = {}
        for k, (parent, m2o, col, original_parent) in self._inherit_fields.iteritems():
            result[k] = fields.column_info(k, col, parent, m2o, original_parent)
        for k, col in self._columns.iteritems():
            result[k] = fields.column_info(k, col)
        return result


    def _inherits_check(self):
        for table, field_name in self._inherits.items():
            if field_name not in self._columns:
                _logger.info('Missing many2one field definition for _inherits reference "%s" in "%s", using default one.', field_name, self._name)
                self._columns[field_name] = fields.many2one(table, string="Automatically created field to link to parent %s" % table,
                                                             required=True, ondelete="cascade")
            elif not self._columns[field_name].required or self._columns[field_name].ondelete.lower() not in ("cascade", "restrict"):
                _logger.warning('Field definition for _inherits reference "%s" in "%s" must be marked as "required" with ondelete="cascade" or "restrict", forcing it to required + cascade.', field_name, self._name)
                self._columns[field_name].required = True
                self._columns[field_name].ondelete = "cascade"


    def fields_get(self, cr, user, allfields=None, context=None, write_access=True):
        """ Return the definition of each field.

        The returned value is a dictionary (indiced by field name) of
        dictionaries. The _inherits'd fields are included. The string, help,
        and selection (if present) attributes are translated.

        :param cr: database cursor
        :param user: current user id
        :param allfields: list of fields
        :param context: context arguments, like lang, time zone
        :return: dictionary of field dictionaries, each one describing a field of the business object
        :raise AccessError: * if user has no create/write rights on the requested object

        """
        if context is None:
            context = {}

        write_access = self.check_access_rights(cr, user, 'write', raise_exception=False) \
            or self.check_access_rights(cr, user, 'create', raise_exception=False)

        res = {}

        translation_obj = self.pool.get('ir.translation')
        for parent in self._inherits:
            res.update(self.pool[parent].fields_get(cr, user, allfields, context))

        for f, field in self._columns.iteritems():
            if (allfields and f not in allfields) or \
                (field.groups and not self.user_has_groups(cr, user, groups=field.groups, context=context)):
                continue

            res[f] = fields.field_to_dict(self, cr, user, field, context=context)

            if not write_access:
                res[f]['readonly'] = True
                res[f]['states'] = {}

            if 'lang' in context:
                if 'string' in res[f]:
                    res_trans = translation_obj._get_source(cr, user, self._name + ',' + f, 'field', context['lang'])
                    if res_trans:
                        res[f]['string'] = res_trans
                if 'help' in res[f]:
                    help_trans = translation_obj._get_source(cr, user, self._name + ',' + f, 'help', context['lang'])
                    if help_trans:
                        res[f]['help'] = help_trans

        return res

    def get_empty_list_help(self, cr, user, help, context=None):
        """ Generic method giving the help message displayed when having
            no result to display in a list or kanban view. By default it returns
            the help given in parameter that is generally the help message
            defined in the action.
        """
        return help

    def check_field_access_rights(self, cr, user, operation, fields, context=None):
        """
        Check the user access rights on the given fields. This raises Access
        Denied if the user does not have the rights. Otherwise it returns the
        fields (as is if the fields is not falsy, or the readable/writable
        fields if fields is falsy).
        """
        def p(field_name):
            """Predicate to test if the user has access to the given field name."""
            # Ignore requested field if it doesn't exist. This is ugly but
            # it seems to happen at least with 'name_alias' on res.partner.
            if field_name not in self._all_columns:
                return True
            field = self._all_columns[field_name].column
            if user != SUPERUSER_ID and field.groups:
                return self.user_has_groups(cr, user, groups=field.groups, context=context)
            else:
                return True
        if not fields:
            fields = filter(p, self._all_columns.keys())
        else:
            filtered_fields = filter(lambda a: not p(a), fields)
            if filtered_fields:
                _logger.warning('Access Denied by ACLs for operation: %s, uid: %s, model: %s, fields: %s', operation, user, self._name, ', '.join(filtered_fields))
                raise except_orm(
                    _('Access Denied'),
                    _('The requested operation cannot be completed due to security restrictions. '
                    'Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % \
                    (self._description, operation))
        return fields

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        """ Read records with given ids with the given fields

        :param cr: database cursor
        :param user: current user id
        :param ids: id or list of the ids of the records to read
        :param fields: optional list of field names to return (default: all fields would be returned)
        :type fields: list (example ['field_name_1', ...])
        :param context: optional context dictionary - it may contains keys for specifying certain options
                        like ``context_lang``, ``context_tz`` to alter the results of the call.
                        A special ``bin_size`` boolean flag may also be passed in the context to request the
                        value of all fields.binary columns to be returned as the size of the binary instead of its
                        contents. This can also be selectively overriden by passing a field-specific flag
                        in the form ``bin_size_XXX: True/False`` where ``XXX`` is the name of the field.
                        Note: The ``bin_size_XXX`` form is new in OpenERP v6.0.
        :return: list of dictionaries((dictionary per record asked)) with requested field values
        :rtype: [{‘name_of_the_field’: value, ...}, ...]
        :raise AccessError: * if user has no read rights on the requested object
                            * if user tries to bypass access rules for read on the requested object

        """

        self.check_access_rights(cr, user, 'read')
        fields = self.check_field_access_rights(cr, user, 'read', fields)
        if isinstance(ids, (int, long)):
            select = [ids]
        else:
            select = ids
        select = map(lambda x: isinstance(x, dict) and x['id'] or x, select)
        result = self._read_flat(cr, user, select, fields, context, load)

        if isinstance(ids, (int, long)):
            return result and result[0] or False
        return result

    def _read_flat(self, cr, user, ids, fields_to_read, context=None, load='_classic_read'):
        if not context:
            context = {}
        if not ids:
            return []
        if fields_to_read is None:
            fields_to_read = self._columns.keys()
        else:
            fields_to_read = list(set(fields_to_read))

        # all inherited fields + all non inherited fields for which the attribute whose name is in load is True
        fields_pre = [f for f in fields_to_read if
                           f == self.CONCURRENCY_CHECK_FIELD
                        or (f in self._columns and getattr(self._columns[f], '_classic_write'))
                     ] + self._inherits.values()

        res = []
        if len(fields_pre):
            def convert_field(f):
                f_qual = '%s."%s"' % (self._table, f) # need fully-qualified references in case len(tables) > 1
                if f in ('create_date', 'write_date'):
                    return "date_trunc('second', %s) as %s" % (f_qual, f)
                if f == self.CONCURRENCY_CHECK_FIELD:
                    if self._log_access:
                        return "COALESCE(%s.write_date, %s.create_date, (now() at time zone 'UTC'))::timestamp AS %s" % (self._table, self._table, f,)
                    return "(now() at time zone 'UTC')::timestamp AS %s" % (f,)
                if isinstance(self._columns[f], fields.binary) and context.get('bin_size', False):
                    return 'length(%s) as "%s"' % (f_qual, f)
                return f_qual

            # Construct a clause for the security rules.
            # 'tables' hold the list of tables necessary for the SELECT including the ir.rule clauses,
            # or will at least contain self._table.
            rule_clause, rule_params, tables = self.pool.get('ir.rule').domain_get(cr, user, self._name, 'read', context=context)

            fields_pre2 = map(convert_field, fields_pre)
            order_by = self._parent_order or self._order
            select_fields = ','.join(fields_pre2 + ['%s.id' % self._table])
            query = 'SELECT %s FROM %s WHERE %s.id IN %%s' % (select_fields, ','.join(tables), self._table)
            if rule_clause:
                query += " AND " + (' OR '.join(rule_clause))
            query += " ORDER BY " + order_by
            for sub_ids in cr.split_for_in_conditions(ids):
                cr.execute(query, [tuple(sub_ids)] + rule_params)
                results = cr.dictfetchall()
                result_ids = [x['id'] for x in results]
                self._check_record_rules_result_count(cr, user, sub_ids, result_ids, 'read', context=context)
                res.extend(results)
        else:
            self.check_access_rule(cr, user, ids, 'read', context=context)
            res = map(lambda x: {'id': x}, ids)

        if context.get('lang'):
            for f in fields_pre:
                if f == self.CONCURRENCY_CHECK_FIELD:
                    continue
                if self._columns[f].translate:
                    ids = [x['id'] for x in res]
                    #TODO: optimize out of this loop
                    res_trans = self.pool.get('ir.translation')._get_ids(cr, user, self._name+','+f, 'model', context['lang'], ids)
                    for r in res:
                        r[f] = res_trans.get(r['id'], False) or r[f]

        for table in self._inherits:
            col = self._inherits[table]
            cols = [x for x in intersect(self._inherit_fields.keys(), fields_to_read) if x not in self._columns.keys()]
            if not cols:
                continue
            res2 = self.pool[table].read(cr, user, [x[col] for x in res], cols, context, load)

            res3 = {}
            for r in res2:
                res3[r['id']] = r
                del r['id']

            for record in res:
                if not record[col]: # if the record is deleted from _inherits table?
                    continue
                record.update(res3[record[col]])
                if col not in fields_to_read:
                    del record[col]

        # all fields which need to be post-processed by a simple function (symbol_get)
        fields_post = filter(lambda x: x in self._columns and self._columns[x]._symbol_get, fields_to_read)
        if fields_post:
            for r in res:
                for f in fields_post:
                    r[f] = self._columns[f]._symbol_get(r[f])
        ids = [x['id'] for x in res]

        # all non inherited fields for which the attribute whose name is in load is False
        fields_post = filter(lambda x: x in self._columns and not getattr(self._columns[x], load), fields_to_read)

        # Compute POST fields
        todo = {}
        for f in fields_post:
            todo.setdefault(self._columns[f]._multi, [])
            todo[self._columns[f]._multi].append(f)
        for key, val in todo.items():
            if key:
                res2 = self._columns[val[0]].get(cr, self, ids, val, user, context=context, values=res)
                assert res2 is not None, \
                    'The function field "%s" on the "%s" model returned None\n' \
                    '(a dictionary was expected).' % (val[0], self._name)
                for pos in val:
                    for record in res:
                        if isinstance(res2[record['id']], str): res2[record['id']] = eval(res2[record['id']]) #TOCHECK : why got string instend of dict in python2.6
                        multi_fields = res2.get(record['id'],{})
                        if multi_fields:
                            record[pos] = multi_fields.get(pos,[])
            else:
                for f in val:
                    res2 = self._columns[f].get(cr, self, ids, f, user, context=context, values=res)
                    for record in res:
                        if res2:
                            record[f] = res2[record['id']]
                        else:
                            record[f] = []

        # Warn about deprecated fields now that fields_pre and fields_post are computed
        # Explicitly use list() because we may receive tuples
        for f in list(fields_pre) + list(fields_post):
            field_column = self._all_columns.get(f) and self._all_columns.get(f).column
            if field_column and field_column.deprecated:
                _logger.warning('Field %s.%s is deprecated: %s', self._name, f, field_column.deprecated)

        readonly = None
        for vals in res:
            for field in vals.copy():
                fobj = None
                if field in self._columns:
                    fobj = self._columns[field]

                if fobj:
                    groups = fobj.read
                    if groups:
                        edit = False
                        for group in groups:
                            module = group.split(".")[0]
                            grp = group.split(".")[1]
                            cr.execute("select count(*) from res_groups_users_rel where gid IN (select res_id from ir_model_data where name=%s and module=%s and model=%s) and uid=%s",  \
                                       (grp, module, 'res.groups', user))
                            readonly = cr.fetchall()
                            if readonly[0][0] >= 1:
                                edit = True
                                break
                            elif readonly[0][0] == 0:
                                edit = False
                            else:
                                edit = False

                        if not edit:
                            if type(vals[field]) == type([]):
                                vals[field] = []
                            elif type(vals[field]) == type(0.0):
                                vals[field] = 0
                            elif type(vals[field]) == type(''):
                                vals[field] = '=No Permission='
                            else:
                                vals[field] = False

                if vals[field] is None:
                    vals[field] = False

        return res

    # TODO check READ access
    def perm_read(self, cr, user, ids, context=None, details=True):
        """
        Returns some metadata about the given records.

        :param details: if True, \*_uid fields are replaced with the name of the user
        :return: list of ownership dictionaries for each requested record
        :rtype: list of dictionaries with the following keys:

                    * id: object id
                    * create_uid: user who created the record
                    * create_date: date when the record was created
                    * write_uid: last user who changed the record
                    * write_date: date of the last change to the record
                    * xmlid: XML ID to use to refer to this record (if there is one), in format ``module.name``
        """
        if not context:
            context = {}
        if not ids:
            return []
        fields = ''
        uniq = isinstance(ids, (int, long))
        if uniq:
            ids = [ids]
        fields = ['id']
        if self._log_access:
            fields += ['create_uid', 'create_date', 'write_uid', 'write_date']
        quoted_table = '"%s"' % self._table
        fields_str = ",".join('%s.%s'%(quoted_table, field) for field in fields)
        query = '''SELECT %s, __imd.module, __imd.name
                   FROM %s LEFT JOIN ir_model_data __imd
                       ON (__imd.model = %%s and __imd.res_id = %s.id)
                   WHERE %s.id IN %%s''' % (fields_str, quoted_table, quoted_table, quoted_table)
        cr.execute(query, (self._name, tuple(ids)))
        res = cr.dictfetchall()
        for r in res:
            for key in r:
                r[key] = r[key] or False
                if details and key in ('write_uid', 'create_uid') and r[key]:
                    try:
                        r[key] = self.pool.get('res.users').name_get(cr, user, [r[key]])[0]
                    except Exception:
                        pass # Leave the numeric uid there
            r['xmlid'] = ("%(module)s.%(name)s" % r) if r['name'] else False
            del r['name'], r['module']
        if uniq:
            return res[ids[0]]
        return res

    def _check_concurrency(self, cr, ids, context):
        if not context:
            return
        if not (context.get(self.CONCURRENCY_CHECK_FIELD) and self._log_access):
            return
        check_clause = "(id = %s AND %s < COALESCE(write_date, create_date, (now() at time zone 'UTC'))::timestamp)"
        for sub_ids in cr.split_for_in_conditions(ids):
            ids_to_check = []
            for id in sub_ids:
                id_ref = "%s,%s" % (self._name, id)
                update_date = context[self.CONCURRENCY_CHECK_FIELD].pop(id_ref, None)
                if update_date:
                    ids_to_check.extend([id, update_date])
            if not ids_to_check:
                continue
            cr.execute("SELECT id FROM %s WHERE %s" % (self._table, " OR ".join([check_clause]*(len(ids_to_check)/2))), tuple(ids_to_check))
            res = cr.fetchone()
            if res:
                # mention the first one only to keep the error message readable
                raise except_orm('ConcurrencyException', _('A document was modified since you last viewed it (%s:%d)') % (self._description, res[0]))

    def _check_record_rules_result_count(self, cr, uid, ids, result_ids, operation, context=None):
        """Verify the returned rows after applying record rules matches
           the length of `ids`, and raise an appropriate exception if it does not.
        """
        ids, result_ids = set(ids), set(result_ids)
        missing_ids = ids - result_ids
        if missing_ids:
            # Attempt to distinguish record rule restriction vs deleted records,
            # to provide a more specific error message - check if the missinf
            cr.execute('SELECT id FROM ' + self._table + ' WHERE id IN %s', (tuple(missing_ids),))
            forbidden_ids = [x[0] for x in cr.fetchall()]
            if forbidden_ids:
                # the missing ids are (at least partially) hidden by access rules
                if uid == SUPERUSER_ID:
                    return
                _logger.warning('Access Denied by record rules for operation: %s on record ids: %r, uid: %s, model: %s', operation, forbidden_ids, uid, self._name)
                raise except_orm(_('Access Denied'),
                                 _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % \
                                    (self._description, operation))
            else:
                # If we get here, the missing_ids are not in the database
                if operation in ('read','unlink'):
                    # No need to warn about deleting an already deleted record.
                    # And no error when reading a record that was deleted, to prevent spurious
                    # errors for non-transactional search/read sequences coming from clients
                    return
                _logger.warning('Failed operation on deleted record(s): %s, uid: %s, model: %s', operation, uid, self._name)
                raise except_orm(_('Missing document(s)'),
                                 _('One of the documents you are trying to access has been deleted, please try again after refreshing.'))


    def check_access_rights(self, cr, uid, operation, raise_exception=True): # no context on purpose.
        """Verifies that the operation given by ``operation`` is allowed for the user
           according to the access rights."""
        return self.pool.get('ir.model.access').check(cr, uid, self._name, operation, raise_exception)

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        """Verifies that the operation given by ``operation`` is allowed for the user
           according to ir.rules.

           :param operation: one of ``write``, ``unlink``
           :raise except_orm: * if current ir.rules do not permit this operation.
           :return: None if the operation is allowed
        """
        if uid == SUPERUSER_ID:
            return

        if self.is_transient():
            # Only one single implicit access rule for transient models: owner only!
            # This is ok to hardcode because we assert that TransientModels always
            # have log_access enabled so that the create_uid column is always there.
            # And even with _inherits, these fields are always present in the local
            # table too, so no need for JOINs.
            cr.execute("""SELECT distinct create_uid
                          FROM %s
                          WHERE id IN %%s""" % self._table, (tuple(ids),))
            uids = [x[0] for x in cr.fetchall()]
            if len(uids) != 1 or uids[0] != uid:
                raise except_orm(_('Access Denied'),
                                 _('For this kind of document, you may only access records you created yourself.\n\n(Document type: %s)') % (self._description,))
        else:
            where_clause, where_params, tables = self.pool.get('ir.rule').domain_get(cr, uid, self._name, operation, context=context)
            if where_clause:
                where_clause = ' and ' + ' and '.join(where_clause)
                for sub_ids in cr.split_for_in_conditions(ids):
                    cr.execute('SELECT ' + self._table + '.id FROM ' + ','.join(tables) +
                               ' WHERE ' + self._table + '.id IN %s' + where_clause,
                               [sub_ids] + where_params)
                    returned_ids = [x['id'] for x in cr.dictfetchall()]
                    self._check_record_rules_result_count(cr, uid, sub_ids, returned_ids, operation, context=context)

    def create_workflow(self, cr, uid, ids, context=None):
        """Create a workflow instance for each given record IDs."""
        from openerp import workflow
        for res_id in ids:
            workflow.trg_create(uid, self._name, res_id, cr)
        return True

    def delete_workflow(self, cr, uid, ids, context=None):
        """Delete the workflow instances bound to the given record IDs."""
        from openerp import workflow
        for res_id in ids:
            workflow.trg_delete(uid, self._name, res_id, cr)
        return True

    def step_workflow(self, cr, uid, ids, context=None):
        """Reevaluate the workflow instances of the given record IDs."""
        from openerp import workflow
        for res_id in ids:
            workflow.trg_write(uid, self._name, res_id, cr)
        return True

    def signal_workflow(self, cr, uid, ids, signal, context=None):
        """Send given workflow signal and return a dict mapping ids to workflow results"""
        from openerp import workflow
        result = {}
        for res_id in ids:
            result[res_id] = workflow.trg_validate(uid, self._name, res_id, signal, cr)
        return result

    def redirect_workflow(self, cr, uid, old_new_ids, context=None):
        """ Rebind the workflow instance bound to the given 'old' record IDs to
            the given 'new' IDs. (``old_new_ids`` is a list of pairs ``(old, new)``.
        """
        from openerp import workflow
        for old_id, new_id in old_new_ids:
            workflow.trg_redirect(uid, self._name, old_id, new_id, cr)
        return True

    def unlink(self, cr, uid, ids, context=None):
        """
        Delete records with given ids

        :param cr: database cursor
        :param uid: current user id
        :param ids: id or list of ids
        :param context: (optional) context arguments, like lang, time zone
        :return: True
        :raise AccessError: * if user has no unlink rights on the requested object
                            * if user tries to bypass access rules for unlink on the requested object
        :raise UserError: if the record is default property for other records

        """
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]

        result_store = self._store_get_values(cr, uid, ids, self._all_columns.keys(), context)

        self._check_concurrency(cr, ids, context)

        self.check_access_rights(cr, uid, 'unlink')

        ir_property = self.pool.get('ir.property')

        # Check if the records are used as default properties.
        domain = [('res_id', '=', False),
                  ('value_reference', 'in', ['%s,%s' % (self._name, i) for i in ids]),
                 ]
        if ir_property.search(cr, uid, domain, context=context):
            raise except_orm(_('Error'), _('Unable to delete this document because it is used as a default property'))

        # Delete the records' properties.
        property_ids = ir_property.search(cr, uid, [('res_id', 'in', ['%s,%s' % (self._name, i) for i in ids])], context=context)
        ir_property.unlink(cr, uid, property_ids, context=context)

        self.delete_workflow(cr, uid, ids, context=context)

        self.check_access_rule(cr, uid, ids, 'unlink', context=context)
        pool_model_data = self.pool.get('ir.model.data')
        ir_values_obj = self.pool.get('ir.values')
        for sub_ids in cr.split_for_in_conditions(ids):
            cr.execute('delete from ' + self._table + ' ' \
                       'where id IN %s', (sub_ids,))

            # Removing the ir_model_data reference if the record being deleted is a record created by xml/csv file,
            # as these are not connected with real database foreign keys, and would be dangling references.
            # Note: following steps performed as admin to avoid access rights restrictions, and with no context
            #       to avoid possible side-effects during admin calls.
            # Step 1. Calling unlink of ir_model_data only for the affected IDS
            reference_ids = pool_model_data.search(cr, SUPERUSER_ID, [('res_id','in',list(sub_ids)),('model','=',self._name)])
            # Step 2. Marching towards the real deletion of referenced records
            if reference_ids:
                pool_model_data.unlink(cr, SUPERUSER_ID, reference_ids)

            # For the same reason, removing the record relevant to ir_values
            ir_value_ids = ir_values_obj.search(cr, uid,
                    ['|',('value','in',['%s,%s' % (self._name, sid) for sid in sub_ids]),'&',('res_id','in',list(sub_ids)),('model','=',self._name)],
                    context=context)
            if ir_value_ids:
                ir_values_obj.unlink(cr, uid, ir_value_ids, context=context)

        for order, obj_name, store_ids, fields in result_store:
            if obj_name == self._name:
                effective_store_ids = list(set(store_ids) - set(ids))
            else:
                effective_store_ids = store_ids
            if effective_store_ids:
                obj = self.pool[obj_name]
                cr.execute('select id from '+obj._table+' where id IN %s', (tuple(effective_store_ids),))
                rids = map(lambda x: x[0], cr.fetchall())
                if rids:
                    obj._store_set_values(cr, uid, rids, fields, context)

        return True

    #
    # TODO: Validate
    #
    def write(self, cr, user, ids, vals, context=None):
        """
        Update records with given ids with the given field values

        :param cr: database cursor
        :param user: current user id
        :type user: integer
        :param ids: object id or list of object ids to update according to **vals**
        :param vals: field values to update, e.g {'field_name': new_field_value, ...}
        :type vals: dictionary
        :param context: (optional) context arguments, e.g. {'lang': 'en_us', 'tz': 'UTC', ...}
        :type context: dictionary
        :return: True
        :raise AccessError: * if user has no write rights on the requested object
                            * if user tries to bypass access rules for write on the requested object
        :raise ValidateError: if user tries to enter invalid value for a field that is not in selection
        :raise UserError: if a loop would be created in a hierarchy of objects a result of the operation (such as setting an object as its own parent)

        **Note**: The type of field values to pass in ``vals`` for relationship fields is specific:

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

            + For a many2one field, simply use the ID of target record, which must already exist, or ``False`` to remove the link.
            + For a reference field, use a string with the model name, a comma, and the target object id (example: ``'product.product, 5'``)

        """
        readonly = None
        self.check_field_access_rights(cr, user, 'write', vals.keys())
        for field in vals.copy():
            fobj = None
            if field in self._columns:
                fobj = self._columns[field]
            elif field in self._inherit_fields:
                fobj = self._inherit_fields[field][2]
            if not fobj:
                continue
            groups = fobj.write

            if groups:
                edit = False
                for group in groups:
                    module = group.split(".")[0]
                    grp = group.split(".")[1]
                    cr.execute("select count(*) from res_groups_users_rel where gid IN (select res_id from ir_model_data where name=%s and module=%s and model=%s) and uid=%s", \
                               (grp, module, 'res.groups', user))
                    readonly = cr.fetchall()
                    if readonly[0][0] >= 1:
                        edit = True
                        break

                if not edit:
                    vals.pop(field)

        if not context:
            context = {}
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]

        self._check_concurrency(cr, ids, context)
        self.check_access_rights(cr, user, 'write')

        result = self._store_get_values(cr, user, ids, vals.keys(), context) or []

        # No direct update of parent_left/right
        vals.pop('parent_left', None)
        vals.pop('parent_right', None)

        parents_changed = []
        parent_order = self._parent_order or self._order
        if self._parent_store and (self._parent_name in vals):
            # The parent_left/right computation may take up to
            # 5 seconds. No need to recompute the values if the
            # parent is the same.
            # Note: to respect parent_order, nodes must be processed in
            # order, so ``parents_changed`` must be ordered properly.
            parent_val = vals[self._parent_name]
            if parent_val:
                query = "SELECT id FROM %s WHERE id IN %%s AND (%s != %%s OR %s IS NULL) ORDER BY %s" % \
                                (self._table, self._parent_name, self._parent_name, parent_order)
                cr.execute(query, (tuple(ids), parent_val))
            else:
                query = "SELECT id FROM %s WHERE id IN %%s AND (%s IS NOT NULL) ORDER BY %s" % \
                                (self._table, self._parent_name, parent_order)
                cr.execute(query, (tuple(ids),))
            parents_changed = map(operator.itemgetter(0), cr.fetchall())

        upd0 = []
        upd1 = []
        upd_todo = []
        updend = []
        direct = []
        totranslate = context.get('lang', False) and (context['lang'] != 'en_US')
        for field in vals:
            field_column = self._all_columns.get(field) and self._all_columns.get(field).column
            if field_column and field_column.deprecated:
                _logger.warning('Field %s.%s is deprecated: %s', self._name, field, field_column.deprecated)
            if field in self._columns:
                if self._columns[field]._classic_write and not (hasattr(self._columns[field], '_fnct_inv')):
                    if (not totranslate) or not self._columns[field].translate:
                        upd0.append('"'+field+'"='+self._columns[field]._symbol_set[0])
                        upd1.append(self._columns[field]._symbol_set[1](vals[field]))
                    direct.append(field)
                else:
                    upd_todo.append(field)
            else:
                updend.append(field)
            if field in self._columns \
                    and hasattr(self._columns[field], 'selection') \
                    and vals[field]:
                self._check_selection_field_value(cr, user, field, vals[field], context=context)

        if self._log_access:
            upd0.append('write_uid=%s')
            upd0.append("write_date=(now() at time zone 'UTC')")
            upd1.append(user)

        if len(upd0):
            self.check_access_rule(cr, user, ids, 'write', context=context)
            for sub_ids in cr.split_for_in_conditions(ids):
                cr.execute('update ' + self._table + ' set ' + ','.join(upd0) + ' ' \
                           'where id IN %s', upd1 + [sub_ids])
                if cr.rowcount != len(sub_ids):
                    raise except_orm(_('AccessError'),
                                     _('One of the records you are trying to modify has already been deleted (Document type: %s).') % self._description)

            if totranslate:
                # TODO: optimize
                for f in direct:
                    if self._columns[f].translate:
                        src_trans = self.pool[self._name].read(cr, user, ids, [f])[0][f]
                        if not src_trans:
                            src_trans = vals[f]
                            # Inserting value to DB
                            context_wo_lang = dict(context, lang=None)
                            self.write(cr, user, ids, {f: vals[f]}, context=context_wo_lang)
                        self.pool.get('ir.translation')._set_ids(cr, user, self._name+','+f, 'model', context['lang'], ids, vals[f], src_trans)


        # call the 'set' method of fields which are not classic_write
        upd_todo.sort(lambda x, y: self._columns[x].priority-self._columns[y].priority)

        # default element in context must be removed when call a one2many or many2many
        rel_context = context.copy()
        for c in context.items():
            if c[0].startswith('default_'):
                del rel_context[c[0]]

        for field in upd_todo:
            for id in ids:
                result += self._columns[field].set(cr, self, id, field, vals[field], user, context=rel_context) or []

        unknown_fields = updend[:]
        for table in self._inherits:
            col = self._inherits[table]
            nids = []
            for sub_ids in cr.split_for_in_conditions(ids):
                cr.execute('select distinct "'+col+'" from "'+self._table+'" ' \
                           'where id IN %s', (sub_ids,))
                nids.extend([x[0] for x in cr.fetchall()])

            v = {}
            for val in updend:
                if self._inherit_fields[val][0] == table:
                    v[val] = vals[val]
                    unknown_fields.remove(val)
            if v:
                self.pool[table].write(cr, user, nids, v, context)

        if unknown_fields:
            _logger.warning(
                'No such field(s) in model %s: %s.',
                self._name, ', '.join(unknown_fields))
        self._validate(cr, user, ids, context)

        # TODO: use _order to set dest at the right position and not first node of parent
        # We can't defer parent_store computation because the stored function
        # fields that are computer may refer (directly or indirectly) to
        # parent_left/right (via a child_of domain)
        if parents_changed:
            if self.pool._init:
                self.pool._init_parent[self._name] = True
            else:
                order = self._parent_order or self._order
                parent_val = vals[self._parent_name]
                if parent_val:
                    clause, params = '%s=%%s' % (self._parent_name,), (parent_val,)
                else:
                    clause, params = '%s IS NULL' % (self._parent_name,), ()

                for id in parents_changed:
                    cr.execute('SELECT parent_left, parent_right FROM %s WHERE id=%%s' % (self._table,), (id,))
                    pleft, pright = cr.fetchone()
                    distance = pright - pleft + 1

                    # Positions of current siblings, to locate proper insertion point;
                    # this can _not_ be fetched outside the loop, as it needs to be refreshed
                    # after each update, in case several nodes are sequentially inserted one
                    # next to the other (i.e computed incrementally)
                    cr.execute('SELECT parent_right, id FROM %s WHERE %s ORDER BY %s' % (self._table, clause, parent_order), params)
                    parents = cr.fetchall()

                    # Find Position of the element
                    position = None
                    for (parent_pright, parent_id) in parents:
                        if parent_id == id:
                            break
                        position = parent_pright and parent_pright + 1 or 1

                    # It's the first node of the parent
                    if not position:
                        if not parent_val:
                            position = 1
                        else:
                            cr.execute('select parent_left from '+self._table+' where id=%s', (parent_val,))
                            position = cr.fetchone()[0] + 1

                    if pleft < position <= pright:
                        raise except_orm(_('UserError'), _('Recursivity Detected.'))

                    if pleft < position:
                        cr.execute('update '+self._table+' set parent_left=parent_left+%s where parent_left>=%s', (distance, position))
                        cr.execute('update '+self._table+' set parent_right=parent_right+%s where parent_right>=%s', (distance, position))
                        cr.execute('update '+self._table+' set parent_left=parent_left+%s, parent_right=parent_right+%s where parent_left>=%s and parent_left<%s', (position-pleft, position-pleft, pleft, pright))
                    else:
                        cr.execute('update '+self._table+' set parent_left=parent_left+%s where parent_left>=%s', (distance, position))
                        cr.execute('update '+self._table+' set parent_right=parent_right+%s where parent_right>=%s', (distance, position))
                        cr.execute('update '+self._table+' set parent_left=parent_left-%s, parent_right=parent_right-%s where parent_left>=%s and parent_left<%s', (pleft-position+distance, pleft-position+distance, pleft+distance, pright+distance))

        result += self._store_get_values(cr, user, ids, vals.keys(), context)
        result.sort()

        done = {}
        for order, model_name, ids_to_update, fields_to_recompute in result:
            key = (model_name, tuple(fields_to_recompute))
            done.setdefault(key, {})
            # avoid to do several times the same computation
            todo = []
            for id in ids_to_update:
                if id not in done[key]:
                    done[key][id] = True
                    todo.append(id)
            self.pool[model_name]._store_set_values(cr, user, todo, fields_to_recompute, context)

        self.step_workflow(cr, user, ids, context=context)
        return True

    #
    # TODO: Should set perm to user.xxx
    #
    def create(self, cr, user, vals, context=None):
        """
        Create a new record for the model.

        The values for the new record are initialized using the ``vals``
        argument, and if necessary the result of ``default_get()``.

        :param cr: database cursor
        :param user: current user id
        :type user: integer
        :param vals: field values for new record, e.g {'field_name': field_value, ...}
        :type vals: dictionary
        :param context: optional context arguments, e.g. {'lang': 'en_us', 'tz': 'UTC', ...}
        :type context: dictionary
        :return: id of new record created
        :raise AccessError: * if user has no create rights on the requested object
                            * if user tries to bypass access rules for create on the requested object
        :raise ValidateError: if user tries to enter invalid value for a field that is not in selection
        :raise UserError: if a loop would be created in a hierarchy of objects a result of the operation (such as setting an object as its own parent)

        **Note**: The type of field values to pass in ``vals`` for relationship fields is specific.
        Please see the description of the :py:meth:`~osv.osv.osv.write` method for details about the possible values and how
        to specify them.

        """
        if not context:
            context = {}

        if self.is_transient():
            self._transient_vacuum(cr, user)

        self.check_access_rights(cr, user, 'create')

        if self._log_access:
            for f in LOG_ACCESS_COLUMNS:
                if vals.pop(f, None) is not None:
                    _logger.warning(
                        'Field `%s` is not allowed when creating the model `%s`.',
                        f, self._name)
        vals = self._add_missing_default_values(cr, user, vals, context)

        tocreate = {}
        for v in self._inherits:
            if self._inherits[v] not in vals:
                tocreate[v] = {}
            else:
                tocreate[v] = {'id': vals[self._inherits[v]]}

        columns = [
            # columns will contain a list of field defined as a tuple
            # tuple(field_name, format_string, field_value)
            # the tuple will be used by the string formatting for the INSERT
            # statement.
            ('id', "nextval('%s')" % self._sequence),
        ]

        upd_todo = []
        unknown_fields = []
        for v in vals.keys():
            if v in self._inherit_fields and v not in self._columns:
                (table, col, col_detail, original_parent) = self._inherit_fields[v]
                tocreate[table][v] = vals[v]
                del vals[v]
            else:
                if (v not in self._inherit_fields) and (v not in self._columns):
                    del vals[v]
                    unknown_fields.append(v)
        if unknown_fields:
            _logger.warning(
                'No such field(s) in model %s: %s.',
                self._name, ', '.join(unknown_fields))

        if not self._sequence:
            raise except_orm(
                _('UserError'),
                _('You cannot perform this operation. New Record Creation is not allowed for this object as this object is for reporting purpose.')
            )

        for table in tocreate:
            if self._inherits[table] in vals:
                del vals[self._inherits[table]]

            record_id = tocreate[table].pop('id', None)

            # When linking/creating parent records, force context without 'no_store_function' key that
            # defers stored functions computing, as these won't be computed in batch at the end of create().
            parent_context = dict(context)
            parent_context.pop('no_store_function', None)

            if record_id is None or not record_id:
                record_id = self.pool[table].create(cr, user, tocreate[table], context=parent_context)
            else:
                self.pool[table].write(cr, user, [record_id], tocreate[table], context=parent_context)

            columns.append((self._inherits[table], '%s', record_id))

        #Start : Set bool fields to be False if they are not touched(to make search more powerful)
        bool_fields = [x for x in self._columns.keys() if self._columns[x]._type=='boolean']

        for bool_field in bool_fields:
            if bool_field not in vals:
                vals[bool_field] = False
        #End
        for field in vals.copy():
            fobj = None
            if field in self._columns:
                fobj = self._columns[field]
            else:
                fobj = self._inherit_fields[field][2]
            if not fobj:
                continue
            groups = fobj.write
            if groups:
                edit = False
                for group in groups:
                    module = group.split(".")[0]
                    grp = group.split(".")[1]
                    cr.execute("select count(*) from res_groups_users_rel where gid IN (select res_id from ir_model_data where name='%s' and module='%s' and model='%s') and uid=%s" % \
                               (grp, module, 'res.groups', user))
                    readonly = cr.fetchall()
                    if readonly[0][0] >= 1:
                        edit = True
                        break
                    elif readonly[0][0] == 0:
                        edit = False
                    else:
                        edit = False

                if not edit:
                    vals.pop(field)
        for field in vals:
            current_field = self._columns[field]
            if current_field._classic_write:
                columns.append((field, '%s', current_field._symbol_set[1](vals[field])))

                #for the function fields that receive a value, we set them directly in the database
                #(they may be required), but we also need to trigger the _fct_inv()
                if (hasattr(current_field, '_fnct_inv')) and not isinstance(current_field, fields.related):
                    #TODO: this way to special case the related fields is really creepy but it shouldn't be changed at
                    #one week of the release candidate. It seems the only good way to handle correctly this is to add an
                    #attribute to make a field `really readonly´ and thus totally ignored by the create()... otherwise
                    #if, for example, the related has a default value (for usability) then the fct_inv is called and it
                    #may raise some access rights error. Changing this is a too big change for now, and is thus postponed
                    #after the release but, definitively, the behavior shouldn't be different for related and function
                    #fields.
                    upd_todo.append(field)
            else:
                #TODO: this `if´ statement should be removed because there is no good reason to special case the fields
                #related. See the above TODO comment for further explanations.
                if not isinstance(current_field, fields.related):
                    upd_todo.append(field)
            if field in self._columns \
                    and hasattr(current_field, 'selection') \
                    and vals[field]:
                self._check_selection_field_value(cr, user, field, vals[field], context=context)
        if self._log_access:
            columns.append(('create_uid', '%s', user))
            columns.append(('write_uid', '%s', user))
            columns.append(('create_date', "(now() at time zone 'UTC')"))
            columns.append(('write_date', "(now() at time zone 'UTC')"))

        # the list of tuples used in this formatting corresponds to
        # tuple(field_name, format, value)
        # In some case, for example (id, create_date, write_date) we does not
        # need to read the third value of the tuple, because the real value is
        # encoded in the second value (the format).
        cr.execute(
            """INSERT INTO "%s" (%s) VALUES(%s) RETURNING id""" % (
                self._table,
                ', '.join('"%s"' % f[0] for f in columns),
                ', '.join(f[1] for f in columns)
            ),
            tuple([f[2] for f in columns if len(f) > 2])
        )

        id_new, = cr.fetchone()
        upd_todo.sort(lambda x, y: self._columns[x].priority-self._columns[y].priority)

        if self._parent_store and not context.get('defer_parent_store_computation'):
            if self.pool._init:
                self.pool._init_parent[self._name] = True
            else:
                parent = vals.get(self._parent_name, False)
                if parent:
                    cr.execute('select parent_right from '+self._table+' where '+self._parent_name+'=%s order by '+(self._parent_order or self._order), (parent,))
                    pleft_old = None
                    result_p = cr.fetchall()
                    for (pleft,) in result_p:
                        if not pleft:
                            break
                        pleft_old = pleft
                    if not pleft_old:
                        cr.execute('select parent_left from '+self._table+' where id=%s', (parent,))
                        pleft_old = cr.fetchone()[0]
                    pleft = pleft_old
                else:
                    cr.execute('select max(parent_right) from '+self._table)
                    pleft = cr.fetchone()[0] or 0
                cr.execute('update '+self._table+' set parent_left=parent_left+2 where parent_left>%s', (pleft,))
                cr.execute('update '+self._table+' set parent_right=parent_right+2 where parent_right>%s', (pleft,))
                cr.execute('update '+self._table+' set parent_left=%s,parent_right=%s where id=%s', (pleft+1, pleft+2, id_new))

        # default element in context must be remove when call a one2many or many2many
        rel_context = context.copy()
        for c in context.items():
            if c[0].startswith('default_'):
                del rel_context[c[0]]

        result = []
        for field in upd_todo:
            result += self._columns[field].set(cr, self, id_new, field, vals[field], user, rel_context) or []
        self._validate(cr, user, [id_new], context)

        if not context.get('no_store_function', False):
            result += self._store_get_values(cr, user, [id_new],
                list(set(vals.keys() + self._inherits.values())),
                context)
            result.sort()
            done = []
            for order, model_name, ids, fields2 in result:
                if not (model_name, ids, fields2) in done:
                    self.pool[model_name]._store_set_values(cr, user, ids, fields2, context)
                    done.append((model_name, ids, fields2))

        if self._log_create and not (context and context.get('no_store_function', False)):
            message = self._description + \
                " '" + \
                self.name_get(cr, user, [id_new], context=context)[0][1] + \
                "' " + _("created.")
            self.log(cr, user, id_new, message, True, context=context)
        self.check_access_rule(cr, user, [id_new], 'create', context=context)
        self.create_workflow(cr, user, [id_new], context=context)
        return id_new

    def browse(self, cr, uid, select, context=None, list_class=None, fields_process=None):
        """Fetch records as objects allowing to use dot notation to browse fields and relations

        :param cr: database cursor
        :param uid: current user id
        :param select: id or list of ids.
        :param context: context arguments, like lang, time zone
        :rtype: object or list of objects requested

        """
        self._list_class = list_class or browse_record_list
        cache = {}
        # need to accepts ints and longs because ids coming from a method
        # launched by button in the interface have a type long...
        if isinstance(select, (int, long)):
            return browse_record(cr, uid, select, self, cache, context=context, list_class=self._list_class, fields_process=fields_process)
        elif isinstance(select, list):
            return self._list_class((browse_record(cr, uid, id, self, cache, context=context, list_class=self._list_class, fields_process=fields_process) for id in select), context=context)
        else:
            return browse_null()

    def _store_get_values(self, cr, uid, ids, fields, context):
        """Returns an ordered list of fields.function to call due to
           an update operation on ``fields`` of records with ``ids``,
           obtained by calling the 'store' triggers of these fields,
           as setup by their 'store' attribute.

           :return: [(priority, model_name, [record_ids,], [function_fields,])]
        """
        if fields is None: fields = []
        stored_functions = self.pool._store_function.get(self._name, [])

        # use indexed names for the details of the stored_functions:
        model_name_, func_field_to_compute_, target_ids_func_, trigger_fields_, priority_ = range(5)

        # only keep store triggers that should be triggered for the ``fields``
        # being written to.
        triggers_to_compute = [f for f in stored_functions \
                if ((not f[trigger_fields_]) or set(fields).intersection(f[trigger_fields_]))]

        to_compute_map = {}
        target_id_results = {}
        for store_trigger in triggers_to_compute:
            target_func_id_ = id(store_trigger[target_ids_func_])
            if not target_func_id_ in target_id_results:
                # use admin user for accessing objects having rules defined on store fields
                target_id_results[target_func_id_] = [i for i in store_trigger[target_ids_func_](self, cr, SUPERUSER_ID, ids, context) if i]
            target_ids = target_id_results[target_func_id_]

            # the compound key must consider the priority and model name
            key = (store_trigger[priority_], store_trigger[model_name_])
            for target_id in target_ids:
                to_compute_map.setdefault(key, {}).setdefault(target_id,set()).add(tuple(store_trigger))

        # Here to_compute_map looks like:
        # { (10, 'model_a') : { target_id1: [ (trigger_1_tuple, trigger_2_tuple) ], ... }
        #   (20, 'model_a') : { target_id2: [ (trigger_3_tuple, trigger_4_tuple) ], ... }
        #   (99, 'model_a') : { target_id1: [ (trigger_5_tuple, trigger_6_tuple) ], ... }
        # }

        # Now we need to generate the batch function calls list
        # call_map =
        #   { (10, 'model_a') : [(10, 'model_a', [record_ids,], [function_fields,])] }
        call_map = {}
        for ((priority,model), id_map) in to_compute_map.iteritems():
            trigger_ids_maps = {}
            # function_ids_maps =
            #   { (function_1_tuple, function_2_tuple) : [target_id1, target_id2, ..] }
            for target_id, triggers in id_map.iteritems():
                trigger_ids_maps.setdefault(tuple(triggers), []).append(target_id)
            for triggers, target_ids in trigger_ids_maps.iteritems():
                call_map.setdefault((priority,model),[]).append((priority, model, target_ids,
                                                                 [t[func_field_to_compute_] for t in triggers]))
        ordered_keys = call_map.keys()
        ordered_keys.sort()
        result = []
        if ordered_keys:
            result = reduce(operator.add, (call_map[k] for k in ordered_keys))
        return result

    def _store_set_values(self, cr, uid, ids, fields, context):
        """Calls the fields.function's "implementation function" for all ``fields``, on records with ``ids`` (taking care of
           respecting ``multi`` attributes), and stores the resulting values in the database directly."""
        if not ids:
            return True
        field_flag = False
        field_dict = {}
        if self._log_access:
            cr.execute('select id,write_date from '+self._table+' where id IN %s', (tuple(ids),))
            res = cr.fetchall()
            for r in res:
                if r[1]:
                    field_dict.setdefault(r[0], [])
                    res_date = time.strptime((r[1])[:19], '%Y-%m-%d %H:%M:%S')
                    write_date = datetime.datetime.fromtimestamp(time.mktime(res_date))
                    for i in self.pool._store_function.get(self._name, []):
                        if i[5]:
                            up_write_date = write_date + datetime.timedelta(hours=i[5])
                            if datetime.datetime.now() < up_write_date:
                                if i[1] in fields:
                                    field_dict[r[0]].append(i[1])
                                    if not field_flag:
                                        field_flag = True
        todo = {}
        keys = []
        for f in fields:
            if self._columns[f]._multi not in keys:
                keys.append(self._columns[f]._multi)
            todo.setdefault(self._columns[f]._multi, [])
            todo[self._columns[f]._multi].append(f)
        for key in keys:
            val = todo[key]
            if key:
                # use admin user for accessing objects having rules defined on store fields
                result = self._columns[val[0]].get(cr, self, ids, val, SUPERUSER_ID, context=context)
                for id, value in result.items():
                    if field_flag:
                        for f in value.keys():
                            if f in field_dict[id]:
                                value.pop(f)
                    upd0 = []
                    upd1 = []
                    for v in value:
                        if v not in val:
                            continue
                        if self._columns[v]._type == 'many2one':
                            try:
                                value[v] = value[v][0]
                            except:
                                pass
                        upd0.append('"'+v+'"='+self._columns[v]._symbol_set[0])
                        upd1.append(self._columns[v]._symbol_set[1](value[v]))
                    upd1.append(id)
                    if upd0 and upd1:
                        cr.execute('update "' + self._table + '" set ' + \
                            ','.join(upd0) + ' where id = %s', upd1)

            else:
                for f in val:
                    # use admin user for accessing objects having rules defined on store fields
                    result = self._columns[f].get(cr, self, ids, f, SUPERUSER_ID, context=context)
                    for r in result.keys():
                        if field_flag:
                            if r in field_dict.keys():
                                if f in field_dict[r]:
                                    result.pop(r)
                    for id, value in result.items():
                        if self._columns[f]._type == 'many2one':
                            try:
                                value = value[0]
                            except:
                                pass
                        cr.execute('update "' + self._table + '" set ' + \
                            '"'+f+'"='+self._columns[f]._symbol_set[0] + ' where id = %s', (self._columns[f]._symbol_set[1](value), id))
        return True

    #
    # TODO: Validate
    #
    def perm_write(self, cr, user, ids, fields, context=None):
        raise NotImplementedError(_('This method does not exist anymore'))

    # TODO: ameliorer avec NULL
    def _where_calc(self, cr, user, domain, active_test=True, context=None):
        """Computes the WHERE clause needed to implement an OpenERP domain.
        :param domain: the domain to compute
        :type domain: list
        :param active_test: whether the default filtering of records with ``active``
                            field set to ``False`` should be applied.
        :return: the query expressing the given domain as provided in domain
        :rtype: osv.query.Query
        """
        if not context:
            context = {}
        domain = domain[:]
        # if the object has a field named 'active', filter out all inactive
        # records unless they were explicitely asked for
        if 'active' in self._all_columns and (active_test and context.get('active_test', True)):
            if domain:
                # the item[0] trick below works for domain items and '&'/'|'/'!'
                # operators too
                if not any(item[0] == 'active' for item in domain):
                    domain.insert(0, ('active', '=', 1))
            else:
                domain = [('active', '=', 1)]

        if domain:
            e = expression.expression(cr, user, domain, self, context)
            tables = e.get_tables()
            where_clause, where_params = e.to_sql()
            where_clause = where_clause and [where_clause] or []
        else:
            where_clause, where_params, tables = [], [], ['"%s"' % self._table]

        return Query(tables, where_clause, where_params)

    def _check_qorder(self, word):
        if not regex_order.match(word):
            raise except_orm(_('AccessError'), _('Invalid "order" specified. A valid "order" specification is a comma-separated list of valid field names (optionally followed by asc/desc for the direction)'))
        return True

    def _apply_ir_rules(self, cr, uid, query, mode='read', context=None):
        """Add what's missing in ``query`` to implement all appropriate ir.rules
          (using the ``model_name``'s rules or the current model's rules if ``model_name`` is None)

           :param query: the current query object
        """
        if uid == SUPERUSER_ID:
            return

        def apply_rule(added_clause, added_params, added_tables, parent_model=None, child_object=None):
            """ :param string parent_model: string of the parent model
                :param model child_object: model object, base of the rule application
            """
            if added_clause:
                if parent_model and child_object:
                    # as inherited rules are being applied, we need to add the missing JOIN
                    # to reach the parent table (if it was not JOINed yet in the query)
                    parent_alias = child_object._inherits_join_add(child_object, parent_model, query)
                    # inherited rules are applied on the external table -> need to get the alias and replace
                    parent_table = self.pool[parent_model]._table
                    added_clause = [clause.replace('"%s"' % parent_table, '"%s"' % parent_alias) for clause in added_clause]
                    # change references to parent_table to parent_alias, because we now use the alias to refer to the table
                    new_tables = []
                    for table in added_tables:
                        # table is just a table name -> switch to the full alias
                        if table == '"%s"' % parent_table:
                            new_tables.append('"%s" as "%s"' % (parent_table, parent_alias))
                        # table is already a full statement -> replace reference to the table to its alias, is correct with the way aliases are generated
                        else:
                            new_tables.append(table.replace('"%s"' % parent_table, '"%s"' % parent_alias))
                    added_tables = new_tables
                query.where_clause += added_clause
                query.where_clause_params += added_params
                for table in added_tables:
                    if table not in query.tables:
                        query.tables.append(table)
                return True
            return False

        # apply main rules on the object
        rule_obj = self.pool.get('ir.rule')
        rule_where_clause, rule_where_clause_params, rule_tables = rule_obj.domain_get(cr, uid, self._name, mode, context=context)
        apply_rule(rule_where_clause, rule_where_clause_params, rule_tables)

        # apply ir.rules from the parents (through _inherits)
        for inherited_model in self._inherits:
            rule_where_clause, rule_where_clause_params, rule_tables = rule_obj.domain_get(cr, uid, inherited_model, mode, context=context)
            apply_rule(rule_where_clause, rule_where_clause_params, rule_tables,
                        parent_model=inherited_model, child_object=self)

    def _generate_m2o_order_by(self, order_field, query):
        """
        Add possibly missing JOIN to ``query`` and generate the ORDER BY clause for m2o fields,
        either native m2o fields or function/related fields that are stored, including
        intermediate JOINs for inheritance if required.

        :return: the qualified field name to use in an ORDER BY clause to sort by ``order_field``
        """
        if order_field not in self._columns and order_field in self._inherit_fields:
            # also add missing joins for reaching the table containing the m2o field
            qualified_field = self._inherits_join_calc(order_field, query)
            order_field_column = self._inherit_fields[order_field][2]
        else:
            qualified_field = '"%s"."%s"' % (self._table, order_field)
            order_field_column = self._columns[order_field]

        assert order_field_column._type == 'many2one', 'Invalid field passed to _generate_m2o_order_by()'
        if not order_field_column._classic_write and not getattr(order_field_column, 'store', False):
            _logger.debug("Many2one function/related fields must be stored " \
                "to be used as ordering fields! Ignoring sorting for %s.%s",
                self._name, order_field)
            return

        # figure out the applicable order_by for the m2o
        dest_model = self.pool[order_field_column._obj]
        m2o_order = dest_model._order
        if not regex_order.match(m2o_order):
            # _order is complex, can't use it here, so we default to _rec_name
            m2o_order = dest_model._rec_name
        else:
            # extract the field names, to be able to qualify them and add desc/asc
            m2o_order_list = []
            for order_part in m2o_order.split(","):
                m2o_order_list.append(order_part.strip().split(" ", 1)[0].strip())
            m2o_order = m2o_order_list

        # Join the dest m2o table if it's not joined yet. We use [LEFT] OUTER join here
        # as we don't want to exclude results that have NULL values for the m2o
        src_table, src_field = qualified_field.replace('"', '').split('.', 1)
        dst_alias, dst_alias_statement = query.add_join((src_table, dest_model._table, src_field, 'id', src_field), implicit=False, outer=True)
        qualify = lambda field: '"%s"."%s"' % (dst_alias, field)
        return map(qualify, m2o_order) if isinstance(m2o_order, list) else qualify(m2o_order)

    def _generate_order_by(self, order_spec, query):
        """
        Attempt to consruct an appropriate ORDER BY clause based on order_spec, which must be
        a comma-separated list of valid field names, optionally followed by an ASC or DESC direction.

        :raise" except_orm in case order_spec is malformed
        """
        order_by_clause = ''
        order_spec = order_spec or self._order
        if order_spec:
            order_by_elements = []
            self._check_qorder(order_spec)
            for order_part in order_spec.split(','):
                order_split = order_part.strip().split(' ')
                order_field = order_split[0].strip()
                order_direction = order_split[1].strip() if len(order_split) == 2 else ''
                inner_clause = None
                if order_field == 'id' or (self._log_access and order_field in LOG_ACCESS_COLUMNS.keys()):
                    order_by_elements.append('"%s"."%s" %s' % (self._table, order_field, order_direction))
                elif order_field in self._columns:
                    order_column = self._columns[order_field]
                    if order_column._classic_read:
                        inner_clause = '"%s"."%s"' % (self._table, order_field)
                    elif order_column._type == 'many2one':
                        inner_clause = self._generate_m2o_order_by(order_field, query)
                    else:
                        continue  # ignore non-readable or "non-joinable" fields
                elif order_field in self._inherit_fields:
                    parent_obj = self.pool[self._inherit_fields[order_field][3]]
                    order_column = parent_obj._columns[order_field]
                    if order_column._classic_read:
                        inner_clause = self._inherits_join_calc(order_field, query)
                    elif order_column._type == 'many2one':
                        inner_clause = self._generate_m2o_order_by(order_field, query)
                    else:
                        continue  # ignore non-readable or "non-joinable" fields
                else:
                    raise ValueError( _("Sorting field %s not found on model %s") %( order_field, self._name))
                if inner_clause:
                    if isinstance(inner_clause, list):
                        for clause in inner_clause:
                            order_by_elements.append("%s %s" % (clause, order_direction))
                    else:
                        order_by_elements.append("%s %s" % (inner_clause, order_direction))
            if order_by_elements:
                order_by_clause = ",".join(order_by_elements)

        return order_by_clause and (' ORDER BY %s ' % order_by_clause) or ''

    def _search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False, access_rights_uid=None):
        """
        Private implementation of search() method, allowing specifying the uid to use for the access right check.
        This is useful for example when filling in the selection list for a drop-down and avoiding access rights errors,
        by specifying ``access_rights_uid=1`` to bypass access rights check, but not ir.rules!
        This is ok at the security level because this method is private and not callable through XML-RPC.

        :param access_rights_uid: optional user ID to use when checking access rights
                                  (not for ir.rules, this is only for ir.model.access)
        """
        if context is None:
            context = {}
        self.check_access_rights(cr, access_rights_uid or user, 'read')

        # For transient models, restrict acces to the current user, except for the super-user
        if self.is_transient() and self._log_access and user != SUPERUSER_ID:
            args = expression.AND(([('create_uid', '=', user)], args or []))

        query = self._where_calc(cr, user, args, context=context)
        self._apply_ir_rules(cr, user, query, 'read', context=context)
        order_by = self._generate_order_by(order, query)
        from_clause, where_clause, where_clause_params = query.get_sql()

        limit_str = limit and ' limit %d' % limit or ''
        offset_str = offset and ' offset %d' % offset or ''
        where_str = where_clause and (" WHERE %s" % where_clause) or ''
        query_str = 'SELECT "%s".id FROM ' % self._table + from_clause + where_str + order_by + limit_str + offset_str

        if count:
            # /!\ the main query must be executed as a subquery, otherwise
            # offset and limit apply to the result of count()!
            cr.execute('SELECT count(*) FROM (%s) AS count' % query_str, where_clause_params)
            res = cr.fetchone()
            return res[0]

        cr.execute(query_str, where_clause_params)
        res = cr.fetchall()

        # TDE note: with auto_join, we could have several lines about the same result
        # i.e. a lead with several unread messages; we uniquify the result using
        # a fast way to do it while preserving order (http://www.peterbe.com/plog/uniqifiers-benchmark)
        def _uniquify_list(seq):
            seen = set()
            return [x for x in seq if x not in seen and not seen.add(x)]

        return _uniquify_list([x[0] for x in res])

    # returns the different values ever entered for one field
    # this is used, for example, in the client when the user hits enter on
    # a char field
    def distinct_field_get(self, cr, uid, field, value, args=None, offset=0, limit=None):
        if not args:
            args = []
        if field in self._inherit_fields:
            return self.pool[self._inherit_fields[field][0]].distinct_field_get(cr, uid, field, value, args, offset, limit)
        else:
            return self._columns[field].search(cr, self, args, field, value, offset, limit, uid)

    def copy_data(self, cr, uid, id, default=None, context=None):
        """
        Copy given record's data with all its fields values

        :param cr: database cursor
        :param uid: current user id
        :param id: id of the record to copy
        :param default: field values to override in the original values of the copied record
        :type default: dictionary
        :param context: context arguments, like lang, time zone
        :type context: dictionary
        :return: dictionary containing all the field values
        """

        if context is None:
            context = {}

        # avoid recursion through already copied records in case of circular relationship
        seen_map = context.setdefault('__copy_data_seen', {})
        if id in seen_map.setdefault(self._name, []):
            return
        seen_map[self._name].append(id)

        if default is None:
            default = {}
        if 'state' not in default:
            if 'state' in self._defaults:
                if callable(self._defaults['state']):
                    default['state'] = self._defaults['state'](self, cr, uid, context)
                else:
                    default['state'] = self._defaults['state']

        # build a black list of fields that should not be copied
        blacklist = set(MAGIC_COLUMNS + ['parent_left', 'parent_right'])
        def blacklist_given_fields(obj):
            # blacklist the fields that are given by inheritance
            for other, field_to_other in obj._inherits.items():
                blacklist.add(field_to_other)
                if field_to_other in default:
                    # all the fields of 'other' are given by the record: default[field_to_other],
                    # except the ones redefined in self
                    blacklist.update(set(self.pool[other]._all_columns) - set(self._columns))
                else:
                    blacklist_given_fields(self.pool[other])
            # blacklist deprecated fields
            for name, field in obj._columns.items():
                if field.deprecated:
                    blacklist.add(name)

        blacklist_given_fields(self)


        fields_to_copy = dict((f,fi) for f, fi in self._all_columns.iteritems()
                                     if f not in default
                                     if f not in blacklist
                                     if not isinstance(fi.column, fields.function))

        data = self.read(cr, uid, [id], fields_to_copy.keys(), context=context)
        if data:
            data = data[0]
        else:
            raise IndexError( _("Record #%d of %s not found, cannot copy!") %( id, self._name))

        res = dict(default)
        for f, colinfo in fields_to_copy.iteritems():
            field = colinfo.column
            if field._type == 'many2one':
                res[f] = data[f] and data[f][0]
            elif field._type == 'one2many':
                other = self.pool[field._obj]
                # duplicate following the order of the ids because we'll rely on
                # it later for copying translations in copy_translation()!
                lines = [other.copy_data(cr, uid, line_id, context=context) for line_id in sorted(data[f])]
                # the lines are duplicated using the wrong (old) parent, but then
                # are reassigned to the correct one thanks to the (0, 0, ...)
                res[f] = [(0, 0, line) for line in lines if line]
            elif field._type == 'many2many':
                res[f] = [(6, 0, data[f])]
            else:
                res[f] = data[f]

        return res

    def copy_translations(self, cr, uid, old_id, new_id, context=None):
        if context is None:
            context = {}

        # avoid recursion through already copied records in case of circular relationship
        seen_map = context.setdefault('__copy_translations_seen',{})
        if old_id in seen_map.setdefault(self._name,[]):
            return
        seen_map[self._name].append(old_id)

        trans_obj = self.pool.get('ir.translation')
        # TODO it seems fields_get can be replaced by _all_columns (no need for translation)
        fields = self.fields_get(cr, uid, context=context)

        for field_name, field_def in fields.items():
            # removing the lang to compare untranslated values
            context_wo_lang = dict(context, lang=None)
            old_record, new_record = self.browse(cr, uid, [old_id, new_id], context=context_wo_lang)
            # we must recursively copy the translations for o2o and o2m
            if field_def['type'] == 'one2many':
                target_obj = self.pool[field_def['relation']]
                # here we rely on the order of the ids to match the translations
                # as foreseen in copy_data()
                old_children = sorted(r.id for r in old_record[field_name])
                new_children = sorted(r.id for r in new_record[field_name])
                for (old_child, new_child) in zip(old_children, new_children):
                    target_obj.copy_translations(cr, uid, old_child, new_child, context=context)
            # and for translatable fields we keep them for copy
            elif field_def.get('translate'):
                if field_name in self._columns:
                    trans_name = self._name + "," + field_name
                    target_id = new_id
                    source_id = old_id
                elif field_name in self._inherit_fields:
                    trans_name = self._inherit_fields[field_name][0] + "," + field_name
                    # get the id of the parent record to set the translation
                    inherit_field_name = self._inherit_fields[field_name][1]
                    target_id = new_record[inherit_field_name].id
                    source_id = old_record[inherit_field_name].id
                else:
                    continue

                trans_ids = trans_obj.search(cr, uid, [
                        ('name', '=', trans_name),
                        ('res_id', '=', source_id)
                ])
                user_lang = context.get('lang')
                for record in trans_obj.read(cr, uid, trans_ids, context=context):
                    del record['id']
                    # remove source to avoid triggering _set_src
                    del record['source']
                    record.update({'res_id': target_id})
                    if user_lang and user_lang == record['lang']:
                        # 'source' to force the call to _set_src
                        # 'value' needed if value is changed in copy(), want to see the new_value
                        record['source'] = old_record[field_name]
                        record['value'] = new_record[field_name]
                    trans_obj.create(cr, uid, record, context=context)


    def copy(self, cr, uid, id, default=None, context=None):
        """
        Duplicate record with given id updating it with default values

        :param cr: database cursor
        :param uid: current user id
        :param id: id of the record to copy
        :param default: dictionary of field values to override in the original values of the copied record, e.g: ``{'field_name': overriden_value, ...}``
        :type default: dictionary
        :param context: context arguments, like lang, time zone
        :type context: dictionary
        :return: id of the newly created record

        """
        if context is None:
            context = {}
        context = context.copy()
        data = self.copy_data(cr, uid, id, default, context)
        new_id = self.create(cr, uid, data, context)
        self.copy_translations(cr, uid, id, new_id, context)
        return new_id

    def exists(self, cr, uid, ids, context=None):
        """Checks whether the given id or ids exist in this model,
           and return the list of ids that do. This is simple to use for
           a truth test on a browse_record::

               if record.exists():
                   pass

           :param ids: id or list of ids to check for existence
           :type ids: int or [int]
           :return: the list of ids that currently exist, out of
                    the given `ids`
        """
        if type(ids) in (int, long):
            ids = [ids]
        if not ids:
            return []
        query = 'SELECT id FROM "%s"' % self._table
        cr.execute(query + "WHERE ID IN %s", (tuple(ids),))
        return [x[0] for x in cr.fetchall()]

    def check_recursion(self, cr, uid, ids, context=None, parent=None):
        _logger.warning("You are using deprecated %s.check_recursion(). Please use the '_check_recursion()' instead!" % \
                        self._name)
        assert parent is None or parent in self._columns or parent in self._inherit_fields,\
                    "The 'parent' parameter passed to check_recursion() must be None or a valid field name"
        return self._check_recursion(cr, uid, ids, context, parent)

    def _check_recursion(self, cr, uid, ids, context=None, parent=None):
        """
        Verifies that there is no loop in a hierarchical structure of records,
        by following the parent relationship using the **parent** field until a loop
        is detected or until a top-level record is found.

        :param cr: database cursor
        :param uid: current user id
        :param ids: list of ids of records to check
        :param parent: optional parent field name (default: ``self._parent_name = parent_id``)
        :return: **True** if the operation can proceed safely, or **False** if an infinite loop is detected.
        """
        if not parent:
            parent = self._parent_name

        # must ignore 'active' flag, ir.rules, etc. => direct SQL query
        query = 'SELECT "%s" FROM "%s" WHERE id = %%s' % (parent, self._table)
        for id in ids:
            current_id = id
            while current_id is not None:
                cr.execute(query, (current_id,))
                result = cr.fetchone()
                current_id = result[0] if result else None
                if current_id == id:
                    return False
        return True

    def _check_m2m_recursion(self, cr, uid, ids, field_name):
        """
        Verifies that there is no loop in a hierarchical structure of records,
        by following the parent relationship using the **parent** field until a loop
        is detected or until a top-level record is found.

        :param cr: database cursor
        :param uid: current user id
        :param ids: list of ids of records to check
        :param field_name: field to check
        :return: **True** if the operation can proceed safely, or **False** if an infinite loop is detected.
        """

        field = self._all_columns.get(field_name)
        field = field.column if field else None
        if not field or field._type != 'many2many' or field._obj != self._name:
            # field must be a many2many on itself
            raise ValueError('invalid field_name: %r' % (field_name,))

        query = 'SELECT distinct "%s" FROM "%s" WHERE "%s" IN %%s' % (field._id2, field._rel, field._id1)
        ids_parent = ids[:]
        while ids_parent:
            ids_parent2 = []
            for i in range(0, len(ids_parent), cr.IN_MAX):
                j = i + cr.IN_MAX
                sub_ids_parent = ids_parent[i:j]
                cr.execute(query, (tuple(sub_ids_parent),))
                ids_parent2.extend(filter(None, map(lambda x: x[0], cr.fetchall())))
            ids_parent = ids_parent2
            for i in ids_parent:
                if i in ids:
                    return False
        return True

    def _get_external_ids(self, cr, uid, ids, *args, **kwargs):
        """Retrieve the External ID(s) of any database record.

        **Synopsis**: ``_get_xml_ids(cr, uid, ids) -> { 'id': ['module.xml_id'] }``

        :return: map of ids to the list of their fully qualified External IDs
                 in the form ``module.key``, or an empty list when there's no External
                 ID for a record, e.g.::

                     { 'id': ['module.ext_id', 'module.ext_id_bis'],
                       'id2': [] }
        """
        ir_model_data = self.pool.get('ir.model.data')
        data_ids = ir_model_data.search(cr, uid, [('model', '=', self._name), ('res_id', 'in', ids)])
        data_results = ir_model_data.read(cr, uid, data_ids, ['module', 'name', 'res_id'])
        result = {}
        for id in ids:
            # can't use dict.fromkeys() as the list would be shared!
            result[id] = []
        for record in data_results:
            result[record['res_id']].append('%(module)s.%(name)s' % record)
        return result

    def get_external_id(self, cr, uid, ids, *args, **kwargs):
        """Retrieve the External ID of any database record, if there
        is one. This method works as a possible implementation
        for a function field, to be able to add it to any
        model object easily, referencing it as ``Model.get_external_id``.

        When multiple External IDs exist for a record, only one
        of them is returned (randomly).

        :return: map of ids to their fully qualified XML ID,
                 defaulting to an empty string when there's none
                 (to be usable as a function field),
                 e.g.::

                     { 'id': 'module.ext_id',
                       'id2': '' }
        """
        results = self._get_xml_ids(cr, uid, ids)
        for k, v in results.iteritems():
            if results[k]:
                results[k] = v[0]
            else:
                results[k] = ''
        return results

    # backwards compatibility
    get_xml_id = get_external_id
    _get_xml_ids = _get_external_ids

    def print_report(self, cr, uid, ids, name, data, context=None):
        """
        Render the report `name` for the given IDs. The report must be defined
        for this model, not another.
        """
        report = self.pool['ir.actions.report.xml']._lookup_report(cr, name)
        assert self._name == report.table
        return report.create(cr, uid, ids, data, context)

    # Transience
    def is_transient(self):
        """ Return whether the model is transient.

        See :class:`TransientModel`.

        """
        return self._transient

    def _transient_clean_rows_older_than(self, cr, seconds):
        assert self._transient, "Model %s is not transient, it cannot be vacuumed!" % self._name
        # Never delete rows used in last 5 minutes
        seconds = max(seconds, 300)
        query = ("SELECT id FROM " + self._table + " WHERE"
            " COALESCE(write_date, create_date, (now() at time zone 'UTC'))::timestamp"
            " < ((now() at time zone 'UTC') - interval %s)")
        cr.execute(query, ("%s seconds" % seconds,))
        ids = [x[0] for x in cr.fetchall()]
        self.unlink(cr, SUPERUSER_ID, ids)

    def _transient_clean_old_rows(self, cr, max_count):
        # Check how many rows we have in the table
        cr.execute("SELECT count(*) AS row_count FROM " + self._table)
        res = cr.fetchall()
        if res[0][0] <= max_count:
            return  # max not reached, nothing to do
        self._transient_clean_rows_older_than(cr, 300)

    def _transient_vacuum(self, cr, uid, force=False):
        """Clean the transient records.

        This unlinks old records from the transient model tables whenever the
        "_transient_max_count" or "_max_age" conditions (if any) are reached.
        Actual cleaning will happen only once every "_transient_check_time" calls.
        This means this method can be called frequently called (e.g. whenever
        a new record is created).
        Example with both max_hours and max_count active:
        Suppose max_hours = 0.2 (e.g. 12 minutes), max_count = 20, there are 55 rows in the
        table, 10 created/changed in the last 5 minutes, an additional 12 created/changed between
        5 and 10 minutes ago, the rest created/changed more then 12 minutes ago.
        - age based vacuum will leave the 22 rows created/changed in the last 12 minutes
        - count based vacuum will wipe out another 12 rows. Not just 2, otherwise each addition
          would immediately cause the maximum to be reached again.
        - the 10 rows that have been created/changed the last 5 minutes will NOT be deleted
        """
        assert self._transient, "Model %s is not transient, it cannot be vacuumed!" % self._name
        _transient_check_time = 20          # arbitrary limit on vacuum executions
        self._transient_check_count += 1
        if not force and (self._transient_check_count < _transient_check_time):
            return True  # no vacuum cleaning this time
        self._transient_check_count = 0

        # Age-based expiration
        if self._transient_max_hours:
            self._transient_clean_rows_older_than(cr, self._transient_max_hours * 60 * 60)

        # Count-based expiration
        if self._transient_max_count:
            self._transient_clean_old_rows(cr, self._transient_max_count)

        return True

    def resolve_2many_commands(self, cr, uid, field_name, commands, fields=None, context=None):
        """ Serializes one2many and many2many commands into record dictionaries
            (as if all the records came from the database via a read()).  This
            method is aimed at onchange methods on one2many and many2many fields.

            Because commands might be creation commands, not all record dicts
            will contain an ``id`` field.  Commands matching an existing record
            will have an ``id``.

            :param field_name: name of the one2many or many2many field matching the commands
            :type field_name: str
            :param commands: one2many or many2many commands to execute on ``field_name``
            :type commands: list((int|False, int|False, dict|False))
            :param fields: list of fields to read from the database, when applicable
            :type fields: list(str)
            :returns: records in a shape similar to that returned by ``read()``
                (except records may be missing the ``id`` field if they don't exist in db)
            :rtype: list(dict)
        """
        result = []             # result (list of dict)
        record_ids = []         # ids of records to read
        updates = {}            # {id: dict} of updates on particular records

        for command in commands:
            if not isinstance(command, (list, tuple)):
                record_ids.append(command)
            elif command[0] == 0:
                result.append(command[2])
            elif command[0] == 1:
                record_ids.append(command[1])
                updates.setdefault(command[1], {}).update(command[2])
            elif command[0] in (2, 3):
                record_ids = [id for id in record_ids if id != command[1]]
            elif command[0] == 4:
                record_ids.append(command[1])
            elif command[0] == 5:
                result, record_ids = [], []
            elif command[0] == 6:
                result, record_ids = [], list(command[2])

        # read the records and apply the updates
        other_model = self.pool[self._all_columns[field_name].column._obj]
        for record in other_model.read(cr, uid, record_ids, fields=fields, context=context):
            record.update(updates.get(record['id'], {}))
            result.append(record)

        return result

    # for backward compatibility
    resolve_o2m_commands_to_record_dicts = resolve_2many_commands

    def search_read(self, cr, uid, domain=None, fields=None, offset=0, limit=None, order=None, context=None):
        """
        Performs a ``search()`` followed by a ``read()``.

        :param cr: database cursor
        :param user: current user id
        :param domain: Search domain, see ``args`` parameter in ``search()``. Defaults to an empty domain that will match all records.
        :param fields: List of fields to read, see ``fields`` parameter in ``read()``. Defaults to all fields.
        :param offset: Number of records to skip, see ``offset`` parameter in ``search()``. Defaults to 0.
        :param limit: Maximum number of records to return, see ``limit`` parameter in ``search()``. Defaults to no limit.
        :param order: Columns to sort result, see ``order`` parameter in ``search()``. Defaults to no sort.
        :param context: context arguments.
        :return: List of dictionaries containing the asked fields.
        :rtype: List of dictionaries.

        """
        record_ids = self.search(cr, uid, domain or [], offset=offset, limit=limit, order=order, context=context)
        if not record_ids:
            return []

        if fields and fields == ['id']:
            # shortcut read if we only want the ids
            return [{'id': id} for id in record_ids]

        # read() ignores active_test, but it would forward it to any downstream search call
        # (e.g. for x2m or function fields), and this is not the desired behavior, the flag
        # was presumably only meant for the main search().
        # TODO: Move this to read() directly?                                                                                                
        read_ctx = dict(context or {})                                                                                                       
        read_ctx.pop('active_test', None)                                                                                                    
                                                                                                                                             
        result = self.read(cr, uid, record_ids, fields, context=read_ctx) 
        if len(result) <= 1:
            return result

        # reorder read
        index = dict((r['id'], r) for r in result)
        return [index[x] for x in record_ids if x in index]

    def _register_hook(self, cr):
        """ stuff to do right after the registry is built """
        pass

    def __getattr__(self, name):
        if name.startswith('signal_'):
            signal_name = name[len('signal_'):]
            assert signal_name
            return (lambda *args, **kwargs:
                    self.signal_workflow(*args, signal=signal_name, **kwargs))
        get = getattr(super(BaseModel, self), '__getattr__', None)
        if get is not None: return get(name)
        raise AttributeError(
            "'%s' object has no attribute '%s'" % (type(self).__name__, name))

# keep this import here, at top it will cause dependency cycle errors
import expression

class Model(BaseModel):
    """Main super-class for regular database-persisted OpenERP models.

    OpenERP models are created by inheriting from this class::

        class user(Model):
            ...

    The system will later instantiate the class once per database (on
    which the class' module is installed).
    """
    _auto = True
    _register = False # not visible in ORM registry, meant to be python-inherited only
    _transient = False # True in a TransientModel

class TransientModel(BaseModel):
    """Model super-class for transient records, meant to be temporarily
       persisted, and regularly vaccuum-cleaned.

       A TransientModel has a simplified access rights management,
       all users can create new records, and may only access the
       records they created. The super-user has unrestricted access
       to all TransientModel records.
    """
    _auto = True
    _register = False # not visible in ORM registry, meant to be python-inherited only
    _transient = True

class AbstractModel(BaseModel):
    """Abstract Model super-class for creating an abstract class meant to be
       inherited by regular models (Models or TransientModels) but not meant to
       be usable on its own, or persisted.

       Technical note: we don't want to make AbstractModel the super-class of
       Model or BaseModel because it would not make sense to put the main
       definition of persistence methods such as create() in it, and still we
       should be able to override them within an AbstractModel.
       """
    _auto = False # don't create any database backend for AbstractModels
    _register = False # not visible in ORM registry, meant to be python-inherited only
    _transient = False

def itemgetter_tuple(items):
    """ Fixes itemgetter inconsistency (useful in some cases) of not returning
    a tuple if len(items) == 1: always returns an n-tuple where n = len(items)
    """
    if len(items) == 0:
        return lambda a: ()
    if len(items) == 1:
        return lambda gettable: (gettable[items[0]],)
    return operator.itemgetter(*items)

class ImportWarning(Warning):
    """ Used to send warnings upwards the stack during the import process
    """
    pass

def convert_pgerror_23502(model, fields, info, e):
    m = re.match(r'^null value in column "(?P<field>\w+)" violates '
                 r'not-null constraint\n',
                 str(e))
    field_name = m and m.group('field')
    if not m or field_name not in fields:
        return {'message': unicode(e)}
    message = _(u"Missing required value for the field '%s'.") % field_name
    field = fields.get(field_name)
    if field:
        message = _(u"Missing required value for the field '%s' (%s)") % (field['string'], field_name)
    return {
        'message': message,
        'field': field_name,
    }

def convert_pgerror_23505(model, fields, info, e):
    m = re.match(r'^duplicate key (?P<field>\w+) violates unique constraint',
                 str(e))
    field_name = m and m.group('field')
    if not m or field_name not in fields:
        return {'message': unicode(e)}
    message = _(u"The value for the field '%s' already exists.") % field_name
    field = fields.get(field_name)
    if field:
        message = _(u"%s This might be '%s' in the current model, or a field "
                    u"of the same name in an o2m.") % (message, field['string'])
    return {
        'message': message,
        'field': field_name,
    }

PGERROR_TO_OE = collections.defaultdict(
    # shape of mapped converters
    lambda: (lambda model, fvg, info, pgerror: {'message': unicode(pgerror)}), {
    # not_null_violation
    '23502': convert_pgerror_23502,
    # unique constraint error
    '23505': convert_pgerror_23505,
})
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
