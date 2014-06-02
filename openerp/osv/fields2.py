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


class Field(object):
    """ Base class of all fields. """
    __metaclass__ = MetaField

    automatic = False           # whether the field is automatically created ("magic" field)
    _origin = None              # the column or field interfaced by self, if any
    _free_attrs = None          # collection of semantic-free attribute names

    name = None                 # name of the field
    type = None                 # type of the field (string)
    relational = False          # whether the field is a relational one
    model_name = None           # name of the model of this field
    comodel_name = None         # name of the model of values (if relational)
    inverse_field = None        # inverse field (object), if it exists

    store = True                # whether the field is stored in database
    index = False               # whether the field is indexed in database
    depends = ()                # collection of field dependencies
    recursive = False           # whether self depends on itself
    compute = None              # compute(recs) computes field on recs
    inverse = None              # inverse(recs) inverses field on recs
    search = None               # search(recs, operator, value) searches on self
    related = None              # sequence of field names, for related fields

    string = None               # field label
    help = None                 # field tooltip
    readonly = False
    required = False
    states = None
    groups = False              # csv list of group xml ids

    def __init__(self, string=None, **kwargs):
        self._free_attrs = []
        kwargs['string'] = string
        # by default, computed fields are not stored and readonly
        if 'compute' in kwargs:
            kwargs['store'] = kwargs.get('store', False)
            kwargs['readonly'] = kwargs.get('readonly', 'inverse' not in kwargs)
        if 'related' in kwargs:
            kwargs['store'] = kwargs.get('store', False)
        for attr, value in kwargs.iteritems():
            if not hasattr(self, attr):
                self._free_attrs.append(attr)
            setattr(self, attr, value)
        self.reset()

    def copy(self, **kwargs):
        """ make a copy of `self`, possibly modified with parameters `kwargs` """
        field = copy(self)
        field._free_attrs = list(self._free_attrs)
        for attr, value in kwargs.iteritems():
            if not hasattr(self, attr):
                self._free_attrs.append(attr)
            setattr(field, attr, value)
        field.reset()
        return field

    def set_model_name(self, model_name, name):
        """ assign the model and field names of `self` """
        self.model_name = model_name
        self.name = name
        if not self.string:
            self.string = name.replace('_', ' ').capitalize()

    def __str__(self):
        return "%s.%s" % (self.model_name, self.name)

    def __repr__(self):
        return "%s.%s" % (self.model_name, self.name)

    #
    # Field setup.
    #
    # Recomputation of computed fields: each field stores a set of triggers
    # (`field`, `path`); when the field is modified, it invalidates the cache of
    # `field` and registers the records to recompute based on `path`. See method
    # `modified` below for details.
    #

    def reset(self):
        """ Prepare `self` for a new setup. """
        self._setup_done = False
        self._triggers = set()          # set of (field, path)

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

        # determine all the fields computed by self.compute
        self.computed_fields = self.compute and [
            field
            for field in env[self.model_name]._fields.itervalues()
            if field.compute in (self.compute, self.compute.__name__)
        ] or []

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
        for attr in dir(self):
            if attr.startswith('_related_'):
                if not getattr(self, attr[9:]):
                    setattr(self, attr[9:], getattr(field, attr))

        # special case: related fields never have an inverse field!
        self.inverse_field = None

    def _compute_related(self, records):
        """ Compute the related field `self` on `records`. """
        for record in records:
            # bypass access rights check when traversing the related path
            value = record.sudo() if record.id else record
            for name in self.related:
                value = value[name]
            record[self.name] = value

    def _inverse_related(self, records):
        """ Inverse the related field `self` on `records`. """
        for record in records:
            other = record
            for name in self.related[:-1]:
                other = other[name]
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

    def _setup_regular(self, env):
        """ Setup the attributes of a non-related field. """
        recs = env[self.model_name]

        # remap compute, inverse an search to their expected type
        if isinstance(self.compute, basestring):
            self.compute = getattr(type(recs), self.compute)
        elif hasattr(self, 'default'):
            self.compute = default_compute(self, self.default)

        if isinstance(self.inverse, basestring):
            self.inverse = getattr(type(recs), self.inverse)
        if isinstance(self.search, basestring):
            self.search = getattr(type(recs), self.search)

        # retrieve dependencies from compute method
        self.depends = getattr(self.compute, '_depends', ())
        if callable(self.depends):
            self.depends = self.depends(recs)

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

            _logger.debug("Add trigger on %s to recompute %s", field, self)
            field._triggers.add((self, '.'.join(path0 or ['id'])))

            # add trigger on inverse field, too
            if field.inverse_field:
                _logger.debug("Add trigger on %s to recompute %s", field.inverse_field, self)
                field.inverse_field._triggers.add((self, '.'.join(path0 + [head])))

            # recursively traverse the dependency
            if tail:
                comodel = env[field.comodel_name]
                self._setup_dependency(path0 + [head], comodel, tail)

    @property
    def dependents(self):
        """ Return the computed fields that depend on `self`. """
        return (field for field, path in self._triggers)

    #
    # Field description
    #

    def get_description(self, env):
        """ Return a dictionary that describes the field `self`. """
        desc = {'type': self.type, 'store': self.store}
        for attr in dir(self):
            if attr.startswith('_description_'):
                value = getattr(self, attr)
                if callable(value):
                    value = value(env)
                if value:
                    desc[attr[13:]] = value
        return desc

    # properties used by get_description()
    _description_depends = property(attrgetter('depends'))
    _description_related = property(attrgetter('related'))
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
        for attr in dir(self):
            if attr.startswith('_column_'):
                args[attr[8:]] = getattr(self, attr)
            elif attr in self._free_attrs:
                args[attr] = getattr(self, attr)
        return getattr(fields, self.type)(**args)

    # properties used by to_column() to create a column instance
    _column_select = property(attrgetter('index'))
    _column_string = property(attrgetter('string'))
    _column_help = property(attrgetter('help'))
    _column_readonly = property(attrgetter('readonly'))
    _column_required = property(attrgetter('required'))
    _column_states = property(attrgetter('states'))
    _column_groups = property(attrgetter('groups'))

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

    #
    # Descriptor methods
    #

    def __get__(self, record, owner):
        """ return the value of field `self` on `record` """
        if record is None:
            return self         # the field is accessed through the owner class

        try:
            return record._cache[self]
        except KeyError:
            pass

        # cache miss, retrieve value
        if record.id:
            # normal record -> read or compute value for this field
            self.determine_value(record[0])
        elif record:
            # new record -> compute default value for this field
            record.add_default_value(self)
        else:
            # null record -> return the null value for this field
            return self.null(record.env)

        # the result should be in cache now
        return record._cache[self]

    def __set__(self, record, value):
        """ set the value of field `self` on `record` """
        if not record:
            raise Warning("Null record %s may not be assigned" % record)

        # only one record is updated
        env = record.env
        record = record[0]

        # adapt value to the cache level
        value = self.convert_to_cache(value, env)

        if env.draft or not record.id:
            # determine dependent fields
            spec = self.modified_draft(record)

            # set value in cache, inverse field, and mark record as dirty
            record._cache[self] = value
            if env.draft:
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

    #
    # Computation of field values
    #

    def compute_value(self, records):
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

    def determine_value(self, record):
        """ Determine the value of `self` for `record`. """
        env = record.env
        if self.depends:
            # this is a computed field
            if self.store and not env.draft:
                # recompute field on record if required
                recs = record._recompute_check(self)
                if recs:
                    # execute the compute method in DRAFT mode; the result is
                    # saved to database by method BaseModel.recompute()
                    with env.do_in_draft():
                        self.compute_value(recs.exists())
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
                else:
                    record._prefetch_field(self)
            else:
                # execute the compute method in DRAFT mode
                with env.do_in_draft():
                    if self.recursive:
                        self.compute_value(record)
                    else:
                        recs = record._in_cache_without(self)
                        self.compute_value(recs.exists())

        elif self.store:
            # this is a simple stored field
            record._prefetch_field(self)

        else:
            # this is a non-stored non-computed field
            record._cache[self] = self.null(env)

    def determine_default(self, record):
        """ determine the default value of field `self` on `record` """
        if self.compute:
            self.compute_value(record)
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

    #
    # Notification when fields are modified
    #

    def modified(self, records):
        """ Notify that field `self` has been modified on `records`: prepare the
            fields/records to recompute, and return a spec indicating what to
            invalidate.
        """
        env = records.env(user=SUPERUSER_ID, context={'active_test': False})

        # invalidate the fields that depend on self, and prepare recomputation
        spec = [(self, records._ids)]
        for field, path in self._triggers:
            if field.store:
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
                    if record.map_cache(path) & records:
                        target += record
            if target:
                spec.append((field, target._ids))

        return spec


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

    def _update(self, records, value):
        # special case, when an integer field is used as inverse for a one2many
        records._cache[self] = value.id or 0


