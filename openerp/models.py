# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


"""
    Object Relational Mapping module:
     * Hierarchical structure
     * Constraints consistency and validation
     * Object metadata depends on its status
     * Optimised processing by complex query (multiple actions at once)
     * Default field values
     * Permissions optimisation
     * Persistant object: DB postgresql
     * Data conversion
     * Multi-level caching system
     * Two different inheritance mechanisms
     * Rich set of field types:
          - classical (varchar, integer, boolean, ...)
          - relational (one2many, many2one, many2many)
          - functional

"""

import datetime
import dateutil
import functools
import itertools
import logging
import operator
import pytz
import re
import time
from collections import defaultdict, MutableMapping
from inspect import getmembers, currentframe
from operator import itemgetter

import babel.dates
import dateutil.relativedelta
import psycopg2
from lxml import etree

import openerp
from . import SUPERUSER_ID
from . import api
from . import tools
from .api import Environment
from .exceptions import AccessError, MissingError, ValidationError, UserError
from .osv import fields
from .osv.query import Query
from .tools import frozendict, lazy_property, ormcache, Collector
from .tools.config import config
from .tools.func import frame_codeinfo
from .tools.misc import CountingStream, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT, pickle
from .tools.safe_eval import safe_eval as eval
from .tools.translate import _

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')
_unlink = logging.getLogger(__name__ + '.unlink')

regex_order = re.compile('^(\s*([a-z0-9:_]+|"[a-z0-9:_]+")(\s+(desc|asc))?\s*(,|$))+(?<!,)$', re.I)
regex_object_name = re.compile(r'^[a-z0-9_.]+$')
regex_pg_name = re.compile(r'^[a-z_][a-z0-9_$]*$', re.I)
onchange_v7 = re.compile(r"^(\w+)\((.*)\)$")

AUTOINIT_RECALCULATE_STORED_FIELDS = 1000

# base environment for doing a safe eval
SAFE_EVAL_BASE = {
    'datetime': datetime,
    'dateutil': dateutil,
    'time': time,
}

def make_compute(text, deps):
    """ Return a compute function from its code body and dependencies. """
    func = lambda self: eval(text, SAFE_EVAL_BASE, {'self': self}, mode="exec")
    deps = [arg.strip() for arg in (deps or "").split(",")]
    return api.depends(*deps)(func)


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
        raise ValueError(msg)

def check_pg_name(name):
    """ Check whether the given name is a valid PostgreSQL identifier name. """
    if not regex_pg_name.match(name):
        raise ValueError("Invalid characters in table name %r" % name)
    if len(name) > 63:
        raise ValueError("Table name %r is too long" % name)

POSTGRES_CONFDELTYPES = {
    'RESTRICT': 'r',
    'NO ACTION': 'a',
    'CASCADE': 'c',
    'SET NULL': 'n',
    'SET DEFAULT': 'd',
}

def intersect(la, lb):
    return filter(lambda x: x in lb, la)

def same_name(f, g):
    """ Test whether functions ``f`` and ``g`` are identical or have the same name """
    return f == g or getattr(f, '__name__', 0) == getattr(g, '__name__', 1)

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
            raise ValueError("VARCHAR parameter should be an int, got %s" % type(size))
        if size > 0:
            return 'VARCHAR(%d)' % size
    return 'VARCHAR'

