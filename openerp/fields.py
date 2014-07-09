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

from copy import copy
from datetime import date, datetime
from functools import partial
from operator import attrgetter
import logging
import pytz
import xmlrpclib

from types import NoneType

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


def default_compute(field, value):
    """ Return a compute function for the given default `value`; `value` is
        either a constant, or a unary function returning the default value.
    """
    name = field.name
    func = value if callable(value) else lambda rec: value
    def compute(recs):
        for rec in recs:
            rec[name] = func(rec)
    return compute


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

        :param states: a dictionary mapping state values to lists of attribute-value
            pairs; possible attributes are: 'readonly', 'required', 'invisible'

        :param groups: comma-separated list of group xml ids (string); this
            restricts the field access to the users of the given groups only

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

        The value of some attributes from related fields are automatically taken
        from the source field, when it makes sense. Examples are the attributes
        `string` or `selection` on selection fields.

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

        A field is defined as class attribute on a model class. If the model is
        extended (see :class:`BaseModel`), one can also extend the field
        definition by redefining a field with the same name and same type on the
        subclass. In that case, the attributes of the field are taken from the
        parent class and overridden by the ones given in subclasses.

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
    _origin = None              # the column or field interfaced by self, if any

    name = None                 # name of the field
    type = None                 # type of the field (string)
    relational = False          # whether the field is a relational one
    model_name = None           # name of the model of this field
    comodel_name = None         # name of the model of values (if relational)
    inverse_field = None        # inverse field (object), if it exists

    store = True                # whether the field is stored in database
    index = False               # whether the field is indexed in database
    copyable = True             # whether the field is copied over by BaseModel.copy()
    depends = ()                # collection of field dependencies
    recursive = False           # whether self depends on itself
    compute = None              # compute(recs) computes field on recs
    inverse = None              # inverse(recs) inverses field on recs
    search = None               # search(recs, operator, value) searches on self
    related = None              # sequence of field names, for related fields
    company_dependent = False   # whether `self` is company-dependent (property field)
    default = None              # default value

    string = None               # field label
    help = None                 # field tooltip
    readonly = False
    required = False
    states = None
    groups = False              # csv list of group xml ids

    def __init__(self, string=None, **kwargs):
        kwargs['string'] = string
        self._attrs = {key: val for key, val in kwargs.iteritems() if val is not None}
        self._free_attrs = []

    def copy(self, **kwargs):
        """ make a copy of `self`, possibly modified with parameters `kwargs` """
        field = copy(self)
        field._attrs = {key: val for key, val in kwargs.iteritems() if val is not None}
        field._free_attrs = list(self._free_attrs)
        return field

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
        if 'copy' in attrs:
            # attribute is copyable because there is also a copy() method
            attrs['copyable'] = attrs.pop('copy')

        for attr, value in attrs.iteritems():
            if not hasattr(self, attr):
                self._free_attrs.append(attr)
            setattr(self, attr, value)

        if not self.string:
            self.string = name.replace('_', ' ').capitalize()

        self.reset()

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
        self._setup_done = False
        # self._triggers is a set of pairs (field, path) that represents the
        # computed fields that depend on `self`. When `self` is modified, it
        # invalidates the cache of each `field`, and registers the records to
        # recompute based on `path`. See method `modified` below for details.
        self._triggers = set()
        self.inverse_field = None

    def setup(self, env):
        """ Complete the setup of `self` (dependencies, recomputation triggers,
            and other properties). This method is idempotent: it has no effect
            if `self` has already been set up.
        """
        if not self._setup_done:
            self._setup_done = True
            self._setup(env)

    def _setup(self, env):
        """ Do the actual setup of `self`. """
        if self.related:
            self._setup_related(env)
        else:
            self._setup_regular(env)

        # put invalidation/recomputation triggers on dependencies
        for path in self.depends:
            self._setup_dependency([], env[self.model_name], path.split('.'))

    #
    # Setup of related fields
    #

    def _setup_related(self, env):
        """ Setup the attributes of a related field. """
        # fix the type of self.related if necessary
        if isinstance(self.related, basestring):
            self.related = tuple(self.related.split('.'))

        # determine the related field, and make sure it is set up
        recs = env[self.model_name]
        for name in self.related[:-1]:
            recs = recs[name]
        field = self.related_field = recs._fields[self.related[-1]]
        field.setup(env)

        # check type consistency
        if self.type != field.type:
            raise Warning("Type of related field %s is inconsistent with %s" % (self, field))

        # determine dependencies, compute, inverse, and search
        self.depends = ('.'.join(self.related),)
        self.compute = self._compute_related
        self.inverse = self._inverse_related
        self.search = self._search_related

        # copy attributes from field to self (string, help, etc.)
        for attr, prop in self.related_attrs:
            if not getattr(self, attr):
                setattr(self, attr, getattr(field, prop))

    def _compute_related(self, records):
        """ Compute the related field `self` on `records`. """
        for record in records:
            # bypass access rights check when traversing the related path
            value = record.sudo() if record.id else record
            # traverse the intermediate fields, and keep at most one record
            for name in self.related[:-1]:
                value = value[name][:1]
            record[self.name] = value[self.related[-1]]

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
    _related_string = property(attrgetter('string'))
    _related_help = property(attrgetter('help'))
    _related_readonly = property(attrgetter('readonly'))
    _related_groups = property(attrgetter('groups'))

    #
    # Setup of non-related fields
    #

    def _setup_regular(self, env):
        """ Setup the attributes of a non-related field. """
        recs = env[self.model_name]

        def make_depends(deps):
            return tuple(deps(recs) if callable(deps) else deps)

        # transform self.default into self.compute
        if self.default is not None and self.compute is None:
            self.compute = default_compute(self, self.default)

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

            field.setup(env)

            #_logger.debug("Add trigger on %s to recompute %s", field, self)
            field._triggers.add((self, '.'.join(path0 or ['id'])))

            # add trigger on inverse field, too
            if field.inverse_field:
                #_logger.debug("Add trigger on %s to recompute %s", field.inverse_field, self)
                field.inverse_field._triggers.add((self, '.'.join(path0 + [head])))

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
        # determine 'store'
        if self.store:
            # if the corresponding column is a function field, check the column
            column = env[self.model_name]._columns.get(self.name)
            desc['store'] = bool(getattr(column, 'store', True))
        else:
            desc['store'] = False
        # determine other attributes
        for attr, prop in self.description_attrs:
            value = getattr(self, prop)
            if callable(value):
                value = value(env)
            if value:
                desc[attr] = value
        return desc

    # properties used by get_description()
    _description_depends = property(attrgetter('depends'))
    _description_related = property(attrgetter('related'))
    _description_company_dependent = property(attrgetter('company_dependent'))
    _description_readonly = property(attrgetter('readonly'))
    _description_required = property(attrgetter('required'))
    _description_states = property(attrgetter('states'))
    _description_groups = property(attrgetter('groups'))

    def _description_string(self, env):
        if self.string and env.lang:
            name = "%s,%s" % (self.model_name, self.name)
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
        assert self.store
        if self._origin:
            assert isinstance(self._origin, fields._column)
            return self._origin

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
            return fields.property(**args)

        return getattr(fields, self.type)(**args)

    # properties used by to_column() to create a column instance
    _column_copy = property(attrgetter('copyable'))
    _column_select = property(attrgetter('index'))
    _column_string = property(attrgetter('string'))
    _column_help = property(attrgetter('help'))
    _column_readonly = property(attrgetter('readonly'))
    _column_required = property(attrgetter('required'))
    _column_states = property(attrgetter('states'))
    _column_groups = property(attrgetter('groups'))

    ############################################################################
    #
    # Conversion of values
    #

    def null(self, env):
        """ return the null value for this field in the given environment """
        return False

    def convert_to_cache(self, value, env):
        """ convert `value` to the cache level in `env`; `value` may come from
            an assignment, or have the format of methods :meth:`BaseModel.read`
            or :meth:`BaseModel.write`
        """
        return value

    def convert_to_read(self, value, use_name_get=True):
        """ convert `value` from the cache to a value as returned by method
            :meth:`BaseModel.read`
        """
        return value

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
            # new record -> compute default value for this field
            record.add_default_value(self)

        # the result should be in cache now
        return record._cache[self]

    def __set__(self, record, value):
        """ set the value of field `self` on `record` """
        env = record.env

        # only a single record may be updated
        record.ensure_one()

        # adapt value to the cache level
        value = self.convert_to_cache(value, env)

        if env.in_draft or not record.id:
            # determine dependent fields
            spec = self.modified_draft(record)

            # set value in cache, inverse field, and mark record as dirty
            record._cache[self] = value
            if env.in_onchange:
                if self.inverse_field:
                    self.inverse_field._update(value, record)
                record._dirty = True

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
        # mark the computed fields failed in cache, so that access before
        # computation raises an exception
        exc = Warning("Field %s is accessed before being computed." % self)
        for field in self.computed_fields:
            records._cache[field] = FailedValue(exc)
            records.env.computed[field].update(records._ids)
        self.compute(records)
        for field in self.computed_fields:
            records.env.computed[field].difference_update(records._ids)

    def compute_value(self, records):
        """ Invoke the compute method on `records`; the results are in cache. """
        with records.env.do_in_draft():
            try:
                self._compute_value(records)
            except MissingError:
                # some record is missing, retry on existing records only
                self._compute_value(records.exists())

    def determine_value(self, record):
        """ Determine the value of `self` for `record`. """
        env = record.env

        if self.store and not (self.depends and env.in_draft):
            # this is a stored field
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
                                })
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

    def determine_default(self, record):
        """ determine the default value of field `self` on `record` """
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
            if field.store:
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
            else:
                for record in target.browse(env.cache[field]) - computed:
                    if record._mapped_cache(path) & records:
                        target += record
            if target:
                spec.append((field, target._ids))

        return spec