class Float(Field):
    """ Float field. """
    type = 'float'
    digits = None

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
    """ Char field. """
    type = 'char'
    size = None

    _column_size = property(attrgetter('size'))
    _related_size = property(attrgetter('size'))
    _description_size = property(attrgetter('size'))

    def convert_to_cache(self, value, env):
        return bool(value) and ustr(value)[:self.size]


class Text(_String):
    """ Text field. """
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
        value = value[:DATE_LENGTH]
        return datetime.strptime(value, DATE_FORMAT).date()

    @staticmethod
    def to_string(value):
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
        value = value[:DATETIME_LENGTH]
        if len(value) == DATE_LENGTH:
            value += " 00:00:00"
        return datetime.strptime(value, DATETIME_FORMAT)

    @staticmethod
    def to_string(value):
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
    """ Selection field. """
    type = 'selection'
    selection = None        # [(value, string), ...], model method or method name

    def __init__(self, selection, string=None, **kwargs):
        """ Selection field.

            :param selection: specifies the possible values for this field.
                It is given as either a list of pairs (`value`, `string`), or a
                model method, or a method name.
        """
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
        return [value for value, label in selection]

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
    """ Reference field. """
    type = 'reference'
    size = 128

    def __init__(self, selection, string=None, **kwargs):
        """ Reference field.

            :param selection: specifies the possible model names for this field.
                It is given as either a list of pairs (`value`, `string`), or a
                model method, or a method name.
        """
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

    def __init__(self, **kwargs):
        super(_Relational, self).__init__(**kwargs)

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
    """ Many2one field. """
    type = 'many2one'
    ondelete = 'set null'               # what to do when value is deleted
    auto_join = False                   # whether joins are generated upon search
    delegate = False                    # whether self implements delegation

    def __init__(self, comodel_name, string=None, **kwargs):
        super(Many2one, self).__init__(comodel_name=comodel_name, string=string, **kwargs)

    def _setup_regular(self, env):
        super(Many2one, self)._setup_regular(env)

        # determine self.inverse_field
        for field in env[self.comodel_name]._fields.itervalues():
            field.setup(env)
            if isinstance(field, One2many) and field.inverse_field == self:
                self.inverse_field = field
                break

        # determine self.delegate
        self.delegate = self.name in env[self.model_name]._inherits.values()

    _column_ondelete = property(attrgetter('ondelete'))
    _column_auto_join = property(attrgetter('auto_join'))

    def _update(self, records, value):
        """ Update the cached value of `self` for `records` with `value`. """
        records._cache[self] = value

    def convert_to_cache(self, value, env):
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
    """ One2many field. """
    type = 'one2many'
    inverse_name = None                 # name of the inverse field
    auto_join = False                   # whether joins are generated upon search
    limit = None                        # optional limit to use upon read

    def __init__(self, comodel_name, inverse_name=None, string=None, **kwargs):
        super(One2many, self).__init__(
            comodel_name=comodel_name, inverse_name=inverse_name, string=string, **kwargs)

    def _setup_regular(self, env):
        super(One2many, self)._setup_regular(env)
        if self.inverse_name:
            self.inverse_field = env[self.comodel_name]._fields[self.inverse_name]

    _description_relation_field = property(attrgetter('inverse_name'))

    _column_fields_id = property(attrgetter('inverse_name'))
    _column_auto_join = property(attrgetter('auto_join'))
    _column_limit = property(attrgetter('limit'))


