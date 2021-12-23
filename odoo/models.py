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
     * Persistent object: DB postgresql
     * Data conversion
     * Multi-level caching system
     * Two different inheritance mechanisms
     * Rich set of field types:
          - classical (varchar, integer, boolean, ...)
          - relational (one2many, many2one, many2many)
          - functional

"""

import collections
import contextlib
import datetime
import dateutil
import fnmatch
import functools
import itertools
import io
import logging
import operator
import pytz
import re
import uuid
from collections import defaultdict, OrderedDict
from collections.abc import MutableMapping
from contextlib import closing
from inspect import getmembers, currentframe
from operator import attrgetter, itemgetter

import babel.dates
import dateutil.relativedelta
import psycopg2, psycopg2.extensions
from lxml import etree
from lxml.builder import E
from psycopg2.extensions import AsIs

import odoo
from . import SUPERUSER_ID
from . import api
from . import tools
from .exceptions import AccessError, MissingError, ValidationError, UserError
from .osv.query import Query
from .tools import frozendict, lazy_classproperty, ormcache, \
                   Collector, LastOrderedSet, OrderedSet, IterableGenerator, \
                   groupby, partition
from .tools.config import config
from .tools.func import frame_codeinfo
from .tools.misc import CountingStream, clean_context, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT, get_lang
from .tools.translate import _
from .tools import date_utils
from .tools import populate
from .tools import unique
from .tools.lru import LRU

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')
_unlink = logging.getLogger(__name__ + '.unlink')

regex_order = re.compile('^(\s*([a-z0-9:_]+|"[a-z0-9:_]+")(\s+(desc|asc))?\s*(,|$))+(?<!,)$', re.I)
regex_object_name = re.compile(r'^[a-z0-9_.]+$')
regex_pg_name = re.compile(r'^[a-z_][a-z0-9_$]*$', re.I)
regex_field_agg = re.compile(r'(\w+)(?::(\w+)(?:\((\w+)\))?)?')

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

def trigger_tree_merge(node1, node2):
    """ Merge two trigger trees. """
    for key, val in node2.items():
        if key is None:
            node1.setdefault(None, set())
            node1[None].update(val)
        else:
            node1.setdefault(key, {})
            trigger_tree_merge(node1[key], node2[key])


class MetaModel(api.Meta):
    """ The metaclass of all model classes.
        Its main purpose is to register the models per module.
    """

    module_to_models = defaultdict(list)

    def __new__(meta, name, bases, attrs):
        attrs.setdefault('__slots__', ())
        return super().__new__(meta, name, bases, attrs)

    def __init__(self, name, bases, attrs):
        if not self._register:
            self._register = True
            super(MetaModel, self).__init__(name, bases, attrs)
            return

        if not hasattr(self, '_module'):
            assert self.__module__.startswith('odoo.addons.'), \
                "Invalid import of %s.%s, it should start with 'odoo.addons'." % (self.__module__, name)
            self._module = self.__module__.split('.')[2]

        # Remember which models to instanciate for this module.
        if self._module:
            self.module_to_models[self._module].append(self)

        for key, val in attrs.items():
            if isinstance(val, Field):
                val.args['_module'] = self._module


class NewId(object):
    """ Pseudo-ids for new records, encapsulating an optional origin id (actual
        record id) and an optional reference (any value).
    """
    __slots__ = ['origin', 'ref']

    def __init__(self, origin=None, ref=None):
        self.origin = origin
        self.ref = ref

    def __bool__(self):
        return False

    def __eq__(self, other):
        return isinstance(other, NewId) and (
            (self.origin and other.origin and self.origin == other.origin)
            or (self.ref and other.ref and self.ref == other.ref)
        )

    def __hash__(self):
        return hash(self.origin or self.ref or id(self))

    def __repr__(self):
        return (
            "<NewId origin=%r>" % self.origin if self.origin else
            "<NewId ref=%r>" % self.ref if self.ref else
            "<NewId 0x%x>" % id(self)
        )

    def __str__(self):
        if self.origin or self.ref:
            id_part = repr(self.origin or self.ref)
        else:
            id_part = hex(id(self))
        return "NewId_%s" % id_part


def origin_ids(ids):
    """ Return an iterator over the origin ids corresponding to ``ids``.
        Actual ids are returned as is, and ids without origin are not returned.
    """
    return ((id_ or id_.origin) for id_ in ids if (id_ or getattr(id_, "origin", None)))


def expand_ids(id0, ids):
    """ Return an iterator of unique ids from the concatenation of ``[id0]`` and
        ``ids``, and of the same kind (all real or all new).
    """
    yield id0
    seen = {id0}
    kind = bool(id0)
    for id_ in ids:
        if id_ not in seen and bool(id_) == kind:
            yield id_
            seen.add(id_)


IdType = (int, str, NewId)


# maximum number of prefetched records
PREFETCH_MAX = 1000

# special columns automatically created by the ORM
LOG_ACCESS_COLUMNS = ['create_uid', 'create_date', 'write_uid', 'write_date']
MAGIC_COLUMNS = ['id'] + LOG_ACCESS_COLUMNS

# valid SQL aggregation functions
VALID_AGGREGATE_FUNCTIONS = {
    'array_agg', 'count', 'count_distinct',
    'bool_and', 'bool_or', 'max', 'min', 'avg', 'sum',
}


class BaseModel(MetaModel('DummyModel', (object,), {'_register': False})):
    """Base class for Odoo models.

    Odoo models are created by inheriting one of the following:

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

    To create a class that should not be instantiated,
    the :attr:`~odoo.models.BaseModel._register` attribute may be set to False.
    """
    __slots__ = ['env', '_ids', '_prefetch_ids']

    _auto = False
    """Whether a database table should be created.
    If set to ``False``, override :meth:`~odoo.models.BaseModel.init`
    to create the database table.

    Automatically defaults to `True` for :class:`Model` and
    :class:`TransientModel`, `False` for :class:`AbstractModel`.

    .. tip:: To create a model without any table, inherit
            from :class:`~odoo.models.AbstractModel`.
    """
    _register = False           #: registry visibility
    _abstract = True
    """ Whether the model is *abstract*.

    .. seealso:: :class:`AbstractModel`
    """
    _transient = False
    """ Whether the model is *transient*.

    .. seealso:: :class:`TransientModel`
    """

    _name = None                #: the model name (in dot-notation, module namespace)
    _description = None         #: the model's informal name
    _custom = False             #: should be True for custom models only

    _inherit = None
    """Python-inherited models:

    :type: str or list(str)

    .. note::

        * If :attr:`._name` is set, name(s) of parent models to inherit from
        * If :attr:`._name` is unset, name of a single model to extend in-place
    """
    _inherits = {}
    """dictionary {'parent_model': 'm2o_field'} mapping the _name of the parent business
    objects to the names of the corresponding foreign key fields to use::

      _inherits = {
          'a.model': 'a_field_id',
          'b.model': 'b_field_id'
      }

    implements composition-based inheritance: the new model exposes all
    the fields of the inherited models but stores none of them:
    the values themselves remain stored on the linked record.

    .. warning::

      if multiple fields with the same name are defined in the
      :attr:`~odoo.models.Model._inherits`-ed models, the inherited field will
      correspond to the last one (in the inherits list order).
    """
    _table = None               #: SQL table name used by model if :attr:`_auto`
    _table_query = None         #: SQL expression of the table's content (optional)
    _sequence = None            #: SQL sequence to use for ID field
    _sql_constraints = []       #: SQL constraints [(name, sql_def, message)]

    _rec_name = None            #: field to use for labeling records, default: ``name``
    _order = 'id'               #: default order field for searching results
    _parent_name = 'parent_id'  #: the many2one field used as parent field
    _parent_store = False
    """set to True to compute parent_path field.

    Alongside a :attr:`~.parent_path` field, sets up an indexed storage
    of the tree structure of records, to enable faster hierarchical queries
    on the records of the current model using the ``child_of`` and
    ``parent_of`` domain operators.
    """
    _active_name = None         #: field to use for active records
    _date_name = 'date'         #: field to use for default calendar view
    _fold_name = 'fold'         #: field to determine folded groups in kanban views

    _needaction = False         # whether the model supports "need actions" (Old API)
    _translate = True           # False disables translations export for this model (Old API)
    _check_company_auto = False
    """On write and create, call ``_check_company`` to ensure companies
    consistency on the relational fields having ``check_company=True``
    as attribute.
    """

    _depends = {}
    """dependencies of models backed up by SQL views
    ``{model_name: field_names}``, where ``field_names`` is an iterable.
    This is only used to determine the changes to flush to database before
    executing ``search()`` or ``read_group()``. It won't be used for cache
    invalidation or recomputing fields.
    """

    # default values for _transient_vacuum()
    _transient_max_count = lazy_classproperty(lambda _: config.get('osv_memory_count_limit'))
    _transient_max_hours = lazy_classproperty(lambda _: config.get('transient_age_limit'))

    CONCURRENCY_CHECK_FIELD = '__last_update'

    @api.model
    def view_init(self, fields_list):
        """ Override this method to do specific things when a form view is
        opened. This method is invoked by :meth:`~default_get`.
        """
        pass

    def _valid_field_parameter(self, field, name):
        """ Return whether the given parameter name is valid for the field. """
        return name == 'related_sudo'

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
        if cls._rec_name == name:
            # fixup _rec_name and display_name's dependencies
            cls._rec_name = None
            cls.display_name.depends = tuple(dep for dep in cls.display_name.depends if dep != name)
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
            add('create_uid', fields.Many2one(
                'res.users', string='Created by', automatic=True, readonly=True))
            add('create_date', fields.Datetime(
                string='Created on', automatic=True, readonly=True))
            add('write_uid', fields.Many2one(
                'res.users', string='Last Updated by', automatic=True, readonly=True))
            add('write_date', fields.Datetime(
                string='Last Updated on', automatic=True, readonly=True))
            last_modified_name = 'compute_concurrency_field_with_access'
        else:
            last_modified_name = 'compute_concurrency_field'

        # this field must override any other column or field
        self._add_field(self.CONCURRENCY_CHECK_FIELD, fields.Datetime(
            string='Last Modified on', compute=last_modified_name,
            compute_sudo=False, automatic=True))

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

        if getattr(cls, '_constraints', None):
            _logger.warning("Model attribute '_constraints' is no longer supported, "
                            "please use @api.constrains on methods instead.")

        # Keep links to non-inherited constraints in cls; this is useful for
        # instance when exporting translations
        cls._local_sql_constraints = cls.__dict__.get('_sql_constraints', [])

        # determine inherited models
        parents = cls._inherit
        parents = [parents] if isinstance(parents, str) else (parents or [])

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
                '_inherit_module': dict(),              # map parent to introducing module
                '_inherit_children': OrderedSet(),      # names of children models
                '_inherits_children': set(),            # names of children models
                '_fields': OrderedDict(),               # populated in _setup_base()
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
                ModelClass._inherit_module[parent] = cls._module
                parent_class._inherit_children.add(name)

        ModelClass.__bases__ = tuple(bases)

        # determine the attributes of the model's class
        ModelClass._build_model_attributes(pool)

        check_pg_name(ModelClass._table)

        # Transience
        if ModelClass._transient:
            assert ModelClass._log_access, \
                "TransientModels must have log_access turned on, " \
                "in order to implement their vacuum policy"

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
        cls._sql_constraints = {}

        for base in reversed(cls.__bases__):
            if not getattr(base, 'pool', None):
                # the following attributes are not taken from model classes
                parents = [base._inherit] if base._inherit and isinstance(base._inherit, str) else (base._inherit or [])
                if cls._name not in parents and not base._description:
                    _logger.warning("The model %s has no _description", cls._name)
                cls._description = base._description or cls._description
                cls._table = base._table or cls._table
                cls._sequence = base._sequence or cls._sequence
                cls._log_access = getattr(base, '_log_access', cls._log_access)

            cls._inherits.update(base._inherits)

            for mname, fnames in base._depends.items():
                cls._depends.setdefault(mname, []).extend(fnames)

            for cons in base._sql_constraints:
                cls._sql_constraints[cons[0]] = cons

        cls._sequence = cls._sequence or (cls._table + '_id_seq')
        cls._sql_constraints = list(cls._sql_constraints.values())

        # update _inherits_children of parent models
        for parent_name in cls._inherits:
            pool[parent_name]._inherits_children.add(cls._name)

        # recompute attributes of _inherit_children models
        for child_name in cls._inherit_children:
            child_class = pool[child_name]
            child_class._build_model_attributes(pool)

    @classmethod
    def _init_constraints_onchanges(cls):
        # store list of sql constraint qualified names
        for (key, _, _) in cls._sql_constraints:
            cls.pool._sql_constraints.add(cls._table + '_' + key)

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
                elif not (field.store or field.inverse or field.inherited):
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

        # collect onchange methods on the model's class
        cls = type(self)
        methods = defaultdict(list)
        for attr, func in getmembers(cls, is_onchange):
            missing = []
            for name in func._onchange:
                if name not in cls._fields:
                    missing.append(name)
                methods[name].append(func)
            if missing:
                _logger.warning(
                    "@api.onchange%r parameters must be field names -> not valid: %s",
                    func._onchange, missing
                )

        # add onchange methods to implement "change_default" on fields
        def onchange_default(field, self):
            value = field.convert_to_write(self[field.name], self)
            condition = "%s=%s" % (field.name, value)
            defaults = self.env['ir.default'].get_model_defaults(self._name, condition)
            self.update(defaults)

        for name, field in cls._fields.items():
            if field.change_default:
                methods[name].append(functools.partial(onchange_default, field))

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

    def _is_an_ordinary_table(self):
        return self.pool.is_an_ordinary_table(self)

    def __ensure_xml_id(self, skip=False):
        """ Create missing external ids for records in ``self``, and return an
            iterator of pairs ``(record, xmlid)`` for the records in ``self``.

        :rtype: Iterable[Model, str | None]
        """
        if skip:
            return ((record, None) for record in self)

        if not self:
            return iter([])

        if not self._is_an_ordinary_table():
            raise Exception(
                "You can not export the column ID of model %s, because the "
                "table %s is not an ordinary table."
                % (self._name, self._table))

        modname = '__export__'

        cr = self.env.cr
        cr.execute("""
            SELECT res_id, module, name
            FROM ir_model_data
            WHERE model = %s AND res_id in %s
        """, (self._name, tuple(self.ids)))
        xids = {
            res_id: (module, name)
            for res_id, module, name in cr.fetchall()
        }
        def to_xid(record_id):
            (module, name) = xids[record_id]
            return ('%s.%s' % (module, name)) if module else name

        # create missing xml ids
        missing = self.filtered(lambda r: r.id not in xids)
        if not missing:
            return (
                (record, to_xid(record.id))
                for record in self
            )

        xids.update(
            (r.id, (modname, '%s_%s_%s' % (
                r._table,
                r.id,
                uuid.uuid4().hex[:8],
            )))
            for r in missing
        )
        fields = ['module', 'model', 'name', 'res_id']

        # disable eventual async callback / support for the extent of
        # the COPY FROM, as these are apparently incompatible
        callback = psycopg2.extensions.get_wait_callback()
        psycopg2.extensions.set_wait_callback(None)
        try:
            cr.copy_from(io.StringIO(
                u'\n'.join(
                    u"%s\t%s\t%s\t%d" % (
                        modname,
                        record._name,
                        xids[record.id][1],
                        record.id,
                    )
                    for record in missing
                )),
                table='ir_model_data',
                columns=fields,
            )
        finally:
            psycopg2.extensions.set_wait_callback(callback)
        self.env['ir.model.data'].invalidate_cache(fnames=fields)

        return (
            (record, to_xid(record.id))
            for record in self
        )

    def _export_rows(self, fields, *, _is_toplevel_call=True):
        """ Export fields of the records in ``self``.

            :param fields: list of lists of fields to traverse
            :param bool _is_toplevel_call:
                used when recursing, avoid using when calling from outside
            :return: list of lists of corresponding values
        """
        import_compatible = self.env.context.get('import_compat', True)
        lines = []

        def splittor(rs):
            """ Splits the self recordset in batches of 1000 (to avoid
            entire-recordset-prefetch-effects) & removes the previous batch
            from the cache after it's been iterated in full
            """
            for idx in range(0, len(rs), 1000):
                sub = rs[idx:idx+1000]
                for rec in sub:
                    yield rec
                rs.invalidate_cache(ids=sub.ids)
        if not _is_toplevel_call:
            splittor = lambda rs: rs

        # memory stable but ends up prefetching 275 fields (???)
        for record in splittor(self):
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
                    current[i] = (record._name, record.id)
                else:
                    field = record._fields[name]
                    value = record[name]

                    # this part could be simpler, but it has to be done this way
                    # in order to reproduce the former behavior
                    if not isinstance(value, BaseModel):
                        current[i] = field.convert_to_export(value, record)
                    else:
                        primary_done.append(name)
                        # recursively export the fields that follow name; use
                        # 'display_name' where no subfield is exported
                        fields2 = [(p[1:] or ['display_name'] if p and p[0] == name else [])
                                   for p in fields]

                        # in import_compat mode, m2m should always be exported as
                        # a comma-separated list of xids or names in a single cell
                        if import_compatible and field.type == 'many2many':
                            index = None
                            # find out which subfield the user wants & its
                            # location as we might not get it as the first
                            # column we encounter
                            for name in ['id', 'name', 'display_name']:
                                with contextlib.suppress(ValueError):
                                    index = fields2.index([name])
                                    break
                            if index is None:
                                # not found anything, assume we just want the
                                # name_get in the first column
                                name = None
                                index = i

                            if name == 'id':
                                xml_ids = [xid for _, xid in value.__ensure_xml_id()]
                                current[index] = ','.join(xml_ids) or False
                            else:
                                current[index] = field.convert_to_export(value, record) or False
                            continue

                        lines2 = value._export_rows(fields2, _is_toplevel_call=False)
                        if lines2:
                            # merge first line with record's main line
                            for j, val in enumerate(lines2[0]):
                                if val or isinstance(val, (int, float)):
                                    current[j] = val
                            # append the other lines at the end
                            lines += lines2[1:]
                        else:
                            current[i] = False

        # if any xid should be exported, only do so at toplevel
        if _is_toplevel_call and any(f[-1] == 'id' for f in fields):
            bymodels = collections.defaultdict(set)
            xidmap = collections.defaultdict(list)
            # collect all the tuples in "lines" (along with their coordinates)
            for i, line in enumerate(lines):
                for j, cell in enumerate(line):
                    if type(cell) is tuple:
                        bymodels[cell[0]].add(cell[1])
                        xidmap[cell].append((i, j))
            # for each model, xid-export everything and inject in matrix
            for model, ids in bymodels.items():
                for record, xid in self.env[model].browse(ids).__ensure_xml_id():
                    for i, j in xidmap.pop((record._name, record.id)):
                        lines[i][j] = xid
            assert not xidmap, "failed to export xids for %s" % ', '.join('{}:{}' % it for it in xidmap.items())

        return lines

    # backward compatibility
    __export_rows = _export_rows

    def export_data(self, fields_to_export):
        """ Export fields for selected objects

            :param fields_to_export: list of fields
            :param raw_data: True to return value in native Python type
            :rtype: dictionary with a *datas* matrix

            This method is used when exporting data via client menu
        """
        if not (self.env.is_admin() or self.env.user.has_group('base.group_allow_export')):
            raise UserError(_("You don't have the rights to export data. Please contact an Administrator."))
        fields_to_export = [fix_import_export_id_paths(f) for f in fields_to_export]
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
        :returns: {ids: list(int)|False, messages: [Message][, lastrow: int]}
        """
        self.flush()

        # determine values of mode, current_module and noupdate
        mode = self._context.get('mode', 'init')
        current_module = self._context.get('module', '__import__')
        noupdate = self._context.get('noupdate', False)
        # add current module in context for the conversion of xml ids
        self = self.with_context(_import_current_module=current_module)

        cr = self._cr
        cr.execute('SAVEPOINT model_load')

        fields = [fix_import_export_id_paths(f) for f in fields]
        fg = self.fields_get()

        ids = []
        messages = []
        ModelData = self.env['ir.model.data']

        # list of (xid, vals, info) for records to be created in batch
        batch = []
        batch_xml_ids = set()
        # models in which we may have created / modified data, therefore might
        # require flushing in order to name_search: the root model and any
        # o2m
        creatable_models = {self._name}
        for field_path in fields:
            if field_path[0] in (None, 'id', '.id'):
                continue
            model_fields = self._fields
            if isinstance(model_fields[field_path[0]], odoo.fields.Many2one):
                # this only applies for toplevel m2o (?) fields
                if field_path[0] in (self.env.context.get('name_create_enabled_fieds') or {}):
                    creatable_models.add(model_fields[field_path[0]].comodel_name)
            for field_name in field_path:
                if field_name in (None, 'id', '.id'):
                    break

                if isinstance(model_fields[field_name], odoo.fields.One2many):
                    comodel = model_fields[field_name].comodel_name
                    creatable_models.add(comodel)
                    model_fields = self.env[comodel]._fields

        def flush(*, xml_id=None, model=None):
            if not batch:
                return

            assert not (xml_id and model), \
                "flush can specify *either* an external id or a model, not both"

            if xml_id and xml_id not in batch_xml_ids:
                if xml_id not in self.env:
                    return
            if model and model not in creatable_models:
                return

            data_list = [
                dict(xml_id=xid, values=vals, info=info, noupdate=noupdate)
                for xid, vals, info in batch
            ]
            batch.clear()
            batch_xml_ids.clear()

            # try to create in batch
            try:
                with cr.savepoint():
                    recs = self._load_records(data_list, mode == 'update')
                    ids.extend(recs.ids)
                return
            except psycopg2.InternalError as e:
                # broken transaction, exit and hope the source error was already logged
                if not any(message['type'] == 'error' for message in messages):
                    info = data_list[0]['info']
                    messages.append(dict(info, type='error', message=_(u"Unknown database error: '%s'", e)))
                return
            except Exception:
                pass

            errors = 0
            # try again, this time record by record
            for i, rec_data in enumerate(data_list, 1):
                try:
                    with cr.savepoint():
                        rec = self._load_records([rec_data], mode == 'update')
                        ids.append(rec.id)
                except psycopg2.Warning as e:
                    info = rec_data['info']
                    messages.append(dict(info, type='warning', message=str(e)))
                except psycopg2.Error as e:
                    info = rec_data['info']
                    messages.append(dict(info, type='error', **PGERROR_TO_OE[e.pgcode](self, fg, info, e)))
                    # Failed to write, log to messages, rollback savepoint (to
                    # avoid broken transaction) and keep going
                    errors += 1
                except Exception as e:
                    _logger.debug("Error while loading record", exc_info=True)
                    info = rec_data['info']
                    message = (_(u'Unknown error during import:') + u' %s: %s' % (type(e), e))
                    moreinfo = _('Resolve other errors first')
                    messages.append(dict(info, type='error', message=message, moreinfo=moreinfo))
                    # Failed for some reason, perhaps due to invalid data supplied,
                    # rollback savepoint and keep going
                    errors += 1
                if errors >= 10 and (errors >= i / 10):
                    messages.append({
                        'type': 'warning',
                        'message': _(u"Found more than 10 errors and more than one error per 10 records, interrupted to avoid showing too many errors.")
                    })
                    break

        # make 'flush' available to the methods below, in the case where XMLID
        # resolution fails, for instance
        flush_self = self.with_context(import_flush=flush, import_cache=LRU(1024))

        # TODO: break load's API instead of smuggling via context?
        limit = self._context.get('_import_limit')
        if limit is None:
            limit = float('inf')
        extracted = flush_self._extract_records(fields, data, log=messages.append, limit=limit)

        converted = flush_self._convert_records(extracted, log=messages.append)

        info = {'rows': {'to': -1}}
        for id, xid, record, info in converted:
            if xid:
                xid = xid if '.' in xid else "%s.%s" % (current_module, xid)
                batch_xml_ids.add(xid)
            elif id:
                record['id'] = id
            batch.append((xid, record, info))

        flush()
        if any(message['type'] == 'error' for message in messages):
            cr.execute('ROLLBACK TO SAVEPOINT model_load')
            ids = False
            # cancel all changes done to the registry/ormcache
            self.pool.reset_changes()

        nextrow = info['rows']['to'] + 1
        if nextrow < limit:
            nextrow = 0
        return {
            'ids': ids,
            'messages': messages,
            'nextrow': nextrow,
        }

    def _add_fake_fields(self, fields):
        from odoo.fields import Char, Integer
        fields[None] = Char('rec_name')
        fields['id'] = Char('External ID')
        fields['.id'] = Integer('Database ID')
        return fields

    def _extract_records(self, fields_, data, log=lambda a: None, limit=float('inf')):
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
        while index < len(data) and index < limit:
            row = data[index]

            # copy non-relational fields to record dict
            record = {fnames[0]: value
                      for fnames, value in zip(fields_, row)
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
                relfield_data = [it for it in map(itemgetter_tuple(indices), record_span) if any(it)]
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
        field_names = {name: field.string for name, field in self._fields.items()}
        if self.env.lang:
            field_names.update(self.env['ir.translation'].get_field_string(self._name))

        convert = self.env['ir.fields.converter'].for_model(self)

        def _log(base, record, field, exception):
            type = 'warning' if isinstance(exception, Warning) else 'error'
            # logs the logical (not human-readable) field name for automated
            # processing of response, but injects human readable in message
            exc_vals = dict(base, record=record, field=field_names[field])
            record = dict(base, type=type, record=record, field=field,
                          message=str(exception.args[0]) % exc_vals)
            if len(exception.args) > 1 and isinstance(exception.args[1], dict):
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
                        message=_(u"Unknown database identifier '%s'", dbid)))
                    dbid = False

            converted = convert(record, functools.partial(_log, extras, stream.index))

            yield dbid, xid, converted, dict(extras, record=stream.index)

    def _validate_fields(self, field_names, excluded_names=()):
        """ Invoke the constraint methods for which at least one field name is
        in ``field_names`` and none is in ``excluded_names``.
        """
        field_names = set(field_names)
        excluded_names = set(excluded_names)
        for check in self._constraint_methods:
            if (not field_names.isdisjoint(check._constrains)
                    and excluded_names.isdisjoint(check._constrains)):
                check(self)

    @api.model
    def default_get(self, fields_list):
        """ default_get(fields_list) -> default_values

        Return default values for the fields in ``fields_list``. Default
        values are determined by the context, user defaults, and the model
        itself.

        :param list fields_list: names of field whose default is requested
        :return: a dictionary mapping field names to their corresponding default values,
            if they have a default value.
        :rtype: dict

        .. note::

            Unrequested defaults won't be considered, there is no need to return a
            value for fields whose names are not in `fields_list`.
        """
        # trigger view init hook
        self.view_init(fields_list)

        defaults = {}
        parent_fields = defaultdict(list)
        ir_defaults = self.env['ir.default'].get_model_defaults(self._name)

        for name in fields_list:
            # 1. look up context
            key = 'default_' + name
            if key in self._context:
                defaults[name] = self._context[key]
                continue

            # 2. look up ir.default
            if name in ir_defaults:
                defaults[name] = ir_defaults[name]
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
        #
        # we explicitly avoid using _convert_to_write() for x2many fields,
        # because the latter leaves values like [(4, 2), (4, 3)], which are not
        # supported by the web client as default values; stepping through the
        # cache allows to normalize such a list to [(6, 0, [2, 3])], which is
        # properly supported by the web client
        for fname, value in defaults.items():
            if fname in self._fields:
                field = self._fields[fname]
                value = field.convert_to_cache(value, self, validate=False)
                defaults[fname] = field.convert_to_write(value, self)

        # add default values for inherited fields
        for model, names in parent_fields.items():
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
                if user.has_group(group_ext_id) and request and request.session.debug:
                    return False
            else:
                if user.has_group(group_ext_id):
                    return False

        for group_ext_id in has_groups:
            if group_ext_id == 'base.group_no_one':
                # check: the group_no_one is effective in debug mode only
                if user.has_group(group_ext_id) and request and request.session.debug:
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
        for fname, field in self._fields.items():
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
        content_div = E.div(field, {'class': "o_kanban_card_content"})
        card_div = E.div(content_div, {'t-attf-class': "oe_kanban_card oe_kanban_global_click"})
        kanban_box = E.t(card_div, {'t-name': "kanban-box"})
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

        if not set_first_of([self._date_name, 'date', 'date_start', 'x_date', 'x_date_start'],
                            self._fields, 'date_start'):
            raise UserError(_("Insufficient fields for Calendar View!"))

        set_first_of(["user_id", "partner_id", "x_user_id", "x_partner_id"],
                     self._fields, 'color')

        if not set_first_of(["date_stop", "date_end", "x_date_stop", "x_date_end"],
                            self._fields, 'date_stop'):
            if not set_first_of(["date_delay", "planned_hours", "x_date_delay", "x_planned_hours"],
                                self._fields, 'date_delay'):
                raise UserError(_("Insufficient fields to generate a Calendar View for %s, missing a date_stop or a date_delay", self._name))

        return view

    @api.model
    def load_views(self, views, options=None):
        """ Returns the fields_views of given views, along with the fields of
            the current model, and optionally its filters for the given action.

        :param views: list of [view_id, view_type]
        :param options['toolbar']: True to include contextual actions when loading fields_views
        :param options['load_filters']: True to return the model's filters
        :param options['action_id']: id of the action to get the filters
        :return: dictionary with fields_views, fields and optionally filters
        """
        options = options or {}
        result = {}

        toolbar = options.get('toolbar')
        result['fields_views'] = {
            v_type: self.fields_view_get(v_id, v_type if v_type != 'list' else 'tree',
                                         toolbar=toolbar if v_type != 'search' else False)
            for [v_id, v_type] in views
        }
        result['fields'] = self.fields_get()

        if options.get('load_filters'):
            result['filters'] = self.env['ir.filters'].get_filters(self._name, options.get('action_id'))


        return result

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        View = self.env['ir.ui.view'].sudo()
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

        if view_id:
            # read the view with inherited views applied
            root_view = View.browse(view_id).read_combined(['id', 'name', 'field_parent', 'type', 'model', 'arch'])
            result['arch'] = root_view['arch']
            result['name'] = root_view['name']
            result['type'] = root_view['type']
            result['view_id'] = root_view['id']
            result['field_parent'] = root_view['field_parent']
            result['base_model'] = root_view['model']
        else:
            # fallback on default views methods if no ir.ui.view could be found
            try:
                arch_etree = getattr(self, '_get_default_%s_view' % view_type)()
                result['arch'] = etree.tostring(arch_etree, encoding='unicode')
                result['type'] = view_type
                result['name'] = 'default'
            except AttributeError:
                raise UserError(_("No default view of type '%s' could be found !", view_type))
        return result

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """ fields_view_get([view_id | view_type='form'])

        Get the detailed composition of the requested view like fields, model, view architecture

        :param int view_id: id of the view or None
        :param str view_type: type of the view to return if view_id is None ('form', 'tree', ...)
        :param bool toolbar: true to include contextual actions
        :param submenu: deprecated
        :return: composition of the requested view (including inherited views and extensions)
        :rtype: dict
        :raise AttributeError:
                * if the inherited view has unknown position to work with other than 'before', 'after', 'inside', 'replace'
                * if some tag other than 'position' is found in parent view
        :raise Invalid ArchitectureError: if there is view type other than form, tree, calendar, search etc defined on the structure
        """
        self.check_access_rights('read')
        view = self.env['ir.ui.view'].sudo().browse(view_id)

        # Get the view arch and all other attributes describing the composition of the view
        result = self._fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        # Override context for postprocessing
        if view_id and result.get('base_model', self._name) != self._name:
            view = view.with_context(base_model_name=result['base_model'])

        # Apply post processing, groups and modifiers etc...
        xarch, xfields = view.postprocess_and_fields(etree.fromstring(result['arch']), model=self._name)
        result['arch'] = xarch
        result['fields'] = xfields

        # Add related action information if aksed
        if toolbar:
            vt = 'list' if view_type == 'tree' else view_type
            bindings = self.env['ir.actions.actions'].get_bindings(self._name)
            resreport = [action
                         for action in bindings['report']
                         if vt in (action.get('binding_view_types') or vt).split(',')]
            resaction = [action
                         for action in bindings['action']
                         if vt in (action.get('binding_view_types') or vt).split(',')]

            result['toolbar'] = {
                'print': resreport,
                'action': resaction,
            }
        return result

    def get_formview_id(self, access_uid=None):
        """ Return an view id to open the document ``self`` with. This method is
            meant to be overridden in addons that want to give specific view ids
            for example.

            Optional access_uid holds the user that would access the form view
            id different from the current environment user.
        """
        return False

    def get_formview_action(self, access_uid=None):
        """ Return an action to open the document ``self``. This method is meant
            to be overridden in addons that want to give specific view ids for
            example.

        An optional access_uid holds the user that will access the document
        that could be different from the current user. """
        view_id = self.sudo().get_formview_id(access_uid=access_uid)
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

    def get_access_action(self, access_uid=None):
        """ Return an action to open the document. This method is meant to be
        overridden in addons that want to give specific access to the document.
        By default it opens the formview of the document.

        An optional access_uid holds the user that will access the document
        that could be different from the current user.
        """
        return self[0].get_formview_action(access_uid=access_uid)

    @api.model
    def search_count(self, args):
        """ search_count(args) -> int

        Returns the number of records in the current model matching :ref:`the
        provided domain <reference/orm/domains>`.
        """
        res = self.search(args, count=True)
        return res if isinstance(res, int) else len(res)

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
        """Compute the value of the `display_name` field.

        In general `display_name` is equal to calling `name_get()[0][1]`.

        In that case, it is recommended to use `display_name` to uniformize the
        code and to potentially take advantage of prefetch when applicable.

        However some models might override this method. For them, the behavior
        might differ, and it is important to select which of `display_name` or
        `name_get()[0][1]` to call depending on the desired result.
        """
        names = dict(self.name_get())
        for record in self:
            record.display_name = names.get(record.id, False)

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
        ids = self._name_search(name, args, operator, limit=limit)
        return self.browse(ids).sudo().name_get()

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """ _name_search(name='', args=None, operator='ilike', limit=100, name_get_uid=None) -> ids

        Private implementation of name_search, allows passing a dedicated user
        for the name_get part to solve some access rights issues.
        """
        args = list(args or [])
        # optimize out the default criterion of ``ilike ''`` that matches everything
        if not self._rec_name:
            _logger.warning("Cannot execute name_search, no _rec_name defined on %s", self._name)
        elif not (name == '' and operator == 'ilike'):
            args += [(self._rec_name, operator, name)]
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    @api.model
    def _add_missing_default_values(self, values):
        # avoid overriding inherited values when parent is set
        avoid_models = set()

        def collect_models_to_avoid(model):
            for parent_mname, parent_fname in model._inherits.items():
                if parent_fname in values:
                    avoid_models.add(parent_mname)
                else:
                    # manage the case where an ancestor parent field is set
                    collect_models_to_avoid(self.env[parent_mname])

        collect_models_to_avoid(self)

        def avoid(field):
            # check whether the field is inherited from one of avoid_models
            if avoid_models:
                while field.inherited:
                    field = field.related_field
                    if field.model_name in avoid_models:
                        return True
            return False

        # compute missing fields
        missing_defaults = {
            name
            for name, field in self._fields.items()
            if name not in values
            if not avoid(field)
        }

        if not missing_defaults:
            return values

        # override defaults with the provided values, never allow the other way around
        defaults = self.default_get(list(missing_defaults))
        for name, value in defaults.items():
            if self._fields[name].type == 'many2many' and value and isinstance(value[0], int):
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
        cls.pool._clear_cache()

    @api.model
    def _read_group_expand_full(self, groups, domain, order):
        """Extend the group to include all targer records by default."""
        return groups.search([], order=order)

    @api.model
    def _read_group_fill_results(self, domain, groupby, remaining_groupbys,
                                 aggregated_fields, count_field,
                                 read_group_result, read_group_order=None):
        """Helper method for filling in empty groups for all possible values of
           the field being grouped by"""
        field = self._fields[groupby]
        if not field.group_expand:
            return read_group_result

        # field.group_expand is the name of a method that returns the groups
        # that we want to display for this field, in the form of a recordset or
        # a list of values (depending on the type of the field). This is useful
        # to implement kanban views for instance, where some columns should be
        # displayed even if they don't contain any record.

        # determine all groups that should be returned
        values = [line[groupby] for line in read_group_result if line[groupby]]

        if field.relational:
            # groups is a recordset; determine order on groups's model
            groups = self.env[field.comodel_name].browse([value[0] for value in values])
            order = groups._order
            if read_group_order == groupby + ' desc':
                order = tools.reverse_order(order)
            groups = getattr(self, field.group_expand)(groups, domain, order)
            groups = groups.sudo()
            values = lazy_name_get(groups)
            value2key = lambda value: value and value[0]

        else:
            # groups is a list of values
            values = getattr(self, field.group_expand)(values, domain, None)
            if read_group_order == groupby + ' desc':
                values.reverse()
            value2key = lambda value: value

        # Merge the current results (list of dicts) with all groups. Determine
        # the global order of results groups, which is supposed to be in the
        # same order as read_group_result (in the case of a many2one field).
        result = OrderedDict((value2key(value), {}) for value in values)

        # fill in results from read_group_result
        for line in read_group_result:
            key = value2key(line[groupby])
            if not result.get(key):
                result[key] = line
            else:
                result[key][count_field] = line[count_field]

        # fill in missing results from all groups
        for value in values:
            key = value2key(value)
            if not result[key]:
                line = dict.fromkeys(aggregated_fields, False)
                line[groupby] = value
                line[groupby + '_count'] = 0
                line['__domain'] = [(groupby, '=', key)] + domain
                if remaining_groupbys:
                    line['__context'] = {'group_by': remaining_groupbys}
                result[key] = line

        # add folding information if present
        if field.relational and groups._fold_name in groups._fields:
            fold = {group.id: group[groups._fold_name]
                    for group in groups.browse([key for key in result if key])}
            for key, line in result.items():
                line['__fold'] = fold.get(key, False)

        return list(result.values())

    @api.model
    def _read_group_fill_temporal(self, data, groupby, aggregated_fields, annotated_groupbys,
                                  interval=dateutil.relativedelta.relativedelta(months=1)):
        """Helper method for filling date/datetime 'holes' in a result set.

        We are in a use case where data are grouped by a date field (typically
        months but it could be any other interval) and displayed in a chart.

        Assume we group records by month, and we only have data for August,
        September and December. By default, plotting the result gives something
        like:
                                                ___
                                      ___      |   |
                                     |   |     |   |
                                     |   | ___ |   |
                                     |   ||   ||   |
                                     |___||___||___|
                                      Aug  Sep  Dec

        The problem is that December data follows immediately September data,
        which is misleading for the user. Adding explicit zeroes for missing data
        gives something like:
                                                     ___
                                 ___                |   |
                                |   |               |   |
                                |   | ___           |   |
                                |   ||   |          |   |
                                |___||___| ___  ___ |___|
                                 Aug  Sep  Oct  Nov  Dec

        :param list data: the data containing groups
        :param list groupby: name of the first group by
        :param list aggregated_fields: list of aggregated fields in the query
        :param relativedelta interval: interval between two temporal groups
                expressed as a relativedelta month by default
        :rtype: list
        :return: list
        """
        first_a_gby = annotated_groupbys[0]
        if not data:
            return data
        if first_a_gby['type'] not in ('date', 'datetime'):
            return data
        interval = first_a_gby['interval']
        groupby_name = groupby[0]

        # existing non null datetimes
        existing = [d[groupby_name] for d in data if d[groupby_name]]

        if len(existing) < 2:
            return data

        # assumption: existing data is sorted by field 'groupby_name'
        first, last = existing[0], existing[-1]

        empty_item = {'id': False, (groupby_name.split(':')[0] + '_count'): 0}
        empty_item.update({key: False for key in aggregated_fields})
        empty_item.update({key: False for key in [group['groupby'] for group in annotated_groupbys[1:]]})

        grouped_data = collections.defaultdict(list)
        for d in data:
            grouped_data[d[groupby_name]].append(d)

        result = []

        for dt in date_utils.date_range(first, last, interval):
            result.extend(grouped_data[dt] or [dict(empty_item, **{groupby_name: dt})])

        if False in grouped_data:
            result.extend(grouped_data[False])

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
        if not orderby:
            return groupby_terms, orderby_terms

        self._check_qorder(orderby)

        # when a field is grouped as 'foo:bar', both orderby='foo' and
        # orderby='foo:bar' generate the clause 'ORDER BY "foo:bar"'
        groupby_fields = {
            gb[key]: gb['groupby']
            for gb in annotated_groupbys
            for key in ('field', 'groupby')
        }
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
                    order_split[0] = '"%s"' % groupby_fields.get(order_field, order_field)
                    orderby_terms.append(' '.join(order_split))
            elif order_field in aggregated_fields:
                order_split[0] = '"%s"' % order_field
                orderby_terms.append(' '.join(order_split))
            elif order_field not in self._fields:
                raise ValueError("Invalid field %r on model %r" % (order_field, self._name))
            else:
                # Cannot order by a field that will not appear in the results (needs to be grouped or aggregated)
                _logger.warning('%s: read_group order by `%s` ignored, cannot sort on empty columns (not grouped/aggregated)',
                             self._name, order_part)

        return groupby_terms, orderby_terms

    @api.model
    def _read_group_process_groupby(self, gb, query):
        """
            Helper method to collect important information about groupbys: raw
            field name, type, time information, qualified name, ...
        """
        split = gb.split(':')
        field = self._fields.get(split[0])
        if not field:
            raise ValueError("Invalid field %r on model %r" % (split[0], self._name))
        field_type = field.type
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
                # Cfr: http://babel.pocoo.org/en/latest/dates.html#date-fields
                'hour': 'hh:00 dd MMM',
                'day': 'dd MMM yyyy', # yyyy = normal year
                'week': "'W'w YYYY",  # w YYYY = ISO week-year
                'month': 'MMMM yyyy',
                'quarter': 'QQQ yyyy',
                'year': 'yyyy',
            }
            time_intervals = {
                'hour': dateutil.relativedelta.relativedelta(hours=1),
                'day': dateutil.relativedelta.relativedelta(days=1),
                'week': datetime.timedelta(days=7),
                'month': dateutil.relativedelta.relativedelta(months=1),
                'quarter': dateutil.relativedelta.relativedelta(months=3),
                'year': dateutil.relativedelta.relativedelta(years=1)
            }
            if tz_convert:
                qualified_field = "timezone('%s', timezone('UTC',%s))" % (self._context.get('tz', 'UTC'), qualified_field)
            qualified_field = "date_trunc('%s', %s::timestamp)" % (gb_function or 'month', qualified_field)
        if field_type == 'boolean':
            qualified_field = "coalesce(%s,false)" % qualified_field
        return {
            'field': split[0],
            'groupby': gb,
            'type': field_type, 
            'display_format': display_formats[gb_function or 'month'] if temporal else None,
            'interval': time_intervals[gb_function or 'month'] if temporal else None,                
            'tz_convert': tz_convert,
            'qualified_field': qualified_field,
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
            if isinstance(value, str):
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
                    locale = get_lang(self.env).code
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
                        # take into account possible hour change between start and end
                        range_end = tzinfo.localize(range_end.replace(tzinfo=None))
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
        """Get the list of records in list view grouped by the given ``groupby`` fields.

        :param list domain: :ref:`A search domain <reference/orm/domains>`. Use an empty
                     list to match all records.
        :param list fields: list of fields present in the list view specified on the object.
                Each element is either 'field' (field name, using the default aggregation),
                or 'field:agg' (aggregate field with aggregation function 'agg'),
                or 'name:agg(field)' (aggregate field with 'agg' and return it as 'name').
                The possible aggregation functions are the ones provided by PostgreSQL
                (https://www.postgresql.org/docs/current/static/functions-aggregate.html)
                and 'count_distinct', with the expected meaning.
        :param list groupby: list of groupby descriptions by which the records will be grouped.  
                A groupby description is either a field (then it will be grouped by that field)
                or a string 'field:groupby_function'.  Right now, the only functions supported
                are 'day', 'week', 'month', 'quarter' or 'year', and they only make sense for 
                date/datetime fields.
        :param int offset: optional number of records to skip
        :param int limit: optional max number of records to return
        :param str orderby: optional ``order by`` specification, for
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

        groupby = [groupby] if isinstance(groupby, str) else list(OrderedSet(groupby))
        dt = [
            f for f in groupby
            if self._fields[f.split(':')[0]].type in ('date', 'datetime')    # e.g. 'date:month'
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
        fields = fields or [f.name for f in self._fields.values() if f.store]

        groupby = [groupby] if isinstance(groupby, str) else list(OrderedSet(groupby))
        groupby_list = groupby[:1] if lazy else groupby
        annotated_groupbys = [self._read_group_process_groupby(gb, query) for gb in groupby_list]
        groupby_fields = [g['field'] for g in annotated_groupbys]
        order = orderby or ','.join([g for g in groupby_list])
        groupby_dict = {gb['groupby']: gb for gb in annotated_groupbys}

        self._apply_ir_rules(query, 'read')
        for gb in groupby_fields:
            if gb not in self._fields:
                raise UserError(_("Unknown field %r in 'groupby'") % gb)
            gb_field = self._fields[gb].base_field
            if not (gb_field.store and gb_field.column_type):
                raise UserError(_("Fields in 'groupby' must be database-persisted fields (no computed fields)"))

        aggregated_fields = []
        select_terms = []
        fnames = []                     # list of fields to flush

        for fspec in fields:
            if fspec == 'sequence':
                continue
            if fspec == '__count':
                # the web client sometimes adds this pseudo-field in the list
                continue

            match = regex_field_agg.match(fspec)
            if not match:
                raise UserError(_("Invalid field specification %r.", fspec))

            name, func, fname = match.groups()
            if func:
                # we have either 'name:func' or 'name:func(fname)'
                fname = fname or name
                field = self._fields.get(fname)
                if not field:
                    raise ValueError("Invalid field %r on model %r" % (fname, self._name))
                if not (field.base_field.store and field.base_field.column_type):
                    raise UserError(_("Cannot aggregate field %r.", fname))
                if func not in VALID_AGGREGATE_FUNCTIONS:
                    raise UserError(_("Invalid aggregation function %r.", func))
            else:
                # we have 'name', retrieve the aggregator on the field
                field = self._fields.get(name)
                if not field:
                    raise ValueError("Invalid field %r on model %r" % (name, self._name))
                if not (field.base_field.store and
                        field.base_field.column_type and field.group_operator):
                    continue
                func, fname = field.group_operator, name

            fnames.append(fname)

            if fname in groupby_fields:
                continue
            if name in aggregated_fields:
                raise UserError(_("Output name %r is used twice.", name))
            aggregated_fields.append(name)

            expr = self._inherits_join_calc(self._table, fname, query)
            if func.lower() == 'count_distinct':
                term = 'COUNT(DISTINCT %s) AS "%s"' % (expr, name)
            else:
                term = '%s(%s) AS "%s"' % (func, expr, name)
            select_terms.append(term)

        for gb in annotated_groupbys:
            select_terms.append('%s as "%s" ' % (gb['qualified_field'], gb['groupby']))

        self._flush_search(domain, fields=fnames + groupby_fields)

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

        self._read_group_resolve_many2one_fields(fetched_data, annotated_groupbys)

        data = [{k: self._read_group_prepare_data(k, v, groupby_dict) for k, v in r.items()} for r in fetched_data]

        if self.env.context.get('fill_temporal') and data:
            data = self._read_group_fill_temporal(data, groupby, aggregated_fields,
                                                  annotated_groupbys)

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

    def _read_group_resolve_many2one_fields(self, data, fields):
        many2onefields = {field['field'] for field in fields if field['type'] == 'many2one'}
        for field in many2onefields:
            ids_set = {d[field] for d in data if d[field]}
            m2o_records = self.env[self._fields[field].comodel_name].browse(ids_set)
            data_dict = dict(lazy_name_get(m2o_records.sudo()))
            for d in data:
                d[field] = (d[field], data_dict[d[field]]) if d[field] else False

    def _inherits_join_add(self, current_model, parent_model_name, query):
        """
        Add missing table SELECT and JOIN clause to ``query`` for reaching the parent table (no duplicates)
        :param current_model: current model object
        :param parent_model_name: name of the parent model for which the clauses should be added
        :param query: query object on which the JOIN should be added
        """
        inherits_field = current_model._inherits[parent_model_name]
        parent_model = self.env[parent_model_name]
        parent_alias = query.left_join(
            current_model._table, inherits_field, parent_model._table, 'id', inherits_field,
        )
        return parent_alias

    @api.model
    def _inherits_join_calc(self, alias, fname, query):
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
            parent_alias = query.left_join(
                alias, parent_fname, parent_model._table, 'id', parent_fname,
            )
            model, alias, field = parent_model, parent_alias, field.related_field
        # handle the case where the field is translated
        if field.translate is True:
            return model._generate_translated_field(alias, fname, query)
        else:
            return '"%s"."%s"' % (alias, fname)

    def _parent_store_compute(self):
        """ Compute parent_path field from scratch. """
        if not self._parent_store:
            return

        # Each record is associated to a string 'parent_path', that represents
        # the path from the record's root node to the record. The path is made
        # of the node ids suffixed with a slash (see example below). The nodes
        # in the subtree of record are the ones where 'parent_path' starts with
        # the 'parent_path' of record.
        #
        #               a                 node | id | parent_path
        #              / \                  a  | 42 | 42/
        #            ...  b                 b  | 63 | 42/63/
        #                / \                c  | 84 | 42/63/84/
        #               c   d               d  | 85 | 42/63/85/
        #
        # Note: the final '/' is necessary to match subtrees correctly: '42/63'
        # is a prefix of '42/630', but '42/63/' is not a prefix of '42/630/'.
        _logger.info('Computing parent_path for table %s...', self._table)
        query = """
            WITH RECURSIVE __parent_store_compute(id, parent_path) AS (
                SELECT row.id, concat(row.id, '/')
                FROM {table} row
                WHERE row.{parent} IS NULL
            UNION
                SELECT row.id, concat(comp.parent_path, row.id, '/')
                FROM {table} row, __parent_store_compute comp
                WHERE row.{parent} = comp.id
            )
            UPDATE {table} row SET parent_path = comp.parent_path
            FROM __parent_store_compute comp
            WHERE row.id = comp.id
        """.format(table=self._table, parent=self._parent_name)
        self.env.cr.execute(query)
        self.invalidate_cache(['parent_path'])
        return True

    def _check_removed_columns(self, log=False):
        # iterate on the database columns to drop the NOT NULL constraints of
        # fields which were required but have been removed (or will be added by
        # another module)
        cr = self._cr
        cols = [name for name, field in self._fields.items()
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
                tools.drop_not_null(cr, self._table, row['attname'])

    def _init_column(self, column_name):
        """ Initialize the value of the given column for existing rows. """
        # get the default value; ideally, we should use default_get(), but it
        # fails due to ir.default not being ready
        field = self._fields[column_name]
        if field.default:
            value = field.default(self)
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

    @ormcache()
    def _table_has_rows(self):
        """ Return whether the model's table has rows. This method should only
            be used when updating the database schema (:meth:`~._auto_init`).
        """
        self.env.cr.execute('SELECT 1 FROM "%s" LIMIT 1' % self._table)
        return self.env.cr.rowcount

    def _auto_init(self):
        """ Initialize the database schema of ``self``:
            - create the corresponding table,
            - create/update the necessary columns/tables for fields,
            - initialize new columns on existing rows,
            - add the SQL constraints given on the model,
            - add the indexes on indexed fields,

            Also prepare post-init stuff to:
            - add foreign key constraints,
            - reflect models, fields, relations and constraints,
            - mark fields to recompute on existing records.

            Note: you should not override this method. Instead, you can modify
            the model's database schema by overriding method :meth:`~.init`,
            which is called right after this one.
        """
        raise_on_invalid_object_name(self._name)

        # This prevents anything called by this method (in particular default
        # values) from prefetching a field for which the corresponding column
        # has not been added in database yet!
        self = self.with_context(prefetch_fields=False)

        cr = self._cr
        update_custom_fields = self._context.get('update_custom_fields', False)
        must_create_table = not tools.table_exists(cr, self._table)
        parent_path_compute = False

        if self._auto:
            if must_create_table:
                def make_type(field):
                    return field.column_type[1] + (" NOT NULL" if field.required else "")

                tools.create_model_table(cr, self._table, self._description, [
                    (name, make_type(field), field.string)
                    for name, field in self._fields.items()
                    if name != 'id' and field.store and field.column_type
                ])

            if self._parent_store:
                if not tools.column_exists(cr, self._table, 'parent_path'):
                    self._create_parent_columns()
                    parent_path_compute = True

            if not must_create_table:
                self._check_removed_columns(log=False)

            # update the database schema for fields
            columns = tools.table_columns(cr, self._table)
            fields_to_compute = []

            for field in self._fields.values():
                if not field.store:
                    continue
                if field.manual and not update_custom_fields:
                    continue            # don't update custom fields
                new = field.update_db(self, columns)
                if new and field.compute:
                    fields_to_compute.append(field.name)

            if fields_to_compute:
                @self.pool.post_init
                def mark_fields_to_compute():
                    recs = self.with_context(active_test=False).search([], order='id')
                    if not recs:
                        return
                    for field in fields_to_compute:
                        _logger.info("Storing computed values of %s.%s", recs._name, field)
                        self.env.add_to_compute(recs._fields[field], recs)

        if self._auto:
            self._add_sql_constraints()

        if must_create_table:
            self._execute_sql()

        if parent_path_compute:
            self._parent_store_compute()

    def init(self):
        """ This method is called after :meth:`~._auto_init`, and may be
            overridden to create or modify a model's database schema.
        """
        pass

    def _create_parent_columns(self):
        tools.create_column(self._cr, self._table, 'parent_path', 'VARCHAR')
        if 'parent_path' not in self._fields:
            _logger.error("add a field parent_path on model %s: parent_path = fields.Char(index=True)", self._name)
        elif not self._fields['parent_path'].index:
            _logger.error('parent_path field on model %s must be indexed! Add index=True to the field definition)', self._name)

    def _add_sql_constraints(self):
        """

        Modify this model's database table constraints so they match the one in
        _sql_constraints.

        """
        cr = self._cr
        foreign_key_re = re.compile(r'\s*foreign\s+key\b.*', re.I)

        for (key, definition, message) in self._sql_constraints:
            conname = '%s_%s' % (self._table, key)
            current_definition = tools.constraint_definition(cr, self._table, conname)
            if current_definition == definition:
                continue

            if current_definition:
                # constraint exists but its definition may have changed
                tools.drop_constraint(cr, self._table, conname)

            if foreign_key_re.match(definition):
                self.pool.post_init(tools.add_constraint, cr, self._table, conname, definition)
            else:
                self.pool.post_constraint(tools.add_constraint, cr, self._table, conname, definition)

    def _execute_sql(self):
        """ Execute the SQL code from the _sql attribute (if any)."""
        if hasattr(self, "_sql"):
            self._cr.execute(self._sql)

    #
    # Update objects that uses this one to update their _inherits fields
    #

    @api.model
    def _add_inherited_fields(self):
        """ Determine inherited fields. """
        if not self._inherits:
            return

        # determine which fields can be inherited
        to_inherit = {
            name: (parent_fname, field)
            for parent_model_name, parent_fname in self._inherits.items()
            for name, field in self.env[parent_model_name]._fields.items()
        }

        # add inherited fields that are not redefined locally
        for name, (parent_fname, field) in to_inherit.items():
            if name not in self._fields:
                # inherited fields are implemented as related fields, with the
                # following specific properties:
                #  - reading inherited fields should not bypass access rights
                #  - copy inherited fields iff their original field is copied
                self._add_field(name, field.new(
                    inherited=True,
                    inherited_field=field,
                    related=(parent_fname, name),
                    related_sudo=False,
                    copy=field.copy,
                    readonly=field.readonly,
                ))

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
            field.delegate = True

        # reflect fields with delegate=True in dictionary self._inherits
        for field in self._fields.values():
            if field.type == 'many2one' and not field.related and field.delegate:
                if not field.required:
                    _logger.warning("Field %s with delegate=True must be required.", field)
                    field.required = True
                if field.ondelete.lower() not in ('cascade', 'restrict'):
                    field.ondelete = 'cascade'
                self._inherits[field.comodel_name] = field.name
                self.pool[field.comodel_name]._inherits_children.add(self._name)

    @api.model
    def _prepare_setup(self):
        """ Prepare the setup of the model. """
        cls = type(self)
        cls._setup_done = False

        # the classes that define this model's base fields and methods
        cls._model_classes = tuple(c for c in cls.mro() if getattr(c, 'pool', None) is None)

        # reset those attributes on the model's class for _setup_fields() below
        for attr in ('_rec_name', '_active_name'):
            try:
                delattr(cls, attr)
            except AttributeError:
                pass

    @api.model
    def _setup_base(self):
        """ Determine the inherited and custom fields of the model. """
        cls = type(self)
        if cls._setup_done:
            return

        # 1. determine the proper fields of the model: the fields defined on the
        # class and magic fields, not the inherited or custom ones
        cls0 = cls.pool.model_cache.get(cls._model_classes)

        if cls0 and cls0._model_classes == cls._model_classes:
            # cls0 is either a model class from another registry, or cls itself.
            # The point is that it has the same base classes. We retrieve stuff
            # from cls0 to optimize the setup of cls. cls0 is guaranteed to be
            # properly set up: registries are loaded under a global lock,
            # therefore two registries are never set up at the same time.

            # remove fields that are not proper to cls
            for name in set(cls._fields).difference(cls0._model_fields):
                delattr(cls, name)
                del cls._fields[name]

            if cls0 is cls:
                # simply reset up fields
                for name, field in cls._fields.items():
                    field.setup_base(self, name)
            else:
                # collect proper fields on cls0, and add them on cls
                for name in cls0._model_fields:
                    field = cls0._fields[name]
                    # regular fields are shared, while related fields are setup from scratch
                    if not field.related:
                        self._add_field(name, field)
                    else:
                        self._add_field(name, field.new(**field.args))
                cls._model_fields = list(cls._fields)

        else:
            # retrieve fields from parent classes, and duplicate them on cls to
            # avoid clashes with inheritance between different models
            for name in cls._fields:
                delattr(cls, name)
            cls._fields = OrderedDict()
            for name, field in sorted(getmembers(cls, Field.__instancecheck__), key=lambda f: f[1]._sequence):
                # do not retrieve magic, custom and inherited fields
                if not any(field.args.get(k) for k in ('automatic', 'manual', 'inherited')):
                    self._add_field(name, field.new())
            self._add_magic_fields()
            cls._model_fields = list(cls._fields)

        cls.pool.model_cache[cls._model_classes] = cls

        # 2. add manual fields
        if self.pool._init_modules:
            self.env['ir.model.fields']._add_manual_fields(self)

        # 3. make sure that parent models determine their own fields, then add
        # inherited fields to cls
        self._inherits_check()
        for parent in self._inherits:
            self.env[parent]._setup_base()
        self._add_inherited_fields()

        # 4. initialize more field metadata
        cls._field_inverses = Collector()   # inverse fields for related fields

        cls._setup_done = True

        # 5. determine and validate rec_name
        if cls._rec_name:
            assert cls._rec_name in cls._fields, \
                "Invalid _rec_name=%r for model %r" % (cls._rec_name, cls._name)
        elif 'name' in cls._fields:
            cls._rec_name = 'name'
        elif cls._custom and 'x_name' in cls._fields:
            cls._rec_name = 'x_name'

        # 6. determine and validate active_name
        if cls._active_name:
            assert (cls._active_name in cls._fields
                    and cls._active_name in ('active', 'x_active')), \
                ("Invalid _active_name=%r for model %r; only 'active' and "
                "'x_active' are supported and the field must be present on "
                "the model") % (cls._active_name, cls._name)
        elif 'active' in cls._fields:
            cls._active_name = 'active'
        elif 'x_active' in cls._fields:
            cls._active_name = 'x_active'

    @api.model
    def _setup_fields(self):
        """ Setup the fields, except for recomputation triggers. """
        cls = type(self)

        # set up fields
        bad_fields = []
        for name, field in cls._fields.items():
            try:
                field.setup_full(self)
            except Exception:
                if field.base_field.manual:
                    # Something goes wrong when setup a manual field.
                    # This can happen with related fields using another manual many2one field
                    # that hasn't been loaded because the comodel does not exist yet.
                    # This can also be a manual function field depending on not loaded fields yet.
                    bad_fields.append(name)
                    continue
                raise

        for name in bad_fields:
            self._pop_field(name)

    @api.model
    def _setup_complete(self):
        """ Setup recomputation triggers, and complete the model setup. """
        cls = type(self)

        # register constraints and onchange methods
        cls._init_constraints_onchanges()

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """ fields_get([fields][, attributes])

        Return the definition of each field.

        The returned value is a dictionary (indexed by field name) of
        dictionaries. The _inherits'd fields are included. The string, help,
        and selection (if present) attributes are translated.

        :param allfields: list of fields to document, all if empty or not provided
        :param attributes: list of description attributes to return for each field, all if empty or not provided
        """
        has_access = functools.partial(self.check_access_rights, raise_exception=False)
        readonly = not (has_access('write') or has_access('create'))

        res = {}
        for fname, field in self._fields.items():
            if allfields and fname not in allfields:
                continue
            if field.groups and not self.env.su and not self.user_has_groups(field.groups):
                continue

            description = field.get_description(self.env)
            if readonly:
                description['readonly'] = True
                description['states'] = {}
            if attributes:
                description = {key: val
                               for key, val in description.items()
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
        if self.env.su:
            return fields or list(self._fields)

        def valid(fname):
            """ determine whether user has access to field ``fname`` """
            field = self._fields.get(fname)
            if field and field.groups:
                return self.user_has_groups(field.groups)
            else:
                return True

        if not fields:
            fields = [name for name in self._fields if valid(name)]
        else:
            invalid_fields = {name for name in fields if not valid(name)}
            if invalid_fields:
                _logger.info('Access Denied by ACLs for operation: %s, uid: %s, model: %s, fields: %s',
                             operation, self._uid, self._name, ', '.join(invalid_fields))

                description = self.env['ir.model']._get(self._name).name
                if not self.env.user.has_group('base.group_no_one'):
                    raise AccessError(
                        _('You do not have enough rights to access the fields "%(fields)s" on %(document_kind)s (%(document_model)s). '\
                          'Please contact your system administrator.\n\n(Operation: %(operation)s)') % {
                        'fields': ','.join(list(invalid_fields)),
                        'document_kind': description,
                        'document_model': self._name,
                        'operation': operation,
                    })

                def format_groups(field):
                    if field.groups == '.':
                        return _("always forbidden")

                    anyof = self.env['res.groups']
                    noneof = self.env['res.groups']
                    for g in field.groups.split(','):
                        if g.startswith('!'):
                            noneof |= self.env.ref(g[1:])
                        else:
                            anyof |= self.env.ref(g)
                    strs = []
                    if anyof:
                        strs.append(_("allowed for groups %s") % ', '.join(
                            anyof.sorted(lambda g: g.id)
                                 .mapped(lambda g: repr(g.display_name))
                        ))
                    if noneof:
                        strs.append(_("forbidden for groups %s") % ', '.join(
                            noneof.sorted(lambda g: g.id)
                                  .mapped(lambda g: repr(g.display_name))
                        ))
                    return '; '.join(strs)

                raise AccessError(_("""The requested operation can not be completed due to security restrictions.

Document type: %(document_kind)s (%(document_model)s)
Operation: %(operation)s
User: %(user)s
Fields:
%(fields_list)s""") % {
                    'document_model': self._name,
                    'document_kind': description or self._name,
                    'operation': operation,
                    'user': self._uid,
                    'fields_list': '\n'.join(
                        '- %s (%s)' % (f, format_groups(self._fields[f]))
                        for f in sorted(invalid_fields)
                    )
                })

        return fields

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
        fields = self.check_field_access_rights('read', fields)

        # fetch stored fields from the database to the cache
        stored_fields = set()
        for name in fields:
            field = self._fields.get(name)
            if not field:
                raise ValueError("Invalid field %r on model %r" % (name, self._name))
            if field.store:
                stored_fields.add(name)
            elif field.compute:
                # optimization: prefetch direct field dependencies
                for dotname in field.depends:
                    f = self._fields[dotname.split('.')[0]]
                    if f.prefetch and (not f.groups or self.user_has_groups(f.groups)):
                        stored_fields.add(f.name)
        self._read(stored_fields)

        return self._read_format(fnames=fields, load=load)

    def _read_format(self, fnames, load='_classic_read'):
        """Returns a list of dictionaries mapping field names to their values,
        with one dictionary per record that exists.

        The output format is similar to the one expected from the `read` method.

        The current method is different from `read` because it retrieves its
        values from the cache without doing a query when it is avoidable.
        """
        data = [(record, {'id': record._ids[0]}) for record in self]
        use_name_get = (load == '_classic_read')
        for name in fnames:
            convert = self._fields[name].convert_to_read
            for record, vals in data:
                # missing records have their vals empty
                if not vals:
                    continue
                try:
                    vals[name] = convert(record[name], record, use_name_get)
                except MissingError:
                    vals.clear()
        result = [vals for record, vals in data if vals]

        return result

    def _fetch_field(self, field):
        """ Read from the database in order to fetch ``field`` (:class:`Field`
            instance) for ``self`` in cache.
        """
        self.check_field_access_rights('read', [field.name])
        # determine which fields can be prefetched
        if self._context.get('prefetch_fields', True) and field.prefetch:
            fnames = [
                name
                for name, f in self._fields.items()
                # select fields that can be prefetched
                if f.prefetch
                # discard fields with groups that the user may not access
                if not (f.groups and not self.user_has_groups(f.groups))
                # discard fields that must be recomputed
                if not (f.compute and self.env.records_to_compute(f))
            ]
            if field.name not in fnames:
                fnames.append(field.name)
                self = self - self.env.records_to_compute(field)
        else:
            fnames = [field.name]
        self._read(fnames)

    def _read(self, fields):
        """ Read the given fields of the records in ``self`` from the database,
            and store them in cache. Access errors are also stored in cache.
            Skip fields that are not stored.

            :param field_names: list of column names of model ``self``; all those
                fields are guaranteed to be read
            :param inherited_field_names: list of column names from parent
                models; some of those fields may not be read
        """
        if not self:
            return
        self.check_access_rights('read')

        # if a read() follows a write(), we must flush updates, as read() will
        # fetch from database and overwrites the cache (`test_update_with_id`)
        self.flush(fields, self)

        field_names = []
        inherited_field_names = []
        for name in fields:
            field = self._fields.get(name)
            if field:
                if field.store:
                    field_names.append(name)
                elif field.base_field.store:
                    inherited_field_names.append(name)
            else:
                _logger.warning("%s.read() with unknown field '%s'", self._name, name)

        # determine the fields that are stored as columns in tables; ignore 'id'
        fields_pre = [
            field
            for field in (self._fields[name] for name in field_names + inherited_field_names)
            if field.name != 'id'
            if field.base_field.store and field.base_field.column_type
            if not (field.inherited and callable(field.base_field.translate))
        ]

        if fields_pre:
            env = self.env
            cr, user, context, su = env.args

            # make a query object for selecting ids, and apply security rules to it
            query = Query(self.env.cr, self._table, self._table_query)
            self._apply_ir_rules(query, 'read')

            # the query may involve several tables: we need fully-qualified names
            def qualify(field):
                col = field.name
                res = self._inherits_join_calc(self._table, field.name, query)
                if field.type == 'binary' and (context.get('bin_size') or context.get('bin_size_' + col)):
                    # PG 9.2 introduces conflicting pg_size_pretty(numeric) -> need ::cast
                    res = 'pg_size_pretty(length(%s)::bigint)' % res
                return '%s as "%s"' % (res, col)

            # selected fields are: 'id' followed by fields_pre
            qual_names = [qualify(name) for name in [self._fields['id']] + fields_pre]

            # determine the actual query to execute (last parameter is added below)
            query.add_where('"%s".id IN %%s' % self._table)
            query_str, params = query.select(*qual_names)

            result = []
            for sub_ids in cr.split_for_in_conditions(self.ids):
                cr.execute(query_str, params + [sub_ids])
                result += cr.fetchall()
        else:
            self.check_access_rule('read')
            result = [(id_,) for id_ in self.ids]

        fetched = self.browse()
        if result:
            cols = zip(*result)
            ids = next(cols)
            fetched = self.browse(ids)

            for field in fields_pre:
                values = next(cols)
                if context.get('lang') and not field.inherited and callable(field.translate):
                    translate = field.get_trans_func(fetched)
                    values = list(values)
                    for index in range(len(ids)):
                        values[index] = translate(ids[index], values[index])

                # store values in cache
                self.env.cache.update(fetched, field, values)

            # determine the fields that must be processed now;
            # for the sake of simplicity, we ignore inherited fields
            for name in field_names:
                field = self._fields[name]
                if not field.column_type:
                    field.read(fetched)
                if field.deprecated:
                    _logger.warning('Field %s is deprecated: %s', field, field.deprecated)

        # possibly raise exception for the records that could not be read
        missing = self - fetched
        if missing:
            extras = fetched - self
            if extras:
                raise AccessError(
                    _("Database fetch misses ids ({}) and has extra ids ({}), may be caused by a type incoherence in a previous request").format(
                        missing._ids, extras._ids,
                    ))
            # mark non-existing records in missing
            forbidden = missing.exists()
            if forbidden:
                raise self.env['ir.rule']._make_access_error('read', forbidden)

    def get_metadata(self):
        """Return some metadata about the given records.

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

        IrModelData = self.env['ir.model.data'].sudo()
        if self._log_access:
            res = self.read(LOG_ACCESS_COLUMNS)
        else:
            res = [{'id': x} for x in self.ids]
        xml_data = dict((x['res_id'], x) for x in IrModelData.search_read([('model', '=', self._name),
                                                                           ('res_id', 'in', self.ids)],
                                                                          ['res_id', 'noupdate', 'module', 'name'],
                                                                          order='id DESC'))
        for r in res:
            value = xml_data.get(r['id'], {})
            r['xmlid'] = '%(module)s.%(name)s' % value if value else False
            r['noupdate'] = value.get('noupdate', False)
        return res

    def get_base_url(self):
        """
        Returns rooturl for a specific given record.

        By default, it return the ir.config.parameter of base_url
        but it can be overidden by model.

        :return: the base url for this record
        :rtype: string

        """
        self.ensure_one()
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url')

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

    def _check_company(self, fnames=None):
        """ Check the companies of the values of the given field names.

        :param list fnames: names of relational fields to check
        :raises UserError: if the `company_id` of the value of any field is not
            in `[False, self.company_id]` (or `self` if
            :class:`~odoo.addons.base.models.res_company`).

        For :class:`~odoo.addons.base.models.res_users` relational fields,
        verifies record company is in `company_ids` fields.

        User with main company A, having access to company A and B, could be
        assigned or linked to records in company B.
        """
        if fnames is None:
            fnames = self._fields

        regular_fields = []
        property_fields = []
        for name in fnames:
            field = self._fields[name]
            if field.relational and field.check_company and \
                    'company_id' in self.env[field.comodel_name]:
                if not field.company_dependent:
                    regular_fields.append(name)
                else:
                    property_fields.append(name)

        if not (regular_fields or property_fields):
            return

        inconsistencies = []
        for record in self:
            company = record.company_id if record._name != 'res.company' else record
            # The first part of the check verifies that all records linked via relation fields are compatible
            # with the company of the origin document, i.e. `self.account_id.company_id == self.company_id`
            for name in regular_fields:
                corecord = record.sudo()[name]
                # Special case with `res.users` since an user can belong to multiple companies.
                if corecord._name == 'res.users' and corecord.company_ids:
                    if not (company <= corecord.company_ids):
                        inconsistencies.append((record, name, corecord))
                elif not (corecord.company_id <= company):
                    inconsistencies.append((record, name, corecord))
            # The second part of the check (for property / company-dependent fields) verifies that the records
            # linked via those relation fields are compatible with the company that owns the property value, i.e.
            # the company for which the value is being assigned, i.e:
            #      `self.property_account_payable_id.company_id == self.env.company
            company = self.env.company
            for name in property_fields:
                # Special case with `res.users` since an user can belong to multiple companies.
                corecord = record.sudo()[name]
                if corecord._name == 'res.users' and corecord.company_ids:
                    if not (company <= corecord.company_ids):
                        inconsistencies.append((record, name, corecord))
                elif not (corecord.company_id <= company):
                    inconsistencies.append((record, name, corecord))

        if inconsistencies:
            lines = [_("Incompatible companies on records:")]
            company_msg = _("- Record is company %(company)r and %(field)r (%(fname)s: %(values)s) belongs to another company.")
            record_msg = _("- %(record)r belongs to company %(company)r and %(field)r (%(fname)s: %(values)s) belongs to another company.")
            for record, name, corecords in inconsistencies[:5]:
                if record._name == 'res.company':
                    msg, company = company_msg, record
                else:
                    msg, company = record_msg, record.company_id
                field = self.env['ir.model.fields']._get(self._name, name)
                lines.append(msg % {
                    'record': record.display_name,
                    'company': company.display_name,
                    'field': field.field_description,
                    'fname': field.name,
                    'values': ", ".join(repr(rec.display_name) for rec in corecords),
                })
            raise UserError("\n".join(lines))

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        """ Verifies that the operation given by ``operation`` is allowed for
            the current user according to the access rights.
        """
        return self.env['ir.model.access'].check(self._name, operation, raise_exception)

    def check_access_rule(self, operation):
        """ Verifies that the operation given by ``operation`` is allowed for
            the current user according to ir.rules.

           :param operation: one of ``write``, ``unlink``
           :raise UserError: * if current ir.rules do not permit this operation.
           :return: None if the operation is allowed
        """
        if self.env.su:
            return

        # SQL Alternative if computing in-memory is too slow for large dataset
        # invalid = self - self._filter_access_rules(operation)
        invalid = self - self._filter_access_rules_python(operation)
        if not invalid:
            return

        forbidden = invalid.exists()
        if forbidden:
            # the invalid records are (partially) hidden by access rules
            raise self.env['ir.rule']._make_access_error(operation, forbidden)

        # If we get here, the invalid records are not in the database.
        if operation in ('read', 'unlink'):
            # No need to warn about deleting an already deleted record.
            # And no error when reading a record that was deleted, to prevent spurious
            # errors for non-transactional search/read sequences coming from clients.
            return
        _logger.info('Failed operation on deleted record(s): %s, uid: %s, model: %s', operation, self._uid, self._name)
        raise MissingError(
            _('One of the documents you are trying to access has been deleted, please try again after refreshing.')
            + '\n\n({} {}, {} {}, {} {}, {} {})'.format(
                _('Document type:'), self._name, _('Operation:'), operation,
                _('Records:'), invalid.ids[:6], _('User:'), self._uid,
            )
        )

    def _filter_access_rules(self, operation):
        """ Return the subset of ``self`` for which ``operation`` is allowed. """
        if self.env.su:
            return self

        if not self._ids:
            return self

        query = Query(self.env.cr, self._table, self._table_query)
        self._apply_ir_rules(query, operation)
        if not query.where_clause:
            return self

        # detemine ids in database that satisfy ir.rules
        valid_ids = set()
        query.add_where(f'"{self._table}".id IN %s')
        query_str, params = query.select()
        self._flush_search([])
        for sub_ids in self._cr.split_for_in_conditions(self.ids):
            self._cr.execute(query_str, params + [sub_ids])
            valid_ids.update(row[0] for row in self._cr.fetchall())

        # return new ids without origin and ids with origin in valid_ids
        return self.browse([
            it
            for it in self._ids
            if not (it or it.origin) or (it or it.origin) in valid_ids
        ])

    def _filter_access_rules_python(self, operation):
        dom = self.env['ir.rule']._compute_domain(self._name, operation)
        return self.sudo().filtered_domain(dom or [])

    def unlink(self):
        """ unlink()

        Deletes the records of the current set

        :raise AccessError: * if user has no unlink rights on the requested object
                            * if user tries to bypass access rules for unlink on the requested object
        :raise UserError: if the record is default property for other records

        """
        if not self:
            return True

        self.check_access_rights('unlink')
        self._check_concurrency()

        # mark fields that depend on 'self' to recompute them after 'self' has
        # been deleted (like updating a sum of lines after deleting one line)
        self.flush()
        self.modified(self._fields, before=True)

        with self.env.norecompute():
            self.check_access_rule('unlink')

            cr = self._cr
            Data = self.env['ir.model.data'].sudo().with_context({})
            Defaults = self.env['ir.default'].sudo()
            Property = self.env['ir.property'].sudo()
            Attachment = self.env['ir.attachment'].sudo()
            ir_model_data_unlink = Data
            ir_attachment_unlink = Attachment

            # TOFIX: this avoids an infinite loop when trying to recompute a
            # field, which triggers the recomputation of another field using the
            # same compute function, which then triggers again the computation
            # of those two fields
            for field in self._fields.values():
                self.env.remove_to_compute(field, self)

            for sub_ids in cr.split_for_in_conditions(self.ids):
                # Check if the records are used as default properties.
                refs = ['%s,%s' % (self._name, i) for i in sub_ids]
                if Property.search([('res_id', '=', False), ('value_reference', 'in', refs)], limit=1):
                    raise UserError(_('Unable to delete this document because it is used as a default property'))

                # Delete the records' properties.
                Property.search([('res_id', 'in', refs)]).unlink()

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
                    ir_model_data_unlink |= data

                # For the same reason, remove the defaults having some of the
                # records as value
                Defaults.discard_records(self.browse(sub_ids))

                # For the same reason, remove the relevant records in ir_attachment
                # (the search is performed with sql as the search method of
                # ir_attachment is overridden to hide attachments of deleted
                # records)
                query = 'SELECT id FROM ir_attachment WHERE res_model=%s AND res_id IN %s'
                cr.execute(query, (self._name, sub_ids))
                attachments = Attachment.browse([row[0] for row in cr.fetchall()])
                if attachments:
                    ir_attachment_unlink |= attachments.sudo()

            # invalidate the *whole* cache, since the orm does not handle all
            # changes made in the database, like cascading delete!
            self.invalidate_cache()
            if ir_model_data_unlink:
                ir_model_data_unlink.unlink()
            if ir_attachment_unlink:
                ir_attachment_unlink.unlink()
            # DLE P93: flush after the unlink, for recompute fields depending on
            # the modified of the unlink
            self.flush()

        # auditing: deletions are infrequent and leave no trace in the database
        _unlink.info('User #%s deleted %s records with IDs: %r', self._uid, self._name, self.ids)

        return True

    def write(self, vals):
        """ write(vals)

        Updates all records in the current set with the provided values.

        :param dict vals: fields to update and the value to set on them e.g::

                {'foo': 1, 'bar': "Qux"}

            will set the field ``foo`` to ``1`` and the field ``bar`` to
            ``"Qux"`` if those are valid (otherwise it will trigger an error).

        :raise AccessError: * if user has no write rights on the requested object
                            * if user tries to bypass access rules for write on the requested object
        :raise ValidationError: if user tries to enter invalid value for a field that is not in selection
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

          ``(0, 0, values)``
              adds a new record created from the provided ``value`` dict.
          ``(1, id, values)``
              updates an existing record of id ``id`` with the values in
              ``values``. Can not be used in :meth:`~.create`.
          ``(2, id, 0)``
              removes the record of id ``id`` from the set, then deletes it
              (from the database). Can not be used in :meth:`~.create`.
          ``(3, id, 0)``
              removes the record of id ``id`` from the set, but does not
              delete it. Can not be used in
              :meth:`~.create`.
          ``(4, id, 0)``
              adds an existing record of id ``id`` to the set.
          ``(5, 0, 0)``
              removes all records from the set, equivalent to using the
              command ``3`` on every record explicitly. Can not be used in
              :meth:`~.create`.
          ``(6, 0, ids)``
              replaces all existing records in the set by the ``ids`` list,
              equivalent to using the command ``5`` followed by a command
              ``4`` for each ``id`` in ``ids``.
        """
        if not self:
            return True

        self.check_access_rights('write')
        self.check_field_access_rights('write', vals.keys())
        self.check_access_rule('write')
        env = self.env

        bad_names = {'id', 'parent_path'}
        if self._log_access:
            # the superuser can set log_access fields while loading registry
            if not(self.env.uid == SUPERUSER_ID and not self.pool.ready):
                bad_names.update(LOG_ACCESS_COLUMNS)

        determine_inverses = defaultdict(list)      # {inverse: fields}
        records_to_inverse = {}                     # {field: records}
        relational_names = []
        protected = set()
        check_company = False
        for fname in vals:
            field = self._fields.get(fname)
            if not field:
                raise ValueError("Invalid field %r on model %r" % (fname, self._name))
            if field.inverse:
                if field.type in ('one2many', 'many2many'):
                    # The written value is a list of commands that must applied
                    # on the field's current value. Because the field is
                    # protected while being written, the field's current value
                    # will not be computed and default to an empty recordset. So
                    # make sure the field's value is in cache before writing, in
                    # order to avoid an inconsistent update.
                    self[fname]
                determine_inverses[field.inverse].append(field)
                # DLE P150: `test_cancel_propagation`, `test_manufacturing_3_steps`, `test_manufacturing_flow`
                # TODO: check whether still necessary
                records_to_inverse[field] = self.filtered('id')
            if field.relational or self._field_inverses[field]:
                relational_names.append(fname)
            if field.inverse or (field.compute and not field.readonly):
                if field.store or field.type not in ('one2many', 'many2many'):
                    # Protect the field from being recomputed while being
                    # inversed. In the case of non-stored x2many fields, the
                    # field's value may contain unexpeced new records (created
                    # by command 0). Those new records are necessary for
                    # inversing the field, but should no longer appear if the
                    # field is recomputed afterwards. Not protecting the field
                    # will automatically invalidate the field from the cache,
                    # forcing its value to be recomputed once dependencies are
                    # up-to-date.
                    protected.update(self.pool.field_computed.get(field, [field]))
            if fname == 'company_id' or (field.relational and field.check_company):
                check_company = True

        # force the computation of fields that are computed with some assigned
        # fields, but are not assigned themselves
        to_compute = [field.name
                      for field in protected
                      if field.compute and field.name not in vals]
        if to_compute:
            self.recompute(to_compute, self)

        # protect fields being written against recomputation
        with env.protecting(protected, self):
            # Determine records depending on values. When modifying a relational
            # field, you have to recompute what depends on the field's values
            # before and after modification.  This is because the modification
            # has an impact on the "data path" between a computed field and its
            # dependency.  Note that this double call to modified() is only
            # necessary for relational fields.
            #
            # It is best explained with a simple example: consider two sales
            # orders SO1 and SO2.  The computed total amount on sales orders
            # indirectly depends on the many2one field 'order_id' linking lines
            # to their sales order.  Now consider the following code:
            #
            #   line = so1.line_ids[0]      # pick a line from SO1
            #   line.order_id = so2         # move the line to SO2
            #
            # In this situation, the total amount must be recomputed on *both*
            # sales order: the line's order before the modification, and the
            # line's order after the modification.
            self.modified(relational_names, before=True)

            real_recs = self.filtered('id')

            # If there are only fields that do not trigger _write (e.g. only
            # determine inverse), the below ensures that `write_date` and
            # `write_uid` are updated (`test_orm.py`, `test_write_date`)
            if self._log_access and self.ids:
                towrite = env.all.towrite[self._name]
                for record in real_recs:
                    towrite[record.id]['write_uid'] = self.env.uid
                    towrite[record.id]['write_date'] = False
                self.env.cache.invalidate([
                    (self._fields['write_date'], self.ids),
                    (self._fields['write_uid'], self.ids),
                ])

            # for monetary field, their related currency field must be cached
            # before the amount so it can be rounded correctly
            for fname in sorted(vals, key=lambda x: self._fields[x].type=='monetary'):
                if fname in bad_names:
                    continue
                field = self._fields[fname]
                field.write(self, vals[fname])

            # determine records depending on new values
            #
            # Call modified after write, because the modified can trigger a
            # search which can trigger a flush which can trigger a recompute
            # which remove the field from the recompute list while all the
            # values required for the computation could not be yet in cache.
            # e.g. Write on `name` of `res.partner` trigger the recompute of
            # `display_name`, which triggers a search on child_ids to find the
            # childs to which the display_name must be recomputed, which
            # triggers the flush of `display_name` because the _order of
            # res.partner includes display_name. The computation of display_name
            # is then done too soon because the parent_id was not yet written.
            # (`test_01_website_reset_password_tour`)
            self.modified(vals)

            if self._parent_store and self._parent_name in vals:
                self.flush([self._parent_name])

            # validate non-inversed fields first
            inverse_fields = [f.name for fs in determine_inverses.values() for f in fs]
            real_recs._validate_fields(vals, inverse_fields)

            for fields in determine_inverses.values():
                # write again on non-stored fields that have been invalidated from cache
                for field in fields:
                    if not field.store and any(self.env.cache.get_missing_ids(real_recs, field)):
                        field.write(real_recs, vals[field.name])

                # inverse records that are not being computed
                try:
                    fields[0].determine_inverse(real_recs)
                except AccessError as e:
                    if fields[0].inherited:
                        description = self.env['ir.model']._get(self._name).name
                        raise AccessError(
                            _("%(previous_message)s\n\nImplicitly accessed through '%(document_kind)s' (%(document_model)s).") % {
                                'previous_message': e.args[0],
                                'document_kind': description,
                                'document_model': self._name,
                            }
                        )
                    raise

            # validate inversed fields
            real_recs._validate_fields(inverse_fields)

        if check_company and self._check_company_auto:
            self._check_company()
        return True

    def _write(self, vals):
        # low-level implementation of write()
        if not self:
            return True

        self._check_concurrency()
        cr = self._cr

        # determine records that require updating parent_path
        parent_records = self._parent_store_update_prepare(vals)

        # determine SQL values
        columns = []                    # list of (column_name, format, value)

        for name, val in sorted(vals.items()):
            if self._log_access and name in LOG_ACCESS_COLUMNS and not val:
                continue
            field = self._fields[name]
            assert field.store

            if field.deprecated:
                _logger.warning('Field %s is deprecated: %s', field, field.deprecated)

            assert field.column_type
            columns.append((name, field.column_format, val))

        if self._log_access:
            if not vals.get('write_uid'):
                columns.append(('write_uid', '%s', self._uid))
            if not vals.get('write_date'):
                columns.append(('write_date', '%s', AsIs("(now() at time zone 'UTC')")))

        # update columns
        if columns:
            query = 'UPDATE "%s" SET %s WHERE id IN %%s' % (
                self._table, ','.join('"%s"=%s' % (column[0], column[1]) for column in columns),
            )
            params = [column[2] for column in columns]
            for sub_ids in cr.split_for_in_conditions(set(self.ids)):
                cr.execute(query, params + [sub_ids])
                if cr.rowcount != len(sub_ids):
                    raise MissingError(
                        _('One of the records you are trying to modify has already been deleted (Document type: %s).', self._description)
                        + '\n\n({} {}, {} {})'.format(_('Records:'), sub_ids[:6], _('User:'), self._uid)
                    )

        # update parent_path
        if parent_records:
            parent_records._parent_store_update()

        return True

    @api.model_create_multi
    @api.returns('self', lambda value: value.id)
    def create(self, vals_list):
        """ create(vals_list) -> records

        Creates new records for the model.

        The new records are initialized using the values from the list of dicts
        ``vals_list``, and if necessary those from :meth:`~.default_get`.

        :param list vals_list:
            values for the model's fields, as a list of dictionaries::

                [{'field_name': field_value, ...}, ...]

            For backward compatibility, ``vals_list`` may be a dictionary.
            It is treated as a singleton list ``[vals]``, and a single record
            is returned.

            see :meth:`~.write` for details

        :return: the created records
        :raise AccessError: * if user has no create rights on the requested object
                            * if user tries to bypass access rules for create on the requested object
        :raise ValidationError: if user tries to enter invalid value for a field that is not in selection
        :raise UserError: if a loop would be created in a hierarchy of objects a result of the operation (such as setting an object as its own parent)
        """
        if not vals_list:
            return self.browse()

        self = self.browse()
        self.check_access_rights('create')

        bad_names = {'id', 'parent_path'}
        if self._log_access:
            # the superuser can set log_access fields while loading registry
            if not(self.env.uid == SUPERUSER_ID and not self.pool.ready):
                bad_names.update(LOG_ACCESS_COLUMNS)

        # classify fields for each record
        data_list = []
        inversed_fields = set()

        for vals in vals_list:
            # add missing defaults
            vals = self._add_missing_default_values(vals)

            # distribute fields into sets for various purposes
            data = {}
            data['stored'] = stored = {}
            data['inversed'] = inversed = {}
            data['inherited'] = inherited = defaultdict(dict)
            data['protected'] = protected = set()
            for key, val in vals.items():
                if key in bad_names:
                    continue
                field = self._fields.get(key)
                if not field:
                    raise ValueError("Invalid field %r on model %r" % (key, self._name))
                if field.company_dependent:
                    irprop_def = self.env['ir.property']._get(key, self._name)
                    cached_def = field.convert_to_cache(irprop_def, self)
                    cached_val = field.convert_to_cache(val, self)
                    if cached_val == cached_def:
                        # val is the same as the default value defined in
                        # 'ir.property'; by design, 'ir.property' will not
                        # create entries specific to these records; skipping the
                        # field inverse saves 4 SQL queries
                        continue
                if field.store:
                    stored[key] = val
                if field.inherited:
                    inherited[field.related_field.model_name][key] = val
                elif field.inverse:
                    inversed[key] = val
                    inversed_fields.add(field)
                # protect non-readonly computed fields against (re)computation
                if field.compute and not field.readonly:
                    protected.update(self.pool.field_computed.get(field, [field]))

            data_list.append(data)

        # create or update parent records
        for model_name, parent_name in self._inherits.items():
            parent_data_list = []
            for data in data_list:
                if not data['stored'].get(parent_name):
                    parent_data_list.append(data)
                elif data['inherited'][model_name]:
                    parent = self.env[model_name].browse(data['stored'][parent_name])
                    parent.write(data['inherited'][model_name])

            if parent_data_list:
                parents = self.env[model_name].create([
                    data['inherited'][model_name]
                    for data in parent_data_list
                ])
                for parent, data in zip(parents, parent_data_list):
                    data['stored'][parent_name] = parent.id

        # create records with stored fields
        records = self._create(data_list)

        # protect fields being written against recomputation
        protected = [(data['protected'], data['record']) for data in data_list]
        with self.env.protecting(protected):
            # group fields by inverse method (to call it once), and order groups
            # by dependence (in case they depend on each other)
            field_groups = (fields for _inv, fields in groupby(inversed_fields, attrgetter('inverse')))
            for fields in field_groups:
                # determine which records to inverse for those fields
                inv_names = {field.name for field in fields}
                rec_vals = [
                    (data['record'], {
                        name: data['inversed'][name]
                        for name in inv_names
                        if name in data['inversed']
                    })
                    for data in data_list
                    if not inv_names.isdisjoint(data['inversed'])
                ]

                # If a field is not stored, its inverse method will probably
                # write on its dependencies, which will invalidate the field on
                # all records. We therefore inverse the field record by record.
                if all(field.store or field.company_dependent for field in fields):
                    batches = [rec_vals]
                else:
                    batches = [[rec_data] for rec_data in rec_vals]

                for batch in batches:
                    for record, vals in batch:
                        record._update_cache(vals)
                    batch_recs = self.concat(*(record for record, vals in batch))
                    fields[0].determine_inverse(batch_recs)

        # check Python constraints for non-stored inversed fields
        for data in data_list:
            data['record']._validate_fields(data['inversed'], data['stored'])

        if self._check_company_auto:
            records._check_company()
        return records

    @api.model
    def _create(self, data_list):
        """ Create records from the stored field values in ``data_list``. """
        assert data_list
        cr = self.env.cr
        quote = '"{}"'.format

        # insert rows
        ids = []                        # ids of created records
        other_fields = set()            # non-column fields
        translated_fields = set()       # translated fields

        # column names, formats and values (for common fields)
        columns0 = [('id', "nextval(%s)", self._sequence)]
        if self._log_access:
            columns0.append(('create_uid', "%s", self._uid))
            columns0.append(('create_date', "%s", AsIs("(now() at time zone 'UTC')")))
            columns0.append(('write_uid', "%s", self._uid))
            columns0.append(('write_date', "%s", AsIs("(now() at time zone 'UTC')")))

        for data in data_list:
            # determine column values
            stored = data['stored']
            columns = [column for column in columns0 if column[0] not in stored]
            for name, val in sorted(stored.items()):
                field = self._fields[name]
                assert field.store

                if field.column_type:
                    col_val = field.convert_to_column(val, self, stored)
                    columns.append((name, field.column_format, col_val))
                    if field.translate is True:
                        translated_fields.add(field)
                else:
                    other_fields.add(field)

            # Insert rows one by one
            # - as records don't all specify the same columns, code building batch-insert query
            #   was very complex
            # - and the gains were low, so not worth spending so much complexity
            #
            # It also seems that we have to be careful with INSERTs in batch, because they have the
            # same problem as SELECTs:
            # If we inject a lot of data in a single query, we fall into pathological perfs in
            # terms of SQL parser and the execution of the query itself.
            # In SELECT queries, we inject max 1000 ids (integers) when we can, because we know
            # that this limit is well managed by PostgreSQL.
            # In INSERT queries, we inject integers (small) and larger data (TEXT blocks for
            # example).
            # 
            # The problem then becomes: how to "estimate" the right size of the batch to have
            # good performance?
            #
            # This requires extensive testing, and it was prefered not to introduce INSERTs in
            # batch, to avoid regressions as much as possible.
            #
            # That said, we haven't closed the door completely.
            query = "INSERT INTO {} ({}) VALUES ({}) RETURNING id".format(
                quote(self._table),
                ", ".join(quote(name) for name, fmt, val in columns),
                ", ".join(fmt for name, fmt, val in columns),
            )
            params = [val for name, fmt, val in columns]
            cr.execute(query, params)
            ids.append(cr.fetchone()[0])

        # put the new records in cache, and update inverse fields, for many2one
        #
        # cachetoclear is an optimization to avoid modified()'s cost until other_fields are processed
        cachetoclear = []
        records = self.browse(ids)
        inverses_update = defaultdict(list)     # {(field, value): ids}
        for data, record in zip(data_list, records):
            data['record'] = record
            # DLE P104: test_inherit.py, test_50_search_one2many
            vals = dict({k: v for d in data['inherited'].values() for k, v in d.items()}, **data['stored'])
            set_vals = list(vals) + LOG_ACCESS_COLUMNS + [self.CONCURRENCY_CHECK_FIELD, 'id', 'parent_path']
            for field in self._fields.values():
                if field.type in ('one2many', 'many2many'):
                    self.env.cache.set(record, field, ())
                elif field.related and not field.column_type:
                    self.env.cache.set(record, field, field.convert_to_cache(None, record))
                # DLE P123: `test_adv_activity`, `test_message_assignation_inbox`, `test_message_log`, `test_create_mail_simple`, ...
                # Set `mail.message.parent_id` to False in cache so it doesn't do the useless SELECT when computing the modified of `child_ids`
                # in other words, if `parent_id` is not set, no other message `child_ids` are impacted.
                # + avoid the fetch of fields which are False. e.g. if a boolean field is not passed in vals and as no default set in the field attributes,
                # then we know it can be set to False in the cache in the case of a create.
                elif field.name not in set_vals and not field.compute:
                    self.env.cache.set(record, field, field.convert_to_cache(None, record))
            for fname, value in vals.items():
                field = self._fields[fname]
                if field.type in ('one2many', 'many2many'):
                    cachetoclear.append((record, field))
                else:
                    cache_value = field.convert_to_cache(value, record)
                    self.env.cache.set(record, field, cache_value)
                    if field.type in ('many2one', 'many2one_reference') and record._field_inverses[field]:
                        inverses_update[(field, cache_value)].append(record.id)

        for (field, value), record_ids in inverses_update.items():
            field._update_inverses(self.browse(record_ids), value)

        # update parent_path
        records._parent_store_create()

        # protect fields being written against recomputation
        protected = [(data['protected'], data['record']) for data in data_list]
        with self.env.protecting(protected):
            # mark computed fields as todo
            records.modified(self._fields, create=True)

            if other_fields:
                # discard default values from context for other fields
                others = records.with_context(clean_context(self._context))
                for field in sorted(other_fields, key=attrgetter('_sequence')):
                    field.create([
                        (other, data['stored'][field.name])
                        for other, data in zip(others, data_list)
                        if field.name in data['stored']
                    ])

                # mark fields to recompute
                records.modified([field.name for field in other_fields], create=True)

            # if value in cache has not been updated by other_fields, remove it
            for record, field in cachetoclear:
                if self.env.cache.contains(record, field) and not self.env.cache.get(record, field):
                    self.env.cache.remove(record, field)

        # check Python constraints for stored fields
        records._validate_fields(name for data in data_list for name in data['stored'])
        records.check_access_rule('create')

        # add translations
        if self.env.lang and self.env.lang != 'en_US':
            Translations = self.env['ir.translation']
            for field in translated_fields:
                tname = "%s,%s" % (field.model_name, field.name)
                for data in data_list:
                    if field.name in data['stored']:
                        record = data['record']
                        val = data['stored'][field.name]
                        Translations._set_ids(tname, 'model', self.env.lang, record.ids, val, val)

        return records

    def _compute_field_value(self, field):
        # This is for base automation, to have something to override to catch
        # the changes of values for stored compute fields.
        if isinstance(field.compute, str):
            getattr(self, field.compute)()
        else:
            field.compute(self)

        if field.store and any(self._ids):
            # check constraints of the fields that have been computed
            fnames = [f.name for f in self.pool.field_computed[field]]
            self.filtered('id')._validate_fields(fnames)

    def _parent_store_create(self):
        """ Set the parent_path field on ``self`` after its creation. """
        if not self._parent_store:
            return

        query = """
            UPDATE {0} node
            SET parent_path=concat((SELECT parent.parent_path FROM {0} parent
                                    WHERE parent.id=node.{1}), node.id, '/')
            WHERE node.id IN %s
        """.format(self._table, self._parent_name)
        self._cr.execute(query, [tuple(self.ids)])

    def _parent_store_update_prepare(self, vals):
        """ Return the records in ``self`` that must update their parent_path
            field. This must be called before updating the parent field.
        """
        if not self._parent_store or self._parent_name not in vals:
            return self.browse()

        # No need to recompute the values if the parent is the same.
        parent_val = vals[self._parent_name]
        if parent_val:
            query = """ SELECT id FROM {0}
                        WHERE id IN %s AND ({1} != %s OR {1} IS NULL) """
            params = [tuple(self.ids), parent_val]
        else:
            query = """ SELECT id FROM {0}
                        WHERE id IN %s AND {1} IS NOT NULL """
            params = [tuple(self.ids)]
        query = query.format(self._table, self._parent_name)
        self._cr.execute(query, params)
        return self.browse([row[0] for row in self._cr.fetchall()])

    def _parent_store_update(self):
        """ Update the parent_path field of ``self``. """
        cr = self.env.cr

        # determine new prefix of parent_path
        query = """
            SELECT parent.parent_path FROM {0} node, {0} parent
            WHERE node.id = %s AND parent.id = node.{1}
        """
        cr.execute(query.format(self._table, self._parent_name), [self.ids[0]])
        prefix = cr.fetchone()[0] if cr.rowcount else ''

        # check for recursion
        if prefix:
            parent_ids = {int(label) for label in prefix.split('/')[:-1]}
            if not parent_ids.isdisjoint(self._ids):
                raise UserError(_("Recursion Detected."))

        # update parent_path of all records and their descendants
        query = """
            UPDATE {0} child
            SET parent_path = concat(%s, substr(child.parent_path,
                    length(node.parent_path) - length(node.id || '/') + 1))
            FROM {0} node
            WHERE node.id IN %s
            AND child.parent_path LIKE concat(node.parent_path, '%%')
            RETURNING child.id
        """
        cr.execute(query.format(self._table), [prefix, tuple(self.ids)])
        modified_ids = {row[0] for row in cr.fetchall()}
        self.browse(modified_ids).modified(['parent_path'])

    def _load_records_write(self, values):
        self.write(values)

    def _load_records_create(self, values):
        return self.create(values)

    def _load_records(self, data_list, update=False):
        """ Create or update records of this model, and assign XMLIDs.

            :param data_list: list of dicts with keys `xml_id` (XMLID to
                assign), `noupdate` (flag on XMLID), `values` (field values)
            :param update: should be ``True`` when upgrading a module

            :return: the records corresponding to ``data_list``
        """
        original_self = self.browse()
        # records created during installation should not display messages
        self = self.with_context(install_mode=True)
        imd = self.env['ir.model.data'].sudo()

        # The algorithm below partitions 'data_list' into three sets: the ones
        # to create, the ones to update, and the others. For each set, we assign
        # data['record'] for each data. All those records are then retrieved for
        # the result.

        # determine existing xml_ids
        xml_ids = [data['xml_id'] for data in data_list if data.get('xml_id')]
        existing = {
            ("%s.%s" % row[1:3]): row
            for row in imd._lookup_xmlids(xml_ids, self)
        }

        # determine which records to create and update
        to_create = []                  # list of data
        to_update = []                  # list of data
        imd_data_list = []              # list of data for _update_xmlids()

        for data in data_list:
            xml_id = data.get('xml_id')
            if not xml_id:
                vals = data['values']
                if vals.get('id'):
                    data['record'] = self.browse(vals['id'])
                    to_update.append(data)
                elif not update:
                    to_create.append(data)
                continue
            row = existing.get(xml_id)
            if not row:
                to_create.append(data)
                continue
            d_id, d_module, d_name, d_model, d_res_id, d_noupdate, r_id = row
            record = self.browse(d_res_id)
            if r_id:
                data['record'] = record
                imd_data_list.append(data)
                if not (update and d_noupdate):
                    to_update.append(data)
            else:
                imd.browse(d_id).unlink()
                to_create.append(data)

        # update existing records
        for data in to_update:
            data['record']._load_records_write(data['values'])

        # check for records to create with an XMLID from another module
        module = self.env.context.get('install_module')
        if module:
            prefix = module + "."
            for data in to_create:
                if data.get('xml_id') and not data['xml_id'].startswith(prefix):
                    _logger.warning("Creating record %s in module %s.", data['xml_id'], module)

        # create records
        records = self._load_records_create([data['values'] for data in to_create])
        for data, record in zip(to_create, records):
            data['record'] = record
            if data.get('xml_id'):
                # add XML ids for parent records that have just been created
                for parent_model, parent_field in self._inherits.items():
                    if not data['values'].get(parent_field):
                        imd_data_list.append({
                            'xml_id': f"{data['xml_id']}_{parent_model.replace('.', '_')}",
                            'record': record[parent_field],
                            'noupdate': data.get('noupdate', False),
                        })
                imd_data_list.append(data)

        # create or update XMLIDs
        imd._update_xmlids(imd_data_list, update)

        return original_self.concat(*(data['record'] for data in data_list))

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
        # if the object has an active field ('active', 'x_active'), filter out all
        # inactive records unless they were explicitely asked for
        if self._active_name and active_test and self._context.get('active_test', True):
            # the item[0] trick below works for domain items and '&'/'|'/'!'
            # operators too
            if not any(item[0] == self._active_name for item in domain):
                domain = [(self._active_name, '=', 1)] + domain

        if domain:
            return expression.expression(domain, self).query
        else:
            return Query(self.env.cr, self._table, self._table_query)

    def _check_qorder(self, word):
        if not regex_order.match(word):
            raise UserError(_(
                'Invalid "order" specified (%s). A valid "order" specification is a comma-separated list of valid field names (optionally followed by asc/desc for the direction)',
                word,
            ))
        return True

    @api.model
    def _apply_ir_rules(self, query, mode='read'):
        """Add what's missing in ``query`` to implement all appropriate ir.rules
          (using the ``model_name``'s rules or the current model's rules if ``model_name`` is None)

           :param query: the current query object
        """
        if self.env.su:
            return

        # apply main rules on the object
        Rule = self.env['ir.rule']
        domain = Rule._compute_domain(self._name, mode)
        if domain:
            expression.expression(domain, self.sudo(), self._table, query)

        # apply ir.rules from the parents (through _inherits)
        for parent_model_name in self._inherits:
            domain = Rule._compute_domain(parent_model_name, mode)
            if domain:
                parent_model = self.env[parent_model_name]
                parent_alias = self._inherits_join_add(self, parent_model_name, query)
                expression.expression(domain, parent_model.sudo(), parent_alias, query)

    @api.model
    def _generate_translated_field(self, table_alias, field, query):
        """
        Add possibly missing JOIN with translations table to ``query`` and
        generate the expression for the translated field.

        :return: the qualified field name (or expression) to use for ``field``
        """
        if self.env.lang:
            alias = query.left_join(
                table_alias, 'id', 'ir_translation', 'res_id', field,
                extra='"{rhs}"."type" = \'model\' AND "{rhs}"."name" = %s AND "{rhs}"."lang" = %s AND "{rhs}"."value" != %s',
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
        dest_alias = query.left_join(alias, order_field, dest_model._table, 'id', order_field)
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
                raise ValueError("Invalid field %r on model %r" % (order_field, self._name))

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
                    qualifield_name = self._inherits_join_calc(alias, order_field, query)
                    if field.type == 'boolean':
                        qualifield_name = "COALESCE(%s, false)" % qualifield_name
                    order_by_elements.append("%s %s" % (qualifield_name, order_direction))
                else:
                    _logger.warning("Model %r cannot be sorted on field %r (not a column)", self._name, order_field)
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
    def _flush_search(self, domain, fields=None, order=None, seen=None):
        """ Flush all the fields appearing in `domain`, `fields` and `order`. """
        if seen is None:
            seen = set()
        elif self._name in seen:
            return
        seen.add(self._name)

        to_flush = defaultdict(set)             # {model_name: field_names}
        if fields:
            to_flush[self._name].update(fields)
        # also take into account the fields in the record rules
        domain = list(domain) + (self.env['ir.rule']._compute_domain(self._name, 'read') or [])
        for arg in domain:
            if isinstance(arg, str):
                continue
            if not isinstance(arg[0], str):
                continue
            model_name = self._name
            for fname in arg[0].split('.'):
                field = self.env[model_name]._fields.get(fname)
                if not field:
                    break
                to_flush[model_name].add(fname)
                # DLE P111: `test_message_process_email_partner_find`
                # Search on res.users with email_normalized in domain
                # must trigger the recompute and flush of res.partner.email_normalized
                if field.related_field:
                    model = self
                    # DLE P129: `test_transit_multi_companies`
                    # `self.env['stock.picking'].search([('product_id', '=', product.id)])`
                    # Should flush `stock.move.picking_ids` as `product_id` on `stock.picking` is defined as:
                    # `product_id = fields.Many2one('product.product', 'Product', related='move_lines.product_id', readonly=False)`
                    for f in field.related:
                        rfield = model._fields.get(f)
                        if rfield:
                            to_flush[model._name].add(f)
                            if rfield.type in ('many2one', 'one2many', 'many2many'):
                                model = self.env[rfield.comodel_name]
                                if rfield.type == 'one2many' and rfield.inverse_name:
                                    to_flush[rfield.comodel_name].add(rfield.inverse_name)
                if field.comodel_name:
                    model_name = field.comodel_name
            # hierarchy operators need the parent field
            if arg[1] in ('child_of', 'parent_of'):
                model = self.env[model_name]
                if model._parent_store:
                    to_flush[model_name].add(model._parent_name)

        # flush the order fields
        order_spec = order or self._order
        for order_part in order_spec.split(','):
            order_field = order_part.split()[0]
            field = self._fields.get(order_field)
            if field is not None:
                to_flush[self._name].add(order_field)
                if field.relational:
                    self.env[field.comodel_name]._flush_search([], seen=seen)

        if self._active_name:
            to_flush[self._name].add(self._active_name)

        # flush model dependencies (recursively)
        if self._depends:
            models = [self]
            while models:
                model = models.pop()
                for model_name, field_names in model._depends.items():
                    to_flush[model_name].update(field_names)
                    models.append(self.env[model_name])

        for model_name, field_names in to_flush.items():
            self.env[model_name].flush(field_names)

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
        model = self.with_user(access_rights_uid) if access_rights_uid else self
        model.check_access_rights('read')

        if expression.is_false(self, args):
            # optimization: no need to query, as no record satisfies the domain
            return 0 if count else []

        # the flush must be done before the _where_calc(), as the latter can do some selects
        self._flush_search(args, order=order)

        query = self._where_calc(args)
        self._apply_ir_rules(query, 'read')

        if count:
            # Ignore order, limit and offset when just counting, they don't make sense and could
            # hurt performance
            query_str, params = query.select("count(1)")
            self._cr.execute(query_str, params)
            res = self._cr.fetchone()
            return res[0]

        query.order = self._generate_order_by(order, query).replace('ORDER BY ', '')
        query.limit = limit
        query.offset = offset

        return query

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

        # build a black list of fields that should not be copied
        blacklist = set(MAGIC_COLUMNS + ['parent_path'])
        whitelist = set(name for name, field in self._fields.items() if not field.inherited)

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
            for name, field in model._fields.items():
                if field.deprecated:
                    blacklist.add(name)

        blacklist_given_fields(self)

        fields_to_copy = {name: field
                          for name, field in self._fields.items()
                          if field.copy and name not in default and name not in blacklist}

        for name, field in fields_to_copy.items():
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

    def copy_translations(old, new, excluded=()):
        """ Recursively copy the translations from original to new record

        :param old: the original record
        :param new: the new record (copy of the original one)
        :param excluded: a container of user-provided field names
        """
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

        for name, field in old._fields.items():
            if not field.copy:
                continue

            if field.inherited and field.related[0] in excluded:
                # inherited fields that come from a user-provided parent record
                # must not copy translations, as the parent record is not a copy
                # of the old parent record
                continue

            if field.type == 'one2many' and field.name not in excluded:
                # we must recursively copy the translations for o2m; here we
                # rely on the order of the ids to match the translations as
                # foreseen in copy_data()
                old_lines = old[name].sorted(key='id')
                new_lines = new[name].sorted(key='id')
                for (old_line, new_line) in zip(old_lines, new_lines):
                    # don't pass excluded as it is not about those lines
                    old_line.copy_translations(new_line)

            elif field.translate:
                # for translatable fields we copy their translations
                trans_name, source_id, target_id = get_trans(field, old, new)
                domain = [('name', '=', trans_name), ('res_id', '=', source_id)]
                new_val = new_wo_lang[name]
                if old.env.lang and callable(field.translate):
                    # the new value *without lang* must be the old value without lang
                    new_wo_lang[name] = old_wo_lang[name]
                vals_list = []
                for vals in Translation.search_read(domain):
                    del vals['id']
                    del vals['module']      # duplicated vals is not linked to any module
                    vals['res_id'] = target_id
                    if not callable(field.translate):
                        vals['src'] = new_wo_lang[name]
                    if vals['lang'] == old.env.lang and field.translate is True:
                        # update master record if the new_val was not changed by copy override
                        if new_val == old[name]:
                            new_wo_lang[name] = old_wo_lang[name]
                            vals['src'] = old_wo_lang[name]
                        # the value should be the new value (given by copy())
                        vals['value'] = new_val
                    vals_list.append(vals)
                Translation._upsert_translations(vals_list)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """ copy(default=None)

        Duplicate record ``self`` updating it with default values

        :param dict default: dictionary of field values to override in the
               original values of the copied record, e.g: ``{'field_name': overridden_value, ...}``
        :returns: new record

        """
        self.ensure_one()
        vals = self.with_context(active_test=False).copy_data(default)[0]
        # To avoid to create a translation in the lang of the user, copy_translation will do it
        new = self.with_context(lang=None).create(vals)
        self.with_context(from_copy_translation=True).copy_translations(new, excluded=default or ())
        return new

    @api.returns('self')
    def exists(self):
        """  exists() -> records

        Returns the subset of records in ``self`` that exist, and marks deleted
        records as such in cache. It can be used as a test on records::

            if record.exists():
                ...

        By convention, new records are returned as existing.
        """
        new_ids, ids = partition(lambda i: isinstance(i, NewId), self._ids)
        if not ids:
            return self
        query = Query(self.env.cr, self._table, self._table_query)
        query.add_where(f'"{self._table}".id IN %s', [tuple(ids)])
        query_str, params = query.select()
        self.env.cr.execute(query_str, params)
        valid_ids = set([r[0] for r in self._cr.fetchall()] + new_ids)
        return self.browse(i for i in self._ids if i in valid_ids)

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
        self.flush([parent])
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

        self.flush([field_name])

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

    def _get_external_ids(self):
        """Retrieve the External ID(s) of any database record.

        **Synopsis**: ``_get_external_ids() -> { 'id': ['module.external_id'] }``

        :return: map of ids to the list of their fully qualified External IDs
                 in the form ``module.key``, or an empty list when there's no External
                 ID for a record, e.g.::

                     { 'id': ['module.ext_id', 'module.ext_id_bis'],
                       'id2': [] }
        """
        result = {record.id: [] for record in self}
        domain = [('model', '=', self._name), ('res_id', 'in', self.ids)]
        for data in self.env['ir.model.data'].sudo().search_read(domain, ['module', 'name', 'res_id'], order='id'):
            result[data['res_id']].append('%(module)s.%(name)s' % data)
        return result

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
                for key, val in results.items()}

    # backwards compatibility
    get_xml_id = get_external_id
    _get_xml_ids = _get_external_ids

    # Transience
    @classmethod
    def is_transient(cls):
        """ Return whether the model is transient.

        See :class:`TransientModel`.

        """
        return cls._transient

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Perform a :meth:`search` followed by a :meth:`read`.

        :param domain: Search domain, see ``args`` parameter in :meth:`search`.
            Defaults to an empty domain that will match all records.
        :param fields: List of fields to read, see ``fields`` parameter in :meth:`read`.
            Defaults to all fields.
        :param int offset: Number of records to skip, see ``offset`` parameter in :meth:`search`.
            Defaults to 0.
        :param int limit: Maximum number of records to return, see ``limit`` parameter in :meth:`search`.
            Defaults to no limit.
        :param order: Columns to sort result, see ``order`` parameter in :meth:`search`.
            Defaults to no sort.
        :return: List of dictionaries containing the asked fields.
        :rtype: list(dict).
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

    def toggle_active(self):
        """ Inverse the value of the field ``(x_)active`` on the records in ``self``. """
        active_recs = self.filtered(self._active_name)
        active_recs[self._active_name] = False
        (self - active_recs)[self._active_name] = True

    def action_archive(self):
        """ Set (x_)active=False on a recordset, by calling toggle_active to
            take the corresponding actions according to the model
        """
        return self.filtered(lambda record: record[self._active_name]).toggle_active()

    def action_unarchive(self):
        """ Set (x_)active=True on a recordset, by calling toggle_active to
            take the corresponding actions according to the model
        """
        return self.filtered(lambda record: not record[self._active_name]).toggle_active()

    def _register_hook(self):
        """ stuff to do right after the registry is built """
        pass

    def _unregister_hook(self):
        """ Clean up what `~._register_hook` has done. """
        pass

    @classmethod
    def _patch_method(cls, name, method):
        """ Monkey-patch a method for all instances of this model. This replaces
            the method called ``name`` by ``method`` in the given class.
            The original method is then accessible via ``method.origin``, and it
            can be restored with :meth:`~._revert_method`.

            Example::

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
        wrapped = api.propagate(origin, method)
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
    def _browse(cls, env, ids, prefetch_ids):
        """ Create a recordset instance.

        :param env: an environment
        :param ids: a tuple of record ids
        :param prefetch_ids: a collection of record ids (for prefetching)
        """
        records = object.__new__(cls)
        records.env = env
        records._ids = ids
        records._prefetch_ids = prefetch_ids
        return records

    def browse(self, ids=None):
        """ browse([ids]) -> records

        Returns a recordset for the ids provided as parameter in the current
        environment.

        .. code-block:: python

            self.browse([7, 18, 12])
            res.partner(7, 18, 12)

        :param ids: id(s)
        :type ids: int or list(int) or None
        :return: recordset
        """
        if not ids:
            ids = ()
        elif ids.__class__ in IdType:
            ids = (ids,)
        else:
            ids = tuple(ids)
        return self._browse(self.env, ids, ids)

    #
    # Internal properties, for manipulating the instance's implementation
    #

    @property
    def ids(self):
        """ Return the list of actual record ids corresponding to ``self``. """
        return list(origin_ids(self._ids))

    # backward-compatibility with former browse records
    _cr = property(lambda self: self.env.cr)
    _uid = property(lambda self: self.env.uid)
    _context = property(lambda self: self.env.context)

    #
    # Conversion methods
    #

    def ensure_one(self):
        """Verify that the current recorset holds a single record.

        :raise odoo.exceptions.ValueError: ``len(self) != 1``
        """
        try:
            # unpack to ensure there is only one value is faster than len when true and
            # has a significant impact as this check is largely called
            _id, = self._ids
            return self
        except ValueError:
            raise ValueError("Expected singleton: %s" % self)

    def with_env(self, env):
        """Return a new version of this recordset attached to the provided environment.

        :param env:
        :type env: :class:`~odoo.api.Environment`

        .. warning::
            The new environment will not benefit from the current
            environment's data cache, so later data access may incur extra
            delays while re-fetching from the database.
            The returned recordset has the same prefetch object as ``self``.
        """
        return self._browse(env, self._ids, self._prefetch_ids)

    def sudo(self, flag=True):
        """ sudo([flag=True])

        Returns a new version of this recordset with superuser mode enabled or
        disabled, depending on `flag`. The superuser mode does not change the
        current user, and simply bypasses access rights checks.

        .. warning::

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
        if not isinstance(flag, bool):
            _logger.warning("deprecated use of sudo(user), use with_user(user) instead", stack_info=True)
            return self.with_user(flag)
        return self.with_env(self.env(su=flag))

    def with_user(self, user):
        """ with_user(user)

        Return a new version of this recordset attached to the given user, in
        non-superuser mode, unless `user` is the superuser (by convention, the
        superuser is always in superuser mode.)
        """
        if not user:
            return self
        return self.with_env(self.env(user=user, su=False))

    def with_company(self, company):
        """ with_company(company)

        Return a new version of this recordset with a modified context, such that::

            result.env.company = company
            result.env.companies = self.env.companies | company

        :param company: main company of the new environment.
        :type company: :class:`~odoo.addons.base.models.res_company` or int

        .. warning::

            When using an unauthorized company for current user,
            accessing the company(ies) on the environment may trigger
            an AccessError if not done in a sudoed environment.
        """
        if not company:
            # With company = None/False/0/[]/empty recordset: keep current environment
            return self

        company_id = int(company)
        allowed_company_ids = self.env.context.get('allowed_company_ids', [])
        if allowed_company_ids and company_id == allowed_company_ids[0]:
            return self
        # Copy the allowed_company_ids list
        # to avoid modifying the context of the current environment.
        allowed_company_ids = list(allowed_company_ids)
        if company_id in allowed_company_ids:
            allowed_company_ids.remove(company_id)
        allowed_company_ids.insert(0, company_id)

        return self.with_context(allowed_company_ids=allowed_company_ids)

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
        if (args and 'force_company' in args[0]) or 'force_company' in kwargs:
            _logger.warning(
                "Context key 'force_company' is no longer supported. "
                "Use with_company(company) instead.",
                stack_info=True,
            )
        if (args and 'company' in args[0]) or 'company' in kwargs:
            _logger.warning(
                "Context key 'company' is not recommended, because "
                "of its special meaning in @depends_context.",
                stack_info=True,
            )
        context = dict(args[0] if args else self._context, **kwargs)
        if 'allowed_company_ids' not in context and 'allowed_company_ids' in self._context:
            # Force 'allowed_company_ids' to be kept when context is overridden
            # without 'allowed_company_ids'
            context['allowed_company_ids'] = self._context['allowed_company_ids']
        return self.with_env(self.env(context=context))

    def with_prefetch(self, prefetch_ids=None):
        """ with_prefetch([prefetch_ids]) -> records

        Return a new version of this recordset that uses the given prefetch ids,
        or ``self``'s ids if not given.
        """
        if prefetch_ids is None:
            prefetch_ids = self._ids
        return self._browse(self.env, self._ids, prefetch_ids)

    def _update_cache(self, values, validate=True):
        """ Update the cache of ``self`` with ``values``.

            :param values: dict of field values, in any format.
            :param validate: whether values must be checked
        """
        def is_monetary(pair):
            return pair[0].type == 'monetary'

        self.ensure_one()
        cache = self.env.cache
        fields = self._fields
        try:
            field_values = [(fields[name], value) for name, value in values.items()]
        except KeyError as e:
            raise ValueError("Invalid field %r on model %r" % (e.args[0], self._name))

        # convert monetary fields last in order to ensure proper rounding
        for field, value in sorted(field_values, key=is_monetary):
            cache.set(self, field, field.convert_to_cache(value, self, validate))

            # set inverse fields on new records in the comodel
            if field.relational:
                inv_recs = self[field.name].filtered(lambda r: not r.id)
                if not inv_recs:
                    continue
                for invf in self._field_inverses[field]:
                    # DLE P98: `test_40_new_fields`
                    # /home/dle/src/odoo/master-nochange-fp/odoo/addons/test_new_api/tests/test_new_fields.py
                    # Be careful to not break `test_onchange_taxes_1`, `test_onchange_taxes_2`, `test_onchange_taxes_3`
                    # If you attempt to find a better solution
                    for inv_rec in inv_recs:
                        if not cache.contains(inv_rec, invf):
                            val = invf.convert_to_cache(self, inv_rec, validate=False)
                            cache.set(inv_rec, invf, val)
                        else:
                            invf._update(inv_rec, self)

    def _convert_to_record(self, values):
        """ Convert the ``values`` dictionary from the cache format to the
        record format.
        """
        return {
            name: self._fields[name].convert_to_record(value, self)
            for name, value in values.items()
        }

    def _convert_to_write(self, values):
        """ Convert the ``values`` dictionary into the format of :meth:`write`. """
        fields = self._fields
        result = {}
        for name, value in values.items():
            if name in fields:
                field = fields[name]
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
        """Apply ``func`` on all records in ``self``, and return the result as a
        list or a recordset (if ``func`` return recordsets). In the latter
        case, the order of the returned recordset is arbitrary.

        :param func: a function or a dot-separated sequence of field names
        :type func: callable or str
        :return: self if func is falsy, result of func applied to all ``self`` records.
        :rtype: list or recordset

        .. code-block:: python3

            # returns a list of summing two fields for each record in the set
            records.mapped(lambda r: r.field1 + r.field2)

        The provided function can be a string to get field values:

        .. code-block:: python3

            # returns a list of names
            records.mapped('name')

            # returns a recordset of partners
            records.mapped('partner_id')

            # returns the union of all partner banks, with duplicates removed
            records.mapped('partner_id.bank_ids')
        """
        if not func:
            return self                 # support for an empty path of fields
        if isinstance(func, str):
            recs = self
            for name in func.split('.'):
                recs = recs._fields[name].mapped(recs)
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
            if recs:
                recs = recs.mapped(lambda rec: field.convert_to_record(rec._cache.get(name, null), rec))
            else:
                recs = field.convert_to_record(null, recs)
        return recs

    def filtered(self, func):
        """Return the records in ``self`` satisfying ``func``.

        :param func: a function or a dot-separated sequence of field names
        :type func: callable or str
        :return: recordset of records satisfying func, may be empty.

        .. code-block:: python3

            # only keep records whose company is the current user's
            records.filtered(lambda r: r.company_id == user.company_id)

            # only keep records whose partner is a company
            records.filtered("partner_id.is_company")
        """
        if isinstance(func, str):
            name = func
            func = lambda rec: any(rec.mapped(name))
            # populate cache
            self.mapped(name)
        return self.browse([rec.id for rec in self if func(rec)])

    def filtered_domain(self, domain):
        if not domain: return self
        result = []
        for d in reversed(domain):
            if d == '|':
                result.append(result.pop() | result.pop())
            elif d == '!':
                result.append(self - result.pop())
            elif d == '&':
                result.append(result.pop() & result.pop())
            elif d == expression.TRUE_LEAF:
                result.append(self)
            elif d == expression.FALSE_LEAF:
                result.append(self.browse())
            else:
                (key, comparator, value) = d
                if comparator in ('child_of', 'parent_of'):
                    result.append(self.search([('id', 'in', self.ids), d]))
                    continue
                if key.endswith('.id'):
                    key = key[:-3]
                if key == 'id':
                    key = ''
                # determine the field with the final type for values
                field = None
                if key:
                    model = self.browse()
                    for fname in key.split('.'):
                        field = model._fields[fname]
                        model = model[fname]
                if comparator in ('like', 'ilike', '=like', '=ilike', 'not ilike', 'not like'):
                    value_esc = value.replace('_', '?').replace('%', '*').replace('[', '?')
                records_ids = OrderedSet()
                for rec in self:
                    data = rec.mapped(key)
                    if isinstance(data, BaseModel):
                        v = value
                        if (isinstance(value, list) or isinstance(value, tuple)) and len(value):
                            v = value[0]
                        if isinstance(v, str):
                            data = data.mapped('display_name')
                        else:
                            data = data and data.ids or [False]
                    elif field and field.type in ('date', 'datetime'):
                        # convert all date and datetime values to datetime
                        normalize = Datetime.to_datetime
                        if isinstance(value, (list, tuple)):
                            value = [normalize(v) for v in value]
                        else:
                            value = normalize(value)
                        data = [normalize(d) for d in data]
                    if comparator in ('in', 'not in'):
                        if not (isinstance(value, list) or isinstance(value, tuple)):
                            value = [value]

                    if comparator == '=':
                        ok = value in data
                    elif comparator == 'in':
                        ok = any(map(lambda x: x in data, value))
                    elif comparator == '<':
                        ok = any(map(lambda x: x is not None and x < value, data))
                    elif comparator == '>':
                        ok = any(map(lambda x: x is not None and x > value, data))
                    elif comparator == '<=':
                        ok = any(map(lambda x: x is not None and x <= value, data))
                    elif comparator == '>=':
                        ok = any(map(lambda x: x is not None and x >= value, data))
                    elif comparator in ('!=', '<>'):
                        ok = value not in data
                    elif comparator == 'not in':
                        ok = all(map(lambda x: x not in data, value))
                    elif comparator == 'not ilike':
                        data = [(x or "") for x in data]
                        ok = all(map(lambda x: value.lower() not in x.lower(), data))
                    elif comparator == 'ilike':
                        data = [(x or "").lower() for x in data]
                        ok = bool(fnmatch.filter(data, '*'+(value_esc or '').lower()+'*'))
                    elif comparator == 'not like':
                        data = [(x or "") for x in data]
                        ok = all(map(lambda x: value not in x, data))
                    elif comparator == 'like':
                        data = [(x or "") for x in data]
                        ok = bool(fnmatch.filter(data, value and '*'+value_esc+'*'))
                    elif comparator == '=?':
                        ok = (value in data) or not value
                    elif comparator in ('=like'):
                        data = [(x or "") for x in data]
                        ok = bool(fnmatch.filter(data, value_esc))
                    elif comparator in ('=ilike'):
                        data = [(x or "").lower() for x in data]
                        ok = bool(fnmatch.filter(data, value and value_esc.lower()))
                    else:
                        raise ValueError
                    if ok:
                       records_ids.add(rec.id)
                result.append(self.browse(records_ids))
        while len(result)>1:
            result.append(result.pop() & result.pop())
        return result[0]


    def sorted(self, key=None, reverse=False):
        """Return the recordset ``self`` ordered by ``key``.

        :param key: either a function of one argument that returns a
            comparison key for each record, or a field name, or ``None``, in
            which case records are ordered according the default model's order
        :type key: callable or str or None
        :param bool reverse: if ``True``, return the result in reverse order

        .. code-block:: python3

            # sort records by name
            records.sorted(key=lambda r: r.name)
        """
        if key is None:
            recs = self.search([('id', 'in', self.ids)])
            return self.browse(reversed(recs._ids)) if reverse else recs
        if isinstance(key, str):
            key = itemgetter(key)
        return self.browse(item.id for item in sorted(self, key=key, reverse=reverse))

    def update(self, values):
        """ Update the records in ``self`` with ``values``. """
        for record in self:
            for name, value in values.items():
                record[name] = value

    @api.model
    def flush(self, fnames=None, records=None):
        """ Process all the pending computations (on all models), and flush all
        the pending updates to the database.

        :param fnames (list<str>): list of field names to flush.  If given,
            limit the processing to the given fields of the current model.
        :param records (Model): if given (together with ``fnames``), limit the
            processing to the given records.
        """
        def process(model, id_vals):
            # group record ids by vals, to update in batch when possible
            updates = defaultdict(list)
            for rid, vals in id_vals.items():
                updates[frozendict(vals)].append(rid)

            for vals, ids in updates.items():
                recs = model.browse(ids)
                try:
                    recs._write(vals)
                except MissingError:
                    recs.exists()._write(vals)

        if fnames is None:
            # flush everything
            self.recompute()
            while self.env.all.towrite:
                model_name, id_vals = self.env.all.towrite.popitem()
                process(self.env[model_name], id_vals)
        else:
            # flush self's model if any of the fields must be flushed
            self.recompute(fnames, records=records)

            # check whether any of 'records' must be flushed
            if records is not None:
                fnames = set(fnames)
                towrite = self.env.all.towrite.get(self._name)
                if not towrite or all(
                    fnames.isdisjoint(towrite.get(record.id, ()))
                    for record in records
                ):
                    return

            # DLE P76: test_onchange_one2many_with_domain_on_related_field
            # ```
            # email.important = True
            # self.assertIn(email, discussion.important_emails)
            # ```
            # When a search on a field coming from a related occurs (the domain
            # on discussion.important_emails field), make sure the related field
            # is flushed
            model_fields = {}
            for fname in fnames:
                field = self._fields[fname]
                model_fields.setdefault(field.model_name, []).append(field)
                if field.related_field:
                    model_fields.setdefault(field.related_field.model_name, []).append(field.related_field)
            for model_name, fields in model_fields.items():
                if any(
                    field.name in vals
                    for vals in self.env.all.towrite.get(model_name, {}).values()
                    for field in fields
                ):
                    id_vals = self.env.all.towrite.pop(model_name)
                    process(self.env[model_name], id_vals)

            # missing for one2many fields, flush their inverse
            for fname in fnames:
                field = self._fields[fname]
                if field.type == 'one2many' and field.inverse_name:
                    self.env[field.comodel_name].flush([field.inverse_name])

    #
    # New records - represent records that do not exist in the database yet;
    # they are used to perform onchanges.
    #

    @api.model
    def new(self, values={}, origin=None, ref=None):
        """ new([values], [origin], [ref]) -> record

        Return a new record instance attached to the current environment and
        initialized with the provided ``value``. The record is *not* created
        in database, it only exists in memory.

        One can pass an ``origin`` record, which is the actual record behind the
        result. It is retrieved as ``record._origin``. Two new records with the
        same origin record are considered equal.

        One can also pass a ``ref`` value to identify the record among other new
        records. The reference is encapsulated in the ``id`` of the record.
        """
        if origin is not None:
            origin = origin.id
        record = self.browse([NewId(origin, ref)])
        record._update_cache(values, validate=False)

        return record

    @property
    def _origin(self):
        """ Return the actual records corresponding to ``self``. """
        ids = tuple(origin_ids(self._ids))
        prefetch_ids = IterableGenerator(origin_ids, self._prefetch_ids)
        return self._browse(self.env, ids, prefetch_ids)

    #
    # "Dunder" methods
    #

    def __bool__(self):
        """ Test whether ``self`` is nonempty. """
        return bool(getattr(self, '_ids', True))
    __nonzero__ = __bool__

    def __len__(self):
        """ Return the size of ``self``. """
        return len(self._ids)

    def __iter__(self):
        """ Return an iterator over ``self``. """
        if len(self._ids) > PREFETCH_MAX and self._prefetch_ids is self._ids:
            for ids in self.env.cr.split_for_in_conditions(self._ids):
                for id_ in ids:
                    yield self._browse(self.env, (id_,), ids)
        else:
            for id in self._ids:
                yield self._browse(self.env, (id,), self._prefetch_ids)

    def __contains__(self, item):
        """ Test whether ``item`` (record or field name) is an element of ``self``.
            In the first case, the test is fully equivalent to::

                any(item == record for record in self)
        """
        if isinstance(item, BaseModel) and self._name == item._name:
            return len(item) == 1 and item.id in self._ids
        elif isinstance(item, str):
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
            return NotImplemented
        return self._name == other._name and set(self._ids) == set(other._ids)

    def __lt__(self, other):
        if not isinstance(other, BaseModel) or self._name != other._name:
            return NotImplemented
        return set(self._ids) < set(other._ids)

    def __le__(self, other):
        if not isinstance(other, BaseModel) or self._name != other._name:
            return NotImplemented
        # these are much cheaper checks than a proper subset check, so
        # optimise for checking if a null or singleton are subsets of a
        # recordset
        if not self or self in other:
            return True
        return set(self._ids) <= set(other._ids)

    def __gt__(self, other):
        if not isinstance(other, BaseModel) or self._name != other._name:
            return NotImplemented
        return set(self._ids) > set(other._ids)

    def __ge__(self, other):
        if not isinstance(other, BaseModel) or self._name != other._name:
            return NotImplemented
        if not other or other in self:
            return True
        return set(self._ids) >= set(other._ids)

    def __int__(self):
        return self.id or 0

    def __repr__(self):
        return "%s%s" % (self._name, getattr(self, '_ids', ""))

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
        if isinstance(key, str):
            # important: one must call the field's getter
            return self._fields[key].__get__(self, type(self))
        elif isinstance(key, slice):
            return self.browse(self._ids[key])
        else:
            return self.browse((self._ids[key],))

    def __setitem__(self, key, value):
        """ Assign the field ``key`` to ``value`` in record ``self``. """
        # important: one must call the field's setter
        return self._fields[key].__set__(self, value)

    #
    # Cache and recomputation management
    #

    @property
    def _cache(self):
        """ Return the cache of ``self``, mapping field names to values. """
        return RecordCache(self)

    def _in_cache_without(self, field, limit=PREFETCH_MAX):
        """ Return records to prefetch that have no value in cache for ``field``
            (:class:`Field` instance), including ``self``.
            Return at most ``limit`` records.
        """
        ids = expand_ids(self.id, self._prefetch_ids)
        ids = self.env.cache.get_missing_ids(self.browse(ids), field)
        if limit:
            ids = itertools.islice(ids, limit)
        # Those records are aimed at being either fetched, or computed.  But the
        # method '_fetch_field' is not correct with new records: it considers
        # them as forbidden records, and clears their cache!  On the other hand,
        # compute methods are not invoked with a mix of real and new records for
        # the sake of code simplicity.
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
                return self.env.cache.invalidate()
            fields = list(self._fields.values())
        else:
            fields = [self._fields[n] for n in fnames]

        # invalidate fields and inverse fields, too
        spec = [(f, ids) for f in fields] + \
               [(invf, None) for f in fields for invf in self._field_inverses[f]]
        self.env.cache.invalidate(spec)

    def modified(self, fnames, create=False, before=False):
        """ Notify that fields will be or have been modified on ``self``. This
        invalidates the cache where necessary, and prepares the recomputation of
        dependent stored fields.

        :param fnames: iterable of field names modified on records ``self``
        :param create: whether called in the context of record creation
        :param before: whether called before modifying records ``self``
        """
        if not self or not fnames:
            return

        # The triggers of a field F is a tree that contains the fields that
        # depend on F, together with the fields to inverse to find out which
        # records to recompute.
        #
        # For instance, assume that G depends on F, H depends on X.F, I depends
        # on W.X.F, and J depends on Y.F. The triggers of F will be the tree:
        #
        #                              [G]
        #                            X/   \Y
        #                          [H]     [J]
        #                        W/
        #                      [I]
        #
        # This tree provides perfect support for the trigger mechanism:
        # when F is # modified on records,
        #  - mark G to recompute on records,
        #  - mark H to recompute on inverse(X, records),
        #  - mark I to recompute on inverse(W, inverse(X, records)),
        #  - mark J to recompute on inverse(Y, records).
        if len(fnames) == 1:
            tree = self.pool.field_triggers.get(self._fields[next(iter(fnames))])
        else:
            # merge dependency trees to evaluate all triggers at once
            tree = {}
            for fname in fnames:
                node = self.pool.field_triggers.get(self._fields[fname])
                if node:
                    trigger_tree_merge(tree, node)

        if tree:
            # determine what to compute (through an iterator)
            tocompute = self.sudo().with_context(active_test=False)._modified_triggers(tree, create)

            # When called after modification, one should traverse backwards
            # dependencies by taking into account all fields already known to be
            # recomputed.  In that case, we mark fieds to compute as soon as
            # possible.
            #
            # When called before modification, one should mark fields to compute
            # after having inversed all dependencies.  This is because we
            # determine what currently depends on self, and it should not be
            # recomputed before the modification!
            if before:
                tocompute = list(tocompute)

            # process what to compute
            for field, records, create in tocompute:
                records -= self.env.protected(field)
                if not records:
                    continue
                if field.compute and field.store:
                    if field.recursive:
                        recursively_marked = self.env.not_to_compute(field, records)
                    self.env.add_to_compute(field, records)
                else:
                    # Dont force the recomputation of compute fields which are
                    # not stored as this is not really necessary.
                    if field.recursive:
                        recursively_marked = records & self.env.cache.get_records(records, field)
                    self.env.cache.invalidate([(field, records._ids)])
                # recursively trigger recomputation of field's dependents
                if field.recursive:
                    recursively_marked.modified([field.name], create)

    def _modified_triggers(self, tree, create=False):
        """ Return an iterator traversing a tree of field triggers on ``self``,
        traversing backwards field dependencies along the way, and yielding
        tuple ``(field, records, created)`` to recompute.
        """
        if not self:
            return

        # first yield what to compute
        for field in tree.get(None, ()):
            yield field, self, create

        # then traverse dependencies backwards, and proceed recursively
        for key, val in tree.items():
            if key is None:
                continue
            elif create and key.type in ('many2one', 'many2one_reference'):
                # upon creation, no other record has a reference to self
                continue
            else:
                # val is another tree of dependencies
                model = self.env[key.model_name]
                for invf in model._field_inverses[key]:
                    # use an inverse of field without domain
                    if not (invf.type in ('one2many', 'many2many') and invf.domain):
                        if invf.type == 'many2one_reference':
                            rec_ids = set()
                            for rec in self:
                                try:
                                    if rec[invf.model_field] == key.model_name:
                                        rec_ids.add(rec[invf.name])
                                except MissingError:
                                    continue
                            records = model.browse(rec_ids)
                        else:
                            try:
                                records = self[invf.name]
                            except MissingError:
                                records = self.exists()[invf.name]

                        # TODO: find a better fix
                        if key.model_name == records._name:
                            if not any(self._ids):
                                # if self are new, records should be new as well
                                records = records.browse(it and NewId(it) for it in records._ids)
                            break
                else:
                    new_records = self.filtered(lambda r: not r.id)
                    real_records = self - new_records
                    records = model.browse()
                    if real_records:
                        records |= model.search([(key.name, 'in', real_records.ids)], order='id')
                    if new_records:
                        cache_records = self.env.cache.get_records(model, key)
                        records |= cache_records.filtered(lambda r: set(r[key.name]._ids) & set(self._ids))
                yield from records._modified_triggers(val)

    @api.model
    def recompute(self, fnames=None, records=None):
        """ Recompute all function fields (or the given ``fnames`` if present).
            The fields and records to recompute have been determined by method
            :meth:`modified`.
        """
        def process(field):
            recs = self.env.records_to_compute(field)
            if not recs:
                return
            if field.compute and field.store:
                # do not force recomputation on new records; those will be
                # recomputed by accessing the field on the records
                recs = recs.filtered('id')
                try:
                    field.recompute(recs)
                except MissingError:
                    existing = recs.exists()
                    field.recompute(existing)
                    # mark the field as computed on missing records, otherwise
                    # they remain forever in the todo list, and lead to an
                    # infinite loop...
                    for f in recs.pool.field_computed[field]:
                        self.env.remove_to_compute(f, recs - existing)
            else:
                self.env.cache.invalidate([(field, recs._ids)])
                self.env.remove_to_compute(field, recs)

        if fnames is None:
            # recompute everything
            for field in list(self.env.fields_to_compute()):
                process(field)
        else:
            fields = [self._fields[fname] for fname in fnames]

            # check whether any 'records' must be computed
            if records is not None and not any(
                records & self.env.records_to_compute(field)
                for field in fields
            ):
                return

            # recompute the given fields on self's model
            for field in fields:
                process(field)

    #
    # Generic onchange method
    #

    def _dependent_fields(self, field):
        """ Return an iterator on the fields that depend on ``field``. """
        def traverse(node):
            for key, val in node.items():
                if key is None:
                    yield from val
                else:
                    yield from traverse(val)
        return traverse(self.pool.field_triggers.get(field, {}))

    def _has_onchange(self, field, other_fields):
        """ Return whether ``field`` should trigger an onchange event in the
            presence of ``other_fields``.
        """
        return (field.name in self._onchange_methods) or any(
            dep in other_fields for dep in self._dependent_fields(field.base_field)
        )

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
                for subinfo in info['fields'][name].get('views', {}).values():
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
                self.update({key: val for key, val in res['value'].items() if key in self._fields})
            if res.get('domain'):
                _logger.warning(
                    "onchange method %s returned a domain, this is deprecated",
                    method.__qualname__
                )
                result.setdefault('domain', {}).update(res['domain'])
            if res.get('warning'):
                result['warnings'].add((
                    res['warning'].get('title') or _("Warning"),
                    res['warning'].get('message') or "",
                    res['warning'].get('type') or "",
                ))

        if onchange in ("1", "true"):
            for method in self._onchange_methods.get(field_name, ()):
                method_res = method(self)
                process(method_res)
            return

    def onchange(self, values, field_name, field_onchange):
        """ Perform an onchange on the given field.

            :param values: dictionary mapping field names to values, giving the
                current state of modification
            :param field_name: name of the modified field, or list of field
                names (in view order), or False
            :param field_onchange: dictionary mapping field names to their
                on_change attribute

            When ``field_name`` is falsy, the method first adds default values
            to ``values``, computes the remaining fields, applies onchange
            methods to them, and return all the fields in ``field_onchange``.
        """
        # this is for tests using `Form`
        self.flush()

        env = self.env
        if isinstance(field_name, list):
            names = field_name
        elif field_name:
            names = [field_name]
        else:
            names = []

        first_call = not names

        if any(name not in self._fields for name in names):
            return {}

        def PrefixTree(model, dotnames):
            """ Return a prefix tree for sequences of field names. """
            if not dotnames:
                return {}
            # group dotnames by prefix
            suffixes = defaultdict(list)
            for dotname in dotnames:
                # name, *names = dotname.split('.', 1)
                names = dotname.split('.', 1)
                name = names.pop(0)
                suffixes[name].extend(names)
            # fill in prefix tree in fields order
            tree = OrderedDict()
            for name, field in model._fields.items():
                if name in suffixes:
                    tree[name] = subtree = PrefixTree(model[name], suffixes[name])
                    if subtree and field.type == 'one2many':
                        subtree.pop(field.inverse_name, None)
            return tree

        class Snapshot(dict):
            """ A dict with the values of a record, following a prefix tree. """
            __slots__ = ()

            def __init__(self, record, tree, fetch=True):
                # put record in dict to include it when comparing snapshots
                super(Snapshot, self).__init__({'<record>': record, '<tree>': tree})
                if fetch:
                    for name in tree:
                        self.fetch(name)

            def fetch(self, name):
                """ Set the value of field ``name`` from the record's value. """
                record = self['<record>']
                tree = self['<tree>']
                if record._fields[name].type in ('one2many', 'many2many'):
                    # x2many fields are serialized as a list of line snapshots
                    self[name] = [Snapshot(line, tree[name]) for line in record[name]]
                else:
                    self[name] = record[name]

            def has_changed(self, name):
                """ Return whether a field on record has changed. """
                if name not in self:
                    return True
                record = self['<record>']
                subnames = self['<tree>'][name]
                if record._fields[name].type not in ('one2many', 'many2many'):
                    return self[name] != record[name]
                return (
                    len(self[name]) != len(record[name])
                    or (
                        set(line_snapshot["<record>"].id for line_snapshot in self[name])
                        != set(record[name]._ids)
                    )
                    or any(
                        line_snapshot.has_changed(subname)
                        for line_snapshot in self[name]
                        for subname in subnames
                    )
                )

            def diff(self, other, force=False):
                """ Return the values in ``self`` that differ from ``other``.
                    Requires record cache invalidation for correct output!
                """
                record = self['<record>']
                result = {}
                for name, subnames in self['<tree>'].items():
                    if name == 'id':
                        continue
                    if not force and other.get(name) == self[name]:
                        continue
                    field = record._fields[name]
                    if field.type not in ('one2many', 'many2many'):
                        result[name] = field.convert_to_onchange(self[name], record, {})
                    else:
                        # x2many fields: serialize value as commands
                        result[name] = commands = [(5,)]
                        # The purpose of the following line is to enable the prefetching.
                        # In the loop below, line._prefetch_ids actually depends on the
                        # value of record[name] in cache (see prefetch_ids on x2many
                        # fields).  But the cache has been invalidated before calling
                        # diff(), therefore evaluating line._prefetch_ids with an empty
                        # cache simply returns nothing, which discards the prefetching
                        # optimization!
                        record._cache[name] = tuple(
                            line_snapshot['<record>'].id for line_snapshot in self[name]
                        )
                        for line_snapshot in self[name]:
                            line = line_snapshot['<record>']
                            line = line._origin or line
                            if not line.id:
                                # new line: send diff from scratch
                                line_diff = line_snapshot.diff({})
                                commands.append((0, line.id.ref or 0, line_diff))
                            else:
                                # existing line: check diff from database
                                # (requires a clean record cache!)
                                line_diff = line_snapshot.diff(Snapshot(line, subnames))
                                if line_diff:
                                    # send all fields because the web client
                                    # might need them to evaluate modifiers
                                    line_diff = line_snapshot.diff({})
                                    commands.append((1, line.id, line_diff))
                                else:
                                    commands.append((4, line.id))
                return result

        nametree = PrefixTree(self.browse(), field_onchange)

        if first_call:
            names = [name for name in values if name != 'id']
            missing_names = [name for name in nametree if name not in values]
            defaults = self.default_get(missing_names)
            for name in missing_names:
                values[name] = defaults.get(name, False)
                if name in defaults:
                    names.append(name)

        # prefetch x2many lines: this speeds up the initial snapshot by avoiding
        # to compute fields on new records as much as possible, as that can be
        # costly and is not necessary at all
        for name, subnames in nametree.items():
            if subnames and values.get(name):
                # retrieve all line ids in commands
                line_ids = set()
                for cmd in values[name]:
                    if cmd[0] in (1, 4):
                        line_ids.add(cmd[1])
                    elif cmd[0] == 6:
                        line_ids.update(cmd[2])
                # prefetch stored fields on lines
                lines = self[name].browse(line_ids)
                fnames = [subname
                          for subname in subnames
                          if lines._fields[subname].base_field.store]
                lines._read(fnames)
                # copy the cache of lines to their corresponding new records;
                # this avoids computing computed stored fields on new_lines
                new_lines = lines.browse(map(NewId, line_ids))
                cache = self.env.cache
                for fname in fnames:
                    field = lines._fields[fname]
                    cache.update(new_lines, field, [
                        field.convert_to_cache(value, new_line, validate=False)
                        for value, new_line in zip(cache.get_values(lines, field), new_lines)
                    ])

        # Isolate changed values, to handle inconsistent data sent from the
        # client side: when a form view contains two one2many fields that
        # overlap, the lines that appear in both fields may be sent with
        # different data. Consider, for instance:
        #
        #   foo_ids: [line with value=1, ...]
        #   bar_ids: [line with value=1, ...]
        #
        # If value=2 is set on 'line' in 'bar_ids', the client sends
        #
        #   foo_ids: [line with value=1, ...]
        #   bar_ids: [line with value=2, ...]
        #
        # The idea is to put 'foo_ids' in cache first, so that the snapshot
        # contains value=1 for line in 'foo_ids'. The snapshot is then updated
        # with the value of `bar_ids`, which will contain value=2 on line.
        #
        # The issue also occurs with other fields. For instance, an onchange on
        # a move line has a value for the field 'move_id' that contains the
        # values of the move, among which the one2many that contains the line
        # itself, with old values!
        #
        changed_values = {name: values[name] for name in names}
        # set changed values to null in initial_values; not setting them
        # triggers default_get() on the new record when creating snapshot0
        initial_values = dict(values, **dict.fromkeys(names, False))

        # do not force delegate fields to False
        for name in self._inherits.values():
            if not initial_values.get(name, True):
                initial_values.pop(name)

        # create a new record with values
        record = self.new(initial_values, origin=self)

        # make a snapshot based on the initial values of record
        snapshot0 = Snapshot(record, nametree, fetch=(not first_call))

        # store changed values in cache; also trigger recomputations based on
        # subfields (e.g., line.a has been modified, line.b is computed stored
        # and depends on line.a, but line.b is not in the form view)
        record._update_cache(changed_values, validate=False)

        # update snapshot0 with changed values
        for name in names:
            snapshot0.fetch(name)

        # Determine which field(s) should be triggered an onchange. On the first
        # call, 'names' only contains fields with a default. If 'self' is a new
        # line in a one2many field, 'names' also contains the one2many's inverse
        # field, and that field may not be in nametree.
        todo = list(unique(itertools.chain(names, nametree))) if first_call else list(names)
        done = set()

        # mark fields to do as modified to trigger recomputations
        protected = [self._fields[name] for name in names]
        with self.env.protecting(protected, record):
            record.modified(todo)
            for name in todo:
                field = self._fields[name]
                if field.inherited:
                    # modifying an inherited field should modify the parent
                    # record accordingly; because we don't actually assign the
                    # modified field on the record, the modification on the
                    # parent record has to be done explicitly
                    parent = record[field.related[0]]
                    parent[name] = record[name]

        result = {'warnings': OrderedSet()}

        # process names in order
        while todo:
            # apply field-specific onchange methods
            for name in todo:
                if field_onchange.get(name):
                    record._onchange_eval(name, field_onchange[name], result)
                done.add(name)

            # determine which fields to process for the next pass
            todo = [
                name
                for name in nametree
                if name not in done and snapshot0.has_changed(name)
            ]

            if not env.context.get('recursive_onchanges', True):
                todo = []

        # make the snapshot with the final values of record
        snapshot1 = Snapshot(record, nametree)

        # determine values that have changed by comparing snapshots
        self.invalidate_cache()
        result['value'] = snapshot1.diff(snapshot0, force=first_call)

        # format warnings
        warnings = result.pop('warnings')
        if len(warnings) == 1:
            title, message, type = warnings.pop()
            if not type:
                type = 'dialog'
            result['warning'] = dict(title=title, message=message, type=type)
        elif len(warnings) > 1:
            # concatenate warning titles and messages
            title = _("Warnings")
            message = '\n\n'.join([warn_title + '\n\n' + warn_message for warn_title, warn_message, warn_type in warnings])
            result['warning'] = dict(title=title, message=message, type='dialog')

        return result

    def _get_placeholder_filename(self, field=None):
        """ Returns the filename of the placeholder to use,
            set on web/static/src/img by default, or the
            complete path to access it (eg: module/path/to/image.png).
        """
        return 'placeholder.png'

    def _populate_factories(self):
        """ Generates a factory for the different fields of the model.

        ``factory`` is a generator of values (dict of field values).

        Factory skeleton::

            def generator(iterator, field_name, model_name):
                for counter, values in enumerate(iterator):
                    # values.update(dict())
                    yield values

        See :mod:`odoo.tools.populate` for population tools and applications.

        :returns: list of pairs(field_name, factory) where `factory` is a generator function.
        :rtype: list(tuple(str, generator))

        .. note::

            It is the responsibility of the generator to handle the field_name correctly.
            The generator could generate values for multiple fields together. In this case,
            the field_name should be more a "field_group" (should be begin by a "_"), covering
            the different fields updated by the generator (e.g. "_address" for a generator
            updating multiple address fields).
        """
        return []

    @property
    def _populate_sizes(self):
        """ Return a dict mapping symbolic sizes (``'small'``, ``'medium'``, ``'large'``) to integers,
        giving the minimal number of records that :meth:`_populate` should create.

        The default population sizes are:

        * ``small`` : 10
        * ``medium`` : 100
        * ``large`` : 1000
        """
        return {
            'small': 10,  # minimal representative set
            'medium': 100,  # average database load
            'large': 1000, # maxi database load
        }

    @property
    def _populate_dependencies(self):
        """ Return the list of models which have to be populated before the current one.

        :rtype: list
        """
        return []

    def _populate(self, size):
        """ Create records to populate this model.

        :param str size: symbolic size for the number of records: ``'small'``, ``'medium'`` or ``'large'``
        """
        batch_size = 1000
        min_size = self._populate_sizes[size]

        record_count = 0
        create_values = []
        complete = False
        field_generators = self._populate_factories()
        if not field_generators:
            return self.browse() # maybe create an automatic generator?
            
        records_batches = []
        generator = populate.chain_factories(field_generators, self._name)
        while record_count <= min_size or not complete:
            values = next(generator)
            complete = values.pop('__complete')
            create_values.append(values)
            record_count += 1
            if len(create_values) >= batch_size:
                _logger.info('Batch: %s/%s', record_count, min_size)
                records_batches.append(self.create(create_values))
                create_values = []

        if create_values:
            records_batches.append(self.create(create_values))
        return self.concat(*records_batches)


collections.Set.register(BaseModel)
# not exactly true as BaseModel doesn't have __reversed__, index or count
collections.Sequence.register(BaseModel)

class RecordCache(MutableMapping):
    """ A mapping from field names to values, to read and update the cache of a record. """
    __slots__ = ['_record']

    def __init__(self, record):
        assert len(record) == 1, "Unexpected RecordCache(%s)" % record
        self._record = record

    def __contains__(self, name):
        """ Return whether `record` has a cached value for field ``name``. """
        field = self._record._fields[name]
        return self._record.env.cache.contains(self._record, field)

    def __getitem__(self, name):
        """ Return the cached value of field ``name`` for `record`. """
        field = self._record._fields[name]
        return self._record.env.cache.get(self._record, field)

    def __setitem__(self, name, value):
        """ Assign the cached value of field ``name`` for ``record``. """
        field = self._record._fields[name]
        self._record.env.cache.set(self._record, field, value)

    def __delitem__(self, name):
        """ Remove the cached value of field ``name`` for ``record``. """
        field = self._record._fields[name]
        self._record.env.cache.remove(self._record, field)

    def __iter__(self):
        """ Iterate over the field names with a cached value. """
        for field in self._record.env.cache.get_fields(self._record):
            yield field.name

    def __len__(self):
        """ Return the number of fields with a cached value. """
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
    persistent, and regularly vacuum-cleaned.

    A TransientModel has a simplified access rights management, all users can
    create new records, and may only access the records they created. The
    superuser has unrestricted access to all TransientModel records.
    """
    _auto = True                # automatically create database backend
    _register = False           # not visible in ORM registry, meant to be python-inherited only
    _abstract = False           # not abstract
    _transient = True           # transient

    @api.autovacuum
    def _transient_vacuum(self):
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
        if self._transient_max_hours:
            # Age-based expiration
            self._transient_clean_rows_older_than(self._transient_max_hours * 60 * 60)

        if self._transient_max_count:
            # Count-based expiration
            self._transient_clean_old_rows(self._transient_max_count)

    def _transient_clean_old_rows(self, max_count):
        # Check how many rows we have in the table
        query = 'SELECT count(*) FROM "{}"'.format(self._table)
        self._cr.execute(query)
        [count] = self._cr.fetchone()
        if count > max_count:
            self._transient_clean_rows_older_than(300)

    def _transient_clean_rows_older_than(self, seconds):
        # Never delete rows used in last 5 minutes
        seconds = max(seconds, 300)
        query = """
            SELECT id FROM "{}"
            WHERE COALESCE(write_date, create_date, (now() AT TIME ZONE 'UTC'))::timestamp
                < (now() AT TIME ZONE 'UTC') - interval %s
        """.format(self._table)
        self._cr.execute(query, ["%s seconds" % seconds])
        ids = [x[0] for x in self._cr.fetchall()]
        self.sudo().browse(ids).unlink()


def itemgetter_tuple(items):
    """ Fixes itemgetter inconsistency (useful in some cases) of not returning
    a tuple if len(items) == 1: always returns an n-tuple where n = len(items)
    """
    if len(items) == 0:
        return lambda a: ()
    if len(items) == 1:
        return lambda gettable: (gettable[items[0]],)
    return operator.itemgetter(*items)

def convert_pgerror_not_null(model, fields, info, e):
    if e.diag.table_name != model._table:
        return {'message': _(u"Missing required value for the field '%s'") % (e.diag.column_name)}

    field_name = e.diag.column_name
    field = fields[field_name]
    message = _(u"Missing required value for the field '%s' (%s)") % (field['string'], field_name)
    return {
        'message': message,
        'field': field_name,
    }

def convert_pgerror_unique(model, fields, info, e):
    # new cursor since we're probably in an error handler in a blown
    # transaction which may not have been rollbacked/cleaned yet
    with closing(model.env.registry.cursor()) as cr_tmp:
        cr_tmp.execute("""
            SELECT
                conname AS "constraint name",
                t.relname AS "table name",
                ARRAY(
                    SELECT attname FROM pg_attribute
                    WHERE attrelid = conrelid
                      AND attnum = ANY(conkey)
                ) as "columns"
            FROM pg_constraint
            JOIN pg_class t ON t.oid = conrelid
            WHERE conname = %s
        """, [e.diag.constraint_name])
        constraint, table, ufields = cr_tmp.fetchone() or (None, None, None)
    # if the unique constraint is on an expression or on an other table
    if not ufields or model._table != table:
        return {'message': tools.ustr(e)}

    # TODO: add stuff from e.diag.message_hint? provides details about the constraint & duplication values but may be localized...
    if len(ufields) == 1:
        field_name = ufields[0]
        field = fields[field_name]
        message = _(u"The value for the field '%s' already exists (this is probably '%s' in the current model).") % (field_name, field['string'])
        return {
            'message': message,
            'field': field_name,
        }
    field_strings = [fields[fname]['string'] for fname in ufields]
    message = _(u"The values for the fields '%s' already exist (they are probably '%s' in the current model).") % (', '.join(ufields), ', '.join(field_strings))
    return {
        'message': message,
        # no field, unclear which one we should pick and they could be in any order
    }

def convert_pgerror_constraint(model, fields, info, e):
    sql_constraints = dict([(('%s_%s') % (e.diag.table_name, x[0]), x) for x in model._sql_constraints])
    if e.diag.constraint_name in sql_constraints.keys():
        return {'message': "'%s'" % sql_constraints[e.diag.constraint_name][2]}
    return {'message': tools.ustr(e)}

PGERROR_TO_OE = defaultdict(
    # shape of mapped converters
    lambda: (lambda model, fvg, info, pgerror: {'message': tools.ustr(pgerror)}), {
    '23502': convert_pgerror_not_null,
    '23505': convert_pgerror_unique,
    '23514': convert_pgerror_constraint,
})


def lazy_name_get(self):
    """ Evaluate self.name_get() lazily. """
    names = tools.lazy(lambda: dict(self.name_get()))
    return [(rid, tools.lazy(operator.getitem, names, rid)) for rid in self.ids]


# keep those imports here to avoid dependency cycle errors
from .osv import expression
from .fields import Field, Datetime