class Any(Field):
    """ Field for arbitrary Python values. """
    # Warning: no storage is defined for this type of field!
    type = 'any'


class Boolean(Field):
    """ Boolean field. """
    type = 'boolean'

    def convert_to_cache(self, value, env):
        return bool(value)

    def convert_to_export(self, value, env):
        if env.context.get('export_raw_data'):
            return value
        return ustr(value)


class Integer(Field):
    """ Integer field. """
    type = 'integer'

    def convert_to_cache(self, value, env):
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
    """ Float field. The precision digits are given by the attribute

        :param digits: a pair (total, decimal), or a function taking a database
            cursor and returning a pair (total, decimal)

    """
    type = 'float'
    _digits = None              # digits argument passed to class initializer
    digits = None               # digits as computed by setup()

    def __init__(self, string=None, digits=None, **kwargs):
        super(Float, self).__init__(string=string, _digits=digits, **kwargs)

    def _setup_regular(self, env):
        super(Float, self)._setup_regular(env)
        self.digits = self._digits(env.cr) if callable(self._digits) else self._digits

    _related_digits = property(attrgetter('digits'))

    _description_digits = property(attrgetter('digits'))

    _column_digits = property(lambda self: not callable(self._digits) and self._digits)
    _column_digits_compute = property(lambda self: callable(self._digits) and self._digits)

    def convert_to_cache(self, value, env):
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
    """ Char field.

        :param size: the maximum size of values stored for that field (integer,
            optional)

        :param translate: whether the value of the field has translations
            (boolean, by default ``False``)

    """
    type = 'char'
    size = None

    _column_size = property(attrgetter('size'))
    _related_size = property(attrgetter('size'))
    _description_size = property(attrgetter('size'))

    def convert_to_cache(self, value, env):
        return bool(value) and ustr(value)[:self.size]


