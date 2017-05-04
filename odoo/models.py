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
from collections import defaultdict, MutableMapping, OrderedDict
from inspect import getmembers, currentframe
from operator import attrgetter, itemgetter

import babel.dates
import dateutil.relativedelta
import psycopg2
from lxml import etree
from lxml.builder import E

import odoo
from . import SUPERUSER_ID
from . import api
from . import tools
from .exceptions import AccessError, MissingError, ValidationError, UserError
from .osv.query import Query
from .tools import frozendict, lazy_classproperty, lazy_property, ormcache, \
                   Collector, LastOrderedSet, OrderedSet
from .tools.config import config
from .tools.func import frame_codeinfo
from .tools.misc import CountingStream, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from .tools.safe_eval import safe_eval
from .tools.translate import _

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')
_unlink = logging.getLogger(__name__ + '.unlink')

regex_order = re.compile('^(\s*([a-z0-9:_]+|"[a-z0-9:_]+")(\s+(desc|asc))?\s*(,|$))+(?<!,)$', re.I)
regex_object_name = re.compile(r'^[a-z0-9_.]+$')
regex_pg_name = re.compile(r'^[a-z_][a-z0-9_$]*$', re.I)
onchange_v7 = re.compile(r"^(\w+)\((.*)\)$")

AUTOINIT_RECALCULATE_STORED_FIELDS = 1000

