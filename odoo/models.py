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
import copy
import datetime
import dateutil
import fnmatch
import functools
import inspect
import itertools
import io
import logging
import operator
import pytz
import re
import uuid
import warnings
from collections import defaultdict, OrderedDict, deque
from collections.abc import MutableMapping
from contextlib import closing
from inspect import getmembers, currentframe
from operator import attrgetter, itemgetter
from typing import Dict, List

import babel
import babel.dates
import dateutil.relativedelta
import psycopg2
import psycopg2.extensions
from psycopg2.extras import Json

import odoo
from . import SUPERUSER_ID
from . import api
from . import tools
from .exceptions import AccessError, MissingError, ValidationError, UserError
from .tools import (
    clean_context, config, CountingStream, date_utils, discardattr,
    DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, frozendict,
    get_lang, LastOrderedSet, lazy_classproperty, OrderedSet, ormcache,
    partition, populate, Query, ReversedIterable, split_every, unique, SQL,
)
from .tools.lru import LRU
from .tools.translate import _, _lt

_logger = logging.getLogger(__name__)
_unlink = logging.getLogger(__name__ + '.unlink')

regex_alphanumeric = re.compile(r'^[a-z0-9_]+$')
regex_order = re.compile(r'''
    ^
    (\s*
        (?P<term>((?P<field>[a-z0-9_]+|"[a-z0-9_]+")(\.(?P<property>[a-z0-9_]+))?(:(?P<func>[a-z_]+))?))
        (\s+(?P<direction>desc|asc))?
        (\s+(?P<nulls>nulls\ first|nulls\ last))?
        \s*
        (,|$)
    )+
    (?<!,)
    $
''', re.IGNORECASE | re.VERBOSE)
regex_object_name = re.compile(r'^[a-z0-9_.]+$')
regex_pg_name = re.compile(r'^[a-z_][a-z0-9_$]*$', re.I)
regex_field_agg = re.compile(r'(\w+)(?::(\w+)(?:\((\w+)\))?)?')  # For read_group
regex_read_group_spec = re.compile(r'(\w+)(\.(\w+))?(?::(\w+))?$')  # For _read_group

AUTOINIT_RECALCULATE_STORED_FIELDS = 1000

INSERT_BATCH_SIZE = 100
SQL_DEFAULT = psycopg2.extensions.AsIs("DEFAULT")

def parse_read_group_spec(spec: str) -> tuple:
    """ Return a triplet corresponding to the given groupby/path/aggregate specification. """
    res_match = regex_read_group_spec.match(spec)
    if not res_match:
        raise ValueError(
            f'Invalid aggregate/groupby specification {spec!r}.\n'
            '- Valid aggregate specification looks like "<field_name>:<agg>" example: "quantity:sum".\n'
            '- Valid groupby specification looks like "<no_datish_field_name>" or "<datish_field_name>:<granularity>" example: "date:month" or "<properties_field_name>.<property>:<granularity>".'
        )

    groups = res_match.groups()
    return groups[0], groups[2], groups[3]

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
        raise AccessError(_('Private methods (such as %s) cannot be called remotely.', name))


def check_property_field_value_name(property_name):
    if not regex_alphanumeric.match(property_name) or len(property_name) > 512:
        raise ValueError(f"Wrong property field value name {property_name!r}.")


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


def to_company_ids(companies):
    if isinstance(companies, BaseModel):
        return companies.ids
    elif isinstance(companies, (list, tuple)):
        return companies
    return [companies]


def check_company_domain_parent_of(self, companies):
    if isinstance(companies, str):
        return ['|', ('company_id', '=', False), ('company_id', 'parent_of', [companies])]

    companies = [id for id in to_company_ids(companies) if id]
    if not companies:
        return [('company_id', '=', False)]

    return ['|', ('company_id', '=', False), ('company_id', 'in', [
        int(parent)
        for rec in self.env['res.company'].sudo().browse(companies)
        for parent in rec.parent_path.split('/')[:-1]
    ])]


class MetaModel(api.Meta):
    """ The metaclass of all model classes.
        Its main purpose is to register the models per module.
    """
    module_to_models = defaultdict(list)

    def __new__(meta, name, bases, attrs):
        # this prevents assignment of non-fields on recordsets
        attrs.setdefault('__slots__', ())
        # this collects the fields defined on the class (via Field.__set_name__())
        attrs.setdefault('_field_definitions', [])

        if attrs.get('_register', True):
            # determine '_module'
            if '_module' not in attrs:
                module = attrs['__module__']
                assert module.startswith('odoo.addons.'), \
                    f"Invalid import of {module}.{name}, it should start with 'odoo.addons'."
                attrs['_module'] = module.split('.')[2]

            # determine model '_name' and normalize '_inherits'
            inherit = attrs.get('_inherit', ())
            if isinstance(inherit, str):
                inherit = attrs['_inherit'] = [inherit]
            if '_name' not in attrs:
                attrs['_name'] = inherit[0] if len(inherit) == 1 else name

        return super().__new__(meta, name, bases, attrs)

    def __init__(self, name, bases, attrs):
        super().__init__(name, bases, attrs)

        if '__init__' in attrs and len(inspect.signature(attrs['__init__']).parameters) != 4:
            _logger.warning("The method %s.__init__ doesn't match the new signature in module %s", name, attrs.get('__module__'))
        if callable(attrs.get('_read')):
            warnings.warn(f"{self.__module__}.{self.__name__}: method BaseModel._read() has been replaced by BaseModel._fetch_query()")

        if not attrs.get('_register', True):
            return

        # Remember which models to instantiate for this module.
        if self._module:
            self.module_to_models[self._module].append(self)

        if not self._abstract and self._name not in self._inherit:
            # this class defines a model: add magic fields
            def add(name, field):
                setattr(self, name, field)
                field.__set_name__(self, name)

            def add_default(name, field):
                if name not in attrs:
                    setattr(self, name, field)
                    field.__set_name__(self, name)

            add('id', fields.Id(automatic=True))
            add_default('display_name', fields.Char(
                string='Display Name', automatic=True, compute='_compute_display_name'))

            if attrs.get('_log_access', self._auto):
                add_default('create_uid', fields.Many2one(
                    'res.users', string='Created by', automatic=True, readonly=True))
                add_default('create_date', fields.Datetime(
                    string='Created on', automatic=True, readonly=True))
                add_default('write_uid', fields.Many2one(
                    'res.users', string='Last Updated by', automatic=True, readonly=True))
                add_default('write_date', fields.Datetime(
                    string='Last Updated on', automatic=True, readonly=True))


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


class OriginIds:
    """ A reversible iterable returning the origin ids of a collection of ``ids``. """
    __slots__ = ['ids']

    def __init__(self, ids):
        self.ids = ids

    def __iter__(self):
        return origin_ids(self.ids)

    def __reversed__(self):
        return origin_ids(reversed(self.ids))


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


IdType = (int, NewId)


# maximum number of prefetched records
PREFETCH_MAX = 1000

# special columns automatically created by the ORM
LOG_ACCESS_COLUMNS = ['create_uid', 'create_date', 'write_uid', 'write_date']
MAGIC_COLUMNS = ['id'] + LOG_ACCESS_COLUMNS

# read_group stuff
READ_GROUP_TIME_GRANULARITY = {
    'hour': dateutil.relativedelta.relativedelta(hours=1),
    'day': dateutil.relativedelta.relativedelta(days=1),
    'week': datetime.timedelta(days=7),
    'month': dateutil.relativedelta.relativedelta(months=1),
    'quarter': dateutil.relativedelta.relativedelta(months=3),
    'year': dateutil.relativedelta.relativedelta(years=1)
}

# valid SQL aggregation functions
READ_GROUP_AGGREGATE = {
    'sum': lambda table, expr: SQL('SUM(%s)', expr),
    'avg': lambda table, expr: SQL('AVG(%s)', expr),
    'max': lambda table, expr: SQL('MAX(%s)', expr),
    'min': lambda table, expr: SQL('MIN(%s)', expr),
    'bool_and': lambda table, expr: SQL('BOOL_AND(%s)', expr),
    'bool_or': lambda table, expr: SQL('BOOL_OR(%s)', expr),
    'array_agg': lambda table, expr: SQL('ARRAY_AGG(%s ORDER BY %s)', expr, SQL.identifier(table, 'id')),
    # 'recordset' aggregates will be post-processed to become recordsets
    'recordset': lambda table, expr: SQL('ARRAY_AGG(%s ORDER BY %s)', expr, SQL.identifier(table, 'id')),
    'count': lambda table, expr: SQL('COUNT(%s)', expr),
    'count_distinct': lambda table, expr: SQL('COUNT(DISTINCT %s)', expr),
}