class Text(_String):
    """ Text field. Very similar to :class:`Char`, but typically for longer
        contents.

        :param translate: whether the value of the field has translations
            (boolean, by default ``False``)

    """
    type = 'text'

    def convert_to_cache(self, value, env):
        return bool(value) and ustr(value)


class Html(_String):
    """ Html field. """
    type = 'html'

    def convert_to_cache(self, value, env):
        return bool(value) and html_sanitize(value)


class Date(Field):
    """ Date field. """
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

    def convert_to_cache(self, value, env):
        if not value:
            return False
        if isinstance(value, basestring):
            value = self.from_string(value)
        return value.strftime(DATE_FORMAT)

    def convert_to_export(self, value, env):
        if value and env.context.get('export_raw_data'):
            return self.from_string(value)
        return bool(value) and ustr(value)


class Datetime(Field):
    """ Datetime field. """
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

    def convert_to_cache(self, value, env):
        if not value:
            return False
        if isinstance(value, basestring):
            value = self.from_string(value)
        return value.strftime(DATETIME_FORMAT)

    def convert_to_export(self, value, env):
        if value and env.context.get('export_raw_data'):
            return self.from_string(value)
        return bool(value) and ustr(value)


class Binary(Field):
    """ Binary field. """
    type = 'binary'


