# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" High-level objects for fields. """

from collections import OrderedDict, defaultdict
from datetime import date, datetime
from functools import partial
from operator import attrgetter
from types import NoneType
import logging
import pytz
import xmlrpclib

import psycopg2

from odoo.sql_db import LazyCursor
from odoo.tools import float_precision, float_repr, float_round, frozendict, \
                       html_sanitize, human_size, pg_varchar, ustr, OrderedSet
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from odoo.tools.translate import html_translate, _
import odoo.tools.sql as sql

DATE_LENGTH = len(date.today().strftime(DATE_FORMAT))
DATETIME_LENGTH = len(datetime.now().strftime(DATETIME_FORMAT))
EMPTY_DICT = frozendict()

RENAMED_ATTRS = [('select', 'index'), ('digits_compute', 'digits')]

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__[:-7] + '.schema')

Default = object()                      # default value for __init__() methods

class SpecialValue(object):
    """ Encapsulates a value in the cache in place of a normal value. """
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value

class FailedValue(SpecialValue):
    """ Special value that encapsulates an exception instead of a value. """
    def __init__(self, exception):
        self.exception = exception
    def get(self):
        raise self.exception

def _check_value(value):
    """ Return ``value``, or call its getter if ``value`` is a :class:`SpecialValue`. """
    return value.get() if isinstance(value, SpecialValue) else value

def copy_cache(records, env):
    """ Recursively copy the cache of ``records`` to the environment ``env``. """
    todo, done = set(records), set()
    while todo:
        record = todo.pop()
        if record not in done:
            done.add(record)
            target = record.with_env(env)
            for name in record._cache:
                field = record._fields[name]
                value = record[name]
                if isinstance(value, BaseModel):
                    todo.update(value)
                target._cache[name] = field.convert_to_cache(value, target, validate=False)


def resolve_mro(model, name, predicate):
    """ Return the list of successively overridden values of attribute ``name``
        in mro order on ``model`` that satisfy ``predicate``.
    """
    result = []
    for cls in type(model).__mro__:
        if name in cls.__dict__:
            value = cls.__dict__[name]
            if not predicate(value):
                break
            result.append(value)
    return result


class MetaField(type):
    """ Metaclass for field classes. """
    by_type = {}

    def __new__(meta, name, bases, attrs):
        """ Combine the ``_slots`` dict from parent classes, and determine
        ``__slots__`` for them on the new class.
        """
        base_slots = {}
        for base in reversed(bases):
            base_slots.update(getattr(base, '_slots', ()))

        slots = dict(base_slots)
        slots.update(attrs.get('_slots', ()))

        attrs['__slots__'] = set(slots) - set(base_slots)
        attrs['_slots'] = slots
        return type.__new__(meta, name, bases, attrs)

    def __init__(cls, name, bases, attrs):
        super(MetaField, cls).__init__(name, bases, attrs)
        if cls.type and cls.type not in MetaField.by_type:
            MetaField.by_type[cls.type] = cls

        # compute class attributes to avoid calling dir() on fields
        cls.related_attrs = []
        cls.description_attrs = []
        for attr in dir(cls):
            if attr.startswith('_related_'):
                cls.related_attrs.append((attr[9:], attr))
            elif attr.startswith('_description_'):
                cls.description_attrs.append((attr[13:], attr))