READ_GROUP_DISPLAY_FORMAT = {
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


# THE DEFINITION AND REGISTRY CLASSES
#
# The framework deals with two kinds of classes for models: the "definition"
# classes and the "registry" classes.
#
# The "definition" classes are the ones defined in modules source code: they
# define models and extend them.  Those classes are essentially "static", for
# whatever that means in Python.  The only exception is custom models: their
# definition class is created dynamically.
#
# The "registry" classes are the ones you find in the registry.  They are the
# actual classes of the recordsets of their model.  The "registry" class of a
# model is created dynamically when the registry is built.  It inherits (in the
# Python sense) from all the definition classes of the model, and possibly other
# registry classes (when the model inherits from another model).  It also
# carries model metadata inferred from its parent classes.
#
#
# THE REGISTRY CLASS OF A MODEL
#
# In the simplest case, a model's registry class inherits from all the classes
# that define the model in a flat hierarchy.  Consider the model definition
# below.  The registry class of model 'a' inherits from the definition classes
# A1, A2, A3, in reverse order, to match the expected overriding order.  The
# registry class carries inferred metadata that is shared between all the
# model's instances for a given registry.
#
#       class A1(Model):                      Model
#           _name = 'a'                       / | \
#                                            A3 A2 A1   <- definition classes
#       class A2(Model):                      \ | /
#           _inherit = 'a'                      a       <- registry class: registry['a']
#                                               |
#       class A3(Model):                     records    <- model instances, like env['a']
#           _inherit = 'a'
#
# Note that when the model inherits from another model, we actually make the
# registry classes inherit from each other, so that extensions to an inherited
# model are visible in the registry class of the child model, like in the
# following example.
#
#       class A1(Model):
#           _name = 'a'                       Model
#                                            / / \ \
#       class B1(Model):                    / /   \ \
#           _name = 'b'                    / A2   A1 \
#                                         B2  \   /  B1
#       class B2(Model):                   \   \ /   /
#           _name = 'b'                     \   a   /
#           _inherit = ['a', 'b']            \  |  /
#                                             \ | /
#       class A2(Model):                        b
#           _inherit = 'a'
#
#
# THE FIELDS OF A MODEL
#
# The fields of a model are given by the model's definition classes, inherited
# models ('_inherit' and '_inherits') and other parties, like custom fields.
# Note that a field can be partially overridden when it appears on several
# definition classes of its model.  In that case, the field's final definition
# depends on the presence or absence of each definition class, which itself
# depends on the modules loaded in the registry.
#
# By design, the registry class has access to all the fields on the model's
# definition classes.  When possible, the field is used directly from the
# model's registry class.  There are a number of cases where the field cannot be
# used directly:
#  - the field is related (and bits may not be shared);
#  - the field is overridden on definition classes;
#  - the field is defined for another model (and accessible by mixin).
#
# The last case prevents sharing the field, because the field object is specific
# to a model, and is used as a key in several key dictionaries, like the record
# cache and pending computations.
#
# Setting up a field on its definition class helps saving memory and time.
# Indeed, when sharing is possible, the field's setup is almost entirely done
# where the field was defined.  It is thus done when the definition class was
# created, and it may be reused across registries.
#
# In the example below, the field 'foo' appears once on its model's definition
# classes.  Assuming that it is not related, that field can be set up directly
# on its definition class.  If the model appears in several registries, the
# field 'foo' is effectively shared across registries.
#
#       class A1(Model):                      Model
#           _name = 'a'                        / \
#           foo = ...                         /   \
#           bar = ...                       A2     A1
#                                            bar    foo, bar
#       class A2(Model):                      \   /
#           _inherit = 'a'                     \ /
#           bar = ...                           a
#                                                bar
#
# On the other hand, the field 'bar' is overridden in its model's definition
# classes.  In that case, the framework recreates the field on the model's
# registry class.  The field's setup will be based on its definitions, and will
# not be shared across registries.
#
# The so-called magic fields ('id', 'display_name', ...) used to be added on
# registry classes.  But doing so prevents them from being shared.  So instead,
# we add them on definition classes that define a model without extending it.
# This increases the number of fields that are shared across registries.

def is_definition_class(cls):
    """ Return whether ``cls`` is a model definition class. """
    return isinstance(cls, MetaModel) and getattr(cls, 'pool', None) is None


def is_registry_class(cls):
    """ Return whether ``cls`` is a model registry class. """
    return getattr(cls, 'pool', None) is not None


class BaseModel(metaclass=MetaModel):
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
    _module = None              #: the model's module (in the Odoo sense)
    _custom = False             #: should be True for custom models only

    _inherit = ()
    """Python-inherited models:

    :type: str or list(str)

    .. note::

        * If :attr:`._name` is set, name(s) of parent models to inherit from
        * If :attr:`._name` is unset, name of a single model to extend in-place
    """
    _inherits = frozendict()
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
    _sql_constraints = []       #: SQL constraints [(name, sql_def, message)]

    _rec_name = None            #: field to use for labeling records, default: ``name``
    _rec_names_search = None    #: fields to consider in ``name_search``
    _order = 'id'               #: default order field for searching results
    _parent_name = 'parent_id'  #: the many2one field used as parent field
    _parent_store = False
    """set to True to compute parent_path field.

    Alongside a :attr:`~.parent_path` field, sets up an indexed storage
    of the tree structure of records, to enable faster hierarchical queries
    on the records of the current model using the ``child_of`` and
    ``parent_of`` domain operators.
    """
    _active_name = None
    """field to use for active records, automatically set to either ``"active"``
    or ``"x_active"``.
    """
    _fold_name = 'fold'         #: field to determine folded groups in kanban views

    _translate = True           # False disables translations export for this model (Old API)
    _check_company_auto = False
    """On write and create, call ``_check_company`` to ensure companies
    consistency on the relational fields having ``check_company=True``
    as attribute.
    """

    _allow_sudo_commands = True
    """Allow One2many and Many2many Commands targeting this model in an environment using `sudo()` or `with_user()`.
    By disabling this flag, security-sensitive models protect themselves
    against malicious manipulation of One2many or Many2many fields
    through an environment using `sudo` or a more priviledged user.
    """

    _depends = frozendict()
    """dependencies of models backed up by SQL views
    ``{model_name: field_names}``, where ``field_names`` is an iterable.
    This is only used to determine the changes to flush to database before
    executing ``search()`` or ``read_group()``. It won't be used for cache
    invalidation or recomputing fields.
    """

    # default values for _transient_vacuum()
    _transient_max_count = lazy_classproperty(lambda _: config.get('osv_memory_count_limit'))
    "maximum number of transient records, unlimited if ``0``"
    _transient_max_hours = lazy_classproperty(lambda _: config.get('transient_age_limit'))
    "maximum idle lifetime (in hours), unlimited if ``0``"

    def _valid_field_parameter(self, field, name):
        """ Return whether the given parameter name is valid for the field. """
        return name == 'related_sudo'

    @api.model
    def _add_field(self, name, field):
        """ Add the given ``field`` under the given ``name`` in the class """
        cls = self.env.registry[self._name]

        # Assert the name is an existing field in the model, or any model in the _inherits
        # or a custom field (starting by `x_`)
        is_class_field = any(
            isinstance(getattr(model, name, None), fields.Field)
            for model in [cls] + [self.env.registry[inherit] for inherit in cls._inherits]
        )
        if not (is_class_field or self.env['ir.model.fields']._is_manual_name(name)):
            raise ValidationError(
                f"The field `{name}` is not defined in the `{cls._name}` Python class and does not start with 'x_'"
            )

        # Assert the attribute to assign is a Field
        if not isinstance(field, fields.Field):
            raise ValidationError("You can only add `fields.Field` objects to a model fields")

        if not isinstance(getattr(cls, name, field), Field):
            _logger.warning("In model %r, field %r overriding existing value", cls._name, name)
        setattr(cls, name, field)
        field._toplevel = True
        field.__set_name__(cls, name)
        # add field as an attribute and in cls._fields (for reflection)
        cls._fields[name] = field

    @api.model
    def _pop_field(self, name):
        """ Remove the field with the given ``name`` from the model.
            This method should only be used for manual fields.
        """
        cls = self.env.registry[self._name]
        field = cls._fields.pop(name, None)
        discardattr(cls, name)
        if cls._rec_name == name:
            # fixup _rec_name and display_name's dependencies
            cls._rec_name = None
            if cls.display_name in cls.pool.field_depends:
                cls.pool.field_depends[cls.display_name] = tuple(
                    dep for dep in cls.pool.field_depends[cls.display_name] if dep != name
                )
        return field

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
        if getattr(cls, '_constraints', None):
            _logger.warning("Model attribute '_constraints' is no longer supported, "
                            "please use @api.constrains on methods instead.")

        # Keep links to non-inherited constraints in cls; this is useful for
        # instance when exporting translations
        cls._local_sql_constraints = cls.__dict__.get('_sql_constraints', [])

        # all models except 'base' implicitly inherit from 'base'
        name = cls._name
        parents = list(cls._inherit)
        if name != 'base':
            parents.append('base')

        # create or retrieve the model's class
        if name in parents:
            if name not in pool:
                raise TypeError("Model %r does not exist in registry." % name)
            ModelClass = pool[name]
            ModelClass._build_model_check_base(cls)
            check_parent = ModelClass._build_model_check_parent
        else:
            ModelClass = type(name, (cls,), {
                '_name': name,
                '_register': False,
                '_original_module': cls._module,
                '_inherit_module': {},                  # map parent to introducing module
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
                for base in parent_class.__base_classes:
                    bases.add(base)
            else:
                check_parent(cls, parent_class)
                bases.add(parent_class)
                ModelClass._inherit_module[parent] = cls._module
                parent_class._inherit_children.add(name)

        # ModelClass.__bases__ must be assigned those classes; however, this
        # operation is quite slow, so we do it once in method _prepare_setup()
        ModelClass.__base_classes = tuple(bases)

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
        cls._log_access = cls._auto
        inherits = {}
        depends = {}
        cls._sql_constraints = {}

        for base in reversed(cls.__base_classes):
            if is_definition_class(base):
                # the following attributes are not taken from registry classes
                if cls._name not in base._inherit and not base._description:
                    _logger.warning("The model %s has no _description", cls._name)
                cls._description = base._description or cls._description
                cls._table = base._table or cls._table
                cls._log_access = getattr(base, '_log_access', cls._log_access)

            inherits.update(base._inherits)

            for mname, fnames in base._depends.items():
                depends.setdefault(mname, []).extend(fnames)

            for cons in base._sql_constraints:
                cls._sql_constraints[cons[0]] = cons

        cls._sql_constraints = list(cls._sql_constraints.values())

        # avoid assigning an empty dict to save memory
        if inherits:
            cls._inherits = inherits
        if depends:
            cls._depends = depends

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
        cls._ondelete_methods = BaseModel._ondelete_methods
        cls._onchange_methods = BaseModel._onchange_methods

    @property
    def _constraint_methods(self):
        """ Return a list of methods implementing Python constraints. """
        def is_constraint(func):
            return callable(func) and hasattr(func, '_constrains')

        def wrap(func, names):
            # wrap func into a proxy function with explicit '_constrains'
            @api.constrains(*names)
            def wrapper(self):
                return func(self)
            return wrapper

        cls = self.env.registry[self._name]
        methods = []
        for attr, func in getmembers(cls, is_constraint):
            if callable(func._constrains):
                func = wrap(func, func._constrains(self))
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
    def _ondelete_methods(self):
        """ Return a list of methods implementing checks before unlinking. """
        def is_ondelete(func):
            return callable(func) and hasattr(func, '_ondelete')

        cls = self.env.registry[self._name]
        methods = [func for _, func in getmembers(cls, is_ondelete)]
        # optimization: memoize results on cls, it will not be recomputed
        cls._ondelete_methods = methods
        return methods

    @property
    def _onchange_methods(self):
        """ Return a dictionary mapping field names to onchange methods. """
        def is_onchange(func):
            return callable(func) and hasattr(func, '_onchange')

        # collect onchange methods on the model's class
        cls = self.env.registry[self._name]
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
            defaults = self.env['ir.default']._get_model_defaults(self._name, condition)
            self.update(defaults)

        for name, field in cls._fields.items():
            if field.change_default:
                methods[name].append(functools.partial(onchange_default, field))

        # optimization: memoize result on cls, it will not be recomputed
        cls._onchange_methods = methods
        return methods

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
        cr.execute(SQL("""
            SELECT res_id, module, name
            FROM ir_model_data
            WHERE model = %s AND res_id IN %s
        """, self._name, tuple(self.ids)))
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
        self.env['ir.model.data'].invalidate_model(fields)

        return (
            (record, to_xid(record.id))
            for record in self
        )

    def _export_rows(self, fields, *, _is_toplevel_call=True):
        """ Export fields of the records in ``self``.

        :param list fields: list of lists of fields to traverse
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
                sub.invalidate_recordset()
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
                                # display_name in the first column
                                name = None
                                index = i

                            if name == 'id':
                                xml_ids = [xid for _, xid in value.__ensure_xml_id()]
                                current[index] = ','.join(xml_ids)
                            else:
                                current[index] = field.convert_to_export(value, record)
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
                            current[i] = ''

        # if any xid should be exported, only do so at toplevel
        if _is_toplevel_call and any(f[-1] == 'id' for f in fields):
            bymodels = collections.defaultdict(set)
            xidmap = collections.defaultdict(list)
            # collect all the tuples in "lines" (along with their coordinates)
            for i, line in enumerate(lines):
                for j, cell in enumerate(line):
                    if isinstance(cell, tuple):
                        bymodels[cell[0]].add(cell[1])
                        xidmap[cell].append((i, j))
            # for each model, xid-export everything and inject in matrix
            for model, ids in bymodels.items():
                for record, xid in self.env[model].browse(ids).__ensure_xml_id():
                    for i, j in xidmap.pop((record._name, record.id)):
                        lines[i][j] = xid
            assert not xidmap, "failed to export xids for %s" % ', '.join('{}:{}' % it for it in xidmap.items())

        return lines

    def export_data(self, fields_to_export):
        """ Export fields for selected objects

        This method is used when exporting data via client menu

        :param list fields_to_export: list of fields
        :returns: dictionary with a *datas* matrix
        :rtype: dict
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
        self.env.flush_all()

        # determine values of mode, current_module and noupdate
        mode = self._context.get('mode', 'init')
        current_module = self._context.get('module', '__import__')
        noupdate = self._context.get('noupdate', False)
        # add current module in context for the conversion of xml ids
        self = self.with_context(_import_current_module=current_module)

        cr = self._cr
        sp = cr.savepoint(flush=False)

        fields = [fix_import_export_id_paths(f) for f in fields]
        fg = self.fields_get()

        ids = []
        messages = []

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
            global_error_message = None
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
            except UserError as e:
                global_error_message = dict(data_list[0]['info'], type='error', message=str(e))
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
                except UserError as e:
                    info = rec_data['info']
                    messages.append(dict(info, type='error', message=str(e)))
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
            if errors > 0 and global_error_message and global_error_message not in messages:
                # If we cannot create the records 1 by 1, we display the error raised when we created the records simultaneously
                messages.insert(0, global_error_message)

        # make 'flush' available to the methods below, in the case where XMLID
        # resolution fails, for instance
        flush_recordset = self.with_context(import_flush=flush, import_cache=LRU(1024))

        # TODO: break load's API instead of smuggling via context?
        limit = self._context.get('_import_limit')
        if limit is None:
            limit = float('inf')
        extracted = flush_recordset._extract_records(fields, data, log=messages.append, limit=limit)

        converted = flush_recordset._convert_records(extracted, log=messages.append)

        info = {'rows': {'to': -1}}
        for id, xid, record, info in converted:
            if self.env.context.get('import_file') and self.env.context.get('import_skip_records'):
                if any([record.get(field) is None for field in self.env.context['import_skip_records']]):
                    continue
            if xid:
                xid = xid if '.' in xid else "%s.%s" % (current_module, xid)
                batch_xml_ids.add(xid)
            elif id:
                record['id'] = id
            batch.append((xid, record, info))

        flush()
        if any(message['type'] == 'error' for message in messages):
            sp.rollback()
            ids = False
            # cancel all changes done to the registry/ormcache
            self.pool.reset_changes()
        sp.close(rollback=False)

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

        * None is the display_name for the record (to use with name_create/name_search)
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
                # non-empty, field path [None] is for display_name field
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
        ``self.create`` or ``(ir.model.data)._update``)

        :returns: a list of triplets of (id, xid, record)
        :rtype: list[(int|None, str|None, dict)]
        """
        field_names = {name: field.string for name, field in self._fields.items()}
        if self.env.lang:
            field_names.update(self.env['ir.model.fields'].get_field_string(self._name))

        convert = self.env['ir.fields.converter'].for_model(self)

        def _log(base, record, field, exception):
            type = 'warning' if isinstance(exception, Warning) else 'error'
            # logs the logical (not human-readable) field name for automated
            # processing of response, but injects human readable in message
            field_name = field_names[field]
            exc_vals = dict(base, record=record, field=field_name)
            record = dict(base, type=type, record=record, field=field,
                          message=str(exception.args[0]) % exc_vals)
            if len(exception.args) > 1:
                info = {}
                if exception.args[1] and isinstance(exception.args[1], dict):
                    info = exception.args[1]
                # ensure field_name is added to the exception. Used in import to
                # concatenate multiple errors in the same block
                info['field_name'] = field_name
                record.update(info)
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
        defaults = {}
        parent_fields = defaultdict(list)
        ir_defaults = self.env['ir.default']._get_model_defaults(self._name)

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
        # because the latter leaves values like [(Command.LINK, 2),
        # (Command.LINK, 3)], which are not supported by the web client as
        # default values; stepping through the cache allows to normalize
        # such a list to [(Command.SET, 0, [2, 3])], which is properly
        # supported by the web client
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
    def _rec_name_fallback(self):
        # if self._rec_name is set, it belongs to self._fields
        return self._rec_name or 'id'

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
    def search_count(self, domain, limit=None):
        """ search_count(domain[, limit=None]) -> int

        Returns the number of records in the current model matching :ref:`the
        provided domain <reference/orm/domains>`.

        :param domain: :ref:`A search domain <reference/orm/domains>`. Use an empty
                     list to match all records.
        :param limit: maximum number of record to count (upperbound) (default: all)

        This is a high-level method, which should not be overridden. Its actual
        implementation is done by method :meth:`_search`.
        """
        query = self._search(domain, limit=limit)
        return len(query)

    @api.model
    @api.returns('self')
    def search(self, domain, offset=0, limit=None, order=None):
        """ search(domain[, offset=0][, limit=None][, order=None])

        Search for the records that satisfy the given ``domain``
        :ref:`search domain <reference/orm/domains>`.

        :param domain: :ref:`A search domain <reference/orm/domains>`. Use an empty
                     list to match all records.
        :param int offset: number of results to ignore (default: none)
        :param int limit: maximum number of records to return (default: all)
        :param str order: sort string
        :returns: at most ``limit`` records matching the search criteria
        :raise AccessError: if user is not allowed to access requested information

        This is a high-level method, which should not be overridden. Its actual
        implementation is done by method :meth:`_search`.
        """
        return self.search_fetch(domain, [], offset=offset, limit=limit, order=order)

    @api.model
    @api.returns('self')
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        """ search_fetch(domain, field_names[, offset=0][, limit=None][, order=None])

        Search for the records that satisfy the given ``domain``
        :ref:`search domain <reference/orm/domains>`, and fetch the given fields
        to the cache.  This method is like a combination of methods :meth:`search`
        and :meth:`fetch`, but it performs both tasks with a minimal number of
        SQL queries.

        :param domain: :ref:`A search domain <reference/orm/domains>`. Use an empty
                     list to match all records.
        :param field_names: a collection of field names to fetch
        :param int offset: number of results to ignore (default: none)
        :param int limit: maximum number of records to return (default: all)
        :param str order: sort string
        :returns: at most ``limit`` records matching the search criteria
        :raise AccessError: if user is not allowed to access requested information
        """
        # first determine a query that satisfies the domain and access rules
        query = self._search(domain, offset=offset, limit=limit, order=order or self._order)

        if query.is_empty():
            # optimization: don't execute the query at all
            return self.browse()

        fields_to_fetch = self._determine_fields_to_fetch(field_names)

        return self._fetch_query(query, fields_to_fetch)

    #
    # display_name, name_get, name_create, name_search
    #

    @api.depends(lambda self: (self._rec_name,) if self._rec_name else ())
    def _compute_display_name(self):
        """Compute the value of the `display_name` field.

        The `display_name` field is a textual representation of the record.
        This method can be overridden to change the representation.  If needed,
        it can be made field-dependent using :attr:`~odoo.api.depends` and
        context-dependent using :attr:`~odoo.api.depends_context`.
        """
        if self._rec_name:
            convert = self._fields[self._rec_name].convert_to_display_name
            for record in self:
                record.display_name = convert(record[self._rec_name], record)
        else:
            for record in self:
                record.display_name = f"{record._name},{record.id}"

    def name_get(self):
        """Returns a textual representation for the records in ``self``, with
        one item output per input record, in the same order.

        .. warning::

            Although :meth:`~.name_get` can use context data for richer
            contextual formatting, as it is the default implementation for
            :attr:`~.display_name` it is important that it resets to the
            "default" behaviour if the context keys are empty / missing.

        .. deprecated:: 17.0
            Deprecated method, read([`display_name`]) instead

        :return: list of pairs ``(id, text_repr)`` for each record
        :rtype: list[(int, str)]
        """
        warnings.warn("Since 17.0, deprecated method, read display_name instead", DeprecationWarning, 2)
        return [(record.id, record.display_name) for record in self]

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
        :return: the (id, display_name) pair value of the created record
        """
        if self._rec_name:
            record = self.create({self._rec_name: name})
            return record.id, record.display_name
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
        value for a relational field. Should usually behave as the reverse of
        ``display_name``, but that is not guaranteed.

        This method is equivalent to calling :meth:`~.search` with a search
        domain based on ``display_name`` and mapping id and display_name on
        the resulting search.

        :param str name: the name pattern to match
        :param list args: optional search domain (see :meth:`~.search` for
                          syntax), specifying further restrictions
        :param str operator: domain operator for matching ``name``, such as
                             ``'like'`` or ``'='``.
        :param int limit: optional max number of records to return
        :rtype: list
        :return: list of pairs ``(id, display_name)`` for all matching records.
        """
        ids = self._name_search(name, args, operator, limit=limit, order=self._order)

        if isinstance(ids, Query):
            records = self._fetch_query(ids, self._determine_fields_to_fetch(['display_name']))
        else:
            # Some override of `_name_search` return list of ids.
            records = self.browse(ids)
            records.fetch(['display_name'])

        return [(record.id, record.display_name) for record in records.sudo()]

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        """ _name_search(name='', domain=None, operator='ilike', limit=None, order=None) -> ids

        Private implementation of name_search, returning ids or a :class:`Query` object.

        No default is applied for parameters ``limit`` and ``order``.
        """
        domain = list(domain or ())
        search_fnames = self._rec_names_search or ([self._rec_name] if self._rec_name else [])
        if not search_fnames:
            _logger.warning("Cannot execute name_search, no _rec_name or _rec_names_search defined on %s", self._name)
        # optimize out the default criterion of ``like ''`` that matches everything
        elif not (name == '' and operator in ('like', 'ilike')):
            aggregator = expression.AND if operator in expression.NEGATIVE_TERM_OPERATORS else expression.OR
            domain += aggregator([[(field_name, operator, name)] for field_name in search_fnames])
        return self._search(domain, limit=limit, order=order)

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
        missing_defaults = [
            name
            for name, field in self._fields.items()
            if name not in values
            if not avoid(field)
        ]

        if missing_defaults:
            # override defaults with the provided values, never allow the other way around
            defaults = self.default_get(missing_defaults)
            for name, value in defaults.items():
                if self._fields[name].type == 'many2many' and value and isinstance(value[0], int):
                    # convert a list of ids into a list of commands
                    defaults[name] = [Command.set(value)]
                elif self._fields[name].type == 'one2many' and value and isinstance(value[0], dict):
                    # convert a list of dicts into a list of commands
                    defaults[name] = [Command.create(x) for x in value]
            defaults.update(values)

        else:
            defaults = values

        # delegate the default properties to the properties field
        for field in self._fields.values():
            if field.type == 'properties':
                defaults[field.name] = field._add_default_values(self.env, defaults)

        return defaults

    @classmethod
    def clear_caches(cls):
        """ Clear the caches

        This clears the caches associated to methods decorated with
        ``tools.ormcache``.
        """
        warnings.warn("Deprecated model.clear_cache(), use registry.clear_cache() instead", DeprecationWarning)
        cls.pool.clear_all_caches()

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        """ Get fields aggregations specified by ``aggregates`` grouped by the given ``groupby``
        fields where record are filtered by the ``domain``.

        :param list domain: :ref:`A search domain <reference/orm/domains>`. Use an empty
                list to match all records.
        :param list groupby: list of groupby descriptions by which the records will be grouped.
                A groupby description is either a field (then it will be grouped by that field)
                or a string `'field:granularity'`. Right now, the only supported granularities
                are `'day'`, `'week'`, `'month'`, `'quarter'` or `'year'`, and they only make sense for
                date/datetime fields.
        :param list aggregates: list of aggregates specification.
                Each element is `'field:agg'` (aggregate field with aggregation function `'agg'`).
                The possible aggregation functions are the ones provided by
                `PostgreSQL <https://www.postgresql.org/docs/current/static/functions-aggregate.html>`_,
                `'count_distinct'` with the expected meaning and `'recordset'` to act like `'array_agg'`
                converted into a recordset.
        :param list having: A domain where the valid "fields" are the aggregates.
        :param int offset: optional number of groups to skip
        :param int limit: optional max number of groups to return
        :param str order: optional ``order by`` specification, for
                overriding the natural sort ordering of the groups,
                see also :meth:`~.search`.
        :return: list of tuple containing in the order the groups values and aggregates values (flatten):
                `[(groupby_1_value, ... , aggregate_1_value_aggregate, ...), ...]`.
                If group is related field, the value of it will be a recordset (with a correct prefetch set).

        :rtype: list
        :raise AccessError: if user is not allowed to access requested information
        """
        self.check_access_rights('read')

        if expression.is_false(self, domain):
            if not groupby:
                # when there is no group, postgresql always return a row
                return [tuple(
                    self._read_group_empty_value(spec)
                    for spec in itertools.chain(groupby, aggregates)
                )]
            return []

        query = self._search(domain)

        fnames_to_flush = OrderedSet()

        groupby_terms: dict[str, SQL] = {}
        for spec in groupby:
            groupby_terms[spec], fnames_used = self._read_group_groupby(spec, query)
            fnames_to_flush.update(fnames_used)

        select_terms: list[SQL] = []
        for spec in aggregates:
            sql_expr, fnames_used = self._read_group_select(spec, query)
            select_terms.append(sql_expr)
            fnames_to_flush.update(fnames_used)

        sql_having, fnames_used = self._read_group_having(having, query)
        fnames_to_flush.update(fnames_used)

        sql_order, sql_extra_groupby, fnames_used = self._read_group_orderby(order, groupby_terms, query)
        fnames_to_flush.update(fnames_used)

        groupby_terms = list(groupby_terms.values())

        query_parts = [
            SQL("SELECT %s", SQL(", ").join(groupby_terms + select_terms)),
            SQL("FROM %s", query.from_clause),
        ]
        if query.where_clause:
            query_parts.append(SQL("WHERE %s", query.where_clause))
        if groupby_terms:
            if sql_extra_groupby:
                groupby_terms.append(sql_extra_groupby)
            query_parts.append(SQL("GROUP BY %s", SQL(", ").join(groupby_terms)))
        if sql_having:
            query_parts.append(SQL("HAVING %s", sql_having))
        if sql_order:
            query_parts.append(SQL("ORDER BY %s", sql_order))
        if limit:
            query_parts.append(SQL("LIMIT %s", limit))
        if offset:
            query_parts.append(SQL("OFFSET %s", offset))

        self._flush_search(domain, fnames_to_flush)
        if fnames_to_flush:
            self._read_group_check_field_access_rights(fnames_to_flush)

        self.env.cr.execute(SQL("\n").join(query_parts))
        # row_values: [(a1, b1, c1), (a2, b2, c2), ...]
        row_values = self.env.cr.fetchall()

        if not row_values:
            return row_values

        # post-process values column by column
        column_iterator = zip(*row_values)

        # column_result: [(a1, a2, ...), (b1, b2, ...), (c1, c2, ...)]
        column_result = []
        for spec in groupby:
            column = self._read_group_postprocess_groupby(spec, next(column_iterator))
            column_result.append(column)
        for spec in aggregates:
            column = self._read_group_postprocess_aggregate(spec, next(column_iterator))
            column_result.append(column)
        assert next(column_iterator, None) is None

        # return [(a1, b1, c1), (a2, b2, c2), ...]
        return list(zip(*column_result))

    def _read_group_select(self, aggregate_spec: str, query: Query) -> tuple[SQL, list[str]]:
        """ Return a pair (<SQL expression>, [<field names used in SQL expression>])
        corresponding to the given aggregation.
        """
        if aggregate_spec == '__count':
            return SQL("COUNT(*)"), []

        fname, property_name, func = parse_read_group_spec(aggregate_spec)

        access_fname = f"{fname}.{property_name}" if property_name else fname

        if fname not in self:
            raise ValueError(f"Invalid field {fname!r} on model {self._name!r} for {aggregate_spec!r}.")
        if not func:
            raise ValueError(f"Aggregate method is mandatory for {access_fname!r}")
        if func not in READ_GROUP_AGGREGATE:
            raise ValueError(f"Invalid aggregate method {func!r} for {aggregate_spec!r}.")

        field = self._fields[fname]
        if func == 'recordset' and not (field.relational or fname == 'id'):
            raise ValueError(f"Aggregate method {func!r} can be only used on relational field (or id) (for {aggregate_spec!r}).")
        if property_name and field.type != 'property':
            warnings.warn(f"Ignore the {property_name!r} part of {aggregate_spec!r}, this notation is reserved for the Property field")

        sql_field = self._field_to_sql(self._table, access_fname, query)
        sql_expr = READ_GROUP_AGGREGATE[func](self._table, sql_field)
        return sql_expr, [fname]

    def _read_group_groupby(self, groupby_spec: str, query: Query) -> tuple[SQL, list[str]]:
        """ Return a pair (<SQL expression>, [<field names used in SQL expression>])
        corresponding to the given groupby element.
        """
        fname, property_name, granularity = parse_read_group_spec(groupby_spec)
        if fname not in self:
            raise ValueError(f"Invalid field {fname!r} on model {self._name!r}")

        field = self._fields[fname]

        if property_name:
            if field.type != "properties":
                raise ValueError(f"Property set on a non properties field: {property_name!r}")
            access_fname = f"{fname}.{property_name}"
        else:
            access_fname = fname

        if granularity and field.type not in ('datetime', 'date', 'properties'):
            raise ValueError(f"Granularity set on a no-datetime field or property: {groupby_spec!r}")

        sql_expr = self._field_to_sql(self._table, access_fname, query)
        if field.type == 'datetime' and self.env.context.get('tz') in pytz.all_timezones_set:
            sql_expr = SQL("timezone(%s, timezone('UTC', %s))", self.env.context['tz'], sql_expr)

        if field.type in ('datetime', 'date') or (field.type == 'properties' and granularity):
            if not granularity:
                raise ValueError(f"Granularity not set on a date(time) field: {groupby_spec!r}")
            if granularity not in READ_GROUP_TIME_GRANULARITY:
                raise ValueError(f"Granularity specification isn't correct: {granularity!r}")

            if granularity == 'week':
                # first_week_day: 0=Monday, 1=Tuesday, ...
                first_week_day = int(get_lang(self.env).week_start) - 1
                days_offset = first_week_day and 7 - first_week_day
                interval = f"-{days_offset} DAY"
                sql_expr = SQL(
                    "(date_trunc('week', %s::timestamp - INTERVAL %s) + INTERVAL %s)",
                    sql_expr, interval, interval,
                )
            else:
                sql_expr = SQL("date_trunc(%s, %s::timestamp)", granularity, sql_expr)

            if field.type == 'date':
                sql_expr = SQL("%s::date", sql_expr)

        elif field.type == 'boolean':
            sql_expr = SQL("COALESCE(%s, FALSE)", sql_expr)

        return sql_expr, [fname]

    def _read_group_having(self, having_domain: list, query: Query) -> tuple[SQL, list[str]]:
        """ Return a pair (<SQL expression>, [<used field name>]) corresponding
        to the having domain.
        """
        if not having_domain:
            return SQL(), []

        stack: list[SQL] = []
        fnames_used = []
        SUPPORTED = ('in', 'not in', '<', '>', '<=', '>=', '=', '!=')
        for item in reversed(having_domain):
            if item == '!':
                stack.append(SQL("(NOT %s)", stack.pop()))
            elif item == '&':
                stack.append(SQL("(%s AND %s)", stack.pop(), stack.pop()))
            elif item == '|':
                stack.append(SQL("(%s OR %s)", stack.pop(), stack.pop()))
            elif isinstance(item, (list, tuple)) and len(item) == 3:
                left, operator, right = item
                if operator not in SUPPORTED:
                    raise ValueError(f"Invalid having clause {item!r}: supported comparators are {SUPPORTED}")
                sql_left, fnames = self._read_group_select(left, query)
                sql_operator = expression.SQL_OPERATORS[operator]
                stack.append(SQL("%s %s %s", sql_left, sql_operator, right))
                fnames_used.extend(fnames)
            else:
                raise ValueError(f"Invalid having clause {item!r}: it should be a domain-like clause")

        while len(stack) > 1:
            stack.append(SQL("(%s AND %s)", stack.pop(), stack.pop()))

        return stack[0], fnames_used

    def _read_group_orderby(self, order: str, groupby_terms: dict[str, SQL],
                            query: Query) -> tuple[SQL, SQL, list[str]]:
        """ Return (<SQL expression>, <SQL expression>, [<field names used>])
        corresponding to the given order and groupby terms.

        :param order: the order specification
        :param groupby_terms: the group by terms mapping ({spec: sql_expression})
        :param query: The query we are building
        """
        if order:
            traverse_many2one = True
        else:
            order = ','.join(groupby_terms)
            traverse_many2one = False

        if not order:
            return SQL(), SQL(), []

        orderby_terms = []
        extra_groupby_terms = []
        fnames_used = []

        for order_part in order.split(','):
            order_match = regex_order.match(order_part)
            if not order_match:
                raise ValueError(f"Invalid order {order!r} for _read_group()")
            term = order_match['term']
            direction = (order_match['direction'] or 'ASC').upper()
            nulls = (order_match['nulls'] or '').upper()

            sql_direction = SQL(direction) if direction in ('ASC', 'DESC') else SQL()
            sql_nulls = SQL(nulls) if nulls in ('NULLS FIRST', 'NULLS LAST') else SQL()

            if term not in groupby_terms:
                try:
                    sql_expr, fnames = self._read_group_select(term, query)
                except ValueError as e:
                    raise ValueError(f"Order term {order_part!r} is not a valid aggregate nor valid groupby") from e
                orderby_terms.append(SQL("%s %s %s", sql_expr, sql_direction, sql_nulls))
                fnames_used.extend(fnames)
                continue

            field = self._fields.get(term)
            if (
                traverse_many2one and field and field.type == 'many2one'
                and self.env[field.comodel_name]._order != 'id'
            ):
                # this generates an extra clause to add in the group by
                sql_order = self._order_to_sql(f'{term} {direction} {nulls}', query)
                orderby_terms.append(sql_order)
                sql_order_str = self.env.cr.mogrify(sql_order).decode()
                extra_groupby_terms.extend(
                    SQL(order.strip().split()[0])
                    for order in sql_order_str.split(",")
                    if order.strip()
                )

            else:
                sql_expr = groupby_terms[term]
                orderby_terms.append(SQL("%s %s %s", sql_expr, sql_direction, sql_nulls))

        return SQL(", ").join(orderby_terms), SQL(", ").join(extra_groupby_terms), fnames_used

    @api.model
    def _read_group_check_field_access_rights(self, field_names):
        """ Check whether the given field names can be grouped or aggregated. """
        self.check_field_access_rights('read', field_names)

    @api.model
    def _read_group_empty_value(self, spec):
        """ Return the empty value corresponding to the given groupby spec or aggregate spec. """
        if spec == '__count':
            return 0
        fname, __, func = parse_read_group_spec(spec)  # func is either None, granularity or an aggregate
        if func in ('count', 'count_distinct'):
            return 0
        if func == 'array_agg':
            return []
        field = self._fields[fname]
        if (not func or func == 'recordset') and (field.relational or fname == 'id'):
            return self.env[field.comodel_name] if field.relational else self.env[self._name]
        return False

    def _read_group_postprocess_groupby(self, groupby_spec, raw_values):
        """ Convert the given values of ``groupby_spec``
        from PostgreSQL to the format returned by method ``_read_group()``.

        The formatting rules can be summarized as:
        - groupby values of relational fields are converted to recordsets with a correct prefetch set;
        - NULL values are converted to empty values corresponding to the given aggregate.
        """
        empty_value = self._read_group_empty_value(groupby_spec)

        fname, *__ = parse_read_group_spec(groupby_spec)
        field = self._fields[fname]

        if field.relational or fname == 'id':
            Model = self.pool[field.comodel_name] if field.relational else self.pool[self._name]
            prefetch_ids = tuple(raw_value for raw_value in raw_values if raw_value)

            def recordset(value):
                return Model(self.env, (value,), prefetch_ids) if value else empty_value

            return (recordset(value) for value in raw_values)

        return ((value if value is not None else empty_value) for value in raw_values)

    def _read_group_postprocess_aggregate(self, aggregate_spec, raw_values):
        """ Convert the given values of ``aggregate_spec``
        from PostgreSQL to the format returned by method ``_read_group()``.

        The formatting rules can be summarized as:
        - 'recordset' aggregates are turned into recordsets with a correct prefetch set;
        - NULL values are converted to empty values corresponding to the given aggregate.
        """
        empty_value = self._read_group_empty_value(aggregate_spec)

        if aggregate_spec == '__count':
            return ((value if value is not None else empty_value) for value in raw_values)

        fname, __, func = parse_read_group_spec(aggregate_spec)
        if func == 'recordset':
            field = self._fields[fname]
            Model = self.pool[field.comodel_name] if field.relational else self.pool[self._name]
            prefetch_ids = tuple(unique(
                id_
                for array_values in raw_values if array_values
                for id_ in array_values if id_
            ))

            def recordset(value):
                if not value:
                    return empty_value
                ids = tuple(unique(id_ for id_ in value if id_))
                return Model(self.env, ids, prefetch_ids)

            return (recordset(value) for value in raw_values)

        return ((value if value is not None else empty_value) for value in raw_values)

    @api.model
    def _read_group_expand_full(self, groups, domain, order):
        """Extend the group to include all target records by default."""
        return groups.search([], order=order)

    @api.model
    def _read_group_fill_results(self, domain, groupby, annoted_aggregates, read_group_result, read_group_order=None):
        """Helper method for filling in empty groups for all possible values of
           the field being grouped by"""
        field_name = groupby.split('.')[0].split(':')[0]
        field = self._fields[field_name]
        if not field or not field.group_expand:
            return read_group_result

        # field.group_expand is a callable or the name of a method, that returns
        # the groups that we want to display for this field, in the form of a
        # recordset or a list of values (depending on the type of the field).
        # This is useful to implement kanban views for instance, where some
        # columns should be displayed even if they don't contain any record.
        group_expand = field.group_expand
        if isinstance(group_expand, str):
            group_expand = getattr(self.env.registry[self._name], group_expand)
        assert callable(group_expand)

        # determine all groups that should be returned
        values = [line[groupby] for line in read_group_result if line[groupby]]

        if field.relational:
            # groups is a recordset; determine order on groups's model
            groups = self.env[field.comodel_name].browse([value.id for value in values])
            order = groups._order
            if read_group_order == groupby + ' desc':
                order = tools.reverse_order(order)
            groups = group_expand(self, groups, domain, order)
            values = groups.sudo()
            value2key = lambda value: value and value.id

        else:
            # groups is a list of values
            values = group_expand(self, values, domain, None)
            if read_group_order == groupby + ' desc':
                values.reverse()
            value2key = lambda value: value

        # Merge the current results (list of dicts) with all groups. Determine
        # the global order of results groups, which is supposed to be in the
        # same order as read_group_result (in the case of a many2one field).

        read_group_result_as_dict = {}
        for line in read_group_result:
            read_group_result_as_dict[value2key(line[groupby])] = line

        empty_item = {
            name: self._read_group_empty_value(spec)
            for name, spec in annoted_aggregates.items()
        }

        result = {}
        # fill result with the values order
        for value in values:
            key = value2key(value)
            if key in read_group_result_as_dict:
                result[key] = read_group_result_as_dict.pop(key)
            else:
                result[key] = dict(empty_item, **{groupby: value})

        for line in read_group_result_as_dict.values():
            key = value2key(line[groupby])
            result[key] = line

        # add folding information if present
        if field.relational and groups._fold_name in groups._fields:
            fold = {group.id: group[groups._fold_name]
                    for group in groups.browse([key for key in result if key])}
            for key, line in result.items():
                line['__fold'] = fold.get(key, False)

        return list(result.values())

    @api.model
    def _read_group_fill_temporal(self, data, groupby, annoted_aggregates,
                                  fill_from=False, fill_to=False, min_groups=False):
        """Helper method for filling date/datetime 'holes' in a result set.

        We are in a use case where data are grouped by a date field (typically
        months but it could be any other interval) and displayed in a chart.

        Assume we group records by month, and we only have data for June,
        September and December. By default, plotting the result gives something
        like::

                                                ___
                                      ___      |   |
                                     |   | ___ |   |
                                     |___||___||___|
                                      Jun  Sep  Dec

        The problem is that December data immediately follow September data,
        which is misleading for the user. Adding explicit zeroes for missing
        data gives something like::

                                                           ___
                             ___                          |   |
                            |   |           ___           |   |
                            |___| ___  ___ |___| ___  ___ |___|
                             Jun  Jul  Aug  Sep  Oct  Nov  Dec

        To customize this output, the context key "fill_temporal" can be used
        under its dictionary format, which has 3 attributes : fill_from,
        fill_to, min_groups (see params of this function)

        Fill between bounds:
        Using either `fill_from` and/or `fill_to` attributes, we can further
        specify that at least a certain date range should be returned as
        contiguous groups. Any group outside those bounds will not be removed,
        but the filling will only occur between the specified bounds. When not
        specified, existing groups will be used as bounds, if applicable.
        By specifying such bounds, we can get empty groups before/after any
        group with data.

        If we want to fill groups only between August (fill_from)
        and October (fill_to)::

                                                     ___
                                 ___                |   |
                                |   |      ___      |   |
                                |___| ___ |___| ___ |___|
                                 Jun  Aug  Sep  Oct  Dec

        We still get June and December. To filter them out, we should match
        `fill_from` and `fill_to` with the domain e.g. ``['&',
        ('date_field', '>=', 'YYYY-08-01'), ('date_field', '<', 'YYYY-11-01')]``::

                                         ___
                                    ___ |___| ___
                                    Aug  Sep  Oct

        Minimal filling amount:
        Using `min_groups`, we can specify that we want at least that amount of
        contiguous groups. This amount is guaranteed to be provided from
        `fill_from` if specified, or from the lowest existing group otherwise.
        This amount is not restricted by `fill_to`. If there is an existing
        group before `fill_from`, `fill_from` is still used as the starting
        group for min_groups, because the filling does not apply on that
        existing group. If neither `fill_from` nor `fill_to` is specified, and
        there is no existing group, no group will be returned.

        If we set min_groups = 4::

                                         ___
                                    ___ |___| ___ ___
                                    Aug  Sep  Oct Nov

        :param list data: the data containing groups
        :param list groupby: list of fields being grouped on
        :param list annoted_aggregates: dict of "<key_name>:<aggregate specification>"
        :param str fill_from: (inclusive) string representation of a
            date/datetime, start bound of the fill_temporal range
            formats: date -> %Y-%m-%d, datetime -> %Y-%m-%d %H:%M:%S
        :param str fill_to: (inclusive) string representation of a
            date/datetime, end bound of the fill_temporal range
            formats: date -> %Y-%m-%d, datetime -> %Y-%m-%d %H:%M:%S
        :param int min_groups: minimal amount of required groups for the
            fill_temporal range (should be >= 1)
        :rtype: list
        :return: list
        """
        # TODO: remove min_groups
        first_group = groupby[0]
        field_name = first_group.split(':')[0].split(".")[0]
        field = self._fields[field_name]
        if field.type not in ('date', 'datetime') and not (field.type == 'properties' and ':' in first_group):
            return data

        granularity = first_group.split(':')[1] if ':' in first_group else 'month'
        days_offset = 0
        if granularity == 'week':
            # _read_group_process_groupby week groups are dependent on the
            # locale, so filled groups should be too to avoid overlaps.
            first_week_day = int(get_lang(self.env).week_start) - 1
            days_offset = first_week_day and 7 - first_week_day
        interval = READ_GROUP_TIME_GRANULARITY[granularity]
        tz = False
        if field.type == 'datetime' and self._context.get('tz') in pytz.all_timezones_set:
            tz = pytz.timezone(self._context['tz'])

        # TODO: refactor remaing lines here

        # existing non null datetimes
        existing = [d[first_group] for d in data if d[first_group]] or [None]
        # assumption: existing data is sorted by field 'groupby_name'
        existing_from, existing_to = existing[0], existing[-1]
        if fill_from:
            fill_from = odoo.fields.Datetime.to_datetime(fill_from) if isinstance(fill_from, datetime.datetime) else odoo.fields.Date.to_date(fill_from)
            fill_from = date_utils.start_of(fill_from, granularity) - datetime.timedelta(days=days_offset)
            if tz:
                fill_from = tz.localize(fill_from)
        elif existing_from:
            fill_from = existing_from
        if fill_to:
            fill_to = odoo.fields.Datetime.to_datetime(fill_to) if isinstance(fill_to, datetime.datetime) else odoo.fields.Date.to_date(fill_to)
            fill_to = date_utils.start_of(fill_to, granularity) - datetime.timedelta(days=days_offset)
            if tz:
                fill_to = tz.localize(fill_to)
        elif existing_to:
            fill_to = existing_to

        if not fill_to and fill_from:
            fill_to = fill_from
        if not fill_from and fill_to:
            fill_from = fill_to
        if not fill_from and not fill_to:
            return data

        if min_groups > 0:
            fill_to = max(fill_to, fill_from + (min_groups - 1) * interval)

        if fill_to < fill_from:
            return data

        required_dates = date_utils.date_range(fill_from, fill_to, interval)

        if existing[0] is None:
            existing = list(required_dates)
        else:
            existing = sorted(set().union(existing, required_dates))

        empty_item = {
            name: self._read_group_empty_value(spec)
            for name, spec in annoted_aggregates.items()
        }
        for group in groupby[1:]:
            empty_item[group] = self._read_group_empty_value(group)

        grouped_data = collections.defaultdict(list)
        for d in data:
            grouped_data[d[first_group]].append(d)

        result = []
        for dt in existing:
            result.extend(grouped_data[dt] or [dict(empty_item, **{first_group: dt})])

        if False in grouped_data:
            result.extend(grouped_data[False])

        return result

    @api.model
    def _read_group_format_result(self, rows_dict, lazy_groupby):
        """
            Helper method to format the data contained in the dictionary data by
            adding the domain corresponding to its values, the groupbys in the
            context and by properly formatting the date/datetime values.

        :param data: a single group
        :param annotated_groupbys: expanded grouping metainformation
        :param groupby: original grouping metainformation
        """
        for group in lazy_groupby:
            field_name = group.split(':')[0].split('.')[0]
            field = self._fields[field_name]

            if field.type in ('date', 'datetime'):
                locale = get_lang(self.env).code
                fmt = DEFAULT_SERVER_DATETIME_FORMAT if field.type == 'datetime' else DEFAULT_SERVER_DATE_FORMAT
                granularity = group.split(':')[1] if ':' in group else 'month'
                interval = READ_GROUP_TIME_GRANULARITY[granularity]

            elif field.type == "properties":
                self._read_group_format_result_properties(rows_dict, group)
                continue

            for row in rows_dict:
                value = row[group]

                if isinstance(value, BaseModel):
                    row[group] = (value.id, value.sudo().display_name) if value else False
                    value = value.id

                if not value and field.type == 'many2many':
                    other_values = [other_row[group][0] if isinstance(other_row[group], tuple)
                                    else other_row[group].id if isinstance(other_row[group], BaseModel)
                                    else other_row[group] for other_row in rows_dict if other_row[group]]
                    additional_domain = [(field_name, 'not in', other_values)]
                else:
                    additional_domain = [(field_name, '=', value)]

                if field.type in ('date', 'datetime'):
                    if value and isinstance(value, (datetime.date, datetime.datetime)):
                        range_start = value
                        range_end = value + interval
                        if field.type == 'datetime':
                            tzinfo = None
                            if self._context.get('tz') in pytz.all_timezones_set:
                                tzinfo = pytz.timezone(self._context['tz'])
                                range_start = tzinfo.localize(range_start).astimezone(pytz.utc)
                                # take into account possible hour change between start and end
                                range_end = tzinfo.localize(range_end).astimezone(pytz.utc)

                            label = babel.dates.format_datetime(
                                range_start, format=READ_GROUP_DISPLAY_FORMAT[granularity],
                                tzinfo=tzinfo, locale=locale
                            )
                        else:
                            label = babel.dates.format_date(
                                value, format=READ_GROUP_DISPLAY_FORMAT[granularity],
                                locale=locale
                            )

                        range_start = range_start.strftime(fmt)
                        range_end = range_end.strftime(fmt)
                        row[group] = label  # TODO should put raw data
                        row.setdefault('__range', {})[group] = {'from': range_start, 'to': range_end}
                        additional_domain = [
                            '&',
                                (field_name, '>=', range_start),
                                (field_name, '<', range_end),
                        ]
                    elif not value:
                        # Set the __range of the group containing records with an unset
                        # date/datetime field value to False.
                        row.setdefault('__range', {})[group] = False

                row['__domain'] = expression.AND([row['__domain'], additional_domain])

    def _read_group_format_result_properties(self, rows_dict, group):
        """Modify the final read group properties result.

        Replace the relational properties ids by a tuple with their display names,
        replace the "raw" tags and selection values by a list containing their labels.
        Adapt the domains for the Falsy group (we can't just keep (selection, =, False)
        e.g. because some values in database might correspond to  option that have
        been remove on the parent).
        """
        if '.' not in group:
            raise ValueError('You must choose the property you want to group by.')
        fullname, __, func = group.partition(':')

        definition = self.get_property_definition(fullname)
        property_type = definition.get('type')

        if property_type == 'selection':
            options = definition.get('selection') or []
            options = tuple(option[0] for option in options)
            for row in rows_dict:
                if not row[fullname]:
                    # can not do ('selection', '=', False) because we might have
                    # option in database that does not exist anymore
                    additional_domain = expression.OR([
                        [(fullname, '=', False)],
                        [(fullname, 'not in', options)],
                    ])
                else:
                    additional_domain = [(fullname, '=', row[fullname])]

                row['__domain'] = expression.AND([row['__domain'], additional_domain])

        elif property_type == 'many2one':
            comodel = definition.get('comodel')
            prefetch_ids = tuple(row[fullname] for row in rows_dict if row[fullname])
            all_groups = tuple(row[fullname] for row in rows_dict if row[fullname])
            for row in rows_dict:
                if not row[fullname]:
                    # can not only do ('many2one', '=', False) because we might have
                    # record in database that does not exist anymore
                    additional_domain = expression.OR([
                        [(fullname, '=', False)],
                        [(fullname, 'not in', all_groups)],
                    ])
                else:
                    additional_domain = [(fullname, '=', row[fullname])]
                    record = self.env[comodel].browse(row[fullname]).with_prefetch(prefetch_ids)
                    row[fullname] = (row[fullname], record.display_name)

                row['__domain'] = expression.AND([row['__domain'], additional_domain])

        elif property_type == 'many2many':
            comodel = definition.get('comodel')
            prefetch_ids = tuple(row[fullname] for row in rows_dict if row[fullname])
            all_groups = tuple(row[fullname] for row in rows_dict if row[fullname])
            for row in rows_dict:
                if not row[fullname]:
                    additional_domain = expression.OR([
                        [(fullname, '=', False)],
                        expression.AND([[(fullname, 'not in', group)] for group in all_groups]),
                    ]) if all_groups else []
                else:
                    additional_domain = [(fullname, 'in', row[fullname])]
                    record = self.env[comodel].browse(row[fullname]).with_prefetch(prefetch_ids)
                    row[fullname] = (row[fullname], record.display_name)

                row['__domain'] = expression.AND([row['__domain'], additional_domain])

        elif property_type == 'tags':
            tags = definition.get('tags') or []
            tags = {tag[0]: tag for tag in tags}
            for row in rows_dict:
                if not row[fullname]:
                    additional_domain = expression.OR([
                        [(fullname, '=', False)],
                        expression.AND([[(fullname, 'not in', tag)] for tag in tags]),
                    ]) if tags else []
                else:
                    additional_domain = [(fullname, 'in', row[fullname])]
                    # replace tag raw value with list of raw value, label and color
                    row[fullname] = tags.get(row[fullname])

                row['__domain'] = expression.AND([row['__domain'], additional_domain])

        elif property_type in ('date', 'datetime'):
            for row in rows_dict:
                if not row[group]:
                    row[group] = False
                    row['__domain'] = expression.AND([row['__domain'], [(fullname, '=', False)]])
                    row['__range'] = {}
                    continue

                # Date / Datetime are not JSONifiable, so they are stored as raw text
                db_format = '%Y-%m-%d' if property_type == 'date' else '%Y-%m-%d %H:%M:%S'

                if func == 'week':
                    # the value is the first day of the week (based on local)
                    start = row[group].strftime(db_format)
                    end = (row[group] + datetime.timedelta(days=7)).strftime(db_format)
                else:
                    start = (date_utils.start_of(row[group], func)).strftime(db_format)
                    end = (date_utils.end_of(row[group], func) + datetime.timedelta(minutes=1)).strftime(db_format)

                row['__domain'] = expression.AND([
                    row['__domain'],
                    [(fullname, '>=', start), (fullname, '<', end)],
                ])
                row['__range'] = {group: {'from': start, 'to': end}}
                row[group] = babel.dates.format_date(
                    row[group],
                    format=READ_GROUP_DISPLAY_FORMAT[func],
                    locale=get_lang(self.env).code
                )
        else:
            for row in rows_dict:
                row['__domain'] = expression.AND([row['__domain'], [(fullname, '=', row[fullname])]])

    @api.model
    def _read_group_get_annoted_groupby(self, groupby, lazy):
        groupby = [groupby] if isinstance(groupby, str) else groupby
        lazy_groupby = groupby[:1] if lazy else groupby

        annoted_groupby = {}  # Key as the name in the result, value as the explicit groupby specification
        for group_spec in lazy_groupby:
            field_name, property_name, granularity = parse_read_group_spec(group_spec)
            if field_name not in self._fields:
                raise ValueError(f"Invalid field {field_name!r} on model {self._name!r}")
            field = self._fields[field_name]
            if property_name and field.type != 'properties':
                raise ValueError(f"Property name {property_name!r} has to be used on a property field.")
            if field.type in ('date', 'datetime'):
                annoted_groupby[group_spec] = f"{field_name}:{granularity or 'month'}"
            else:
                annoted_groupby[group_spec] = group_spec
        return annoted_groupby

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Get the list of records in list view grouped by the given ``groupby`` fields.

        :param list domain: :ref:`A search domain <reference/orm/domains>`. Use an empty
                     list to match all records.
        :param list fields: list of fields present in the list view specified on the object.
                Each element is either 'field' (field name, using the default aggregation),
                or 'field:agg' (aggregate field with aggregation function 'agg'),
                or 'name:agg(field)' (aggregate field with 'agg' and return it as 'name').
                The possible aggregation functions are the ones provided by
                `PostgreSQL <https://www.postgresql.org/docs/current/static/functions-aggregate.html>`_
                and 'count_distinct', with the expected meaning.
        :param list groupby: list of groupby descriptions by which the records will be grouped.
                A groupby description is either a field (then it will be grouped by that field)
                or a string 'field:granularity'. Right now, the only supported granularities
                are 'day', 'week', 'month', 'quarter' or 'year', and they only make sense for
                date/datetime fields.
        :param int offset: optional number of groups to skip
        :param int limit: optional max number of groups to return
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
                    * __range: (date/datetime only) dictionary with field_name:granularity as keys
                        mapping to a dictionary with keys: "from" (inclusive) and "to" (exclusive)
                        mapping to a string representation of the temporal bounds of the group
        :rtype: [{'field_name_1': value, ...}, ...]
        :raise AccessError: if user is not allowed to access requested information
        """

        groupby = [groupby] if isinstance(groupby, str) else groupby
        lazy_groupby = groupby[:1] if lazy else groupby

        # Compatibility layer with _read_group, it should be remove in the second part of the refactoring
        # - Modify `groupby` default value 'month' into specifique groupby specification
        # - Modify `fields` into aggregates specification of _read_group
        # - Modify the order to be compatible with the _read_group specification
        annoted_groupby = self._read_group_get_annoted_groupby(groupby, lazy=lazy)

        annoted_aggregates = {  # Key as the name in the result, value as the explicit aggregate specification
            f"{lazy_groupby[0].split(':')[0]}_count" if lazy and len(lazy_groupby) == 1 else '__count': '__count',
        }
        for field_spec in fields:
            if field_spec == '__count':
                continue
            match = regex_field_agg.match(field_spec)
            if not match:
                raise ValueError(f"Invalid field specification {field_spec!r}.")
            name, func, fname = match.groups()

            if fname:  # Manage this kind of specification : "field_min:min(field)"
                annoted_aggregates[name] = f"{fname}:{func}"
                continue
            if func:  # Manage this kind of specification : "field:min"
                annoted_aggregates[name] = f"{name}:{func}"
                continue

            if name not in self._fields:
                raise ValueError(f"Invalid field {name!r} on model {self._name!r}")
            field = self._fields[name]
            if field.base_field.store and field.base_field.column_type and field.group_operator and field_spec not in annoted_groupby:
                annoted_aggregates[name] = f"{name}:{field.group_operator}"

        if orderby:
            new_terms = []
            for order_term in orderby.split(','):
                order_term = order_term.strip()
                for key_name, annoted in itertools.chain(reversed(annoted_groupby.items()), annoted_aggregates.items()):
                    key_name = key_name.split(':')[0]
                    if order_term.startswith(f'{key_name} ') or key_name == order_term:
                        order_term = order_term.replace(key_name, annoted)
                        break
                new_terms.append(order_term)
            orderby = ','.join(new_terms)
        else:
            orderby = ','.join(annoted_groupby.values())

        rows = self._read_group(domain, annoted_groupby.values(), annoted_aggregates.values(), offset=offset, limit=limit, order=orderby)
        rows_dict = [
            dict(zip(itertools.chain(annoted_groupby, annoted_aggregates), row))
            for row in rows
        ]

        fill_temporal = self.env.context.get('fill_temporal')
        if lazy_groupby and (rows_dict and fill_temporal) or isinstance(fill_temporal, dict):
            # fill_temporal = {} is equivalent to fill_temporal = True
            # if fill_temporal is a dictionary and there is no data, there is a chance that we
            # want to display empty columns anyway, so we should apply the fill_temporal logic
            if not isinstance(fill_temporal, dict):
                fill_temporal = {}
            # TODO Shouldn't be possible with a limit
            rows_dict = self._read_group_fill_temporal(
                rows_dict, lazy_groupby,
                annoted_aggregates, **fill_temporal,
            )

        if lazy_groupby and lazy:
            # Right now, read_group only fill results in lazy mode (by default).
            # If you need to have the empty groups in 'eager' mode, then the
            # method _read_group_fill_results need to be completely reimplemented
            # in a sane way
            # TODO Shouldn't be possible with a limit or the limit should be in account
            rows_dict = self._read_group_fill_results(
                domain, lazy_groupby[0],
                annoted_aggregates, rows_dict, read_group_order=orderby,
            )

        for row in rows_dict:
            row['__domain'] = domain
            if len(lazy_groupby) < len(groupby):
                row['__context'] = {'group_by': groupby[len(lazy_groupby):]}

        self._read_group_format_result(rows_dict, lazy_groupby)

        return rows_dict

    @api.model
    def _inherits_join_calc(self, alias, fname, query):
        """
        Adds missing table select and join clause(s) to ``query`` for reaching
        the field coming from an '_inherits' parent table (no duplicates).

        :param alias: name of the initial SQL alias
        :param fname: name of inherited field to reach
        :param query: query object on which the JOIN should be added
        :return: qualified name of field, to be used in SELECT clause

        .. deprecated:: 17.0
            Deprecated method, use _field_to_sql() instead
        """
        warnings.warn("Deprecated method _inherits_join_calc(), _field_to_sql() instead", DeprecationWarning, 2)
        sql = self._field_to_sql(alias, fname, query)
        return self.env.cr.mogrify(sql).decode()

    def _field_to_sql(self, alias: str, fname: str, query: (Query | None) = None) -> SQL:
        """ Return an :class:`SQL` object that represents the value of the given
        field from the given table alias, in the context of the given query.
        The query object is necessary for inherited fields, many2one fields and
        properties fields, where joins are added to the query.
        """
        full_fname = fname
        property_name = None
        if '.' in fname:
            fname, property_name = fname.split('.', 1)

        field = self._fields[fname]
        if field.inherited:
            # retrieve the parent model where field is inherited from
            parent_model = self.env[field.related_field.model_name]
            parent_fname = field.related.split('.')[0]
            # LEFT JOIN parent_model._table AS parent_alias ON alias.parent_fname = parent_alias.id
            parent_alias = query.make_alias(alias, parent_fname)
            query.add_join('LEFT JOIN', parent_alias, parent_model._table, SQL(
                "%s = %s",
                self._field_to_sql(alias, parent_fname, query),
                SQL.identifier(parent_alias, 'id'),
            ))
            # delegate to the parent model
            return parent_model._field_to_sql(parent_alias, full_fname, query)

        if not field.store:
            raise ValueError(f"Cannot convert field {field} to SQL")

        if field.type == 'many2many':
            # special case for many2many fields: prepare a query on the comodel
            # in order to reuse the mechanism _apply_ir_rules, then inject the
            # query as an extra condition of the left join
            comodel = self.env[field.comodel_name]
            coquery = comodel._where_calc([], active_test=False)
            comodel._apply_ir_rules(coquery)
            # LEFT JOIN {field.relation} AS rel_alias ON
            #     alias.id = rel_alias.{field.column1}
            #     AND rel_alias.{field.column2} IN ({coquery})
            rel_alias = query.make_alias(alias, field.name)
            condition = SQL(
                "%s = %s",
                SQL.identifier(alias, 'id'),
                SQL.identifier(rel_alias, field.column1),
            )
            if coquery.where_clause:
                condition = SQL(
                    "%s AND %s IN %s",
                    condition,
                    SQL.identifier(rel_alias, field.column2),
                    coquery.subselect(),
                )
            query.add_join("LEFT JOIN", rel_alias, field.relation, condition)
            return SQL.identifier(rel_alias, field.column2)

        elif field.translate and not self.env.context.get('prefetch_langs'):
            sql_field = SQL.identifier(alias, fname)
            langs = field.get_translation_fallback_langs(self.env)
            sql_field_langs = [SQL("%s->>%s", sql_field, lang) for lang in langs]
            if len(sql_field_langs) == 1:
                return sql_field_langs[0]
            return SQL("COALESCE(%s)", SQL(", ").join(sql_field_langs))

        elif field.type == 'properties' and property_name:
            return self._field_properties_to_sql(alias, fname, property_name, query)

        return SQL.identifier(alias, fname)

    def _field_properties_to_sql(self, alias: str, fname: str, property_name: str,
                                 query: Query) -> SQL:
        definition = self.get_property_definition(f"{fname}.{property_name}")
        property_type = definition.get('type')

        sql_field = self._field_to_sql(alias, fname, query)
        sql_property = SQL("%s -> %s", sql_field, property_name)

        # JOIN on the JSON array
        if property_type in ('tags', 'many2many'):
            property_alias = query.make_alias(alias, f'{fname}_{property_name}')
            sql_property = SQL(
                """ CASE
                        WHEN jsonb_typeof(%(property)s) = 'array'
                        THEN %(property)s
                        ELSE '[]'::jsonb
                     END """,
                property=sql_property,
            )
            if property_type == 'tags':
                # ignore invalid tags
                tags = [tag[0] for tag in definition.get('tags') or []]
                # `->>0 : convert "JSON string" into string
                condition = SQL(
                    "%s->>0 = ANY(%s::text[])",
                    SQL.identifier(property_alias), tags,
                )
            else:
                comodel = self.env.get(definition.get('comodel'))
                if comodel is None or comodel._transient or comodel._abstract:
                    raise UserError(_(
                                            "You cannot use %(property_name)r because the linked %(model_name)r model doesn't exist or is invalid",
                        property_name=definition.get('string', property_name), model_name=definition.get('comodel'),
                    ))

                # check the existences of the many2many
                condition = SQL(
                    "%s::int IN (SELECT id FROM %s)",
                    SQL.identifier(property_alias), SQL.identifier(comodel._table),
                )

            query.add_join(
                "LEFT JOIN",
                property_alias,
                SQL("jsonb_array_elements(%s)", sql_property),
                condition,
            )

            return SQL.identifier(property_alias)

        elif property_type == 'selection':
            options = [option[0] for option in definition.get('selection') or ()]

            # check the existence of the option
            property_alias = query.make_alias(alias, f'{fname}_{property_name}')
            query.add_join(
                "LEFT JOIN",
                property_alias,
                SQL("(SELECT unnest(%s::text[]) %s)", options, SQL.identifier(property_alias)),
                SQL("%s->>0 = %s", sql_property, SQL.identifier(property_alias)),
            )

            return SQL.identifier(property_alias)

        elif property_type == 'many2one':
            comodel = self.env.get(definition.get('comodel'))
            if comodel is None or comodel._transient or comodel._abstract:
                raise UserError(_(
                    "You cannot use %(property_name)r because the linked %(model_name)r model doesn't exist or is invalid",
                    property_name=definition.get('string', property_name), model_name=definition.get('comodel'),
                ))

            return SQL(
                """ CASE
                        WHEN jsonb_typeof(%(property)s) = 'number'
                         AND (%(property)s)::int IN (SELECT id FROM %(table)s)
                        THEN %(property)s
                        ELSE NULL
                     END """,
                property=sql_property,
                table=SQL.identifier(comodel._table),
            )

        elif property_type == 'date':
            return SQL(
                """ CASE
                        WHEN jsonb_typeof(%(property)s) = 'string'
                        THEN (%(property)s->>0)::DATE
                        ELSE NULL
                     END """,
                property=sql_property,
            )

        elif property_type == 'datetime':
            return SQL(
                """ CASE
                        WHEN jsonb_typeof(%(property)s) = 'string'
                        THEN to_timestamp(%(property)s->>0, 'YYYY-MM-DD HH24:MI:SS')
                        ELSE NULL
                     END """,
                property=sql_property,
            )

        # if the key is not present in the dict, fallback to false instead of none
        return SQL("COALESCE(%s, 'false')", sql_property)

    @api.model
    def get_property_definition(self, full_name):
        """Return the definition of the given property.

        :param full_name: Name of the field / property
            (e.g. "property.integer")
        """
        self.check_access_rights("read")
        field_name, property_name = full_name.split(".")
        check_property_field_value_name(property_name)
        if field_name not in self._fields:
            raise ValueError(f"Wrong field name {field_name!r}.")

        field = self._fields[field_name]
        target_model = self.env[self._fields[field.definition_record].comodel_name]
        self.env.cr.execute(SQL(
            """ SELECT definition
                  FROM %(table)s, jsonb_array_elements(%(field)s) definition
                 WHERE %(field)s IS NOT NULL AND definition->>'name' = %(name)s
                 LIMIT 1 """,
            table=SQL.identifier(target_model._table),
            field=SQL.identifier(field.definition_record_field),
            name=property_name,
        ))
        result = self.env.cr.dictfetchone()
        return result["definition"] if result else {}

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
        query = SQL(
            """ WITH RECURSIVE __parent_store_compute(id, parent_path) AS (
                    SELECT row.id, concat(row.id, '/')
                    FROM %(table)s row
                    WHERE row.%(parent)s IS NULL
                UNION
                    SELECT row.id, concat(comp.parent_path, row.id, '/')
                    FROM %(table)s row, __parent_store_compute comp
                    WHERE row.%(parent)s = comp.id
                )
                UPDATE %(table)s row SET parent_path = comp.parent_path
                FROM __parent_store_compute comp
                WHERE row.id = comp.id """,
            table=SQL.identifier(self._table),
            parent=SQL.identifier(self._parent_name),
        )
        self.env.cr.execute(query)
        self.invalidate_model(['parent_path'])
        return True

    def _check_removed_columns(self, log=False):
        if self._abstract:
            return
        # iterate on the database columns to drop the NOT NULL constraints of
        # fields which were required but have been removed (or will be added by
        # another module)
        cr = self._cr
        cols = [name for name, field in self._fields.items()
                     if field.store and field.column_type]
        cr.execute(SQL(
            """ SELECT a.attname, a.attnotnull
                  FROM pg_class c, pg_attribute a
                 WHERE c.relname=%s
                   AND c.oid=a.attrelid
                   AND a.attisdropped=%s
                   AND pg_catalog.format_type(a.atttypid, a.atttypmod) NOT IN ('cid', 'tid', 'oid', 'xid')
                   AND a.attname NOT IN %s """,
            self._table, False, tuple(cols),
        ))

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
            self._cr.execute(SQL(
                "UPDATE %(table)s SET %(field)s = %(value)s WHERE %(field)s IS NULL",
                table=SQL.identifier(self._table),
                field=SQL.identifier(column_name),
                value=value,
            ))

    @ormcache()
    def _table_has_rows(self):
        """ Return whether the model's table has rows. This method should only
            be used when updating the database schema (:meth:`~._auto_init`).
        """
        self.env.cr.execute(SQL('SELECT 1 FROM %s LIMIT 1', SQL.identifier(self._table)))
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
                    (field.name, make_type(field), field.string)
                    for field in sorted(self._fields.values(), key=lambda f: f.column_order)
                    if field.name != 'id' and field.store and field.column_type
                ])

            if self._parent_store:
                if not tools.column_exists(cr, self._table, 'parent_path'):
                    tools.create_column(self._cr, self._table, 'parent_path', 'VARCHAR')
                    parent_path_compute = True
                self._check_parent_path()

            if not must_create_table:
                self._check_removed_columns(log=False)

            # update the database schema for fields
            columns = tools.table_columns(cr, self._table)
            fields_to_compute = []

            for field in sorted(self._fields.values(), key=lambda f: f.column_order):
                if not field.store:
                    continue
                if field.manual and not update_custom_fields:
                    continue            # don't update custom fields
                new = field.update_db(self, columns)
                if new and field.compute:
                    fields_to_compute.append(field)

            if fields_to_compute:
                # mark existing records for computation now, so that computed
                # required fields are flushed before the NOT NULL constraint is
                # added to the database
                cr.execute(SQL('SELECT id FROM %s', SQL.identifier(self._table)))
                records = self.browse(row[0] for row in cr.fetchall())
                if records:
                    for field in fields_to_compute:
                        _logger.info("Prepare computation of %s", field)
                        self.env.add_to_compute(field, records)

        if self._auto:
            self._add_sql_constraints()

        if parent_path_compute:
            self._parent_store_compute()

    def init(self):
        """ This method is called after :meth:`~._auto_init`, and may be
            overridden to create or modify a model's database schema.
        """

    def _check_parent_path(self):
        field = self._fields.get('parent_path')
        if field is None:
            _logger.error("add a field parent_path on model %r: `parent_path = fields.Char(index=True, unaccent=False)`.", self._name)
        elif not field.index:
            _logger.error('parent_path field on model %r should be indexed! Add index=True to the field definition.', self._name)
        elif field.unaccent:
            _logger.warning("parent_path field on model %r should have unaccent disabled. Add `unaccent=False` to the field definition.", self._name)

    def _add_sql_constraints(self):
        """ Modify this model's database table constraints so they match the one
        in _sql_constraints.

        """
        cr = self._cr
        foreign_key_re = re.compile(r'\s*foreign\s+key\b.*', re.I)

        for (key, definition, message) in self._sql_constraints:
            conname = '%s_%s' % (self._table, key)
            if len(conname) > 63:
                hashed_conname = tools.make_identifier(conname)
                current_definition = tools.constraint_definition(cr, self._table, hashed_conname)
                if not current_definition:
                    _logger.info("Constraint name %r has more than 63 characters, internal PG identifier is %r", conname, hashed_conname)
                conname = hashed_conname
            else:
                current_definition = tools.constraint_definition(cr, self._table, conname)
            if current_definition == definition:
                continue

            if current_definition:
                # constraint exists but its definition may have changed
                tools.drop_constraint(cr, self._table, conname)

            if not definition:
                # virtual constraint (e.g. implemented by a custom index)
                self.pool.post_init(tools.check_index_exist, cr, conname)
            elif foreign_key_re.match(definition):
                self.pool.post_init(tools.add_constraint, cr, self._table, conname, definition)
            else:
                self.pool.post_constraint(tools.add_constraint, cr, self._table, conname, definition)

    #
    # Update objects that use this one to update their _inherits fields
    #

    @api.model
    def _add_inherited_fields(self):
        """ Determine inherited fields. """
        if self._abstract or not self._inherits:
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
                Field = type(field)
                self._add_field(name, Field(
                    inherited=True,
                    inherited_field=field,
                    related=f"{parent_fname}.{name}",
                    related_sudo=False,
                    copy=field.copy,
                    readonly=field.readonly,
                    export_string_translation=field.export_string_translation,
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
            elif not (field.required and (field.ondelete or "").lower() in ("cascade", "restrict")):
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
                self.pool[self._name]._inherits = {**self._inherits, field.comodel_name: field.name}
                self.pool[field.comodel_name]._inherits_children.add(self._name)

    @api.model
    def _prepare_setup(self):
        """ Prepare the setup of the model. """
        cls = self.env.registry[self._name]
        cls._setup_done = False

        # changing base classes is costly, do it only when necessary
        if cls.__bases__ != cls.__base_classes:
            cls.__bases__ = cls.__base_classes

        # reset those attributes on the model's class for _setup_fields() below
        for attr in ('_rec_name', '_active_name'):
            discardattr(cls, attr)

    @api.model
    def _setup_base(self):
        """ Determine the inherited and custom fields of the model. """
        cls = self.env.registry[self._name]
        if cls._setup_done:
            return

        # the classes that define this model, i.e., the ones that are not
        # registry classes; the purpose of this attribute is to behave as a
        # cache of [c for c in cls.mro() if not is_registry_class(c))], which
        # is heavily used in function fields.resolve_mro()
        cls._model_classes = tuple(c for c in cls.mro() if getattr(c, 'pool', None) is None)

        # 1. determine the proper fields of the model: the fields defined on the
        # class and magic fields, not the inherited or custom ones

        # retrieve fields from parent classes, and duplicate them on cls to
        # avoid clashes with inheritance between different models
        for name in cls._fields:
            discardattr(cls, name)
        cls._fields.clear()

        # collect the definitions of each field (base definition + overrides)
        definitions = defaultdict(list)
        for klass in reversed(cls._model_classes):
            # this condition is an optimization of is_definition_class(klass)
            if isinstance(klass, MetaModel):
                for field in klass._field_definitions:
                    definitions[field.name].append(field)
        for name, fields_ in definitions.items():
            if f'{cls._name}.{name}' in cls.pool._database_translated_fields:
                # the field is currently translated in the database; ensure the
                # field is translated to avoid converting its column to varchar
                # and losing data
                translate = next((
                    field.args['translate'] for field in reversed(fields_) if 'translate' in field.args
                ), False)
                if not translate:
                    # patch the field definition by adding an override
                    _logger.debug("Patching %s.%s with translate=True", cls._name, name)
                    fields_.append(type(fields_[0])(translate=True))
            if len(fields_) == 1 and fields_[0]._direct and fields_[0].model_name == cls._name:
                cls._fields[name] = fields_[0]
            else:
                Field = type(fields_[-1])
                self._add_field(name, Field(_base_fields=fields_))

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
        cls._setup_done = True

        for field in cls._fields.values():
            field.prepare_setup()

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
        cls = self.env.registry[self._name]

        # set up fields
        bad_fields = []
        for name, field in cls._fields.items():
            try:
                field.setup(self)
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
        cls = self.env.registry[self._name]

        # register constraints and onchange methods
        cls._init_constraints_onchanges()

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """ fields_get([allfields][, attributes])

        Return the definition of each field.

        The returned value is a dictionary (indexed by field name) of
        dictionaries. The _inherits'd fields are included. The string, help,
        and selection (if present) attributes are translated.

        :param list allfields: fields to document, all if empty or not provided
        :param list attributes: attributes to return for each field, all if empty or not provided
        :return: dictionary mapping field names to a dictionary mapping attributes to values.
        :rtype: dict
        """
        res = {}
        for fname, field in self._fields.items():
            if allfields and fname not in allfields:
                continue
            if field.groups and not self.env.su and not self.user_has_groups(field.groups):
                continue

            description = field.get_description(self.env, attributes=attributes)
            res[fname] = description

        return res

    @api.model
    def check_field_access_rights(self, operation, field_names):
        """Check the user access rights on the given fields.

        :param str operation: one of ``create``, ``read``, ``write``, ``unlink``
        :param field_names: names of the fields
        :type field_names: list or None
        :return: provided fields if fields is truthy (or the fields
          readable by the current user).
        :rtype: list
        :raise AccessError: if the user is not allowed to access
          the provided fields.
        """
        if self.env.su:
            return field_names or list(self._fields)

        def valid(fname):
            """ determine whether user has access to field ``fname`` """
            field = self._fields.get(fname)
            if field and field.groups:
                return self.user_has_groups(field.groups)
            else:
                return True

        if not field_names:
            field_names = [name for name in self._fields if valid(name)]
        else:
            invalid_fields = {name for name in field_names if not valid(name)}
            if invalid_fields:
                _logger.info('Access Denied by ACLs for operation: %s, uid: %s, model: %s, fields: %s',
                             operation, self._uid, self._name, ', '.join(invalid_fields))

                description = self.env['ir.model']._get(self._name).name
                if not self.env.user.has_group('base.group_no_one'):
                    raise AccessError(_(
                        "You do not have enough rights to access the fields \"%(fields)s\""
                        " on %(document_kind)s (%(document_model)s). "
                        "Please contact your system administrator."
                        "\n\n(Operation: %(operation)s)",
                        fields=','.join(list(invalid_fields)),
                        document_kind=description,
                        document_model=self._name,
                        operation=operation,
                    ))

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
                        strs.append(_(
                            "allowed for groups %s",
                            ', '.join(
                                anyof.sorted(lambda g: g.id)
                                    .mapped(lambda g: repr(g.display_name))
                            ),
                        ))
                    if noneof:
                        strs.append(_(
                            "forbidden for groups %s",
                            ', '.join(
                                noneof.sorted(lambda g: g.id)
                                    .mapped(lambda g: repr(g.display_name))
                            ),
                        ))
                    return '; '.join(strs)

                raise AccessError(_(
                    "The requested operation can not be completed due to security restrictions."
                    "\n\nDocument type: %(document_kind)s (%(document_model)s)"
                    "\nOperation: %(operation)s"
                    "\nUser: %(user)s"
                    "\nFields:"
                    "\n%(fields_list)s",
                    document_model=self._name,
                    document_kind=description or self._name,
                    operation=operation,
                    user=self._uid,
                    fields_list='\n'.join(
                        '- %s (%s)' % (f, format_groups(self._fields[f]))
                        for f in sorted(invalid_fields)
                    ),
                ))

        return field_names

    def read(self, fields=None, load='_classic_read'):
        """ read([fields])

        Read the requested fields for the records in ``self``, and return their
        values as a list of dicts.

        :param list fields: field names to return (default is all fields)
        :param str load: loading mode, currently the only option is to set to
            ``None`` to avoid loading the `display_name` of m2o fields
        :return: a list of dictionaries mapping field names to their values,
                 with one dictionary per record
        :rtype: list
        :raise AccessError: if user is not allowed to access requested information
        :raise ValueError: if a requested field does not exist

        This is a high-level method that is not supposed to be overridden. In
        order to modify how fields are read from database, see methods
        :meth:`_fetch_query` and :meth:`_read_format`.
        """
        fields = self.check_field_access_rights('read', fields)
        self._origin.fetch(fields)
        return self._read_format(fnames=fields, load=load)

    def update_field_translations(self, field_name, translations):
        """ Update the values of a translated field.

        :param str field_name: field name
        :param dict translations: if the field has ``translate=True``, it should be a dictionary
            like ``{lang: new_value}``; if ``translate`` is a callable, it should be like
            ``{lang: {old_term: new_term}}``
        """
        return self._update_field_translations(field_name, translations)

    def _update_field_translations(self, field_name, translations, digest=None):
        """ Private implementation of :meth:`~update_field_translations`.
        The main difference comes from the extra function ``digest``, which may
        be used to make identifiers for old terms.

        :param dict translations:
            if the field has ``translate=True``, it should be a dictionary like ``{lang: new_value}``
                new_value: str: the new translation for lang
                new_value: False: void the current translation for lang and fallback to current en_US value
            if ``translate`` is a callable, it should be like
            ``{lang: {old_term: new_term}}``, or ``{lang: {digest(old_term): new_term}}`` when ``digest`` is callable
                new_value: str: the new translation of old_term for lang
        :param digest: an optional digest function for the old_term
        """
        self.ensure_one()

        self.check_access_rights('write')
        self.check_field_access_rights('write', [field_name])
        self.check_access_rule('write')

        valid_langs = set(code for code, _ in self.env['res.lang'].get_installed()) | {'en_US'}
        missing_langs = set(translations) - valid_langs
        if missing_langs:
            raise UserError(
                _("The following languages are not activated: %(missing_names)s",
                missing_names=', '.join(missing_langs))
            )

        field = self._fields[field_name]

        if not field.translate:
            return False  # or raise error

        if not field.store and not field.related and field.compute:
            # a non-related non-stored computed field cannot be translated, even if it has inverse function
            return False

        # Strictly speaking, a translated related/computed field cannot be stored
        # because the compute function only support one language
        # `not field.store` is a redundant logic.
        # But some developers store translated related fields.
        # In these cases, only all translations of the first stored translation field will be updated
        # For other stored related translated field, the translation for the flush language will be updated
        if field.related and not field.store:
            related_path, field_name = field.related.rsplit(".", 1)
            return self.mapped(related_path)._update_field_translations(field_name, translations, digest)

        if field.translate is True:
            # falsy values (except emtpy str) are used to void the corresponding translation
            if any(translation and not isinstance(translation, str) for translation in translations.values()):
                raise UserError(_("Translations for model translated fields only accept falsy values and str"))
            value_en = translations.get('en_US', True)
            if not value_en and value_en != '':
                translations.pop('en_US')
            translations = {
                lang: translation if isinstance(translation, str) else None
                for lang, translation in translations.items()
            }
            if not translations:
                return False

            translation_fallback = translations['en_US'] if translations.get('en_US') is not None \
                else translations[self.env.lang] if translations.get(self.env.lang) is not None \
                else next((v for v in translations.values() if v is not None), None)
            self.invalidate_recordset([field_name])
            self._cr.execute(SQL(
                """ UPDATE %(table)s
                    SET %(field)s = NULLIF(
                        jsonb_strip_nulls(%(fallback)s || COALESCE(%(field)s, '{}'::jsonb) || %(value)s),
                        '{}'::jsonb)
                    WHERE id = %(id)s
                """,
                table=SQL.identifier(self._table),
                field=SQL.identifier(field_name),
                fallback=Json({'en_US': translation_fallback}),
                value=Json(translations),
                id=self.id,
            ))
            self.modified([field_name])
        else:
            # Note:
            # update terms in 'en_US' will not change its value other translated values
            # record_en = Model_en.create({'html': '<div>English 1</div><div>English 2<div/>'
            # record_en.update_field_translations('html', {'fr_FR': {'English 2': 'French 2'}}
            # record_en.update_field_translations('html', {'en_US': {'English 1': 'English 3'}}
            # assert record_en                            == '<div>English 3</div><div>English 2<div/>'
            # assert record_fr.with_context(lang='fr_FR') == '<div>English 1</div><div>French 2<div/>'
            # assert record_nl.with_context(lang='nl_NL') == '<div>English 3</div><div>English 2<div/>'

            stored_translations = field._get_stored_translations(self)
            if not stored_translations:
                return False
            old_translations = {
                k: stored_translations.get(f'_{k}', v)
                for k, v in stored_translations.items()
                if not k.startswith('_')
            }
            for lang, translation in translations.items():
                old_value = old_translations.get(lang) or old_translations.get('en_US')
                if digest:
                    old_terms = field.get_trans_terms(old_value)
                    old_terms_digested2value = {digest(old_term): old_term for old_term in old_terms}
                    translation = {
                        old_terms_digested2value[key]: value
                        for key, value in translation.items()
                        if key in old_terms_digested2value
                    }
                stored_translations[lang] = field.translate(translation.get, old_value)
                stored_translations.pop(f'_{lang}', None)
            self.env.cache.update_raw(self, field, [stored_translations], dirty=True)

        # the following write is incharge of
        # 1. mark field as modified
        # 2. execute logics in the override `write` method
        # 3. update write_date of the record if exists to support 't-cache'
        # even if the value in cache is the same as the value written
        self[field_name] = self[field_name]
        return True

    def get_field_translations(self, field_name, langs=None):
        """ get model/model_term translations for records
        :param str field_name: field name
        :param list langs: languages

        :return: (translations, context) where
            translations: list of dicts like [{"lang": lang, "source": source_term, "value": value_term}]
            context: {"translation_type": "text"/"char", "translation_show_source": True/False}
        """
        self.ensure_one()
        field = self._fields[field_name]
        # We don't forbid reading inactive/non-existing languages,
        langs = set(langs or [l[0] for l in self.env['res.lang'].get_installed()])
        self_lang = self.with_context(check_translations=True, prefetch_langs=True)
        val_en = self_lang.with_context(lang='en_US')[field_name]
        if not field.translate:
            translations = []
        elif field.translate is True:
            translations = [{
                'lang': lang,
                'source': val_en,
                'value': self_lang.with_context(lang=lang)[field_name]
            } for lang in langs]
        else:
            translation_dictionary = field.get_translation_dictionary(
                val_en, {lang: self_lang.with_context(lang=lang)[field_name] for lang in langs}
            )
            translations = [{
                'lang': lang,
                'source': term_en,
                'value': term_lang if term_lang != term_en else ''
            } for term_en, translations in translation_dictionary.items()
                for lang, term_lang in translations.items()]
        context = {}
        context['translation_type'] = 'text' if field.type in ['text', 'html'] else 'char'
        context['translation_show_source'] = callable(field.translate)

        return translations, context

    def _get_base_lang(self):
        """ Returns the base language of the record. """
        self.ensure_one()
        return 'en_US'

    def _read_format(self, fnames, load='_classic_read'):
        """Returns a list of dictionaries mapping field names to their values,
        with one dictionary per record that exists.

        The output format is the one expected from the `read` method, which uses
        this method as its implementation for formatting values.

        For the properties fields, call convert_to_read_multi instead of convert_to_read
        to prepare everything (record existences, display name, etc) in batch.

        The current method is different from `read` because it retrieves its
        values from the cache without doing a query when it is avoidable.
        """
        data = [(record, {'id': record.id}) for record in self]
        use_display_name = (load == '_classic_read')
        for name in fnames:
            field = self._fields[name]
            if field.type == 'properties':
                values_list = []
                records = []
                for record, vals in data:
                    try:
                        values_list.append(record[name])
                        records.append(record.id)
                    except MissingError:
                        vals.clear()

                results = field.convert_to_read_multi(values_list, self.browse(records))
                for record_read_vals, convert_result in zip(data, results):
                    record_read_vals[1][name] = convert_result
                continue

            convert = field.convert_to_read
            for record, vals in data:
                # missing records have their vals empty
                if not vals:
                    continue
                try:
                    vals[name] = convert(record[name], record, use_display_name)
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
                # select fields with the same prefetch group
                if f.prefetch == field.prefetch
                # discard fields with groups that the user may not access
                if not (f.groups and not self.user_has_groups(f.groups))
            ]
            if field.name not in fnames:
                fnames.append(field.name)
        else:
            fnames = [field.name]
        self.fetch(fnames)

    def fetch(self, field_names):
        """ Make sure the given fields are in memory for the records in ``self``,
        by fetching what is necessary from the database.  Non-stored fields are
        mostly ignored, except for their stored dependencies. This method should
        be called to optimize code.

        :param field_names: a collection of field names to fetch
        :raise AccessError: if user is not allowed to access requested information

        This method is implemented thanks to methods :meth:`_search` and
        :meth:`_fetch_query`, and should not be overridden.
        """
        if not self or not field_names:
            return

        fields_to_fetch = self._determine_fields_to_fetch(field_names, ignore_when_in_cache=True)

        if not fields_to_fetch:
            # there is nothing to fetch, but we expect an error anyway in case
            # self is not accessible
            self.check_access_rights('read')
            try:
                self.check_access_rule('read')
            except MissingError:
                # Method fetch() should never raise a MissingError, but method
                # check_access_rule() can, because it must read fields on self.
                # So we restrict 'self' to existing records (to avoid an extra
                # exists() at the end of the method).
                self.exists().check_access_rule('read')
            return

        # first determine a query that satisfies the domain and access rules
        if any(field.column_type for field in fields_to_fetch):
            query = self.with_context(active_test=False)._search([('id', 'in', self.ids)])
        else:
            self.check_access_rights('read')
            try:
                self.check_access_rule('read')
            except MissingError:
                # Method fetch() should never raise a MissingError, but method
                # check_access_rule() can, because it must read fields on self.
                # So we restrict 'self' to existing records (to avoid an extra
                # exists() at the end of the method).
                self = self.exists()
                self.check_access_rule('read')
            query = self._as_query(ordered=False)

        # fetch the fields
        fetched = self._fetch_query(query, fields_to_fetch)

        # possibly raise exception for the records that could not be read
        if fetched != self:
            forbidden = (self - fetched).exists()
            if forbidden:
                raise self.env['ir.rule']._make_access_error('read', forbidden)

    def _determine_fields_to_fetch(self, field_names, ignore_when_in_cache=False) -> List["Field"]:
        """
        Return the fields to fetch from database among the given field names,
        and following the dependencies of computed fields. The method is used
        by :meth:`fetch` and :meth:`search_fetch`.

        :param field_names: the list of fields requested
        :param ignore_when_in_cache: whether to ignore fields that are alreay in cache for ``self``
        :return: the list of fields that must be fetched
        """
        if not field_names:
            return []

        cache = self.env.cache

        fields_to_fetch = []
        field_names_todo = deque(self.check_field_access_rights('read', field_names))
        field_names_done = {'id'}  # trick: ignore 'id'

        while field_names_todo:
            field_name = field_names_todo.popleft()
            if field_name in field_names_done:
                continue
            field_names_done.add(field_name)
            field = self._fields.get(field_name)
            if not field:
                raise ValueError(f"Invalid field {field_name!r} on model {self._name!r}")
            if ignore_when_in_cache and not any(cache.get_missing_ids(self, field)):
                # field is already in cache: don't fetch it
                continue
            if field.store:
                fields_to_fetch.append(field)
            else:
                # optimization: fetch field dependencies
                for dotname in self.pool.field_depends[field]:
                    dep_field = self._fields[dotname.split('.', 1)[0]]
                    if (not dep_field.store) or (dep_field.prefetch is True and (
                        not dep_field.groups or self.user_has_groups(dep_field.groups)
                    )):
                        field_names_todo.append(dep_field.name)

        return fields_to_fetch

    def _fetch_query(self, query, fields):
        """ Fetch the given fields (iterable of :class:`Field` instances) from
        the given query, put them in cache, and return the fetched records.

        This method may be overridden to change what fields to actually fetch,
        or to change the values that are put in cache.
        """

        # determine columns fields and those with their own read() method
        column_fields = OrderedSet()
        other_fields = OrderedSet()
        for field in fields:
            if field.name == 'id':
                continue
            assert field.store
            (column_fields if field.column_type else other_fields).add(field)

        # necessary to retrieve the en_US value of fields without a translation
        context = self.env.context
        field_names_to_flush = [
            field.name for field in column_fields
            if field.translate or (
                field.type == 'binary'
                and (context.get('bin_size') or context.get('bin_size_' + field.name))
            )
        ]
        if field_names_to_flush:
            self.flush_model(field_names_to_flush)

        if column_fields:
            # the query may involve several tables: we need fully-qualified names
            sql_terms = [SQL.identifier(self._table, 'id')]
            for field in column_fields:
                sql = self._field_to_sql(self._table, field.name, query)
                if field.type == 'binary' and (
                        context.get('bin_size') or context.get('bin_size_' + field.name)):
                    # PG 9.2 introduces conflicting pg_size_pretty(numeric) -> need ::cast
                    sql = SQL("pg_size_pretty(length(%s)::bigint)", sql)
                sql_terms.append(sql)

            # select the given columns from the rows in the query
            self.env.cr.execute(query.select(*sql_terms))
            rows = self.env.cr.fetchall()

            if not rows:
                return self.browse()

            # rows = [(id1, a1, b1), (id2, a2, b2), ...]
            # column_values = [(id1, id2, ...), (a1, a2, ...), (b1, b2, ...)]
            column_values = zip(*rows)
            ids = next(column_values)
            fetched = self.browse(ids)

            # If we assume that the value of a pending update is in cache, we
            # can avoid flushing pending updates if the fetched values do not
            # overwrite values in cache.
            for field in column_fields:
                values = next(column_values)
                # store values in cache, but without overwriting
                self.env.cache.insert_missing(fetched, field, values)

        else:
            fetched = self.browse(query)

        # process non-column fields
        if fetched:
            for field in other_fields:
                field.read(fetched)

        return fetched

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
            * xmlids: list of dict with xmlid in format ``module.name``, and noupdate as boolean
            * noupdate: A boolean telling if the record will be updated or not
        """

        IrModelData = self.env['ir.model.data'].sudo()
        if self._log_access:
            res = self.read(LOG_ACCESS_COLUMNS)
        else:
            res = [{'id': x} for x in self.ids]


        xml_data = defaultdict(list)
        imds = IrModelData.search_read(
            [('model', '=', self._name), ('res_id', 'in', self.ids)],
            ['res_id', 'noupdate', 'module', 'name'],
            order='id DESC'
        )
        for imd in imds:
            xml_data[imd['res_id']].append({
                'xmlid': "%s.%s" % (imd['module'], imd['name']),
                'noupdate': imd['noupdate'],
            })

        for r in res:
            main = xml_data.get(r['id'], [{}])[-1]
            r['xmlid'] = main.get('xmlid', False)
            r['noupdate'] = main.get('noupdate', False)
            r['xmlids'] = xml_data.get(r['id'], [])[::-1]
        return res

    def get_base_url(self):
        """ Return rooturl for a specific record.

        By default, it returns the ir.config.parameter of base_url
        but it can be overridden by model.

        :return: the base url for this record
        :rtype: str
        """
        if len(self) > 1:
            raise ValueError("Expected singleton or no record: %s" % self)
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url')

    def _check_company_domain(self, companies):
        """Domain to be used for company consistency between records regarding this model.

        :param companies: the allowed companies for the related record
        :type companies: BaseModel or list or tuple or int or unquote
        """
        if not companies:
            return [('company_id', '=', False)]
        return ['|', ('company_id', '=', False), ('company_id', 'in', to_company_ids(companies))]

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
        if fnames is None or 'company_id' in fnames:
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
                if corecord:
                    domain = corecord._check_company_domain(company)
                    if domain and not corecord.with_context(active_test=False).filtered_domain(domain):
                        inconsistencies.append((record, name, corecord))
            # The second part of the check (for property / company-dependent fields) verifies that the records
            # linked via those relation fields are compatible with the company that owns the property value, i.e.
            # the company for which the value is being assigned, i.e:
            #      `self.property_account_payable_id.company_id == self.env.company
            company = self.env.company
            for name in property_fields:
                corecord = record.sudo()[name]
                if corecord:
                    domain = corecord._check_company_domain(company)
                    if domain and not corecord.with_context(active_test=False).filtered_domain(domain):
                        inconsistencies.append((record, name, corecord))

        if inconsistencies:
            lines = [_("Incompatible companies on records:")]
            company_msg = _lt("- Record is company %(company)r and %(field)r (%(fname)s: %(values)s) belongs to another company.")
            record_msg = _lt("- %(record)r belongs to company %(company)r and %(field)r (%(fname)s: %(values)s) belongs to another company.")
            root_company_msg = _lt("- Only a root company can be set on %(record)r. Currently set to %(company)r")
            for record, name, corecords in inconsistencies[:5]:
                if record._name == 'res.company':
                    msg, company = company_msg, record
                elif record == corecords and name == 'company_id':
                    msg, company = root_company_msg, record.company_id
                else:
                    msg, company = record_msg, record.company_id
                field = self.env['ir.model.fields']._get(self._name, name)
                lines.append(str(msg) % {
                    'record': record.display_name,
                    'company': company.display_name,
                    'field': field.field_description,
                    'fname': field.name,
                    'values': ", ".join(repr(rec.display_name) for rec in corecords),
                })
            raise UserError("\n".join(lines))

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        """ Verify that the given operation is allowed for the current user accord to ir.model.access.

        :param str operation: one of ``create``, ``read``, ``write``, ``unlink``
        :param bool raise_exception: whether an exception should be raise if operation is forbidden
        :return: whether the operation is allowed
        :rtype: bool
        :raise AccessError: if the operation is forbidden and raise_exception is True
        """
        return self.env['ir.model.access'].check(self._name, operation, raise_exception)

    def check_access_rule(self, operation):
        """ Verify that the given operation is allowed for the current user according to ir.rules.

        :param str operation: one of ``create``, ``read``, ``write``, ``unlink``
        :return: None if the operation is allowed
        :raise UserError: if current ``ir.rules`` do not permit this operation.
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

        # determine ids in database that satisfy ir.rules
        self._flush_search([])
        query.add_where(SQL("%s IN %s", SQL.identifier(self._table, 'id'), tuple(self.ids)))
        self._cr.execute(query.select())
        valid_ids = {row[0] for row in self._cr.fetchall()}

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

        Deletes the records in ``self``.

        :raise AccessError: if the user is not allowed to delete all the given records
        :raise UserError: if the record is default property for other records
        """
        if not self:
            return True

        self.check_access_rights('unlink')
        self.check_access_rule('unlink')

        from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
        for func in self._ondelete_methods:
            # func._ondelete is True if it should be called during uninstallation
            if func._ondelete or not self._context.get(MODULE_UNINSTALL_FLAG):
                func(self)

        # TOFIX: this avoids an infinite loop when trying to recompute a
        # field, which triggers the recomputation of another field using the
        # same compute function, which then triggers again the computation
        # of those two fields
        for field in self._fields.values():
            self.env.remove_to_compute(field, self)

        self.env.flush_all()

        cr = self._cr
        Data = self.env['ir.model.data'].sudo().with_context({})
        Defaults = self.env['ir.default'].sudo()
        Property = self.env['ir.property'].sudo()
        Attachment = self.env['ir.attachment'].sudo()
        ir_property_unlink = Property
        ir_model_data_unlink = Data
        ir_attachment_unlink = Attachment

        # mark fields that depend on 'self' to recompute them after 'self' has
        # been deleted (like updating a sum of lines after deleting one line)
        with self.env.protecting(self._fields.values(), self):
            self.modified(self._fields, before=True)

        for sub_ids in cr.split_for_in_conditions(self.ids):
            records = self.browse(sub_ids)

            # Check if the records are used as default properties.
            refs = [f'{self._name},{id_}' for id_ in sub_ids]
            default_properties = Property.search([('res_id', '=', False), ('value_reference', 'in', refs)])
            if not self._context.get(MODULE_UNINSTALL_FLAG) and default_properties:
                raise UserError(_('Unable to delete this document because it is used as a default property'))
            else:
                ir_property_unlink |= default_properties

            # Delete the records' properties.
            ir_property_unlink |= Property.search([('res_id', 'in', refs)])

            cr.execute(SQL(
                "DELETE FROM %s WHERE id IN %s",
                SQL.identifier(self._table), sub_ids,
            ))

            # Removing the ir_model_data reference if the record being deleted
            # is a record created by xml/csv file, as these are not connected
            # with real database foreign keys, and would be dangling references.
            #
            # Note: the following steps are performed as superuser to avoid
            # access rights restrictions, and with no context to avoid possible
            # side-effects during admin calls.
            data = Data.search([('model', '=', self._name), ('res_id', 'in', sub_ids)])
            ir_model_data_unlink |= data

            # For the same reason, remove the defaults having some of the
            # records as value
            Defaults.discard_records(records)

            # For the same reason, remove the relevant records in ir_attachment
            # (the search is performed with sql as the search method of
            # ir_attachment is overridden to hide attachments of deleted
            # records)
            cr.execute(SQL(
                "SELECT id FROM ir_attachment WHERE res_model=%s AND res_id IN %s",
                self._name, sub_ids,
            ))
            ir_attachment_unlink |= Attachment.browse(row[0] for row in cr.fetchall())

        # invalidate the *whole* cache, since the orm does not handle all
        # changes made in the database, like cascading delete!
        self.env.invalidate_all(flush=False)
        if ir_property_unlink:
            ir_property_unlink.unlink()
        if ir_model_data_unlink:
            ir_model_data_unlink.unlink()
        if ir_attachment_unlink:
            ir_attachment_unlink.unlink()

        # auditing: deletions are infrequent and leave no trace in the database
        _unlink.info('User #%s deleted %s records with IDs: %r', self._uid, self._name, self.ids)

        return True

    def write(self, vals):
        """ write(vals)

        Updates all records in ``self`` with the provided values.

        :param dict vals: fields to update and the value to set on them
        :raise AccessError: if user is not allowed to modify the specified records/fields
        :raise ValidationError: if invalid values are specified for selection fields
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
        * The expected value of a :class:`~odoo.fields.One2many` or
          :class:`~odoo.fields.Many2many` relational field is a list of
          :class:`~odoo.fields.Command` that manipulate the relation the
          implement. There are a total of 7 commands:
          :meth:`~odoo.fields.Command.create`,
          :meth:`~odoo.fields.Command.update`,
          :meth:`~odoo.fields.Command.delete`,
          :meth:`~odoo.fields.Command.unlink`,
          :meth:`~odoo.fields.Command.link`,
          :meth:`~odoo.fields.Command.clear`, and
          :meth:`~odoo.fields.Command.set`.
        * For :class:`~odoo.fields.Date` and `~odoo.fields.Datetime`,
          the value should be either a date(time), or a string.

          .. warning::

            If a string is provided for Date(time) fields,
            it must be UTC-only and formatted according to
            :const:`odoo.tools.misc.DEFAULT_SERVER_DATE_FORMAT` and
            :const:`odoo.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT`

        * Other non-relational fields use a string for value
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

        # set magic fields
        vals = {key: val for key, val in vals.items() if key not in bad_names}
        if self._log_access:
            vals.setdefault('write_uid', self.env.uid)
            vals.setdefault('write_date', self.env.cr.now())

        field_values = []                           # [(field, value)]
        determine_inverses = defaultdict(list)      # {inverse: fields}
        fnames_modifying_relations = []
        protected = set()
        check_company = False
        for fname, value in vals.items():
            field = self._fields.get(fname)
            if not field:
                raise ValueError("Invalid field %r on model %r" % (fname, self._name))
            field_values.append((field, value))
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
            if self.pool.is_modifying_relations(field):
                fnames_modifying_relations.append(fname)
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
            self._recompute_recordset(to_compute)

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
            self.modified(fnames_modifying_relations, before=True)

            real_recs = self.filtered('id')

            # field.write_sequence determines a priority for writing on fields.
            # Monetary fields need their corresponding currency field in cache
            # for rounding values. X2many fields must be written last, because
            # they flush other fields when deleting lines.
            for field, value in sorted(field_values, key=lambda item: item[0].write_sequence):
                field.write(self, value)

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
                self.flush_model([self._parent_name])

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
                        raise AccessError(_(
                            "%(previous_message)s\n\nImplicitly accessed through '%(document_kind)s' (%(document_model)s).",
                            previous_message=e.args[0],
                            document_kind=description,
                            document_model=self._name,
                        ))
                    raise

            # validate inversed fields
            real_recs._validate_fields(inverse_fields)

        if check_company and self._check_company_auto:
            self._check_company()
        return True

    def _write(self, vals):
        """ Low-level implementation of write()

        The ids of self should be a database id and unique.
        Ignore non-existent record.
        """
        if not self:
            return

        cr = self._cr

        # determine records that require updating parent_path
        parent_records = self._parent_store_update_prepare(vals)

        if self._log_access:
            # set magic fields (already done by write(), but not for computed fields)
            vals = dict(vals)
            vals.setdefault('write_uid', self.env.uid)
            vals.setdefault('write_date', self.env.cr.now())

        # determine SQL assignments
        assignments = []

        for name, val in sorted(vals.items()):
            if self._log_access and name in LOG_ACCESS_COLUMNS and not val:
                continue
            field = self._fields[name]
            assert field.store
            assert field.column_type
            if field.translate is True and val:
                # The first param is for the fallback value {'en_US': 'first_written_value'}
                # which fills the 'en_US' key of jsonb only when the old column value is NULL.
                # The second param is for the real value {'fr_FR': 'French', 'nl_NL': 'Dutch'}
                assignments.append(SQL(
                    "%(field)s = %(fallback)s || COALESCE(%(field)s, '{}'::jsonb) || %(value)s",
                    field=SQL.identifier(name),
                    fallback=Json({} if 'en_US' in val.adapted else {'en_US': next(iter(val.adapted.values()))}),
                    value=val,
                ))
            else:
                assignments.append(SQL('%s = %s', SQL.identifier(name), val))

        # update columns
        if assignments:
            for sub_ids in cr.split_for_in_conditions(self._ids):
                cr.execute(SQL(
                    "UPDATE %s SET %s WHERE id IN %s",
                    SQL.identifier(self._table),
                    SQL(", ").join(assignments),
                    sub_ids,
                ))

        # update parent_path
        if parent_records:
            parent_records._parent_store_update()

    @api.model_create_multi
    def create(self, vals_list):
        """ create(vals_list) -> records

        Creates new records for the model.

        The new records are initialized using the values from the list of dicts
        ``vals_list``, and if necessary those from :meth:`~.default_get`.

        :param Union[list[dict], dict] vals_list:
            values for the model's fields, as a list of dictionaries::

                [{'field_name': field_value, ...}, ...]

            For backward compatibility, ``vals_list`` may be a dictionary.
            It is treated as a singleton list ``[vals]``, and a single record
            is returned.

            see :meth:`~.write` for details

        :return: the created records
        :raise AccessError: if the current user is not allowed to create records of the specified model
        :raise ValidationError: if user tries to enter invalid value for a selection field
        :raise ValueError: if a field name specified in the create values does not exist.
        :raise UserError: if a loop would be created in a hierarchy of objects a result of the operation
          (such as setting an object as its own parent)
        """
        if not vals_list:
            return self.browse()

        self = self.browse()
        self.check_access_rights('create')

        new_vals_list = self._prepare_create_values(vals_list)

        # classify fields for each record
        data_list = []
        determine_inverses = defaultdict(set)       # {inverse: fields}

        for vals in new_vals_list:
            precomputed = vals.pop('__precomputed__', ())

            # distribute fields into sets for various purposes
            data = {}
            data['stored'] = stored = {}
            data['inversed'] = inversed = {}
            data['inherited'] = inherited = defaultdict(dict)
            data['protected'] = protected = set()
            for key, val in vals.items():
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
                elif field.inverse and field not in precomputed:
                    inversed[key] = val
                    determine_inverses[field.inverse].add(field)
                # protect editable computed fields and precomputed fields
                # against (re)computation
                if field.compute and (not field.readonly or field.precompute):
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
            # call inverse method for each group of fields
            for fields in determine_inverses.values():
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
                    next(iter(fields)).determine_inverse(batch_recs)

        # check Python constraints for non-stored inversed fields
        for data in data_list:
            data['record']._validate_fields(data['inversed'], data['stored'])

        if self._check_company_auto:
            records._check_company()

        import_module = self.env.context.get('_import_current_module')
        if not import_module: # not an import -> bail
            return records

        # It is to support setting xids directly in create by
        # providing an "id" key (otherwise stripped by create) during an import
        # (which should strip 'id' from the input data anyway)
        noupdate = self.env.context.get('noupdate', False)

        xids = (v.get('id') for v in vals_list)
        self.env['ir.model.data']._update_xmlids([
            {
                'xml_id': xid if '.' in xid else ('%s.%s' % (import_module, xid)),
                'record': rec,
                # note: this is not used when updating o2ms above...
                'noupdate': noupdate,
            }
            for rec, xid in zip(records, xids)
            if xid and isinstance(xid, str)
        ])

        return records

    def _prepare_create_values(self, vals_list):
        """ Clean up and complete the given create values, and return a list of
        new vals containing:

        * default values,
        * discarded forbidden values (magic fields),
        * precomputed fields.

        :param list vals_list: List of create values
        :returns: new list of completed create values
        :rtype: dict
        """
        bad_names = ['id', 'parent_path']
        if self._log_access:
            # the superuser can set log_access fields while loading registry
            if not(self.env.uid == SUPERUSER_ID and not self.pool.ready):
                bad_names.extend(LOG_ACCESS_COLUMNS)

        # also discard precomputed readonly fields (to force their computation)
        bad_names.extend(
            fname
            for fname, field in self._fields.items()
            if field.precompute and field.readonly
        )

        result_vals_list = []
        for vals in vals_list:
            # add default values
            vals = self._add_missing_default_values(vals)

            # add magic fields
            for fname in bad_names:
                vals.pop(fname, None)
            if self._log_access:
                vals.setdefault('create_uid', self.env.uid)
                vals.setdefault('create_date', self.env.cr.now())
                vals.setdefault('write_uid', self.env.uid)
                vals.setdefault('write_date', self.env.cr.now())

            result_vals_list.append(vals)

        # add precomputed fields
        self._add_precomputed_values(result_vals_list)

        return result_vals_list

    def _add_precomputed_values(self, vals_list):
        """ Add missing precomputed fields to ``vals_list`` values.
        Only applies for precompute=True fields.

        :param dict vals_list: list(dict) of create values
        """
        precomputable = {
            fname: field
            for fname, field in self._fields.items()
            if field.precompute
        }
        if not precomputable:
            return

        # determine which vals must be completed
        vals_list_todo = [
            vals
            for vals in vals_list
            if any(fname not in vals for fname in precomputable)
        ]
        if not vals_list_todo:
            return

        # create new records for the vals that must be completed
        records = self.browse().concat(*(self.new(vals) for vals in vals_list_todo))

        for record, vals in zip(records, vals_list_todo):
            vals['__precomputed__'] = precomputed = set()
            for fname, field in precomputable.items():
                if fname not in vals:
                    # computed stored fields with a column
                    # have to be computed before create
                    # s.t. required and constraints can be applied on those fields.
                    vals[fname] = field.convert_to_write(record[fname], self)
                    precomputed.add(field)

    @api.model
    def _create(self, data_list):
        """ Create records from the stored field values in ``data_list``. """
        assert data_list
        cr = self.env.cr

        # insert rows in batches of maximum INSERT_BATCH_SIZE
        ids = []                                # ids of created records
        other_fields = OrderedSet()             # non-column fields

        for data_sublist in split_every(INSERT_BATCH_SIZE, data_list):
            stored_list = [data['stored'] for data in data_sublist]
            fnames = sorted({name for stored in stored_list for name in stored})

            columns = []
            rows = [[] for _ in stored_list]
            for fname in fnames:
                field = self._fields[fname]
                if field.column_type:
                    columns.append(fname)
                    for stored, row in zip(stored_list, rows):
                        if fname in stored:
                            colval = field.convert_to_column(stored[fname], self, stored)
                            if field.translate is True and colval:
                                if 'en_US' not in colval.adapted:
                                    colval.adapted['en_US'] = next(iter(colval.adapted.values()))
                            row.append(colval)
                        else:
                            row.append(SQL_DEFAULT)
                else:
                    other_fields.add(field)

                if field.type == 'properties':
                    # force calling fields.create for properties field because
                    # we might want to update the parent definition
                    other_fields.add(field)

            if not columns:
                # manage the case where we create empty records
                columns = ['id']
                for row in rows:
                    row.append(SQL_DEFAULT)

            cr.execute(SQL(
                'INSERT INTO %s (%s) VALUES %s RETURNING "id"',
                SQL.identifier(self._table),
                SQL(', ').join(map(SQL.identifier, columns)),
                SQL(', ').join(tuple(row) for row in rows),
            ))
            ids.extend(id_ for id_, in cr.fetchall())

        # put the new records in cache, and update inverse fields, for many2one
        # (using bin_size=False to put binary values in the right place)
        #
        # cachetoclear is an optimization to avoid modified()'s cost until other_fields are processed
        cachetoclear = []
        records = self.browse(ids)
        inverses_update = defaultdict(list)     # {(field, value): ids}
        common_set_vals = set(LOG_ACCESS_COLUMNS + ['id', 'parent_path'])
        for data, record in zip(data_list, records.with_context(bin_size=False)):
            data['record'] = record
            # DLE P104: test_inherit.py, test_50_search_one2many
            vals = dict({k: v for d in data['inherited'].values() for k, v in d.items()}, **data['stored'])
            set_vals = common_set_vals.union(vals)
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
                elif field.store and field.name not in set_vals and not field.compute:
                    self.env.cache.set(record, field, field.convert_to_cache(None, record))
            for fname, value in vals.items():
                field = self._fields[fname]
                if field.type in ('one2many', 'many2many'):
                    cachetoclear.append((record, field))
                else:
                    cache_value = field.convert_to_cache(value, record)
                    self.env.cache.set(record, field, cache_value)
                    if field.type in ('many2one', 'many2one_reference') and self.pool.field_inverses[field]:
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
        return records

    def _compute_field_value(self, field):
        fields.determine(field.compute, self)

        if field.store and any(self._ids):
            # check constraints of the fields that have been computed
            fnames = [f.name for f in self.pool.field_computed[field]]
            self.filtered('id')._validate_fields(fnames)

    def _parent_store_create(self):
        """ Set the parent_path field on ``self`` after its creation. """
        if not self._parent_store:
            return

        self._cr.execute(SQL(
            """ UPDATE %(table)s node
                SET parent_path=concat((
                        SELECT parent.parent_path
                        FROM %(table)s parent
                        WHERE parent.id=node.%(parent)s
                    ), node.id, '/')
                WHERE node.id IN %(ids)s
                RETURNING node.id, node.parent_path """,
            table=SQL.identifier(self._table),
            parent=SQL.identifier(self._parent_name),
            ids=tuple(self.ids),
        ))

        # update the cache of updated nodes, and determine what to recompute
        updated = dict(self._cr.fetchall())
        records = self.browse(updated)
        self.env.cache.update(records, self._fields['parent_path'], updated.values())

    def _parent_store_update_prepare(self, vals):
        """ Return the records in ``self`` that must update their parent_path
            field. This must be called before updating the parent field.
        """
        if not self._parent_store or self._parent_name not in vals:
            return self.browse()

        # No need to recompute the values if the parent is the same.
        parent_val = vals[self._parent_name]
        if parent_val:
            condition = SQL(
                "(%(parent)s != %(value)s OR %(parent)s IS NULL)",
                parent=SQL.identifier(self._parent_name),
                value=parent_val,
            )
        else:
            condition = SQL(
                "%(parent)s IS NOT NULL",
                parent=SQL.identifier(self._parent_name),
            )
        self._cr.execute(SQL(
            "SELECT id FROM %s WHERE id IN %s AND %s",
            SQL.identifier(self._table),
            tuple(self.ids),
            condition,
        ))
        return self.browse([row[0] for row in self._cr.fetchall()])

    def _parent_store_update(self):
        """ Update the parent_path field of ``self``. """
        cr = self.env.cr

        # determine new prefix of parent_path
        cr.execute(SQL(
            """ SELECT parent.parent_path
                FROM %(table)s node, %(table)s parent
                WHERE node.id = %(id)s AND parent.id = node.%(parent)s """,
            table=SQL.identifier(self._table),
            parent=SQL.identifier(self._parent_name),
            id=self.ids[0],
        ))
        prefix = cr.fetchone()[0] if cr.rowcount else ''

        # check for recursion
        if prefix:
            parent_ids = {int(label) for label in prefix.split('/')[:-1]}
            if not parent_ids.isdisjoint(self._ids):
                raise UserError(_("Recursion Detected."))

        # update parent_path of all records and their descendants
        cr.execute(SQL(
            """ UPDATE %(table)s child
                SET parent_path = concat(%(prefix)s, substr(child.parent_path,
                        length(node.parent_path) - length(node.id || '/') + 1))
                FROM %(table)s node
                WHERE node.id IN %(ids)s
                AND child.parent_path LIKE concat(node.parent_path, %(wildcard)s)
                RETURNING child.id, child.parent_path """,
            table=SQL.identifier(self._table),
            prefix=prefix,
            ids=tuple(self.ids),
            wildcard='%',
        ))

        # update the cache of updated nodes, and determine what to recompute
        updated = dict(cr.fetchall())
        records = self.browse(updated)
        self.env.cache.update(records, self._fields['parent_path'], updated.values())
        records.modified(['parent_path'])

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
            if self._name != d_model:
                raise ValidationError(
                    f"For external id {xml_id} "
                    f"when trying to create/update a record of model {self._name} "
                    f"found record of different model {d_model} ({d_id})"
                )
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

        if self.env.context.get('import_file'):
            existing_modules = self.env['ir.module.module'].sudo().search([]).mapped('name')
            for data in to_create:
                xml_id = data.get('xml_id')
                if xml_id:
                    module_name, sep, record_id = xml_id.partition('.')
                    if sep and module_name in existing_modules:
                        raise UserError(
                            _("The record %(xml_id)s has the module prefix %(module_name)s. This is the part before the '.' in the external id. Because the prefix refers to an existing module, the record would be deleted when the module is upgraded. Use either no prefix and no dot or a prefix that isn't an existing module. For example, __import__, resulting in the external id __import__.%(record_id)s.",
                              xml_id=xml_id, module_name=module_name, record_id=record_id))

        # create records
        if to_create:
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

        :param list domain: the domain to compute
        :param bool active_test: whether the default filtering of records with
            ``active`` field set to ``False`` should be applied.
        :return: the query expressing the given domain as provided in domain
        :rtype: Query
        """
        # if the object has an active field ('active', 'x_active'), filter out all
        # inactive records unless they were explicitly asked for
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
                "Invalid \"order\" specified (%s)."
                " A valid \"order\" specification is a comma-separated list of valid field names"
                " (optionally followed by asc/desc for the direction)",
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

    def _order_to_sql(self, order: str, query: Query, alias: (str | None) = None,
                      reverse: bool = False) -> SQL:
        """ Return an :class:`SQL` object that represents the given ORDER BY
        clause, without the ORDER BY keyword.
        """
        order = order or self._order
        if not order:
            return []
        self._check_qorder(order)

        alias = alias or self._table

        terms = []
        for order_part in order.split(','):
            order_match = regex_order.match(order_part)
            field_name = order_match['field']

            property_name = order_match['property']
            if property_name:
                field_name = f"{field_name}.{property_name}"

            direction = (order_match['direction'] or '').upper()
            nulls = (order_match['nulls'] or '').upper()
            if reverse:
                direction = 'ASC' if direction == 'DESC' else 'DESC'
                if nulls:
                    nulls = 'NULLS LAST' if nulls == 'NULLS FIRST' else 'NULLS FIRST'

            sql_direction = SQL(direction) if direction in ('ASC', 'DESC') else SQL()
            sql_nulls = SQL(nulls) if nulls in ('NULLS FIRST', 'NULLS LAST') else SQL()

            term = self._order_field_to_sql(alias, field_name, sql_direction, sql_nulls, query)
            if term:
                terms.append(term)

        return SQL(", ").join(terms)

    def _order_field_to_sql(self, alias: str, field_name: str, direction: SQL,
                            nulls: SQL, query: Query) -> SQL:
        """ Return an :class:`SQL` object that represents the ordering by the
        given field.

        :param direction: one of ``SQL("ASC")``, ``SQL("DESC")``, ``SQL()``
        :param nulls: one of ``SQL("NULLS FIRST")``, ``SQL("NULLS LAST")``, ``SQL()``
        """
        full_name = field_name
        property_name = None
        if '.' in field_name:
            field_name, property_name = field_name.split('.', 1)

        field = self._fields.get(field_name)
        if not field:
            raise ValueError(f"Invalid field {field_name!r} on model {self._name!r}")

        if property_name and field.type != 'properties':
            raise ValueError(f'Order a property ({property_name!r}) on a non-properties field ({field_name!r})')

        if field.inherited:
            # delegate to the parent model via a join
            parent_model = self.env[field.related_field.model_name]
            parent_fname = field.related.split('.')[0]
            parent_alias = query.make_alias(alias, parent_fname)
            query.add_join('LEFT JOIN', parent_alias, parent_model._table, SQL(
                "%s = %s",
                self._field_to_sql(alias, parent_fname, query),
                SQL.identifier(parent_alias, 'id'),
            ))
            return parent_model._order_field_to_sql(parent_alias, full_name, direction, nulls, query)

        if not (field.store and field.column_type):
            _logger.warning("Model %r cannot be sorted on field %r (not a column)", self._name, field_name)
            return

        if field.type == 'many2one':
            seen = self.env.context.get('__m2o_order_seen', ())
            if field in seen:
                return
            self = self.with_context(__m2o_order_seen=frozenset((field, *seen)))

            # figure out the applicable order_by for the m2o
            comodel = self.env[field.comodel_name]
            coorder = comodel._order
            if not regex_order.match(coorder):
                # _order is complex, can't use it here, so we default to _rec_name
                coorder = comodel._rec_name

            if coorder == 'id':
                sql_field = self._field_to_sql(alias, field_name, query)
                return SQL("%s %s %s", sql_field, direction, nulls)

            # instead of ordering by the field's raw value, use the comodel's
            # order on many2one values
            terms = []
            if nulls.code == 'NULLS FIRST':
                terms.append(SQL("%s IS NOT NULL", self._field_to_sql(alias, field_name, query)))
            elif nulls.code == 'NULLS LAST':
                terms.append(SQL("%s IS NULL", self._field_to_sql(alias, field_name, query)))

            # LEFT JOIN the comodel table, in order to include NULL values, too
            coalias = query.make_alias(alias, field_name)
            query.add_join('LEFT JOIN', coalias, comodel._table, SQL(
                "%s = %s",
                self._field_to_sql(alias, field_name, query),
                SQL.identifier(coalias, 'id'),
            ))

            # delegate the order to the comodel
            reverse = direction.code == 'DESC'
            term = comodel._order_to_sql(coorder, query, alias=coalias, reverse=reverse)
            if term:
                terms.append(term)
            return SQL(", ").join(terms)

        sql_field = self._field_to_sql(alias, field_name, query)
        if field.type == 'boolean':
            sql_field = SQL("COALESCE(%s, FALSE)", sql_field)
        elif field.type == 'properties' and property_name:
            sql_field = SQL("(%s -> %s)", sql_field, property_name)

        return SQL("%s %s %s", sql_field, direction, nulls)

    @api.model
    def _generate_order_by(self, order_spec, query):
        """
        Attempt to construct an appropriate ORDER BY clause based on order_spec, which must be
        a comma-separated list of valid field names, optionally followed by an ASC or DESC direction.

        :raise ValueError in case order_spec is malformed

        .. deprecated:: 17.0
            Deprecated method, use _order_to_sql() instead
        """
        warnings.warn("Deprecated method _generate_order_by(), _order_to_sql() instead", DeprecationWarning, 2)
        sql = self._order_to_sql(order_spec, query)
        order_by_clause = self.env.cr.mogrify(sql).decode()
        return order_by_clause and (' ORDER BY %s ' % order_by_clause) or ''

    @api.model
    def _flush_search(self, domain, fields=None, order=None, seen=None):
        """ Flush all the fields appearing in `domain`, `fields` and `order`.

        Note that ``order=None`` actually means no order, so if you expect some
        fallback order, you have to provide it yourself.
        """
        if seen is None:
            seen = set()
        elif self._name in seen:
            return
        seen.add(self._name)

        to_flush = defaultdict(OrderedSet)             # {model_name: field_names}
        if fields:
            to_flush[self._name].update(fields)

        def collect_from_domain(model, domain):
            for arg in domain:
                if isinstance(arg, str):
                    continue
                if not isinstance(arg[0], str):
                    continue
                comodel = collect_from_path(model, arg[0])
                if arg[1] in ('child_of', 'parent_of') and comodel._parent_store:
                    # hierarchy operators need the parent field
                    collect_from_path(comodel, comodel._parent_name)
                if arg[1] in ('any', 'not any'):
                    collect_from_domain(comodel, arg[2])

        def collect_from_path(model, path):
            # path is a dot-separated sequence of field names
            for fname in path.split('.'):
                field = model._fields.get(fname)
                if not field:
                    break
                to_flush[model._name].add(fname)
                if field.type == 'one2many' and field.inverse_name:
                    to_flush[field.comodel_name].add(field.inverse_name)
                    field_domain = field.get_domain_list(model)
                    if field_domain:
                        collect_from_domain(self.env[field.comodel_name], field_domain)
                # DLE P111: `test_message_process_email_partner_find`
                # Search on res.users with email_normalized in domain
                # must trigger the recompute and flush of res.partner.email_normalized
                if field.related:
                    # DLE P129: `test_transit_multi_companies`
                    # `self.env['stock.picking'].search([('product_id', '=', product.id)])`
                    # Should flush `stock.move.picking_ids` as `product_id` on `stock.picking` is defined as:
                    # `product_id = fields.Many2one('product.product', 'Product', related='move_lines.product_id', readonly=False)`
                    collect_from_path(model, field.related)
                if field.relational:
                    model = self.env[field.comodel_name]
            # return the model found by traversing all fields (used in collect_from_domain)
            return model

        # flush the order fields
        if order:
            for order_part in order.split(','):
                order_field = order_part.split()[0]
                field = self._fields.get(order_field)
                if field is not None:
                    to_flush[self._name].add(order_field)
                    if field.relational:
                        comodel = self.env[field.comodel_name]
                        comodel._flush_search([], order=comodel._order, seen=seen)

        if self._active_name and self.env.context.get('active_test', True):
            to_flush[self._name].add(self._active_name)

        collect_from_domain(self, domain)

        # Check access of fields with groups
        for model_name, field_names in to_flush.items():
            self.env[model_name].check_field_access_rights('read', field_names)

        # also take into account the fields in the record rules
        if ir_rule_domain := self.env['ir.rule']._compute_domain(self._name, 'read'):
            collect_from_domain(self, ir_rule_domain)

        # flush model dependencies (recursively)
        if self._depends:
            models = [self]
            while models:
                model = models.pop()
                for model_name, field_names in model._depends.items():
                    to_flush[model_name].update(field_names)
                    models.append(self.env[model_name])

        for model_name, field_names in to_flush.items():
            self.env[model_name].flush_model(field_names)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        """
        Private implementation of search() method, allowing specifying the uid to use for the access right check.
        This is useful for example when filling in the selection list for a drop-down and avoiding access rights errors,
        by specifying ``access_rights_uid=1`` to bypass access rights check, but not ir.rules!
        This is ok at the security level because this method is private and not callable through XML-RPC.

        No default order is applied when the method is invoked without parameter ``order``.

        :param access_rights_uid: optional user ID to use when checking access rights
                                  (not for ir.rules, this is only for ir.model.access)
        :return: a :class:`Query` object that represents the matching records

        This method may be overridden to modify the domain being searched, or to
        do some post-filtering of the resulting query object. Be careful with
        the latter option, though, as it might hurt performance. Indeed, by
        default the returned query object is not actually executed, and it can
        be injected as a value in a domain in order to generate sub-queries.
        """
        model = self.with_user(access_rights_uid) if access_rights_uid else self
        model.check_access_rights('read')

        if expression.is_false(self, domain):
            # optimization: no need to query, as no record satisfies the domain
            return self.browse()._as_query()

        # the flush must be done before the _where_calc(), as the latter can do some selects
        self._flush_search(domain, order=order)

        query = self._where_calc(domain)
        self._apply_ir_rules(query, 'read')

        if order:
            query.order = self._order_to_sql(order, query)
        query.limit = limit
        query.offset = offset

        return query

    def _as_query(self, ordered=True):
        """ Return a :class:`Query` that corresponds to the recordset ``self``.
        This method is convenient for making a query object with a known result.

        :param ordered: whether the recordset order must be enforced by the query
        """
        query = Query(self.env.cr, self._table, self._table_query)
        query.set_result_ids(self._ids, ordered)
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

        blacklist_given_fields(self)

        fields_to_copy = {name: field
                          for name, field in self._fields.items()
                          if field.copy and name not in default and name not in blacklist}

        for name, field in fields_to_copy.items():
            if field.type == 'one2many':
                # duplicate following the order of the ids because we'll rely on
                # it later for copying translations in copy_translation()!
                lines = [rec.copy_data()[0] for rec in self[name].sorted(key='id')]
                # the lines are duplicated using the wrong (old) parent, but then are
                # reassigned to the correct one thanks to the (Command.CREATE, 0, ...)
                default[name] = [Command.create(line) for line in lines if line]
            elif field.type == 'many2many':
                default[name] = [Command.set(self[name].ids)]
            else:
                default[name] = field.convert_to_write(self[name], self)

        return [default]

    def copy_translations(self, new, excluded=()):
        """ Recursively copy the translations from original to new record

        :param self: the original record
        :param new: the new record (copy of the original one)
        :param excluded: a container of user-provided field names
        """
        old = self
        # avoid recursion through already copied records in case of circular relationship
        if '__copy_translations_seen' not in old._context:
            old = old.with_context(__copy_translations_seen=defaultdict(set))
        seen_map = old._context['__copy_translations_seen']
        if old.id in seen_map[old._name]:
            return
        seen_map[old._name].add(old.id)
        valid_langs = set(code for code, _ in self.env['res.lang'].get_installed()) | {'en_US'}

        for name, field in old._fields.items():
            if not field.copy:
                continue

            if field.inherited and field.related.split('.')[0] in excluded:
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

            elif field.translate and field.store and name not in excluded and old[name]:
                # for translatable fields we copy their translations
                old_stored_translations = field._get_stored_translations(old)
                if not old_stored_translations:
                    continue
                lang = self.env.lang or 'en_US'
                if field.translate is True:
                    new.update_field_translations(name, {
                        k: v for k, v in old_stored_translations.items() if k in valid_langs and k != lang
                    })
                else:
                    old_translations = {
                        k: old_stored_translations.get(f'_{k}', v)
                        for k, v in old_stored_translations.items()
                        if k in valid_langs
                    }
                    # {from_lang_term: {lang: to_lang_term}
                    translation_dictionary = field.get_translation_dictionary(
                        old_translations.pop(lang, old_translations['en_US']),
                        old_translations
                    )
                    # {lang: {old_term: new_term}}
                    translations = defaultdict(dict)
                    for from_lang_term, to_lang_terms in translation_dictionary.items():
                        for lang, to_lang_term in to_lang_terms.items():
                            translations[lang][from_lang_term] = to_lang_term
                    new.update_field_translations(name, translations)

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
        record_copy = self.create(vals)
        self.with_context(from_copy_translation=True).copy_translations(record_copy, excluded=default or ())

        return record_copy

    @api.returns('self')
    def copy_multi(self, default=None):
        """ copy_multi(default=None)

        Duplicate records in ``self`` updating it with default values

        :param dict default: dictionary of field values to override in the
               original values of the copied records, e.g: ``{'field_name': overridden_value, ...}``
        :returns: new records

        """
        return self.browse([record.copy(default).id for record in self])

    @api.returns('self')
    def exists(self):
        """  exists() -> records

        Returns the subset of records in ``self`` that exist.
        It can be used as a test on records::

            if record.exists():
                ...

        By convention, new records are returned as existing.
        """
        new_ids, ids = partition(lambda i: isinstance(i, NewId), self._ids)
        if not ids:
            return self
        query = Query(self.env.cr, self._table, self._table_query)
        query.add_where(SQL("%s IN %s", SQL.identifier(self._table, 'id'), tuple(ids)))
        self.env.cr.execute(query.select())
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
        self.flush_model([parent])
        for id in self.ids:
            current_id = id
            seen_ids = {current_id}
            while current_id:
                cr.execute(SQL(
                    "SELECT %s FROM %s WHERE id = %s",
                    SQL.identifier(parent), SQL.identifier(self._table), current_id,
                ))
                result = cr.fetchone()
                current_id = result[0] if result else None
                if current_id in seen_ids:
                    return False
                seen_ids.add(current_id)
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

        self.flush_model([field_name])

        cr = self._cr
        succs = defaultdict(set)        # transitive closure of successors
        preds = defaultdict(set)        # transitive closure of predecessors
        todo, done = set(self.ids), set()
        while todo:
            # retrieve the respective successors of the nodes in 'todo'
            cr.execute(SQL(
                """ SELECT %(col1)s, %(col2)s FROM %(rel)s
                    WHERE %(col1)s IN %(ids)s AND %(col2)s IS NOT NULL """,
                rel=SQL.identifier(field.relation),
                col1=SQL.identifier(field.column1),
                col2=SQL.identifier(field.column2),
                ids=tuple(todo),
            ))
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
        result = defaultdict(list)
        domain = [('model', '=', self._name), ('res_id', 'in', self.ids)]
        for data in self.env['ir.model.data'].sudo().search_read(domain, ['module', 'name', 'res_id'], order='id'):
            result[data['res_id']].append('%(module)s.%(name)s' % data)
        return {
            record.id: result[record._origin.id]
            for record in self
        }

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

    @classmethod
    def is_transient(cls):
        """ Return whether the model is transient.

        See :class:`TransientModel`.

        """
        return cls._transient

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, **read_kwargs):
        """ Perform a :meth:`search_fetch` followed by a :meth:`_read_format`.

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
        :param read_kwargs: All read keywords arguments used to call
            ``read(..., **read_kwargs)`` method e.g. you can use
            ``search_read(..., load='')`` in order to avoid computing display_name
        :return: List of dictionaries containing the asked fields.
        :rtype: list(dict).
        """
        fields = self.check_field_access_rights('read', fields)
        records = self.search_fetch(domain or [], fields, offset=offset, limit=limit, order=order)

        # Method _read_format() ignores 'active_test', but it would forward it
        # to any downstream search call(e.g. for x2m or computed fields), and
        # this is not the desired behavior. The flag was presumably only meant
        # for the main search().
        if 'active_test' in self._context:
            context = dict(self._context)
            del context['active_test']
            records = records.with_context(context)

        return records._read_format(fnames=fields, **read_kwargs)

    def toggle_active(self):
        "Inverses the value of :attr:`active` on the records in ``self``."
        active_recs = self.filtered(self._active_name)
        active_recs[self._active_name] = False
        (self - active_recs)[self._active_name] = True

    def action_archive(self):
        """Sets :attr:`active` to ``False`` on a recordset, by calling
         :meth:`toggle_active` on its currently active records.
        """
        return self.filtered(lambda record: record[self._active_name]).toggle_active()

    def action_unarchive(self):
        """Sets :attr:`active` to ``True`` on a recordset, by calling
        :meth:`toggle_active` on its currently inactive records.
        """
        return self.filtered(lambda record: not record[self._active_name]).toggle_active()

    def _register_hook(self):
        """ stuff to do right after the registry is built """

    def _unregister_hook(self):
        """ Clean up what `~._register_hook` has done. """

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

    def __init__(self, env, ids, prefetch_ids):
        """ Create a recordset instance.

        :param env: an environment
        :param ids: a tuple of record ids
        :param prefetch_ids: a reversible iterable of record ids (for prefetching)
        """
        self.env = env
        self._ids = ids
        self._prefetch_ids = prefetch_ids

    def browse(self, ids=None):
        """ browse([ids]) -> records

        Returns a recordset for the ids provided as parameter in the current
        environment.

        .. code-block:: python

            self.browse([7, 18, 12])
            res.partner(7, 18, 12)

        :param ids: id(s)
        :type ids: int or iterable(int) or None
        :return: recordset
        """
        if not ids:
            ids = ()
        elif ids.__class__ is int:
            ids = (ids,)
        else:
            ids = tuple(ids)
        return self.__class__(self.env, ids, ids)

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
        """Verify that the current recordset holds a single record.

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

        .. note::
            The returned recordset has the same prefetch object as ``self``.
        """
        return self.__class__(env, self._ids, self._prefetch_ids)

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

            The returned recordset has the same prefetch object as ``self``.

        """
        assert isinstance(flag, bool)
        if flag == self.env.su:
            return self
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
        allowed_company_ids = self.env.context.get('allowed_company_ids') or []
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
        """ with_context([context][, **overrides]) -> Model

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
        """  # noqa: RST210
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
        return self.__class__(self.env, self._ids, prefetch_ids)

    def _update_cache(self, values, validate=True):
        """ Update the cache of ``self`` with ``values``.

            :param values: dict of field values, in any format.
            :param validate: whether values must be checked
        """
        self.ensure_one()
        cache = self.env.cache
        fields = self._fields
        try:
            field_values = [(fields[name], value) for name, value in values.items() if name != 'id']
        except KeyError as e:
            raise ValueError("Invalid field %r on model %r" % (e.args[0], self._name))

        # convert monetary fields after other columns for correct value rounding
        for field, value in sorted(field_values, key=lambda item: item[0].write_sequence):
            value = field.convert_to_cache(value, self, validate)
            cache.set(self, field, value, check_dirty=False)

            # set inverse fields on new records in the comodel
            if field.relational:
                inv_recs = self[field.name].filtered(lambda r: not r.id)
                if not inv_recs:
                    continue
                # we need to adapt the value of the inverse fields to integrate self into it:
                # x2many fields should add self, while many2one fields should replace with self
                for invf in self.pool.field_inverses[field]:
                    invf._update(inv_recs, self)

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
        return self.browse([rec.id for rec in self if func(rec)])

    def grouped(self, key):
        """Eagerly groups the records of ``self`` by the ``key``, returning a
        dict from the ``key``'s result to recordsets. All the resulting
        recordsets are guaranteed to be part of the same prefetch-set.

        Provides a convenience method to partition existing recordsets without
        the overhead of a :meth:`~.read_group`, but performs no aggregation.

        .. note:: unlike :func:`itertools.groupby`, does not care about input
                  ordering, however the tradeoff is that it can not be lazy

        :param key: either a callable from a :class:`Model` to a (hashable)
                    value, or a field name. In the latter case, it is equivalent
                    to ``itemgetter(key)`` (aka the named field's value)
        :type key: callable | str
        :rtype: dict
        """
        if isinstance(key, str):
            key = itemgetter(key)

        collator = defaultdict(list)
        for record in self:
            collator[key(record)].extend(record._ids)

        browse = functools.partial(type(self), self.env, prefetch_ids=self._prefetch_ids)
        return {key: browse(tuple(ids)) for key, ids in collator.items()}

    def filtered_domain(self, domain):
        """Return the records in ``self`` satisfying the domain and keeping the same order.

        :param domain: :ref:`A search domain <reference/orm/domains>`.
        """
        if not domain or not self:
            return self

        stack = []
        for leaf in reversed(domain):
            if leaf == '|':
                stack.append(stack.pop() | stack.pop())
            elif leaf == '!':
                stack.append(set(self._ids) - stack.pop())
            elif leaf == '&':
                stack.append(stack.pop() & stack.pop())
            elif leaf == expression.TRUE_LEAF:
                stack.append(set(self._ids))
            elif leaf == expression.FALSE_LEAF:
                stack.append(set())
            else:
                (key, comparator, value) = leaf
                if comparator in ('child_of', 'parent_of'):
                    if key == 'company_id':  # avoid an explicit search
                        value_companies = self.env['res.company'].browse(value)
                        if comparator == 'child_of':
                            stack.append({record.id for record in self if record.company_id.parent_ids & value_companies})
                        else:
                            stack.append({record.id for record in self if record.company_id & value_companies.parent_ids})
                    else:
                        stack.append(set(self.with_context(active_test=False).search([('id', 'in', self.ids), leaf], order='id')._ids))
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
                if comparator in ('in', 'not in'):
                    if isinstance(value, (list, tuple)):
                        value = set(value)
                    else:
                        value = (value,)
                    if field and field.type in ('date', 'datetime'):
                        value = {Datetime.to_datetime(v) for v in value}
                elif field and field.type in ('date', 'datetime'):
                    value = Datetime.to_datetime(value)

                matching_ids = set()
                for record in self:
                    data = record.mapped(key)
                    if isinstance(data, BaseModel) and comparator not in ('any', 'not any'):
                        v = value
                        if isinstance(value, (list, tuple, set)) and value:
                            v = next(iter(value))
                        if isinstance(v, str):
                            data = data.mapped('display_name')
                        else:
                            data = data and data.ids or [False]
                    elif field and field.type in ('date', 'datetime'):
                        data = [Datetime.to_datetime(d) for d in data]

                    if comparator == '=':
                        ok = value in data
                    elif comparator == '!=':
                        ok = value not in data
                    elif comparator == '=?':
                        ok = not value or (value in data)
                    elif comparator == 'in':
                        ok = value and any(x in value for x in data)
                    elif comparator == 'not in':
                        ok = not (value and any(x in value for x in data))
                    elif comparator == '<':
                        ok = any(x is not None and x < value for x in data)
                    elif comparator == '>':
                        ok = any(x is not None and x > value for x in data)
                    elif comparator == '<=':
                        ok = any(x is not None and x <= value for x in data)
                    elif comparator == '>=':
                        ok = any(x is not None and x >= value for x in data)
                    elif comparator == 'ilike':
                        data = [(x or "").lower() for x in data]
                        ok = fnmatch.filter(data, '*' + (value_esc or '').lower() + '*')
                    elif comparator == 'not ilike':
                        value = value.lower()
                        ok = not any(value in (x or "").lower() for x in data)
                    elif comparator == 'like':
                        data = [(x or "") for x in data]
                        ok = fnmatch.filter(data, value and '*' + value_esc + '*')
                    elif comparator == 'not like':
                        ok = not any(value in (x or "") for x in data)
                    elif comparator == '=like':
                        data = [(x or "") for x in data]
                        ok = fnmatch.filter(data, value_esc)
                    elif comparator == '=ilike':
                        data = [(x or "").lower() for x in data]
                        ok = fnmatch.filter(data, value and value_esc.lower())
                    elif comparator == 'any':
                        ok = data.filtered_domain(value)
                    elif comparator == 'not any':
                        ok = not data.filtered_domain(value)
                    else:
                        raise ValueError(f"Invalid term domain '{leaf}', operator '{comparator}' doesn't exist.")

                    if ok:
                        matching_ids.add(record.id)

                stack.append(matching_ids)

        while len(stack) > 1:
            stack.append(stack.pop() & stack.pop())

        [result_ids] = stack
        return self.browse(id_ for id_ in self._ids if id_ in result_ids)

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
            if any(self._ids):
                ids = self.search([('id', 'in', self.ids)])._ids
            else:  # Don't support new ids because search() doesn't work on new records
                ids = self._ids
            ids = tuple(reversed(ids)) if reverse else ids
        else:
            if isinstance(key, str):
                key = itemgetter(key)
            ids = tuple(item.id for item in sorted(self, key=key, reverse=reverse))
        return self.__class__(self.env, ids, self._prefetch_ids)

    def update(self, values):
        """ Update the records in ``self`` with ``values``. """
        for name, value in values.items():
            self[name] = value

    def flush_model(self, fnames=None):
        """ Process the pending computations and database updates on ``self``'s
        model.  When the parameter is given, the method guarantees that at least
        the given fields are flushed to the database.  More fields can be
        flushed, though.

        :param fnames: optional iterable of field names to flush
        """
        self._recompute_model(fnames)
        self._flush(fnames)

    def flush_recordset(self, fnames=None):
        """ Process the pending computations and database updates on the records
        ``self``.   When the parameter is given, the method guarantees that at
        least the given fields on records ``self`` are flushed to the database.
        More fields and records can be flushed, though.

        :param fnames: optional iterable of field names to flush
        """
        self._recompute_recordset(fnames)
        fields_ = None if fnames is None else (self._fields[fname] for fname in fnames)
        if self.env.cache.has_dirty_fields(self, fields_):
            self._flush(fnames)

    def _flush(self, fnames=None):

        def convert(record, field, value):
            if field.translate:
                return field._convert_from_cache_to_column(value)
            return field.convert_to_column(
                field.convert_to_write(value, record),
                record,
            )

        # DLE P76: test_onchange_one2many_with_domain_on_related_field
        # ```
        # email.important = True
        # self.assertIn(email, discussion.important_emails)
        # ```
        # When a search on a field coming from a related occurs (the domain
        # on discussion.important_emails field), make sure the related field
        # is flushed
        if fnames is None:
            fields = self._fields.values()
        else:
            fields = [self._fields[fname] for fname in fnames]

        model_fields = defaultdict(list)
        for field in fields:
            model_fields[field.model_name].append(field)
            if field.related_field:
                model_fields[field.related_field.model_name].append(field.related_field)

        for model_name, fields_ in model_fields.items():
            dirty_fields = self.env.cache.get_dirty_fields()
            if not any(field in dirty_fields for field in fields_):
                continue

            # if any field is context-dependent, the values to flush should
            # be found with a context where the context keys are all None
            context_none = dict.fromkeys(
                key
                for field in fields_
                for key in self.pool.field_depends_context[field]
            )
            model = self.env(context=context_none)[model_name]

            # pop dirty fields and their corresponding record ids from cache
            dirty_field_ids = {
                field: self.env.cache.clear_dirty_field(field)
                for field in model._fields.values()
                if field in dirty_fields
            }
            # Memory optimization: get a reference to each dirty field's cache.
            # This avoids allocating extra memory for storing the data taken
            # from cache. Beware that this breaks the cache abstraction!
            dirty_field_cache = {
                field: self.env.cache._get_field_cache(model, field)
                for field in dirty_field_ids
            }

            # build a mapping {vals: ids} of field updates and their record ids
            vals_ids = defaultdict(list)
            while dirty_field_ids:
                some_field, some_ids = next(iter(dirty_field_ids.items()))
                try:
                    for id_ in some_ids:
                        record = model.browse(id_)
                        vals = {
                            f.name: convert(record, f, dirty_field_cache[f][id_])
                            for f, ids in dirty_field_ids.items()
                            if id_ in ids
                        }
                        vals_ids[frozendict(vals)].append(id_)
                except KeyError:
                    raise AssertionError(
                        f"Could not find all values of {record} to flush them\n"
                        f"    Context: {self.env.context}\n"
                        f"    Cache: {self.env.cache!r}"
                    )

                # discard some_ids from all dirty ids sets
                dirty_field_ids.pop(some_field)
                for field, ids in list(dirty_field_ids.items()):
                    ids.difference_update(some_ids)
                    if not ids:
                        dirty_field_ids.pop(field)

            # apply the field updates to their corresponding records
            for vals, ids in vals_ids.items():
                model.browse(ids)._write(vals)

        # flush the inverse of one2many fields, too
        for field in fields:
            if field.type == 'one2many' and field.inverse_name:
                self.env[field.comodel_name].flush_model([field.inverse_name])

    #
    # New records - represent records that do not exist in the database yet;
    # they are used to perform onchanges.
    #

    @api.model
    def new(self, values=None, origin=None, ref=None):
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
        if values is None:
            values = {}
        if origin is not None:
            origin = origin.id
        record = self.browse((NewId(origin, ref),))
        record._update_cache(values, validate=False)

        return record

    @property
    def _origin(self):
        """ Return the actual records corresponding to ``self``. """
        ids = tuple(origin_ids(self._ids))
        prefetch_ids = OriginIds(self._prefetch_ids)
        return self.__class__(self.env, ids, prefetch_ids)

    #
    # "Dunder" methods
    #

    def __bool__(self):
        """ Test whether ``self`` is nonempty. """
        return True if self._ids else False  # fast version of bool(self._ids)

    __nonzero__ = __bool__

    def __len__(self):
        """ Return the size of ``self``. """
        return len(self._ids)

    def __iter__(self):
        """ Return an iterator over ``self``. """
        if len(self._ids) > PREFETCH_MAX and self._prefetch_ids is self._ids:
            for ids in self.env.cr.split_for_in_conditions(self._ids):
                for id_ in ids:
                    yield self.__class__(self.env, (id_,), ids)
        else:
            for id_ in self._ids:
                yield self.__class__(self.env, (id_,), self._prefetch_ids)

    def __reversed__(self):
        """ Return an reversed iterator over ``self``. """
        if len(self._ids) > PREFETCH_MAX and self._prefetch_ids is self._ids:
            for ids in self.env.cr.split_for_in_conditions(reversed(self._ids)):
                for id_ in ids:
                    yield self.__class__(self.env, (id_,), ids)
        elif self._ids:
            prefetch_ids = ReversedIterable(self._prefetch_ids)
            for id_ in reversed(self._ids):
                yield self.__class__(self.env, (id_,), prefetch_ids)

    def __contains__(self, item):
        """ Test whether ``item`` (record or field name) is an element of ``self``.
            In the first case, the test is fully equivalent to::

                any(item == record for record in self)
        """
        try:
            if self._name == item._name:
                return len(item) == 1 and item.id in self._ids
            raise TypeError(f"inconsistent models in: {item} in {self}")
        except AttributeError:
            if isinstance(item, str):
                return item in self._fields
            raise TypeError(f"unsupported operand types in: {item!r} in {self}")

    def __add__(self, other):
        """ Return the concatenation of two recordsets. """
        return self.concat(other)

    def concat(self, *args):
        """ Return the concatenation of ``self`` with all the arguments (in
            linear time complexity).
        """
        ids = list(self._ids)
        for arg in args:
            try:
                if arg._name != self._name:
                    raise TypeError(f"inconsistent models in: {self} + {arg}")
                ids.extend(arg._ids)
            except AttributeError:
                raise TypeError(f"unsupported operand types in: {self} + {arg!r}")
        return self.browse(ids)

    def __sub__(self, other):
        """ Return the recordset of all the records in ``self`` that are not in
            ``other``. Note that recordset order is preserved.
        """
        try:
            if self._name != other._name:
                raise TypeError(f"inconsistent models in: {self} - {other}")
            other_ids = set(other._ids)
            return self.browse([id for id in self._ids if id not in other_ids])
        except AttributeError:
            raise TypeError(f"unsupported operand types in: {self} - {other!r}")

    def __and__(self, other):
        """ Return the intersection of two recordsets.
            Note that first occurrence order is preserved.
        """
        try:
            if self._name != other._name:
                raise TypeError(f"inconsistent models in: {self} & {other}")
            other_ids = set(other._ids)
            return self.browse(OrderedSet(id for id in self._ids if id in other_ids))
        except AttributeError:
            raise TypeError(f"unsupported operand types in: {self} & {other!r}")

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
            try:
                if arg._name != self._name:
                    raise TypeError(f"inconsistent models in: {self} | {arg}")
                ids.extend(arg._ids)
            except AttributeError:
                raise TypeError(f"unsupported operand types in: {self} | {arg!r}")
        return self.browse(OrderedSet(ids))

    def __eq__(self, other):
        """ Test whether two recordsets are equivalent (up to reordering). """
        try:
            return self._name == other._name and set(self._ids) == set(other._ids)
        except AttributeError:
            if other:
                warnings.warn(f"unsupported operand type(s) for \"==\": '{self._name}()' == '{other!r}'", stacklevel=2)
        return NotImplemented

    def __lt__(self, other):
        try:
            if self._name == other._name:
                return set(self._ids) < set(other._ids)
        except AttributeError:
            pass
        return NotImplemented

    def __le__(self, other):
        try:
            if self._name == other._name:
                # these are much cheaper checks than a proper subset check, so
                # optimise for checking if a null or singleton are subsets of a
                # recordset
                if not self or self in other:
                    return True
                return set(self._ids) <= set(other._ids)
        except AttributeError:
            pass
        return NotImplemented

    def __gt__(self, other):
        try:
            if self._name == other._name:
                return set(self._ids) > set(other._ids)
        except AttributeError:
            pass
        return NotImplemented

    def __ge__(self, other):
        try:
            if self._name == other._name:
                if not other or other in self:
                    return True
                return set(self._ids) >= set(other._ids)
        except AttributeError:
            pass
        return NotImplemented

    def __int__(self):
        return self.id or 0

    def __repr__(self):
        return f"{self._name}{self._ids!r}"

    def __hash__(self):
        return hash((self._name, frozenset(self._ids)))

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
            return self._fields[key].__get__(self, self.env.registry[self._name])
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

    def invalidate_model(self, fnames=None, flush=True):
        """ Invalidate the cache of all records of ``self``'s model, when the
        cached values no longer correspond to the database values.  If the
        parameter is given, only the given fields are invalidated from cache.

        :param fnames: optional iterable of field names to invalidate
        :param flush: whether pending updates should be flushed before invalidation.
            It is ``True`` by default, which ensures cache consistency.
            Do not use this parameter unless you know what you are doing.
        """
        if flush:
            self.flush_model(fnames)
        self._invalidate_cache(fnames)

    def invalidate_recordset(self, fnames=None, flush=True):
        """ Invalidate the cache of the records in ``self``, when the cached
        values no longer correspond to the database values.  If the parameter
        is given, only the given fields on ``self`` are invalidated from cache.

        :param fnames: optional iterable of field names to invalidate
        :param flush: whether pending updates should be flushed before invalidation.
            It is ``True`` by default, which ensures cache consistency.
            Do not use this parameter unless you know what you are doing.
        """
        if flush:
            self.flush_recordset(fnames)
        self._invalidate_cache(fnames, self._ids)

    def _invalidate_cache(self, fnames=None, ids=None):
        if fnames is None:
            fields = self._fields.values()
        else:
            fields = [self._fields[fname] for fname in fnames]
        spec = []
        for field in fields:
            spec.append((field, ids))
            # TODO VSC: used to remove the inverse of many_to_one from the cache, though we might not need it anymore
            for invf in self.pool.field_inverses[field]:
                self.env[invf.model_name].flush_model([invf.name])
                spec.append((invf, None))
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

        if before:
            # When called before modification, we should determine what
            # currently depends on self, and it should not be recomputed before
            # the modification.  So we only collect what should be marked for
            # recomputation.
            marked = self.env.all.tocompute     # {field: ids}
            tomark = defaultdict(OrderedSet)    # {field: ids}
        else:
            # When called after modification, one should traverse backwards
            # dependencies by taking into account all fields already known to
            # be recomputed.  In that case, we mark fieds to compute as soon as
            # possible.
            marked = {}
            tomark = self.env.all.tocompute

        # determine what to trigger (with iterators)
        todo = [self._modified([self._fields[fname] for fname in fnames], create)]

        # process what to trigger by lazily chaining todo
        for field, records, create in itertools.chain.from_iterable(todo):
            records -= self.env.protected(field)
            if not records:
                continue

            if field.recursive:
                # discard already processed records, in order to avoid cycles
                if field.compute and field.store:
                    ids = (marked.get(field) or set()) | (tomark.get(field) or set())
                    records = records.browse(id_ for id_ in records._ids if id_ not in ids)
                else:
                    records = records & self.env.cache.get_records(records, field, all_contexts=True)
                if not records:
                    continue
                # recursively trigger recomputation of field's dependents
                todo.append(records._modified([field], create))

            # mark for recomputation (now or later, depending on 'before')
            if field.compute and field.store:
                tomark[field].update(records._ids)
            else:
                # Don't force the recomputation of compute fields which are
                # not stored as this is not really necessary.
                self.env.cache.invalidate([(field, records._ids)])

        if before:
            # effectively mark for recomputation now
            for field, ids in tomark.items():
                records = self.env[field.model_name].browse(ids)
                self.env.add_to_compute(field, records)

    def _modified(self, fields, create):
        """ Return an iterator traversing a tree of field triggers on ``self``,
        traversing backwards field dependencies along the way, and yielding
        tuple ``(field, records, created)`` to recompute.
        """
        cache = self.env.cache

        # The fields' trigger trees are merged in order to evaluate all triggers
        # at once. For non-stored computed fields, `_modified_triggers` might
        # traverse the tree (at the cost of extra queries) only to know which
        # records to invalidate in cache. But in many cases, most of these
        # fields have no data in cache, so they can be ignored from the start.
        # This allows us to discard subtrees from the merged tree when they
        # only contain such fields.
        def select(field):
            return (field.compute and field.store) or cache.contains_field(field)

        tree = self.pool.get_trigger_tree(fields, select=select)
        if not tree:
            return ()

        return self.sudo().with_context(active_test=False)._modified_triggers(tree, create)

    def _modified_triggers(self, tree, create=False):
        """ Return an iterator traversing a tree of field triggers on ``self``,
        traversing backwards field dependencies along the way, and yielding
        tuple ``(field, records, created)`` to recompute.
        """
        if not self:
            return

        # first yield what to compute
        for field in tree.root:
            yield field, self, create

        # then traverse dependencies backwards, and proceed recursively
        for field, subtree in tree.items():
            if create and field.type in ('many2one', 'many2one_reference'):
                # upon creation, no other record has a reference to self
                continue

            # subtree is another tree of dependencies
            model = self.env[field.model_name]
            for invf in model.pool.field_inverses[field]:
                # use an inverse of field without domain
                if not (invf.type in ('one2many', 'many2many') and invf.domain):
                    if invf.type == 'many2one_reference':
                        rec_ids = OrderedSet()
                        for rec in self:
                            try:
                                if rec[invf.model_field] == field.model_name:
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
                    if field.model_name == records._name:
                        if not any(self._ids):
                            # if self are new, records should be new as well
                            records = records.browse(it and NewId(it) for it in records._ids)
                        break
            else:
                new_records = self.filtered(lambda r: not r.id)
                real_records = self - new_records
                records = model.browse()
                if real_records:
                    records = model.search([(field.name, 'in', real_records.ids)], order='id')
                if new_records:
                    cache_records = self.env.cache.get_records(model, field)
                    new_ids = set(self._ids)
                    records |= cache_records.filtered(lambda r: not set(r[field.name]._ids).isdisjoint(new_ids))

            yield from records._modified_triggers(subtree)

    def _recompute_model(self, fnames=None):
        """ Process the pending computations of the fields of ``self``'s model.

        :param fnames: optional iterable of field names to compute
        """
        if fnames is None:
            fields = self._fields.values()
        else:
            fields = [self._fields[fname] for fname in fnames]

        for field in fields:
            if field.compute and field.store:
                self._recompute_field(field)

    def _recompute_recordset(self, fnames=None):
        """ Process the pending computations of the fields of the records in ``self``.

        :param fnames: optional iterable of field names to compute
        """
        if fnames is None:
            fields = self._fields.values()
        else:
            fields = [self._fields[fname] for fname in fnames]

        for field in fields:
            if field.compute and field.store:
                self._recompute_field(field, self._ids)

    def _recompute_field(self, field, ids=None):
        ids_to_compute = self.env.all.tocompute.get(field, ())
        if ids is None:
            ids = ids_to_compute
        else:
            ids = [id_ for id_ in ids if id_ in ids_to_compute]
        if not ids:
            return

        # do not force recomputation on new records; those will be
        # recomputed by accessing the field on the records
        records = self.browse(tuple(id_ for id_ in ids if id_))
        field.recompute(records)

    #
    # Generic onchange method
    #

    def _has_onchange(self, field, other_fields):
        """ Return whether ``field`` should trigger an onchange event in the
            presence of ``other_fields``.
        """
        return (field.name in self._onchange_methods) or any(
            dep in other_fields
            for dep in self.pool.get_dependent_fields(field.base_field)
        )

    def _apply_onchange_methods(self, field_name, result):
        """ Apply onchange method(s) for field ``field_name`` on ``self``. Value
            assignments are applied on ``self``, while warning messages are put
            in dictionary ``result``.
        """
        for method in self._onchange_methods.get(field_name, ()):
            res = method(self)
            if not res:
                continue
            if res.get('value'):
                for key, val in res['value'].items():
                    if key in self._fields and key != 'id':
                        self[key] = val
            if res.get('warning'):
                result['warnings'].add((
                    res['warning'].get('title') or _("Warning"),
                    res['warning'].get('message') or "",
                    res['warning'].get('type') or "",
                ))

    def onchange(self, values: Dict, field_names: List[str], fields_spec: Dict):
        raise NotImplementedError("onchange() is implemented in module 'web'")

    def _get_placeholder_filename(self, field):
        """ Returns the filename of the placeholder to use,
            set on web/static/img by default, or the
            complete path to access it (eg: module/path/to/image.png).
        """
        return False

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
                self.env.cr.commit()
                create_values = []

        if create_values:
            records_batches.append(self.create(create_values))
        return self.concat(*records_batches)


collections.abc.Set.register(BaseModel)
# not exactly true as BaseModel doesn't have index or count
collections.abc.Sequence.register(BaseModel)

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
        :attr:`_transient_max_count` or :attr:`_transient_max_hours` conditions
        (if any) are reached.

        Actual cleaning will happen only once every 5 minutes. This means this
        method can be called frequently (e.g. whenever a new record is created).

        Example with both max_hours and max_count active:

        Suppose max_hours = 0.2 (aka 12 minutes), max_count = 20, there are
        55 rows in the table, 10 created/changed in the last 5 minutes, an
        additional 12 created/changed between 5 and 10 minutes ago, the rest
        created/changed more than 12 minutes ago.

        - age based vacuum will leave the 22 rows created/changed in the last 12
          minutes
        - count based vacuum will wipe out another 12 rows. Not just 2,
          otherwise each addition would immediately cause the maximum to be
          reached again.
        - the 10 rows that have been created/changed the last 5 minutes will NOT
          be deleted
        """
        if self._transient_max_hours:
            # Age-based expiration
            self._transient_clean_rows_older_than(self._transient_max_hours * 60 * 60)

        if self._transient_max_count:
            # Count-based expiration
            self._transient_clean_old_rows(self._transient_max_count)

    def _transient_clean_old_rows(self, max_count):
        # Check how many rows we have in the table
        self._cr.execute(SQL("SELECT count(*) FROM %s", SQL.identifier(self._table)))
        [count] = self._cr.fetchone()
        if count > max_count:
            self._transient_clean_rows_older_than(300)

    def _transient_clean_rows_older_than(self, seconds):
        # Never delete rows used in last 5 minutes
        seconds = max(seconds, 300)
        self._cr.execute(SQL(
            "SELECT id FROM %s WHERE %s < %s",
            SQL.identifier(self._table),
            SQL("COALESCE(write_date, create_date, (now() AT TIME ZONE 'UTC'))::timestamp"),
            SQL("(now() AT TIME ZONE 'UTC') - interval %s", f"{seconds} seconds"),
        ))
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
        return {'message': _(u"Missing required value for the field '%s'", e.diag.column_name)}

    field_name = e.diag.column_name
    field = fields[field_name]
    message = _(u"Missing required value for the field '%s' (%s)", field['string'], field_name)
    return {
        'message': message,
        'field': field_name,
    }

def convert_pgerror_unique(model, fields, info, e):
    # new cursor since we're probably in an error handler in a blown
    # transaction which may not have been rollbacked/cleaned yet
    with closing(model.env.registry.cursor()) as cr_tmp:
        cr_tmp.execute(SQL("""
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
        """, e.diag.constraint_name))
        constraint, table, ufields = cr_tmp.fetchone() or (None, None, None)
    # if the unique constraint is on an expression or on an other table
    if not ufields or model._table != table:
        return {'message': tools.ustr(e)}

    # TODO: add stuff from e.diag.message_hint? provides details about the constraint & duplication values but may be localized...
    if len(ufields) == 1:
        field_name = ufields[0]
        field = fields[field_name]
        message = _(
            u"The value for the field '%s' already exists (this is probably '%s' in the current model).",
            field_name,
            field['string']
        )
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

# keep those imports here to avoid dependency cycle errors
# pylint: disable=wrong-import-position
from . import fields
from .osv import expression
from .fields import Field, Datetime, Command