class Selection(Field):
    """ Selection field.

        :param selection: specifies the possible values for this field.
            It is given as either a list of pairs (`value`, `string`), or a
            model method, or a method name.

        The attribute `selection` is mandatory except in the case of related
        fields (see :ref:`field-related`) or field extensions
        (see :ref:`field-incremental-definition`).
    """
    type = 'selection'
    selection = None        # [(value, string), ...], model method or method name

    def __init__(self, selection=None, string=None, **kwargs):
        if callable(selection):
            from openerp import api
            selection = api.expected(api.model, selection)
        super(Selection, self).__init__(selection=selection, string=string, **kwargs)

    def _setup_related(self, env):
        super(Selection, self)._setup_related(env)
        # selection must be computed on related field
        field = self.related_field
        self.selection = lambda model: field._description_selection(model.env)

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
            return [(value, translate(label)) for value, label in selection]
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

    def convert_to_cache(self, value, env):
        if value in self.get_values(env):
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
    """ Reference field.

        :param selection: specifies the possible model names for this field.
            It is given as either a list of pairs (`value`, `string`), or a
            model method, or a method name.

        The attribute `selection` is mandatory except in the case of related
        fields (see :ref:`field-related`) or field extensions
        (see :ref:`field-incremental-definition`).
    """
    type = 'reference'
    size = 128

    def __init__(self, selection=None, string=None, **kwargs):
        super(Reference, self).__init__(selection=selection, string=string, **kwargs)

    _related_size = property(attrgetter('size'))

    _column_size = property(attrgetter('size'))

    def convert_to_cache(self, value, env):
        if isinstance(value, BaseModel):
            if value._name in self.get_values(env) and len(value) <= 1:
                return value.with_env(env) or False
        elif isinstance(value, basestring):
            res_model, res_id = value.split(',')
            return env[res_model].browse(int(res_id))
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
        # Invalidate cache for self.inverse_field, too. Note that recomputation
        # of fields that depend on self.inverse_field is already covered by the
        # triggers (see above).
        spec = super(_Relational, self).modified(records)
        if self.inverse_field:
            spec.append((self.inverse_field, None))
        return spec