class Many2many(_RelationalMulti):
    """ Many2many field. """
    type = 'many2many'
    relation = None                     # name of table
    column1 = None                      # column of table referring to model
    column2 = None                      # column of table referring to comodel
    limit = None                        # optional limit to use upon read

    def __init__(self, comodel_name, relation=None, column1=None, column2=None,
                string=None, **kwargs):
        super(Many2many, self).__init__(comodel_name=comodel_name, relation=relation,
            column1=column1, column2=column2, string=string, **kwargs)

    def _setup_regular(self, env):
        super(Many2many, self)._setup_regular(env)

        if self.store and not self.relation:
            model = env[self.model_name]
            column = model._columns[self.name]
            if not isinstance(column, fields.function):
                self.relation, self.column1, self.column2 = column._sql_names(model)

        if self.relation:
            expected = (self.relation, self.column2, self.column1)
            for field in env[self.comodel_name]._fields.itervalues():
                field.setup(env)
                if isinstance(field, Many2many) and \
                        (field.relation, field.column1, field.column2) == expected:
                    self.inverse_field = field
                    break

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

    def __get__(self, instance, owner):
        if instance is None:
            return self         # the field is accessed through the class owner
        return bool(instance._ids) and instance._ids[0]

    def __set__(self, instance, value):
        raise NotImplementedError()


# imported here to avoid dependency cycle issues
from openerp import SUPERUSER_ID
from openerp.exceptions import Warning, MissingError
from openerp.osv import fields
from openerp.osv.orm import BaseModel, MAGIC_COLUMNS