def check_object_name(name):
    """ Check if the given name is a valid model name.

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
        raise ValidationError("Invalid characters in table name %r" % name)
    if len(name) > 63:
        raise ValidationError("Table name %r is too long" % name)

# match private methods, to prevent their remote invocation
regex_private = re.compile(r'^(_.*|init)$')

def check_method_name(name):
    """ Raise an ``AccessError`` if ``name`` is a private method name. """
    if regex_private.match(name):
        raise AccessError(_('Private methods (such as %s) cannot be called remotely.') % (name,))

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


class MetaModel(api.Meta):
    """ The metaclass of all model classes.
        Its main purpose is to register the models per module.
    """

    module_to_models = defaultdict(list)

    def __init__(self, name, bases, attrs):
        if not self._register:
            self._register = True
            super(MetaModel, self).__init__(name, bases, attrs)
            return

        if not hasattr(self, '_module'):
            self._module = self._get_addon_name(self.__module__)

        # Remember which models to instanciate for this module.
        if not self._custom:
            self.module_to_models[self._module].append(self)

        # check for new-api conversion error: leave comma after field definition
        for key, val in attrs.iteritems():
            if type(val) is tuple and len(val) == 1 and isinstance(val[0], Field):
                _logger.error("Trailing comma after field definition: %s.%s", self, key)
            if isinstance(val, Field):
                val.args = dict(val.args, _module=self._module)

    def _get_addon_name(self, full_name):
        # The (OpenERP) module name can be in the ``odoo.addons`` namespace
        # or not. For instance, module ``sale`` can be imported as
        # ``odoo.addons.sale`` (the right way) or ``sale`` (for backward
        # compatibility).
        module_parts = full_name.split('.')
        if len(module_parts) > 2 and module_parts[:2] == ['odoo', 'addons']:
            addon_name = full_name.split('.')[2]
        else:
            addon_name = full_name.split('.')[0]
        return addon_name


class NewId(object):
    """ Pseudo-ids for new records. """
    def __nonzero__(self):
        return False

IdType = (int, long, str, unicode, NewId)


# maximum number of prefetched records
PREFETCH_MAX = 1000

# special columns automatically created by the ORM
LOG_ACCESS_COLUMNS = ['create_uid', 'create_date', 'write_uid', 'write_date']
MAGIC_COLUMNS = ['id'] + LOG_ACCESS_COLUMNS


class BaseModel(object):
    """ Base class for Odoo models.

    Odoo models are created by inheriting:

    *   :class:`Model` for regular database-persisted models

    *   :class:`TransientModel` for temporary data, stored in the database but
        automatically vacuumed every so often

    *   :class:`AbstractModel` for abstract super classes meant to be shared by
        multiple inheriting models

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
    _auto = False               # don't create any database backend
    _register = False           # not visible in ORM registry
    _abstract = True            # whether model is abstract
    _transient = False          # whether model is transient

    _name = None                # the model name
    _description = None         # the model's informal name
    _custom = False             # should be True for custom models only

    _inherit = None             # Python-inherited models ('model' or ['model'])
    _inherits = {}              # inherited models {'parent_model': 'm2o_field'}
    _constraints = []           # Python constraints (old API)

    _table = None               # SQL table name used by model
    _sequence = None            # SQL sequence to use for ID field
    _sql_constraints = []       # SQL constraints [(name, sql_def, message)]

    _rec_name = None            # field to use for labeling records
    _order = 'id'               # default order for searching results
    _parent_name = 'parent_id'  # the many2one field used as parent field
    _parent_store = False       # set to True to compute MPTT (parent_left, parent_right)
    _parent_order = False       # order to use for siblings in MPTT
    _date_name = 'date'         # field to use for default calendar view
    _fold_name = 'fold'         # field to determine folded groups in kanban views

    _needaction = False         # whether the model supports "need actions" (see mail)
    _translate = True           # False disables translations export for this model

    _depends = {}               # dependencies of models backed up by sql views
                                # {model_name: field_names, ...}

    # default values for _transient_vacuum()
    _transient_check_count = 0
    _transient_max_count = lazy_classproperty(lambda _: config.get('osv_memory_count_limit'))
    _transient_max_hours = lazy_classproperty(lambda _: config.get('osv_memory_age_limit'))

    CONCURRENCY_CHECK_FIELD = '__last_update'

    @api.model
    def view_init(self, fields_list):
        """ Override this method to do specific things when a form view is
        opened. This method is invoked by :meth:`~default_get`.
        """
        pass

    @api.model_cr_context
    def _field_create(self):
        """ Reflect the models and its fields in the models 'ir.model' and
        'ir.model.fields'. Also create entries in 'ir.model.data' if the key
        'module' is passed to the context.
        """
        cr = self._cr

        # create/update the entries in 'ir.model' and 'ir.model.data'
        params = {
            'model': self._name,
            'name': self._description,
            'info': next(cls.__doc__ for cls in type(self).mro() if cls.__doc__),
            'state': 'manual' if self._custom else 'base',
            'transient': self._transient,
        }
        cr.execute(""" UPDATE ir_model
                       SET name=%(name)s, info=%(info)s, transient=%(transient)s
                       WHERE model=%(model)s
                       RETURNING id """, params)
        if not cr.rowcount:
            cr.execute(""" INSERT INTO ir_model (model, name, info, state, transient)
                           VALUES (%(model)s, %(name)s, %(info)s, %(state)s, %(transient)s)
                           RETURNING id """, params)
        model = self.env['ir.model'].browse(cr.fetchone()[0])
        self._context['todo'].append((10, model.modified, [['name', 'info', 'transient']]))

        if self._module == self._context.get('module'):
            # self._module is the name of the module that last extended self
            xmlid = 'model_' + self._name.replace('.', '_')
            cr.execute("SELECT * FROM ir_model_data WHERE name=%s AND module=%s",
                       (xmlid, self._context['module']))
            if not cr.rowcount:
                cr.execute(""" INSERT INTO ir_model_data (name, date_init, date_update, module, model, res_id)
                               VALUES (%s, (now() at time zone 'UTC'), (now() at time zone 'UTC'), %s, %s, %s) """,
                           (xmlid, self._context['module'], 'ir.model', model.id))

        # create/update the entries in 'ir.model.fields' and 'ir.model.data'
        cr.execute("SELECT * FROM ir_model_fields WHERE model=%s", (self._name,))
        cols = {rec['name']: rec for rec in cr.dictfetchall()}

        Fields = self.env['ir.model.fields']

        # sparse fields should be created at the end, as they depend on their serialized field
        model_fields = sorted(self._fields.itervalues(), key=lambda field: bool(field.sparse))
        for field in model_fields:
            vals = {
                'model_id': model.id,
                'model': self._name,
                'name': field.name,
                'field_description': field.string,
                'help': field.help or None,
                'ttype': field.type,
                'relation': field.comodel_name or None,
                'index': bool(field.index),
                'store': bool(field.store),
                'copy': bool(field.copy),
                'related': ".".join(field.related) if field.related else None,
                'readonly': bool(field.readonly),
                'required': bool(field.required),
                'selectable': bool(field.search or field.store),
                'translate': bool(field.translate),
                'relation_field': field.inverse_name if field.type == 'one2many' else None,
                'serialization_field_id': None,
                'relation_table': field.relation if field.type == 'many2many' else None,
                'column1': field.column1 if field.type == 'many2many' else None,
                'column2': field.column2 if field.type == 'many2many' else None,
            }
            if field.sparse:
                # resolve link to serialization_field if specified by name
                serialization_field = Fields.search([('model', '=', vals['model']), ('name', '=', field.sparse)])
                if not serialization_field:
                    raise UserError(_("Serialization field `%s` not found for sparse field `%s`!") % (field.sparse, field.name))
                vals['serialization_field_id'] = serialization_field.id

            if field.name not in cols:
                query = "INSERT INTO ir_model_fields (%s) VALUES (%s) RETURNING id" % (
                    ",".join(vals),
                    ",".join("%%(%s)s" % name for name in vals),
                )
                cr.execute(query, vals)
                field_id = cr.fetchone()[0]
                self._context['todo'].append((20, Fields.browse(field_id).modified, [list(vals)]))

                module = field._module or self._context.get('module')
                if module:
                    xmlid = 'field_%s_%s' % (self._table, field.name)
                    cr.execute("SELECT name FROM ir_model_data WHERE name=%s", (xmlid,))
                    if cr.fetchone():
                        xmlid = xmlid + "_" + str(field_id)
                    cr.execute(""" INSERT INTO ir_model_data (name, date_init, date_update, module, model, res_id)
                                   VALUES (%s, (now() at time zone 'UTC'), (now() at time zone 'UTC'), %s, %s, %s) """,
                               (xmlid, module, 'ir.model.fields', field_id))

            elif not all(cols[field.name][key] == vals[key] for key in vals):
                names = set(vals) - {'model', 'name'}
                query = "UPDATE ir_model_fields SET %s WHERE model=%%(model)s AND name=%%(name)s RETURNING id" % (
                    ",".join("%s=%%(%s)s" % (name, name) for name in names),
                )
                cr.execute(query, vals)
                field_id = cr.fetchone()[0]
                self._context['todo'].append((20, Fields.browse(field_id).modified, [names]))

        if not self.pool._init:
            # remove ir.model.fields that are not in self._fields
            fields = Fields.browse([col['id']
                                    for name, col in cols.iteritems()
                                    if name not in self._fields])
            # add key '_force_unlink' in context to (1) force the removal of the
            # fields and (2) not reload the registry
            fields.with_context(_force_unlink=True).unlink()

        self.invalidate_cache()

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

    @api.model
    def _pop_field(self, name):
        """ Remove the field with the given ``name`` from the model.
            This method should only be used for manual fields.
        """
        cls = type(self)
        field = cls._fields.pop(name, None)
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

    def compute_concurrency_field(self):
        for record in self:
            record[self.CONCURRENCY_CHECK_FIELD] = odoo.fields.Datetime.now()

    @api.depends('create_date', 'write_date')
    def compute_concurrency_field_with_access(self):
        for record in self:
            record[self.CONCURRENCY_CHECK_FIELD] = \
                record.write_date or record.create_date or odoo.fields.Datetime.now()

    #
    # Goal: try to apply inheritance at the instantiation level and
    #       put objects in the pool var
    #
    @classmethod
    def _build_model(cls, pool, cr):
        """ Instantiate a given model in the registry.

        This method creates or extends a "registry" class for the given model.
        This "registry" class carries inferred model metadata, and inherits (in
        the Python sense) from all classes that define the model, and possibly
        other registry classes.

        """

        # In the simplest case, the model's registry class inherits from cls and
        # the other classes that define the model in a flat hierarchy. The
        # registry contains the instance ``model`` (on the left). Its class,
        # ``ModelClass``, carries inferred metadata that is shared between all
        # the model's instances for this registry only.
        #
        #   class A1(Model):                          Model
        #       _name = 'a'                           / | \
        #                                            A3 A2 A1
        #   class A2(Model):                          \ | /
        #       _inherit = 'a'                      ModelClass
        #                                             /   \
        #   class A3(Model):                      model   recordset
        #       _inherit = 'a'
        #
        # When a model is extended by '_inherit', its base classes are modified
        # to include the current class and the other inherited model classes.
        # Note that we actually inherit from other ``ModelClass``, so that
        # extensions to an inherited model are immediately visible in the
        # current model class, like in the following example:
        #
        #   class A1(Model):
        #       _name = 'a'                           Model
        #                                            / / \ \
        #   class B1(Model):                        / A2 A1 \
        #       _name = 'b'                        /   \ /   \
        #                                         B2  ModelA  B1
        #   class B2(Model):                       \    |    /
        #       _name = 'b'                         \   |   /
        #       _inherit = ['a', 'b']                \  |  /
        #                                             ModelB
        #   class A2(Model):
        #       _inherit = 'a'

        # Keep links to non-inherited constraints in cls; this is useful for
        # instance when exporting translations
        cls._local_constraints = cls.__dict__.get('_constraints', [])
        cls._local_sql_constraints = cls.__dict__.get('_sql_constraints', [])

        # determine inherited models
        parents = cls._inherit
        parents = [parents] if isinstance(parents, basestring) else (parents or [])

        # determine the model's name
        name = cls._name or (len(parents) == 1 and parents[0]) or cls.__name__

        # all models except 'base' implicitly inherit from 'base'
        if name != 'base':
            parents = list(parents) + ['base']

        # create or retrieve the model's class
        if name in parents:
            if name not in pool:
                raise TypeError("Model %r does not exist in registry." % name)
            ModelClass = pool[name]
            ModelClass._build_model_check_base(cls)
            check_parent = ModelClass._build_model_check_parent
        else:
            ModelClass = type(name, (BaseModel,), {
                '_name': name,
                '_register': False,
                '_original_module': cls._module,
                '_inherit_children': OrderedSet(),      # names of children models
                '_inherits_children': set(),            # names of children models
                '_fields': {},                          # populated in _setup_base()
            })
            check_parent = cls._build_model_check_parent

        # determine all the classes the model should inherit from
        bases = LastOrderedSet([cls])
        for parent in parents:
            if parent not in pool:
                raise TypeError("Model %r inherits from non-existing model %r." % (name, parent))
            parent_class = pool[parent]
            if parent == name:
                for base in parent_class.__bases__:
                    bases.add(base)
            else:
                check_parent(cls, parent_class)
                bases.add(parent_class)
                parent_class._inherit_children.add(name)
        ModelClass.__bases__ = tuple(bases)

        # determine the attributes of the model's class
        ModelClass._build_model_attributes(pool)

        check_pg_name(ModelClass._table)

        # Transience
        if ModelClass._transient:
            assert ModelClass._log_access, \
                "TransientModels must have log_access turned on, " \
                "in order to implement their access rights policy"

        # link the class to the registry, and update the registry
        ModelClass.pool = pool
        pool[name] = ModelClass

        # backward compatibility: instantiate the model, and initialize it
        model = object.__new__(ModelClass)
        model.__init__(pool, cr)

        return ModelClass

    @classmethod
    def _build_model_check_base(model_class, cls):
        """ Check whether ``model_class`` can be extended with ``cls``. """
        if model_class._abstract and not cls._abstract:
            msg = ("%s transforms the abstract model %r into a non-abstract model. "
                   "That class should either inherit from AbstractModel, or set a different '_name'.")
            raise TypeError(msg % (cls, model_class._name))
        if model_class._transient != cls._transient:
            if model_class._transient:
                msg = ("%s transforms the transient model %r into a non-transient model. "
                       "That class should either inherit from TransientModel, or set a different '_name'.")
            else:
                msg = ("%s transforms the model %r into a transient model. "
                       "That class should either inherit from Model, or set a different '_name'.")
            raise TypeError(msg % (cls, model_class._name))

    @classmethod
    def _build_model_check_parent(model_class, cls, parent_class):
        """ Check whether ``model_class`` can inherit from ``parent_class``. """
        if model_class._abstract and not parent_class._abstract:
            msg = ("In %s, the abstract model %r cannot inherit from the non-abstract model %r.")
            raise TypeError(msg % (cls, model_class._name, parent_class._name))

    @classmethod
    def _build_model_attributes(cls, pool):
        """ Initialize base model attributes. """
        cls._description = cls._name
        cls._table = cls._name.replace('.', '_')
        cls._sequence = None
        cls._log_access = cls._auto
        cls._inherits = {}
        cls._depends = {}
        cls._constraints = {}
        cls._sql_constraints = []

        for base in reversed(cls.__bases__):
            if not getattr(base, 'pool', None):
                # the following attributes are not taken from model classes
                cls._description = base._description or cls._description
                cls._table = base._table or cls._table
                cls._sequence = base._sequence or cls._sequence
                cls._log_access = getattr(base, '_log_access', cls._log_access)

            cls._inherits.update(base._inherits)

            for mname, fnames in base._depends.iteritems():
                cls._depends[mname] = cls._depends.get(mname, []) + fnames

            for cons in base._constraints:
                # cons may override a constraint with the same function name
                cls._constraints[getattr(cons[0], '__name__', id(cons[0]))] = cons

            cls._sql_constraints += base._sql_constraints

        cls._sequence = cls._sequence or (cls._table + '_id_seq')
        cls._constraints = cls._constraints.values()

        # update _inherits_children of parent models
        for parent_name in cls._inherits:
            pool[parent_name]._inherits_children.add(cls._name)

        # recompute attributes of _inherit_children models
        for child_name in cls._inherit_children:
            child_class = pool[child_name]
            child_class._build_model_attributes(pool)

    @api.model
    def _add_manual_fields(self, partial):
        IrModelFields = self.env['ir.model.fields']
        manual_fields = self.pool.get_manual_fields(self._cr, self._name)
        for name, field_data in manual_fields.iteritems():
            if name not in self._fields:
                field = IrModelFields._instanciate(field_data, partial)
                if field:
                    self._add_field(name, field)

    @classmethod
    def _init_constraints_onchanges(cls):
        # store sql constraint error messages
        for (key, _, msg) in cls._sql_constraints:
            cls.pool._sql_error[cls._table + '_' + key] = msg

        # reset properties memoized on cls
        cls._constraint_methods = BaseModel._constraint_methods
        cls._onchange_methods = BaseModel._onchange_methods

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
                elif not (field.store or field.inverse):
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
        return None

    def __init__(self, pool, cr):
        """ Deprecated method to initialize the model. """
        pass

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
    def _export_rows(self, fields):
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
                        current[i] = field.convert_to_export(value, record)
                    else:
                        primary_done.append(name)

                        # This is a special case, its strange behavior is intended!
                        if field.type == 'many2many' and len(path) > 1 and path[1] == 'id':
                            xml_ids = [r.__export_xml_id() for r in value]
                            current[i] = ','.join(xml_ids) or False
                            continue

                        # recursively export the fields that follow name
                        fields2 = [(p[1:] if p and p[0] == name else []) for p in fields]
                        lines2 = value._export_rows(fields2)
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

    # backward compatibility
    __export_rows = _export_rows

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
        return {'datas': self._export_rows(fields_to_export)}

    @api.model
    def load(self, fields, data):
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
        :returns: {ids: list(int)|False, messages: [Message]}
        """
        # determine values of mode, current_module and noupdate
        mode = self._context.get('mode', 'init')
        current_module = self._context.get('module', '')
        noupdate = self._context.get('noupdate', False)

        # add current module in context for the conversion of xml ids
        self = self.with_context(_import_current_module=current_module)

        cr = self._cr
        cr.execute('SAVEPOINT model_load')

        fields = map(fix_import_export_id_paths, fields)
        fg = self.fields_get()

        ids = []
        messages = []
        ModelData = self.env['ir.model.data']
        ModelData.clear_caches()
        extracted = self._extract_records(fields, data, log=messages.append)
        converted = self._convert_records(extracted, log=messages.append)
        for id, xid, record, info in converted:
            try:
                cr.execute('SAVEPOINT model_load_save')
            except psycopg2.InternalError as e:
                # broken transaction, exit and hope the source error was
                # already logged
                if not any(message['type'] == 'error' for message in messages):
                    messages.append(dict(info, type='error',message=u"Unknown database error: '%s'" % e))
                break
            try:
                ids.append(ModelData._update(self._name, current_module, record, mode=mode,
                                             xml_id=xid, noupdate=noupdate, res_id=id))
                cr.execute('RELEASE SAVEPOINT model_load_save')
            except psycopg2.Warning as e:
                messages.append(dict(info, type='warning', message=str(e)))
                cr.execute('ROLLBACK TO SAVEPOINT model_load_save')
            except psycopg2.Error as e:
                messages.append(dict(info, type='error', **PGERROR_TO_OE[e.pgcode](self, fg, info, e)))
                # Failed to write, log to messages, rollback savepoint (to
                # avoid broken transaction) and keep going
                cr.execute('ROLLBACK TO SAVEPOINT model_load_save')
            except Exception as e:
                message = (_('Unknown error during import:') + ' %s: %s' % (type(e), unicode(e)))
                moreinfo = _('Resolve other errors first')
                messages.append(dict(info, type='error', message=message, moreinfo=moreinfo))
                # Failed for some reason, perhaps due to invalid data supplied,
                # rollback savepoint and keep going
                cr.execute('ROLLBACK TO SAVEPOINT model_load_save')
        if any(message['type'] == 'error' for message in messages):
            cr.execute('ROLLBACK TO SAVEPOINT model_load')
            ids = False

        if ids and self._context.get('defer_parent_store_computation'):
            self._parent_store_compute()

        return {'ids': ids, 'messages': messages}

    def _add_fake_fields(self, fields):
        from odoo.fields import Char, Integer
        fields[None] = Char('rec_name')
        fields['id'] = Char('External ID')
        fields['.id'] = Integer('Database ID')
        return fields

    @api.model
    def _extract_records(self, fields_, data, log=lambda a: None):
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
        fields = self._add_fake_fields(fields)
        # m2o fields can't be on multiple lines so exclude them from the
        # is_relational field rows filter, but special-case it later on to
        # be handled with relational fields (as it can have subfields)
        is_relational = lambda field: fields[field].relational
        get_o2m_values = itemgetter_tuple([
            index
            for index, fnames in enumerate(fields_)
            if fields[fnames[0]].type == 'one2many'
        ])
        get_nono2m_values = itemgetter_tuple([
            index
            for index, fnames in enumerate(fields_)
            if fields[fnames[0]].type != 'one2many'
        ])
        # Checks if the provided row has any non-empty one2many fields
        def only_o2m_values(row):
            return any(get_o2m_values(row)) and not any(get_nono2m_values(row))

        index = 0
        while index < len(data):
            row = data[index]

            # copy non-relational fields to record dict
            record = {fnames[0]: value
                      for fnames, value in itertools.izip(fields_, row)
                      if not is_relational(fnames[0])}

            # Get all following rows which have relational values attached to
            # the current record (no non-relational values)
            record_span = itertools.takewhile(
                only_o2m_values, itertools.islice(data, index + 1, None))
            # stitch record row back on for relational fields
            record_span = list(itertools.chain([row], record_span))
            for relfield in set(fnames[0] for fnames in fields_ if is_relational(fnames[0])):
                comodel = self.env[fields[relfield].comodel_name]

                # get only cells for this sub-field, should be strictly
                # non-empty, field path [None] is for name_get field
                indices, subfields = zip(*((index, fnames[1:] or [None])
                                           for index, fnames in enumerate(fields_)
                                           if fnames[0] == relfield))

                # return all rows which have at least one value for the
                # subfields of relfield
                relfield_data = filter(any, map(itemgetter_tuple(indices), record_span))
                record[relfield] = [
                    subrecord
                    for subrecord, _subinfo in comodel._extract_records(subfields, relfield_data, log=log)
                ]

            yield record, {'rows': {
                'from': index,
                'to': index + len(record_span) - 1,
            }}
            index += len(record_span)

    @api.model
    def _convert_records(self, records, log=lambda a: None):
        """ Converts records from the source iterable (recursive dicts of
        strings) into forms which can be written to the database (via
        self.create or (ir.model.data)._update)

        :returns: a list of triplets of (id, xid, record)
        :rtype: list((int|None, str|None, dict))
        """
        field_names = {name: field.string for name, field in self._fields.iteritems()}
        if self.env.lang:
            field_names.update(self.env['ir.translation'].get_field_string(self._name))

        convert = self.env['ir.fields.converter'].for_model(self)

        def _log(base, record, field, exception):
            type = 'warning' if isinstance(exception, Warning) else 'error'
            # logs the logical (not human-readable) field name for automated
            # processing of response, but injects human readable in message
            exc_vals = dict(base, record=record, field=field_names[field])
            record = dict(base, type=type, record=record, field=field,
                          message=unicode(exception.args[0]) % exc_vals)
            if len(exception.args) > 1 and exception.args[1]:
                record.update(exception.args[1])
            log(record)

        stream = CountingStream(records)
        for record, extras in stream:
            # xid
            xid = record.get('id', False)
            # dbid
            dbid = False
            if '.id' in record:
                try:
                    dbid = int(record['.id'])
                except ValueError:
                    # in case of overridden id column
                    dbid = record['.id']
                if not self.search([('id', '=', dbid)]):
                    log(dict(extras,
                        type='error',
                        record=stream.index,
                        field='.id',
                        message=_(u"Unknown database identifier '%s'") % dbid))
                    dbid = False

            converted = convert(record, functools.partial(_log, extras, stream.index))

            yield dbid, xid, converted, dict(extras, record=stream.index)

    @api.multi
    def _validate_fields(self, field_names):
        field_names = set(field_names)

        # old-style constraint methods
        trans = self.env['ir.translation']
        errors = []
        for func, msg, names in self._constraints:
            try:
                # validation must be context-independent; call ``func`` without context
                valid = names and not (set(names) & field_names)
                valid = valid or func(self)
                extra_error = None
            except Exception, e:
                _logger.debug('Exception while validating constraint', exc_info=True)
                valid = False
                extra_error = tools.ustr(e)
            if not valid:
                if callable(msg):
                    res_msg = msg(self)
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

            # 3. look up field.default
            if field and field.default:
                defaults[name] = field.default(self)
                continue

            # 4. delegate to parent model
            if field and field.inherited:
                field = field.related_field
                parent_fields[field.model_name].append(field.name)

        # convert default values to the right format
        defaults = self._convert_to_write(defaults)

        # add default values for inherited fields
        for model, names in parent_fields.iteritems():
            defaults.update(self.env[model].default_get(names))

        return defaults

    @api.model
    def fields_get_keys(self):
        return list(self._fields)

    @api.model
    def _rec_name_fallback(self):
        # if self._rec_name is set, it belongs to self._fields
        return self._rec_name or 'id'

    #
    # Override this method if you need a window title that depends on the context
    #
    @api.model
    def view_header_get(self, view_id=None, view_type='form'):
        return False

    @api.model
    def user_has_groups(self, groups):
        """Return true if the user is member of at least one of the groups in
        ``groups``, and is not a member of any of the groups in ``groups``
        preceded by ``!``. Typically used to resolve ``groups`` attribute in
        view and model definitions.

        :param str groups: comma-separated list of fully-qualified group
            external IDs, e.g., ``base.group_user,base.group_system``,
            optionally preceded by ``!``
        :return: True if the current user is a member of one of the given groups
            not preceded by ``!`` and is not member of any of the groups
            preceded by ``!``
        """
        from odoo.http import request
        user = self.env.user

        has_groups = []
        not_has_groups = []
        for group_ext_id in groups.split(','):
            group_ext_id = group_ext_id.strip()
            if group_ext_id[0] == '!':
                not_has_groups.append(group_ext_id[1:])
            else:
                has_groups.append(group_ext_id)

        for group_ext_id in not_has_groups:
            if group_ext_id == 'base.group_no_one':
                # check: the group_no_one is effective in debug mode only
                if user.has_group(group_ext_id) and request and request.debug:
                    return False
            else:
                if user.has_group(group_ext_id):
                    return False

        for group_ext_id in has_groups:
            if group_ext_id == 'base.group_no_one':
                # check: the group_no_one is effective in debug mode only
                if user.has_group(group_ext_id) and request and request.debug:
                    return True
            else:
                if user.has_group(group_ext_id):
                    return True

        return not has_groups

    @api.model
    def _get_default_form_view(self):
        """ Generates a default single-line form view using all fields
        of the current model.

        :returns: a form view as an lxml document
        :rtype: etree._Element
        """
        group = E.group(col="4")
        for fname, field in self._fields.iteritems():
            if field.automatic:
                continue
            elif field.type in ('one2many', 'many2many', 'text', 'html'):
                group.append(E.newline())
                group.append(E.field(name=fname, colspan="4"))
                group.append(E.newline())
            else:
                group.append(E.field(name=fname))
        group.append(E.separator())
        return E.form(E.sheet(group, string=self._description))

    @api.model
    def _get_default_search_view(self):
        """ Generates a single-field search view, based on _rec_name.

        :returns: a tree view as an lxml document
        :rtype: etree._Element
        """
        element = E.field(name=self._rec_name_fallback())
        return E.search(element, string=self._description)

    @api.model
    def _get_default_tree_view(self):
        """ Generates a single-field tree view, based on _rec_name.

        :returns: a tree view as an lxml document
        :rtype: etree._Element
        """
        element = E.field(name=self._rec_name_fallback())
        return E.tree(element, string=self._description)

    @api.model
    def _get_default_pivot_view(self):
        """ Generates an empty pivot view.

        :returns: a pivot view as an lxml document
        :rtype: etree._Element
        """
        return E.pivot(string=self._description)

    @api.model
    def _get_default_kanban_view(self):
        """ Generates a single-field kanban view, based on _rec_name.

        :returns: a kanban view as an lxml document
        :rtype: etree._Element
        """

        field = E.field(name=self._rec_name_fallback())
        div = E.div(field, {'class': "oe_kanban_card oe_kanban_global_click"})
        kanban_box = E.t(div, {'t-name': "kanban-box"})
        templates = E.templates(kanban_box)
        return E.kanban(templates, string=self._description)

    @api.model
    def _get_default_graph_view(self):
        """ Generates a single-field graph view, based on _rec_name.

        :returns: a graph view as an lxml document
        :rtype: etree._Element
        """
        element = E.field(name=self._rec_name_fallback())
        return E.graph(element, string=self._description)

    @api.model
    def _get_default_calendar_view(self):
        """ Generates a default calendar view by trying to infer
        calendar fields from a number of pre-set attribute names

        :returns: a calendar view
        :rtype: etree._Element
        """
        def set_first_of(seq, in_, to):
            """Sets the first value of ``seq`` also found in ``in_`` to
            the ``to`` attribute of the ``view`` being closed over.

            Returns whether it's found a suitable value (and set it on
            the attribute) or not
            """
            for item in seq:
                if item in in_:
                    view.set(to, item)
                    return True
            return False

        view = E.calendar(string=self._description)
        view.append(E.field(name=self._rec_name_fallback()))

        if self._date_name not in self._fields:
            date_found = False
            for dt in ['date', 'date_start', 'x_date', 'x_date_start']:
                if dt in self._fields:
                    self._date_name = dt
                    break
            else:
                raise UserError(_("Insufficient fields for Calendar View!"))
        view.set('date_start', self._date_name)

        set_first_of(["user_id", "partner_id", "x_user_id", "x_partner_id"],
                     self._fields, 'color')

        if not set_first_of(["date_stop", "date_end", "x_date_stop", "x_date_end"],
                            self._fields, 'date_stop'):
            if not set_first_of(["date_delay", "planned_hours", "x_date_delay", "x_planned_hours"],
                                self._fields, 'date_delay'):
                raise UserError(_("Insufficient fields to generate a Calendar View for %s, missing a date_stop or a date_delay") % self._name)

        return view

    @api.model
    def load_views(self, views, options=None):
        """ Returns the fields_views of given views, and optionally filters and fields.

        :param views: list of [view_id, view_type]
        :param options['toolbar']: True to include contextual actions when loading fields_views
        :param options['load_filters']: True to return the model's filters
        :param options['action_id']: id of the action to get the filters
        :param options['load_fields']: True to load the model's fields
        :return: dictionary with fields_views, filters and fields
        """
        options = options or {}
        result = {}

        toolbar = options.get('toolbar')
        result['fields_views'] = {
            v_type: self.fields_view_get(v_id, v_type if v_type != 'list' else 'tree',
                                         toolbar=toolbar if v_type != 'search' else False)
            for [v_id, v_type] in views
        }

        if options.get('load_filters'):
            result['filters'] = self.env['ir.filters'].get_filters(self._name, options.get('action_id'))

        if options.get('load_fields'):
            result['fields'] = self.fields_get()

        return result

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
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
        View = self.env['ir.ui.view']

        result = {
            'model': self._name,
            'field_parent': False,
        }

        # try to find a view_id if none provided
        if not view_id:
            # <view_type>_view_ref in context can be used to overrride the default view
            view_ref_key = view_type + '_view_ref'
            view_ref = self._context.get(view_ref_key)
            if view_ref:
                if '.' in view_ref:
                    module, view_ref = view_ref.split('.', 1)
                    query = "SELECT res_id FROM ir_model_data WHERE model='ir.ui.view' AND module=%s AND name=%s"
                    self._cr.execute(query, (module, view_ref))
                    view_ref_res = self._cr.fetchone()
                    if view_ref_res:
                        view_id = view_ref_res[0]
                else:
                    _logger.warning('%r requires a fully-qualified external id (got: %r for model %s). '
                        'Please use the complete `module.view_id` form instead.', view_ref_key, view_ref,
                        self._name)

            if not view_id:
                # otherwise try to find the lowest priority matching ir.ui.view
                view_id = View.default_view(self._name, view_type)

        # context for post-processing might be overriden
        if view_id:
            # read the view with inherited views applied
            root_view = View.browse(view_id).read_combined(['id', 'name', 'field_parent', 'type', 'model', 'arch'])
            result['arch'] = root_view['arch']
            result['name'] = root_view['name']
            result['type'] = root_view['type']
            result['view_id'] = root_view['id']
            result['field_parent'] = root_view['field_parent']
            # override context from postprocessing
            if root_view['model'] != self._name:
                View = View.with_context(base_model_name=root_view['model'])
        else:
            # fallback on default views methods if no ir.ui.view could be found
            try:
                arch_etree = getattr(self, '_get_default_%s_view' % view_type)()
                result['arch'] = etree.tostring(arch_etree, encoding='utf-8')
                result['type'] = view_type
                result['name'] = 'default'
            except AttributeError:
                raise UserError(_("No default view of type '%s' could be found !") % view_type)

        # Apply post processing, groups and modifiers etc...
        xarch, xfields = View.postprocess_and_fields(self._name, etree.fromstring(result['arch']), view_id)
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
            IrValues = self.env['ir.values']
            resprint = IrValues.get_actions('client_print_multi', self._name)
            resaction = IrValues.get_actions('client_action_multi', self._name)
            resrelate = IrValues.get_actions('client_action_relate', self._name)
            resprint = [clean(print_)
                        for print_ in resprint
                        if view_type == 'tree' or not print_[2].get('multi')]
            resaction = [clean(action)
                         for action in resaction
                         if view_type == 'tree' or not action[2].get('multi')]
            #When multi="True" set it will display only in More of the list view
            resrelate = [clean(action)
                         for action in resrelate
                         if (action[2].get('multi') and view_type == 'tree') or (not action[2].get('multi') and view_type == 'form')]

            for x in itertools.chain(resprint, resaction, resrelate):
                x['string'] = x['name']

            result['toolbar'] = {
                'print': resprint,
                'action': resaction,
                'relate': resrelate,
            }
        return result

    @api.multi
    def get_formview_id(self):
        """ Return an view id to open the document ``self`` with. This method is
            meant to be overridden in addons that want to give specific view ids
            for example.
        """
        return False

    @api.multi
    def get_formview_action(self):
        """ Return an action to open the document ``self``. This method is meant
            to be overridden in addons that want to give specific view ids for
            example.
        """
        view_id = self.get_formview_id()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'target': 'current',
            'res_id': self.id,
            'context': dict(self._context),
        }

    @api.multi
    def get_access_action(self):
        """ Return an action to open the document. This method is meant to be
        overridden in addons that want to give specific access to the document.
        By default it opens the formview of the document.
        """
        return self[0].get_formview_action()

    @api.model
    def search_count(self, args):
        """ search_count(args) -> int

        Returns the number of records in the current model matching :ref:`the
        provided domain <reference/orm/domains>`.
        """
        res = self.search(args, count=True)
        return res if isinstance(res, (int, long)) else len(res)

    @api.model
    @api.returns('self',
        upgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False: value if count else self.browse(value),
        downgrade=lambda self, value, args, offset=0, limit=None, order=None, count=False: value if count else value.ids)
    def search(self, args, offset=0, limit=None, order=None, count=False):
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
        res = self._search(args, offset=offset, limit=limit, order=order, count=count)
        return res if count else self.browse(res)

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

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        # private implementation of name_search, allows passing a dedicated user
        # for the name_get part to solve some access rights issues
        args = list(args or [])
        # optimize out the default criterion of ``ilike ''`` that matches everything
        if not self._rec_name:
            _logger.warning("Cannot execute name_search, no _rec_name defined on %s", self._name)
        elif not (name == '' and operator == 'ilike'):
            args += [(self._rec_name, operator, name)]
        access_rights_uid = name_get_uid or self._uid
        ids = self._search(args, limit=limit, access_rights_uid=access_rights_uid)
        recs = self.browse(ids)
        return recs.sudo(access_rights_uid).name_get()

    @api.model
    def _add_missing_default_values(self, values):
        # avoid overriding inherited values when parent is set
        avoid_models = {
            parent_model
            for parent_model, parent_field in self._inherits.iteritems()
            if parent_field in values
        }

        # compute missing fields
        missing_defaults = {
            name
            for name, field in self._fields.iteritems()
            if name not in values
            if name not in MAGIC_COLUMNS
            if not (field.inherited and field.related_field.model_name in avoid_models)
        }

        if not missing_defaults:
            return values

        # override defaults with the provided values, never allow the other way around
        defaults = self.default_get(list(missing_defaults))
        for name, value in defaults.iteritems():
            if self._fields[name].type == 'many2many' and value and isinstance(value[0], (int, long)):
                # convert a list of ids into a list of commands
                defaults[name] = [(6, 0, value)]
            elif self._fields[name].type == 'one2many' and value and isinstance(value[0], dict):
                # convert a list of dicts into a list of commands
                defaults[name] = [(0, 0, x) for x in value]
        defaults.update(values)
        return defaults

    @classmethod
    def clear_caches(cls):
        """ Clear the caches

        This clears the caches associated to methods decorated with
        ``tools.ormcache`` or ``tools.ormcache_multi``.
        """
        try:
            cls.pool.cache.clear()
            cls.pool.cache_cleared = True
        except AttributeError:
            pass

    @api.model
    def _read_group_fill_results(self, domain, groupby, remaining_groupbys,
                                 aggregated_fields, count_field,
                                 read_group_result, read_group_order=None):
        """Helper method for filling in empty groups for all possible values of
           the field being grouped by"""
        field = self._fields[groupby]
        if not field.group_expand:
            return read_group_result

        # field.group_expand is the name of a method that returns a list of all
        # aggregated values that we want to display for this field, in the form
        # of a m2o-like pair (key,label).
        # This is useful to implement kanban views for instance, where all
        # columns should be displayed even if they don't contain any record.

        # Grab the list of all groups that should be displayed, including all present groups
        group_ids = [x[groupby][0] for x in read_group_result if x[groupby]]
        groups = self.env[field.comodel_name].browse(group_ids)
        # determine order on groups's model
        order = groups._order
        if read_group_order == groupby + ' desc':
            order = tools.reverse_order(order)
        groups = getattr(self, field.group_expand)(groups, domain, order)
        groups = groups.sudo()

        result_template = dict.fromkeys(aggregated_fields, False)
        result_template[groupby + '_count'] = 0
        if remaining_groupbys:
            result_template['__context'] = {'group_by': remaining_groupbys}

        # Merge the current results (list of dicts) with all groups (recordset).
        # Determine the global order of results from all groups, which is
        # supposed to be in the same order as read_group_result.
        result = OrderedDict((group.id, {}) for group in groups)

        # fill in results from read_group_result
        for left_side in read_group_result:
            left_id = (left_side[groupby] or (False,))[0]
            if not result.get(left_id):
                result[left_id] = left_side
            else:
                result[left_id][count_field] = left_side[count_field]

        # fill in missing results from all groups
        for right_side in groups.name_get():
            right_id = right_side[0]
            if not result[right_id]:
                line = dict(result_template)
                line[groupby] = right_side
                line['__domain'] = [(groupby, '=', right_id)] + domain
                result[right_id] = line

        result = result.values()

        if groups._fold_name in groups._fields:
            for r in result:
                group = groups.browse(r[groupby] and r[groupby][0])
                r['__fold'] = group[groups._fold_name]
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

    @api.model
    def _read_group_prepare_data(self, key, value, groupby_dict):
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
                value = pytz.timezone(self._context['tz']).localize(value)
        return value

    @api.model
    def _read_group_format_result(self, data, annotated_groupbys, groupby, domain):
        """
            Helper method to format the data contained in the dictionary data by 
            adding the domain corresponding to its values, the groupbys in the 
            context and by properly formatting the date/datetime values.

        :param data: a single group
        :param annotated_groupbys: expanded grouping metainformation
        :param groupby: original grouping metainformation
        :param domain: original domain for read_group
        """

        sections = []
        for gb in annotated_groupbys:
            ftype = gb['type']
            value = data[gb['groupby']]

            # full domain for this groupby spec
            d = None
            if value:
                if ftype == 'many2one':
                    value = value[0]
                elif ftype in ('date', 'datetime'):
                    locale = self._context.get('lang') or 'en_US'
                    fmt = DEFAULT_SERVER_DATETIME_FORMAT if ftype == 'datetime' else DEFAULT_SERVER_DATE_FORMAT
                    tzinfo = None
                    range_start = value
                    range_end = value + gb['interval']
                    # value from postgres is in local tz (so range is
                    # considered in local tz e.g. "day" is [00:00, 00:00[
                    # local rather than UTC which could be [11:00, 11:00]
                    # local) but domain and raw value should be in UTC
                    if gb['tz_convert']:
                        tzinfo = range_start.tzinfo
                        range_start = range_start.astimezone(pytz.utc)
                        range_end = range_end.astimezone(pytz.utc)

                    range_start = range_start.strftime(fmt)
                    range_end = range_end.strftime(fmt)
                    if ftype == 'datetime':
                        label = babel.dates.format_datetime(
                            value, format=gb['display_format'],
                            tzinfo=tzinfo, locale=locale
                        )
                    else:
                        label = babel.dates.format_date(
                            value, format=gb['display_format'],
                            locale=locale
                        )
                    data[gb['groupby']] = ('%s/%s' % (range_start, range_end), label)
                    d = [
                        '&',
                        (gb['field'], '>=', range_start),
                        (gb['field'], '<', range_end),
                    ]

            if d is None:
                d = [(gb['field'], '=', value)]
            sections.append(d)
        sections.append(domain)

        data['__domain'] = expression.AND(sections)
        if len(groupby) - len(annotated_groupbys) >= 1:
            data['__context'] = { 'group_by': groupby[len(annotated_groupbys):]}
        del data['id']
        return data

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """
        Get the list of records in list view grouped by the given ``groupby`` fields

        :param domain: list specifying search criteria [['field_name', 'operator', 'value'], ...]
        :param list fields: list of fields present in the list view specified on the object
        :param list groupby: list of groupby descriptions by which the records will be grouped.  
                A groupby description is either a field (then it will be grouped by that field)
                or a string 'field:groupby_function'.  Right now, the only functions supported
                are 'day', 'week', 'month', 'quarter' or 'year', and they only make sense for 
                date/datetime fields.
        :param int offset: optional number of records to skip
        :param int limit: optional max number of records to return
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
        result = self._read_group_raw(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        groupby = [groupby] if isinstance(groupby, basestring) else list(OrderedSet(groupby))
        dt = [
            f for f in groupby
            if self._fields[f.split(':')[0]].type in ('date', 'datetime')
        ]

        # iterate on all results and replace the "full" date/datetime value
        # (range, label) by just the formatted label, in-place
        for group in result:
            for df in dt:
                # could group on a date(time) field which is empty in some
                # records, in which case as with m2o the _raw value will be
                # `False` instead of a (value, label) pair. In that case,
                # leave the `False` value alone
                if group.get(df):
                    group[df] = group[df][1]
        return result

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        self.check_access_rights('read')
        query = self._where_calc(domain)
        fields = fields or [f.name for f in self._fields.itervalues() if f.store]

        groupby = [groupby] if isinstance(groupby, basestring) else list(OrderedSet(groupby))
        groupby_list = groupby[:1] if lazy else groupby
        annotated_groupbys = [self._read_group_process_groupby(gb, query) for gb in groupby_list]
        groupby_fields = [g['field'] for g in annotated_groupbys]
        order = orderby or ','.join([g for g in groupby_list])
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}

        self._apply_ir_rules(query, 'read')
        for gb in groupby_fields:
            assert gb in fields, "Fields in 'groupby' must appear in the list of fields to read (perhaps it's missing in the list view?)"
            assert gb in self._fields, "Unknown field %r in 'groupby'" % gb
            gb_field = self._fields[gb].base_field
            assert gb_field.store and gb_field.column_type, "Fields in 'groupby' must be regular database-persisted fields (no function or related fields), or function fields with store=True"

        aggregated_fields = [
            f for f in fields
            if f != 'sequence'
            if f not in groupby_fields
            for field in [self._fields.get(f)]
            if field
            if field.group_operator
            if field.base_field.store and field.base_field.column_type
        ]

        field_formatter = lambda f: (
            self._fields[f].group_operator,
            self._inherits_join_calc(self._table, f, query),
            f,
        )
        select_terms = ['%s(%s) AS "%s" ' % field_formatter(f) for f in aggregated_fields]

        for gb in annotated_groupbys:
            select_terms.append('%s as "%s" ' % (gb['qualified_field'], gb['groupby']))

        groupby_terms, orderby_terms = self._read_group_prepare(order, aggregated_fields, annotated_groupbys, query)
        from_clause, where_clause, where_clause_params = query.get_sql()
        if lazy and (len(groupby_fields) >= 2 or not self._context.get('group_by_no_leaf')):
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
        self._cr.execute(query, where_clause_params)
        fetched_data = self._cr.dictfetchall()

        if not groupby_fields:
            return fetched_data

        many2onefields = [gb['field'] for gb in annotated_groupbys if gb['type'] == 'many2one']
        if many2onefields:
            data_ids = [r['id'] for r in fetched_data]
            many2onefields = list(set(many2onefields))
            data_dict = {d['id']: d for d in self.browse(data_ids).read(many2onefields)}
            for d in fetched_data:
                d.update(data_dict[d['id']])

        data = map(lambda r: {k: self._read_group_prepare_data(k,v, groupby_dict) for k,v in r.iteritems()}, fetched_data)
        result = [self._read_group_format_result(d, annotated_groupbys, groupby, domain) for d in data]
        if lazy:
            # Right now, read_group only fill results in lazy mode (by default).
            # If you need to have the empty groups in 'eager' mode, then the
            # method _read_group_fill_results need to be completely reimplemented
            # in a sane way 
            result = self._read_group_fill_results(
                domain, groupby_fields[0], groupby[len(annotated_groupbys):],
                aggregated_fields, count_field, result, read_group_order=order,
            )
        return result

    def _inherits_join_add(self, current_model, parent_model_name, query):
        """
        Add missing table SELECT and JOIN clause to ``query`` for reaching the parent table (no duplicates)
        :param current_model: current model object
        :param parent_model_name: name of the parent model for which the clauses should be added
        :param query: query object on which the JOIN should be added
        """
        inherits_field = current_model._inherits[parent_model_name]
        parent_model = self.env[parent_model_name]
        parent_alias, parent_alias_statement = query.add_join((current_model._table, parent_model._table, inherits_field, 'id', inherits_field), implicit=True)
        return parent_alias

    @api.model
    def _inherits_join_calc(self, alias, fname, query, implicit=True, outer=False):
        """
        Adds missing table select and join clause(s) to ``query`` for reaching
        the field coming from an '_inherits' parent table (no duplicates).

        :param alias: name of the initial SQL alias
        :param fname: name of inherited field to reach
        :param query: query object on which the JOIN should be added
        :return: qualified name of field, to be used in SELECT clause
        """
        # INVARIANT: alias is the SQL alias of model._table in query
        model, field = self, self._fields[fname]
        while field.inherited:
            # retrieve the parent model where field is inherited from
            parent_model = self.env[field.related_field.model_name]
            parent_fname = field.related[0]
            # JOIN parent_model._table AS parent_alias ON alias.parent_fname = parent_alias.id
            parent_alias, _ = query.add_join(
                (alias, parent_model._table, parent_fname, 'id', parent_fname),
                implicit=implicit, outer=outer,
            )
            model, alias, field = parent_model, parent_alias, field.related_field
        # handle the case where the field is translated
        if field.translate is True:
            return model._generate_translated_field(alias, fname, query)
        else:
            return '"%s"."%s"' % (alias, fname)

    @api.model_cr
    def _parent_store_compute(self):
        if not self._parent_store:
            return

        _logger.info('Computing parent left and right for table %s...', self._table)
        cr = self._cr
        select = "SELECT id FROM %s WHERE %s=%%s ORDER BY %s" % \
                    (self._table, self._parent_name, self._parent_order)
        update = "UPDATE %s SET parent_left=%%s, parent_right=%%s WHERE id=%%s" % self._table

        def process(root, left):
            """ Set root.parent_left to ``left``, and return root.parent_right + 1 """
            cr.execute(select, (root,))
            right = left + 1
            for (id,) in cr.fetchall():
                right = process(id, right)
            cr.execute(update, (left, right, root))
            return right + 1

        select0 = "SELECT id FROM %s WHERE %s IS NULL ORDER BY %s" % \
                    (self._table, self._parent_name, self._parent_order)
        cr.execute(select0)
        pos = 0
        for (id,) in cr.fetchall():
            pos = process(id, pos)
        self.invalidate_cache(['parent_left', 'parent_right'])
        return True

    @api.model
    def _check_selection_field_value(self, field, value):
        """ Check whether value is among the valid values for the given
            selection/reference field, and raise an exception if not.
        """
        field = self._fields[field]
        field.convert_to_cache(value, self)

    @api.model_cr
    def _check_removed_columns(self, log=False):
        # iterate on the database columns to drop the NOT NULL constraints of
        # fields which were required but have been removed (or will be added by
        # another module)
        cr = self._cr
        cols = [name for name, field in self._fields.iteritems()
                     if field.store and field.column_type]
        cr.execute("SELECT a.attname, a.attnotnull"
                   "  FROM pg_class c, pg_attribute a"
                   " WHERE c.relname=%s"
                   "   AND c.oid=a.attrelid"
                   "   AND a.attisdropped=%s"
                   "   AND pg_catalog.format_type(a.atttypid, a.atttypmod) NOT IN ('cid', 'tid', 'oid', 'xid')"
                   "   AND a.attname NOT IN %s", (self._table, False, tuple(cols))),

        for row in cr.dictfetchall():
            if log:
                _logger.debug("column %s is in the table %s but not in the corresponding object %s",
                              row['attname'], self._table, self._name)
            if row['attnotnull']:
                cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" DROP NOT NULL' % (self._table, row['attname']))
                _schema.debug("Table '%s': column '%s': dropped NOT NULL constraint",
                              self._table, row['attname'])

    @api.model_cr
    def _save_constraint(self, constraint_name, type, definition, module):
        """
        Record the creation of a constraint for this model, to make it possible
        to delete it later when the module is uninstalled. Type can be either
        'f' or 'u' depending on the constraint being a foreign key or not.
        """
        if not module:
            # no need to save constraints for custom models as they're not part
            # of any module
            return
        assert type in ('f', 'u')
        cr = self._cr
        cr.execute("""
            SELECT type, definition FROM ir_model_constraint, ir_module_module
            WHERE ir_model_constraint.module=ir_module_module.id
                AND ir_model_constraint.name=%s
                AND ir_module_module.name=%s
            """, (constraint_name, module))
        constraints = cr.dictfetchone()
        if not constraints:
            cr.execute("""
                INSERT INTO ir_model_constraint
                    (name, date_init, date_update, module, model, type, definition)
                VALUES (%s, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC',
                    (SELECT id FROM ir_module_module WHERE name=%s),
                    (SELECT id FROM ir_model WHERE model=%s), %s, %s)""",
                    (constraint_name, module, self._name, type, definition))
        elif constraints['type'] != type or (definition and constraints['definition'] != definition):
            cr.execute("""
                UPDATE ir_model_constraint
                SET date_update=now() AT TIME ZONE 'UTC', type=%s, definition=%s
                WHERE name=%s AND module = (SELECT id FROM ir_module_module WHERE name=%s)""",
                    (type, definition, constraint_name, module))

    @api.model_cr
    def _drop_constraint(self, source_table, constraint_name):
        self._cr.execute("ALTER TABLE %s DROP CONSTRAINT %s" % (source_table, constraint_name))

    @api.model_cr
    def _save_relation_table(self, relation_table, module):
        """
        Record the creation of a many2many for this model, to make it possible
        to delete it later when the module is uninstalled.
        """
        cr = self._cr
        cr.execute("""
            SELECT 1 FROM ir_model_relation, ir_module_module
            WHERE ir_model_relation.module=ir_module_module.id
                AND ir_model_relation.name=%s
                AND ir_module_module.name=%s
            """, (relation_table, module))
        if not cr.rowcount:
            cr.execute("""INSERT INTO ir_model_relation (name, date_init, date_update, module, model)
                                 VALUES (%s, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC',
                    (SELECT id FROM ir_module_module WHERE name=%s),
                    (SELECT id FROM ir_model WHERE model=%s))""",
                       (relation_table, module, self._name))
            self.invalidate_cache()

    # checked version: for direct m2o starting from ``self``
    def _m2o_add_foreign_key_checked(self, source_field, dest_model, ondelete):
        assert self.is_transient() or not dest_model.is_transient(), \
            'Many2One relationships from non-transient Model to TransientModel are forbidden'
        if self.is_transient() and not dest_model.is_transient():
            # TransientModel relationships to regular Models are annoying
            # usually because they could block deletion due to the FKs.
            # So unless stated otherwise we default them to ondelete=cascade.
            ondelete = ondelete or 'cascade'
        field = self._fields[source_field]
        self._m2o_add_foreign_key_unchecked(self._table, source_field, dest_model, ondelete, field._module)

    # unchecked version: for custom cases, such as m2m relationships
    def _m2o_add_foreign_key_unchecked(self, source_table, source_field, dest_model, ondelete, module):
        fk_def = (source_table, source_field, dest_model._table, ondelete or 'set null', module)
        self._foreign_keys.add(fk_def)
        _schema.debug("Table '%s': added foreign key '%s' with definition=REFERENCES \"%s\" ON DELETE %s", *fk_def[:-1])

    @api.model_cr
    def _m2o_fix_foreign_key(self, source_table, source_field, dest_model, ondelete):
        # Find FK constraint(s) currently established for the m2o field,
        # and see whether they are stale or not
        query = """ SELECT confdeltype as ondelete_rule, conname as constraint_name,
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
                       AND con.contype = 'f' """
        self._cr.execute(query, (source_table, source_field, 'id'))
        constraints = self._cr.dictfetchall()
        if constraints:
            if len(constraints) == 1:
                # Is it the right constraint?
                cons, = constraints
                if cons['ondelete_rule'] != POSTGRES_CONFDELTYPES.get((ondelete or 'set null').upper(), 'a')\
                    or cons['foreign_table'] != dest_model._table:
                    # Wrong FK: drop it and recreate
                    _schema.debug("Table '%s': dropping obsolete FK constraint: '%s'",
                                  source_table, cons['constraint_name'])
                    self._drop_constraint(source_table, cons['constraint_name'])
                else:
                    # it's all good, nothing to do!
                    return
            else:
                # Multiple FKs found for the same field, drop them all, and re-create
                for cons in constraints:
                    _schema.debug("Table '%s': dropping duplicate FK constraints: '%s'",
                                  source_table, cons['constraint_name'])
                    self._drop_constraint(source_table, cons['constraint_name'])

        # (re-)create the FK
        self._m2o_add_foreign_key_checked(source_field, dest_model, ondelete)

    @api.model_cr_context
    def _init_column(self, column_name):
        """ Initialize the value of the given column for existing rows. """
        # get the default value; ideally, we should use default_get(), but it
        # fails due to ir.values not being ready
        field = self._fields[column_name]
        if field.default:
            value = field.default(self)
            value = field.convert_to_cache(value, self, validate=False)
            value = field.convert_to_record(value, self)
            value = field.convert_to_write(value, self)
            value = field.convert_to_column(value, self)
        else:
            value = None
        # Write value if non-NULL, except for booleans for which False means
        # the same as NULL - this saves us an expensive query on large tables.
        necessary = (value is not None) if field.type != 'boolean' else value
        if necessary:
            _logger.debug("Table '%s': setting default value of new column %s to %r",
                          self._table, column_name, value)
            query = 'UPDATE "%s" SET "%s"=%s WHERE "%s" IS NULL' % (
                self._table, column_name, field.column_format, column_name)
            self._cr.execute(query, (value,))
            # this is a disgrace
            self._cr.commit()

    @api.model_cr_context
    def _auto_init(self):
        """ Reflect the model and initialize the database schema of ``self``:
        - create the corresponding table in database,
        - add the parent columns in database,
        - add the '_log_access' columns if required,
        - report on database columns no more existing in ``self._fields``,
        - remove no more existing not null constraints,
        - alter existing database columns to match ``self._fields``,
        - create database tables to match ``self._fields``,
        - add database indices to match ``self._fields``,
        - save in self._foreign_keys a list a foreign keys to create (see
          _auto_end).

        Note: you should not override this method. Instead, you can modify the
        model's database schema by overriding method :meth:`~.init`, which is
        called right after this one.
        """
        assert 'todo' in self._context, "Context not passed correctly to method _auto_init()."

        type(self)._foreign_keys = set()
        raise_on_invalid_object_name(self._name)

        # This prevents anything called by this method (in particular default
        # values) from prefetching a field for which the corresponding column
        # has not been added in database yet!
        self = self.with_context(prefetch_fields=False)

        cr = self._cr
        parent_store_compute = False
        stored_fields = []              # new-style stored fields with compute
        todo_end = self._context['todo']
        update_custom_fields = self._context.get('update_custom_fields', False)
        self._field_create()
        create = not self._table_exist()

        if self._auto:

            if create:
                self._create_table()
                has_rows = False
            else:
                cr.execute('SELECT 1 FROM "%s" LIMIT 1' % self._table)
                has_rows = cr.rowcount

            cr.commit()
            if self._parent_store:
                if not self._parent_columns_exist():
                    self._create_parent_columns()
                    parent_store_compute = True

            self._check_removed_columns(log=False)

            # retrieve existing database columns
            column_data = self._select_column_data()

            for name, field in self._fields.iteritems():
                if name == 'id':
                    continue

                if not field.store:
                    continue

                if field.manual and not update_custom_fields:
                    # Don't update custom (also called manual) fields
                    continue

                if not field.column_type:
                    # the field is not stored as a column
                    if field.check_schema(self) and field.compute:
                        stored_fields.append(field)

                else:
                    res = column_data.get(name)

                    # The column is not found as-is in database. Check whether
                    # it exists with an old name, and rename it.
                    if not res and hasattr(field, 'oldname'):
                        res = column_data.get(field.oldname)
                        if res:
                            cr.execute('ALTER TABLE "%s" RENAME "%s" TO "%s"' % (self._table, field.oldname, name))
                            res['attname'] = name
                            _schema.debug("Table '%s': renamed column '%s' to '%s'", self._table, field.oldname, name)

                    # The column already exists in database. Possibly change its
                    # type, rename it, drop it or change its constraints.
                    if res:
                        f_pg_type = res['typname']
                        f_pg_size = res['size']
                        f_pg_notnull = res['attnotnull']
                        column_type = field.column_type

                        if column_type:
                            converted = False
                            casts = [
                                ('text', 'char', column_type[1], '::' + column_type[1]),
                                ('varchar', 'text', 'TEXT', ''),
                                ('int4', 'float', column_type[1], '::' + column_type[1]),
                                ('date', 'datetime', 'TIMESTAMP', '::TIMESTAMP'),
                                ('timestamp', 'date', 'date', '::date'),
                                ('numeric', 'float', column_type[1], '::' + column_type[1]),
                                ('float8', 'float', column_type[1], '::' + column_type[1]),
                                ('float8', 'monetary', column_type[1], '::' + column_type[1]),
                            ]
                            if f_pg_type == 'varchar' and field.type == 'char' and f_pg_size and (field.size is None or f_pg_size < field.size):
                                try:
                                    with cr.savepoint():
                                        cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" TYPE %s' % (self._table, name, column_type[1]), log_exceptions=False)
                                except psycopg2.NotSupportedError:
                                    # In place alter table cannot be done because a view is depending of this field.
                                    # Do a manual copy. This will drop the view (that will be recreated later)
                                    cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO temp_change_size' % (self._table, name))
                                    cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, name, column_type[1]))
                                    cr.execute('UPDATE "%s" SET "%s"=temp_change_size::%s' % (self._table, name, column_type[1]))
                                    cr.execute('ALTER TABLE "%s" DROP COLUMN temp_change_size CASCADE' % (self._table,))
                                cr.commit()
                                _schema.debug("Table '%s': column '%s' (type varchar) changed size from %s to %s",
                                              self._table, name, f_pg_size or 'unlimited', field.size or 'unlimited')
                            for c in casts:
                                if (f_pg_type == c[0]) and (field.type == c[1]):
                                    if f_pg_type != column_type[0]:
                                        converted = True
                                        try:
                                            with cr.savepoint():
                                                cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" TYPE %s' % (self._table, name, c[2]), log_exceptions=False)
                                        except psycopg2.NotSupportedError:
                                            # can't do inplace change -> use a casted temp column
                                            cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO __temp_type_cast' % (self._table, name))
                                            cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, name, c[2]))
                                            cr.execute('UPDATE "%s" SET "%s"= __temp_type_cast%s' % (self._table, name, c[3]))
                                            cr.execute('ALTER TABLE "%s" DROP COLUMN  __temp_type_cast CASCADE' % (self._table,))
                                        cr.commit()
                                        _schema.debug("Table '%s': column '%s' changed type from %s to %s",
                                                      self._table, name, c[0], c[1])
                                    break

                            if f_pg_type != column_type[0]:
                                if not converted:
                                    i = 0
                                    while True:
                                        newname = name + '_moved' + str(i)
                                        cr.execute("SELECT count(1) FROM pg_class c,pg_attribute a " \
                                            "WHERE c.relname=%s " \
                                            "AND a.attname=%s " \
                                            "AND c.oid=a.attrelid ", (self._table, newname))
                                        if not cr.fetchone()[0]:
                                            break
                                        i += 1
                                    if f_pg_notnull:
                                        cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" DROP NOT NULL' % (self._table, name))
                                    cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % (self._table, name, newname))
                                    cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, name, column_type[1]))
                                    cr.execute("COMMENT ON COLUMN %s.\"%s\" IS %%s" % (self._table, name), (field.string,))
                                    _schema.warning("Table `%s`: column `%s` has changed type (DB=%s, def=%s), data moved to column `%s`",
                                                    self._table, name, f_pg_type, field.type, newname)

                            # if the field is required and hasn't got a NOT NULL constraint
                            if field.required and f_pg_notnull == 0:
                                if has_rows:
                                    self._init_column(name)
                                # add the NOT NULL constraint
                                try:
                                    cr.commit()
                                    cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" SET NOT NULL' % (self._table, name), log_exceptions=False)
                                    _schema.debug("Table '%s': column '%s': added NOT NULL constraint",
                                                  self._table, name)
                                except Exception:
                                    msg = "Table '%s': unable to set a NOT NULL constraint on column '%s' !\n"\
                                        "If you want to have it, you should update the records and execute manually:\n"\
                                        "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL"
                                    _schema.warning(msg, self._table, name, self._table, name)
                                cr.commit()
                            elif not field.required and f_pg_notnull == 1:
                                cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" DROP NOT NULL' % (self._table, name))
                                cr.commit()
                                _schema.debug("Table '%s': column '%s': dropped NOT NULL constraint",
                                              self._table, name)
                            # Verify index
                            indexname = '%s_%s_index' % (self._table, name)
                            cr.execute("SELECT indexname FROM pg_indexes WHERE indexname = %s and tablename = %s", (indexname, self._table))
                            res2 = cr.dictfetchall()
                            if not res2 and field.index:
                                cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (self._table, name, self._table, name))
                                cr.commit()
                                if field.type == 'text':
                                    # FIXME: for fields.text columns we should try creating GIN indexes instead (seems most suitable for an ERP context)
                                    msg = "Table '%s': Adding (b-tree) index for %s column '%s'."\
                                        "This is probably useless (does not work for fulltext search) and prevents INSERTs of long texts"\
                                        " because there is a length limit for indexable btree values!\n"\
                                        "Use a search view instead if you simply want to make the field searchable."
                                    _schema.warning(msg, self._table, field.type, name)
                            if res2 and not field.index:
                                cr.execute('DROP INDEX "%s_%s_index"' % (self._table, name))
                                cr.commit()
                                msg = "Table '%s': dropping index for column '%s' of type '%s' as it is not required anymore"
                                _schema.debug(msg, self._table, name, field.type)

                            if field.type == 'many2one':
                                comodel = self.env[field.comodel_name]
                                if comodel._auto and comodel._table != 'ir_actions':
                                    self._m2o_fix_foreign_key(self._table, name, comodel, field.ondelete)

                    else:
                        # the column doesn't exist in database, create it
                        cr.execute('ALTER TABLE "%s" ADD COLUMN "%s" %s' % (self._table, name, field.column_type[1]))
                        cr.execute("COMMENT ON COLUMN %s.\"%s\" IS %%s" % (self._table, name), (field.string,))
                        _schema.debug("Table '%s': added column '%s' with definition=%s",
                                      self._table, name, field.column_type[1])

                        # initialize it
                        if has_rows:
                            self._init_column(name)

                        # remember new-style stored fields with compute method
                        if field.compute:
                            stored_fields.append(field)

                        # and add constraints if needed
                        if field.type == 'many2one' and field.store:
                            if field.comodel_name not in self.env:
                                raise ValueError(_('There is no reference available for %s') % (field.comodel_name,))
                            comodel = self.env[field.comodel_name]
                            # ir_actions is inherited so foreign key doesn't work on it
                            if comodel._auto and comodel._table != 'ir_actions':
                                self._m2o_add_foreign_key_checked(name, comodel, field.ondelete)
                        if field.index:
                            cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (self._table, name, self._table, name))
                        if field.required:
                            try:
                                cr.commit()
                                cr.execute('ALTER TABLE "%s" ALTER COLUMN "%s" SET NOT NULL' % (self._table, name))
                                _schema.debug("Table '%s': column '%s': added a NOT NULL constraint",
                                              self._table, name)
                            except Exception:
                                msg = "WARNING: unable to set column %s of table %s not null !\n"\
                                    "Try to re-run: openerp-server --update=module\n"\
                                    "If it doesn't work, update records and execute manually:\n"\
                                    "ALTER TABLE %s ALTER COLUMN %s SET NOT NULL"
                                _logger.warning(msg, name, self._table, self._table, name, exc_info=True)
                        cr.commit()

        else:
            cr.execute("SELECT relname FROM pg_class WHERE relkind IN ('r','v') AND relname=%s", (self._table,))
            create = not bool(cr.fetchone())

        cr.commit()     # start a new transaction

        if self._auto:
            self._add_sql_constraints()

        if create:
            self._execute_sql()

        if parent_store_compute:
            self._parent_store_compute()
            cr.commit()

        if stored_fields:
            # trigger computation of new-style stored fields with a compute
            def func():
                fnames = [f.name for f in stored_fields]
                _logger.info("Storing computed values of %s fields %s",
                             self._name, ', '.join(sorted(fnames)))
                recs = self.with_context(active_test=False).search([])
                if recs:
                    recs.invalidate_cache(fnames, recs.ids)
                    for f in stored_fields:
                        recs._recompute_todo(f)

            todo_end.append((1000, func, ()))

    @api.model_cr_context
    def _auto_end(self):
        """ Create the foreign keys recorded by _auto_init. """
        cr = self._cr
        query = 'ALTER TABLE "%s" ADD FOREIGN KEY ("%s") REFERENCES "%s" ON DELETE %s'
        for table1, column, table2, ondelete, module in self._foreign_keys:
            cr.execute(query % (table1, column, table2, ondelete))
            self._save_constraint("%s_%s_fkey" % (table1, column), 'f', False, module)
        cr.commit()
        del type(self)._foreign_keys

    @api.model_cr
    def init(self):
        """ This method is called after :meth:`~._auto_init`, and may be
            overridden to create or modify a model's database schema.
        """
        pass

    @api.model_cr
    def _table_exist(self):
        query = "SELECT relname FROM pg_class WHERE relkind IN ('r','v') AND relname=%s"
        self._cr.execute(query, (self._table,))
        return self._cr.rowcount

    @api.model_cr
    def _create_table(self):
        self._cr.execute('CREATE TABLE "%s" (id SERIAL NOT NULL, PRIMARY KEY(id))' % (self._table,))
        self._cr.execute("COMMENT ON TABLE \"%s\" IS %%s" % self._table, (self._description,))
        _schema.debug("Table '%s': created", self._table)

    @api.model_cr
    def _parent_columns_exist(self):
        query = """ SELECT c.relname FROM pg_class c, pg_attribute a
                    WHERE c.relname=%s AND a.attname=%s AND c.oid=a.attrelid """
        self._cr.execute(query, (self._table, 'parent_left'))
        return self._cr.rowcount

    @api.model_cr
    def _create_parent_columns(self):
        self._cr.execute('ALTER TABLE "%s" ADD COLUMN "parent_left" INTEGER' % (self._table,))
        self._cr.execute('ALTER TABLE "%s" ADD COLUMN "parent_right" INTEGER' % (self._table,))
        if 'parent_left' not in self._fields:
            _logger.error("add a field parent_left on model %s: parent_left = fields.Integer('Left Parent', index=True)", self._name)
            _schema.debug("Table '%s': added column '%s' with definition=%s", self._table, 'parent_left', 'INTEGER')
        elif not self._fields['parent_left'].index:
            _logger.error('parent_left field on model %s must be indexed! Add index=True to the field definition)', self._name)
        if 'parent_right' not in self._fields:
            _logger.error("add a field parent_right on model %s: parent_right = fields.Integer('Left Parent', index=True)", self._name)
            _schema.debug("Table '%s': added column '%s' with definition=%s", self._table, 'parent_right', 'INTEGER')
        elif not self._fields['parent_right'].index:
            _logger.error("parent_right field on model %s must be indexed! Add index=True to the field definition)", self._name)
        if self._fields[self._parent_name].ondelete not in ('cascade', 'restrict'):
            _logger.error("The field %s on model %s must be set as ondelete='cascade' or 'restrict'", self._parent_name, self._name)
        self._cr.commit()

    @api.model_cr
    def _select_column_data(self):
        # attlen is the number of bytes necessary to represent the type when
        # the type has a fixed size. If the type has a varying size attlen is
        # -1 and atttypmod is the size limit + 4, or -1 if there is no limit.
        query = """ SELECT c.relname, a.attname, a.attlen, a.atttypmod, a.attnotnull, a.atthasdef, t.typname,
                           CASE WHEN a.attlen=-1 THEN (CASE WHEN a.atttypmod=-1 THEN 0 ELSE a.atttypmod-4 END) ELSE a.attlen END as size
                    FROM pg_class c, pg_attribute a, pg_type t
                    WHERE c.relname=%s AND c.oid=a.attrelid AND a.atttypid=t.oid """
        self._cr.execute(query, (self._table,))
        return {row['attname']: row for row in self._cr.dictfetchall()}

    @api.model_cr
    def _add_sql_constraints(self):
        """

        Modify this model's database table constraints so they match the one in
        _sql_constraints.

        """
        cr = self._cr

        def unify_cons_text(txt):
            return txt.lower().replace(', ',',').replace(' (','(')

        def drop(name, definition, old_definition):
            try:
                cr.execute('ALTER TABLE "%s" DROP CONSTRAINT "%s"' % (self._table, name))
                cr.commit()
                _schema.debug("Table '%s': dropped constraint '%s'. Reason: its definition changed from '%s' to '%s'",
                              self._table, name, old_definition, definition)
            except Exception:
                _schema.warning("Table '%s': unable to drop constraint '%s'!", self._table, definition)
                cr.rollback()

        def add(name, definition):
            query = 'ALTER TABLE "%s" ADD CONSTRAINT "%s" %s' % (self._table, name, definition)
            try:
                cr.execute(query)
                cr.commit()
                _schema.debug("Table '%s': added constraint '%s' with definition=%s",
                              self._table, name, definition)
            except Exception:
                _schema.warning("Table '%s': unable to add constraint '%s'!\n"
                                "If you want to have it, you should update the records and execute manually:\n%s",
                                self._table, definition, query)
                cr.rollback()

        # map each constraint on the name of the module where it is defined
        constraint_module = {
            constraint[0]: cls._module
            for cls in reversed(type(self).mro())
            if not getattr(cls, 'pool', None)
            for constraint in getattr(cls, '_local_sql_constraints', ())
        }

        for (key, definition, _) in self._sql_constraints:
            conname = '%s_%s' % (self._table, key)

            # using 1 to get result if no imc but one pgc
            cr.execute("""SELECT definition, 1
                          FROM ir_model_constraint imc
                          RIGHT JOIN pg_constraint pgc
                          ON (pgc.conname = imc.name)
                          WHERE pgc.conname=%s
                          """, (conname, ))
            existing = cr.dictfetchone()
            if not existing:
                # constraint does not exists
                add(conname, definition)
            elif unify_cons_text(definition) != existing['definition']:
                # constraint exists but its definition has changed
                drop(conname, definition, existing['definition'] or '')
                add(conname, definition)

            # we need to add the constraint:
            module = constraint_module.get(key)
            self._save_constraint(conname, 'u', unify_cons_text(definition), module)

    @api.model_cr
    def _execute_sql(self):
        """ Execute the SQL code from the _sql attribute (if any)."""
        if hasattr(self, "_sql"):
            self._cr.execute(self._sql)
            self._cr.commit()

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
        cls = type(self)
        cls._setup_done = False
        # a model's base structure depends on its mro (without registry classes)
        cls._model_cache_key = tuple(c for c in cls.mro() if not getattr(c, 'pool', None))

    @api.model
    def _setup_base(self, partial):
        """ Determine the inherited and custom fields of the model. """
        cls = type(self)
        if cls._setup_done:
            return

        # 1. determine the proper fields of the model: the fields defined on the
        # class and magic fields, not the inherited or custom ones
        cls0 = cls.pool.model_cache.get(cls._model_cache_key)
        if cls0 and cls0._model_cache_key == cls._model_cache_key:
            # cls0 is either a model class from another registry, or cls itself.
            # The point is that it has the same base classes. We retrieve stuff
            # from cls0 to optimize the setup of cls. cls0 is guaranteed to be
            # properly set up: registries are loaded under a global lock,
            # therefore two registries are never set up at the same time.

            # remove fields that are not proper to cls
            for name in set(cls._fields) - cls0._proper_fields:
                delattr(cls, name)
                cls._fields.pop(name, None)
            # collect proper fields on cls0, and add them on cls
            for name in cls0._proper_fields:
                field = cls0._fields[name]
                # regular fields are shared, while related fields are setup from scratch
                if not field.related:
                    self._add_field(name, field)
                else:
                    self._add_field(name, field.new(**field.args))
            cls._proper_fields = set(cls._fields)

        else:
            # retrieve fields from parent classes, and duplicate them on cls to
            # avoid clashes with inheritance between different models
            for name in cls._fields:
                delattr(cls, name)
            cls._fields = {}
            for name, field in getmembers(cls, Field.__instancecheck__):
                # do not retrieve magic, custom and inherited fields
                if not any(field.args.get(k) for k in ('automatic', 'manual', 'inherited')):
                    self._add_field(name, field.new())
            self._add_magic_fields()
            cls._proper_fields = set(cls._fields)

        cls.pool.model_cache[cls._model_cache_key] = cls

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

        # set up fields
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

        if isinstance(self, Model):
            # set up field triggers (on database-persisted models only)
            for field in cls._fields.itervalues():
                # dependencies of custom fields may not exist; ignore that case
                exceptions = (Exception,) if field.manual else ()
                with tools.ignore(*exceptions):
                    field.setup_triggers(self)

        # register constraints and onchange methods
        cls._init_constraints_onchanges()

        # validate rec_name
        if cls._rec_name:
            assert cls._rec_name in cls._fields, \
                "Invalid rec_name %s for model %s" % (cls._rec_name, cls._name)
        elif 'name' in cls._fields:
            cls._rec_name = 'name'
        elif 'x_name' in cls._fields:
            cls._rec_name = 'x_name'

        # make sure parent_order is set when necessary
        if cls._parent_store and not cls._parent_order:
            cls._parent_order = cls._order

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """ fields_get([fields][, attributes])

        Return the definition of each field.

        The returned value is a dictionary (indiced by field name) of
        dictionaries. The _inherits'd fields are included. The string, help,
        and selection (if present) attributes are translated.

        :param allfields: list of fields to document, all if empty or not provided
        :param attributes: list of description attributes to return for each field, all if empty or not provided
        """
        has_access = functools.partial(self.check_access_rights, raise_exception=False)
        readonly = not (has_access('write') or has_access('create'))

        res = {}
        for fname, field in self._fields.iteritems():
            if allfields and fname not in allfields:
                continue
            if field.groups and not self.user_has_groups(field.groups):
                continue

            description = field.get_description(self.env)
            if readonly:
                description['readonly'] = True
                description['states'] = {}
            if attributes:
                description = {key: val
                               for key, val in description.iteritems()
                               if key in attributes}
            res[fname] = description

        return res

    @api.model
    def get_empty_list_help(self, help):
        """ Generic method giving the help message displayed when having
            no result to display in a list or kanban view. By default it returns
            the help given in parameter that is generally the help message
            defined in the action.
        """
        return help

    @api.model
    def check_field_access_rights(self, operation, fields):
        """
        Check the user access rights on the given fields. This raises Access
        Denied if the user does not have the rights. Otherwise it returns the
        fields (as is if the fields is not falsy, or the readable/writable
        fields if fields is falsy).
        """
        if self._uid == SUPERUSER_ID:
            return fields or list(self._fields)

        def valid(fname):
            """ determine whether user has access to field ``fname`` """
            field = self._fields.get(fname)
            if field and field.groups:
                return self.user_has_groups(field.groups)
            else:
                return True

        if not fields:
            fields = filter(valid, self._fields)
        else:
            invalid_fields = set(filter(lambda name: not valid(name), fields))
            if invalid_fields:
                _logger.info('Access Denied by ACLs for operation: %s, uid: %s, model: %s, fields: %s',
                    operation, self._uid, self._name, ', '.join(invalid_fields))
                raise AccessError(_('The requested operation cannot be completed due to security restrictions. '
                                    'Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % \
                                  (self._description, operation))

        return fields

    @api.multi
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
            field = self._fields.get(name)
            if field:
                if field.store:
                    stored.append(name)
                elif field.base_field.store:
                    inherited.append(name)
                else:
                    computed.append(name)
            else:
                _logger.warning("%s.read() with unknown field '%s'", self._name, name)

        # fetch stored fields from the database to the cache; this should feed
        # the prefetching of secondary records
        self._read_from_database(stored, inherited)

        # retrieve results from records; this takes values from the cache and
        # computes remaining fields
        result = []
        name_fields = [(name, self._fields[name]) for name in (stored + inherited + computed)]
        use_name_get = (load == '_classic_read')
        for record in self:
            try:
                values = {'id': record.id}
                for name, field in name_fields:
                    values[name] = field.convert_to_read(record[name], record, use_name_get)
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
        if self._context.get('prefetch_fields', True) and field.prefetch:
            fs.update(
                f
                for f in self._fields.itervalues()
                # select fields that can be prefetched
                if f.prefetch
                # discard fields with groups that the user may not access
                if not (f.groups and not self.user_has_groups(f.groups))
                # discard fields that must be recomputed
                if not (f.compute and self.env.field_todo(f))
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
        records = records.with_prefetch(self._prefetch)
        result = []
        try:
            result = records.read([f.name for f in fs], load='_classic_write')
        except AccessError:
            # not all records may be accessible, try with only current record
            result = self.read([f.name for f in fs], load='_classic_write')

        # check the cache, and update it if necessary
        if field not in self._cache:
            for values in result:
                record = self.browse(values.pop('id'), self._prefetch)
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
            if field.base_field.store and field.base_field.column_type
            if not (field.inherited and callable(field.base_field.translate))
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
                    if not field.inherited and callable(field.translate):
                        f = field.name
                        translate = field.get_trans_func(fetched)
                        for vals in result:
                            vals[f] = translate(vals['id'], vals[f])

            # store result in cache for POST fields
            for vals in result:
                record = self.browse(vals['id'], self._prefetch)
                record._cache.update(record._convert_to_cache(vals, validate=False))

            # determine the fields that must be processed now;
            # for the sake of simplicity, we ignore inherited fields
            for f in field_names:
                field = self._fields[f]
                if not field.column_type:
                    field.read(fetched)

        # Warn about deprecated fields now that fields_pre and fields_post are computed
        for f in field_names:
            field = self._fields[f]
            if field.deprecated:
                _logger.warning('Field %s is deprecated: %s', field, field.deprecated)

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
            fields += LOG_ACCESS_COLUMNS
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

    @api.multi
    def _check_concurrency(self):
        if not (self._log_access and self._context.get(self.CONCURRENCY_CHECK_FIELD)):
            return
        check_clause = "(id = %s AND %s < COALESCE(write_date, create_date, (now() at time zone 'UTC'))::timestamp)"
        for sub_ids in self._cr.split_for_in_conditions(self.ids):
            nclauses = 0
            params = []
            for id in sub_ids:
                id_ref = "%s,%s" % (self._name, id)
                update_date = self._context[self.CONCURRENCY_CHECK_FIELD].pop(id_ref, None)
                if update_date:
                    nclauses += 1
                    params.extend([id, update_date])
            if not nclauses:
                continue
            query = "SELECT id FROM %s WHERE %s" % (self._table, " OR ".join([check_clause] * nclauses))
            self._cr.execute(query, tuple(params))
            res = self._cr.fetchone()
            if res:
                # mention the first one only to keep the error message readable
                raise ValidationError(_('A document was modified since you last viewed it (%s:%d)') % (self._description, res[0]))

    @api.multi
    def _check_record_rules_result_count(self, result_ids, operation):
        """ Verify the returned rows after applying record rules matches the
            length of ``self``, and raise an appropriate exception if it does not.
        """
        ids, result_ids = set(self.ids), set(result_ids)
        missing_ids = ids - result_ids
        if missing_ids:
            # Attempt to distinguish record rule restriction vs deleted records,
            # to provide a more specific error message
            self._cr.execute('SELECT id FROM %s WHERE id IN %%s' % self._table, (tuple(missing_ids),))
            forbidden_ids = [x[0] for x in self._cr.fetchall()]
            if forbidden_ids:
                # the missing ids are (at least partially) hidden by access rules
                if self._uid == SUPERUSER_ID:
                    return
                _logger.info('Access Denied by record rules for operation: %s on record ids: %r, uid: %s, model: %s', operation, forbidden_ids, self._uid, self._name)
                raise AccessError(_('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % \
                                    (self._description, operation))
            else:
                # If we get here, the missing_ids are not in the database
                if operation in ('read','unlink'):
                    # No need to warn about deleting an already deleted record.
                    # And no error when reading a record that was deleted, to prevent spurious
                    # errors for non-transactional search/read sequences coming from clients
                    return
                _logger.info('Failed operation on deleted record(s): %s, uid: %s, model: %s', operation, self._uid, self._name)
                raise MissingError(_('Missing document(s)') + ':' + _('One of the documents you are trying to access has been deleted, please try again after refreshing.'))

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        """ Verifies that the operation given by ``operation`` is allowed for
            the current user according to the access rights.
        """
        return self.env['ir.model.access'].check(self._name, operation, raise_exception)

    @api.multi
    def check_access_rule(self, operation):
        """ Verifies that the operation given by ``operation`` is allowed for
            the current user according to ir.rules.

           :param operation: one of ``write``, ``unlink``
           :raise UserError: * if current ir.rules do not permit this operation.
           :return: None if the operation is allowed
        """
        if self._uid == SUPERUSER_ID:
            return

        if self.is_transient():
            # Only one single implicit access rule for transient models: owner only!
            # This is ok to hardcode because we assert that TransientModels always
            # have log_access enabled so that the create_uid column is always there.
            # And even with _inherits, these fields are always present in the local
            # table too, so no need for JOINs.
            query = "SELECT DISTINCT create_uid FROM %s WHERE id IN %%s" % self._table
            self._cr.execute(query, (tuple(self.ids),))
            uids = [x[0] for x in self._cr.fetchall()]
            if len(uids) != 1 or uids[0] != self._uid:
                raise AccessError(_('For this kind of document, you may only access records you created yourself.\n\n(Document type: %s)') % (self._description,))
        else:
            where_clause, where_params, tables = self.env['ir.rule'].domain_get(self._name, operation)
            if where_clause:
                query = "SELECT %s.id FROM %s WHERE %s.id IN %%s AND " % (self._table, ",".join(tables), self._table)
                query = query + " AND ".join(where_clause)
                for sub_ids in self._cr.split_for_in_conditions(self.ids):
                    self._cr.execute(query, [sub_ids] + where_params)
                    returned_ids = [x[0] for x in self._cr.fetchall()]
                    self.browse(sub_ids)._check_record_rules_result_count(returned_ids, operation)

    @api.multi
    def create_workflow(self):
        """ Create a workflow instance for the given records. """
        from odoo import workflow
        for res_id in self.ids:
            workflow.trg_create(self._uid, self._name, res_id, self._cr)
        return True

    @api.multi
    def delete_workflow(self):
        """ Delete the workflow instances bound to the given records. """
        from odoo import workflow
        for res_id in self.ids:
            workflow.trg_delete(self._uid, self._name, res_id, self._cr)
        self.invalidate_cache()
        return True

    @api.multi
    def step_workflow(self):
        """ Reevaluate the workflow instances of the given records. """
        from odoo import workflow
        for res_id in self.ids:
            workflow.trg_write(self._uid, self._name, res_id, self._cr)
        return True

    @api.multi
    def signal_workflow(self, signal):
        """ Send the workflow signal, and return a dict mapping ids to workflow results. """
        from odoo import workflow
        result = {}
        for res_id in self.ids:
            result[res_id] = workflow.trg_validate(self._uid, self._name, res_id, signal, self._cr)
        return result

    @api.model
    def redirect_workflow(self, old_new_ids):
        """ Rebind the workflow instance bound to the given 'old' record IDs to
            the given 'new' IDs. (``old_new_ids`` is a list of pairs ``(old, new)``.
        """
        from odoo import workflow
        for old_id, new_id in old_new_ids:
            workflow.trg_redirect(self._uid, self._name, old_id, new_id, self._cr)
        self.invalidate_cache()
        return True

    @api.multi
    def unlink(self):
        """ unlink()

        Deletes the records of the current set

        :raise AccessError: * if user has no unlink rights on the requested object
                            * if user tries to bypass access rules for unlink on the requested object
        :raise UserError: if the record is default property for other records

        """
        if not self:
            return True

        # for recomputing fields
        self.modified(self._fields)

        self._check_concurrency()

        self.check_access_rights('unlink')

        # Check if the records are used as default properties.
        refs = ['%s,%s' % (self._name, i) for i in self.ids]
        if self.env['ir.property'].search([('res_id', '=', False), ('value_reference', 'in', refs)]):
            raise UserError(_('Unable to delete this document because it is used as a default property'))

        # Delete the records' properties.
        self.env['ir.property'].search([('res_id', 'in', refs)]).unlink()

        self.delete_workflow()

        self.check_access_rule('unlink')

        cr = self._cr
        Data = self.env['ir.model.data'].sudo().with_context({})
        Values = self.env['ir.values']
        Attachment = self.env['ir.attachment']

        for sub_ids in cr.split_for_in_conditions(self.ids):
            query = "DELETE FROM %s WHERE id IN %%s" % self._table
            cr.execute(query, (sub_ids,))

            # Removing the ir_model_data reference if the record being deleted
            # is a record created by xml/csv file, as these are not connected
            # with real database foreign keys, and would be dangling references.
            #
            # Note: the following steps are performed as superuser to avoid
            # access rights restrictions, and with no context to avoid possible
            # side-effects during admin calls.
            data = Data.search([('model', '=', self._name), ('res_id', 'in', sub_ids)])
            if data:
                data.unlink()

            # For the same reason, remove the relevant records in ir_values
            refs = ['%s,%s' % (self._name, i) for i in sub_ids]
            values = Values.search(['|', ('value', 'in', refs),
                                         '&', ('model', '=', self._name),
                                              ('res_id', 'in', sub_ids)])
            if values:
                values.unlink()

            # For the same reason, remove the relevant records in ir_attachment
            # (the search is performed with sql as the search method of
            # ir_attachment is overridden to hide attachments of deleted
            # records)
            query = 'SELECT id FROM ir_attachment WHERE res_model=%s AND res_id IN %s'
            cr.execute(query, (self._name, sub_ids))
            attachments = Attachment.browse([row[0] for row in cr.fetchall()])
            if attachments:
                attachments.unlink()

        # invalidate the *whole* cache, since the orm does not handle all
        # changes made in the database, like cascading delete!
        self.invalidate_cache()

        # recompute new-style fields
        if self.env.recompute and self._context.get('recompute', True):
            self.recompute()

        # auditing: deletions are infrequent and leave no trace in the database
        _unlink.info('User #%s deleted %s records with IDs: %r', self._uid, self._name, self.ids)

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

        * For numeric fields (:class:`~odoo.fields.Integer`,
          :class:`~odoo.fields.Float`) the value should be of the
          corresponding type
        * For :class:`~odoo.fields.Boolean`, the value should be a
          :class:`python:bool`
        * For :class:`~odoo.fields.Selection`, the value should match the
          selection values (generally :class:`python:str`, sometimes
          :class:`python:int`)
        * For :class:`~odoo.fields.Many2one`, the value should be the
          database identifier of the record to set
        * Other non-relational fields use a string for value

          .. danger::

              for historical and compatibility reasons,
              :class:`~odoo.fields.Date` and
              :class:`~odoo.fields.Datetime` fields use strings as values
              (written and read) rather than :class:`~python:datetime.date` or
              :class:`~python:datetime.datetime`. These date strings are
              UTC-only and formatted according to
              :const:`odoo.tools.misc.DEFAULT_SERVER_DATE_FORMAT` and
              :const:`odoo.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT`
        * .. _openerp/models/relationals/format:

          :class:`~odoo.fields.One2many` and
          :class:`~odoo.fields.Many2many` use a special "commands" format to
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
              :class:`~odoo.fields.One2many`. Can not be used in
              :meth:`~.create`.
          ``(4, id, _)``
              adds an existing record of id ``id`` to the set. Can not be
              used on :class:`~odoo.fields.One2many`.
          ``(5, _, _)``
              removes all records from the set, equivalent to using the
              command ``3`` on every record explicitly. Can not be used on
              :class:`~odoo.fields.One2many`. Can not be used in
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

        self._check_concurrency()
        self.check_access_rights('write')

        # No user-driven update of these columns
        for field in itertools.chain(MAGIC_COLUMNS, ('parent_left', 'parent_right')):
            vals.pop(field, None)

        # split up fields into old-style and pure new-style ones
        old_vals, new_vals, unknown = {}, {}, []
        for key, val in vals.iteritems():
            field = self._fields.get(key)
            if field:
                if field.store or field.inherited:
                    old_vals[key] = val
                if field.inverse and not field.inherited:
                    new_vals[key] = val
            else:
                unknown.append(key)

        if unknown:
            _logger.warning("%s.write() with unknown fields: %s", self._name, ', '.join(sorted(unknown)))

        protected_fields = map(self._fields.get, new_vals)
        with self.env.protecting(protected_fields, self):
            # write old-style fields with (low-level) method _write
            if old_vals:
                self._write(old_vals)

            if new_vals:
                # put the values of pure new-style fields into cache, and inverse them
                self.modified(set(new_vals) - set(old_vals))
                for record in self:
                    record._cache.update(record._convert_to_cache(new_vals, update=True))
                for key in new_vals:
                    self._fields[key].determine_inverse(self)
                self.modified(set(new_vals) - set(old_vals))
                # check Python constraints for inversed fields
                self._validate_fields(set(new_vals) - set(old_vals))
                # recompute new-style fields
                if self.env.recompute and self._context.get('recompute', True):
                    self.recompute()

        return True

    @api.multi
    def _write(self, vals):
        # low-level implementation of write()
        self.check_field_access_rights('write', list(vals))

        cr = self._cr

        # for recomputing new-style fields
        extra_fields = ['write_date', 'write_uid'] if self._log_access else []
        self.modified(list(vals) + extra_fields)

        # for updating parent_left, parent_right
        parents_changed = []
        if self._parent_store and (self._parent_name in vals) and \
                not self._context.get('defer_parent_store_computation'):
            # The parent_left/right computation may take up to 5 seconds. No
            # need to recompute the values if the parent is the same.
            #
            # Note: to respect parent_order, nodes must be processed in
            # order, so ``parents_changed`` must be ordered properly.
            parent_val = vals[self._parent_name]
            if parent_val:
                query = "SELECT id FROM %s WHERE id IN %%s AND (%s != %%s OR %s IS NULL) ORDER BY %s" % \
                                (self._table, self._parent_name, self._parent_name, self._parent_order)
                cr.execute(query, (tuple(self.ids), parent_val))
            else:
                query = "SELECT id FROM %s WHERE id IN %%s AND (%s IS NOT NULL) ORDER BY %s" % \
                                (self._table, self._parent_name, self._parent_order)
                cr.execute(query, (tuple(self.ids),))
            parents_changed = map(operator.itemgetter(0), cr.fetchall())

        updates = []            # list of (column, expr) or (column, pattern, value)
        upd_todo = []           # list of column names to set explicitly
        updend = []             # list of possibly inherited field names
        direct = []             # list of direcly updated columns
        has_trans = self.env.lang and self.env.lang != 'en_US'
        single_lang = len(self.env['res.lang'].get_installed()) <= 1
        for name, val in vals.iteritems():
            field = self._fields[name]
            if field and field.deprecated:
                _logger.warning('Field %s.%s is deprecated: %s', self._name, name, field.deprecated)
            if field.store:
                if hasattr(field, 'selection') and val:
                    self._check_selection_field_value(name, val)
                if field.column_type:
                    if single_lang or not (has_trans and field.translate is True):
                        # val is not a translation: update the table
                        val = field.convert_to_column(val, self)
                        updates.append((name, field.column_format, val))
                    direct.append(name)
                else:
                    upd_todo.append(name)
            else:
                updend.append(name)

        if self._log_access:
            updates.append(('write_uid', '%s', self._uid))
            updates.append(('write_date', "(now() at time zone 'UTC')"))
            direct.append('write_uid')
            direct.append('write_date')

        if updates:
            self.check_access_rule('write')
            query = 'UPDATE "%s" SET %s WHERE id IN %%s' % (
                self._table, ','.join('"%s"=%s' % (u[0], u[1]) for u in updates),
            )
            params = tuple(u[2] for u in updates if len(u) > 2)
            for sub_ids in cr.split_for_in_conditions(set(self.ids)):
                cr.execute(query, params + (sub_ids,))
                if cr.rowcount != len(sub_ids):
                    raise MissingError(_('One of the records you are trying to modify has already been deleted (Document type: %s).') % self._description)

            # TODO: optimize
            for name in direct:
                field = self._fields[name]
                if callable(field.translate):
                    # The source value of a field has been modified,
                    # synchronize translated terms when possible.
                    self.env['ir.translation']._sync_terms_translations(self._fields[name], self)

                elif has_trans and field.translate:
                    # The translated value of a field has been modified.
                    src_trans = self.read([name])[0][name]
                    if not src_trans:
                        # Insert value to DB
                        src_trans = vals[name]
                        self.with_context(lang=None).write({name: src_trans})
                    val = field.convert_to_column(vals[name], self)
                    tname = "%s,%s" % (self._name, name)
                    self.env['ir.translation']._set_ids(
                        tname, 'model', self.env.lang, self.ids, val, src_trans)

        # invalidate and mark new-style fields to recompute; do this before
        # setting other fields, because it can require the value of computed
        # fields, e.g., a one2many checking constraints on records
        self.modified(direct)

        # defaults in context must be removed when call a one2many or many2many
        rel_context = {key: val
                       for key, val in self._context.iteritems()
                       if not key.startswith('default_')}

        # call the 'write' method of fields which are not columns
        for name in upd_todo:
            field = self._fields[name]
            field.write(self.with_context(rel_context), vals[name])

        # for recomputing new-style fields
        self.modified(upd_todo)

        # write inherited fields on the corresponding parent records
        unknown_fields = set(updend)
        for parent_model, parent_field in self._inherits.iteritems():
            parent_ids = []
            for sub_ids in cr.split_for_in_conditions(self.ids):
                query = "SELECT DISTINCT %s FROM %s WHERE id IN %%s" % (parent_field, self._table)
                cr.execute(query, (sub_ids,))
                parent_ids.extend([row[0] for row in cr.fetchall()])

            parent_vals = {}
            for name in updend:
                field = self._fields[name]
                if field.inherited and field.related[0] == parent_field:
                    parent_vals[name] = vals[name]
                    unknown_fields.discard(name)

            if parent_vals:
                self.env[parent_model].browse(parent_ids).write(parent_vals)

        if unknown_fields:
            _logger.warning('No such field(s) in model %s: %s.', self._name, ', '.join(unknown_fields))

        # check Python constraints
        self._validate_fields(vals)

        # TODO: use _order to set dest at the right position and not first node of parent
        # We can't defer parent_store computation because the stored function
        # fields that are computer may refer (directly or indirectly) to
        # parent_left/right (via a child_of domain)
        if parents_changed:
            if self.pool._init:
                self.pool._init_parent[self._name] = True
            else:
                parent_val = vals[self._parent_name]
                if parent_val:
                    clause, params = '%s=%%s' % self._parent_name, (parent_val,)
                else:
                    clause, params = '%s IS NULL' % self._parent_name, ()

                for id in parents_changed:
                    # determine old parent_left, parent_right of current record
                    cr.execute('SELECT parent_left, parent_right FROM %s WHERE id=%%s' % self._table, (id,))
                    pleft0, pright0 = cr.fetchone()
                    width = pright0 - pleft0 + 1

                    # determine new parent_left of current record; it comes
                    # right after the parent_right of its closest left sibling
                    # (this CANNOT be fetched outside the loop, as it needs to
                    # be refreshed after each update, in case several nodes are
                    # sequentially inserted one next to the other)
                    pleft1 = None
                    cr.execute('SELECT id, parent_right FROM %s WHERE %s ORDER BY %s' % \
                               (self._table, clause, self._parent_order), params)
                    for (sibling_id, sibling_parent_right) in cr.fetchall():
                        if sibling_id == id:
                            break
                        pleft1 = (sibling_parent_right or 0) + 1
                    if not pleft1:
                        # the current record is the first node of the parent
                        if not parent_val:
                            pleft1 = 0          # the first node starts at 0
                        else:
                            cr.execute('SELECT parent_left FROM %s WHERE id=%%s' % self._table, (parent_val,))
                            pleft1 = cr.fetchone()[0] + 1

                    if pleft0 < pleft1 <= pright0:
                        raise UserError(_('Recursivity Detected.'))

                    # make some room for parent_left and parent_right at the new position
                    cr.execute('UPDATE %s SET parent_left=parent_left+%%s WHERE %%s<=parent_left' % self._table, (width, pleft1))
                    cr.execute('UPDATE %s SET parent_right=parent_right+%%s WHERE %%s<=parent_right' % self._table, (width, pleft1))
                    # slide the subtree of the current record to its new position
                    if pleft0 < pleft1:
                        cr.execute('''UPDATE %s SET parent_left=parent_left+%%s, parent_right=parent_right+%%s
                                      WHERE %%s<=parent_left AND parent_left<%%s''' % self._table,
                                   (pleft1 - pleft0, pleft1 - pleft0, pleft0, pright0))
                    else:
                        cr.execute('''UPDATE %s SET parent_left=parent_left-%%s, parent_right=parent_right-%%s
                                      WHERE %%s<=parent_left AND parent_left<%%s''' % self._table,
                                   (pleft0 - pleft1 + width, pleft0 - pleft1 + width, pleft0 + width, pright0 + width))

                self.invalidate_cache(['parent_left', 'parent_right'])

        # recompute new-style fields
        if self.env.recompute and self._context.get('recompute', True):
            self.recompute()

        self.step_workflow()
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
                if field.store or field.inherited:
                    old_vals[key] = val
                if field.inverse and not field.inherited:
                    new_vals[key] = val
            else:
                unknown.append(key)

        if unknown:
            _logger.warning("%s.create() includes unknown fields: %s", self._name, ', '.join(sorted(unknown)))

        # create record with old-style fields
        record = self.browse(self._create(old_vals))

        protected_fields = map(self._fields.get, new_vals)
        with self.env.protecting(protected_fields, record):
            # put the values of pure new-style fields into cache, and inverse them
            record.modified(set(new_vals) - set(old_vals))
            record._cache.update(record._convert_to_cache(new_vals))
            for key in new_vals:
                self._fields[key].determine_inverse(record)
            record.modified(set(new_vals) - set(old_vals))
            # check Python constraints for inversed fields
            record._validate_fields(set(new_vals) - set(old_vals))
            # recompute new-style fields
            if self.env.recompute and self._context.get('recompute', True):
                self.recompute()

        return record

    @api.model
    def _create(self, vals):
        # low-level implementation of create()
        if self.is_transient():
            self._transient_vacuum()

        # data of parent records to create or update, by model
        tocreate = {
            parent_model: {'id': vals.pop(parent_field, None)}
            for parent_model, parent_field in self._inherits.iteritems()
        }

        # list of column assignments defined as tuples like:
        #   (column_name, format_string, column_value)
        #   (column_name, sql_formula)
        # Those tuples will be used by the string formatting for the INSERT
        # statement below.
        updates = [
            ('id', "nextval('%s')" % self._sequence),
        ]

        upd_todo = []
        unknown_fields = []
        protected_fields = []
        for name, val in vals.items():
            field = self._fields.get(name)
            if not field:
                unknown_fields.append(name)
                del vals[name]
            elif field.inherited:
                tocreate[field.related_field.model_name][name] = val
                del vals[name]
            elif not field.store:
                del vals[name]
            elif field.inverse:
                protected_fields.append(field)
        if unknown_fields:
            _logger.warning('No such field(s) in model %s: %s.', self._name, ', '.join(unknown_fields))

        # create or update parent records
        for parent_model, parent_vals in tocreate.iteritems():
            parent_id = parent_vals.pop('id')
            if not parent_id:
                parent_id = self.env[parent_model].create(parent_vals).id
            else:
                self.env[parent_model].browse(parent_id).write(parent_vals)
            updates.append((self._inherits[parent_model], '%s', parent_id))

        # set boolean fields to False by default (to make search more powerful)
        for name, field in self._fields.iteritems():
            if field.type == 'boolean' and field.store and name not in vals:
                vals[name] = False

        # determine SQL values
        for name, val in vals.iteritems():
            field = self._fields[name]
            if field.store and field.column_type:
                updates.append((name, field.column_format, field.convert_to_column(val, self)))
            else:
                upd_todo.append(name)

            if hasattr(field, 'selection') and val:
                self._check_selection_field_value(name, val)

        if self._log_access:
            updates.append(('create_uid', '%s', self._uid))
            updates.append(('write_uid', '%s', self._uid))
            updates.append(('create_date', "(now() at time zone 'UTC')"))
            updates.append(('write_date', "(now() at time zone 'UTC')"))

        # insert a row for this record
        cr = self._cr
        query = """INSERT INTO "%s" (%s) VALUES(%s) RETURNING id""" % (
                self._table,
                ', '.join('"%s"' % u[0] for u in updates),
                ', '.join(u[1] for u in updates),
            )
        cr.execute(query, tuple(u[2] for u in updates if len(u) > 2))

        # from now on, self is the new record
        id_new, = cr.fetchone()
        self = self.browse(id_new)

        if self.env.lang and self.env.lang != 'en_US':
            # add translations for self.env.lang
            for name, val in vals.iteritems():
                field = self._fields[name]
                if field.store and field.column_type and field.translate is True:
                    tname = "%s,%s" % (self._name, name)
                    self.env['ir.translation']._set_ids(tname, 'model', self.env.lang, self.ids, val, val)

        if self._parent_store and not self._context.get('defer_parent_store_computation'):
            if self.pool._init:
                self.pool._init_parent[self._name] = True
            else:
                parent_val = vals.get(self._parent_name)
                if parent_val:
                    # determine parent_left: it comes right after the
                    # parent_right of its closest left sibling
                    pleft = None
                    cr.execute("SELECT parent_right FROM %s WHERE %s=%%s ORDER BY %s" % \
                                    (self._table, self._parent_name, self._parent_order),
                               (parent_val,))
                    for (pright,) in cr.fetchall():
                        if not pright:
                            break
                        pleft = pright + 1
                    if not pleft:
                        # this is the leftmost child of its parent
                        cr.execute("SELECT parent_left FROM %s WHERE id=%%s" % self._table, (parent_val,))
                        pleft = cr.fetchone()[0] + 1
                else:
                    # determine parent_left: it comes after all top-level parent_right
                    cr.execute("SELECT MAX(parent_right) FROM %s" % self._table)
                    pleft = (cr.fetchone()[0] or 0) + 1

                # make some room for the new node, and insert it in the MPTT
                cr.execute("UPDATE %s SET parent_left=parent_left+2 WHERE parent_left>=%%s" % self._table,
                           (pleft,))
                cr.execute("UPDATE %s SET parent_right=parent_right+2 WHERE parent_right>=%%s" % self._table,
                           (pleft,))
                cr.execute("UPDATE %s SET parent_left=%%s, parent_right=%%s WHERE id=%%s" % self._table,
                           (pleft, pleft + 1, id_new))
                self.invalidate_cache(['parent_left', 'parent_right'])

        with self.env.protecting(protected_fields, self):
            # invalidate and mark new-style fields to recompute; do this before
            # setting other fields, because it can require the value of computed
            # fields, e.g., a one2many checking constraints on records
            self.modified(self._fields)

            # defaults in context must be removed when call a one2many or many2many
            rel_context = {key: val
                           for key, val in self._context.iteritems()
                           if not key.startswith('default_')}

            # call the 'write' method of fields which are not columns
            for name in upd_todo:
                field = self._fields[name]
                field.write(self.with_context(rel_context), vals[name])

            # for recomputing new-style fields
            self.modified(upd_todo)

            # check Python constraints
            self._validate_fields(vals)

            if self.env.recompute and self._context.get('recompute', True):
                # recompute new-style fields
                self.recompute()

        self.check_access_rule('create')
        self.create_workflow()
        return id_new

    # TODO: ameliorer avec NULL
    @api.model
    def _where_calc(self, domain, active_test=True):
        """Computes the WHERE clause needed to implement an OpenERP domain.
        :param domain: the domain to compute
        :type domain: list
        :param active_test: whether the default filtering of records with ``active``
                            field set to ``False`` should be applied.
        :return: the query expressing the given domain as provided in domain
        :rtype: osv.query.Query
        """
        # if the object has a field named 'active', filter out all inactive
        # records unless they were explicitely asked for
        if 'active' in self._fields and active_test and self._context.get('active_test', True):
            # the item[0] trick below works for domain items and '&'/'|'/'!'
            # operators too
            if not any(item[0] == 'active' for item in domain):
                domain = [('active', '=', 1)] + domain

        if domain:
            e = expression.expression(domain, self)
            tables = e.get_tables()
            where_clause, where_params = e.to_sql()
            where_clause = [where_clause] if where_clause else []
        else:
            where_clause, where_params, tables = [], [], ['"%s"' % self._table]

        return Query(tables, where_clause, where_params)

    def _check_qorder(self, word):
        if not regex_order.match(word):
            raise UserError(_('Invalid "order" specified. A valid "order" specification is a comma-separated list of valid field names (optionally followed by asc/desc for the direction)'))
        return True

    @api.model
    def _apply_ir_rules(self, query, mode='read'):
        """Add what's missing in ``query`` to implement all appropriate ir.rules
          (using the ``model_name``'s rules or the current model's rules if ``model_name`` is None)

           :param query: the current query object
        """
        if self._uid == SUPERUSER_ID:
            return

        def apply_rule(clauses, params, tables, parent_model=None):
            """ :param parent_model: name of the parent model, if the added
                    clause comes from a parent model
            """
            if clauses:
                if parent_model:
                    # as inherited rules are being applied, we need to add the
                    # missing JOIN to reach the parent table (if not JOINed yet)
                    parent_table = '"%s"' % self.env[parent_model]._table
                    parent_alias = '"%s"' % self._inherits_join_add(self, parent_model, query)
                    # inherited rules are applied on the external table, replace
                    # parent_table by parent_alias
                    clauses = [clause.replace(parent_table, parent_alias) for clause in clauses]
                    # replace parent_table by parent_alias, and introduce
                    # parent_alias if needed
                    tables = [
                        (parent_table + ' as ' + parent_alias) if table == parent_table \
                            else table.replace(parent_table, parent_alias)
                        for table in tables
                    ]
                query.where_clause += clauses
                query.where_clause_params += params
                for table in tables:
                    if table not in query.tables:
                        query.tables.append(table)

        # apply main rules on the object
        Rule = self.env['ir.rule']
        where_clause, where_params, tables = Rule.domain_get(self._name, mode)
        apply_rule(where_clause, where_params, tables)

        # apply ir.rules from the parents (through _inherits)
        for parent_model in self._inherits:
            where_clause, where_params, tables = Rule.domain_get(parent_model, mode)
            apply_rule(where_clause, where_params, tables, parent_model)

    @api.model
    def _generate_translated_field(self, table_alias, field, query):
        """
        Add possibly missing JOIN with translations table to ``query`` and
        generate the expression for the translated field.

        :return: the qualified field name (or expression) to use for ``field``
        """
        if self.env.lang:
            # Sub-select to return at most one translation per record.
            # Even if it shoud probably not be the case,
            # this is possible to have multiple translations for a same record in the same language.
            # The parenthesis surrounding the select are important, as this is a sub-select.
            # The quotes surrounding `ir_translation` are important as well.
            unique_translation_subselect = """
                (SELECT DISTINCT ON (res_id) res_id, value
                 FROM "ir_translation"
                 WHERE name=%s AND lang=%s AND value!=%s
                 ORDER BY res_id, id DESC)
            """
            alias, alias_statement = query.add_join(
                (table_alias, unique_translation_subselect, 'id', 'res_id', field),
                implicit=False,
                outer=True,
                extra_params=["%s,%s" % (self._name, field), self.env.lang, ""],
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
        field = self._fields[order_field]
        if field.inherited:
            # also add missing joins for reaching the table containing the m2o field
            qualified_field = self._inherits_join_calc(alias, order_field, query)
            alias, order_field = qualified_field.replace('"', '').split('.', 1)
            field = field.base_field

        assert field.type == 'many2one', 'Invalid field passed to _generate_m2o_order_by()'
        if not field.store:
            _logger.debug("Many2one function/related fields must be stored "
                          "to be used as ordering fields! Ignoring sorting for %s.%s",
                          self._name, order_field)
            return []

        # figure out the applicable order_by for the m2o
        dest_model = self.env[field.comodel_name]
        m2o_order = dest_model._order
        if not regex_order.match(m2o_order):
            # _order is complex, can't use it here, so we default to _rec_name
            m2o_order = dest_model._rec_name

        # Join the dest m2o table if it's not joined yet. We use [LEFT] OUTER join here
        # as we don't want to exclude results that have NULL values for the m2o
        join = (alias, dest_model._table, order_field, 'id', order_field)
        dest_alias, _ = query.add_join(join, implicit=False, outer=True)
        return dest_model._generate_order_by_inner(dest_alias, m2o_order, query,
                                                   reverse_direction, seen)

    @api.model
    def _generate_order_by_inner(self, alias, order_spec, query, reverse_direction=False, seen=None):
        if seen is None:
            seen = set()
        self._check_qorder(order_spec)

        order_by_elements = []
        for order_part in order_spec.split(','):
            order_split = order_part.strip().split(' ')
            order_field = order_split[0].strip()
            order_direction = order_split[1].strip().upper() if len(order_split) == 2 else ''
            if reverse_direction:
                order_direction = 'ASC' if order_direction == 'DESC' else 'DESC'
            do_reverse = order_direction == 'DESC'

            field = self._fields.get(order_field)
            if not field:
                raise ValueError(_("Sorting field %s not found on model %s") % (order_field, self._name))

            if order_field == 'id':
                order_by_elements.append('"%s"."%s" %s' % (alias, order_field, order_direction))
            else:
                if field.inherited:
                    field = field.base_field
                if field.store and field.type == 'many2one':
                    key = (field.model_name, field.comodel_name, order_field)
                    if key not in seen:
                        seen.add(key)
                        order_by_elements += self._generate_m2o_order_by(alias, order_field, query, do_reverse, seen)
                elif field.store and field.column_type:
                    qualifield_name = self._inherits_join_calc(alias, order_field, query, implicit=False, outer=True)
                    if field.type == 'boolean':
                        qualifield_name = "COALESCE(%s, false)" % qualifield_name
                    order_by_elements.append("%s %s" % (qualifield_name, order_direction))
                else:
                    continue  # ignore non-readable or "non-joinable" fields

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

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """
        Private implementation of search() method, allowing specifying the uid to use for the access right check.
        This is useful for example when filling in the selection list for a drop-down and avoiding access rights errors,
        by specifying ``access_rights_uid=1`` to bypass access rights check, but not ir.rules!
        This is ok at the security level because this method is private and not callable through XML-RPC.

        :param access_rights_uid: optional user ID to use when checking access rights
                                  (not for ir.rules, this is only for ir.model.access)
        :return: a list of record ids or an integer (if count is True)
        """
        self.sudo(access_rights_uid or self._uid).check_access_rights('read')

        # For transient models, restrict access to the current user, except for the super-user
        if self.is_transient() and self._log_access and self._uid != SUPERUSER_ID:
            args = expression.AND(([('create_uid', '=', self._uid)], args or []))

        query = self._where_calc(args)
        self._apply_ir_rules(query, 'read')
        order_by = self._generate_order_by(order, query)
        from_clause, where_clause, where_clause_params = query.get_sql()

        where_str = where_clause and (" WHERE %s" % where_clause) or ''

        if count:
            # Ignore order, limit and offset when just counting, they don't make sense and could
            # hurt performance
            query_str = 'SELECT count(1) FROM ' + from_clause + where_str
            self._cr.execute(query_str, where_clause_params)
            res = self._cr.fetchone()
            return res[0]

        limit_str = limit and ' limit %d' % limit or ''
        offset_str = offset and ' offset %d' % offset or ''
        query_str = 'SELECT "%s".id FROM ' % self._table + from_clause + where_str + order_by + limit_str + offset_str
        self._cr.execute(query_str, where_clause_params)
        res = self._cr.fetchall()

        # TDE note: with auto_join, we could have several lines about the same result
        # i.e. a lead with several unread messages; we uniquify the result using
        # a fast way to do it while preserving order (http://www.peterbe.com/plog/uniqifiers-benchmark)
        def _uniquify_list(seq):
            seen = set()
            return [x for x in seq if x not in seen and not seen.add(x)]

        return _uniquify_list([x[0] for x in res])

    @api.multi
    @api.returns(None, lambda value: value[0])
    def copy_data(self, default=None):
        """
        Copy given record's data with all its fields values

        :param default: field values to override in the original values of the copied record
        :return: list with a dictionary containing all the field values
        """
        # In the old API, this method took a single id and return a dict. When
        # invoked with the new API, it returned a list of dicts.
        self.ensure_one()

        # avoid recursion through already copied records in case of circular relationship
        if '__copy_data_seen' not in self._context:
            self = self.with_context(__copy_data_seen=defaultdict(set))
        seen_map = self._context['__copy_data_seen']
        if self.id in seen_map[self._name]:
            return
        seen_map[self._name].add(self.id)

        default = dict(default or [])
        if 'state' not in default and 'state' in self._fields:
            field = self._fields['state']
            if field.default:
                value = field.default(self)
                value = field.convert_to_cache(value, self)
                value = field.convert_to_record(value, self)
                value = field.convert_to_write(value, self)
                default['state'] = value

        # build a black list of fields that should not be copied
        blacklist = set(MAGIC_COLUMNS + ['parent_left', 'parent_right'])
        whitelist = set(name for name, field in self._fields.iteritems() if not field.inherited)

        def blacklist_given_fields(model):
            # blacklist the fields that are given by inheritance
            for parent_model, parent_field in model._inherits.items():
                blacklist.add(parent_field)
                if parent_field in default:
                    # all the fields of 'parent_model' are given by the record:
                    # default[parent_field], except the ones redefined in self
                    blacklist.update(set(self.env[parent_model]._fields) - whitelist)
                else:
                    blacklist_given_fields(self.env[parent_model])
            # blacklist deprecated fields
            for name, field in model._fields.iteritems():
                if field.deprecated:
                    blacklist.add(name)

        blacklist_given_fields(self)

        fields_to_copy = {name: field
                          for name, field in self._fields.iteritems()
                          if field.copy and name not in default and name not in blacklist}

        for name, field in fields_to_copy.iteritems():
            if field.type == 'one2many':
                # duplicate following the order of the ids because we'll rely on
                # it later for copying translations in copy_translation()!
                lines = [rec.copy_data()[0] for rec in self[name].sorted(key='id')]
                # the lines are duplicated using the wrong (old) parent, but then
                # are reassigned to the correct one thanks to the (0, 0, ...)
                default[name] = [(0, 0, line) for line in lines if line]
            elif field.type == 'many2many':
                default[name] = [(6, 0, self[name].ids)]
            else:
                default[name] = field.convert_to_write(self[name], self)

        return [default]

    @api.multi
    def copy_translations(old, new):
        # avoid recursion through already copied records in case of circular relationship
        if '__copy_translations_seen' not in old._context:
            old = old.with_context(__copy_translations_seen=defaultdict(set))
        seen_map = old._context['__copy_translations_seen']
        if old.id in seen_map[old._name]:
            return
        seen_map[old._name].add(old.id)

        def get_trans(field, old, new):
            """ Return the 'name' of the translations to search for, together
                with the record ids corresponding to ``old`` and ``new``.
            """
            if field.inherited:
                pname = field.related[0]
                return get_trans(field.related_field, old[pname], new[pname])
            return "%s,%s" % (field.model_name, field.name), old.id, new.id

        # removing the lang to compare untranslated values
        old_wo_lang, new_wo_lang = (old + new).with_context(lang=None)
        Translation = old.env['ir.translation']

        for name, field in old._fields.iteritems():
            if not field.copy:
                continue

            if field.type == 'one2many':
                # we must recursively copy the translations for o2m; here we
                # rely on the order of the ids to match the translations as
                # foreseen in copy_data()
                old_lines = old[name].sorted(key='id')
                new_lines = new[name].sorted(key='id')
                for (old_line, new_line) in zip(old_lines, new_lines):
                    old_line.copy_translations(new_line)

            elif field.translate:
                # for translatable fields we copy their translations
                trans_name, source_id, target_id = get_trans(field, old, new)
                domain = [('name', '=', trans_name), ('res_id', '=', source_id)]
                for vals in Translation.search_read(domain):
                    del vals['id']
                    del vals['source']      # remove source to avoid triggering _set_src
                    del vals['module']      # duplicated vals is not linked to any module
                    vals['res_id'] = target_id
                    if vals['lang'] == old.env.lang:
                        # 'source' to force the call to _set_src
                        # 'value' needed if value is changed in copy(), want to see the new_value
                        vals['source'] = old_wo_lang[name]
                        vals['value'] = new_wo_lang[name]
                    Translation.create(vals)

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """ copy(default=None)

        Duplicate record ``self`` updating it with default values

        :param dict default: dictionary of field values to override in the
               original values of the copied record, e.g: ``{'field_name': overridden_value, ...}``
        :returns: new record

        """
        self.ensure_one()
        vals = self.copy_data(default)[0]
        # To avoid to create a translation in the lang of the user, copy_translation will do it
        new = self.with_context(lang=None).create(vals)
        self.copy_translations(new)
        return new

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

    @api.multi
    def _check_recursion(self, parent=None):
        """
        Verifies that there is no loop in a hierarchical structure of records,
        by following the parent relationship using the **parent** field until a
        loop is detected or until a top-level record is found.

        :param parent: optional parent field name (default: ``self._parent_name``)
        :return: **True** if no loop was found, **False** otherwise.
        """
        if not parent:
            parent = self._parent_name

        # must ignore 'active' flag, ir.rules, etc. => direct SQL query
        cr = self._cr
        query = 'SELECT "%s" FROM "%s" WHERE id = %%s' % (parent, self._table)
        for id in self.ids:
            current_id = id
            while current_id:
                cr.execute(query, (current_id,))
                result = cr.fetchone()
                current_id = result[0] if result else None
                if current_id == id:
                    return False
        return True

    @api.multi
    def _check_m2m_recursion(self, field_name):
        """
        Verifies that there is no loop in a directed graph of records, by
        following a many2many relationship with the given field name.

        :param field_name: field to check
        :return: **True** if no loop was found, **False** otherwise.
        """
        field = self._fields.get(field_name)
        if not (field and field.type == 'many2many' and
                field.comodel_name == self._name and field.store):
            # field must be a many2many on itself
            raise ValueError('invalid field_name: %r' % (field_name,))

        cr = self._cr
        query = 'SELECT "%s", "%s" FROM "%s" WHERE "%s" IN %%s AND "%s" IS NOT NULL' % \
                    (field.column1, field.column2, field.relation, field.column1, field.column2)

        succs = defaultdict(set)        # transitive closure of successors
        preds = defaultdict(set)        # transitive closure of predecessors
        todo, done = set(self.ids), set()
        while todo:
            # retrieve the respective successors of the nodes in 'todo'
            cr.execute(query, [tuple(todo)])
            done.update(todo)
            todo.clear()
            for id1, id2 in cr.fetchall():
                # connect id1 and its predecessors to id2 and its successors
                for x, y in itertools.product([id1] + list(preds[id1]),
                                              [id2] + list(succs[id2])):
                    if x == y:
                        return False    # we found a cycle here!
                    succs[x].add(y)
                    preds[y].add(x)
                if id2 not in done:
                    todo.add(id2)
        return True

    @api.multi
    def _get_external_ids(self):
        """Retrieve the External ID(s) of any database record.

        **Synopsis**: ``_get_xml_ids() -> { 'id': ['module.xml_id'] }``

        :return: map of ids to the list of their fully qualified External IDs
                 in the form ``module.key``, or an empty list when there's no External
                 ID for a record, e.g.::

                     { 'id': ['module.ext_id', 'module.ext_id_bis'],
                       'id2': [] }
        """
        result = {record.id: [] for record in self}
        domain = [('model', '=', self._name), ('res_id', 'in', self.ids)]
        for data in self.env['ir.model.data'].search_read(domain, ['module', 'name', 'res_id']):
            result[data['res_id']].append('%(module)s.%(name)s' % data)
        return result

    @api.multi
    def get_external_id(self):
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
        results = self._get_external_ids()
        return {key: val[0] if val else ''
                for key, val in results.iteritems()}

    # backwards compatibility
    get_xml_id = get_external_id
    _get_xml_ids = _get_external_ids

    @api.multi
    def print_report(self, name, data):
        """
        Render the report ``name`` for the given IDs. The report must be defined
        for this model, not another.
        """
        report = self.env['ir.actions.report.xml']._lookup_report(name)
        assert self._name == report.table
        cr, uid, context = self.env.args
        return report.create(cr, uid, self.ids, data, context)

    # Transience
    @classmethod
    def is_transient(cls):
        """ Return whether the model is transient.

        See :class:`TransientModel`.

        """
        return cls._transient

    @api.model_cr
    def _transient_clean_rows_older_than(self, seconds):
        assert self._transient, "Model %s is not transient, it cannot be vacuumed!" % self._name
        # Never delete rows used in last 5 minutes
        seconds = max(seconds, 300)
        query = ("SELECT id FROM " + self._table + " WHERE"
            " COALESCE(write_date, create_date, (now() at time zone 'UTC'))::timestamp"
            " < ((now() at time zone 'UTC') - interval %s)")
        self._cr.execute(query, ("%s seconds" % seconds,))
        ids = [x[0] for x in self._cr.fetchall()]
        self.sudo().browse(ids).unlink()

    @api.model_cr
    def _transient_clean_old_rows(self, max_count):
        # Check how many rows we have in the table
        self._cr.execute("SELECT count(*) AS row_count FROM " + self._table)
        res = self._cr.fetchall()
        if res[0][0] <= max_count:
            return  # max not reached, nothing to do
        self._transient_clean_rows_older_than(300)

    @api.model
    def _transient_vacuum(self, force=False):
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
        cls = type(self)
        cls._transient_check_count += 1
        if not force and (cls._transient_check_count < _transient_check_time):
            return True  # no vacuum cleaning this time
        cls._transient_check_count = 0

        # Age-based expiration
        if self._transient_max_hours:
            self._transient_clean_rows_older_than(self._transient_max_hours * 60 * 60)

        # Count-based expiration
        if self._transient_max_count:
            self._transient_clean_old_rows(self._transient_max_count)

        return True

    @api.model
    def resolve_2many_commands(self, field_name, commands, fields=None):
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
        result = []                     # result (list of dict)
        record_ids = []                 # ids of records to read
        updates = defaultdict(dict)     # {id: vals} of updates on records

        for command in commands or []:
            if not isinstance(command, (list, tuple)):
                record_ids.append(command)
            elif command[0] == 0:
                result.append(command[2])
            elif command[0] == 1:
                record_ids.append(command[1])
                updates[command[1]].update(command[2])
            elif command[0] in (2, 3):
                record_ids = [id for id in record_ids if id != command[1]]
            elif command[0] == 4:
                record_ids.append(command[1])
            elif command[0] == 5:
                result, record_ids = [], []
            elif command[0] == 6:
                result, record_ids = [], list(command[2])

        # read the records and apply the updates
        field = self._fields[field_name]
        records = self.env[field.comodel_name].browse(record_ids)
        for data in records.read(fields):
            data.update(updates.get(data['id'], {}))
            result.append(data)

        return result

    # for backward compatibility
    resolve_o2m_commands_to_record_dicts = resolve_2many_commands

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """
        Performs a ``search()`` followed by a ``read()``.

        :param domain: Search domain, see ``args`` parameter in ``search()``. Defaults to an empty domain that will match all records.
        :param fields: List of fields to read, see ``fields`` parameter in ``read()``. Defaults to all fields.
        :param offset: Number of records to skip, see ``offset`` parameter in ``search()``. Defaults to 0.
        :param limit: Maximum number of records to return, see ``limit`` parameter in ``search()``. Defaults to no limit.
        :param order: Columns to sort result, see ``order`` parameter in ``search()``. Defaults to no sort.
        :return: List of dictionaries containing the asked fields.
        :rtype: List of dictionaries.

        """
        records = self.search(domain or [], offset=offset, limit=limit, order=order)
        if not records:
            return []

        if fields and fields == ['id']:
            # shortcut read if we only want the ids
            return [{'id': record.id} for record in records]

        # read() ignores active_test, but it would forward it to any downstream search call
        # (e.g. for x2m or function fields), and this is not the desired behavior, the flag
        # was presumably only meant for the main search().
        # TODO: Move this to read() directly?
        if 'active_test' in self._context:
            context = dict(self._context)
            del context['active_test']
            records = records.with_context(context)

        result = records.read(fields)
        if len(result) <= 1:
            return result

        # reorder read
        index = {vals['id']: vals for vals in result}
        return [index[record.id] for record in records if record.id in index]

    @api.multi
    def toggle_active(self):
        """ Inverse the value of the field ``active`` on the records in ``self``. """
        for record in self:
            record.active = not record.active

    @api.model_cr
    def _register_hook(self):
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
    def _browse(cls, ids, env, prefetch=None):
        """ Create a recordset instance.

        :param ids: a tuple of record ids
        :param env: an environment
        :param prefetch: an optional prefetch object
        """
        records = object.__new__(cls)
        records.env = env
        records._ids = ids
        if prefetch is None:
            prefetch = defaultdict(set)         # {model_name: set(ids)}
        records._prefetch = prefetch
        prefetch[cls._name].update(ids)
        return records

    def browse(self, arg=None, prefetch=None):
        """ browse([ids]) -> records

        Returns a recordset for the ids provided as parameter in the current
        environment.

        Can take no ids, a single id or a sequence of ids.
        """
        ids = _normalize_ids(arg)
        #assert all(isinstance(id, IdType) for id in ids), "Browsing invalid ids: %s" % ids
        return self._browse(ids, self.env, prefetch)

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
            The returned recordset has the same prefetch object as ``self``.

        :type env: :class:`~odoo.api.Environment`
        """
        return self._browse(self._ids, env, self._prefetch)

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
            The returned recordset has the same prefetch object as ``self``.

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

        .. note:

            The returned recordset has the same prefetch object as ``self``.
        """
        context = dict(args[0] if args else self._context, **kwargs)
        return self.with_env(self.env(context=context))

    def with_prefetch(self, prefetch=None):
        """ with_prefetch([prefetch]) -> records

        Return a new version of this recordset that uses the given prefetch
        object, or a new prefetch object if not given.
        """
        return self._browse(self._ids, self.env, prefetch)

    def _convert_to_cache(self, values, update=False, validate=True):
        """ Convert the ``values`` dictionary into cached values.

            :param update: whether the conversion is made for updating ``self``;
                this is necessary for interpreting the commands of *2many fields
            :param validate: whether values must be checked
        """
        fields = self._fields
        target = self if update else self.browse([], self._prefetch)
        return {
            name: fields[name].convert_to_cache(value, target, validate=validate)
            for name, value in values.iteritems()
            if name in fields
        }

    def _convert_to_record(self, values):
        """ Convert the ``values`` dictionary from the cache format to the
        record format.
        """
        return {
            name: self._fields[name].convert_to_record(value, self)
            for name, value in values.iteritems()
        }

    def _convert_to_write(self, values):
        """ Convert the ``values`` dictionary into the format of :meth:`write`. """
        fields = self._fields
        result = {}
        for name, value in values.iteritems():
            if name in fields:
                field = fields[name]
                value = field.convert_to_cache(value, self, validate=False)
                value = field.convert_to_record(value, self)
                value = field.convert_to_write(value, self)
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
                return vals[0].union(*vals)         # union of all recordsets
            return vals
        else:
            vals = func(self)
            return vals if isinstance(vals, BaseModel) else []

    def mapped(self, func):
        """ Apply ``func`` on all records in ``self``, and return the result as a
            list or a recordset (if ``func`` return recordsets). In the latter
            case, the order of the returned recordset is arbitrary.

            :param func: a function or a dot-separated sequence of field names
                (string); any falsy value simply returns the recordset ``self``
        """
        if not func:
            return self                 # support for an empty path of fields
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
            null = field.convert_to_cache(False, self, validate=False)
            recs = recs.mapped(lambda rec: field.convert_to_record(rec._cache.get(field, null), rec))
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
                comparison key for each record, or a field name, or ``None``, in
                which case records are ordered according the default model's order

            :param reverse: if ``True``, return the result in reverse order
        """
        if key is None:
            recs = self.search([('id', 'in', self.ids)])
            return self.browse(reversed(recs._ids)) if reverse else recs
        if isinstance(key, basestring):
            key = itemgetter(key)
        return self.browse(map(attrgetter('id'), sorted(self, key=key, reverse=reverse)))

    @api.multi
    def update(self, values):
        """ Update the records in ``self`` with ``values``. """
        for record in self:
            for name, value in values.iteritems():
                record[name] = value

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
            yield self._browse((id,), self.env, self._prefetch)

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
        return self.concat(other)

    def concat(self, *args):
        """ Return the concatenation of ``self`` with all the arguments (in
            linear time complexity).
        """
        ids = list(self._ids)
        for arg in args:
            if not (isinstance(arg, BaseModel) and arg._name == self._name):
                raise TypeError("Mixing apples and oranges: %s.concat(%s)" % (self, arg))
            ids.extend(arg._ids)
        return self.browse(ids)

    def __sub__(self, other):
        """ Return the recordset of all the records in ``self`` that are not in
            ``other``. Note that recordset order is preserved.
        """
        if not isinstance(other, BaseModel) or self._name != other._name:
            raise TypeError("Mixing apples and oranges: %s - %s" % (self, other))
        other_ids = set(other._ids)
        return self.browse([id for id in self._ids if id not in other_ids])

    def __and__(self, other):
        """ Return the intersection of two recordsets.
            Note that first occurrence order is preserved.
        """
        if not isinstance(other, BaseModel) or self._name != other._name:
            raise TypeError("Mixing apples and oranges: %s & %s" % (self, other))
        other_ids = set(other._ids)
        return self.browse(OrderedSet(id for id in self._ids if id in other_ids))

    def __or__(self, other):
        """ Return the union of two recordsets.
            Note that first occurrence order is preserved.
        """
        return self.union(other)

    def union(self, *args):
        """ Return the union of ``self`` with all the arguments (in linear time
            complexity, with first occurrence order preserved).
        """
        ids = list(self._ids)
        for arg in args:
            if not (isinstance(arg, BaseModel) and arg._name == self._name):
                raise TypeError("Mixing apples and oranges: %s.union(%s)" % (self, arg))
            ids.extend(arg._ids)
        return self.browse(OrderedSet(ids))

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
            return self._browse(self._ids[key], self.env)
        else:
            return self._browse((self._ids[key],), self.env)

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
        ids = filter(None, self._prefetch[self._name] - set(self.env.cache[field]))
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

        def process(res):
            if not res:
                return
            if res.get('value'):
                res['value'].pop('id', None)
                self.update({key: val for key, val in res['value'].iteritems() if key in self._fields})
            if res.get('domain'):
                result.setdefault('domain', {}).update(res['domain'])
            if res.get('warning'):
                if result.get('warning'):
                    # Concatenate multiple warnings
                    warning = result['warning']
                    warning['message'] = '\n\n'.join(filter(None, [
                        warning.get('title'),
                        warning.get('message'),
                        res['warning'].get('title'),
                        res['warning'].get('message'),
                    ]))
                    warning['title'] = _('Warnings')
                else:
                    result['warning'] = res['warning']

        # onchange V8
        if onchange in ("1", "true"):
            for method in self._onchange_methods.get(field_name, ()):
                method_res = method(self)
                process(method_res)
            return

        # onchange V7
        match = onchange_v7.match(onchange)
        if match:
            method, params = match.groups()

            class RawRecord(object):
                def __init__(self, record):
                    self._record = record
                def __getitem__(self, name):
                    record = self._record
                    field = record._fields[name]
                    return field.convert_to_write(record[name], record)
                def __getattr__(self, name):
                    return self[name]

            # evaluate params -> tuple
            global_vars = {'context': self._context, 'uid': self._uid}
            if self._context.get('field_parent'):
                record = self[self._context['field_parent']]
                global_vars['parent'] = RawRecord(record)
            field_vars = RawRecord(self)
            params = safe_eval("[%s]" % params, global_vars, field_vars, nocopy=True)

            # invoke onchange method
            method_res = getattr(self._origin, method)(*params)
            process(method_res)

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
            values = {name: record[name] for name in record._cache}
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
            name: self._fields[name].convert_to_onchange(record[name], record, subfields[name])
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


AbstractModel = BaseModel

class Model(AbstractModel):
    """ Main super-class for regular database-persisted Odoo models.

    Odoo models are created by inheriting from this class::

        class user(Model):
            ...

    The system will later instantiate the class once per database (on
    which the class' module is installed).
    """
    _auto = True                # automatically create database backend
    _register = False           # not visible in ORM registry, meant to be python-inherited only
    _abstract = False           # not abstract
    _transient = False          # not transient

class TransientModel(Model):
    """ Model super-class for transient records, meant to be temporarily
    persisted, and regularly vacuum-cleaned.

    A TransientModel has a simplified access rights management, all users can
    create new records, and may only access the records they created. The super-
    user has unrestricted access to all TransientModel records.
    """
    _auto = True                # automatically create database backend
    _register = False           # not visible in ORM registry, meant to be python-inherited only
    _abstract = False           # not abstract
    _transient = True           # transient

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

def _normalize_ids(arg, atoms=set(IdType)):
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