class Many2one(_Relational):
    """ Many2one field; the value of such a field is a recordset of size 0 (no
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

    def _setup_regular(self, env):
        super(Many2one, self)._setup_regular(env)

        # self.inverse_field is determined by the corresponding One2many field

        # determine self.delegate
        self.delegate = self.name in env[self.model_name]._inherits.values()

    _column_ondelete = property(attrgetter('ondelete'))
    _column_auto_join = property(attrgetter('auto_join'))

    def _update(self, records, value):
        """ Update the cached value of `self` for `records` with `value`. """
        records._cache[self] = value

    def convert_to_cache(self, value, env):
        if isinstance(value, (NoneType, int)):
            return env[self.comodel_name].browse(value)
        if isinstance(value, BaseModel):
            if value._name == self.comodel_name and len(value) <= 1:
                return value.with_env(env)
            raise ValueError("Wrong value for %s: %r" % (self, value))
        elif isinstance(value, tuple):
            return env[self.comodel_name].browse(value[0])
        elif isinstance(value, dict):
            return env[self.comodel_name].new(value)
        else:
            return env[self.comodel_name].browse(value)

    def convert_to_read(self, value, use_name_get=True):
        if use_name_get and value:
            # evaluate name_get() as superuser, because the visibility of a
            # many2one field value (id and name) depends on the current record's
            # access rights, and not the value's access rights.
            return value.sudo().name_get()[0]
        else:
            return value.id

    def convert_to_write(self, value, target=None, fnames=None):
        return bool(value) and (value.id or value._convert_to_write(value._cache))

    def convert_to_onchange(self, value):
        return value.id

    def convert_to_export(self, value, env):
        return bool(value) and value.name_get()[0][1]

    def convert_to_display_name(self, value):
        return ustr(value.display_name)

    def determine_default(self, record):
        super(Many2one, self).determine_default(record)
        if self.delegate:
            # special case: fields that implement inheritance between models
            value = record[self.name]
            if not value:
                # the default value cannot be null, use a new record instead
                record[self.name] = record.env[self.comodel_name].new()


class _RelationalMulti(_Relational):
    """ Abstract class for relational fields *2many. """

    def _update(self, records, value):
        """ Update the cached value of `self` for `records` with `value`. """
        for record in records:
            record._cache[self] = record[self.name] | value

    def convert_to_cache(self, value, env):
        if isinstance(value, BaseModel):
            if value._name == self.comodel_name:
                return value.with_env(env)
        elif isinstance(value, list):
            # value is a list of record ids or commands
            result = env[self.comodel_name]
            for command in value:
                if isinstance(command, (tuple, list)):
                    if command[0] == 0:
                        result += result.new(command[2])
                    elif command[0] == 1:
                        record = result.browse(command[1])
                        record.update(command[2])
                        result += record
                    elif command[0] == 2:
                        pass
                    elif command[0] == 3:
                        pass
                    elif command[0] == 4:
                        result += result.browse(command[1])
                    elif command[0] == 5:
                        result = result.browse()
                    elif command[0] == 6:
                        result = result.browse(command[2])
                elif isinstance(command, dict):
                    result += result.new(command)
                else:
                    result += result.browse(command)
            return result
        elif not value:
            return self.null(env)
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
            # take all fields in cache, except the inverse of self
            fnames = set(value._fields) - set(MAGIC_COLUMNS)
            if self.inverse_field:
                fnames.discard(self.inverse_field.name)

        # add new and existing records
        for record in value:
            if not record.id or record._dirty:
                values = dict((k, v) for k, v in record._cache.iteritems() if k in fnames)
                values = record._convert_to_write(values)
                if not record.id:
                    result.append((0, 0, values))
                else:
                    result.append((1, record.id, values))
            else:
                add_existing(record.id)

        return result

    def convert_to_export(self, value, env):
        return bool(value) and ','.join(name for id, name in value.name_get())

    def convert_to_display_name(self, value):
        raise NotImplementedError()


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
    copyable = False                    # o2m are not copied by default

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
            invf = env[self.comodel_name]._fields[self.inverse_name]
            self.inverse_field = invf
            invf.inverse_field = self

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

        if self.store and not self.relation:
            model = env[self.model_name]
            column = model._columns[self.name]
            if not isinstance(column, fields.function):
                self.relation, self.column1, self.column2 = column._sql_names(model)

        if self.relation:
            m2m = env.registry._m2m
            # if inverse field has already been setup, it is present in m2m
            invf = m2m.get((self.relation, self.column2, self.column1))
            if invf:
                self.inverse_field = invf
                invf.inverse_field = self
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
    readonly = True

    def to_column(self):
        return fields.integer('ID')

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
from .exceptions import Warning, MissingError
from .models import BaseModel, MAGIC_COLUMNS
from .osv import fields
