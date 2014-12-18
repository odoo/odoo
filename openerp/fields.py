# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-2014 OpenERP (<http://www.openerp.com>).
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

""" High-level objects for fields. """

from datetime import date, datetime
from functools import partial
from operator import attrgetter
from types import NoneType
import logging
import pytz
import xmlrpclib

from openerp.tools import float_round, ustr, html_sanitize
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

DATE_LENGTH = len(date.today().strftime(DATE_FORMAT))
DATETIME_LENGTH = len(datetime.now().strftime(DATETIME_FORMAT))

_logger = logging.getLogger(__name__)

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
    """ Return `value`, or call its getter if `value` is a :class:`SpecialValue`. """
    return value.get() if isinstance(value, SpecialValue) else value


def resolve_all_mro(cls, name, reverse=False):
    """ Return the (successively overridden) values of attribute `name` in `cls`
        in mro order, or inverse mro order if `reverse` is true.
    """
    klasses = reversed(cls.__mro__) if reverse else cls.__mro__
    for klass in klasses:
        if name in klass.__dict__:
            yield klass.__dict__[name]


class MetaField(type):
    """ Metaclass for field classes. """
    by_type = {}

    def __init__(cls, name, bases, attrs):
        super(MetaField, cls).__init__(name, bases, attrs)
        if cls.type:
            cls.by_type[cls.type] = cls

        # compute class attributes to avoid calling dir() on fields
        cls.column_attrs = []
        cls.related_attrs = []
        cls.description_attrs = []
        for attr in dir(cls):
            if attr.startswith('_column_'):
                cls.column_attrs.append((attr[8:], attr))
            elif attr.startswith('_related_'):
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
            value, or a function taking a recordset and returning a value

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
        for the attribute `compute`.

        :param compute: name of a method that computes the field

        :param inverse: name of a method that inverses the field (optional)

        :param search: name of a method that implement search on the field (optional)

        :param store: whether the field is stored in database (boolean, by
            default ``False`` on computed fields)

        The methods given for `compute`, `inverse` and `search` are model
        methods. Their signature is shown in the following example::

            upper = fields.Char(compute='_compute_upper',
                                inverse='_inverse_upper',
                                search='_search_upper')

            @api.depends('name')
            def _compute_upper(self):
                for rec in self:
                    self.upper = self.name.upper() if self.name else False

            def _inverse_upper(self):
                for rec in self:
                    self.name = self.upper.lower() if self.upper else False

            def _search_upper(self, operator, value):
                if operator == 'like':
                    operator = 'ilike'
                return [('name', operator, value)]

        The compute method has to assign the field on all records of the invoked
        recordset. The decorator :meth:`openerp.api.depends` must be applied on
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
        condition: `field operator value`.

        .. _field-related:

        .. rubric:: Related fields

        The value of a related field is given by following a sequence of
        relational fields and reading a field on the reached model. The complete
        sequence of fields to traverse is specified by the attribute

        :param related: sequence of field names

        Some field attributes are automatically copied from the source field if
        they are not redefined: `string`, `help`, `readonly`, `required` (only
        if all fields in the sequence are required), `groups`, `digits`, `size`,
        `translate`, `sanitize`, `selection`, `comodel_name`, `domain`,
        `context`. All semantic-free attributes are copied from the source
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
        is extended (see :class:`~openerp.models.Model`), one can also extend
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

    _attrs = None               # dictionary with all field attributes
    _free_attrs = None          # list of semantic-free attribute names

    automatic = False           # whether the field is automatically created ("magic" field)
    inherited = False           # whether the field is inherited (_inherits)
    column = None               # the column corresponding to the field
    setup_done = False          # whether the field has been set up

    name = None                 # name of the field
    type = None                 # type of the field (string)
    relational = False          # whether the field is a relational one
    model_name = None           # name of the model of this field
    comodel_name = None         # name of the model of values (if relational)
    inverse_fields = None       # list of inverse fields (objects)

    store = True                # whether the field is stored in database
    index = False               # whether the field is indexed in database
    manual = False              # whether the field is a custom field
    copy = True                 # whether the field is copied over by BaseModel.copy()
    depends = ()                # collection of field dependencies
    recursive = False           # whether self depends on itself
    compute = None              # compute(recs) computes field on recs
    inverse = None              # inverse(recs) inverses field on recs
    search = None               # search(recs, operator, value) searches on self
    related = None              # sequence of field names, for related fields
    related_sudo = True         # whether related fields should be read as admin
    company_dependent = False   # whether `self` is company-dependent (property field)
    default = None              # default(recs) returns the default value

    string = None               # field label
    help = None                 # field tooltip
    readonly = False
    required = False
    states = None
    groups = False              # csv list of group xml ids
    change_default = None       # whether the field may trigger a "user-onchange"
    deprecated = None           # whether the field is ... deprecated

    def __init__(self, string=None, **kwargs):
        kwargs['string'] = string
        self._attrs = {key: val for key, val in kwargs.iteritems() if val is not None}
        self._free_attrs = []

    def new(self, **kwargs):
        """ Return a field of the same type as `self`, with its own parameters. """
        return type(self)(**kwargs)

    def set_class_name(self, cls, name):
        """ Assign the model class and field name of `self`. """
        self.model_name = cls._name
        self.name = name

        # determine all inherited field attributes
        attrs = {}
        for field in resolve_all_mro(cls, name, reverse=True):
            if isinstance(field, type(self)):
                attrs.update(field._attrs)
            else:
                attrs.clear()
        attrs.update(self._attrs)       # necessary in case self is not in cls

        # initialize `self` with `attrs`
        if attrs.get('compute'):
            # by default, computed fields are not stored, not copied and readonly
            attrs['store'] = attrs.get('store', False)
            attrs['copy'] = attrs.get('copy', False)
            attrs['readonly'] = attrs.get('readonly', not attrs.get('inverse'))
        if attrs.get('related'):
            # by default, related fields are not stored
            attrs['store'] = attrs.get('store', False)

        # fix for function fields overridden by regular columns
        if not isinstance(attrs.get('column'), (NoneType, fields.function)):
            attrs.pop('store', None)

        for attr, value in attrs.iteritems():
            if not hasattr(self, attr):
                self._free_attrs.append(attr)
            setattr(self, attr, value)

        if not self.string and not self.related:
            # related fields get their string from their parent field
            self.string = name.replace('_', ' ').capitalize()

        # determine self.default and cls._defaults in a consistent way
        self._determine_default(cls, name)

        self.reset()

    def _determine_default(self, cls, name):
        """ Retrieve the default value for `self` in the hierarchy of `cls`, and
            determine `self.default` and `cls._defaults` accordingly.
        """
        self.default = None

        # traverse the class hierarchy upwards, and take the first field
        # definition with a default or _defaults for self
        for klass in cls.__mro__:
            if name in klass.__dict__:
                field = klass.__dict__[name]
                if not isinstance(field, type(self)):
                    # klass contains another value overridden by self
                    return

                if 'default' in field._attrs:
                    # take the default in field, and adapt it for cls._defaults
                    value = field._attrs['default']
                    if callable(value):
                        from openerp import api
                        self.default = value
                        cls._defaults[name] = api.model(
                            lambda recs: self.convert_to_write(value(recs))
                        )
                    else:
                        self.default = lambda recs: value
                        cls._defaults[name] = value
                    return

            defaults = klass.__dict__.get('_defaults') or {}
            if name in defaults:
                # take the value from _defaults, and adapt it for self.default
                value = defaults[name]
                if callable(value):
                    func = lambda recs: value(recs._model, recs._cr, recs._uid, recs._context)
                else:
                    func = lambda recs: value
                self.default = lambda recs: self.convert_to_cache(
                    func(recs), recs, validate=False,
                )
                cls._defaults[name] = value
                return

    def __str__(self):
        return "%s.%s" % (self.model_name, self.name)

    def __repr__(self):
        return "%s.%s" % (self.model_name, self.name)

    ############################################################################
    #
    # Field setup
    #

    def reset(self):
        """ Prepare `self` for a new setup. """
        self.setup_done = False
        # self._triggers is a set of pairs (field, path) that represents the
        # computed fields that depend on `self`. When `self` is modified, it
        # invalidates the cache of each `field`, and registers the records to
        # recompute based on `path`. See method `modified` below for details.
        self._triggers = set()
        self.inverse_fields = []

    def setup(self, env):
        """ Complete the setup of `self` (dependencies, recomputation triggers,
            and other properties). This method is idempotent: it has no effect
            if `self` has already been set up.
        """
        if not self.setup_done:
            self._setup(env)
            self.setup_done = True

    def _setup(self, env):
        """ Do the actual setup of `self`. """
        if self.related:
            self._setup_related(env)
        else:
            self._setup_regular(env)

        # put invalidation/recomputation triggers on field dependencies
        model = env[self.model_name]
        for path in self.depends:
            self._setup_dependency([], model, path.split('.'))

        # put invalidation triggers on model dependencies
        for dep_model_name, field_names in model._depends.iteritems():
            dep_model = env[dep_model_name]
            dep_model._setup_fields()
            for field_name in field_names:
                field = dep_model._fields[field_name]
                field._triggers.add((self, None))

    #
    # Setup of related fields
    #

    def _setup_related(self, env):
        """ Setup the attributes of a related field. """
        # fix the type of self.related if necessary
        if isinstance(self.related, basestring):
            self.related = tuple(self.related.split('.'))

        # determine the chain of fields, and make sure they are all set up
        recs = env[self.model_name]
        fields = []
        for name in self.related:
            recs._setup_fields()
            field = recs._fields[name]
            recs = recs[name]
            fields.append(field)

        self.related_field = field

        # check type consistency
        if self.type != field.type:
            raise Warning("Type of related field %s is inconsistent with %s" % (self, field))

        # determine dependencies, compute, inverse, and search
        self.depends = ('.'.join(self.related),)
        self.compute = self._compute_related
        self.inverse = self._inverse_related
        if field._description_searchable:
            # allow searching on self only if the related field is searchable
            self.search = self._search_related

        # copy attributes from field to self (string, help, etc.)
        for attr, prop in self.related_attrs:
            if not getattr(self, attr):
                setattr(self, attr, getattr(field, prop))

        for attr in field._free_attrs:
            if attr not in self._free_attrs:
                self._free_attrs.append(attr)
                setattr(self, attr, getattr(field, attr))

        # special case for states: copy it only for inherited fields
        if not self.states and self.inherited:
            self.states = field.states

        # special case for required: check if all fields are required
        if not self.store and not self.required:
            self.required = all(field.required for field in fields)

    def _compute_related(self, records):
        """ Compute the related field `self` on `records`. """
        # when related_sudo, bypass access rights checks when reading values
        others = records.sudo() if self.related_sudo else records
        for record, other in zip(records, others):
            if not record.id:
                # draft record, do not switch to another environment
                other = record
            # traverse the intermediate fields; follow the first record at each step
            for name in self.related[:-1]:
                other = other[name][:1]
            record[self.name] = other[self.related[-1]]

    def _inverse_related(self, records):
        """ Inverse the related field `self` on `records`. """
        for record in records:
            other = record
            # traverse the intermediate fields, and keep at most one record
            for name in self.related[:-1]:
                other = other[name][:1]
            if other:
                other[self.related[-1]] = record[self.name]

    def _search_related(self, records, operator, value):
        """ Determine the domain to search on field `self`. """
        return [('.'.join(self.related), operator, value)]

    # properties used by _setup_related() to copy values from related field
    _related_comodel_name = property(attrgetter('comodel_name'))
    _related_string = property(attrgetter('string'))
    _related_help = property(attrgetter('help'))
    _related_readonly = property(attrgetter('readonly'))
    _related_groups = property(attrgetter('groups'))

    @property
    def base_field(self):
        """ Return the base field of an inherited field, or `self`. """
        return self.related_field if self.inherited else self

    #
    # Setup of non-related fields
    #

    def _setup_regular(self, env):
        """ Setup the attributes of a non-related field. """
        recs = env[self.model_name]

        def make_depends(deps):
            return tuple(deps(recs) if callable(deps) else deps)

        # convert compute into a callable and determine depends
        if isinstance(self.compute, basestring):
            # if the compute method has been overridden, concatenate all their _depends
            self.depends = ()
            for method in resolve_all_mro(type(recs), self.compute, reverse=True):
                self.depends += make_depends(getattr(method, '_depends', ()))
            self.compute = getattr(type(recs), self.compute)
        else:
            self.depends = make_depends(getattr(self.compute, '_depends', ()))

        # convert inverse and search into callables
        if isinstance(self.inverse, basestring):
            self.inverse = getattr(type(recs), self.inverse)
        if isinstance(self.search, basestring):
            self.search = getattr(type(recs), self.search)

    def _setup_dependency(self, path0, model, path1):
        """ Make `self` depend on `model`; `path0 + path1` is a dependency of
            `self`, and `path0` is the sequence of field names from `self.model`
            to `model`.
        """
        env = model.env
        head, tail = path1[0], path1[1:]

        model._setup_fields()
        if head == '*':
            # special case: add triggers on all fields of model (except self)
            fields = set(model._fields.itervalues()) - set([self])
        else:
            fields = [model._fields[head]]

        for field in fields:
            if field == self:
                _logger.debug("Field %s is recursively defined", self)
                self.recursive = True
                continue

            #_logger.debug("Add trigger on %s to recompute %s", field, self)
            field._triggers.add((self, '.'.join(path0 or ['id'])))

            # add trigger on inverse fields, too
            for invf in field.inverse_fields:
                #_logger.debug("Add trigger on %s to recompute %s", invf, self)
                invf._triggers.add((self, '.'.join(path0 + [head])))

            # recursively traverse the dependency
            if tail:
                comodel = env[field.comodel_name]
                self._setup_dependency(path0 + [head], comodel, tail)

    @property
    def dependents(self):
        """ Return the computed fields that depend on `self`. """
        return (field for field, path in self._triggers)

    ############################################################################
    #
    # Field description
    #

    def get_description(self, env):
        """ Return a dictionary that describes the field `self`. """
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
        return bool(self.store or self.search or (self.column and self.column._fnct_search))

    @property
    def _description_sortable(self):
        return self.store or (self.inherited and self.related_field._description_sortable)

    def _description_string(self, env):
        if self.string and env.lang:
            field = self.base_field
            name = "%s,%s" % (field.model_name, field.name)
            trans = env['ir.translation']._get_source(name, 'field', env.lang)
            return trans or self.string
        return self.string

    def _description_help(self, env):
        if self.help and env.lang:
            name = "%s,%s" % (self.model_name, self.name)
            trans = env['ir.translation']._get_source(name, 'help', env.lang)
            return trans or self.help
        return self.help

    ############################################################################
    #
    # Conversion to column instance
    #

    def to_column(self):
        """ return a low-level field object corresponding to `self` """
        assert self.store or self.column

        # determine column parameters
        _logger.debug("Create fields._column for Field %s", self)
        args = {}
        for attr, prop in self.column_attrs:
            args[attr] = getattr(self, prop)
        for attr in self._free_attrs:
            args[attr] = getattr(self, attr)

        if self.company_dependent:
            # company-dependent fields are mapped to former property fields
            args['type'] = self.type
            args['relation'] = self.comodel_name
            self.column = fields.property(**args)
        elif self.column:
            # let the column provide a valid column for the given parameters
            self.column = self.column.new(**args)
        else:
            # create a fresh new column of the right type
            self.column = getattr(fields, self.type)(**args)

        return self.column

    # properties used by to_column() to create a column instance
    _column_copy = property(attrgetter('copy'))
    _column_select = property(attrgetter('index'))
    _column_manual = property(attrgetter('manual'))
    _column_string = property(attrgetter('string'))
    _column_help = property(attrgetter('help'))
    _column_readonly = property(attrgetter('readonly'))
    _column_required = property(attrgetter('required'))
    _column_states = property(attrgetter('states'))
    _column_groups = property(attrgetter('groups'))
    _column_change_default = property(attrgetter('change_default'))
    _column_deprecated = property(attrgetter('deprecated'))

    ############################################################################
    #
    # Conversion of values
    #

    def null(self, env):
        """ return the null value for this field in the given environment """
        return False

    def convert_to_cache(self, value, record, validate=True):
        """ convert `value` to the cache level in `env`; `value` may come from
            an assignment, or have the format of methods :meth:`BaseModel.read`
            or :meth:`BaseModel.write`

            :param record: the target record for the assignment, or an empty recordset

            :param bool validate: when True, field-specific validation of
                `value` will be performed
        """
        return value

    def convert_to_read(self, value, use_name_get=True):
        """ convert `value` from the cache to a value as returned by method
            :meth:`BaseModel.read`

            :param bool use_name_get: when True, value's diplay name will
                be computed using :meth:`BaseModel.name_get`, if relevant
                for the field
        """
        return False if value is None else value

    def convert_to_write(self, value, target=None, fnames=None):
        """ convert `value` from the cache to a valid value for method
            :meth:`BaseModel.write`.

            :param target: optional, the record to be modified with this value
            :param fnames: for relational fields only, an optional collection of
                field names to convert
        """
        return self.convert_to_read(value)

    def convert_to_onchange(self, value):
        """ convert `value` from the cache to a valid value for an onchange
            method v7.
        """
        return self.convert_to_write(value)

    def convert_to_export(self, value, env):
        """ convert `value` from the cache to a valid value for export. The
            parameter `env` is given for managing translations.
        """
        if env.context.get('export_raw_data'):
            return value
        return bool(value) and ustr(value)

    def convert_to_display_name(self, value):
        """ convert `value` from the cache to a suitable display name. """
        return ustr(value)

    ############################################################################
    #
    # Descriptor methods
    #

    def __get__(self, record, owner):
        """ return the value of field `self` on `record` """
        if record is None:
            return self         # the field is accessed through the owner class

        if not record:
            # null record -> return the null value for this field
            return self.null(record.env)

        # only a single record may be accessed
        record.ensure_one()

        try:
            return record._cache[self]
        except KeyError:
            pass

        # cache miss, retrieve value
        if record.id:
            # normal record -> read or compute value for this field
            self.determine_value(record)
        else:
            # draft record -> compute the value or let it be null
            self.determine_draft_value(record)

        # the result should be in cache now
        return record._cache[self]

    def __set__(self, record, value):
        """ set the value of field `self` on `record` """
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
                for invf in self.inverse_fields:
                    invf._update(value, record)
                record._set_dirty(self.name)

            # determine more dependent fields, and invalidate them
            if self.relational:
                spec += self.modified_draft(record)
            env.invalidate(spec)

        else:
            # simply write to the database, and update cache
            record.write({self.name: self.convert_to_write(value)})
            record._cache[self] = value

    ############################################################################
    #
    # Computation of field values
    #

    def _compute_value(self, records):
        """ Invoke the compute method on `records`. """
        # initialize the fields to their corresponding null value in cache
        for field in self.computed_fields:
            records._cache[field] = field.null(records.env)
            records.env.computed[field].update(records._ids)
        self.compute(records)
        for field in self.computed_fields:
            records.env.computed[field].difference_update(records._ids)

    def compute_value(self, records):
        """ Invoke the compute method on `records`; the results are in cache. """
        with records.env.do_in_draft():
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
        """ Determine the value of `self` for `record`. """
        env = record.env

        if self.column and not (self.depends and env.in_draft):
            # this is a stored field or an old-style function field
            if self.depends:
                # this is a stored computed field, check for recomputation
                recs = record._recompute_check(self)
                if recs:
                    # recompute the value (only in cache)
                    self.compute_value(recs)
                    # HACK: if result is in the wrong cache, copy values
                    if recs.env != env:
                        for source, target in zip(recs, recs.with_env(env)):
                            try:
                                values = target._convert_to_cache({
                                    f.name: source[f.name] for f in self.computed_fields
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
            # field in draft mode
            if self.recursive:
                self.compute_value(record)
            else:
                recs = record._in_cache_without(self)
                self.compute_value(recs)

        else:
            # this is a non-stored non-computed field
            record._cache[self] = self.null(env)

    def determine_draft_value(self, record):
        """ Determine the value of `self` for the given draft `record`. """
        if self.compute:
            self._compute_value(record)
        else:
            record._cache[self] = SpecialValue(self.null(record.env))

    def determine_inverse(self, records):
        """ Given the value of `self` on `records`, inverse the computation. """
        if self.inverse:
            self.inverse(records)

    def determine_domain(self, records, operator, value):
        """ Return a domain representing a condition on `self`. """
        if self.search:
            return self.search(records, operator, value)
        else:
            return [(self.name, operator, value)]

    ############################################################################
    #
    # Notification when fields are modified
    #

    def modified(self, records):
        """ Notify that field `self` has been modified on `records`: prepare the
            fields/records to recompute, and return a spec indicating what to
            invalidate.
        """
        # invalidate the fields that depend on self, and prepare recomputation
        spec = [(self, records._ids)]
        for field, path in self._triggers:
            if path and field.store:
                # don't move this line to function top, see log
                env = records.env(user=SUPERUSER_ID, context={'active_test': False})
                target = env[field.model_name].search([(path, 'in', records.ids)])
                if target:
                    spec.append((field, target._ids))
                    target.with_env(records.env)._recompute_todo(field)
            else:
                spec.append((field, None))

        return spec

    def modified_draft(self, records):
        """ Same as :meth:`modified`, but in draft mode. """
        env = records.env

        # invalidate the fields on the records in cache that depend on
        # `records`, except fields currently being computed
        spec = []
        for field, path in self._triggers:
            target = env[field.model_name]
            computed = target.browse(env.computed[field])
            if path == 'id':
                target = records - computed
            elif path:
                target = (target.browse(env.cache[field]) - computed).filtered(
                    lambda rec: rec._mapped_cache(path) & records
                )
            else:
                target = target.browse(env.cache[field]) - computed

            if target:
                spec.append((field, target._ids))

        return spec


class Boolean(Field):
    type = 'boolean'

    def convert_to_cache(self, value, record, validate=True):
        return bool(value)

    def convert_to_export(self, value, env):
        if env.context.get('export_raw_data'):
            return value
        return ustr(value)


class Integer(Field):
    type = 'integer'
    group_operator = None       # operator for aggregating values

    _related_group_operator = property(attrgetter('group_operator'))

    _column_group_operator = property(attrgetter('group_operator'))

    def convert_to_cache(self, value, record, validate=True):
        if isinstance(value, dict):
            # special case, when an integer field is used as inverse for a one2many
            return value.get('id', False)
        return int(value or 0)

    def convert_to_read(self, value, use_name_get=True):
        # Integer values greater than 2^31-1 are not supported in pure XMLRPC,
        # so we have to pass them as floats :-(
        if value and value > xmlrpclib.MAXINT:
            return float(value)
        return value

    def _update(self, records, value):
        # special case, when an integer field is used as inverse for a one2many
        records._cache[self] = value.id or 0


class Float(Field):
    """ The precision digits are given by the attribute

    :param digits: a pair (total, decimal), or a function taking a database
                   cursor and returning a pair (total, decimal)
    """
    type = 'float'
    _digits = None              # digits argument passed to class initializer
    digits = None               # digits as computed by setup()
    group_operator = None       # operator for aggregating values

    def __init__(self, string=None, digits=None, **kwargs):
        super(Float, self).__init__(string=string, _digits=digits, **kwargs)

    def _setup_digits(self, env):
        """ Setup the digits for `self` and its corresponding column """
        self.digits = self._digits(env.cr) if callable(self._digits) else self._digits
        if self.digits:
            assert isinstance(self.digits, (tuple, list)) and len(self.digits) >= 2, \
                "Float field %s with digits %r, expecting (total, decimal)" % (self, self.digits)
        if self.column:
            self.column.digits_change(env.cr)

    def _setup_regular(self, env):
        super(Float, self)._setup_regular(env)
        self._setup_digits(env)

    _related_digits = property(attrgetter('digits'))
    _related_group_operator = property(attrgetter('group_operator'))

    _description_digits = property(attrgetter('digits'))

    _column_digits = property(lambda self: not callable(self._digits) and self._digits)
    _column_digits_compute = property(lambda self: callable(self._digits) and self._digits)
    _column_group_operator = property(attrgetter('group_operator'))

    def convert_to_cache(self, value, record, validate=True):
        # apply rounding here, otherwise value in cache may be wrong!
        if self.digits:
            return float_round(float(value or 0.0), precision_digits=self.digits[1])
        else:
            return float(value or 0.0)


class _String(Field):
    """ Abstract class for string fields. """
    translate = False

    _column_translate = property(attrgetter('translate'))
    _related_translate = property(attrgetter('translate'))
    _description_translate = property(attrgetter('translate'))


class Char(_String):
    """ Basic string field, can be length-limited, usually displayed as a
    single-line string in clients

    :param int size: the maximum size of values stored for that field
    :param bool translate: whether the values of this field can be translated
    """
    type = 'char'
    size = None

    def _setup(self, env):
        super(Char, self)._setup(env)
        assert isinstance(self.size, (NoneType, int)), \
            "Char field %s with non-integer size %r" % (self, self.size)

    _column_size = property(attrgetter('size'))
    _related_size = property(attrgetter('size'))
    _description_size = property(attrgetter('size'))

    def convert_to_cache(self, value, record, validate=True):
        if value is None or value is False:
            return False
        return ustr(value)[:self.size]

class Text(_String):
    """ Very similar to :class:`~.Char` but used for longer contents, does not
    have a size and usually displayed as a multiline text box.

    :param translate: whether the value of this field can be translated
    """
    type = 'text'

    def convert_to_cache(self, value, record, validate=True):
        if value is None or value is False:
            return False
        return ustr(value)

class Html(_String):
    type = 'html'
    sanitize = True                     # whether value must be sanitized

    _column_sanitize = property(attrgetter('sanitize'))
    _related_sanitize = property(attrgetter('sanitize'))
    _description_sanitize = property(attrgetter('sanitize'))

    def convert_to_cache(self, value, record, validate=True):
        if value is None or value is False:
            return False
        if validate and self.sanitize:
            return html_sanitize(value)
        return value


class Date(Field):
    type = 'date'

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
        """ Convert an ORM `value` into a :class:`date` value. """
        value = value[:DATE_LENGTH]
        return datetime.strptime(value, DATE_FORMAT).date()

    @staticmethod
    def to_string(value):
        """ Convert a :class:`date` value into the format expected by the ORM. """
        return value.strftime(DATE_FORMAT)

    def convert_to_cache(self, value, record, validate=True):
        if not value:
            return False
        if isinstance(value, basestring):
            if validate:
                # force parsing for validation
                self.from_string(value)
            return value[:DATE_LENGTH]
        return self.to_string(value)

    def convert_to_export(self, value, env):
        if value and env.context.get('export_raw_data'):
            return self.from_string(value)
        return bool(value) and ustr(value)


class Datetime(Field):
    type = 'datetime'

    @staticmethod
    def now(*args):
        """ Return the current day and time in the format expected by the ORM.
            This function may be used to compute default values.
        """
        return datetime.now().strftime(DATETIME_FORMAT)

    @staticmethod
    def context_timestamp(record, timestamp):
        """Returns the given timestamp converted to the client's timezone.
           This method is *not* meant for use as a _defaults initializer,
           because datetime fields are automatically converted upon
           display on client side. For _defaults you :meth:`fields.datetime.now`
           should be used instead.

           :param datetime timestamp: naive datetime value (expressed in UTC)
                                      to be converted to the client timezone
           :rtype: datetime
           :return: timestamp converted to timezone-aware datetime in context
                    timezone
        """
        assert isinstance(timestamp, datetime), 'Datetime instance expected'
        tz_name = record._context.get('tz') or record.env.user.tz
        if tz_name:
            try:
                utc = pytz.timezone('UTC')
                context_tz = pytz.timezone(tz_name)
                utc_timestamp = utc.localize(timestamp, is_dst=False)  # UTC = no DST
                return utc_timestamp.astimezone(context_tz)
            except Exception:
                _logger.debug("failed to compute context/client-specific timestamp, "
                              "using the UTC value",
                              exc_info=True)
        return timestamp

    @staticmethod
    def from_string(value):
        """ Convert an ORM `value` into a :class:`datetime` value. """
        value = value[:DATETIME_LENGTH]
        if len(value) == DATE_LENGTH:
            value += " 00:00:00"
        return datetime.strptime(value, DATETIME_FORMAT)

    @staticmethod
    def to_string(value):
        """ Convert a :class:`datetime` value into the format expected by the ORM. """
        return value.strftime(DATETIME_FORMAT)

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

    def convert_to_export(self, value, env):
        if value and env.context.get('export_raw_data'):
            return self.from_string(value)
        return bool(value) and ustr(value)


class Binary(Field):
    type = 'binary'


class Selection(Field):
    """
    :param selection: specifies the possible values for this field.
        It is given as either a list of pairs (`value`, `string`), or a
        model method, or a method name.
    :param selection_add: provides an extension of the selection in the case
        of an overridden field. It is a list of pairs (`value`, `string`).

    The attribute `selection` is mandatory except in the case of
    :ref:`related fields <field-related>` or :ref:`field extensions
    <field-incremental-definition>`.
    """
    type = 'selection'
    selection = None        # [(value, string), ...], function or method name
    selection_add = None    # [(value, string), ...]

    def __init__(self, selection=None, string=None, **kwargs):
        if callable(selection):
            from openerp import api
            selection = api.expected(api.model, selection)
        super(Selection, self).__init__(selection=selection, string=string, **kwargs)

    def _setup(self, env):
        super(Selection, self)._setup(env)
        assert self.selection is not None, "Field %s without selection" % self

    def _setup_related(self, env):
        super(Selection, self)._setup_related(env)
        # selection must be computed on related field
        field = self.related_field
        self.selection = lambda model: field._description_selection(model.env)

    def set_class_name(self, cls, name):
        super(Selection, self).set_class_name(cls, name)
        # determine selection (applying 'selection_add' extensions)
        selection = None
        for field in resolve_all_mro(cls, name, reverse=True):
            if isinstance(field, type(self)):
                # We cannot use field.selection or field.selection_add here
                # because those attributes are overridden by `set_class_name`.
                if 'selection' in field._attrs:
                    selection = field._attrs['selection']
                if 'selection_add' in field._attrs:
                    selection = selection + field._attrs['selection_add']
            else:
                selection = None
        self.selection = selection

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

    @property
    def _column_selection(self):
        if isinstance(self.selection, basestring):
            method = self.selection
            return lambda self, *a, **kw: getattr(self, method)(*a, **kw)
        else:
            return self.selection

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

    def convert_to_export(self, value, env):
        if not isinstance(self.selection, list):
            # FIXME: this reproduces an existing buggy behavior!
            return value
        for item in self._description_selection(env):
            if item[0] == value:
                return item[1]
        return False


class Reference(Selection):
    type = 'reference'
    size = None

    def __init__(self, selection=None, string=None, **kwargs):
        super(Reference, self).__init__(selection=selection, string=string, **kwargs)

    def _setup(self, env):
        super(Reference, self)._setup(env)
        assert isinstance(self.size, (NoneType, int)), \
            "Reference field %s with non-integer size %r" % (self, self.size)

    _related_size = property(attrgetter('size'))

    _column_size = property(attrgetter('size'))

    def convert_to_cache(self, value, record, validate=True):
        if isinstance(value, BaseModel):
            if ((not validate or value._name in self.get_values(record.env))
                    and len(value) <= 1):
                return value.with_env(record.env) or False
        elif isinstance(value, basestring):
            res_model, res_id = value.split(',')
            return record.env[res_model].browse(int(res_id))
        elif not value:
            return False
        raise ValueError("Wrong value for %s: %r" % (self, value))

    def convert_to_read(self, value, use_name_get=True):
        return "%s,%s" % (value._name, value.id) if value else False

    def convert_to_export(self, value, env):
        return bool(value) and value.name_get()[0][1]

    def convert_to_display_name(self, value):
        return ustr(value and value.display_name)


class _Relational(Field):
    """ Abstract class for relational fields. """
    relational = True
    domain = None                       # domain for searching values
    context = None                      # context for searching values

    def _setup(self, env):
        super(_Relational, self)._setup(env)
        assert self.comodel_name in env.registry, \
            "Field %s with unknown comodel_name %r" % (self, self.comodel_name)

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

    _column_obj = property(attrgetter('comodel_name'))
    _column_domain = property(attrgetter('domain'))
    _column_context = property(attrgetter('context'))

    def null(self, env):
        return env[self.comodel_name]

    def modified(self, records):
        # Invalidate cache for self.inverse_fields, too. Note that recomputation
        # of fields that depend on self.inverse_fields is already covered by the
        # triggers (see above).
        spec = super(_Relational, self).modified(records)
        for invf in self.inverse_fields:
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

    The attribute `comodel_name` is mandatory except in the case of related
    fields or field extensions.
    """
    type = 'many2one'
    ondelete = 'set null'               # what to do when value is deleted
    auto_join = False                   # whether joins are generated upon search
    delegate = False                    # whether self implements delegation

    def __init__(self, comodel_name=None, string=None, **kwargs):
        super(Many2one, self).__init__(comodel_name=comodel_name, string=string, **kwargs)

    def set_class_name(self, cls, name):
        super(Many2one, self).set_class_name(cls, name)
        # determine self.delegate
        if not self.delegate:
            self.delegate = name in cls._inherits.values()

    _column_ondelete = property(attrgetter('ondelete'))
    _column_auto_join = property(attrgetter('auto_join'))

    def _update(self, records, value):
        """ Update the cached value of `self` for `records` with `value`. """
        records._cache[self] = value

    def convert_to_cache(self, value, record, validate=True):
        if isinstance(value, (NoneType, int, long)):
            return record.env[self.comodel_name].browse(value)
        if isinstance(value, BaseModel):
            if value._name == self.comodel_name and len(value) <= 1:
                return value.with_env(record.env)
            raise ValueError("Wrong value for %s: %r" % (self, value))
        elif isinstance(value, tuple):
            return record.env[self.comodel_name].browse(value[0])
        elif isinstance(value, dict):
            return record.env[self.comodel_name].new(value)
        else:
            return self.null(record.env)

    def convert_to_read(self, value, use_name_get=True):
        if use_name_get and value:
            # evaluate name_get() as superuser, because the visibility of a
            # many2one field value (id and name) depends on the current record's
            # access rights, and not the value's access rights.
            try:
                return value.sudo().name_get()[0]
            except MissingError:
                # Should not happen, unless the foreign key is missing.
                return False
        else:
            return value.id

    def convert_to_write(self, value, target=None, fnames=None):
        return value.id

    def convert_to_onchange(self, value):
        return value.id

    def convert_to_export(self, value, env):
        return bool(value) and value.name_get()[0][1]

    def convert_to_display_name(self, value):
        return ustr(value.display_name)


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
        record._cache[field] = new_value = record[field.name] | value
        return new_value


class _RelationalMulti(_Relational):
    """ Abstract class for relational fields *2many. """

    def _update(self, records, value):
        """ Update the cached value of `self` for `records` with `value`. """
        for record in records:
            if self in record._cache:
                record._cache[self] = record[self.name] | value
            else:
                record._cache[self] = UnionUpdate(self, record, value)

    def convert_to_cache(self, value, record, validate=True):
        if isinstance(value, BaseModel):
            if value._name == self.comodel_name:
                return value.with_env(record.env)
        elif isinstance(value, list):
            # value is a list of record ids or commands
            if not record.id:
                record = record.browse()        # new record has no value
            result = record[self.name]
            # modify result with the commands;
            # beware to not introduce duplicates in result
            for command in value:
                if isinstance(command, (tuple, list)):
                    if command[0] == 0:
                        result += result.new(command[2])
                    elif command[0] == 1:
                        result.browse(command[1]).update(command[2])
                        result += result.browse(command[1]) - result
                    elif command[0] == 2:
                        # note: the record will be deleted by write()
                        result -= result.browse(command[1])
                    elif command[0] == 3:
                        result -= result.browse(command[1])
                    elif command[0] == 4:
                        result += result.browse(command[1]) - result
                    elif command[0] == 5:
                        result = result.browse()
                    elif command[0] == 6:
                        result = result.browse(command[2])
                elif isinstance(command, dict):
                    result += result.new(command)
                else:
                    result += result.browse(command) - result
            return result
        elif not value:
            return self.null(record.env)
        raise ValueError("Wrong value for %s: %s" % (self, value))

    def convert_to_read(self, value, use_name_get=True):
        return value.ids

    def convert_to_write(self, value, target=None, fnames=None):
        # remove/delete former records
        if target is None:
            set_ids = []
            result = [(6, 0, set_ids)]
            add_existing = lambda id: set_ids.append(id)
        else:
            tag = 2 if self.type == 'one2many' else 3
            result = [(tag, record.id) for record in target[self.name] - value]
            add_existing = lambda id: result.append((4, id))

        if fnames is None:
            # take all fields in cache, except the inverses of self
            fnames = set(value._fields) - set(MAGIC_COLUMNS)
            for invf in self.inverse_fields:
                fnames.discard(invf.name)

        # add new and existing records
        for record in value:
            if not record.id:
                values = {k: v for k, v in record._cache.iteritems() if k in fnames}
                values = record._convert_to_write(values)
                result.append((0, 0, values))
            elif record._is_dirty():
                values = {k: record._cache[k] for k in record._get_dirty() if k in fnames}
                values = record._convert_to_write(values)
                result.append((1, record.id, values))
            else:
                add_existing(record.id)

        return result

    def convert_to_export(self, value, env):
        return bool(value) and ','.join(name for id, name in value.name_get())

    def convert_to_display_name(self, value):
        raise NotImplementedError()

    def _compute_related(self, records):
        """ Compute the related field `self` on `records`. """
        for record in records:
            value = record
            # traverse the intermediate fields, and keep at most one record
            for name in self.related[:-1]:
                value = value[name][:1]
            record[self.name] = value[self.related[-1]]


class One2many(_RelationalMulti):
    """ One2many field; the value of such a field is the recordset of all the
        records in `comodel_name` such that the field `inverse_name` is equal to
        the current record.

        :param comodel_name: name of the target model (string)

        :param inverse_name: name of the inverse `Many2one` field in
            `comodel_name` (string)

        :param domain: an optional domain to set on candidate values on the
            client side (domain or string)

        :param context: an optional context to use on the client side when
            handling that field (dictionary)

        :param auto_join: whether JOINs are generated upon search through that
            field (boolean, by default ``False``)

        :param limit: optional limit to use upon read (integer)

        The attributes `comodel_name` and `inverse_name` are mandatory except in
        the case of related fields or field extensions.
    """
    type = 'one2many'
    inverse_name = None                 # name of the inverse field
    auto_join = False                   # whether joins are generated upon search
    limit = None                        # optional limit to use upon read
    copy = False                        # o2m are not copied by default

    def __init__(self, comodel_name=None, inverse_name=None, string=None, **kwargs):
        super(One2many, self).__init__(
            comodel_name=comodel_name,
            inverse_name=inverse_name,
            string=string,
            **kwargs
        )

    def _setup_regular(self, env):
        super(One2many, self)._setup_regular(env)

        if self.inverse_name:
            # link self to its inverse field and vice-versa
            comodel = env[self.comodel_name]
            comodel._setup_fields()
            invf = comodel._fields[self.inverse_name]
            # In some rare cases, a `One2many` field can link to `Int` field
            # (res_model/res_id pattern). Only inverse the field if this is
            # a `Many2one` field.
            if isinstance(invf, Many2one):
                self.inverse_fields.append(invf)
                invf.inverse_fields.append(self)

    _description_relation_field = property(attrgetter('inverse_name'))

    _column_fields_id = property(attrgetter('inverse_name'))
    _column_auto_join = property(attrgetter('auto_join'))
    _column_limit = property(attrgetter('limit'))


class Many2many(_RelationalMulti):
    """ Many2many field; the value of such a field is the recordset.

        :param comodel_name: name of the target model (string)

        The attribute `comodel_name` is mandatory except in the case of related
        fields or field extensions.

        :param relation: optional name of the table that stores the relation in
            the database (string)

        :param column1: optional name of the column referring to "these" records
            in the table `relation` (string)

        :param column2: optional name of the column referring to "those" records
            in the table `relation` (string)

        The attributes `relation`, `column1` and `column2` are optional. If not
        given, names are automatically generated from model names, provided
        `model_name` and `comodel_name` are different!

        :param domain: an optional domain to set on candidate values on the
            client side (domain or string)

        :param context: an optional context to use on the client side when
            handling that field (dictionary)

        :param limit: optional limit to use upon read (integer)

    """
    type = 'many2many'
    relation = None                     # name of table
    column1 = None                      # column of table referring to model
    column2 = None                      # column of table referring to comodel
    limit = None                        # optional limit to use upon read

    def __init__(self, comodel_name=None, relation=None, column1=None, column2=None,
                 string=None, **kwargs):
        super(Many2many, self).__init__(
            comodel_name=comodel_name,
            relation=relation,
            column1=column1,
            column2=column2,
            string=string,
            **kwargs
        )

    def _setup_regular(self, env):
        super(Many2many, self)._setup_regular(env)

        if not self.relation:
            if isinstance(self.column, fields.many2many):
                self.relation, self.column1, self.column2 = \
                    self.column._sql_names(env[self.model_name])

        if self.relation:
            m2m = env.registry._m2m
            # if inverse field has already been setup, it is present in m2m
            invf = m2m.get((self.relation, self.column2, self.column1))
            if invf:
                self.inverse_fields.append(invf)
                invf.inverse_fields.append(self)
            else:
                # add self in m2m, so that its inverse field can find it
                m2m[(self.relation, self.column1, self.column2)] = self

    _column_rel = property(attrgetter('relation'))
    _column_id1 = property(attrgetter('column1'))
    _column_id2 = property(attrgetter('column2'))
    _column_limit = property(attrgetter('limit'))


class Id(Field):
    """ Special case for field 'id'. """
    store = True
    #: Can't write this!
    readonly = True

    def __init__(self, string=None, **kwargs):
        super(Id, self).__init__(type='integer', string=string, **kwargs)

    def to_column(self):
        self.column = fields.integer('ID')
        return self.column

    def __get__(self, record, owner):
        if record is None:
            return self         # the field is accessed through the class owner
        if not record:
            return False
        return record.ensure_one()._ids[0]

    def __set__(self, record, value):
        raise TypeError("field 'id' cannot be assigned")


# imported here to avoid dependency cycle issues
from openerp import SUPERUSER_ID
from .exceptions import Warning, AccessError, MissingError
from .models import BaseModel, MAGIC_COLUMNS
from .osv import fields