FIELDS_TO_PGTYPES = {
    fields.boolean: 'bool',
    fields.integer: 'int4',
    fields.monetary: 'numeric',
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
        # Explicit support for "falsy" digits (0, False) to indicate a
        # NUMERIC field with no fixed precision. The values will be saved
        # in the database with all significant digits.
        # FLOAT8 type is still the default when there is no precision because
        # it is faster for most operations (sums, etc.)
        if f.digits is not None:
            pg_type = ('numeric', 'NUMERIC')
        else:
            pg_type = ('float8', 'DOUBLE PRECISION')
    elif issubclass(field_type, (fields.char, fields.reference)):
        pg_type = ('varchar', pg_varchar(f.size))
    elif issubclass(field_type, fields.selection):
        if (f.selection and isinstance(f.selection, list) and isinstance(f.selection[0][0], int))\
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


class MetaModel(api.Meta):
    """ Metaclass for the models.

    This class is used as the metaclass for the class :class:`BaseModel` to
    discover the models defined in a module (without instantiating them).
    If the automatic discovery is not needed, it is possible to set the model's
    ``_register`` attribute to False.

    """

    module_to_models = {}

    def __init__(self, name, bases, attrs):
        if not self._register:
            self._register = True
            super(MetaModel, self).__init__(name, bases, attrs)
            return

        if not hasattr(self, '_module'):
            # The (OpenERP) module name can be in the ``openerp.addons`` namespace
            # or not.  For instance, module ``sale`` can be imported as
            # ``openerp.addons.sale`` (the right way) or ``sale`` (for backward
            # compatibility).
            module_parts = self.__module__.split('.')
            if len(module_parts) > 2 and module_parts[:2] == ['openerp', 'addons']:
                module_name = self.__module__.split('.')[2]
            else:
                module_name = self.__module__.split('.')[0]
            self._module = module_name

        # Remember which models to instanciate for this module.
        if not self._custom:
            self.module_to_models.setdefault(self._module, []).append(self)

        # check for new-api conversion error: leave comma after field definition
        for key, val in attrs.iteritems():
            if type(val) is tuple and len(val) == 1 and isinstance(val[0], Field):
                _logger.error("Trailing comma after field definition: %s.%s", self, key)

        # transform columns into new-style fields (enables field inheritance)
        for name, column in self._columns.iteritems():
            if name in self.__dict__:
                _logger.warning("In class %s, field %r overriding an existing value", self, name)
            setattr(self, name, column.to_field())


class NewId(object):
    """ Pseudo-ids for new records. """
    def __nonzero__(self):
        return False

IdType = (int, long, basestring, NewId)


# maximum number of prefetched records
PREFETCH_MAX = 1000

# special columns automatically created by the ORM
LOG_ACCESS_COLUMNS = ['create_uid', 'create_date', 'write_uid', 'write_date']
MAGIC_COLUMNS = ['id'] + LOG_ACCESS_COLUMNS

class BaseModel(object):
    """ Base class for OpenERP models.

    OpenERP models are created by inheriting from this class' subclasses:

    *   :class:`Model` for regular database-persisted models

    *   :class:`TransientModel` for temporary data, stored in the database but
        automatically vacuumed every so often

    *   :class:`AbstractModel` for abstract super classes meant to be shared by
        multiple inheriting model

    The system automatically instantiates every model once per database. Those
    instances represent the available models on each database, and depend on
    which modules are installed on that database. The actual class of each
    instance is built from the Python classes that create and inherit from the
    corresponding model.

    Every model instance is a "recordset", i.e., an ordered collection of
    records of the model. Recordsets are returned by methods like
    :meth:`~.browse`, :meth:`~.search`, or field accesses. Records have no
    explicit representation: a record is represented as a recordset of one
    record.

    To create a class that should not be instantiated, the _register class
    attribute may be set to False.
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
    _translate = True # set to False to disable translations export for this model

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

    _table = None
    _sql_constraints = []

    # model dependencies, for models backed up by sql views:
    # {model_name: field_names, ...}
    _depends = {}

    CONCURRENCY_CHECK_FIELD = '__last_update'

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
        cr.execute("""
            UPDATE ir_model
               SET transient=%s
             WHERE model=%s
         RETURNING id
        """, [self._transient, self._name])
        if not cr.rowcount:
            cr.execute('SELECT nextval(%s)', ('ir_model_id_seq',))
            model_id = cr.fetchone()[0]
            cr.execute("INSERT INTO ir_model (id, model, name, info, state, transient) VALUES (%s, %s, %s, %s, %s, %s)",
                       (model_id, self._name, self._description, self.__doc__, 'base', self._transient))
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
        model_fields = sorted(self._fields.items(), key=lambda x: 1 if x[1].type == 'sparse' else 0)
        for (k, f) in model_fields:
            vals = {
                'model_id': model_id,
                'model': self._name,
                'name': k,
                'field_description': f.string,
                'help': f.help or None,
                'ttype': f.type,
                'relation': f.comodel_name or None,
                'index': bool(f.index),
                'copy': bool(f.copy),
                'related': f.related and ".".join(f.related),
                'readonly': bool(f.readonly),
                'required': bool(f.required),
                'selectable': bool(f.search or f.store),
                'translate': bool(getattr(f, 'translate', False)),
                'relation_field': f.type == 'one2many' and f.inverse_name or None,
                'serialization_field_id': None,
                'relation_table': f.type == 'many2many' and f.relation or None,
                'column1': f.type == 'many2many' and f.column1 or None,
                'column2': f.type == 'many2many' and f.column2 or None,
            }
            if getattr(f, 'serialization_field', None):
                # resolve link to serialization_field if specified by name
                serialization_field_id = ir_model_fields_obj.search(cr, SUPERUSER_ID, [('model','=',vals['model']), ('name', '=', f.serialization_field)])
                if not serialization_field_id:
                    raise UserError(_("Serialization field `%s` not found for sparse field `%s`!") % (f.serialization_field, k))
                vals['serialization_field_id'] = serialization_field_id[0]

            if k not in cols:
                cr.execute('select nextval(%s)', ('ir_model_fields_id_seq',))
                id = cr.fetchone()[0]
                vals['id'] = id
                query = "INSERT INTO ir_model_fields (%s) VALUES (%s)" % (
                    ",".join(vals),
                    ",".join("%%(%s)s" % name for name in vals),
                )
                cr.execute(query, vals)
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
                        names = set(vals) - set(['model', 'name'])
                        query = "UPDATE ir_model_fields SET %s WHERE model=%%(model)s and name=%%(name)s" % (
                            ",".join("%s=%%(%s)s" % (name, name) for name in names),
                        )
                        cr.execute(query, vals)
                        break
        self.invalidate_cache(cr, SUPERUSER_ID)

    @api.model
    def _add_field(self, name, field):
        """ Add the given ``field`` under the given ``name`` in the class """
        cls = type(self)
        # add field as an attribute and in cls._fields (for reflection)
        if not isinstance(getattr(cls, name, field), Field):
            _logger.warning("In model %r, field %r overriding existing value", cls._name, name)
        setattr(cls, name, field)
        cls._fields[name] = field

        # basic setup of field
        field.setup_base(self, name)

        # cls._columns will be updated once fields are fully set up

    @api.model
    def _pop_field(self, name):
        """ Remove the field with the given ``name`` from the model.
            This method should only be used for manual fields.
        """
        cls = type(self)
        field = cls._fields.pop(name)
        cls._columns.pop(name, None)
        if hasattr(cls, name):
            delattr(cls, name)
        return field

    @api.model
    def _add_magic_fields(self):
        """ Introduce magic fields on the current class

        * id is a "normal" field (with a specific getter)
        * create_uid, create_date, write_uid and write_date have become
          "normal" fields
        * $CONCURRENCY_CHECK_FIELD is a computed field with its computing
          method defined dynamically. Uses ``str(datetime.datetime.utcnow())``
          to get the same structure as the previous
          ``(now() at time zone 'UTC')::timestamp``::

              # select (now() at time zone 'UTC')::timestamp;
                        timezone
              ----------------------------
               2013-06-18 08:30:37.292809

              >>> str(datetime.datetime.utcnow())
              '2013-06-18 08:31:32.821177'
        """
        def add(name, field):
            """ add ``field`` with the given ``name`` if it does not exist yet """
            if name not in self._fields:
                self._add_field(name, field)

        # cyclic import
        from . import fields

        # this field 'id' must override any other column or field
        self._add_field('id', fields.Id(automatic=True))

        add('display_name', fields.Char(string='Display Name', automatic=True,
            compute='_compute_display_name'))

        if self._log_access:
            add('create_uid', fields.Many2one('res.users', string='Created by', automatic=True))
            add('create_date', fields.Datetime(string='Created on', automatic=True))
            add('write_uid', fields.Many2one('res.users', string='Last Updated by', automatic=True))
            add('write_date', fields.Datetime(string='Last Updated on', automatic=True))
            last_modified_name = 'compute_concurrency_field_with_access'
        else:
            last_modified_name = 'compute_concurrency_field'

        # this field must override any other column or field
        self._add_field(self.CONCURRENCY_CHECK_FIELD, fields.Datetime(
            string='Last Modified on', compute=last_modified_name, automatic=True))

    @api.one
    def compute_concurrency_field(self):
        self[self.CONCURRENCY_CHECK_FIELD] = \
            datetime.datetime.utcnow().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    @api.one
    @api.depends('create_date', 'write_date')
    def compute_concurrency_field_with_access(self):
        self[self.CONCURRENCY_CHECK_FIELD] = \
            self.write_date or self.create_date or \
            datetime.datetime.utcnow().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    #
    # Goal: try to apply inheritance at the instantiation level and
    #       put objects in the pool var
    #
    @classmethod
    def _build_model(cls, pool, cr):
        """ Instantiate a given model.

        This class method instantiates the class of some model (i.e. a class
        deriving from osv or osv_memory). The class might be the class passed
        in argument or, if it inherits from another class, a class constructed
        by combining the two classes.

        """

        # The model's class inherits from cls and the classes of the inherited
        # models. All those classes are combined in a flat hierarchy:
        #
        #         Model                 the base class of all models
        #        /  |  \
        #      cls  c2  c1              the classes defined in modules
        #        \  |  /
        #       ModelClass              the final class of the model
        #        /  |  \
        #     model   recordset ...     the class' instances
        #
        # The registry contains the instance ``model``. Its class, ``ModelClass``,
        # carries inferred metadata that is shared between all the model's
        # instances for this registry only. When we '_inherit' from another
        # model, we do not inherit its ``ModelClass``, but this class' parents.
        # This is a limitation of the inheritance mechanism.

        # Keep links to non-inherited constraints in cls; this is useful for
        # instance when exporting translations
        cls._local_constraints = cls.__dict__.get('_constraints', [])
        cls._local_sql_constraints = cls.__dict__.get('_sql_constraints', [])

        # determine inherited models
        parents = getattr(cls, '_inherit', [])
        parents = [parents] if isinstance(parents, basestring) else (parents or [])

        # determine the model's name
        name = cls._name or (len(parents) == 1 and parents[0]) or cls.__name__

        # determine the module that introduced the model
        original_module = pool[name]._original_module if name in parents else cls._module

        # determine all the classes the model should inherit from
        bases = [cls]
        hierarchy = cls
        for parent in parents:
            if parent not in pool:
                raise TypeError('The model "%s" specifies an unexisting parent class "%s"\n'
                    'You may need to add a dependency on the parent class\' module.' % (name, parent))
            parent_class = type(pool[parent])
            bases += parent_class.__bases__
            hierarchy = type(name, (hierarchy, parent_class), {'_register': False})

        # order bases following the mro of class hierarchy
        bases = [base for base in hierarchy.mro() if base in bases]

        # determine the attributes of the model's class
        inherits = {}
        depends = {}
        constraints = {}
        sql_constraints = []

        for base in reversed(bases):
            inherits.update(base._inherits)

            for mname, fnames in base._depends.iteritems():
                depends[mname] = depends.get(mname, []) + fnames

            for cons in base._constraints:
                # cons may override a constraint with the same function name
                constraints[getattr(cons[0], '__name__', id(cons[0]))] = cons

            sql_constraints += base._sql_constraints

        # build the actual class of the model
        ModelClass = type(name, tuple(bases), {
            '_name': name,
            '_register': False,
            '_columns': {},             # recomputed in _setup_fields()
            '_defaults': {},            # recomputed in _setup_base()
            '_fields': {},              # idem
            '_inherits': inherits,
            '_depends': depends,
            '_constraints': constraints.values(),
            '_sql_constraints': sql_constraints,
            '_original_module': original_module,
        })

        # instantiate the model, and initialize it
        model = object.__new__(ModelClass)
        model.__init__(pool, cr)
        return model

    @classmethod
    def _init_function_fields(cls, pool, cr):
        # initialize the list of non-stored function fields for this model
        pool._pure_function_fields[cls._name] = []

        # process store of low-level function fields
        for fname, column in cls._columns.iteritems():
            # filter out existing store about this field
            pool._store_function[cls._name] = [
                stored
                for stored in pool._store_function.get(cls._name, [])
                if (stored[0], stored[1]) != (cls._name, fname)
            ]
            if not isinstance(column, fields.function):
                continue
            if not column.store:
                # register it on the pool for invalidation
                pool._pure_function_fields[cls._name].append(fname)
                continue
            # process store parameter
            store = column.store
            if store is True:
                get_ids = lambda self, cr, uid, ids, c={}: ids
                store = {cls._name: (get_ids, None, column.priority, None)}
            for model, spec in store.iteritems():
                if len(spec) == 4:
                    (fnct, fields2, order, length) = spec
                elif len(spec) == 3:
                    (fnct, fields2, order) = spec
                    length = None
                else:
                    raise UserError(_('Invalid function definition %s in object %s !\nYou must use the definition: store={object:(fnct, fields, priority, time length)}.') % (fname, cls._name))
                pool._store_function.setdefault(model, [])
                t = (cls._name, fname, fnct, tuple(fields2) if fields2 else None, order, length)
                if t not in pool._store_function[model]:
                    pool._store_function[model].append(t)
                    pool._store_function[model].sort(key=lambda x: x[4])

    @api.model
    def _add_manual_fields(self, partial):
        manual_fields = self.pool.get_manual_fields(self._cr, self._name)

        for name, field in manual_fields.iteritems():
            if name in self._fields:
                continue
            attrs = {
                'manual': True,
                'string': field['field_description'],
                'help': field['help'],
                'index': bool(field['index']),
                'copy': bool(field['copy']),
                'related': field['related'],
                'required': bool(field['required']),
                'readonly': bool(field['readonly']),
            }
            # FIXME: ignore field['serialization_field_id']
            if field['ttype'] in ('char', 'text', 'html'):
                attrs['translate'] = bool(field['translate'])
                attrs['size'] = field['size'] or None
            elif field['ttype'] in ('selection', 'reference'):
                attrs['selection'] = eval(field['selection'])
            elif field['ttype'] == 'many2one':
                if partial and field['relation'] not in self.pool:
                    continue
                attrs['comodel_name'] = field['relation']
                attrs['ondelete'] = field['on_delete']
                attrs['domain'] = eval(field['domain']) if field['domain'] else None
            elif field['ttype'] == 'one2many':
                if partial and not (
                    field['relation'] in self.pool and (
                        field['relation_field'] in self.pool[field['relation']]._fields or
                        field['relation_field'] in self.pool.get_manual_fields(self._cr, field['relation'])
                )):
                    continue
                attrs['comodel_name'] = field['relation']
                attrs['inverse_name'] = field['relation_field']
                attrs['domain'] = eval(field['domain']) if field['domain'] else None
            elif field['ttype'] == 'many2many':
                if partial and field['relation'] not in self.pool:
                    continue
                attrs['comodel_name'] = field['relation']
                rel, col1, col2 = self.env['ir.model.fields']._custom_many2many_names(field['model'], field['relation'])
                attrs['relation'] = field['relation_table'] or rel
                attrs['column1'] = field['column1'] or col1
                attrs['column2'] = field['column2'] or col2
                attrs['domain'] = eval(field['domain']) if field['domain'] else None
            # add compute function if given
            if field['compute']:
                attrs['compute'] = make_compute(field['compute'], field['depends'])
            self._add_field(name, Field.by_type[field['ttype']](**attrs))

    @classmethod
    def _init_constraints_onchanges(cls):
        # store sql constraint error messages
        for (key, _, msg) in cls._sql_constraints:
            cls.pool._sql_error[cls._table + '_' + key] = msg

    @property
    def _constraint_methods(self):
        """ Return a list of methods implementing Python constraints. """
        def is_constraint(func):
            return callable(func) and hasattr(func, '_constrains')

        cls = type(self)
        methods = []
        for attr, func in getmembers(cls, is_constraint):
            for name in func._constrains:
                field = cls._fields.get(name)
                if not field:
                    _logger.warning("method %s.%s: @constrains parameter %r is not a field name", cls._name, attr, name)
                elif not (field.store or field.column and field.column._fnct_inv):
                    _logger.warning("method %s.%s: @constrains parameter %r is not writeable", cls._name, attr, name)
            methods.append(func)

        # optimization: memoize result on cls, it will not be recomputed
        cls._constraint_methods = methods
        return methods

    @property
    def _onchange_methods(self):
        """ Return a dictionary mapping field names to onchange methods. """
        def is_onchange(func):
            return callable(func) and hasattr(func, '_onchange')

        cls = type(self)
        methods = defaultdict(list)
        for attr, func in getmembers(cls, is_onchange):
            for name in func._onchange:
                if name not in cls._fields:
                    _logger.warning("@onchange%r parameters must be field names", func._onchange)
                methods[name].append(func)

        # optimization: memoize result on cls, it will not be recomputed
        cls._onchange_methods = methods
        return methods

    def __new__(cls):
        # In the past, this method was registering the model class in the server.
        # This job is now done entirely by the metaclass MetaModel.
        #
        # Do not create an instance here.  Model instances are created by method
        # _build_model().
        return None

    def __init__(self, pool, cr):
        """ Initialize a model and make it part of the given registry.

        - copy the stored fields' functions in the registry,
        - retrieve custom fields and add them in the model,
        - ensure there is a many2one for each _inherits'd parent,
        - update the children's _columns,
        - give a chance to each field to initialize itself.

        """
        cls = type(self)

        # link the class to the registry, and update the registry
        cls.pool = pool
        cls._model = self              # backward compatibility
        pool.add(cls._name, self)

        # determine description, table, sequence and log_access
        if not cls._description:
            cls._description = cls._name
        if not cls._table:
            cls._table = cls._name.replace('.', '_')
        if not cls._sequence:
            cls._sequence = cls._table + '_id_seq'
        if not hasattr(cls, '_log_access'):
            # If _log_access is not specified, it is the same value as _auto.
            cls._log_access = cls._auto

        check_pg_name(cls._table)

        # Transience
        if cls.is_transient():
            cls._transient_check_count = 0
            cls._transient_max_count = config.get('osv_memory_count_limit')
            cls._transient_max_hours = config.get('osv_memory_age_limit')
            assert cls._log_access, \
                "TransientModels must have log_access turned on, " \
                "in order to implement their access rights policy"

    @api.model
    @ormcache()
    def _is_an_ordinary_table(self):
        self.env.cr.execute("""\
            SELECT  1
            FROM    pg_class
            WHERE   relname = %s
            AND     relkind = %s""", [self._table, 'r'])
        return bool(self.env.cr.fetchone())

    def __export_xml_id(self):
        """ Return a valid xml_id for the record ``self``. """
        if not self._is_an_ordinary_table():
            raise Exception(
                "You can not export the column ID of model %s, because the "
                "table %s is not an ordinary table."
                % (self._name, self._table))
        ir_model_data = self.sudo().env['ir.model.data']
        data = ir_model_data.search([('model', '=', self._name), ('res_id', '=', self.id)])
        if data:
            if data[0].module:
                return '%s.%s' % (data[0].module, data[0].name)
            else:
                return data[0].name
        else:
            postfix = 0
            name = '%s_%s' % (self._table, self.id)
            while ir_model_data.search([('module', '=', '__export__'), ('name', '=', name)]):
                postfix += 1
                name = '%s_%s_%s' % (self._table, self.id, postfix)
            ir_model_data.create({
                'model': self._name,
                'res_id': self.id,
                'module': '__export__',
                'name': name,
            })
            return '__export__.' + name

    @api.multi
    def __export_rows(self, fields):
        """ Export fields of the records in ``self``.

            :param fields: list of lists of fields to traverse
            :return: list of lists of corresponding values
        """
        lines = []
        for record in self:
            # main line of record, initially empty
            current = [''] * len(fields)
            lines.append(current)

            # list of primary fields followed by secondary field(s)
            primary_done = []

            # process column by column
            for i, path in enumerate(fields):
                if not path:
                    continue

                name = path[0]
                if name in primary_done:
                    continue

                if name == '.id':
                    current[i] = str(record.id)
                elif name == 'id':
                    current[i] = record.__export_xml_id()
                else:
                    field = record._fields[name]
                    value = record[name]

                    # this part could be simpler, but it has to be done this way
                    # in order to reproduce the former behavior
                    if not isinstance(value, BaseModel):
                        current[i] = field.convert_to_export(value, self.env)
                    else:
                        primary_done.append(name)

                        # This is a special case, its strange behavior is intended!
                        if field.type == 'many2many' and len(path) > 1 and path[1] == 'id':
                            xml_ids = [r.__export_xml_id() for r in value]
                            current[i] = ','.join(xml_ids) or False
                            continue

                        # recursively export the fields that follow name
                        fields2 = [(p[1:] if p and p[0] == name else []) for p in fields]
                        lines2 = value.__export_rows(fields2)
                        if lines2:
                            # merge first line with record's main line
                            for j, val in enumerate(lines2[0]):
                                if val or isinstance(val, bool):
                                    current[j] = val
                            # check value of current field
                            if not current[i] and not isinstance(current[i], bool):
                                # assign xml_ids, and forget about remaining lines
                                xml_ids = [item[1] for item in value.name_get()]
                                current[i] = ','.join(xml_ids)
                            else:
                                # append the other lines at the end
                                lines += lines2[1:]
                        else:
                            current[i] = False

        return lines

    @api.multi
    def export_data(self, fields_to_export, raw_data=False):
        """ Export fields for selected objects

            :param fields_to_export: list of fields
            :param raw_data: True to return value in native Python type
            :rtype: dictionary with a *datas* matrix

            This method is used when exporting data via client menu
        """
        fields_to_export = map(fix_import_export_id_paths, fields_to_export)
        if raw_data:
            self = self.with_context(export_raw_data=True)
        return {'datas': self.__export_rows(fields_to_export)}

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
        if context is None:
            context = {}
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
            except Exception, e:
                message = (_('Unknown error during import:') +
                           ' %s: %s' % (type(e), unicode(e)))
                moreinfo = _('Resolve other errors first')
                messages.append(dict(info, type='error',
                                     message=message,
                                     moreinfo=moreinfo))
                # Failed for some reason, perhaps due to invalid data supplied,
                # rollback savepoint and keep going
                cr.execute('ROLLBACK TO SAVEPOINT model_load_save')
        if any(message['type'] == 'error' for message in messages):
            cr.execute('ROLLBACK TO SAVEPOINT model_load')
            ids = False

        if ids and context.get('defer_parent_store_computation'):
            self._parent_store_compute(cr)

        return {'ids': ids, 'messages': messages}

    def _add_fake_fields(self, cr, uid, fields, context=None):
        from openerp.fields import Char, Integer
        fields[None] = Char('rec_name')
        fields['id'] = Char('External ID')
        fields['.id'] = Integer('Database ID')
        return fields

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
        fields = dict(self._fields)
        # Fake fields to avoid special cases in extractor
        fields = self._add_fake_fields(cr, uid, fields, context=context)
        # m2o fields can't be on multiple lines so exclude them from the
        # is_relational field rows filter, but special-case it later on to
        # be handled with relational fields (as it can have subfields)
        is_relational = lambda field: fields[field].relational
        get_o2m_values = itemgetter_tuple(
            [index for index, field in enumerate(fields_)
                   if fields[field[0]].type == 'one2many'])
        get_nono2m_values = itemgetter_tuple(
            [index for index, field in enumerate(fields_)
                   if fields[field[0]].type != 'one2many'])
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
                # FIXME: how to not use _obj without relying on fields_get?
                Model = self.pool[fields[relfield].comodel_name]

                # get only cells for this sub-field, should be strictly
                # non-empty, field path [None] is for name_get field
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
        Translation = self.pool['ir.translation']
        fields = dict(self._fields)
        field_names = {name: field.string for name, field in fields.iteritems()}
        if context.get('lang'):
            field_names.update(
                Translation.get_field_string(cr, uid, self._name, context=context)
            )

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

    @api.multi
    def _validate_fields(self, field_names):
        field_names = set(field_names)

        # old-style constraint methods
        trans = self.env['ir.translation']
        cr, uid, context = self.env.args
        ids = self.ids
        errors = []
        for fun, msg, names in self._constraints:
            try:
                # validation must be context-independent; call ``fun`` without context
                valid = names and not (set(names) & field_names)
                valid = valid or fun(self._model, cr, uid, ids)
                extra_error = None
            except Exception, e:
                _logger.debug('Exception while validating constraint', exc_info=True)
                valid = False
                extra_error = tools.ustr(e)
            if not valid:
                if callable(msg):
                    res_msg = msg(self._model, cr, uid, ids, context=context)
                    if isinstance(res_msg, tuple):
                        template, params = res_msg
                        res_msg = template % params
                else:
                    res_msg = trans._get_source(self._name, 'constraint', self.env.lang, msg)
                if extra_error:
                    res_msg += "\n\n%s\n%s" % (_('Error details:'), extra_error)
                errors.append(res_msg)
        if errors:
            raise ValidationError('\n'.join(errors))

        # new-style constraint methods
        for check in self._constraint_methods:
            if set(check._constrains) & field_names:
                try:
                    check(self)
                except ValidationError, e:
                    raise
                except Exception, e:
                    raise ValidationError("%s\n\n%s" % (_("Error while validating constraint"), tools.ustr(e)))

    @api.model
    def default_get(self, fields_list):
        """ default_get(fields) -> default_values

        Return default values for the fields in ``fields_list``. Default
        values are determined by the context, user defaults, and the model
        itself.

        :param fields_list: a list of field names
        :return: a dictionary mapping each field name to its corresponding
            default value, if it has one.

        """
        # trigger view init hook
        self.view_init(fields_list)

        defaults = {}
        parent_fields = defaultdict(list)

        for name in fields_list:
            # 1. look up context
            key = 'default_' + name
            if key in self._context:
                defaults[name] = self._context[key]
                continue

            # 2. look up ir_values
            #    Note: performance is good, because get_defaults_dict is cached!
            ir_values_dict = self.env['ir.values'].get_defaults_dict(self._name)
            if name in ir_values_dict:
                defaults[name] = ir_values_dict[name]
                continue

            field = self._fields.get(name)

            # 3. look up property fields
            #    TODO: get rid of this one
            if field and field.company_dependent:
                defaults[name] = self.env['ir.property'].get(name, self._name)
                continue

            # 4. look up field.default
            if field and field.default:
                defaults[name] = field.default(self)
                continue

            # 5. delegate to parent model
            if field and field.inherited:
                field = field.related_field
                parent_fields[field.model_name].append(field.name)

        # convert default values to the right format
        defaults = self._convert_to_cache(defaults, validate=False)
        defaults = self._convert_to_write(defaults)

        # add default values for inherited fields
        for model, names in parent_fields.iteritems():
            defaults.update(self.env[model].default_get(names))

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
        from openerp.http import request
        Users = self.pool['res.users']
        for group_ext_id in groups.split(','):
            group_ext_id = group_ext_id.strip()
            if group_ext_id == 'base.group_no_one':
                # check: the group_no_one is effective in debug mode only
                if Users.has_group(cr, uid, group_ext_id) and request and request.debug:
                    return True
            else:
                if Users.has_group(cr, uid, group_ext_id):
                    return True
        return False

    def _get_default_form_view(self, cr, user, context=None):
        """ Generates a default single-line form view using all fields
        of the current model.

        :param cr: database cursor
        :param int user: user id
        :param dict context: connection context
        :returns: a form view as an lxml document
        :rtype: etree._Element
        """
        view = etree.Element('form', string=self._description)
        group = etree.SubElement(view, 'group', col="4")
        for fname, field in self._fields.iteritems():
            if field.automatic:
                continue

            etree.SubElement(group, 'field', name=fname)
            if field.type == 'text':
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

    def _get_default_pivot_view(self, cr, user, context=None):
        view = etree.Element('pivot', string=self._description)
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
                raise UserError(_("Insufficient fields for Calendar View!"))
        view.set('date_start', self._date_name)

        set_first_of(["user_id", "partner_id", "x_user_id", "x_partner_id"],
                     self._columns, 'color')

        if not set_first_of(["date_stop", "date_end", "x_date_stop", "x_date_end"],
                            self._columns, 'date_stop'):
            if not set_first_of(["date_delay", "planned_hours", "x_date_delay", "x_planned_hours"],
                                self._columns, 'date_delay'):
                raise UserError(_("Insufficient fields to generate a Calendar View for %s, missing a date_stop or a date_delay") % self._name)

        return view

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """ fields_view_get([view_id | view_type='form'])

        Get the detailed composition of the requested view like fields, model, view architecture

        :param view_id: id of the view or None
        :param view_type: type of the view to return if view_id is None ('form', 'tree', ...)
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
            # override context from postprocessing
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
                raise UserError(_("No default view of type '%s' could be found !") % view_type)

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
            resprint = ir_values_obj.get_actions(cr, uid, 'client_print_multi', self._name, context=context)
            resaction = ir_values_obj.get_actions(cr, uid, 'client_action_multi', self._name, context=context)
            resrelate = ir_values_obj.get_actions(cr, uid, 'client_action_relate', self._name, context=context)
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
            'context': context,
        }

    def get_access_action(self, cr, uid, ids, context=None):
        """ Return an action to open the document. This method is meant to be
        overridden in addons that want to give specific access to the document.
        By default it opens the formview of the document.

        :param int id: id of the document to open
        """
        return self.get_formview_action(cr, uid, ids[0], context=context)

    def _view_look_dom_arch(self, cr, uid, node, view_id, context=None):
        return self.pool['ir.ui.view'].postprocess_and_fields(
            cr, uid, self._name, node, view_id, context=context)

    def search_count(self, cr, user, args, context=None):
        """ search_count(args) -> int

        Returns the number of records in the current model matching :ref:`the
        provided domain <reference/orm/domains>`.
        """
        res = self.search(cr, user, args, context=context, count=True)
        if isinstance(res, list):
            return len(res)
        return res

    @api.returns('self',
        upgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False: value if count else self.browse(value),
        downgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False: value if count else value.ids)
    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        """ search(args[, offset=0][, limit=None][, order=None][, count=False])

        Searches for records based on the ``args``
        :ref:`search domain <reference/orm/domains>`.

        :param args: :ref:`A search domain <reference/orm/domains>`. Use an empty
                     list to match all records.
        :param int offset: number of results to ignore (default: none)
        :param int limit: maximum number of records to return (default: all)
        :param str order: sort string
        :param bool count: if True, only counts and returns the number of matching records (default: False)
        :returns: at most ``limit`` records matching the search criteria

        :raise AccessError: * if user tries to bypass access rules for read on the requested object.
        """
        return self._search(cr, user, args, offset=offset, limit=limit, order=order, context=context, count=count)

    #
    # display_name, name_get, name_create, name_search
    #

    @api.depends(lambda self: (self._rec_name,) if self._rec_name else ())
    def _compute_display_name(self):
        names = dict(self.name_get())
        for record in self:
            record.display_name = names.get(record.id, False)

    @api.multi
    def name_get(self):
        """ name_get() -> [(id, name), ...]

        Returns a textual representation for the records in ``self``.
        By default this is the value of the ``display_name`` field.

        :return: list of pairs ``(id, text_repr)`` for each records
        :rtype: list(tuple)
        """
        result = []
        name = self._rec_name
        if name in self._fields:
            convert = self._fields[name].convert_to_display_name
            for record in self:
                result.append((record.id, convert(record[name], record)))
        else:
            for record in self:
                result.append((record.id, "%s,%s" % (record._name, record.id)))

        return result

    @api.model
    def name_create(self, name):
        """ name_create(name) -> record

        Create a new record by calling :meth:`~.create` with only one value
        provided: the display name of the new record.

        The new record will be initialized with any default values
        applicable to this model, or provided through the context. The usual
        behavior of :meth:`~.create` applies.

        :param name: display name of the record to create
        :rtype: tuple
        :return: the :meth:`~.name_get` pair value of the created record
        """
        if self._rec_name:
            record = self.create({self._rec_name: name})
            return record.name_get()[0]
        else:
            _logger.warning("Cannot execute name_create, no _rec_name defined on %s", self._name)
            return False

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """ name_search(name='', args=None, operator='ilike', limit=100) -> records

        Search for records that have a display name matching the given
        ``name`` pattern when compared with the given ``operator``, while also
        matching the optional search domain (``args``).

        This is used for example to provide suggestions based on a partial
        value for a relational field. Sometimes be seen as the inverse
        function of :meth:`~.name_get`, but it is not guaranteed to be.

        This method is equivalent to calling :meth:`~.search` with a search
        domain based on ``display_name`` and then :meth:`~.name_get` on the
        result of the search.

        :param str name: the name pattern to match
        :param list args: optional search domain (see :meth:`~.search` for
                          syntax), specifying further restrictions
        :param str operator: domain operator for matching ``name``, such as
                             ``'like'`` or ``'='``.
        :param int limit: optional max number of records to return
        :rtype: list
        :return: list of pairs ``(id, text_repr)`` for all matching records.
        """
        return self._name_search(name, args, operator, limit=limit)

    def _name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100, name_get_uid=None):
        # private implementation of name_search, allows passing a dedicated user
        # for the name_get part to solve some access rights issues
        args = list(args or [])
        # optimize out the default criterion of ``ilike ''`` that matches everything
        if not self._rec_name:
            _logger.warning("Cannot execute name_search, no _rec_name defined on %s", self._name)
        elif not (name == '' and operator == 'ilike'):
            args += [(self._rec_name, operator, name)]
        access_rights_uid = name_get_uid or user
        ids = self._search(cr, user, args, limit=limit, context=context, access_rights_uid=access_rights_uid)
        res = self.name_get(cr, access_rights_uid, ids, context)
        return res

    def _add_missing_default_values(self, cr, uid, values, context=None):
        # avoid overriding inherited values when parent is set
        avoid_tables = []
        for tables, parent_field in self._inherits.items():
            if parent_field in values:
                avoid_tables.append(tables)

        # compute missing fields
        missing_defaults = set()
        for field in self._columns.keys():
            if not field in values:
                missing_defaults.add(field)
        for field in self._inherit_fields.keys():
            if (field not in values) and (self._inherit_fields[field][0] not in avoid_tables):
                missing_defaults.add(field)
        # discard magic fields
        missing_defaults -= set(MAGIC_COLUMNS)

        if missing_defaults:
            # override defaults with the provided values, never allow the other way around
            defaults = self.default_get(cr, uid, list(missing_defaults), context)
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
            self.pool.cache.clear()
            self.pool._any_cache_cleared = True
        except AttributeError:
            pass


    def _read_group_fill_results(self, cr, uid, domain, groupby, remaining_groupbys,
                                 aggregated_fields, count_field,
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
                known_values[grouped_value].update({count_field: left_side[count_field]})
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

    @api.model
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
            if order_field == 'id' or order_field in groupby_fields:

                if self._fields[order_field.split(':')[0]].type == 'many2one':
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

    @api.model
    def _read_group_process_groupby(self, gb, query):
        """
            Helper method to collect important information about groupbys: raw
            field name, type, time information, qualified name, ...
        """
        split = gb.split(':')
        field_type = self._fields[split[0]].type
        gb_function = split[1] if len(split) == 2 else None
        temporal = field_type in ('date', 'datetime')
        tz_convert = field_type == 'datetime' and self._context.get('tz') in pytz.all_timezones
        qualified_field = self._inherits_join_calc(self._table, split[0], query)
        if temporal:
            display_formats = {
                # Careful with week/year formats:
                #  - yyyy (lower) must always be used, *except* for week+year formats
                #  - YYYY (upper) must always be used for week+year format
                #         e.g. 2006-01-01 is W52 2005 in some locales (de_DE),
                #                         and W1 2006 for others
                #
                # Mixing both formats, e.g. 'MMM YYYY' would yield wrong results,
                # such as 2006-01-01 being formatted as "January 2005" in some locales.
                # Cfr: http://babel.pocoo.org/docs/dates/#date-fields
                'day': 'dd MMM yyyy', # yyyy = normal year
                'week': "'W'w YYYY",  # w YYYY = ISO week-year
                'month': 'MMMM yyyy',
                'quarter': 'QQQ yyyy',
                'year': 'yyyy',
            }
            time_intervals = {
                'day': dateutil.relativedelta.relativedelta(days=1),
                'week': datetime.timedelta(days=7),
                'month': dateutil.relativedelta.relativedelta(months=1),
                'quarter': dateutil.relativedelta.relativedelta(months=3),
                'year': dateutil.relativedelta.relativedelta(years=1)
            }
            if tz_convert:
                qualified_field = "timezone('%s', timezone('UTC',%s))" % (self._context.get('tz', 'UTC'), qualified_field)
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
            Helper method to format the data contained in the dictionary data by 
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
        annotated_groupbys = [
            self._read_group_process_groupby(cr, uid, gb, query, context=context)
            for gb in groupby_list
        ]
        groupby_fields = [g['field'] for g in annotated_groupbys]
        order = orderby or ','.join([g for g in groupby_list])
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}

        self._apply_ir_rules(cr, uid, query, 'read', context=context)
        for gb in groupby_fields:
            assert gb in fields, "Fields in 'groupby' must appear in the list of fields to read (perhaps it's missing in the list view?)"
            groupby_def = self._columns.get(gb) or (self._inherit_fields.get(gb) and self._inherit_fields.get(gb)[2])
            assert groupby_def and groupby_def._classic_write, "Fields in 'groupby' must be regular database-persisted fields (no function or related fields), or function fields with store=True"
            if not (gb in self._fields):
                # Don't allow arbitrary values, as this would be a SQL injection vector!
                raise UserError(_('Invalid group_by specification: "%s".\nA group_by specification must be a list of valid fields.') % (gb,))

        aggregated_fields = [
            f for f in fields
            if f not in ('id', 'sequence')
            if f not in groupby_fields
            if f in self._fields
            if self._fields[f].type in ('integer', 'float', 'monetary')
            if getattr(self._fields[f].base_field.column, '_classic_write', False)
        ]

        field_formatter = lambda f: (
            self._fields[f].group_operator or 'sum',
            self._inherits_join_calc(cr, uid, self._table, f, query, context=context),
            f,
        )
        select_terms = ['%s(%s) AS "%s" ' % field_formatter(f) for f in aggregated_fields]

        for gb in annotated_groupbys:
            select_terms.append('%s as "%s" ' % (gb['qualified_field'], gb['groupby']))

        groupby_terms, orderby_terms = self._read_group_prepare(cr, uid, order, aggregated_fields, annotated_groupbys, query, context=context)
        from_clause, where_clause, where_clause_params = query.get_sql()
        if lazy and (len(groupby_fields) >= 2 or not context.get('group_by_no_leaf')):
            count_field = groupby_fields[0] if len(groupby_fields) >= 1 else '_'
        else:
            count_field = '_'
        count_field += '_count'

        prefix_terms = lambda prefix, terms: (prefix + " " + ",".join(terms)) if terms else ''
        prefix_term = lambda prefix, term: ('%s %s' % (prefix, term)) if term else ''

        query = """
            SELECT min("%(table)s".id) AS id, count("%(table)s".id) AS "%(count_field)s" %(extra_fields)s
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
                                                       aggregated_fields, count_field, result, read_group_order=order,
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

    @api.model
    def _inherits_join_calc(self, alias, field, query, implicit=True, outer=False):
        """
        Adds missing table select and join clause(s) to ``query`` for reaching
        the field coming from an '_inherits' parent table (no duplicates).

        :param alias: name of the initial SQL alias
        :param field: name of inherited field to reach
        :param query: query object on which the JOIN should be added
        :return: qualified name of field, to be used in SELECT clause
        """
        # INVARIANT: alias is the SQL alias of model._table in query
        model = self
        while field in model._inherit_fields and field not in model._columns:
            # retrieve the parent model where field is inherited from
            parent_model_name = model._inherit_fields[field][0]
            parent_model = self.env[parent_model_name]
            parent_field = model._inherits[parent_model_name]
            # JOIN parent_model._table AS parent_alias ON alias.parent_field = parent_alias.id
            parent_alias, _ = query.add_join(
                (alias, parent_model._table, parent_field, 'id', parent_field),
                implicit=implicit, outer=outer,
            )
            model, alias = parent_model, parent_alias
        # handle the case where the field is translated
        translate = model._columns[field].translate
        if translate and not callable(translate):
            return model._generate_translated_field(alias, field, query)
        else:
            return '"%s"."%s"' % (alias, field)

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
        self.invalidate_cache(cr, SUPERUSER_ID, ['parent_left', 'parent_right'])
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
                if f._type == 'boolean' or val is not False:
                    cr.execute(update_query, (ss[1](val), key))

    @api.model
    def _check_selection_field_value(self, field, value):
        """ Check whether value is among the valid values for the given
            selection/reference field, and raise an exception if not.
        """
        field = self._fields[field]
        field.convert_to_cache(value, self)

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

    def _save_constraint(self, cr, constraint_name, type, definition):
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
            SELECT type, definition FROM ir_model_constraint, ir_module_module
            WHERE ir_model_constraint.module=ir_module_module.id
                AND ir_model_constraint.name=%s
                AND ir_module_module.name=%s
            """, (constraint_name, self._module))
        constraints = cr.dictfetchone()
        if not constraints:
            cr.execute("""
                INSERT INTO ir_model_constraint
                    (name, date_init, date_update, module, model, type, definition)
                VALUES (%s, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC',
                    (SELECT id FROM ir_module_module WHERE name=%s),
                    (SELECT id FROM ir_model WHERE model=%s), %s, %s)""",
                    (constraint_name, self._module, self._name, type, definition))
        elif constraints['type'] != type or (definition and constraints['definition'] != definition):
            cr.execute("""
                UPDATE ir_model_constraint
                SET date_update=now() AT TIME ZONE 'UTC', type=%s, definition=%s
                WHERE name=%s AND module = (SELECT id FROM ir_module_module WHERE name=%s)""",
                    (type, definition, constraint_name, self._module))

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
            self.invalidate_cache(cr, SUPERUSER_ID)

    # checked version: for direct m2o starting from ``self``
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


    def _set_default_value_on_column(self, cr, column_name, context=None):
        # ideally, we should use default_get(), but it fails due to ir.values
        # not being ready

        # get default value
        default = self._defaults.get(column_name)
        if callable(default):
            default = default(self, cr, SUPERUSER_ID, context)

        column = self._columns[column_name]
        ss = column._symbol_set
        db_default = ss[1](default)
        # Write default if non-NULL, except for booleans for which False means
        # the same as NULL - this saves us an expensive query on large tables.
        write_default = (db_default is not None if column._type != 'boolean'
                            else db_default)
        if write_default:
            _logger.debug("Table '%s': setting default value of new column %s to %r",
                          self._table, column_name, default)
            query = 'UPDATE "%s" SET "%s"=%s WHERE "%s" is NULL' % (
                self._table, column_name, ss[0], column_name)
            cr.execute(query, (db_default,))
            # this is a disgrace
            cr.commit()

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

        # This prevents anything called by this method (in particular default
        # values) from prefetching a field for which the corresponding column
        # has not been added in database yet!
        context = dict(context or {}, prefetch_fields=False)

        # Make sure an environment is available for get_pg_type(). This is
        # because we access column.digits, which retrieves a cursor from
        # existing environments.
        env = api.Environment(cr, SUPERUSER_ID, context)

        store_compute = False
        stored_fields = []              # new-style stored fields with compute
        todo_end = []
        update_custom_fields = context.get('update_custom_fields', False)
        self._field_create(cr, context=context)
        create = not self._table_exist(cr)
        if self._auto:

            if create:
                self._create_table(cr)
                has_rows = False
            else:
                cr.execute('SELECT 1 FROM "%s" LIMIT 1' % self._table)
                has_rows = cr.rowcount

            cr.commit()
            if self._parent_store:
                if not self._parent_columns_exist(cr):
                    self._create_parent_columns(cr)
                    store_compute = True

            self._check_removed_columns(cr, log=False)

            # iterate on the "object columns"
            column_data = self._select_column_data(cr)

            for k, f in self._columns.iteritems():
                if k == 'id': # FIXME: maybe id should be a regular column?
                    continue
                # Don't update custom (also called manual) fields
                if f.manual and not update_custom_fields:
                    continue

                if isinstance(f, fields.one2many):
                    self._o2m_raise_on_missing_reference(cr, f)

                elif isinstance(f, fields.many2many):
                    res = self._m2m_raise_or_create_relation(cr, f)
                    if res and self._fields[k].depends:
                        stored_fields.append(self._fields[k])

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
                                ('float8', 'monetary', get_pg_type(f)[1], '::'+get_pg_type(f)[1]),
                            ]
                            if f_pg_type == 'varchar' and f._type in ('char', 'selection') and f_pg_size and (f.size is None or f_pg_size < f.size):
                                try:
                                    with cr.savepoint():
                                        cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" TYPE %s' % (self._table, k, pg_varchar(f.size)), log_exceptions=False)
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
                                        try:
                                            with cr.savepoint():
                                                cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" TYPE %s' % (self._table, k, c[2]), log_exceptions=False)
                                        except psycopg2.NotSupportedError:
                                            # can't do inplace change -> use a casted temp column
                                            cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO __temp_type_cast' % (self._table, k))
                                            cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, c[2]))
                                            cr.execute('UPDATE "%s" SET "%s"= __temp_type_cast%s' % (self._table, k, c[3]))
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
                                    _schema.warning("Table `%s`: column `%s` has changed type (DB=%s, def=%s), data moved to column `%s`",
                                                    self._table, k, f_pg_type, f._type, newname)

                            # if the field is required and hasn't got a NOT NULL constraint
                            if f.required and f_pg_notnull == 0:
                                if has_rows:
                                    self._set_default_value_on_column(cr, k, context=context)
                                # add the NOT NULL constraint
                                try:
                                    cr.commit()
                                    cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" SET NOT NULL' % (self._table, k), log_exceptions=False)
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
                                if dest_model._auto and dest_model._table != 'ir_actions':
                                    self._m2o_fix_foreign_key(cr, self._table, k, dest_model, f.ondelete)

                    # The field doesn't exist in database. Create it if necessary.
                    else:
                        if f._classic_write:
                            # add the missing field
                            cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, k, get_pg_type(f)[1]))
                            cr.execute("COMMENT ON COLUMN %s.\"%s\" IS %%s" % (self._table, k), (f.string,))
                            _schema.debug("Table '%s': added column '%s' with definition=%s",
                                self._table, k, get_pg_type(f)[1])

                            # initialize it
                            if has_rows:
                                self._set_default_value_on_column(cr, k, context=context)

                            # remember the functions to call for the stored fields
                            if isinstance(f, fields.function):
                                order = 10
                                if f.store is not True: # i.e. if f.store is a dict
                                    order = f.store[f.store.keys()[0]][2]
                                todo_end.append((order, self._update_store, (f, k)))

                            # remember new-style stored fields with compute method
                            if k in self._fields and self._fields[k].depends:
                                stored_fields.append(self._fields[k])

                            # and add constraints if needed
                            if isinstance(f, fields.many2one) or (isinstance(f, fields.function) and f._type == 'many2one' and f.store):
                                if f._obj not in self.pool:
                                    raise ValueError(_('There is no reference available for %s') % (f._obj,))
                                dest_model = self.pool[f._obj]
                                ref = dest_model._table
                                # ir_actions is inherited so foreign key doesn't work on it
                                if dest_model._auto and ref != 'ir_actions':
                                    self._m2o_add_foreign_key_checked(k, dest_model, f.ondelete)
                            if f.select:
                                cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (self._table, k, self._table, k))
                            if f.required:
                                try:
                                    cr.commit()
                                    cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" SET NOT NULL' % (self._table, k))
                                    _schema.debug("Table '%s': column '%s': added a NOT NULL constraint",
                                        self._table, k)
                                except Exception:
                                    msg = "WARNING: unable to set column %s of table %s not null !\n"\
                                        "Try to re-run: openerp-server --update=module\n"\
                                        "If it doesn't work, update records and execute manually:\n"\
                                        "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL"
                                    _logger.warning(msg, k, self._table, self._table, k, exc_info=True)
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

        if stored_fields:
            # trigger computation of new-style stored fields with a compute
            def func(cr):
                fnames = [f.name for f in stored_fields]
                _logger.info("Storing computed values of %s fields %s",
                             self._name, ', '.join(sorted(fnames)))
                recs = self.browse(cr, SUPERUSER_ID, [], {'active_test': False})
                recs = recs.search([])
                if recs:
                    recs.invalidate_cache(fnames, recs.ids)
                    map(recs._recompute_todo, stored_fields)

            todo_end.append((1000, func, ()))

        return todo_end

    def _auto_end(self, cr, context=None):
        """ Create the foreign keys recorded by _auto_init. """
        for t, k, r, d in self._foreign_keys:
            cr.execute('ALTER TABLE "%s" ADD FOREIGN KEY ("%s") REFERENCES "%s" ON DELETE %s' % (t, k, r, d))
            self._save_constraint(cr, "%s_%s_fkey" % (t, k), 'f', False)
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
                    raise UserError(_("There is no reference field '%s' found for '%s'") % (f._fields_id, f._obj))

    def _m2m_raise_or_create_relation(self, cr, f):
        """ Create the table for the relation if necessary.
        Return ``True`` if the relation had to be created.
        """
        m2m_tbl, col1, col2 = f._sql_names(self)
        # do not create relations for custom fields as they do not belong to a module
        # they will be automatically removed when dropping the corresponding ir.model.field
        # table name for custom relation all starts with x_, see __init__
        if not m2m_tbl.startswith('x_'):
            self._save_relation_table(cr, m2m_tbl)
        cr.execute("SELECT relname FROM pg_class WHERE relkind IN ('r','v') AND relname=%s", (m2m_tbl,))
        if not cr.dictfetchall():
            if f._obj not in self.pool:
                raise UserError(_('Many2Many destination model does not exist: `%s`') % (f._obj,))
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

            cr.execute('CREATE INDEX ON "%s" ("%s")' % (m2m_tbl, col1))
            cr.execute('CREATE INDEX ON "%s" ("%s")' % (m2m_tbl, col2))
            cr.execute("COMMENT ON TABLE \"%s\" IS 'RELATION BETWEEN %s AND %s'" % (m2m_tbl, self._table, ref))
            cr.commit()
            _schema.debug("Create table '%s': m2m relation between '%s' and '%s'", m2m_tbl, self._table, ref)
            return True


    def _add_sql_constraints(self, cr):
        """

        Modify this model's database table constraints so they match the one in
        _sql_constraints.

        """
        def unify_cons_text(txt):
            return txt.lower().replace(', ',',').replace(' (','(')

        for (key, con, _) in self._sql_constraints:
            conname = '%s_%s' % (self._table, key)

            # using 1 to get result if no imc but one pgc
            cr.execute("""SELECT definition, 1
                          FROM ir_model_constraint imc
                          RIGHT JOIN pg_constraint pgc
                          ON (pgc.conname = imc.name)
                          WHERE pgc.conname=%s
                          """, (conname, ))
            existing_constraints = cr.dictfetchone()
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
            elif unify_cons_text(con) != existing_constraints['definition']:
                # constraint exists but its definition has changed:
                sql_actions['drop']['execute'] = True
                sql_actions['drop']['msg_ok'] = sql_actions['drop']['msg_ok'] % (existing_constraints['definition'] or '', )
                sql_actions['add']['execute'] = True
                sql_actions['add']['msg_err'] = sql_actions['add']['msg_err'] % (sql_actions['add']['query'], )

            # we need to add the constraint:
            self._save_constraint(cr, conname, 'u', unify_cons_text(con))
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

    @api.model
    def _add_inherited_fields(self):
        """ Determine inherited fields. """
        # determine candidate inherited fields
        fields = {}
        for parent_model, parent_field in self._inherits.iteritems():
            parent = self.env[parent_model]
            for name, field in parent._fields.iteritems():
                # inherited fields are implemented as related fields, with the
                # following specific properties:
                #  - reading inherited fields should not bypass access rights
                #  - copy inherited fields iff their original field is copied
                fields[name] = field.new(
                    inherited=True,
                    related=(parent_field, name),
                    related_sudo=False,
                    copy=field.copy,
                )

        # add inherited fields that are not redefined locally
        for name, field in fields.iteritems():
            if name not in self._fields:
                self._add_field(name, field)

    @classmethod
    def _inherits_reload(cls):
        """ Recompute the _inherit_fields mapping. """
        cls._inherit_fields = struct = {}
        for parent_model, parent_field in cls._inherits.iteritems():
            parent = cls.pool[parent_model]
            parent._inherits_reload()
            for name, column in parent._columns.iteritems():
                struct[name] = (parent_model, parent_field, column, parent_model)
            for name, source in parent._inherit_fields.iteritems():
                struct[name] = (parent_model, parent_field, source[2], source[3])

    @property
    def _all_columns(self):
        """ Returns a dict mapping all fields names (self fields and inherited
        field via _inherits) to a ``column_info`` object giving detailed column
        information. This property is deprecated, use ``_fields`` instead.
        """
        result = {}
        # do not inverse for loops, since local fields may hide inherited ones!
        for k, (parent, m2o, col, original_parent) in self._inherit_fields.iteritems():
            result[k] = fields.column_info(k, col, parent, m2o, original_parent)
        for k, col in self._columns.iteritems():
            result[k] = fields.column_info(k, col)
        return result

    @api.model
    def _inherits_check(self):
        for table, field_name in self._inherits.items():
            field = self._fields.get(field_name)
            if not field:
                _logger.info('Missing many2one field definition for _inherits reference "%s" in "%s", using default one.', field_name, self._name)
                from .fields import Many2one
                field = Many2one(table, string="Automatically created field to link to parent %s" % table, required=True, ondelete="cascade")
                self._add_field(field_name, field)
            elif not field.required or field.ondelete.lower() not in ("cascade", "restrict"):
                _logger.warning('Field definition for _inherits reference "%s" in "%s" must be marked as "required" with ondelete="cascade" or "restrict", forcing it to required + cascade.', field_name, self._name)
                field.required = True
                field.ondelete = "cascade"

        # reflect fields with delegate=True in dictionary self._inherits
        for field in self._fields.itervalues():
            if field.type == 'many2one' and not field.related and field.delegate:
                if not field.required:
                    _logger.warning("Field %s with delegate=True must be required.", field)
                    field.required = True
                if field.ondelete.lower() not in ('cascade', 'restrict'):
                    field.ondelete = 'cascade'
                self._inherits[field.comodel_name] = field.name

    @api.model
    def _prepare_setup(self):
        """ Prepare the setup of the model. """
        type(self)._setup_done = False

    @api.model
    def _setup_base(self, partial):
        """ Determine the inherited and custom fields of the model. """
        cls = type(self)
        if cls._setup_done:
            return

        # 1. determine the proper fields of the model: the fields defined on the
        # class and magic fields, not the inherited or custom ones
        cls0 = cls.pool.model_cache.get(cls.__bases__)
        if cls0:
            # cls0 is either a model class from another registry, or cls itself.
            # The point is that it has the same base classes. We retrieve stuff
            # from cls0 to optimize the setup of cls. cls0 is guaranteed to be
            # properly set up: registries are loaded under a global lock,
            # therefore two registries are never set up at the same time.

            # remove fields that are not proper to cls
            for name in set(cls._fields) - cls0._proper_fields:
                delattr(cls, name)
                cls._fields.pop(name, None)
                cls._defaults.pop(name, None)
            # collect proper fields on cls0, and add them on cls
            for name in cls0._proper_fields:
                field = cls0._fields[name]
                if not field.related:
                    # regular fields are shared, and their default value copied
                    self._add_field(name, field)
                    if name in cls0._defaults:
                        cls._defaults[name] = cls0._defaults[name]
                else:
                    # related fields are copied, and setup from scratch
                    self._add_field(name, field.new(**field.args))
            cls._proper_fields = set(cls._fields)

        else:
            # retrieve fields from parent classes, and duplicate them on cls to
            # avoid clashes with inheritance between different models
            cls._fields = {}
            cls._defaults = {}
            for name, field in getmembers(cls, Field.__instancecheck__):
                self._add_field(name, field.new())
            self._add_magic_fields()
            cls._proper_fields = set(cls._fields)

            cls.pool.model_cache[cls.__bases__] = cls

        # 2. add custom fields
        self._add_manual_fields(partial)

        # 3. make sure that parent models determine their own fields, then add
        # inherited fields to cls
        self._inherits_check()
        for parent in self._inherits:
            self.env[parent]._setup_base(partial)
        self._add_inherited_fields()

        # 4. initialize more field metadata
        cls._field_computed = {}            # fields computed with the same method
        cls._field_inverses = Collector()   # inverse fields for related fields
        cls._field_triggers = Collector()   # list of (field, path) to invalidate

        cls._setup_done = True

    @api.model
    def _setup_fields(self, partial):
        """ Setup the fields, except for recomputation triggers. """
        cls = type(self)

        # set up fields, and determine their corresponding column
        cls._columns = {}
        bad_fields = []
        for name, field in cls._fields.iteritems():
            try:
                field.setup_full(self)
            except Exception:
                if partial and field.manual:
                    # Something goes wrong when setup a manual field.
                    # This can happen with related fields using another manual many2one field
                    # that hasn't been loaded because the comodel does not exist yet.
                    # This can also be a manual function field depending on not loaded fields yet.
                    bad_fields.append(name)
                    continue
                raise
            column = field.to_column()
            if column:
                cls._columns[name] = column

        for name in bad_fields:
            del cls._fields[name]
            delattr(cls, name)

        # map each field to the fields computed with the same method
        groups = defaultdict(list)
        for field in cls._fields.itervalues():
            if field.compute:
                cls._field_computed[field] = group = groups[field.compute]
                group.append(field)
        for fields in groups.itervalues():
            compute_sudo = fields[0].compute_sudo
            if not all(field.compute_sudo == compute_sudo for field in fields):
                _logger.warning("%s: inconsistent 'compute_sudo' for computed fields: %s",
                                self._name, ", ".join(field.name for field in fields))

    @api.model
    def _setup_complete(self):
        """ Setup recomputation triggers, and complete the model setup. """
        cls = type(self)

        # set up field triggers
        for field in cls._fields.itervalues():
            # dependencies of custom fields may not exist; ignore that case
            exceptions = (Exception,) if field.manual else ()
            with tools.ignore(*exceptions):
                field.setup_triggers(self.env)

        # add invalidation triggers on model dependencies
        if cls._depends:
            for model_name, field_names in cls._depends.iteritems():
                model = self.env[model_name]
                for field_name in field_names:
                    field = model._fields[field_name]
                    for dependent in cls._fields.itervalues():
                        model._field_triggers.add(field, (dependent, None))

        # determine old-api structures about inherited fields
        cls._inherits_reload()

        # register stuff about low-level function fields
        cls._init_function_fields(cls.pool, self._cr)

        # register constraints and onchange methods
        cls._init_constraints_onchanges()

        # check defaults
        for name in cls._defaults:
            assert name in cls._fields, \
                "Model %s has a default for nonexiting field %s" % (cls._name, name)

        # validate rec_name
        if cls._rec_name:
            assert cls._rec_name in cls._fields, \
                "Invalid rec_name %s for model %s" % (cls._rec_name, cls._name)
        elif 'name' in cls._fields:
            cls._rec_name = 'name'
        elif 'x_name' in cls._fields:
            cls._rec_name = 'x_name'

    def fields_get(self, cr, user, allfields=None, context=None, write_access=True, attributes=None):
        """ fields_get([fields][, attributes])

        Return the definition of each field.

        The returned value is a dictionary (indiced by field name) of
        dictionaries. The _inherits'd fields are included. The string, help,
        and selection (if present) attributes are translated.

        :param allfields: list of fields to document, all if empty or not provided
        :param attributes: list of description attributes to return for each field, all if empty or not provided
        """
        recs = self.browse(cr, user, [], context)

        has_access = functools.partial(recs.check_access_rights, raise_exception=False)
        readonly = not (has_access('write') or has_access('create'))

        res = {}
        for fname, field in self._fields.iteritems():
            if allfields and fname not in allfields:
                continue
            if field.groups and not recs.user_has_groups(field.groups):
                continue

            description = field.get_description(recs.env)
            if readonly:
                description['readonly'] = True
                description['states'] = {}
            if attributes:
                description = {k: v for k, v in description.iteritems()
                               if k in attributes}
            res[fname] = description

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
        if user == SUPERUSER_ID:
            return fields or list(self._fields)

        def valid(fname):
            """ determine whether user has access to field ``fname`` """
            field = self._fields.get(fname)
            if field and field.groups:
                return self.user_has_groups(cr, user, groups=field.groups, context=context)
            else:
                return True

        if not fields:
            fields = filter(valid, self._fields)
        else:
            invalid_fields = set(filter(lambda name: not valid(name), fields))
            if invalid_fields:
                _logger.info('Access Denied by ACLs for operation: %s, uid: %s, model: %s, fields: %s',
                    operation, user, self._name, ', '.join(invalid_fields))
                raise AccessError(_('The requested operation cannot be completed due to security restrictions. '
                                        'Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % \
                                        (self._description, operation))

        return fields

    # add explicit old-style implementation to read()
    @api.v7
    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        records = self.browse(cr, user, ids, context)
        result = BaseModel.read(records, fields, load=load)
        return result if isinstance(ids, list) else (bool(result) and result[0])

    # new-style implementation of read()
    @api.v8
    def read(self, fields=None, load='_classic_read'):
        """ read([fields])

        Reads the requested fields for the records in ``self``, low-level/RPC
        method. In Python code, prefer :meth:`~.browse`.

        :param fields: list of field names to return (default is all fields)
        :return: a list of dictionaries mapping field names to their values,
                 with one dictionary per record
        :raise AccessError: if user has no read rights on some of the given
                records
        """
        # check access rights
        self.check_access_rights('read')
        fields = self.check_field_access_rights('read', fields)

        # split fields into stored and computed fields
        stored, inherited, computed = [], [], []
        for name in fields:
            if name in self._columns:
                stored.append(name)
            elif name in self._fields:
                computed.append(name)
                field = self._fields[name]
                if field.inherited and field.base_field.column:
                    inherited.append(name)
            else:
                _logger.warning("%s.read() with unknown field '%s'", self._name, name)

        # fetch stored fields from the database to the cache
        self._read_from_database(stored, inherited)

        # retrieve results from records; this takes values from the cache and
        # computes remaining fields
        result = []
        name_fields = [(name, self._fields[name]) for name in (stored + computed)]
        use_name_get = (load == '_classic_read')
        for record in self:
            try:
                values = {'id': record.id}
                for name, field in name_fields:
                    values[name] = field.convert_to_read(record[name], use_name_get)
                result.append(values)
            except MissingError:
                pass

        return result

    @api.multi
    def _prefetch_field(self, field):
        """ Read from the database in order to fetch ``field`` (:class:`Field`
            instance) for ``self`` in cache.
        """
        # fetch the records of this model without field_name in their cache
        records = self._in_cache_without(field)

        # determine which fields can be prefetched
        fs = {field}
        if self._context.get('prefetch_fields', True) and field.column._prefetch:
            fs.update(
                f
                for f in self._fields.itervalues()
                # select stored fields that can be prefetched
                if f.store and f.column._prefetch
                # discard fields with groups that the user may not access
                if not (f.groups and not self.user_has_groups(f.groups))
                # discard fields that must be recomputed
                if not (f.compute and self.env.field_todo(f))
            )
        elif field.column._multi:
            # prefetch all function fields with the same value for 'multi'
            multi = field.column._multi
            fs.update(
                f
                for f in self._fields.itervalues()
                # select stored fields with the same multi
                if f.column and f.column._multi == multi
                # discard fields with groups that the user may not access
                if not (f.groups and not self.user_has_groups(f.groups))
            )

        # special case: discard records to recompute for field
        records -= self.env.field_todo(field)

        # in onchange mode, discard computed fields and fields in cache
        if self.env.in_onchange:
            for f in list(fs):
                if f.compute or (f.name in self._cache):
                    fs.discard(f)
                else:
                    records &= self._in_cache_without(f)

        # prefetch at most PREFETCH_MAX records
        if len(records) > PREFETCH_MAX:
            records = records[:PREFETCH_MAX] | self

        # fetch records with read()
        assert self in records and field in fs
        result = []
        try:
            result = records.read([f.name for f in fs], load='_classic_write')
        except AccessError:
            # not all records may be accessible, try with only current record
            result = self.read([f.name for f in fs], load='_classic_write')

        # check the cache, and update it if necessary
        if field not in self._cache:
            for values in result:
                record = self.browse(values.pop('id'))
                record._cache.update(record._convert_to_cache(values, validate=False))
            if not self._cache.contains(field):
                e = AccessError("No value found for %s.%s" % (self, field.name))
                self._cache[field] = FailedValue(e)

    @api.multi
    def _read_from_database(self, field_names, inherited_field_names=[]):
        """ Read the given fields of the records in ``self`` from the database,
            and store them in cache. Access errors are also stored in cache.

            :param field_names: list of column names of model ``self``; all those
                fields are guaranteed to be read
            :param inherited_field_names: list of column names from parent
                models; some of those fields may not be read
        """
        env = self.env
        cr, user, context = env.args

        # make a query object for selecting ids, and apply security rules to it
        param_ids = object()
        query = Query(['"%s"' % self._table], ['"%s".id IN %%s' % self._table], [param_ids])
        self._apply_ir_rules(query, 'read')
        order_str = self._generate_order_by(None, query)

        # determine the fields that are stored as columns in tables;
        fields = map(self._fields.get, field_names + inherited_field_names)
        fields_pre = [
            field
            for field in fields
            if field.base_field.column._classic_write
            if not (field.inherited and callable(field.base_field.column.translate))
        ]

        # the query may involve several tables: we need fully-qualified names
        def qualify(field):
            col = field.name
            res = self._inherits_join_calc(self._table, field.name, query)
            if field.type == 'binary' and (context.get('bin_size') or context.get('bin_size_' + col)):
                # PG 9.2 introduces conflicting pg_size_pretty(numeric) -> need ::cast
                res = 'pg_size_pretty(length(%s)::bigint)' % res
            return '%s as "%s"' % (res, col)

        qual_names = map(qualify, set(fields_pre + [self._fields['id']]))

        # determine the actual query to execute
        from_clause, where_clause, params = query.get_sql()
        query_str = """ SELECT %(qual_names)s FROM %(from_clause)s
                        WHERE %(where_clause)s %(order_str)s
                    """ % {
                        'qual_names': ",".join(qual_names),
                        'from_clause': from_clause,
                        'where_clause': where_clause,
                        'order_str': order_str,
                    }

        result = []
        param_pos = params.index(param_ids)
        for sub_ids in cr.split_for_in_conditions(self.ids):
            params[param_pos] = tuple(sub_ids)
            cr.execute(query_str, params)
            result.extend(cr.dictfetchall())

        ids = [vals['id'] for vals in result]
        fetched = self.browse(ids)

        if ids:
            # translate the fields if necessary
            if context.get('lang'):
                for field in fields_pre:
                    if not field.inherited and callable(field.column.translate):
                        f = field.name
                        translate = field.get_trans_func(fetched)
                        for vals in result:
                            vals[f] = translate(vals['id'], vals[f])

            # apply the symbol_get functions of the fields we just read
            for field in fields_pre:
                symbol_get = field.base_field.column._symbol_get
                if symbol_get:
                    f = field.name
                    for vals in result:
                        vals[f] = symbol_get(vals[f])

            # store result in cache for POST fields
            for vals in result:
                record = self.browse(vals['id'])
                record._cache.update(record._convert_to_cache(vals, validate=False))

            # determine the fields that must be processed now;
            # for the sake of simplicity, we ignore inherited fields
            fields_post = [f for f in field_names if not self._columns[f]._classic_write]

            # Compute POST fields, grouped by multi
            by_multi = defaultdict(list)
            for f in fields_post:
                by_multi[self._columns[f]._multi].append(f)

            for multi, fs in by_multi.iteritems():
                if multi:
                    res2 = self._columns[fs[0]].get(cr, self._model, ids, fs, user, context=context, values=result)
                    assert res2 is not None, \
                        'The function field "%s" on the "%s" model returned None\n' \
                        '(a dictionary was expected).' % (fs[0], self._name)
                    for vals in result:
                        # TOCHECK : why got string instend of dict in python2.6
                        # if isinstance(res2[vals['id']], str): res2[vals['id']] = eval(res2[vals['id']])
                        multi_fields = res2.get(vals['id'], {})
                        if multi_fields:
                            for f in fs:
                                vals[f] = multi_fields.get(f, [])
                else:
                    for f in fs:
                        res2 = self._columns[f].get(cr, self._model, ids, f, user, context=context, values=result)
                        for vals in result:
                            if res2:
                                vals[f] = res2[vals['id']]
                            else:
                                vals[f] = []

        # Warn about deprecated fields now that fields_pre and fields_post are computed
        for f in field_names:
            column = self._columns[f]
            if column.deprecated:
                _logger.warning('Field %s.%s is deprecated: %s', self._name, f, column.deprecated)

        # store result in cache
        for vals in result:
            record = self.browse(vals.pop('id'))
            record._cache.update(record._convert_to_cache(vals, validate=False))

        # store failed values in cache for the records that could not be read
        missing = self - fetched
        if missing:
            extras = fetched - self
            if extras:
                raise AccessError(
                    _("Database fetch misses ids ({}) and has extra ids ({}), may be caused by a type incoherence in a previous request").format(
                        ', '.join(map(repr, missing._ids)),
                        ', '.join(map(repr, extras._ids)),
                    ))
            # mark non-existing records in missing
            forbidden = missing.exists()
            if forbidden:
                # store an access error exception in existing records
                exc = AccessError(
                    _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % \
                    (self._name, 'read')
                )
                forbidden._cache.update(FailedValue(exc))

    @api.multi
    def get_metadata(self):
        """
        Returns some metadata about the given records.

        :return: list of ownership dictionaries for each requested record
        :rtype: list of dictionaries with the following keys:

                    * id: object id
                    * create_uid: user who created the record
                    * create_date: date when the record was created
                    * write_uid: last user who changed the record
                    * write_date: date of the last change to the record
                    * xmlid: XML ID to use to refer to this record (if there is one), in format ``module.name``
                    * noupdate: A boolean telling if the record will be updated or not
        """
        fields = ['id']
        if self._log_access:
            fields += ['create_uid', 'create_date', 'write_uid', 'write_date']
        quoted_table = '"%s"' % self._table
        fields_str = ",".join('%s.%s' % (quoted_table, field) for field in fields)
        query = '''SELECT %s, __imd.noupdate, __imd.module, __imd.name
                   FROM %s LEFT JOIN ir_model_data __imd
                       ON (__imd.model = %%s and __imd.res_id = %s.id)
                   WHERE %s.id IN %%s''' % (fields_str, quoted_table, quoted_table, quoted_table)
        self._cr.execute(query, (self._name, tuple(self.ids)))
        res = self._cr.dictfetchall()

        uids = set(r[k] for r in res for k in ['write_uid', 'create_uid'] if r.get(k))
        names = dict(self.env['res.users'].browse(uids).name_get())

        for r in res:
            for key in r:
                value = r[key] = r[key] or False
                if key in ('write_uid', 'create_uid') and value in names:
                    r[key] = (value, names[value])
            r['xmlid'] = ("%(module)s.%(name)s" % r) if r['name'] else False
            del r['name'], r['module']
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
                raise ValidationError(_('A document was modified since you last viewed it (%s:%d)') % (self._description, res[0]))

    def _check_record_rules_result_count(self, cr, uid, ids, result_ids, operation, context=None):
        """Verify the returned rows after applying record rules matches
           the length of ``ids``, and raise an appropriate exception if it does not.
        """
        if context is None:
            context = {}
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
                _logger.info('Access Denied by record rules for operation: %s on record ids: %r, uid: %s, model: %s', operation, forbidden_ids, uid, self._name)
                raise AccessError(_('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % \
                                    (self._description, operation))
            else:
                # If we get here, the missing_ids are not in the database
                if operation in ('read','unlink'):
                    # No need to warn about deleting an already deleted record.
                    # And no error when reading a record that was deleted, to prevent spurious
                    # errors for non-transactional search/read sequences coming from clients
                    return
                _logger.info('Failed operation on deleted record(s): %s, uid: %s, model: %s', operation, uid, self._name)
                raise MissingError(_('Missing document(s)') + ':' + _('One of the documents you are trying to access has been deleted, please try again after refreshing.'))


    def check_access_rights(self, cr, uid, operation, raise_exception=True): # no context on purpose.
        """Verifies that the operation given by ``operation`` is allowed for the user
           according to the access rights."""
        return self.pool.get('ir.model.access').check(cr, uid, self._name, operation, raise_exception)

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        """Verifies that the operation given by ``operation`` is allowed for the user
           according to ir.rules.

           :param operation: one of ``write``, ``unlink``
           :raise UserError: * if current ir.rules do not permit this operation.
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
                raise AccessError(_('For this kind of document, you may only access records you created yourself.\n\n(Document type: %s)') % (self._description,))
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
        # self.invalidate_cache(cr, uid, context=context) ?
        return True

    def delete_workflow(self, cr, uid, ids, context=None):
        """Delete the workflow instances bound to the given record IDs."""
        from openerp import workflow
        for res_id in ids:
            workflow.trg_delete(uid, self._name, res_id, cr)
        self.invalidate_cache(cr, uid, context=context)
        return True

    def step_workflow(self, cr, uid, ids, context=None):
        """Reevaluate the workflow instances of the given record IDs."""
        from openerp import workflow
        for res_id in ids:
            workflow.trg_write(uid, self._name, res_id, cr)
        # self.invalidate_cache(cr, uid, context=context) ?
        return True

    def signal_workflow(self, cr, uid, ids, signal, context=None):
        """Send given workflow signal and return a dict mapping ids to workflow results"""
        from openerp import workflow
        result = {}
        for res_id in ids:
            result[res_id] = workflow.trg_validate(uid, self._name, res_id, signal, cr)
        # self.invalidate_cache(cr, uid, context=context) ?
        return result

    def redirect_workflow(self, cr, uid, old_new_ids, context=None):
        """ Rebind the workflow instance bound to the given 'old' record IDs to
            the given 'new' IDs. (``old_new_ids`` is a list of pairs ``(old, new)``.
        """
        from openerp import workflow
        for old_id, new_id in old_new_ids:
            workflow.trg_redirect(uid, self._name, old_id, new_id, cr)
        self.invalidate_cache(cr, uid, context=context)
        return True

    def unlink(self, cr, uid, ids, context=None):
        """ unlink()

        Deletes the records of the current set

        :raise AccessError: * if user has no unlink rights on the requested object
                            * if user tries to bypass access rules for unlink on the requested object
        :raise UserError: if the record is default property for other records

        """
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not context:
            context = {}

        result_store = self._store_get_values(cr, uid, ids, self._fields.keys(), context)

        # for recomputing new-style fields
        recs = self.browse(cr, uid, ids, context)
        recs.modified(self._fields)

        self._check_concurrency(cr, ids, context)

        self.check_access_rights(cr, uid, 'unlink')

        ir_property = self.pool.get('ir.property')

        # Check if the records are used as default properties.
        domain = [('res_id', '=', False),
                  ('value_reference', 'in', ['%s,%s' % (self._name, i) for i in ids]),
                 ]
        if ir_property.search(cr, uid, domain, context=context):
            raise UserError(_('Unable to delete this document because it is used as a default property'))

        # Delete the records' properties.
        property_ids = ir_property.search(cr, uid, [('res_id', 'in', ['%s,%s' % (self._name, i) for i in ids])], context=context)
        ir_property.unlink(cr, uid, property_ids, context=context)

        self.delete_workflow(cr, uid, ids, context=context)

        self.check_access_rule(cr, uid, ids, 'unlink', context=context)
        pool_model_data = self.pool.get('ir.model.data')
        ir_values_obj = self.pool.get('ir.values')
        ir_attachment_obj = self.pool.get('ir.attachment')
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

            # For the same reason, removing the record relevant to ir_attachment
            # The search is performed with sql as the search method of ir_attachment is overridden to hide attachments of deleted records
            cr.execute('select id from ir_attachment where res_model = %s and res_id in %s', (self._name, sub_ids))
            ir_attachment_ids = [ir_attachment[0] for ir_attachment in cr.fetchall()]
            if ir_attachment_ids:
                ir_attachment_obj.unlink(cr, uid, ir_attachment_ids, context=context)

        # invalidate the *whole* cache, since the orm does not handle all
        # changes made in the database, like cascading delete!
        recs.invalidate_cache()

        for order, obj_name, store_ids, fields in result_store:
            if obj_name == self._name:
                effective_store_ids = set(store_ids) - set(ids)
            else:
                effective_store_ids = store_ids
            if effective_store_ids:
                obj = self.pool[obj_name]
                cr.execute('select id from '+obj._table+' where id IN %s', (tuple(effective_store_ids),))
                rids = map(lambda x: x[0], cr.fetchall())
                if rids:
                    obj._store_set_values(cr, uid, rids, fields, context)

        # recompute new-style fields
        if recs.env.recompute and context.get('recompute', True):
            recs.recompute()

        # auditing: deletions are infrequent and leave no trace in the database
        _unlink.info('User #%s deleted %s records with IDs: %r', uid, self._name, ids)

        return True

    #
    # TODO: Validate
    #
    @api.multi
    def write(self, vals):
        """ write(vals)

        Updates all records in the current set with the provided values.

        :param dict vals: fields to update and the value to set on them e.g::

                {'foo': 1, 'bar': "Qux"}

            will set the field ``foo`` to ``1`` and the field ``bar`` to
            ``"Qux"`` if those are valid (otherwise it will trigger an error).

        :raise AccessError: * if user has no write rights on the requested object
                            * if user tries to bypass access rules for write on the requested object
        :raise ValidateError: if user tries to enter invalid value for a field that is not in selection
        :raise UserError: if a loop would be created in a hierarchy of objects a result of the operation (such as setting an object as its own parent)

        * For numeric fields (:class:`~openerp.fields.Integer`,
          :class:`~openerp.fields.Float`) the value should be of the
          corresponding type
        * For :class:`~openerp.fields.Boolean`, the value should be a
          :class:`python:bool`
        * For :class:`~openerp.fields.Selection`, the value should match the
          selection values (generally :class:`python:str`, sometimes
          :class:`python:int`)
        * For :class:`~openerp.fields.Many2one`, the value should be the
          database identifier of the record to set
        * Other non-relational fields use a string for value

          .. danger::

              for historical and compatibility reasons,
              :class:`~openerp.fields.Date` and
              :class:`~openerp.fields.Datetime` fields use strings as values
              (written and read) rather than :class:`~python:datetime.date` or
              :class:`~python:datetime.datetime`. These date strings are
              UTC-only and formatted according to
              :const:`openerp.tools.misc.DEFAULT_SERVER_DATE_FORMAT` and
              :const:`openerp.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT`
        * .. _openerp/models/relationals/format:

          :class:`~openerp.fields.One2many` and
          :class:`~openerp.fields.Many2many` use a special "commands" format to
          manipulate the set of records stored in/associated with the field.

          This format is a list of triplets executed sequentially, where each
          triplet is a command to execute on the set of records. Not all
          commands apply in all situations. Possible commands are:

          ``(0, _, values)``
              adds a new record created from the provided ``value`` dict.
          ``(1, id, values)``
              updates an existing record of id ``id`` with the values in
              ``values``. Can not be used in :meth:`~.create`.
          ``(2, id, _)``
              removes the record of id ``id`` from the set, then deletes it
              (from the database). Can not be used in :meth:`~.create`.
          ``(3, id, _)``
              removes the record of id ``id`` from the set, but does not
              delete it. Can not be used on
              :class:`~openerp.fields.One2many`. Can not be used in
              :meth:`~.create`.
          ``(4, id, _)``
              adds an existing record of id ``id`` to the set. Can not be
              used on :class:`~openerp.fields.One2many`.
          ``(5, _, _)``
              removes all records from the set, equivalent to using the
              command ``3`` on every record explicitly. Can not be used on
              :class:`~openerp.fields.One2many`. Can not be used in
              :meth:`~.create`.
          ``(6, _, ids)``
              replaces all existing records in the set by the ``ids`` list,
              equivalent to using the command ``5`` followed by a command
              ``4`` for each ``id`` in ``ids``.

          .. note:: Values marked as ``_`` in the list above are ignored and
                    can be anything, generally ``0`` or ``False``.
        """
        if not self:
            return True

        self._check_concurrency(self._ids)
        self.check_access_rights('write')

        # No user-driven update of these columns
        for field in itertools.chain(MAGIC_COLUMNS, ('parent_left', 'parent_right')):
            vals.pop(field, None)

        # split up fields into old-style and pure new-style ones
        old_vals, new_vals, unknown = {}, {}, []
        for key, val in vals.iteritems():
            field = self._fields.get(key)
            if field:
                if field.column or field.inherited:
                    old_vals[key] = val
                if field.inverse and not field.inherited:
                    new_vals[key] = val
            else:
                unknown.append(key)

        if unknown:
            _logger.warning("%s.write() with unknown fields: %s", self._name, ', '.join(sorted(unknown)))

        # write old-style fields with (low-level) method _write
        if old_vals:
            self._write(old_vals)

        if new_vals:
            # put the values of pure new-style fields into cache
            for record in self:
                record._cache.update(record._convert_to_cache(new_vals, update=True))
            # mark the fields as being computed, to avoid their invalidation
            for key in new_vals:
                self.env.computed[self._fields[key]].update(self._ids)
            # inverse the fields
            for key in new_vals:
                self._fields[key].determine_inverse(self)
            for key in new_vals:
                self.env.computed[self._fields[key]].difference_update(self._ids)

        return True

    def _write(self, cr, user, ids, vals, context=None):
        # low-level implementation of write()
        if not context:
            context = {}

        readonly = None
        self.check_field_access_rights(cr, user, 'write', vals.keys())
        deleted_related = defaultdict(list)
        for field in vals.keys():
            fobj = None
            if field in self._columns:
                fobj = self._columns[field]
            elif field in self._inherit_fields:
                fobj = self._inherit_fields[field][2]
            if not fobj:
                continue
            if fobj._type in ['one2many', 'many2many'] and vals[field]:
                for wtuple in vals[field]:
                    if isinstance(wtuple, (tuple, list)) and wtuple[0] == 2:
                        deleted_related[fobj._obj].append(wtuple[1])
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

        result = self._store_get_values(cr, user, ids, vals.keys(), context) or []

        # for recomputing new-style fields
        recs = self.browse(cr, user, ids, context)
        modified_fields = list(vals)
        if self._log_access:
            modified_fields += ['write_date', 'write_uid']
        recs.modified(modified_fields)

        parents_changed = []
        parent_order = self._parent_order or self._order
        if self._parent_store and (self._parent_name in vals) and not context.get('defer_parent_store_computation'):
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

        updates = []            # list of (column, expr) or (column, pattern, value)
        upd_todo = []
        updend = []
        direct = []
        has_trans = context.get('lang') and context['lang'] != 'en_US'
        for field in vals:
            ffield = self._fields.get(field)
            if ffield and ffield.deprecated:
                _logger.warning('Field %s.%s is deprecated: %s', self._name, field, ffield.deprecated)
            if field in self._columns:
                column = self._columns[field]
                if hasattr(column, 'selection') and vals[field]:
                    self._check_selection_field_value(cr, user, field, vals[field], context=context)
                if column._classic_write and not hasattr(column, '_fnct_inv'):
                    if not (has_trans and column.translate and not callable(column.translate)):
                        # vals[field] is not a translation: update the table
                        updates.append((field, column._symbol_set[0], column._symbol_set[1](vals[field])))
                    direct.append(field)
                else:
                    upd_todo.append(field)
            else:
                updend.append(field)

        if self._log_access:
            updates.append(('write_uid', '%s', user))
            updates.append(('write_date', "(now() at time zone 'UTC')"))
            direct.append('write_uid')
            direct.append('write_date')

        if updates:
            self.check_access_rule(cr, user, ids, 'write', context=context)
            query = 'UPDATE "%s" SET %s WHERE id IN %%s' % (
                self._table, ','.join('"%s"=%s' % u[:2] for u in updates),
            )
            params = tuple(u[2] for u in updates if len(u) > 2)
            for sub_ids in cr.split_for_in_conditions(set(ids)):
                cr.execute(query, params + (sub_ids,))
                if cr.rowcount != len(sub_ids):
                    raise MissingError(_('One of the records you are trying to modify has already been deleted (Document type: %s).') % self._description)

            # TODO: optimize
            for f in direct:
                column = self._columns[f]
                if callable(column.translate):
                    # The source value of a field has been modified,
                    # synchronize translated terms when possible.
                    self.pool['ir.translation']._sync_terms_translations(
                        cr, user, self._fields[f], recs, context=context)

                elif has_trans and column.translate:
                    # The translated value of a field has been modified.
                    src_trans = self.pool[self._name].read(cr, user, ids, [f])[0][f]
                    if not src_trans:
                        # Insert value to DB
                        src_trans = vals[f]
                        context_wo_lang = dict(context, lang=None)
                        self.write(cr, user, ids, {f: vals[f]}, context=context_wo_lang)
                    translation_value = self._columns[f]._symbol_set[1](vals[f])
                    self.pool['ir.translation']._set_ids(cr, user, self._name+','+f, 'model', context['lang'], ids, translation_value, src_trans)

        # invalidate and mark new-style fields to recompute; do this before
        # setting other fields, because it can require the value of computed
        # fields, e.g., a one2many checking constraints on records
        recs.modified(direct)

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

        # for recomputing new-style fields
        recs.modified(upd_todo)

        unknown_fields = set(updend)
        for table, inherit_field in self._inherits.iteritems():
            col = self._inherits[table]
            nids = []
            for sub_ids in cr.split_for_in_conditions(ids):
                cr.execute('select distinct "'+col+'" from "'+self._table+'" ' \
                           'where id IN %s', (sub_ids,))
                nids.extend([x[0] for x in cr.fetchall()])

            v = {}
            for fname in updend:
                field = self._fields[fname]
                if field.inherited and field.related[0] == inherit_field:
                    v[fname] = vals[fname]
                    unknown_fields.discard(fname)
            if v:
                self.pool[table].write(cr, user, nids, v, context)

        if unknown_fields:
            _logger.warning(
                'No such field(s) in model %s: %s.',
                self._name, ', '.join(unknown_fields))

        # check Python constraints
        recs._validate_fields(vals)

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
                        raise UserError(_('Recursivity Detected.'))

                    if pleft < position:
                        cr.execute('update '+self._table+' set parent_left=parent_left+%s where parent_left>=%s', (distance, position))
                        cr.execute('update '+self._table+' set parent_right=parent_right+%s where parent_right>=%s', (distance, position))
                        cr.execute('update '+self._table+' set parent_left=parent_left+%s, parent_right=parent_right+%s where parent_left>=%s and parent_left<%s', (position-pleft, position-pleft, pleft, pright))
                    else:
                        cr.execute('update '+self._table+' set parent_left=parent_left+%s where parent_left>=%s', (distance, position))
                        cr.execute('update '+self._table+' set parent_right=parent_right+%s where parent_right>=%s', (distance, position))
                        cr.execute('update '+self._table+' set parent_left=parent_left-%s, parent_right=parent_right-%s where parent_left>=%s and parent_left<%s', (pleft-position+distance, pleft-position+distance, pleft+distance, pright+distance))
                    recs.invalidate_cache(['parent_left', 'parent_right'])

        result += self._store_get_values(cr, user, ids, vals.keys(), context)

        done = {}
        recs.env.recompute_old.extend(result)
        while recs.env.recompute_old:
            sorted_recompute_old = sorted(recs.env.recompute_old)
            recs.env.clear_recompute_old()
            for __, model_name, ids_to_update, fields_to_recompute in \
                    sorted_recompute_old:
                key = (model_name, tuple(fields_to_recompute))
                done.setdefault(key, {})
                # avoid to do several times the same computation
                todo = []
                for id in ids_to_update:
                    if id not in done[key]:
                        done[key][id] = True
                        if id not in deleted_related[model_name]:
                            todo.append(id)
                self.pool[model_name]._store_set_values(
                    cr, user, todo, fields_to_recompute, context)

        # recompute new-style fields
        if recs.env.recompute and context.get('recompute', True):
            recs.recompute()

        self.step_workflow(cr, user, ids, context=context)
        return True

    #
    # TODO: Should set perm to user.xxx
    #
    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        """ create(vals) -> record

        Creates a new record for the model.

        The new record is initialized using the values from ``vals`` and
        if necessary those from :meth:`~.default_get`.

        :param dict vals:
            values for the model's fields, as a dictionary::

                {'field_name': field_value, ...}

            see :meth:`~.write` for details
        :return: new record created
        :raise AccessError: * if user has no create rights on the requested object
                            * if user tries to bypass access rules for create on the requested object
        :raise ValidateError: if user tries to enter invalid value for a field that is not in selection
        :raise UserError: if a loop would be created in a hierarchy of objects a result of the operation (such as setting an object as its own parent)
        """
        self.check_access_rights('create')

        # add missing defaults, and drop fields that may not be set by user
        vals = self._add_missing_default_values(vals)
        for field in itertools.chain(MAGIC_COLUMNS, ('parent_left', 'parent_right')):
            vals.pop(field, None)

        # split up fields into old-style and pure new-style ones
        old_vals, new_vals, unknown = {}, {}, []
        for key, val in vals.iteritems():
            field = self._fields.get(key)
            if field:
                if field.column or field.inherited:
                    old_vals[key] = val
                if field.inverse and not field.inherited:
                    new_vals[key] = val
            else:
                unknown.append(key)

        if unknown:
            _logger.warning("%s.create() includes unknown fields: %s", self._name, ', '.join(sorted(unknown)))

        # create record with old-style fields
        record = self.browse(self._create(old_vals))

        # put the values of pure new-style fields into cache
        record._cache.update(record._convert_to_cache(new_vals))
        # mark the fields as being computed, to avoid their invalidation
        for key in new_vals:
            self.env.computed[self._fields[key]].add(record.id)
        # inverse the fields
        for key in new_vals:
            self._fields[key].determine_inverse(record)
        for key in new_vals:
            self.env.computed[self._fields[key]].discard(record.id)

        return record

    def _create(self, cr, user, vals, context=None):
        # low-level implementation of create()
        if not context:
            context = {}

        if self.is_transient():
            self._transient_vacuum(cr, user)

        tocreate = {}
        for v in self._inherits:
            if self._inherits[v] not in vals:
                tocreate[v] = {}
            else:
                tocreate[v] = {'id': vals[self._inherits[v]]}

        updates = [
            # list of column assignments defined as tuples like:
            #   (column_name, format_string, column_value)
            #   (column_name, sql_formula)
            # Those tuples will be used by the string formatting for the INSERT
            # statement below.
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

        for table in tocreate:
            if self._inherits[table] in vals:
                del vals[self._inherits[table]]

            record_id = tocreate[table].pop('id', None)

            if record_id is None or not record_id:
                record_id = self.pool[table].create(cr, user, tocreate[table], context=context)
            else:
                self.pool[table].write(cr, user, [record_id], tocreate[table], context=context)

            updates.append((self._inherits[table], '%s', record_id))

        #Start : Set bool fields to be False if they are not touched(to make search more powerful)
        bool_fields = [x for x in self._columns.keys() if self._columns[x]._type=='boolean']

        for bool_field in bool_fields:
            if bool_field not in vals:
                vals[bool_field] = False
        #End
        for field in vals.keys():
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
                updates.append((field, current_field._symbol_set[0], current_field._symbol_set[1](vals[field])))

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
            updates.append(('create_uid', '%s', user))
            updates.append(('write_uid', '%s', user))
            updates.append(('create_date', "(now() at time zone 'UTC')"))
            updates.append(('write_date', "(now() at time zone 'UTC')"))

        # the list of tuples used in this formatting corresponds to
        # tuple(field_name, format, value)
        # In some case, for example (id, create_date, write_date) we does not
        # need to read the third value of the tuple, because the real value is
        # encoded in the second value (the format).
        cr.execute(
            """INSERT INTO "%s" (%s) VALUES(%s) RETURNING id""" % (
                self._table,
                ', '.join('"%s"' % u[0] for u in updates),
                ', '.join(u[1] for u in updates)
            ),
            tuple([u[2] for u in updates if len(u) > 2])
        )

        id_new, = cr.fetchone()
        recs = self.browse(cr, user, id_new, context)

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
                recs.invalidate_cache(['parent_left', 'parent_right'])

        # invalidate and mark new-style fields to recompute; do this before
        # setting other fields, because it can require the value of computed
        # fields, e.g., a one2many checking constraints on records
        recs.modified(self._fields)

        # call the 'set' method of fields which are not classic_write
        upd_todo.sort(lambda x, y: self._columns[x].priority-self._columns[y].priority)

        # default element in context must be remove when call a one2many or many2many
        rel_context = context.copy()
        for c in context.items():
            if c[0].startswith('default_'):
                del rel_context[c[0]]

        result = []
        for field in upd_todo:
            result += self._columns[field].set(cr, self, id_new, field, vals[field], user, rel_context) or []

        # for recomputing new-style fields
        recs.modified(upd_todo)

        # check Python constraints
        recs._validate_fields(vals)

        result += self._store_get_values(cr, user, [id_new],
                list(set(vals.keys() + self._inherits.values())),
                context)
        recs.env.recompute_old.extend(result)

        if recs.env.recompute and context.get('recompute', True):
            done = []
            while recs.env.recompute_old:
                sorted_recompute_old = sorted(recs.env.recompute_old)
                recs.env.clear_recompute_old()
                for __, model_name, ids, fields2 in sorted_recompute_old:
                    if not (model_name, ids, fields2) in done:
                        self.pool[model_name]._store_set_values(
                            cr, user, ids, fields2, context)
                        done.append((model_name, ids, fields2))

            # recompute new-style fields
            recs.recompute()

        self.check_access_rule(cr, user, [id_new], 'create', context=context)
        self.create_workflow(cr, user, [id_new], context=context)
        return id_new

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
        triggers_to_compute = (
            f for f in stored_functions
            if not f[trigger_fields_] or set(fields).intersection(f[trigger_fields_])
        )

        to_compute_map = {}
        target_id_results = {}
        for store_trigger in triggers_to_compute:
            target_func_id_ = id(store_trigger[target_ids_func_])
            if target_func_id_ not in target_id_results:
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
        result = []
        if call_map:
            result = reduce(operator.add, (call_map[k] for k in sorted(call_map)))
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
                    updates = []        # list of (column, pattern, value)
                    for v in value:
                        if v not in val:
                            continue
                        column = self._columns[v]
                        if column._type == 'many2one':
                            try:
                                value[v] = value[v][0]
                            except:
                                pass
                        updates.append((v, column._symbol_set[0], column._symbol_set[1](value[v])))
                    if updates:
                        query = 'UPDATE "%s" SET %s WHERE id = %%s' % (
                            self._table, ','.join('"%s"=%s' % u[:2] for u in updates),
                        )
                        params = tuple(u[2] for u in updates)
                        cr.execute(query, params + (id,))

            else:
                for f in val:
                    column = self._columns[f]
                    # use admin user for accessing objects having rules defined on store fields
                    result = column.get(cr, self, ids, f, SUPERUSER_ID, context=context)
                    for r in result.keys():
                        if field_flag:
                            if r in field_dict.keys():
                                if f in field_dict[r]:
                                    result.pop(r)
                    for id, value in result.items():
                        if column._type == 'many2one':
                            try:
                                value = value[0]
                            except:
                                pass
                        query = 'UPDATE "%s" SET "%s"=%s WHERE id = %%s' % (
                            self._table, f, column._symbol_set[0],
                        )
                        cr.execute(query, (column._symbol_set[1](value), id))

        # invalidate and mark new-style fields to recompute
        self.browse(cr, uid, ids, context).modified(fields)

        return True

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
        if 'active' in self._fields and active_test and context.get('active_test', True):
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
            raise UserError(_('Invalid "order" specified. A valid "order" specification is a comma-separated list of valid field names (optionally followed by asc/desc for the direction)'))
        return True

    def _apply_ir_rules(self, cr, uid, query, mode='read', context=None):
        """Add what's missing in ``query`` to implement all appropriate ir.rules
          (using the ``model_name``'s rules or the current model's rules if ``model_name`` is None)

           :param query: the current query object
        """
        if uid == SUPERUSER_ID:
            return

        def apply_rule(added_clause, added_params, added_tables, parent_model=None):
            """ :param parent_model: name of the parent model, if the added
                    clause comes from a parent model
            """
            if added_clause:
                if parent_model:
                    # as inherited rules are being applied, we need to add the missing JOIN
                    # to reach the parent table (if it was not JOINed yet in the query)
                    parent_alias = self._inherits_join_add(self, parent_model, query)
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
                       parent_model=inherited_model)

    @api.model
    def _generate_translated_field(self, table_alias, field, query):
        """
        Add possibly missing JOIN with translations table to ``query`` and
        generate the expression for the translated field.

        :return: the qualified field name (or expression) to use for ``field``
        """
        lang = self._context.get('lang')
        if lang:
            # Sub-select to return at most one translation per record.
            # Even if it shoud probably not be the case,
            # this is possible to have multiple translations for a same record in the same language.
            # The parenthesis surrounding the select are important, as this is a sub-select.
            # The quotes surrounding `ir_translation` are important as well.
            unique_translation_subselect = """
            (SELECT DISTINCT ON (res_id) res_id, value
            FROM "ir_translation"
            WHERE
                name = %s AND
                lang = %s AND
                value != %s
            ORDER BY res_id, id DESC)
            """
            alias, alias_statement = query.add_join(
                (table_alias, unique_translation_subselect, 'id', 'res_id', field),
                implicit=False,
                outer=True,
                extra_params=["%s,%s" % (self._name, field), lang, ""],
            )
            return 'COALESCE("%s"."%s", "%s"."%s")' % (alias, 'value', table_alias, field)
        else:
            return '"%s"."%s"' % (table_alias, field)

    @api.model
    def _generate_m2o_order_by(self, alias, order_field, query, reverse_direction, seen):
        """
        Add possibly missing JOIN to ``query`` and generate the ORDER BY clause for m2o fields,
        either native m2o fields or function/related fields that are stored, including
        intermediate JOINs for inheritance if required.

        :return: the qualified field name to use in an ORDER BY clause to sort by ``order_field``
        """
        if order_field not in self._columns and order_field in self._inherit_fields:
            # also add missing joins for reaching the table containing the m2o field
            order_field_column = self._inherit_fields[order_field][2]
            qualified_field = self._inherits_join_calc(alias, order_field, query)
            alias, order_field = qualified_field.replace('"', '').split('.', 1)
        else:
            order_field_column = self._columns[order_field]

        assert order_field_column._type == 'many2one', 'Invalid field passed to _generate_m2o_order_by()'
        if not order_field_column._classic_write and not getattr(order_field_column, 'store', False):
            _logger.debug("Many2one function/related fields must be stored "
                          "to be used as ordering fields! Ignoring sorting for %s.%s",
                          self._name, order_field)
            return []

        # figure out the applicable order_by for the m2o
        dest_model = self.env[order_field_column._obj]
        m2o_order = dest_model._order
        if not regex_order.match(m2o_order):
            # _order is complex, can't use it here, so we default to _rec_name
            m2o_order = dest_model._rec_name

        # Join the dest m2o table if it's not joined yet. We use [LEFT] OUTER join here
        # as we don't want to exclude results that have NULL values for the m2o
        join = (alias, dest_model._table, order_field, 'id', order_field)
        dst_alias, dst_alias_statement = query.add_join(join, implicit=False, outer=True)
        return dest_model._generate_order_by_inner(dst_alias, m2o_order, query,
                                                   reverse_direction=reverse_direction, seen=seen)

    @api.model
    def _generate_order_by_inner(self, alias, order_spec, query, reverse_direction=False, seen=None):
        if seen is None:
            seen = set()
        order_by_elements = []
        self._check_qorder(order_spec)
        for order_part in order_spec.split(','):
            order_split = order_part.strip().split(' ')
            order_field = order_split[0].strip()
            order_direction = order_split[1].strip().upper() if len(order_split) == 2 else ''
            if reverse_direction:
                order_direction = 'ASC' if order_direction == 'DESC' else 'DESC'
            do_reverse = order_direction == 'DESC'
            order_column = None
            inner_clauses = []
            add_dir = False
            if order_field == 'id':
                order_by_elements.append('"%s"."%s" %s' % (alias, order_field, order_direction))
            elif order_field in self._columns:
                order_column = self._columns[order_field]
                if order_column._classic_read:
                    if order_column.translate and not callable(order_column.translate):
                        inner_clauses = [self._generate_translated_field(alias, order_field, query)]
                    else:
                        inner_clauses = ['"%s"."%s"' % (alias, order_field)]
                    add_dir = True
                elif order_column._type == 'many2one':
                    key = (self._name, order_column._obj, order_field)
                    if key not in seen:
                        seen.add(key)
                        inner_clauses = self._generate_m2o_order_by(alias, order_field, query, do_reverse, seen)
                else:
                    continue  # ignore non-readable or "non-joinable" fields
            elif order_field in self._inherit_fields:
                parent_obj = self.pool[self._inherit_fields[order_field][3]]
                order_column = parent_obj._columns[order_field]
                if order_column._classic_read:
                    inner_clauses = [self._inherits_join_calc(alias, order_field, query, implicit=False, outer=True)]
                    add_dir = True
                elif order_column._type == 'many2one':
                    key = (parent_obj._name, order_column._obj, order_field)
                    if key not in seen:
                        seen.add(key)
                        inner_clauses = self._generate_m2o_order_by(alias, order_field, query, do_reverse, seen)
                else:
                    continue  # ignore non-readable or "non-joinable" fields
            else:
                raise ValueError(_("Sorting field %s not found on model %s") % (order_field, self._name))
            if order_column and order_column._type == 'boolean':
                inner_clauses = ["COALESCE(%s, false)" % inner_clauses[0]]

            for clause in inner_clauses:
                if add_dir:
                    order_by_elements.append("%s %s" % (clause, order_direction))
                else:
                    order_by_elements.append(clause)
        return order_by_elements

    @api.model
    def _generate_order_by(self, order_spec, query):
        """
        Attempt to construct an appropriate ORDER BY clause based on order_spec, which must be
        a comma-separated list of valid field names, optionally followed by an ASC or DESC direction.

        :raise ValueError in case order_spec is malformed
        """
        order_by_clause = ''
        order_spec = order_spec or self._order
        if order_spec:
            order_by_elements = self._generate_order_by_inner(self._table, order_spec, query)
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

        # For transient models, restrict access to the current user, except for the super-user
        if self.is_transient() and self._log_access and user != SUPERUSER_ID:
            args = expression.AND(([('create_uid', '=', user)], args or []))

        query = self._where_calc(cr, user, args, context=context)
        self._apply_ir_rules(cr, user, query, 'read', context=context)
        order_by = self._generate_order_by(cr, user, order, query, context=context)
        from_clause, where_clause, where_clause_params = query.get_sql()

        where_str = where_clause and (" WHERE %s" % where_clause) or ''

        if count:
            # Ignore order, limit and offset when just counting, they don't make sense and could
            # hurt performance
            query_str = 'SELECT count(1) FROM ' + from_clause + where_str
            cr.execute(query_str, where_clause_params)
            res = cr.fetchone()
            return res[0]

        limit_str = limit and ' limit %d' % limit or ''
        offset_str = offset and ' offset %d' % offset or ''
        query_str = 'SELECT "%s".id FROM ' % self._table + from_clause + where_str + order_by + limit_str + offset_str
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
        if '__copy_data_seen' not in context:
            context = dict(context, __copy_data_seen=defaultdict(list))
        seen_map = context['__copy_data_seen']
        if id in seen_map[self._name]:
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
        whitelist = set(name for name, field in self._fields.iteritems() if not field.inherited)

        def blacklist_given_fields(obj):
            # blacklist the fields that are given by inheritance
            for other, field_to_other in obj._inherits.items():
                blacklist.add(field_to_other)
                if field_to_other in default:
                    # all the fields of 'other' are given by the record: default[field_to_other],
                    # except the ones redefined in self
                    blacklist.update(set(self.pool[other]._fields) - whitelist)
                else:
                    blacklist_given_fields(self.pool[other])
            # blacklist deprecated fields
            for name, field in obj._fields.iteritems():
                if field.deprecated:
                    blacklist.add(name)

        blacklist_given_fields(self)


        fields_to_copy = dict((f,fi) for f, fi in self._fields.iteritems()
                                     if fi.copy
                                     if f not in default
                                     if f not in blacklist)

        data = self.read(cr, uid, [id], fields_to_copy.keys(), context=context)
        if data:
            data = data[0]
        else:
            raise IndexError(_("Record #%d of %s not found, cannot copy!") % ( id, self._name))

        res = dict(default)
        for f, field in fields_to_copy.iteritems():
            if field.type == 'many2one':
                res[f] = data[f] and data[f][0]
            elif field.type == 'one2many':
                other = self.pool[field.comodel_name]
                # duplicate following the order of the ids because we'll rely on
                # it later for copying translations in copy_translation()!
                lines = [other.copy_data(cr, uid, line_id, context=context) for line_id in sorted(data[f])]
                # the lines are duplicated using the wrong (old) parent, but then
                # are reassigned to the correct one thanks to the (0, 0, ...)
                res[f] = [(0, 0, line) for line in lines if line]
            elif field.type == 'many2many':
                res[f] = [(6, 0, data[f])]
            else:
                res[f] = data[f]

        return res

    def copy_translations(self, cr, uid, old_id, new_id, context=None):
        if context is None:
            context = {}

        # avoid recursion through already copied records in case of circular relationship
        if '__copy_translations_seen' not in context:
            context = dict(context, __copy_translations_seen=defaultdict(list))
        seen_map = context['__copy_translations_seen']
        if old_id in seen_map[self._name]:
            return
        seen_map[self._name].append(old_id)

        trans_obj = self.pool.get('ir.translation')

        for field_name, field in self._fields.iteritems():
            if not field.copy:
                continue
            # removing the lang to compare untranslated values
            context_wo_lang = dict(context, lang=None)
            old_record, new_record = self.browse(cr, uid, [old_id, new_id], context=context_wo_lang)
            # we must recursively copy the translations for o2o and o2m
            if field.type == 'one2many':
                target_obj = self.pool[field.comodel_name]
                # here we rely on the order of the ids to match the translations
                # as foreseen in copy_data()
                old_children = sorted(r.id for r in old_record[field_name])
                new_children = sorted(r.id for r in new_record[field_name])
                for (old_child, new_child) in zip(old_children, new_children):
                    target_obj.copy_translations(cr, uid, old_child, new_child, context=context)
            # and for translatable fields we keep them for copy
            elif getattr(field, 'translate', False):
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
                    # duplicated record is not linked to any module
                    del record['module']
                    record.update({'res_id': target_id})
                    if user_lang and user_lang == record['lang']:
                        # 'source' to force the call to _set_src
                        # 'value' needed if value is changed in copy(), want to see the new_value
                        record['source'] = old_record[field_name]
                        record['value'] = new_record[field_name]
                    trans_obj.create(cr, uid, record, context=context)

    @api.returns('self', lambda value: value.id)
    def copy(self, cr, uid, id, default=None, context=None):
        """ copy(default=None)

        Duplicate record with given id updating it with default values

        :param dict default: dictionary of field values to override in the
               original values of the copied record, e.g: ``{'field_name': overridden_value, ...}``
        :returns: new record

        """
        if context is None:
            context = {}
        context = context.copy()
        data = self.copy_data(cr, uid, id, default, context)
        new_id = self.create(cr, uid, data, context)
        self.copy_translations(cr, uid, id, new_id, context)
        return new_id

    @api.multi
    @api.returns('self')
    def exists(self):
        """  exists() -> records

        Returns the subset of records in ``self`` that exist, and marks deleted
        records as such in cache. It can be used as a test on records::

            if record.exists():
                ...

        By convention, new records are returned as existing.
        """
        ids, new_ids = [], []
        for i in self._ids:
            (ids if isinstance(i, (int, long)) else new_ids).append(i)
        if not ids:
            return self
        query = """SELECT id FROM "%s" WHERE id IN %%s""" % self._table
        self._cr.execute(query, [tuple(ids)])
        ids = [r[0] for r in self._cr.fetchall()]
        existing = self.browse(ids + new_ids)
        if len(existing) < len(self):
            # mark missing records in cache with a failed value
            exc = MissingError(_("Record does not exist or has been deleted."))
            (self - existing)._cache.update(FailedValue(exc))
        return existing

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

        field = self._fields.get(field_name)
        if not (field and field.type == 'many2many' and
                field.comodel_name == self._name and field.store):
            # field must be a many2many on itself
            raise ValueError('invalid field_name: %r' % (field_name,))

        query = 'SELECT distinct "%s" FROM "%s" WHERE "%s" IN %%s' % \
                    (field.column2, field.relation, field.column1)
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
        Render the report ``name`` for the given IDs. The report must be defined
        for this model, not another.
        """
        report = self.pool['ir.actions.report.xml']._lookup_report(cr, name)
        assert self._name == report.table
        return report.create(cr, uid, ids, data, context)

    # Transience
    @classmethod
    def is_transient(cls):
        """ Return whether the model is transient.

        See :class:`TransientModel`.

        """
        return cls._transient

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

        for command in commands or []:
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
        other_model = self.pool[self._fields[field_name].comodel_name]
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

    @api.multi
    def toggle_active(self):
        """ Inverse the value of the field ``active`` on the records in ``self``. """
        for record in self:
            record.active = not record.active

    def _register_hook(self, cr):
        """ stuff to do right after the registry is built """
        pass

    @classmethod
    def _patch_method(cls, name, method):
        """ Monkey-patch a method for all instances of this model. This replaces
            the method called ``name`` by ``method`` in the given class.
            The original method is then accessible via ``method.origin``, and it
            can be restored with :meth:`~._revert_method`.

            Example::

                @api.multi
                def do_write(self, values):
                    # do stuff, and call the original method
                    return do_write.origin(self, values)

                # patch method write of model
                model._patch_method('write', do_write)

                # this will call do_write
                records = model.search([...])
                records.write(...)

                # restore the original method
                model._revert_method('write')
        """
        origin = getattr(cls, name)
        method.origin = origin
        # propagate decorators from origin to method, and apply api decorator
        wrapped = api.guess(api.propagate(origin, method))
        wrapped.origin = origin
        setattr(cls, name, wrapped)

    @classmethod
    def _revert_method(cls, name):
        """ Revert the original method called ``name`` in the given class.
            See :meth:`~._patch_method`.
        """
        method = getattr(cls, name)
        setattr(cls, name, method.origin)

    #
    # Instance creation
    #
    # An instance represents an ordered collection of records in a given
    # execution environment. The instance object refers to the environment, and
    # the records themselves are represented by their cache dictionary. The 'id'
    # of each record is found in its corresponding cache dictionary.
    #
    # This design has the following advantages:
    #  - cache access is direct and thus fast;
    #  - one can consider records without an 'id' (see new records);
    #  - the global cache is only an index to "resolve" a record 'id'.
    #

    @classmethod
    def _browse(cls, env, ids):
        """ Create an instance attached to ``env``; ``ids`` is a tuple of record
            ids.
        """
        records = object.__new__(cls)
        records.env = env
        records._ids = ids
        env.prefetch[cls._name].update(ids)
        return records

    @api.v7
    def browse(self, cr, uid, arg=None, context=None):
        ids = _normalize_ids(arg)
        #assert all(isinstance(id, IdType) for id in ids), "Browsing invalid ids: %s" % ids
        return self._browse(Environment(cr, uid, context or {}), ids)

    @api.v8
    def browse(self, arg=None):
        """ browse([ids]) -> records

        Returns a recordset for the ids provided as parameter in the current
        environment.

        Can take no ids, a single id or a sequence of ids.
        """
        ids = _normalize_ids(arg)
        #assert all(isinstance(id, IdType) for id in ids), "Browsing invalid ids: %s" % ids
        return self._browse(self.env, ids)

    #
    # Internal properties, for manipulating the instance's implementation
    #

    @property
    def ids(self):
        """ List of actual record ids in this recordset (ignores placeholder
        ids for records to create)
        """
        return filter(None, list(self._ids))

    # backward-compatibility with former browse records
    _cr = property(lambda self: self.env.cr)
    _uid = property(lambda self: self.env.uid)
    _context = property(lambda self: self.env.context)

    #
    # Conversion methods
    #

    def ensure_one(self):
        """ Verifies that the current recorset holds a single record. Raises
        an exception otherwise.
        """
        if len(self) == 1:
            return self
        raise ValueError("Expected singleton: %s" % self)

    def with_env(self, env):
        """ Returns a new version of this recordset attached to the provided
        environment

        .. warning::
            The new environment will not benefit from the current
            environment's data cache, so later data access may incur extra
            delays while re-fetching from the database.

        :type env: :class:`~openerp.api.Environment`
        """
        return self._browse(env, self._ids)

    def sudo(self, user=SUPERUSER_ID):
        """ sudo([user=SUPERUSER])

        Returns a new version of this recordset attached to the provided
        user.

        By default this returns a ``SUPERUSER`` recordset, where access
        control and record rules are bypassed.

        .. note::

            Using ``sudo`` could cause data access to cross the
            boundaries of record rules, possibly mixing records that
            are meant to be isolated (e.g. records from different
            companies in multi-company environments).

            It may lead to un-intuitive results in methods which select one
            record among many - for example getting the default company, or
            selecting a Bill of Materials.

        .. note::

            Because the record rules and access control will have to be
            re-evaluated, the new recordset will not benefit from the current
            environment's data cache, so later data access may incur extra
            delays while re-fetching from the database.

        """
        return self.with_env(self.env(user=user))

    def with_context(self, *args, **kwargs):
        """ with_context([context][, **overrides]) -> records

        Returns a new version of this recordset attached to an extended
        context.

        The extended context is either the provided ``context`` in which
        ``overrides`` are merged or the *current* context in which
        ``overrides`` are merged e.g.::

            # current context is {'key1': True}
            r2 = records.with_context({}, key2=True)
            # -> r2._context is {'key2': True}
            r2 = records.with_context(key2=True)
            # -> r2._context is {'key1': True, 'key2': True}
        """
        context = dict(args[0] if args else self._context, **kwargs)
        return self.with_env(self.env(context=context))

    def _convert_to_cache(self, values, update=False, validate=True):
        """ Convert the ``values`` dictionary into cached values.

            :param update: whether the conversion is made for updating ``self``;
                this is necessary for interpreting the commands of *2many fields
            :param validate: whether values must be checked
        """
        fields = self._fields
        target = self if update else self.browse()
        return {
            name: fields[name].convert_to_cache(value, target, validate=validate)
            for name, value in values.iteritems()
            if name in fields
        }

    def _convert_to_write(self, values):
        """ Convert the ``values`` dictionary into the format of :meth:`write`. """
        fields = self._fields
        result = {}
        for name, value in values.iteritems():
            if name in fields:
                value = fields[name].convert_to_write(value)
                if not isinstance(value, NewId):
                    result[name] = value
        return result

    #
    # Record traversal and update
    #

    def _mapped_func(self, func):
        """ Apply function ``func`` on all records in ``self``, and return the
            result as a list or a recordset (if ``func`` returns recordsets).
        """
        if self:
            vals = [func(rec) for rec in self]
            if isinstance(vals[0], BaseModel):
                # return the union of all recordsets in O(n)
                ids = set(itertools.chain(*[rec._ids for rec in vals]))
                return vals[0].browse(ids)
            return vals
        else:
            vals = func(self)
            return vals if isinstance(vals, BaseModel) else []

    def mapped(self, func):
        """ Apply ``func`` on all records in ``self``, and return the result as a
            list or a recordset (if ``func`` return recordsets). In the latter
            case, the order of the returned recordset is arbitrary.

            :param func: a function or a dot-separated sequence of field names
        """
        if isinstance(func, basestring):
            recs = self
            for name in func.split('.'):
                recs = recs._mapped_func(operator.itemgetter(name))
            return recs
        else:
            return self._mapped_func(func)

    def _mapped_cache(self, name_seq):
        """ Same as `~.mapped`, but ``name_seq`` is a dot-separated sequence of
            field names, and only cached values are used.
        """
        recs = self
        for name in name_seq.split('.'):
            field = recs._fields[name]
            null = field.null(self.env)
            recs = recs.mapped(lambda rec: rec._cache.get(field, null))
        return recs

    def filtered(self, func):
        """ Select the records in ``self`` such that ``func(rec)`` is true, and
            return them as a recordset.

            :param func: a function or a dot-separated sequence of field names
        """
        if isinstance(func, basestring):
            name = func
            func = lambda rec: filter(None, rec.mapped(name))
        return self.browse([rec.id for rec in self if func(rec)])

    def sorted(self, key=None, reverse=False):
        """ Return the recordset ``self`` ordered by ``key``.

            :param key: either a function of one argument that returns a
                comparison key for each record, or ``None``, in which case
                records are ordered according the default model's order

            :param reverse: if ``True``, return the result in reverse order
        """
        if key is None:
            recs = self.search([('id', 'in', self.ids)])
            return self.browse(reversed(recs._ids)) if reverse else recs
        else:
            return self.browse(map(itemgetter('id'), sorted(self, key=key, reverse=reverse)))

    def update(self, values):
        """ Update record `self[0]` with ``values``. """
        for name, value in values.iteritems():
            self[name] = value

    #
    # New records - represent records that do not exist in the database yet;
    # they are used to perform onchanges.
    #

    @api.model
    def new(self, values={}):
        """ new([values]) -> record

        Return a new record instance attached to the current environment and
        initialized with the provided ``value``. The record is *not* created
        in database, it only exists in memory.
        """
        record = self.browse([NewId()])
        record._cache.update(record._convert_to_cache(values, update=True))

        if record.env.in_onchange:
            # The cache update does not set inverse fields, so do it manually.
            # This is useful for computing a function field on secondary
            # records, if that field depends on the main record.
            for name in values:
                field = self._fields.get(name)
                if field:
                    for invf in self._field_inverses[field]:
                        invf._update(record[name], record)

        return record

    #
    # Dirty flags, to mark record fields modified (in draft mode)
    #

    def _is_dirty(self):
        """ Return whether any record in ``self`` is dirty. """
        dirty = self.env.dirty
        return any(record in dirty for record in self)

    def _get_dirty(self):
        """ Return the list of field names for which ``self`` is dirty. """
        dirty = self.env.dirty
        return list(dirty.get(self, ()))

    def _set_dirty(self, field_name):
        """ Mark the records in ``self`` as dirty for the given ``field_name``. """
        dirty = self.env.dirty
        for record in self:
            dirty[record].add(field_name)

    #
    # "Dunder" methods
    #

    def __nonzero__(self):
        """ Test whether ``self`` is nonempty. """
        return bool(getattr(self, '_ids', True))

    def __len__(self):
        """ Return the size of ``self``. """
        return len(self._ids)

    def __iter__(self):
        """ Return an iterator over ``self``. """
        for id in self._ids:
            yield self._browse(self.env, (id,))

    def __contains__(self, item):
        """ Test whether ``item`` (record or field name) is an element of ``self``.
            In the first case, the test is fully equivalent to::

                any(item == record for record in self)
        """
        if isinstance(item, BaseModel) and self._name == item._name:
            return len(item) == 1 and item.id in self._ids
        elif isinstance(item, basestring):
            return item in self._fields
        else:
            raise TypeError("Mixing apples and oranges: %s in %s" % (item, self))

    def __add__(self, other):
        """ Return the concatenation of two recordsets. """
        if not isinstance(other, BaseModel) or self._name != other._name:
            raise TypeError("Mixing apples and oranges: %s + %s" % (self, other))
        return self.browse(self._ids + other._ids)

    def __sub__(self, other):
        """ Return the recordset of all the records in ``self`` that are not in ``other``. """
        if not isinstance(other, BaseModel) or self._name != other._name:
            raise TypeError("Mixing apples and oranges: %s - %s" % (self, other))
        other_ids = set(other._ids)
        return self.browse([id for id in self._ids if id not in other_ids])

    def __and__(self, other):
        """ Return the intersection of two recordsets.
            Note that recordset order is not preserved.
        """
        if not isinstance(other, BaseModel) or self._name != other._name:
            raise TypeError("Mixing apples and oranges: %s & %s" % (self, other))
        return self.browse(set(self._ids) & set(other._ids))

    def __or__(self, other):
        """ Return the union of two recordsets.
            Note that recordset order is not preserved.
        """
        if not isinstance(other, BaseModel) or self._name != other._name:
            raise TypeError("Mixing apples and oranges: %s | %s" % (self, other))
        return self.browse(set(self._ids) | set(other._ids))

    def __eq__(self, other):
        """ Test whether two recordsets are equivalent (up to reordering). """
        if not isinstance(other, BaseModel):
            if other:
                filename, lineno = frame_codeinfo(currentframe(), 1)
                _logger.warning("Comparing apples and oranges: %r == %r (%s:%s)",
                                self, other, filename, lineno)
            return False
        return self._name == other._name and set(self._ids) == set(other._ids)

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, BaseModel) or self._name != other._name:
            raise TypeError("Mixing apples and oranges: %s < %s" % (self, other))
        return set(self._ids) < set(other._ids)

    def __le__(self, other):
        if not isinstance(other, BaseModel) or self._name != other._name:
            raise TypeError("Mixing apples and oranges: %s <= %s" % (self, other))
        return set(self._ids) <= set(other._ids)

    def __gt__(self, other):
        if not isinstance(other, BaseModel) or self._name != other._name:
            raise TypeError("Mixing apples and oranges: %s > %s" % (self, other))
        return set(self._ids) > set(other._ids)

    def __ge__(self, other):
        if not isinstance(other, BaseModel) or self._name != other._name:
            raise TypeError("Mixing apples and oranges: %s >= %s" % (self, other))
        return set(self._ids) >= set(other._ids)

    def __int__(self):
        return self.id

    def __str__(self):
        return "%s%s" % (self._name, getattr(self, '_ids', ""))

    def __unicode__(self):
        return unicode(str(self))

    __repr__ = __str__

    def __hash__(self):
        if hasattr(self, '_ids'):
            return hash((self._name, frozenset(self._ids)))
        else:
            return hash(self._name)

    def __getitem__(self, key):
        """ If ``key`` is an integer or a slice, return the corresponding record
            selection as an instance (attached to ``self.env``).
            Otherwise read the field ``key`` of the first record in ``self``.

            Examples::

                inst = model.search(dom)    # inst is a recordset
                r4 = inst[3]                # fourth record in inst
                rs = inst[10:20]            # subset of inst
                nm = rs['name']             # name of first record in inst
        """
        if isinstance(key, basestring):
            # important: one must call the field's getter
            return self._fields[key].__get__(self, type(self))
        elif isinstance(key, slice):
            return self._browse(self.env, self._ids[key])
        else:
            return self._browse(self.env, (self._ids[key],))

    def __setitem__(self, key, value):
        """ Assign the field ``key`` to ``value`` in record ``self``. """
        # important: one must call the field's setter
        return self._fields[key].__set__(self, value)

    #
    # Cache and recomputation management
    #

    @lazy_property
    def _cache(self):
        """ Return the cache of ``self``, mapping field names to values. """
        return RecordCache(self)

    @api.model
    def _in_cache_without(self, field):
        """ Make sure ``self`` is present in cache (for prefetching), and return
            the records of model ``self`` in cache that have no value for ``field``
            (:class:`Field` instance).
        """
        env = self.env
        prefetch_ids = env.prefetch[self._name]
        prefetch_ids.update(self._ids)
        ids = filter(None, prefetch_ids - set(env.cache[field]))
        return self.browse(ids)

    @api.model
    def refresh(self):
        """ Clear the records cache.

            .. deprecated:: 8.0
                The record cache is automatically invalidated.
        """
        self.invalidate_cache()

    @api.model
    def invalidate_cache(self, fnames=None, ids=None):
        """ Invalidate the record caches after some records have been modified.
            If both ``fnames`` and ``ids`` are ``None``, the whole cache is cleared.

            :param fnames: the list of modified fields, or ``None`` for all fields
            :param ids: the list of modified record ids, or ``None`` for all
        """
        if fnames is None:
            if ids is None:
                return self.env.invalidate_all()
            fields = self._fields.values()
        else:
            fields = map(self._fields.__getitem__, fnames)

        # invalidate fields and inverse fields, too
        spec = [(f, ids) for f in fields] + \
               [(invf, None) for f in fields for invf in self._field_inverses[f]]
        self.env.invalidate(spec)

    @api.multi
    def modified(self, fnames):
        """ Notify that fields have been modified on ``self``. This invalidates
            the cache, and prepares the recomputation of stored function fields
            (new-style fields only).

            :param fnames: iterable of field names that have been modified on
                records ``self``
        """
        # each field knows what to invalidate and recompute
        spec = []
        for fname in fnames:
            spec += self._fields[fname].modified(self)

        cached_fields = {
            field
            for env in self.env.all
            for field in env.cache
        }
        # invalidate non-stored fields.function which are currently cached
        spec += [(f, None) for f in self.pool.pure_function_fields
                 if f in cached_fields]

        self.env.invalidate(spec)

    def _recompute_check(self, field):
        """ If ``field`` must be recomputed on some record in ``self``, return the
            corresponding records that must be recomputed.
        """
        return self.env.check_todo(field, self)

    def _recompute_todo(self, field):
        """ Mark ``field`` to be recomputed. """
        self.env.add_todo(field, self)

    def _recompute_done(self, field):
        """ Mark ``field`` as recomputed. """
        self.env.remove_todo(field, self)

    @api.model
    def recompute(self):
        """ Recompute stored function fields. The fields and records to
            recompute have been determined by method :meth:`modified`.
        """
        while self.env.has_todo():
            field, recs = self.env.get_todo()
            # determine the fields to recompute
            fs = self.env[field.model_name]._field_computed[field]
            ns = [f.name for f in fs if f.store]
            # evaluate fields, and group record ids by update
            updates = defaultdict(set)
            for rec in recs.exists():
                vals = rec._convert_to_write({n: rec[n] for n in ns})
                updates[frozendict(vals)].add(rec.id)
            # update records in batch when possible
            with recs.env.norecompute():
                for vals, ids in updates.iteritems():
                    recs.browse(ids)._write(dict(vals))
            # mark computed fields as done
            map(recs._recompute_done, fs)

    #
    # Generic onchange method
    #

    def _has_onchange(self, field, other_fields):
        """ Return whether ``field`` should trigger an onchange event in the
            presence of ``other_fields``.
        """
        # test whether self has an onchange method for field, or field is a
        # dependency of any field in other_fields
        return field.name in self._onchange_methods or \
            any(dep in other_fields for dep, _ in self._field_triggers[field])

    @api.model
    def _onchange_spec(self, view_info=None):
        """ Return the onchange spec from a view description; if not given, the
            result of ``self.fields_view_get()`` is used.
        """
        result = {}

        # for traversing the XML arch and populating result
        def process(node, info, prefix):
            if node.tag == 'field':
                name = node.attrib['name']
                names = "%s.%s" % (prefix, name) if prefix else name
                if not result.get(names):
                    result[names] = node.attrib.get('on_change')
                # traverse the subviews included in relational fields
                for subinfo in info['fields'][name].get('views', {}).itervalues():
                    process(etree.fromstring(subinfo['arch']), subinfo, names)
            else:
                for child in node:
                    process(child, info, prefix)

        if view_info is None:
            view_info = self.fields_view_get()
        process(etree.fromstring(view_info['arch']), view_info, '')
        return result

    def _onchange_eval(self, field_name, onchange, result):
        """ Apply onchange method(s) for field ``field_name`` with spec ``onchange``
            on record ``self``. Value assignments are applied on ``self``, while
            domain and warning messages are put in dictionary ``result``.
        """
        onchange = onchange.strip()

        # onchange V8
        if onchange in ("1", "true"):
            for method in self._onchange_methods.get(field_name, ()):
                method_res = method(self)
                if not method_res:
                    continue
                if 'domain' in method_res:
                    result.setdefault('domain', {}).update(method_res['domain'])
                if 'warning' in method_res:
                    if result.get('warning'):
                        if method_res['warning']:
                            # Concatenate multiple warnings
                            warning = result['warning']
                            warning['message'] = '\n\n'.join(filter(None, [
                                warning.get('title'),
                                warning.get('message'),
                                method_res['warning'].get('title'),
                                method_res['warning'].get('message')
                            ]))
                            warning['title'] = _('Warnings')
                    else:
                        result['warning'] = method_res['warning']
            return

        # onchange V7
        match = onchange_v7.match(onchange)
        if match:
            method, params = match.groups()

            class RawRecord(object):
                def __init__(self, record):
                    self._record = record
                def __getitem__(self, name):
                    field = self._record._fields[name]
                    value = self._record[name]
                    return field.convert_to_write(value)
                def __getattr__(self, name):
                    return self[name]

            # evaluate params -> tuple
            global_vars = {'context': self._context, 'uid': self._uid}
            if self._context.get('field_parent'):
                record = self[self._context['field_parent']]
                global_vars['parent'] = RawRecord(record)
            field_vars = RawRecord(self)
            params = eval("[%s]" % params, global_vars, field_vars, nocopy=True)

            # call onchange method with context when possible
            args = (self._cr, self._uid, self._origin.ids) + tuple(params)
            try:
                method_res = getattr(self._model, method)(*args, context=self._context)
            except TypeError:
                method_res = getattr(self._model, method)(*args)

            if not isinstance(method_res, dict):
                return
            if 'value' in method_res:
                method_res['value'].pop('id', None)
                self.update(self._convert_to_cache(method_res['value'], validate=False))
            if 'domain' in method_res:
                result.setdefault('domain', {}).update(method_res['domain'])
            if 'warning' in method_res:
                if result.get('warning'):
                    if method_res['warning']:
                        # Concatenate multiple warnings
                        warning = result['warning']
                        warning['message'] = '\n\n'.join(filter(None, [
                            warning.get('title'),
                            warning.get('message'),
                            method_res['warning'].get('title'),
                            method_res['warning'].get('message')
                        ]))
                        warning['title'] = _('Warnings')
                else:
                    result['warning'] = method_res['warning']
    @api.multi
    def onchange(self, values, field_name, field_onchange):
        """ Perform an onchange on the given field.

            :param values: dictionary mapping field names to values, giving the
                current state of modification
            :param field_name: name of the modified field, or list of field
                names (in view order), or False
            :param field_onchange: dictionary mapping field names to their
                on_change attribute
        """
        env = self.env
        if isinstance(field_name, list):
            names = field_name
        elif field_name:
            names = [field_name]
        else:
            names = []

        if not all(name in self._fields for name in names):
            return {}

        # determine subfields for field.convert_to_onchange() below
        secondary = []
        subfields = defaultdict(set)
        for dotname in field_onchange:
            if '.' in dotname:
                secondary.append(dotname)
                name, subname = dotname.split('.')
                subfields[name].add(subname)

        # create a new record with values, and attach ``self`` to it
        with env.do_in_onchange():
            record = self.new(values)
            values = dict(record._cache)
            # attach ``self`` with a different context (for cache consistency)
            record._origin = self.with_context(__onchange=True)

        # load fields on secondary records, to avoid false changes
        with env.do_in_onchange():
            for field_seq in secondary:
                record.mapped(field_seq)

        # determine which field(s) should be triggered an onchange
        todo = list(names) or list(values)
        done = set()

        # dummy assignment: trigger invalidations on the record
        for name in todo:
            if name == 'id':
                continue
            value = record[name]
            field = self._fields[name]
            if field.type == 'many2one' and field.delegate and not value:
                # do not nullify all fields of parent record for new records
                continue
            record[name] = value

        result = {}
        dirty = set()

        # process names in order (or the keys of values if no name given)
        while todo:
            name = todo.pop(0)
            if name in done:
                continue
            done.add(name)

            with env.do_in_onchange():
                # apply field-specific onchange methods
                if field_onchange.get(name):
                    record._onchange_eval(name, field_onchange[name], result)

                # force re-evaluation of function fields on secondary records
                for field_seq in secondary:
                    record.mapped(field_seq)

                # determine which fields have been modified
                for name, oldval in values.iteritems():
                    field = self._fields[name]
                    newval = record[name]
                    if newval != oldval or (
                        field.type in ('one2many', 'many2many') and newval._is_dirty()
                    ):
                        todo.append(name)
                        dirty.add(name)

        # At the moment, the client does not support updates on a *2many field
        # while this one is modified by the user.
        if isinstance(field_name, basestring) and \
                self._fields[field_name].type in ('one2many', 'many2many'):
            dirty.discard(field_name)

        # collect values from dirty fields
        result['value'] = {
            name: self._fields[name].convert_to_onchange(record[name], subfields.get(name))
            for name in dirty
        }

        return result


class RecordCache(MutableMapping):
    """ Implements a proxy dictionary to read/update the cache of a record.
        Upon iteration, it looks like a dictionary mapping field names to
        values. However, fields may be used as keys as well.
    """
    def __init__(self, records):
        self._recs = records

    def contains(self, field):
        """ Return whether `records[0]` has a value for ``field`` in cache. """
        if isinstance(field, basestring):
            field = self._recs._fields[field]
        return self._recs.id in self._recs.env.cache[field]

    def __contains__(self, field):
        """ Return whether `records[0]` has a regular value for ``field`` in cache. """
        if isinstance(field, basestring):
            field = self._recs._fields[field]
        dummy = SpecialValue(None)
        value = self._recs.env.cache[field].get(self._recs.id, dummy)
        return not isinstance(value, SpecialValue)

    def get(self, field, default=None):
        """ Return the cached, regular value of ``field`` for `records[0]`, or ``default``. """
        if isinstance(field, basestring):
            field = self._recs._fields[field]
        dummy = SpecialValue(None)
        value = self._recs.env.cache[field].get(self._recs.id, dummy)
        return default if isinstance(value, SpecialValue) else value

    def __getitem__(self, field):
        """ Return the cached value of ``field`` for `records[0]`. """
        if isinstance(field, basestring):
            field = self._recs._fields[field]
        value = self._recs.env.cache[field][self._recs.id]
        return value.get() if isinstance(value, SpecialValue) else value

    def __setitem__(self, field, value):
        """ Assign the cached value of ``field`` for all records in ``records``. """
        if isinstance(field, basestring):
            field = self._recs._fields[field]
        values = dict.fromkeys(self._recs._ids, value)
        self._recs.env.cache[field].update(values)

    def update(self, *args, **kwargs):
        """ Update the cache of all records in ``records``. If the argument is a
            ``SpecialValue``, update all fields (except "magic" columns).
        """
        if args and isinstance(args[0], SpecialValue):
            values = dict.fromkeys(self._recs._ids, args[0])
            for name, field in self._recs._fields.iteritems():
                if name != 'id':
                    self._recs.env.cache[field].update(values)
        else:
            return super(RecordCache, self).update(*args, **kwargs)

    def __delitem__(self, field):
        """ Remove the cached value of ``field`` for all ``records``. """
        if isinstance(field, basestring):
            field = self._recs._fields[field]
        field_cache = self._recs.env.cache[field]
        for id in self._recs._ids:
            field_cache.pop(id, None)

    def __iter__(self):
        """ Iterate over the field names with a regular value in cache. """
        cache, id = self._recs.env.cache, self._recs.id
        dummy = SpecialValue(None)
        for name, field in self._recs._fields.iteritems():
            if name != 'id' and not isinstance(cache[field].get(id, dummy), SpecialValue):
                yield name

    def __len__(self):
        """ Return the number of fields with a regular value in cache. """
        return sum(1 for name in self)

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
       persisted, and regularly vacuum-cleaned.

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

def convert_pgerror_23502(model, fields, info, e):
    m = re.match(r'^null value in column "(?P<field>\w+)" violates '
                 r'not-null constraint\n',
                 tools.ustr(e))
    field_name = m and m.group('field')
    if not m or field_name not in fields:
        return {'message': tools.ustr(e)}
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
                 tools.ustr(e))
    field_name = m and m.group('field')
    if not m or field_name not in fields:
        return {'message': tools.ustr(e)}
    message = _(u"The value for the field '%s' already exists.") % field_name
    field = fields.get(field_name)
    if field:
        message = _(u"%s This might be '%s' in the current model, or a field "
                    u"of the same name in an o2m.") % (message, field['string'])
    return {
        'message': message,
        'field': field_name,
    }

PGERROR_TO_OE = defaultdict(
    # shape of mapped converters
    lambda: (lambda model, fvg, info, pgerror: {'message': tools.ustr(pgerror)}), {
    # not_null_violation
    '23502': convert_pgerror_23502,
    # unique constraint error
    '23505': convert_pgerror_23505,
})

def _normalize_ids(arg, atoms={int, long, str, unicode, NewId}):
    """ Normalizes the ids argument for ``browse`` (v7 and v8) to a tuple.

    Various implementations were tested on the corpus of all browse() calls
    performed during a full crawler run (after having installed all website_*
    modules) and this one was the most efficient overall.

    A possible bit of correctness was sacrificed by not doing any test on
    Iterable and just assuming that any non-atomic type was an iterable of
    some kind.

    :rtype: tuple
    """
    # much of the corpus is falsy objects (empty list, tuple or set, None)
    if not arg:
        return ()

    # `type in set` is significantly faster (because more restrictive) than
    # isinstance(arg, set) or issubclass(type, set); and for new-style classes
    # obj.__class__ is equivalent to but faster than type(obj). Not relevant
    # (and looks much worse) in most cases, but over millions of calls it
    # does have a very minor effect.
    if arg.__class__ in atoms:
        return arg,

    return tuple(arg)

# keep those imports here to avoid dependency cycle errors
from .osv import expression
from .fields import Field, SpecialValue, FailedValue