class Field(object):
    """ The field descriptor contains the field definition, and manages accesses
        and assignments of the corresponding field on records. The following
        attributes may be provided when instanciating a field:

        :param string: the label of the field seen by users (string); if not
            set, the ORM takes the field name in the class (capitalized).

        :param help: the tooltip of the field seen by users (string)

        :param readonly: whether the field is readonly (boolean, by default ``False``)

        :param required: whether the value of the field is required (boolean, by
            default ``False``)

        :param index: whether the field is indexed in database (boolean, by
            default ``False``)

        :param default: the default value for the field; this is either a static
            value, or a function taking a recordset and returning a value; use
            ``default=None`` to discard default values for the field

        :param states: a dictionary mapping state values to lists of UI attribute-value
            pairs; possible attributes are: 'readonly', 'required', 'invisible'.
            Note: Any state-based condition requires the ``state`` field value to be
            available on the client-side UI. This is typically done by including it in
            the relevant views, possibly made invisible if not relevant for the
            end-user.

        :param groups: comma-separated list of group xml ids (string); this
            restricts the field access to the users of the given groups only

        :param bool copy: whether the field value should be copied when the record
            is duplicated (default: ``True`` for normal fields, ``False`` for
            ``one2many`` and computed fields, including property fields and
            related fields)

        :param string oldname: the previous name of this field, so that ORM can rename
            it automatically at migration

        .. _field-computed:

        .. rubric:: Computed fields

        One can define a field whose value is computed instead of simply being
        read from the database. The attributes that are specific to computed
        fields are given below. To define such a field, simply provide a value
        for the attribute ``compute``.

        :param compute: name of a method that computes the field

        :param inverse: name of a method that inverses the field (optional)

        :param search: name of a method that implement search on the field (optional)

        :param store: whether the field is stored in database (boolean, by
            default ``False`` on computed fields)

        :param compute_sudo: whether the field should be recomputed as superuser
            to bypass access rights (boolean, by default ``False``)

        The methods given for ``compute``, ``inverse`` and ``search`` are model
        methods. Their signature is shown in the following example::

            upper = fields.Char(compute='_compute_upper',
                                inverse='_inverse_upper',
                                search='_search_upper')

            @api.depends('name')
            def _compute_upper(self):
                for rec in self:
                    rec.upper = rec.name.upper() if rec.name else False

            def _inverse_upper(self):
                for rec in self:
                    rec.name = rec.upper.lower() if rec.upper else False

            def _search_upper(self, operator, value):
                if operator == 'like':
                    operator = 'ilike'
                return [('name', operator, value)]

        The compute method has to assign the field on all records of the invoked
        recordset. The decorator :meth:`odoo.api.depends` must be applied on
        the compute method to specify the field dependencies; those dependencies
        are used to determine when to recompute the field; recomputation is
        automatic and guarantees cache/database consistency. Note that the same
        method can be used for several fields, you simply have to assign all the
        given fields in the method; the method will be invoked once for all
        those fields.

        By default, a computed field is not stored to the database, and is
        computed on-the-fly. Adding the attribute ``store=True`` will store the
        field's values in the database. The advantage of a stored field is that
        searching on that field is done by the database itself. The disadvantage
        is that it requires database updates when the field must be recomputed.

        The inverse method, as its name says, does the inverse of the compute
        method: the invoked records have a value for the field, and you must
        apply the necessary changes on the field dependencies such that the
        computation gives the expected value. Note that a computed field without
        an inverse method is readonly by default.

        The search method is invoked when processing domains before doing an
        actual search on the model. It must return a domain equivalent to the
        condition: ``field operator value``.

        .. _field-related:

        .. rubric:: Related fields

        The value of a related field is given by following a sequence of
        relational fields and reading a field on the reached model. The complete
        sequence of fields to traverse is specified by the attribute

        :param related: sequence of field names

        Some field attributes are automatically copied from the source field if
        they are not redefined: ``string``, ``help``, ``readonly``, ``required`` (only
        if all fields in the sequence are required), ``groups``, ``digits``, ``size``,
        ``translate``, ``sanitize``, ``selection``, ``comodel_name``, ``domain``,
        ``context``. All semantic-free attributes are copied from the source
        field.

        By default, the values of related fields are not stored to the database.
        Add the attribute ``store=True`` to make it stored, just like computed
        fields. Related fields are automatically recomputed when their
        dependencies are modified.

        .. _field-company-dependent:

        .. rubric:: Company-dependent fields

        Formerly known as 'property' fields, the value of those fields depends
        on the company. In other words, users that belong to different companies
        may see different values for the field on a given record.

        :param company_dependent: whether the field is company-dependent (boolean)

        .. _field-incremental-definition:

        .. rubric:: Incremental definition

        A field is defined as class attribute on a model class. If the model
        is extended (see :class:`~odoo.models.Model`), one can also extend
        the field definition by redefining a field with the same name and same
        type on the subclass. In that case, the attributes of the field are
        taken from the parent class and overridden by the ones given in
        subclasses.

        For instance, the second class below only adds a tooltip on the field
        ``state``::

            class First(models.Model):
                _name = 'foo'
                state = fields.Selection([...], required=True)

            class Second(models.Model):
                _inherit = 'foo'
                state = fields.Selection(help="Blah blah blah")

    """
    __metaclass__ = MetaField

    type = None                         # type of the field (string)
    relational = False                  # whether the field is a relational one
    translate = False                   # whether the field is translated

    column_type = None                  # database column type (ident, spec)
    column_format = '%s'                # placeholder for value in queries
    column_cast_from = ()               # column types that may be cast to this

    _slots = {
        'args': EMPTY_DICT,             # the parameters given to __init__()
        '_attrs': EMPTY_DICT,           # the field's non-slot attributes
        '_module': None,                # the field's module name
        '_setup_done': None,            # the field's setup state: None, 'base' or 'full'

        'automatic': False,             # whether the field is automatically created ("magic" field)
        'inherited': False,             # whether the field is inherited (_inherits)

        'name': None,                   # name of the field
        'model_name': None,             # name of the model of this field
        'comodel_name': None,           # name of the model of values (if relational)

        'store': True,                  # whether the field is stored in database
        'index': False,                 # whether the field is indexed in database
        'manual': False,                # whether the field is a custom field
        'copy': True,                   # whether the field is copied over by BaseModel.copy()
        'depends': (),                  # collection of field dependencies
        'recursive': False,             # whether self depends on itself
        'compute': None,                # compute(recs) computes field on recs
        'compute_sudo': False,          # whether field should be recomputed as admin
        'inverse': None,                # inverse(recs) inverses field on recs
        'search': None,                 # search(recs, operator, value) searches on self
        'related': None,                # sequence of field names, for related fields
        'related_sudo': True,           # whether related fields should be read as admin
        'company_dependent': False,     # whether ``self`` is company-dependent (property field)
        'default': None,                # default(recs) returns the default value

        'string': None,                 # field label
        'help': None,                   # field tooltip
        'readonly': False,              # whether the field is readonly
        'required': False,              # whether the field is required
        'states': None,                 # set readonly and required depending on state
        'groups': None,                 # csv list of group xml ids
        'change_default': False,        # whether the field may trigger a "user-onchange"
        'deprecated': None,             # whether the field is deprecated

        'related_field': None,          # corresponding related field
        'group_operator': None,         # operator for aggregating values
        'group_expand': None,           # name of method to expand groups in read_group()
        'prefetch': True,               # whether the field is prefetched
    }

    def __init__(self, string=Default, **kwargs):
        kwargs['string'] = string
        args = {key: val for key, val in kwargs.iteritems() if val is not Default}
        self.args = args or EMPTY_DICT
        self._setup_done = None

    def new(self, **kwargs):
        """ Return a field of the same type as ``self``, with its own parameters. """
        return type(self)(**kwargs)

    def __getattr__(self, name):
        """ Access non-slot field attribute. """
        try:
            return self._attrs[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        """ Set slot or non-slot field attribute. """
        try:
            object.__setattr__(self, name, value)
        except AttributeError:
            if self._attrs:
                self._attrs[name] = value
            else:
                self._attrs = {name: value}     # replace EMPTY_DICT

    def set_all_attrs(self, attrs):
        """ Set all field attributes at once (with slot defaults). """
        # optimization: we assign slots only
        assign = object.__setattr__
        for key, val in self._slots.iteritems():
            assign(self, key, attrs.pop(key, val))
        if attrs:
            assign(self, '_attrs', attrs)

    def __delattr__(self, name):
        """ Remove non-slot field attribute. """
        try:
            del self._attrs[name]
        except KeyError:
            raise AttributeError(name)

    def __str__(self):
        return "%s.%s" % (self.model_name, self.name)

    def __repr__(self):
        return "%s.%s" % (self.model_name, self.name)

    ############################################################################
    #
    # Base field setup: things that do not depend on other models/fields
    #

    def setup_base(self, model, name):
        """ Base setup: things that do not depend on other models/fields. """
        if self._setup_done and not self.related:
            # optimization for regular fields: keep the base setup
            self._setup_done = 'base'
        else:
            # do the base setup from scratch
            self._setup_attrs(model, name)
            if not self.related:
                self._setup_regular_base(model)
            self._setup_done = 'base'

    #
    # Setup field parameter attributes
    #

    def _can_setup_from(self, field):
        """ Return whether ``self`` can retrieve parameters from ``field``. """
        return isinstance(field, type(self))

    def _get_attrs(self, model, name):
        """ Return the field parameter attributes as a dictionary. """
        # determine all inherited field attributes
        attrs = {}
        if not (self.args.get('automatic') or self.args.get('manual')):
            # magic and custom fields do not inherit from parent classes
            for field in reversed(resolve_mro(model, name, self._can_setup_from)):
                attrs.update(field.args)
        attrs.update(self.args)         # necessary in case self is not in class

        attrs['args'] = self.args
        attrs['model_name'] = model._name
        attrs['name'] = name

        # initialize ``self`` with ``attrs``
        if attrs.get('compute'):
            # by default, computed fields are not stored, not copied and readonly
            attrs['store'] = attrs.get('store', False)
            attrs['copy'] = attrs.get('copy', False)
            attrs['readonly'] = attrs.get('readonly', not attrs.get('inverse'))
        if attrs.get('related'):
            # by default, related fields are not stored and not copied
            attrs['store'] = attrs.get('store', False)
            attrs['copy'] = attrs.get('copy', False)
        if attrs.get('company_dependent'):
            # by default, company-dependent fields are not stored and not copied
            attrs['store'] = False
            attrs['copy'] = attrs.get('copy', False)
            attrs['default'] = self._default_company_dependent
            attrs['compute'] = self._compute_company_dependent
            if not attrs.get('readonly'):
                attrs['inverse'] = self._inverse_company_dependent
            attrs['search'] = self._search_company_dependent

        return attrs

    def _setup_attrs(self, model, name):
        """ Initialize the field parameter attributes. """
        attrs = self._get_attrs(model, name)
        self.set_all_attrs(attrs)

        # check for renamed attributes (conversion errors)
        for key1, key2 in RENAMED_ATTRS:
            if key1 in attrs:
                _logger.warning("Field %s: parameter %r is no longer supported; use %r instead.",
                                self, key1, key2)

        # prefetch only stored, column, non-manual and non-deprecated fields
        if not (self.store and self.column_type) or self.manual or self.deprecated:
            self.prefetch = False

        if not self.string and not self.related:
            # related fields get their string from their parent field
            self.string = (
                name[:-4] if name.endswith('_ids') else
                name[:-3] if name.endswith('_id') else name
            ).replace('_', ' ').title()

        # self.default must be a callable
        if self.default is not None:
            value = self.default
            self.default = value if callable(value) else lambda model: value

    ############################################################################
    #
    # Full field setup: everything else, except recomputation triggers
    #

    def setup_full(self, model):
        """ Full setup: everything else, except recomputation triggers. """
        if self._setup_done != 'full':
            if not self.related:
                self._setup_regular_full(model)
            else:
                self._setup_related_full(model)
            self._setup_done = 'full'

    #
    # Setup of non-related fields
    #

    def _setup_regular_base(self, model):
        """ Setup the attributes of a non-related field. """
        def make_depends(deps):
            return tuple(deps(model) if callable(deps) else deps)

        if isinstance(self.compute, basestring):
            # if the compute method has been overridden, concatenate all their _depends
            self.depends = ()
            for method in resolve_mro(model, self.compute, callable):
                self.depends += make_depends(getattr(method, '_depends', ()))
        else:
            self.depends = make_depends(getattr(self.compute, '_depends', ()))

    def _setup_regular_full(self, model):
        """ Setup the inverse field(s) of ``self``. """
        pass

    #
    # Setup of related fields
    #

    def _setup_related_full(self, model):
        """ Setup the attributes of a related field. """
        # fix the type of self.related if necessary
        if isinstance(self.related, basestring):
            self.related = tuple(self.related.split('.'))

        # determine the chain of fields, and make sure they are all set up
        target = model
        for name in self.related:
            field = target._fields[name]
            field.setup_full(target)
            target = target[name]

        self.related_field = field

        # check type consistency
        if self.type != field.type:
            raise TypeError("Type of related field %s is inconsistent with %s" % (self, field))

        # determine dependencies, compute, inverse, and search
        self.depends = ('.'.join(self.related),)
        self.compute = self._compute_related
        if not (self.readonly or field.readonly):
            self.inverse = self._inverse_related
        if field._description_searchable:
            # allow searching on self only if the related field is searchable
            self.search = self._search_related

        # copy attributes from field to self (string, help, etc.)
        for attr, prop in self.related_attrs:
            if not getattr(self, attr):
                setattr(self, attr, getattr(field, prop))

        for attr, value in field._attrs.iteritems():
            if attr not in self._attrs:
                setattr(self, attr, value)

        # special case for states: copy it only for inherited fields
        if not self.states and self.inherited:
            self.states = field.states

        # special case for inherited required fields
        if self.inherited and field.required:
            self.required = True

    def traverse_related(self, record):
        """ Traverse the fields of the related field `self` except for the last
        one, and return it as a pair `(last_record, last_field)`. """
        for name in self.related[:-1]:
            record = record[name][:1]
        return record, self.related_field

    def _compute_related(self, records):
        """ Compute the related field ``self`` on ``records``. """
        # when related_sudo, bypass access rights checks when reading values
        others = records.sudo() if self.related_sudo else records
        for record, other in zip(records, others):
            if not record.id and record.env != other.env:
                # draft records: copy record's cache to other's cache first
                copy_cache(record, other.env)
            other, field = self.traverse_related(other)
            record[self.name] = other[field.name]

    def _inverse_related(self, records):
        """ Inverse the related field ``self`` on ``records``. """
        # store record values, otherwise they may be lost by cache invalidation!
        record_value = {record: record[self.name] for record in records}
        for record in records:
            other, field = self.traverse_related(record)
            if other:
                other[field.name] = record_value[record]

    def _search_related(self, records, operator, value):
        """ Determine the domain to search on field ``self``. """
        return [('.'.join(self.related), operator, value)]

    # properties used by _setup_related_full() to copy values from related field
    _related_comodel_name = property(attrgetter('comodel_name'))
    _related_string = property(attrgetter('string'))
    _related_help = property(attrgetter('help'))
    _related_readonly = property(attrgetter('readonly'))
    _related_groups = property(attrgetter('groups'))
    _related_group_operator = property(attrgetter('group_operator'))

    @property
    def base_field(self):
        """ Return the base field of an inherited field, or ``self``. """
        return self.related_field.base_field if self.inherited else self

    #
    # Company-dependent fields
    #

    def _default_company_dependent(self, model):
        return model.env['ir.property'].get(self.name, self.model_name)

    def _compute_company_dependent(self, records):
        Property = records.env['ir.property']
        values = Property.get_multi(self.name, self.model_name, records.ids)
        for record in records:
            record[self.name] = values.get(record.id)

    def _inverse_company_dependent(self, records):
        Property = records.env['ir.property']
        values = {
            record.id: self.convert_to_write(record[self.name], record)
            for record in records
        }
        Property.set_multi(self.name, self.model_name, values)

    def _search_company_dependent(self, records, operator, value):
        Property = records.env['ir.property']
        return Property.search_multi(self.name, self.model_name, operator, value)

    #
    # Setup of field triggers
    #
    # The triggers of ``self`` are a collection of pairs ``(field, path)`` of
    # fields that depend on ``self``. When ``self`` is modified, it invalidates
    # the cache of each ``field``, and determines the records to recompute based
    # on ``path``. See method ``modified`` below for details.
    #

    def resolve_deps(self, model):
        """ Return the dependencies of ``self`` as tuples ``(model, field, path)``,
            where ``path`` is an optional list of field names.
        """
        model0 = model
        result = []

        # add self's own dependencies
        for dotnames in self.depends:
            if dotnames == self.name:
                _logger.warning("Field %s depends on itself; please fix its decorator @api.depends().", self)
            model, path = model0, dotnames.split('.')
            for i, fname in enumerate(path):
                field = model._fields[fname]
                result.append((model, field, path[:i]))
                model = model0.env.get(field.comodel_name)

        # add self's model dependencies
        for mname, fnames in model0._depends.iteritems():
            model = model0.env[mname]
            for fname in fnames:
                field = model._fields[fname]
                result.append((model, field, None))

        # add indirect dependencies from the dependencies found above
        for model, field, path in list(result):
            for inv_field in model._field_inverses[field]:
                inv_model = model0.env[inv_field.model_name]
                inv_path = None if path is None else path + [field.name]
                result.append((inv_model, inv_field, inv_path))

        return result

    def setup_triggers(self, model):
        """ Add the necessary triggers to invalidate/recompute ``self``. """
        for model, field, path in self.resolve_deps(model):
            if field is not self:
                path_str = None if path is None else ('.'.join(path) or 'id')
                model._field_triggers.add(field, (self, path_str))
            elif path:
                self.recursive = True
                model._field_triggers.add(field, (self, '.'.join(path)))

    ############################################################################
    #
    # Field description
    #

    def get_description(self, env):
        """ Return a dictionary that describes the field ``self``. """
        desc = {'type': self.type}
        for attr, prop in self.description_attrs:
            value = getattr(self, prop)
            if callable(value):
                value = value(env)
            if value is not None:
                desc[attr] = value

        return desc

    # properties used by get_description()
    _description_store = property(attrgetter('store'))
    _description_manual = property(attrgetter('manual'))
    _description_depends = property(attrgetter('depends'))
    _description_related = property(attrgetter('related'))
    _description_company_dependent = property(attrgetter('company_dependent'))
    _description_readonly = property(attrgetter('readonly'))
    _description_required = property(attrgetter('required'))
    _description_states = property(attrgetter('states'))
    _description_groups = property(attrgetter('groups'))
    _description_change_default = property(attrgetter('change_default'))
    _description_deprecated = property(attrgetter('deprecated'))

    @property
    def _description_searchable(self):
        return bool(self.store or self.search)

    @property
    def _description_sortable(self):
        return self.store or (self.inherited and self.related_field._description_sortable)

    def _description_string(self, env):
        if self.string and env.lang:
            model_name = self.base_field.model_name
            field_string = env['ir.translation'].get_field_string(model_name)
            return field_string.get(self.name) or self.string
        return self.string

    def _description_help(self, env):
        if self.help and env.lang:
            model_name = self.base_field.model_name
            field_help = env['ir.translation'].get_field_help(model_name)
            return field_help.get(self.name) or self.help
        return self.help

    ############################################################################
    #
    # Conversion of values
    #

    def null(self, record):
        """ Return the null value for this field in the record format. """
        return False

    def convert_to_column(self, value, record):
        """ Convert ``value`` from the ``write`` format to the SQL format. """
        if value is None or value == False:
            return None
        if isinstance(value, unicode):
            return value.encode('utf8')
        return str(value)

    def convert_to_cache(self, value, record, validate=True):
        """ Convert ``value`` to the cache format; ``value`` may come from an
        assignment, or have the format of methods :meth:`BaseModel.read` or
        :meth:`BaseModel.write`. If the value represents a recordset, it should
        be added for prefetching on ``record``.

        :param bool validate: when True, field-specific validation of ``value``
            will be performed
        """
        return value

    def convert_to_record(self, value, record):
        """ Convert ``value`` from the cache format to the record format.
        If the value represents a recordset, it should share the prefetching of
        ``record``.
        """
        return value

    def convert_to_read(self, value, record, use_name_get=True):
        """ Convert ``value`` from the record format to the format returned by
        method :meth:`BaseModel.read`.

        :param bool use_name_get: when True, the value's display name will be
            computed using :meth:`BaseModel.name_get`, if relevant for the field
        """
        return False if value is None else value

    def convert_to_write(self, value, record):
        """ Convert ``value`` from the record format to the format of method
        :meth:`BaseModel.write`.
        """
        return self.convert_to_read(value, record)

    def convert_to_onchange(self, value, record, fnames=()):
        """ Convert ``value`` from the record format to the format returned by
        method :meth:`BaseModel.onchange`.

        :param fnames: an optional collection of field names to convert
            (for relational fields only)
        """
        return self.convert_to_read(value, record)

    def convert_to_export(self, value, record):
        """ Convert ``value`` from the record format to the export format. """
        if not value:
            return ''
        return value if record._context.get('export_raw_data') else ustr(value)

    def convert_to_display_name(self, value, record):
        """ Convert ``value`` from the record format to a suitable display name. """
        return ustr(value)

    ############################################################################
    #
    # Update database schema
    #

    def update_db(self, model, columns):
        """ Update the database schema to implement this field.

            :param model: an instance of the field's model
            :param columns: a dict mapping column names to their configuration in database
            :return: ``True`` if the field must be recomputed on existing rows
        """
        if not self.column_type:
            return

        column = columns.get(self.name)
        if not column and hasattr(self, 'oldname'):
            # column not found; check whether it exists under its old name
            column = columns.get(self.oldname)
            if column:
                sql.rename_column(model._cr, model._table, self.oldname, self.name)

        # create/update the column, not null constraint, indexes
        self.update_db_column(model, column)
        self.update_db_notnull(model, column)
        self.update_db_index(model, column)

        return not column

    def update_db_column(self, model, column):
        """ Create/update the column corresponding to ``self``.

            :param model: an instance of the field's model
            :param column: the column's configuration (dict) if it exists, or ``None``
        """
        if not column:
            # the column does not exist, create it
            sql.create_column(model._cr, model._table, self.name, self.column_type[1], self.string)
            return
        if column['udt_name'] == self.column_type[0]:
            return
        if column['udt_name'] in self.column_cast_from:
            sql.convert_column(model._cr, model._table, self.name, self.column_type[1])
        else:
            newname = (self.name + '_moved{}').format
            i = 0
            while sql.column_exists(model._cr, model._table, newname(i)):
                i += 1
            if column['is_nullable'] == 'NO':
                sql.drop_not_null(model._cr, model._table, self.name)
            sql.rename_column(model._cr, model._table, self.name, newname(i))
            sql.create_column(model._cr, model._table, self.name, self.column_type[1], self.string)

    def update_db_notnull(self, model, column):
        """ Add or remove the NOT NULL constraint on ``self``.

            :param model: an instance of the field's model
            :param column: the column's configuration (dict) if it exists, or ``None``
        """
        has_notnull = column and column['is_nullable'] == 'NO'

        if not column or (self.required and not has_notnull):
            # the column is new or it becomes required; initialize its values
            if model._table_has_rows():
                model._init_column(self.name)

        if self.required and not has_notnull:
            sql.set_not_null(model._cr, model._table, self.name)
        elif not self.required and has_notnull:
            sql.drop_not_null(model._cr, model._table, self.name)

    def update_db_index(self, model, column):
        """ Add or remove the index corresponding to ``self``.

            :param model: an instance of the field's model
            :param column: the column's configuration (dict) if it exists, or ``None``
        """
        indexname = '%s_%s_index' % (model._table, self.name)
        if self.index:
            sql.create_index(model._cr, indexname, model._table, ['"%s"' % self.name])
        else:
            sql.drop_index(model._cr, indexname, model._table)

    ############################################################################
    #
    # Read from/write to database
    #

    def read(self, records):
        """ Read the value of ``self`` on ``records``, and store it in cache. """
        return NotImplementedError("Method read() undefined on %s" % self)

    def write(self, records, value):
        """ Write the value of ``self`` on ``records``. The ``value`` must be in
        the format of method :meth:`BaseModel.write`.
        """
        return NotImplementedError("Method write() undefined on %s" % self)

    ############################################################################
    #
    # Descriptor methods
    #

    def __get__(self, record, owner):
        """ return the value of field ``self`` on ``record`` """
        if record is None:
            return self         # the field is accessed through the owner class

        if record:
            # only a single record may be accessed
            record.ensure_one()
            try:
                value = record._cache[self]
            except KeyError:
                # cache miss, determine value and retrieve it
                if record.id:
                    self.determine_value(record)
                else:
                    self.determine_draft_value(record)
                value = record._cache[self]
        else:
            # null record -> return the null value for this field
            value = self.convert_to_cache(False, record, validate=False)

        return self.convert_to_record(value, record)

    def __set__(self, record, value):
        """ set the value of field ``self`` on ``record`` """
        env = record.env

        # only a single record may be updated
        record.ensure_one()

        # adapt value to the cache level
        value = self.convert_to_cache(value, record)

        if env.in_draft or not record.id:
            # determine dependent fields
            spec = self.modified_draft(record)

            # set value in cache, inverse field, and mark record as dirty
            record._cache[self] = value
            if env.in_onchange:
                for invf in record._field_inverses[self]:
                    invf._update(record[self.name], record)
                record._set_dirty(self.name)

            # determine more dependent fields, and invalidate them
            if self.relational:
                spec += self.modified_draft(record)
            env.invalidate(spec)

        else:
            # Write to database
            write_value = self.convert_to_write(self.convert_to_record(value, record), record)
            record.write({self.name: write_value})
            # Update the cache unless value contains a new record
            if not (self.relational and not all(value)):
                record._cache[self] = value

    ############################################################################
    #
    # Computation of field values
    #

    def _compute_value(self, records):
        """ Invoke the compute method on ``records``. """
        # initialize the fields to their corresponding null value in cache
        fields = records._field_computed[self]
        for field in fields:
            for record in records:
                record._cache[field] = field.convert_to_cache(False, record, validate=False)
        if isinstance(self.compute, basestring):
            getattr(records, self.compute)()
        else:
            self.compute(records)

    def compute_value(self, records):
        """ Invoke the compute method on ``records``; the results are in cache. """
        fields = records._field_computed[self]
        with records.env.do_in_draft(), records.env.protecting(fields, records):
            try:
                self._compute_value(records)
            except (AccessError, MissingError):
                # some record is forbidden or missing, retry record by record
                for record in records:
                    try:
                        self._compute_value(record)
                    except Exception as exc:
                        record._cache[self.name] = FailedValue(exc)

    def determine_value(self, record):
        """ Determine the value of ``self`` for ``record``. """
        env = record.env

        if self.store and not (self.compute and env.in_onchange):
            # this is a stored field or an old-style function field
            if self.compute:
                # this is a stored computed field, check for recomputation
                recs = record._recompute_check(self)
                if recs:
                    # recompute the value (only in cache)
                    self.compute_value(recs)
                    # HACK: if result is in the wrong cache, copy values
                    if recs.env != env:
                        computed = record._field_computed[self]
                        for source, target in zip(recs, recs.with_env(env)):
                            try:
                                values = target._convert_to_cache({
                                    f.name: source[f.name] for f in computed
                                }, validate=False)
                            except MissingError as e:
                                values = FailedValue(e)
                            target._cache.update(values)
                    # the result is saved to database by BaseModel.recompute()
                    return

            # read the field from database
            record._prefetch_field(self)

        elif self.compute:
            # this is either a non-stored computed field, or a stored computed
            # field in onchange mode
            if self.recursive:
                self.compute_value(record)
            else:
                recs = record._in_cache_without(self)
                self.compute_value(recs)

        else:
            # this is a non-stored non-computed field
            record._cache[self] = self.convert_to_cache(False, record, validate=False)

    def determine_draft_value(self, record):
        """ Determine the value of ``self`` for the given draft ``record``. """
        if self.compute:
            fields = record._field_computed[self]
            with record.env.protecting(fields, record):
                self._compute_value(record)
        else:
            null = self.convert_to_cache(False, record, validate=False)
            record._cache[self] = SpecialValue(null)

    def determine_inverse(self, records):
        """ Given the value of ``self`` on ``records``, inverse the computation. """
        if isinstance(self.inverse, basestring):
            getattr(records, self.inverse)()
        else:
            self.inverse(records)

    def determine_domain(self, records, operator, value):
        """ Return a domain representing a condition on ``self``. """
        if isinstance(self.search, basestring):
            return getattr(records, self.search)(operator, value)
        else:
            return self.search(records, operator, value)

    ############################################################################
    #
    # Notification when fields are modified
    #

    def modified(self, records):
        """ Notify that field ``self`` has been modified on ``records``: prepare the
            fields/records to recompute, and return a spec indicating what to
            invalidate.
        """
        # invalidate the fields that depend on self, and prepare recomputation
        spec = [(self, records._ids)]

        # group triggers by model and path to reduce the number of calls to search()
        bymodel = defaultdict(lambda: defaultdict(list))
        for field, path in records._field_triggers[self]:
            bymodel[field.model_name][path].append(field)

        for model_name, bypath in bymodel.iteritems():
            for path, fields in bypath.iteritems():
                if path and any(field.compute and field.store for field in fields):
                    # process stored fields
                    stored = set(field for field in fields if field.compute and field.store)
                    fields = set(fields) - stored
                    if path == 'id':
                        target0 = records
                    else:
                        # don't move this line to function top, see log
                        env = records.env(user=SUPERUSER_ID, context={'active_test': False})
                        target0 = env[model_name].search([(path, 'in', records.ids)])
                    if target0:
                        for field in stored:
                            # discard records to not recompute for field
                            target = target0 - records.env.protected(field)
                            if not target:
                                continue
                            spec.append((field, target._ids))
                            # recompute field on target in the environment of
                            # records, and as user admin if required
                            if field.compute_sudo:
                                target = target.with_env(records.env(user=SUPERUSER_ID))
                            else:
                                target = target.with_env(records.env)
                            target._recompute_todo(field)
                # process non-stored fields
                for field in fields:
                    spec.append((field, None))

        return spec

    def modified_draft(self, records):
        """ Same as :meth:`modified`, but in draft mode. """
        env = records.env

        # invalidate the fields on the records in cache that depend on
        # ``records``, except fields currently being computed
        spec = []
        for field, path in records._field_triggers[self]:
            if not field.compute:
                # Note: do not invalidate non-computed fields. Such fields may
                # require invalidation in general (like *2many fields with
                # domains) but should not be invalidated in this case, because
                # we would simply lose their values during an onchange!
                continue

            target = env[field.model_name]
            protected = env.protected(field)
            if path == 'id' and field.model_name == records._name:
                target = records - protected
            elif path and env.in_onchange:
                target = (target.browse(env.cache[field]) - protected).filtered(
                    lambda rec: rec if path == 'id' else rec._mapped_cache(path) & records
                )
            else:
                target = target.browse(env.cache[field]) - protected

            if target:
                spec.append((field, target._ids))

        return spec


class Boolean(Field):
    type = 'boolean'
    column_type = ('bool', 'bool')

    def convert_to_column(self, value, record):
        return bool(value)

    def convert_to_cache(self, value, record, validate=True):
        return bool(value)

    def convert_to_export(self, value, record):
        if record._context.get('export_raw_data'):
            return value
        return ustr(value)


class Integer(Field):
    type = 'integer'
    column_type = ('int4', 'int4')
    _slots = {
        'group_operator': 'sum',
    }

    _description_group_operator = property(attrgetter('group_operator'))

    def convert_to_column(self, value, record):
        return int(value or 0)

    def convert_to_cache(self, value, record, validate=True):
        if isinstance(value, dict):
            # special case, when an integer field is used as inverse for a one2many
            return value.get('id', False)
        return int(value or 0)

    def convert_to_read(self, value, record, use_name_get=True):
        # Integer values greater than 2^31-1 are not supported in pure XMLRPC,
        # so we have to pass them as floats :-(
        if value and value > xmlrpclib.MAXINT:
            return float(value)
        return value

    def _update(self, records, value):
        # special case, when an integer field is used as inverse for a one2many
        records._cache[self] = value.id or 0

    def convert_to_export(self, value, record):
        if value or value == 0:
            return value if record._context.get('export_raw_data') else ustr(value)
        return ''


class Float(Field):
    """ The precision digits are given by the attribute

    :param digits: a pair (total, decimal), or a function taking a database
                   cursor and returning a pair (total, decimal)
    """
    type = 'float'
    column_cast_from = ('int4', 'numeric', 'float8')
    _slots = {
        '_digits': None,                # digits argument passed to class initializer
        'group_operator': 'sum',
    }

    def __init__(self, string=Default, digits=Default, **kwargs):
        super(Float, self).__init__(string=string, _digits=digits, **kwargs)

    @property
    def column_type(self):
        # Explicit support for "falsy" digits (0, False) to indicate a NUMERIC
        # field with no fixed precision. The values are saved in the database
        # with all significant digits.
        # FLOAT8 type is still the default when there is no precision because it
        # is faster for most operations (sums, etc.)
        return ('numeric', 'numeric') if self.digits is not None else \
               ('float8', 'double precision')

    @property
    def digits(self):
        if callable(self._digits):
            with LazyCursor() as cr:
                return self._digits(cr)
        else:
            return self._digits

    _related__digits = property(attrgetter('_digits'))
    _description_digits = property(attrgetter('digits'))
    _description_group_operator = property(attrgetter('group_operator'))

    def convert_to_column(self, value, record):
        result = float(value or 0.0)
        digits = self.digits
        if digits:
            precision, scale = digits
            result = float_repr(float_round(result, precision_digits=scale), precision_digits=scale)
        return result

    def convert_to_cache(self, value, record, validate=True):
        # apply rounding here, otherwise value in cache may be wrong!
        value = float(value or 0.0)
        if not validate:
            return value
        digits = self.digits
        return float_round(value, precision_digits=digits[1]) if digits else value

    def convert_to_export(self, value, record):
        if value or value == 0.0:
            return value if record._context.get('export_raw_data') else ustr(value)
        return ''


class Monetary(Field):
    """ The decimal precision and currency symbol are taken from the attribute

    :param currency_field: name of the field holding the currency this monetary
                           field is expressed in (default: `currency_id`)
    """
    type = 'monetary'
    column_type = ('numeric', 'numeric')
    column_cast_from = ('float8',)
    _slots = {
        'currency_field': None,
        'group_operator': 'sum',
    }

    def __init__(self, string=Default, currency_field=Default, **kwargs):
        super(Monetary, self).__init__(string=string, currency_field=currency_field, **kwargs)

    _related_currency_field = property(attrgetter('currency_field'))
    _description_currency_field = property(attrgetter('currency_field'))
    _description_group_operator = property(attrgetter('group_operator'))

    def _setup_regular_full(self, model):
        super(Monetary, self)._setup_regular_full(model)
        if not self.currency_field:
            # pick a default, trying in order: 'currency_id', 'x_currency_id'
            if 'currency_id' in model._fields:
                self.currency_field = 'currency_id'
            elif 'x_currency_id' in model._fields:
                self.currency_field = 'x_currency_id'
        assert self.currency_field in model._fields, \
            "Field %s with unknown currency_field %r" % (self, self.currency_field)

    def convert_to_column(self, value, record):
        try:
            return value.float_repr()         # see float_precision.float_repr()
        except Exception:
            return float(value or 0.0)

    def convert_to_cache(self, value, record, validate=True):
        if validate:
            currency = record[self.currency_field]
            # FIXME @rco-odoo: currency may not be already initialized if it is
            # a function or related field!
            if currency:
                value = currency.round(float(value or 0.0))
                return float_precision(value, currency.decimal_places)
        return float(value or 0.0)

    def convert_to_read(self, value, record, use_name_get=True):
        # float_precision values are not supported in pure XMLRPC
        return float(value)

    def convert_to_write(self, value, record):
        return value


class _String(Field):
    """ Abstract class for string fields. """
    _slots = {
        'translate': False,             # whether the field is translated
    }

    def __init__(self, string=Default, **kwargs):
        # translate is either True, False, or a callable
        if 'translate' in kwargs and not callable(kwargs['translate']):
            kwargs['translate'] = bool(kwargs['translate'])
        super(_String, self).__init__(string=string, **kwargs)

    _related_translate = property(attrgetter('translate'))

    def _description_translate(self, env):
        return bool(self.translate)

    def get_trans_terms(self, value):
        """ Return the sequence of terms to translate found in `value`. """
        if not callable(self.translate):
            return [value] if value else []
        terms = []
        self.translate(terms.append, value)
        return terms

    def get_trans_func(self, records):
        """ Return a translation function `translate` for `self` on the given
        records; the function call `translate(record_id, value)` translates the
        field value to the language given by the environment of `records`.
        """
        if callable(self.translate):
            rec_src_trans = records.env['ir.translation']._get_terms_translations(self, records)

            def translate(record_id, value):
                src_trans = rec_src_trans[record_id]
                return self.translate(src_trans.get, value)

        else:
            rec_trans = records.env['ir.translation']._get_ids(
                '%s,%s' % (self.model_name, self.name), 'model', records.env.lang, records.ids)

            def translate(record_id, value):
                return rec_trans.get(record_id) or value

        return translate

    def check_trans_value(self, value):
        """ Check and possibly sanitize the translated term `value`. """
        if callable(self.translate):
            # do a "no-translation" to sanitize the value
            callback = lambda term: None
            return self.translate(callback, value)
        else:
            return value


class Char(_String):
    """ Basic string field, can be length-limited, usually displayed as a
    single-line string in clients.

    :param int size: the maximum size of values stored for that field

    :param translate: enable the translation of the field's values; use
        ``translate=True`` to translate field values as a whole; ``translate``
        may also be a callable such that ``translate(callback, value)``
        translates ``value`` by using ``callback(term)`` to retrieve the
        translation of terms.
    """
    type = 'char'
    column_cast_from = ('text',)
    _slots = {
        'size': None,                   # maximum size of values (deprecated)
    }

    @property
    def column_type(self):
        return ('varchar', pg_varchar(self.size))

    def update_db_column(self, model, column):
        if (
            column and column['udt_name'] == 'varchar' and column['character_maximum_length'] and
            (self.size is None or column['character_maximum_length'] < self.size)
        ):
            # the column's varchar size does not match self.size; convert it
            sql.convert_column(model._cr, model._table, self.name, self.column_type[1])
        super(Char, self).update_db_column(model, column)

    _related_size = property(attrgetter('size'))
    _description_size = property(attrgetter('size'))

    def _setup_regular_base(self, model):
        super(Char, self)._setup_regular_base(model)
        assert isinstance(self.size, (NoneType, int)), \
            "Char field %s with non-integer size %r" % (self, self.size)

    def convert_to_column(self, value, record):
        #TODO:
        # * we need to remove the "value==False" from the next line BUT
        #   for now too many things rely on this broken behavior
        # * the value==None test should be common to all data types
        if value is None or value == False:
            return None
        # we need to convert the string to a unicode object to be able
        # to evaluate its length (and possibly truncate it) reliably
        return ustr(value)[:self.size].encode('utf8')

    def convert_to_cache(self, value, record, validate=True):
        if value is None or value is False:
            return False
        return ustr(value)[:self.size]


class Text(_String):
    """ Very similar to :class:`~.Char` but used for longer contents, does not
    have a size and usually displayed as a multiline text box.

    :param translate: enable the translation of the field's values; use
        ``translate=True`` to translate field values as a whole; ``translate``
        may also be a callable such that ``translate(callback, value)``
        translates ``value`` by using ``callback(term)`` to retrieve the
        translation of terms.
    """
    type = 'text'
    column_type = ('text', 'text')
    column_cast_from = ('varchar',)

    def convert_to_cache(self, value, record, validate=True):
        if value is None or value is False:
            return False
        return ustr(value)


class Html(_String):
    type = 'html'
    column_type = ('text', 'text')
    _slots = {
        'sanitize': True,               # whether value must be sanitized
        'sanitize_tags': True,          # whether to sanitize tags (only a white list of attributes is accepted)
        'sanitize_attributes': True,    # whether to sanitize attributes (only a white list of attributes is accepted)
        'sanitize_style': False,        # whether to sanitize style attributes
        'strip_style': False,           # whether to strip style attributes (removed and therefore not sanitized)
        'strip_classes': False,         # whether to strip classes attributes
    }

    def _setup_attrs(self, model, name):
        super(Html, self)._setup_attrs(model, name)
        # Translated sanitized html fields must use html_translate or a callable.
        if self.translate is True and self.sanitize:
            self.translate = html_translate

    _related_sanitize = property(attrgetter('sanitize'))
    _related_sanitize_tags = property(attrgetter('sanitize_tags'))
    _related_sanitize_attributes = property(attrgetter('sanitize_attributes'))
    _related_sanitize_style = property(attrgetter('sanitize_style'))
    _related_strip_style = property(attrgetter('strip_style'))
    _related_strip_classes = property(attrgetter('strip_classes'))

    _description_sanitize = property(attrgetter('sanitize'))
    _description_sanitize_tags = property(attrgetter('sanitize_tags'))
    _description_sanitize_attributes = property(attrgetter('sanitize_attributes'))
    _description_sanitize_style = property(attrgetter('sanitize_style'))
    _description_strip_style = property(attrgetter('strip_style'))
    _description_strip_classes = property(attrgetter('strip_classes'))

    def convert_to_column(self, value, record):
        if value is None or value is False:
            return None
        if self.sanitize:
            return html_sanitize(
                value, silent=True,
                sanitize_tags=self.sanitize_tags,
                sanitize_attributes=self.sanitize_attributes,
                sanitize_style=self.sanitize_style,
                strip_style=self.strip_style,
                strip_classes=self.strip_classes)
        return value

    def convert_to_cache(self, value, record, validate=True):
        if value is None or value is False:
            return False
        if validate and self.sanitize:
            return html_sanitize(
                value, silent=True,
                sanitize_tags=self.sanitize_tags,
                sanitize_attributes=self.sanitize_attributes,
                sanitize_style=self.sanitize_style,
                strip_style=self.strip_style,
                strip_classes=self.strip_classes)
        return value


class Date(Field):
    type = 'date'
    column_type = ('date', 'date')
    column_cast_from = ('timestamp',)

    @staticmethod
    def today(*args):
        """ Return the current day in the format expected by the ORM.
            This function may be used to compute default values.
        """
        return date.today().strftime(DATE_FORMAT)

    @staticmethod
    def context_today(record, timestamp=None):
        """ Return the current date as seen in the client's timezone in a format
            fit for date fields. This method may be used to compute default
            values.

            :param datetime timestamp: optional datetime value to use instead of
                the current date and time (must be a datetime, regular dates
                can't be converted between timezones.)
            :rtype: str
        """
        today = timestamp or datetime.now()
        context_today = None
        tz_name = record._context.get('tz') or record.env.user.tz
        if tz_name:
            try:
                today_utc = pytz.timezone('UTC').localize(today, is_dst=False)  # UTC = no DST
                context_today = today_utc.astimezone(pytz.timezone(tz_name))
            except Exception:
                _logger.debug("failed to compute context/client-specific today date, using UTC value for `today`",
                              exc_info=True)
        return (context_today or today).strftime(DATE_FORMAT)

    @staticmethod
    def from_string(value):
        """ Convert an ORM ``value`` into a :class:`date` value. """
        if not value:
            return None
        value = value[:DATE_LENGTH]
        return datetime.strptime(value, DATE_FORMAT).date()

    @staticmethod
    def to_string(value):
        """ Convert a :class:`date` value into the format expected by the ORM. """
        return value.strftime(DATE_FORMAT) if value else False

    def convert_to_cache(self, value, record, validate=True):
        if not value:
            return False
        if isinstance(value, basestring):
            if validate:
                # force parsing for validation
                self.from_string(value)
            return value[:DATE_LENGTH]
        return self.to_string(value)

    def convert_to_export(self, value, record):
        if not value:
            return ''
        return self.from_string(value) if record._context.get('export_raw_data') else ustr(value)


class Datetime(Field):
    type = 'datetime'
    column_type = ('timestamp', 'timestamp')
    column_cast_from = ('date',)

    @staticmethod
    def now(*args):
        """ Return the current day and time in the format expected by the ORM.
            This function may be used to compute default values.
        """
        return datetime.now().strftime(DATETIME_FORMAT)

    @staticmethod
    def context_timestamp(record, timestamp):
        """Returns the given timestamp converted to the client's timezone.
           This method is *not* meant for use as a default initializer,
           because datetime fields are automatically converted upon
           display on client side. For default values :meth:`fields.datetime.now`
           should be used instead.

           :param datetime timestamp: naive datetime value (expressed in UTC)
                                      to be converted to the client timezone
           :rtype: datetime
           :return: timestamp converted to timezone-aware datetime in context
                    timezone
        """
        assert isinstance(timestamp, datetime), 'Datetime instance expected'
        tz_name = record._context.get('tz') or record.env.user.tz
        utc_timestamp = pytz.utc.localize(timestamp, is_dst=False)  # UTC = no DST
        if tz_name:
            try:
                context_tz = pytz.timezone(tz_name)
                return utc_timestamp.astimezone(context_tz)
            except Exception:
                _logger.debug("failed to compute context/client-specific timestamp, "
                              "using the UTC value",
                              exc_info=True)
        return utc_timestamp

    @staticmethod
    def from_string(value):
        """ Convert an ORM ``value`` into a :class:`datetime` value. """
        if not value:
            return None
        value = value[:DATETIME_LENGTH]
        if len(value) == DATE_LENGTH:
            value += " 00:00:00"
        return datetime.strptime(value, DATETIME_FORMAT)

    @staticmethod
    def to_string(value):
        """ Convert a :class:`datetime` value into the format expected by the ORM. """
        return value.strftime(DATETIME_FORMAT) if value else False

    def convert_to_cache(self, value, record, validate=True):
        if not value:
            return False
        if isinstance(value, basestring):
            if validate:
                # force parsing for validation
                self.from_string(value)
            value = value[:DATETIME_LENGTH]
            if len(value) == DATE_LENGTH:
                value += " 00:00:00"
            return value
        return self.to_string(value)

    def convert_to_export(self, value, record):
        if not value:
            return ''
        return self.from_string(value) if record._context.get('export_raw_data') else ustr(value)

    def convert_to_display_name(self, value, record):
        assert record, 'Record expected'
        return Datetime.to_string(Datetime.context_timestamp(record, Datetime.from_string(value)))


class Binary(Field):
    type = 'binary'
    _slots = {
        'prefetch': False,              # not prefetched by default
        'attachment': False,            # whether value is stored in attachment
    }

    @property
    def column_type(self):
        return None if self.attachment else ('bytea', 'bytea')

    _description_attachment = property(attrgetter('attachment'))

    def convert_to_column(self, value, record):
        # Binary values may be byte strings (python 2.6 byte array), but
        # the legacy OpenERP convention is to transfer and store binaries
        # as base64-encoded strings. The base64 string may be provided as a
        # unicode in some circumstances, hence the str() cast here.
        # This str() coercion will only work for pure ASCII unicode strings,
        # on purpose - non base64 data must be passed as a 8bit byte strings.
        return psycopg2.Binary(str(value)) if value else None

    def convert_to_cache(self, value, record, validate=True):
        if isinstance(value, buffer):
            return str(value)
        if isinstance(value, (int, long)) and \
                (record._context.get('bin_size') or
                 record._context.get('bin_size_' + self.name)):
            # If the client requests only the size of the field, we return that
            # instead of the content. Presumably a separate request will be done
            # to read the actual content, if necessary.
            return human_size(value)
        return value

    def read(self, records):
        # values are stored in attachments, retrieve them
        assert self.attachment
        domain = [
            ('res_model', '=', records._name),
            ('res_field', '=', self.name),
            ('res_id', 'in', records.ids),
        ]
        # Note: the 'bin_size' flag is handled by the field 'datas' itself
        data = {att.res_id: att.datas
                for att in records.env['ir.attachment'].sudo().search(domain)}
        for record in records:
            record._cache[self.name] = data.get(record.id, False)

    def write(self, records, value):
        # retrieve the attachments that stores the value, and adapt them
        assert self.attachment
        domain = [
            ('res_model', '=', records._name),
            ('res_field', '=', self.name),
            ('res_id', 'in', records.ids),
        ]
        atts = records.env['ir.attachment'].sudo().search(domain)
        with records.env.norecompute():
            if value:
                # update the existing attachments
                atts.write({'datas': value})
                # create the missing attachments
                for record in (records - records.browse(atts.mapped('res_id'))):
                    atts.create({
                        'name': self.name,
                        'res_model': record._name,
                        'res_field': self.name,
                        'res_id': record.id,
                        'type': 'binary',
                        'datas': value,
                    })
            else:
                atts.unlink()


class Selection(Field):
    """
    :param selection: specifies the possible values for this field.
        It is given as either a list of pairs (``value``, ``string``), or a
        model method, or a method name.
    :param selection_add: provides an extension of the selection in the case
        of an overridden field. It is a list of pairs (``value``, ``string``).

    The attribute ``selection`` is mandatory except in the case of
    :ref:`related fields <field-related>` or :ref:`field extensions
    <field-incremental-definition>`.
    """
    type = 'selection'
    _slots = {
        'selection': None,              # [(value, string), ...], function or method name
    }

    def __init__(self, selection=Default, string=Default, **kwargs):
        super(Selection, self).__init__(selection=selection, string=string, **kwargs)

    @property
    def column_type(self):
        if (self.selection and
                isinstance(self.selection, list) and
                isinstance(self.selection[0][0], int)):
            return ('int4', 'integer')
        else:
            return ('varchar', pg_varchar())

    def _setup_regular_base(self, model):
        super(Selection, self)._setup_regular_base(model)
        assert self.selection is not None, "Field %s without selection" % self

    def _setup_related_full(self, model):
        super(Selection, self)._setup_related_full(model)
        # selection must be computed on related field
        field = self.related_field
        self.selection = lambda model: field._description_selection(model.env)

    def _setup_attrs(self, model, name):
        super(Selection, self)._setup_attrs(model, name)
        # determine selection (applying 'selection_add' extensions)
        for field in reversed(resolve_mro(model, name, self._can_setup_from)):
            # We cannot use field.selection or field.selection_add here
            # because those attributes are overridden by ``_setup_attrs``.
            if 'selection' in field.args:
                self.selection = field.args['selection']
            if 'selection_add' in field.args:
                # use an OrderedDict to update existing values
                selection_add = field.args['selection_add']
                self.selection = OrderedDict(self.selection + selection_add).items()

    def _description_selection(self, env):
        """ return the selection list (pairs (value, label)); labels are
            translated according to context language
        """
        selection = self.selection
        if isinstance(selection, basestring):
            return getattr(env[self.model_name], selection)()
        if callable(selection):
            return selection(env[self.model_name])

        # translate selection labels
        if env.lang:
            name = "%s,%s" % (self.model_name, self.name)
            translate = partial(
                env['ir.translation']._get_source, name, 'selection', env.lang)
            return [(value, translate(label) if label else label) for value, label in selection]
        else:
            return selection

    def get_values(self, env):
        """ return a list of the possible values """
        selection = self.selection
        if isinstance(selection, basestring):
            selection = getattr(env[self.model_name], selection)()
        elif callable(selection):
            selection = selection(env[self.model_name])
        return [value for value, _ in selection]

    def convert_to_cache(self, value, record, validate=True):
        if not validate:
            return value or False
        if value in self.get_values(record.env):
            return value
        elif not value:
            return False
        raise ValueError("Wrong value for %s: %r" % (self, value))

    def convert_to_export(self, value, record):
        if not isinstance(self.selection, list):
            # FIXME: this reproduces an existing buggy behavior!
            return value if value else ''
        for item in self._description_selection(record.env):
            if item[0] == value:
                return item[1]
        return False

    def convert_to_column(self, value, record):
        """ Convert ``value`` from the ``write`` format to the SQL format. """
        if value is None or value is False:
            return None
        if isinstance(value, unicode):
            return value.encode('utf8')
        return str(value)


class Reference(Selection):
    type = 'reference'

    @property
    def column_type(self):
        return ('varchar', pg_varchar())

    def convert_to_cache(self, value, record, validate=True):
        # cache format: (res_model, res_id) or False
        def process(res_model, res_id):
            record._prefetch[res_model].add(res_id)
            return (res_model, res_id)

        if isinstance(value, BaseModel):
            if not validate or (value._name in self.get_values(record.env) and len(value) <= 1):
                return process(value._name, value.id) if value else False
        elif isinstance(value, basestring):
            res_model, res_id = value.split(',')
            if record.env[res_model].browse(int(res_id)).exists():
                return process(res_model, int(res_id))
            else:
                return False
        elif not value:
            return False
        raise ValueError("Wrong value for %s: %r" % (self, value))

    def convert_to_record(self, value, record):
        return value and record.env[value[0]].browse([value[1]], record._prefetch)

    def convert_to_read(self, value, record, use_name_get=True):
        return "%s,%s" % (value._name, value.id) if value else False

    def convert_to_export(self, value, record):
        return value.name_get()[0][1] if value else ''

    def convert_to_display_name(self, value, record):
        return ustr(value and value.display_name)


class _Relational(Field):
    """ Abstract class for relational fields. """
    relational = True
    _slots = {
        'domain': [],                   # domain for searching values
        'context': {},                  # context for searching values
    }

    def _setup_regular_base(self, model):
        super(_Relational, self)._setup_regular_base(model)
        if self.comodel_name not in model.pool:
            _logger.warning("Field %s with unknown comodel_name %r", self, self.comodel_name)
            self.comodel_name = '_unknown'

    @property
    def _related_domain(self):
        if callable(self.domain):
            # will be called with another model than self's
            return lambda recs: self.domain(recs.env[self.model_name])
        else:
            # maybe not correct if domain is a string...
            return self.domain

    _related_context = property(attrgetter('context'))

    _description_relation = property(attrgetter('comodel_name'))
    _description_context = property(attrgetter('context'))

    def _description_domain(self, env):
        return self.domain(env[self.model_name]) if callable(self.domain) else self.domain

    def null(self, record):
        return record.env[self.comodel_name]

    def modified(self, records):
        # Invalidate cache for inverse fields, too. Note that the recomputation
        # of fields that depend on inverse fields is already covered by the
        # triggers.
        spec = super(_Relational, self).modified(records)
        for invf in records._field_inverses[self]:
            spec.append((invf, None))
        return spec


class Many2one(_Relational):
    """ The value of such a field is a recordset of size 0 (no
    record) or 1 (a single record).

    :param comodel_name: name of the target model (string)

    :param domain: an optional domain to set on candidate values on the
        client side (domain or string)

    :param context: an optional context to use on the client side when
        handling that field (dictionary)

    :param ondelete: what to do when the referred record is deleted;
        possible values are: ``'set null'``, ``'restrict'``, ``'cascade'``

    :param auto_join: whether JOINs are generated upon search through that
        field (boolean, by default ``False``)

    :param delegate: set it to ``True`` to make fields of the target model
        accessible from the current model (corresponds to ``_inherits``)

    The attribute ``comodel_name`` is mandatory except in the case of related
    fields or field extensions.
    """
    type = 'many2one'
    column_type = ('int4', 'int4')
    _slots = {
        'ondelete': 'set null',         # what to do when value is deleted
        'auto_join': False,             # whether joins are generated upon search
        'delegate': False,              # whether self implements delegation
    }

    def __init__(self, comodel_name=Default, string=Default, **kwargs):
        super(Many2one, self).__init__(comodel_name=comodel_name, string=string, **kwargs)

    def _setup_attrs(self, model, name):
        super(Many2one, self)._setup_attrs(model, name)
        # determine self.delegate
        if not self.delegate:
            self.delegate = name in model._inherits.values()

    def update_db(self, model, columns):
        comodel = model.env[self.comodel_name]
        if not model.is_transient() and comodel.is_transient():
            raise ValueError('Many2one %s from Model to TransientModel is forbidden' % self)
        if model.is_transient() and not comodel.is_transient():
            # Many2one relations from TransientModel Model are annoying because
            # they can block deletion due to foreign keys. So unless stated
            # otherwise, we default them to ondelete='cascade'.
            self.ondelete = self.ondelete or 'cascade'
        return super(Many2one, self).update_db(model, columns)

    def update_db_column(self, model, column):
        super(Many2one, self).update_db_column(model, column)
        model.pool.post_init(self.update_db_foreign_key, model, column)

    def update_db_foreign_key(self, model, column):
        comodel = model.env[self.comodel_name]
        # ir_actions is inherited, so foreign key doesn't work on it
        if not comodel._auto or comodel._table == 'ir_actions':
            return
        # create/update the foreign key, and reflect it in 'ir.model.constraint'
        process = sql.fix_foreign_key if column else sql.add_foreign_key
        new = process(model._cr, model._table, self.name, comodel._table, 'id', self.ondelete or 'set null')
        if new:
            conname = '%s_%s_fkey' % (model._table, self.name)
            model.env['ir.model.constraint']._reflect_constraint(model, conname, 'f', None, self._module)

    def _update(self, records, value):
        """ Update the cached value of ``self`` for ``records`` with ``value``.
        This is used to reflect the assignment ``value[name] = records``, where
        ``name`` is the inverse field of ``self``.
        """
        records._cache[self] = self.convert_to_cache(value, records, validate=False)

    def convert_to_column(self, value, record):
        return value or None

    def convert_to_cache(self, value, record, validate=True):
        # cache format: tuple(ids)
        def process(ids):
            return record._prefetch[self.comodel_name].update(ids) or ids

        if type(value) in IdType:
            return process((value,))
        elif isinstance(value, BaseModel):
            if not validate or (value._name == self.comodel_name and len(value) <= 1):
                return process(value._ids)
            raise ValueError("Wrong value for %s: %r" % (self, value))
        elif isinstance(value, tuple):
            # value is either a pair (id, name), or a tuple of ids
            return process(value[:1])
        elif isinstance(value, dict):
            return process(record.env[self.comodel_name].new(value)._ids)
        else:
            return ()

    def convert_to_record(self, value, record):
        return record.env[self.comodel_name]._browse(value, record.env, record._prefetch)

    def convert_to_read(self, value, record, use_name_get=True):
        if use_name_get and value:
            # evaluate name_get() as superuser, because the visibility of a
            # many2one field value (id and name) depends on the current record's
            # access rights, and not the value's access rights.
            try:
                # performance: value.sudo() prefetches the same records as value
                return value.sudo().name_get()[0]
            except MissingError:
                # Should not happen, unless the foreign key is missing.
                return False
        else:
            return value.id

    def convert_to_write(self, value, record):
        return value.id

    def convert_to_export(self, value, record):
        return value.name_get()[0][1] if value else ''

    def convert_to_display_name(self, value, record):
        return ustr(value.display_name)

    def convert_to_onchange(self, value, record, fnames=()):
        if not value.id:
            return False
        return super(Many2one, self).convert_to_onchange(value, record, fnames)

class UnionUpdate(SpecialValue):
    """ Placeholder for a value update; when this value is taken from the cache,
        it returns ``record[field.name] | value`` and stores it in the cache.
    """
    def __init__(self, field, record, value):
        self.args = (field, record, value)

    def get(self):
        field, record, value = self.args
        # in order to read the current field's value, remove self from cache
        del record._cache[field]
        # read the current field's value, and update it in cache only
        value = field.convert_to_cache(record[field.name] | value, record, validate=False)
        record._cache[field] = value
        return value


class _RelationalMulti(_Relational):
    """ Abstract class for relational fields *2many. """

    def _update(self, records, value):
        """ Update the cached value of ``self`` for ``records`` with ``value``. """
        for record in records:
            if self in record._cache:
                val = self.convert_to_cache(record[self.name] | value, record, validate=False)
            else:
                val = UnionUpdate(self, record, value)
            record._cache[self] = val

    def convert_to_cache(self, value, record, validate=True):
        # cache format: tuple(ids)
        def process(ids):
            return record._prefetch[self.comodel_name].update(ids) or ids

        if isinstance(value, BaseModel):
            if not validate or (value._name == self.comodel_name):
                return process(value._ids)
        elif isinstance(value, (list, tuple)):
            # value is a list/tuple of commands, dicts or record ids
            comodel = record.env[self.comodel_name]
            # determine the value ids; by convention empty on new records
            ids = OrderedSet(record[self.name].ids if record.id else ())
            # modify ids with the commands
            for command in value:
                if isinstance(command, (tuple, list)):
                    if command[0] == 0:
                        ids.add(comodel.new(command[2]).id)
                    elif command[0] == 1:
                        comodel.browse(command[1]).update(command[2])
                        ids.add(command[1])
                    elif command[0] == 2:
                        # note: the record will be deleted by write()
                        ids.discard(command[1])
                    elif command[0] == 3:
                        ids.discard(command[1])
                    elif command[0] == 4:
                        ids.add(command[1])
                    elif command[0] == 5:
                        ids.clear()
                    elif command[0] == 6:
                        ids = OrderedSet(command[2])
                elif isinstance(command, dict):
                    ids.add(comodel.new(command).id)
                else:
                    ids.add(command)
            # return result as a tuple
            return process(tuple(ids))
        elif not value:
            return ()
        raise ValueError("Wrong value for %s: %s" % (self, value))

    def convert_to_record(self, value, record):
        return record.env[self.comodel_name]._browse(value, record.env, record._prefetch)

    def convert_to_read(self, value, record, use_name_get=True):
        return value.ids

    def convert_to_write(self, value, record):
        # make result with new and existing records
        result = [(6, 0, [])]
        for record in value:
            if not record.id:
                values = {name: record[name] for name in record._cache}
                values = record._convert_to_write(values)
                result.append((0, 0, values))
            elif record._is_dirty():
                values = {name: record[name] for name in record._get_dirty()}
                values = record._convert_to_write(values)
                result.append((1, record.id, values))
            else:
                result[0][2].append(record.id)
        return result

    def convert_to_onchange(self, value, record, fnames=()):
        # return the recordset value as a list of commands; the commands may
        # give all fields values, the client is responsible for figuring out
        # which fields are actually dirty
        converters = [(name, value._fields[name].convert_to_onchange)
                      for name in fnames if name != 'id']
        result = [(5,)]
        for record in value:
            vals = {name: convert(record[name], record) for name, convert in converters}
            if not record.id:
                result.append((0, 0, vals))
            elif vals:
                result.append((1, record.id, vals))
            else:
                result.append((4, record.id))
        return result

    def convert_to_export(self, value, record):
        return ','.join(name for id, name in value.name_get()) if value else ''

    def convert_to_display_name(self, value, record):
        raise NotImplementedError()

    def _compute_related(self, records):
        """ Compute the related field ``self`` on ``records``. """
        super(_RelationalMulti, self)._compute_related(records)
        if self.related_sudo:
            # determine which records in the relation are actually accessible
            target = records.mapped(self.name)
            target_ids = set(target.search([('id', 'in', target.ids)]).ids)
            accessible = lambda target: target.id in target_ids
            # filter values to keep the accessible records only
            for record in records:
                record[self.name] = record[self.name].filtered(accessible)

    def _setup_regular_base(self, model):
        super(_RelationalMulti, self)._setup_regular_base(model)
        if isinstance(self.domain, list):
            self.depends += tuple(
                self.name + '.' + arg[0]
                for arg in self.domain
                if isinstance(arg, (tuple, list)) and isinstance(arg[0], basestring)
            )


class One2many(_RelationalMulti):
    """ One2many field; the value of such a field is the recordset of all the
        records in ``comodel_name`` such that the field ``inverse_name`` is equal to
        the current record.

        :param comodel_name: name of the target model (string)

        :param inverse_name: name of the inverse ``Many2one`` field in
            ``comodel_name`` (string)

        :param domain: an optional domain to set on candidate values on the
            client side (domain or string)

        :param context: an optional context to use on the client side when
            handling that field (dictionary)

        :param auto_join: whether JOINs are generated upon search through that
            field (boolean, by default ``False``)

        :param limit: optional limit to use upon read (integer)

        The attributes ``comodel_name`` and ``inverse_name`` are mandatory except in
        the case of related fields or field extensions.
    """
    type = 'one2many'
    _slots = {
        'inverse_name': None,           # name of the inverse field
        'auto_join': False,             # whether joins are generated upon search
        'limit': None,                  # optional limit to use upon read
        'copy': False,                  # o2m are not copied by default
    }

    def __init__(self, comodel_name=Default, inverse_name=Default, string=Default, **kwargs):
        super(One2many, self).__init__(
            comodel_name=comodel_name,
            inverse_name=inverse_name,
            string=string,
            **kwargs
        )

    def _setup_regular_full(self, model):
        super(One2many, self)._setup_regular_full(model)
        if self.inverse_name:
            # link self to its inverse field and vice-versa
            comodel = model.env[self.comodel_name]
            invf = comodel._fields[self.inverse_name]
            # In some rare cases, a ``One2many`` field can link to ``Int`` field
            # (res_model/res_id pattern). Only inverse the field if this is
            # a ``Many2one`` field.
            if isinstance(invf, Many2one):
                model._field_inverses.add(self, invf)
                comodel._field_inverses.add(invf, self)

    _description_relation_field = property(attrgetter('inverse_name'))

    def convert_to_onchange(self, value, record, fnames=()):
        fnames = set(fnames or ())
        fnames.discard(self.inverse_name)
        return super(One2many, self).convert_to_onchange(value, record, fnames)

    def update_db(self, model, columns):
        if self.comodel_name in model.env:
            comodel = model.env[self.comodel_name]
            if self.inverse_name not in comodel._fields:
                raise UserError(_("No inverse field %r found for %r") % (self.inverse_name, self.comodel_name))

    def read(self, records):
        # retrieve the lines in the comodel
        comodel = records.env[self.comodel_name].with_context(**self.context)
        inverse = self.inverse_name
        domain = self.domain(records) if callable(self.domain) else self.domain
        domain = domain + [(inverse, 'in', records.ids)]
        lines = comodel.search(domain, limit=self.limit)

        # group lines by inverse field (without prefetching other fields)
        group = defaultdict(list)
        for line in lines.with_context(prefetch_fields=False):
            # line[inverse] may be a record or an integer
            group[int(line[inverse])].append(line.id)

        # store result in cache
        for record in records:
            record._cache[self.name] = tuple(group[record.id])

    def write(self, records, value):
        comodel = records.env[self.comodel_name].with_context(**self.context)
        inverse = self.inverse_name

        with records.env.norecompute():
            for act in (value or []):
                if act[0] == 0:
                    for record in records:
                        act[2][inverse] = record.id
                        comodel.create(act[2])
                elif act[0] == 1:
                    comodel.browse(act[1]).write(act[2])
                elif act[0] == 2:
                    comodel.browse(act[1]).unlink()
                elif act[0] == 3:
                    inverse_field = comodel._fields[inverse]
                    if inverse_field.ondelete == 'cascade':
                        comodel.browse(act[1]).unlink()
                    else:
                        comodel.browse(act[1]).write({inverse: False})
                elif act[0] == 4:
                    record = records[-1]
                    line = comodel.browse(act[1])
                    line_sudo = line.sudo().with_context(prefetch_fields=False)
                    if int(line_sudo[inverse]) != record.id:
                        line.write({inverse: record.id})
                elif act[0] == 5:
                    domain = self.domain(records) if callable(self.domain) else self.domain
                    domain = domain + [(inverse, 'in', records.ids)]
                    inverse_field = comodel._fields[inverse]
                    if inverse_field.ondelete == 'cascade':
                        comodel.search(domain).unlink()
                    else:
                        comodel.search(domain).write({inverse: False})
                elif act[0] == 6:
                    record = records[-1]
                    comodel.browse(act[2]).write({inverse: record.id})
                    query = "SELECT id FROM %s WHERE %s=%%s AND id <> ALL(%%s)" % (comodel._table, inverse)
                    comodel._cr.execute(query, (record.id, act[2] or [0]))
                    lines = comodel.browse([row[0] for row in comodel._cr.fetchall()])
                    inverse_field = comodel._fields[inverse]
                    if inverse_field.ondelete == 'cascade':
                        lines.unlink()
                    else:
                        lines.write({inverse: False})


class Many2many(_RelationalMulti):
    """ Many2many field; the value of such a field is the recordset.

        :param comodel_name: name of the target model (string)

        The attribute ``comodel_name`` is mandatory except in the case of related
        fields or field extensions.

        :param relation: optional name of the table that stores the relation in
            the database (string)

        :param column1: optional name of the column referring to "these" records
            in the table ``relation`` (string)

        :param column2: optional name of the column referring to "those" records
            in the table ``relation`` (string)

        The attributes ``relation``, ``column1`` and ``column2`` are optional. If not
        given, names are automatically generated from model names, provided
        ``model_name`` and ``comodel_name`` are different!

        :param domain: an optional domain to set on candidate values on the
            client side (domain or string)

        :param context: an optional context to use on the client side when
            handling that field (dictionary)

        :param limit: optional limit to use upon read (integer)

    """
    type = 'many2many'
    _slots = {
        'relation': None,               # name of table
        'column1': None,                # column of table referring to model
        'column2': None,                # column of table referring to comodel
        'auto_join': False,             # whether joins are generated upon search
        'limit': None,                  # optional limit to use upon read
    }

    def __init__(self, comodel_name=Default, relation=Default, column1=Default,
                 column2=Default, string=Default, **kwargs):
        super(Many2many, self).__init__(
            comodel_name=comodel_name,
            relation=relation,
            column1=column1,
            column2=column2,
            string=string,
            **kwargs
        )

    def _setup_regular_base(self, model):
        super(Many2many, self)._setup_regular_base(model)
        if self.store:
            if not (self.relation and self.column1 and self.column2):
                # table name is based on the stable alphabetical order of tables
                comodel = model.env[self.comodel_name]
                if not self.relation:
                    tables = sorted([model._table, comodel._table])
                    assert tables[0] != tables[1], \
                        "%s: Implicit/canonical naming of many2many relationship " \
                        "table is not possible when source and destination models " \
                        "are the same" % self
                    self.relation = '%s_%s_rel' % tuple(tables)
                if not self.column1:
                    self.column1 = '%s_id' % model._table
                if not self.column2:
                    self.column2 = '%s_id' % comodel._table
            # check validity of table name
            check_pg_name(self.relation)

    def _setup_regular_full(self, model):
        super(Many2many, self)._setup_regular_full(model)
        if self.relation:
            m2m = model.pool._m2m
            # if inverse field has already been setup, it is present in m2m
            invf = m2m.get((self.relation, self.column2, self.column1))
            if invf:
                comodel = model.env[self.comodel_name]
                model._field_inverses.add(self, invf)
                comodel._field_inverses.add(invf, self)
            else:
                # add self in m2m, so that its inverse field can find it
                m2m[(self.relation, self.column1, self.column2)] = self

    def update_db(self, model, columns):
        cr = model._cr
        # Do not reflect relations for custom fields, as they do not belong to a
        # module. They are automatically removed when dropping the corresponding
        # 'ir.model.field'.
        if not self.manual:
            model.pool.post_init(model.env['ir.model.relation']._reflect_relation,
                                 model, self.relation, self._module)
        if not sql.table_exists(cr, self.relation):
            comodel = model.env[self.comodel_name]
            query = """
                CREATE TABLE "{rel}" ("{id1}" INTEGER NOT NULL,
                                      "{id2}" INTEGER NOT NULL,
                                      UNIQUE("{id1}","{id2}"));
                COMMENT ON TABLE "{rel}" IS %s;
                CREATE INDEX ON "{rel}" ("{id1}");
                CREATE INDEX ON "{rel}" ("{id2}")
            """.format(rel=self.relation, id1=self.column1, id2=self.column2)
            cr.execute(query, ['RELATION BETWEEN %s AND %s' % (model._table, comodel._table)])
            _schema.debug("Create table %r: m2m relation between %r and %r", self.relation, model._table, comodel._table)
            model.pool.post_init(self.update_db_foreign_keys, model)
            return True

    def update_db_foreign_keys(self, model):
        """ Add the foreign keys corresponding to the field's relation table. """
        cr = model._cr
        comodel = model.env[self.comodel_name]
        reflect = model.env['ir.model.constraint']._reflect_constraint
        # create foreign key references with ondelete=cascade, unless the targets are SQL views
        if sql.table_kind(cr, model._table) != 'v':
            sql.add_foreign_key(cr, self.relation, self.column1, model._table, 'id', 'cascade')
            reflect(model, '%s_%s_fkey' % (self.relation, self.column1), 'f', None, self._module)
        if sql.table_kind(cr, comodel._table) != 'v':
            sql.add_foreign_key(cr, self.relation, self.column2, comodel._table, 'id', 'cascade')
            reflect(model, '%s_%s_fkey' % (self.relation, self.column2), 'f', None, self._module)

    def read(self, records):
        comodel = records.env[self.comodel_name]

        # String domains are supposed to be dynamic and evaluated on client-side
        # only (thus ignored here).
        domain = self.domain if isinstance(self.domain, list) else []

        wquery = comodel._where_calc(domain)
        comodel._apply_ir_rules(wquery, 'read')
        order_by = comodel._generate_order_by(None, wquery)
        from_c, where_c, where_params = wquery.get_sql()
        query = """ SELECT {rel}.{id1}, {rel}.{id2} FROM {rel}, {from_c}
                    WHERE {where_c} AND {rel}.{id1} IN %s AND {rel}.{id2} = {tbl}.id
                    {order_by} {limit} OFFSET {offset}
                """.format(rel=self.relation, id1=self.column1, id2=self.column2,
                           tbl=comodel._table, from_c=from_c, where_c=where_c or '1=1',
                           limit=(' LIMIT %d' % self.limit) if self.limit else '',
                           offset=0, order_by=order_by)
        where_params.append(tuple(records.ids))

        # retrieve lines and group them by record
        group = defaultdict(list)
        records._cr.execute(query, where_params)
        for row in records._cr.fetchall():
            group[row[0]].append(row[1])

        # store result in cache
        for record in records:
            record._cache[self.name] = tuple(group[record.id])

    def write(self, records, value):
        cr = records._cr
        comodel = records.env[self.comodel_name]
        parts = dict(rel=self.relation, id1=self.column1, id2=self.column2)

        def link(ids):
            # beware of duplicates when inserting
            query = """ INSERT INTO {rel} ({id1}, {id2})
                        (SELECT a, b FROM unnest(%s) AS a, unnest(%s) AS b)
                        EXCEPT (SELECT {id1}, {id2} FROM {rel} WHERE {id1} IN %s)
                    """.format(**parts)
            for sub_ids in cr.split_for_in_conditions(ids):
                cr.execute(query, (records.ids, list(sub_ids), tuple(records.ids)))

        def unlink(ids):
            query = """ DELETE FROM {rel}
                        WHERE {id1} IN %s AND {id2} IN %s
                    """.format(**parts)
            cr.execute(query, (tuple(records.ids), tuple(ids)))

        def unlink_all():
            # remove all records for which user has access rights
            clauses, params, tables = comodel.env['ir.rule'].domain_get(comodel._name)
            cond = " AND ".join(clauses) if clauses else "1=1"
            query = """ DELETE FROM {rel} USING {tables}
                        WHERE {rel}.{id1} IN %s AND {rel}.{id2}={table}.id AND {cond}
                    """.format(table=comodel._table, tables=','.join(tables), cond=cond, **parts)
            cr.execute(query, [tuple(records.ids)] + params)

        for act in (value or []):
            if not isinstance(act, (list, tuple)) or not act:
                continue
            if act[0] == 0:
                lines = records.mapped(lambda record: comodel.create(act[2]))
                link(lines.ids)
            elif act[0] == 1:
                comodel.browse(act[1]).write(act[2])
            elif act[0] == 2:
                comodel.browse(act[1]).unlink()
            elif act[0] == 3:
                unlink([act[1]])
            elif act[0] == 4:
                link([act[1]])
            elif act[0] == 5:
                unlink_all()
            elif act[0] == 6:
                unlink_all()
                link(act[2])


class Id(Field):
    """ Special case for field 'id'. """
    type = 'integer'
    column_type = ('int4', 'int4')
    _slots = {
        'string': 'ID',
        'store': True,
        'readonly': True,
    }

    def update_db(self, model, columns):
        pass                            # this column is created with the table

    def __get__(self, record, owner):
        if record is None:
            return self         # the field is accessed through the class owner
        if not record:
            return False
        return record.ensure_one()._ids[0]

    def __set__(self, record, value):
        raise TypeError("field 'id' cannot be assigned")

# imported here to avoid dependency cycle issues
from odoo import SUPERUSER_ID
from .exceptions import AccessError, MissingError, UserError
from .models import check_pg_name, BaseModel, IdType
