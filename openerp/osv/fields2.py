# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 OpenERP (<http://www.openerp.com>).
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

import base64
from copy import copy
from datetime import date, datetime

from openerp.tools import float_round, ustr, html_sanitize, lazy_property
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


def _invoke_model(func, model):
    """ hack for invoking a callable with a model in both API styles """
    try:
        return func(model)
    except TypeError:
        cr, uid, context = scope
        return func(model, cr, uid, context=context)


class MetaField(type):
    """ Metaclass for field classes. """
    _class_by_type = {}

    def __init__(cls, name, bases, attrs):
        super(MetaField, cls).__init__(name, bases, attrs)
        if cls.type:
            cls._class_by_type[cls.type] = cls


class Field(object):
    """ Base class of all fields. """
    __metaclass__ = MetaField

    interface = False           # whether the field is created by the ORM

    name = None                 # name of the field
    model = None                # name of the model of this field
    type = None                 # type of the field (string)
    relational = False          # whether the field is a relational one

    store = True                # whether the field is stored in database
    compute = None              # name of model method that computes value
    depends = ()                # collection of field dependencies

    string = None               # field label
    help = None                 # field tooltip
    readonly = False
    required = False
    groups = False              # csv list of group xml ids

    # attributes passed when converting from/to a column
    _attrs = ('string', 'help', 'readonly', 'required', 'groups')

    # attributes exported by get_description()
    _desc0 = ('type', 'store')
    _desc1 = ('compute', 'depends', 'string', 'help', 'readonly', 'required', 'groups')

    def __init__(self, string=None, **kwargs):
        kwargs['string'] = string
        for attr in kwargs:
            setattr(self, attr, kwargs[attr])

    def copy(self):
        """ make a copy of `self` (used for field inheritance among models) """
        field = copy(self)
        # reset all lazy properties
        for attr, value in field.__class__.__dict__.iteritems():
            if isinstance(value, lazy_property):
                field.__dict__.pop(attr, None)
        return field

    def set_model_name(self, model, name):
        """ assign the model and field names of `self` """
        self.model = model
        self.name = name
        if not self.string:
            self.string = name.replace('_', ' ').capitalize()

    def get_description(self):
        """ Return a dictionary that describes the field `self`. """
        desc = {}
        for arg in self._desc0:
            desc[arg] = getattr(self, arg)
        for arg in self._desc1:
            if getattr(self, arg, None):
                desc[arg] = getattr(self, arg)
        return desc

    @classmethod
    def from_column(cls, column):
        """ return a field for interfacing the low-level field `column` """
        # delegate to the subclass corresponding to the column type, or Field
        # for unknown column types
        field_class = cls._class_by_type.get(column._type, Field)
        field = field_class._from_column(column)
        field.interface = True
        return field

    @classmethod
    def _from_column(cls, column):
        # generic implementation
        kwargs = dict((attr, getattr(column, attr)) for attr in cls._attrs)
        if cls is Field:
            kwargs['type'] = column._type
        return cls(**kwargs)

    def to_column(self):
        """ return a low-level field object corresponding to `self` """
        kwargs = dict((attr, getattr(self, attr)) for attr in self._attrs)
        if self.store:
            column_type = getattr(fields, self.type)
        else:
            from . import api
            column_type = fields.function
            kwargs['store'] = False
            kwargs['type'] = self.type
            @api.recordset
            def fnct(self, field_name, arg):
                return dict((record.id, record[field_name])
                            for record in self.exists())
            kwargs['fnct'] = fnct

        column_type, kwargs = self._to_column(column_type, kwargs)
        return column_type(**kwargs)

    def _to_column(self, column_type, kwargs):
        return column_type, kwargs

    def __get__(self, instance, owner):
        """ read the value of field `self` for the record `instance` """
        if instance is None:
            return self         # the field is accessed through the class owner
        assert instance._name == self.model
        return instance._get_field(self.name)

    def __set__(self, instance, value):
        """ set the value of field `self` for the record `instance` """
        assert instance._name == self.model
        # adapt value to the cache level (must be in record's scope!)
        with instance._scope:
            value = self.convert_value(value)
        return instance._set_field(self.name, value)

    def null(self):
        """ return the null value for this field """
        return False

    def convert_value(self, value):
        """ convert `value` (from an assignment) to the cache level """
        return value

    def convert_from_read(self, value):
        """ convert `value` from method :meth:`openerp.osv.orm.BaseModel.read`
            to the cache level
        """
        return value

    def convert_to_read(self, value):
        """ convert `value` from the cache to a value as returned by method
            :meth:`openerp.osv.orm.BaseModel.read`
        """
        return value

    def convert_to_write(self, value):
        """ convert `value` from the cache to a valid value for method
            :meth:`openerp.osv.orm.BaseModel.write`
        """
        return value

    def compute_default(self, record):
        """ assign the default value of field `self` to `record` """
        if self.compute:
            getattr(record, self.compute)()
        else:
            # Do not store the null value in record._record_draft, since it is
            # not a "forced" null value. Instead, put it in the regular cache.
            # The purpose is to not make it visible in record._record_draft.
            record._record_cache[self.name] = self.null()


class Boolean(Field):
    """ Boolean field. """
    type = 'boolean'

    def convert_value(self, value):
        return bool(value)


class Integer(Field):
    """ Integer field. """
    type = 'integer'

    def convert_value(self, value):
        return int(value or 0)


class Float(Field):
    """ Float field. """
    type = 'float'
    digits = None                       # None, (precision, scale), or callable

    _attrs = Field._attrs + ('digits',)
    _desc1 = Field._desc1 + ('digits',)

    @classmethod
    def _from_column(cls, column):
        column.digits_change(scope.cr)      # determine column.digits
        kwargs = dict((attr, getattr(column, attr)) for attr in cls._attrs)
        return cls(**kwargs)

    def to_column(self):
        if callable(self.digits):
            self.digits = self.digits(scope.cr)
        return super(Float, self).to_column()

    def convert_value(self, value):
        # apply rounding here, otherwise value in cache may be wrong!
        if self.digits:
            return float_round(float(value or 0.0), precision_digits=self.digits[1])
        else:
            return float(value or 0.0)


class _String(Field):
    """ Abstract class for string fields. """
    translate = False

    _attrs = Field._attrs + ('translate',)
    _desc1 = Field._desc1 + ('translate',)

    def convert_value(self, value):
        return bool(value) and ustr(value)


class Char(_String):
    """ Char field. """
    type = 'char'
    size = None

    _attrs = _String._attrs + ('size',)
    _desc1 = _String._desc1 + ('size',)

    def convert_value(self, value):
        return bool(value) and ustr(value)[:self.size]


class Text(_String):
    """ Text field. """
    type = 'text'


class Html(_String):
    """ Html field. """
    type = 'html'

    def convert_value(self, value):
        return bool(value) and html_sanitize(value)


class Date(Field):
    """ Date field. """
    type = 'date'

    def convert_value(self, value):
        if isinstance(value, (date, datetime)):
            value = value.strftime(DEFAULT_SERVER_DATE_FORMAT)
        elif value:
            datetime.strptime(value, DEFAULT_SERVER_DATE_FORMAT)    # check format
        return value or False


class Datetime(Field):
    """ Datetime field. """
    type = 'datetime'

    def convert_value(self, value):
        if isinstance(value, (date, datetime)):
            value = value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        elif value:
            datetime.strptime(value, DEFAULT_SERVER_DATETIME_FORMAT)    # check format
        return value or False


class Binary(Field):
    """ Binary field. """
    type = 'binary'

    def convert_value(self, value):
        if value:
            base64.b64decode(value)             # check value format
        return value or False


class Selection(Field):
    """ Selection field. """
    type = 'selection'
    selection = None        # [(value, string), ...], model method or method name

    _attrs = Field._attrs + ('selection',)

    def __init__(self, selection, string=None, **kwargs):
        """ Selection field.

            :param selection: specifies the possible values for this field.
                It is given as either a list of pairs (`value`, `string`), or a
                model method, or a method name.
        """
        super(Selection, self).__init__(selection=selection, string=string, **kwargs)

    def get_description(self):
        desc = super(Selection, self).get_description()
        desc['selection'] = self.get_selection()
        return desc

    def _to_column(self, column_type, kwargs):
        if isinstance(self.selection, basestring):
            method = self.selection
            kwargs['selection'] = lambda self, *args, **kwargs: getattr(self, method)(*args, **kwargs)
        return super(Selection, self)._to_column(column_type, kwargs)

    def get_selection(self):
        """ return the selection list (pairs (value, string)) """
        value = self.selection
        if isinstance(value, basestring):
            value = getattr(scope.model(self.model), value)()
        elif callable(value):
            value = _invoke_model(value, scope.model(self.model))
        return value

    def get_values(self):
        """ return a list of the possible values """
        return [item[0] for item in self.get_selection()]

    def convert_value(self, value):
        if value is None or value is False:
            return False
        if value in self.get_values():
            return value
        raise ValueError("Wrong value for %s.%s: %r" % (self.model, self.name, value))


class Reference(Selection):
    """ Reference field. """
    type = 'reference'
    size = 128

    _attrs = Selection._attrs + ('size',)

    def __init__(self, selection, string=None, **kwargs):
        """ Reference field.

            :param selection: specifies the possible model names for this field.
                It is given as either a list of pairs (`value`, `string`), or a
                model method, or a method name.
        """
        super(Reference, self).__init__(selection=selection, string=string, **kwargs)

    def convert_value(self, value):
        if value is None or value is False:
            return False
        if isinstance(value, Record) and value._name in self.get_values():
            return value.scoped()
        raise ValueError("Wrong value for %s.%s: %r" % (self.model, self.name, value))

    def convert_from_read(self, value):
        if value:
            res_model, res_id = value.split(',')
            return scope.model(res_model).record(int(res_id))
        return False

    def convert_to_read(self, value):
        return "%s,%s" % (value._name, value._record_id) if value else False

    def convert_to_write(self, value):
        return "%s,%s" % (value._name, value._record_id) if value else False


class Many2one(Field):
    """ Many2one field. """
    type = 'many2one'
    relational = True
    comodel = None                      # model of values
    ondelete = None                     # defaults to 'set null' in ORM
    domain = None
    context = None

    _attrs = Field._attrs + ('ondelete',)

    def __init__(self, comodel, string=None, **kwargs):
        super(Many2one, self).__init__(comodel=comodel, string=string, **kwargs)

    @lazy_property
    def inverse(self):
        # retrieve the name of the inverse field, if it exists
        comodel = scope.model(self.comodel)
        for field in comodel._fields.itervalues():
            if isinstance(field, One2many) and \
                    field.comodel == self.model and field.inverse == self.name:
                return field.name
        return None

    @lazy_property
    def inherits(self):
        """ Whether `self` implements inheritance between model and comodel. """
        model = scope.model(self.model)
        return self.name in model._inherits.itervalues()

    def get_description(self):
        desc = super(Many2one, self).get_description()
        desc['relation'] = self.comodel
        desc['domain'] = self.domain(model) if callable(self.domain) else self.domain
        desc['context'] = self.context
        return desc

    @classmethod
    def _from_column(cls, column):
        kwargs = dict((attr, getattr(column, attr)) for attr in cls._attrs)
        kwargs['comodel'] = column._obj
        return cls(**kwargs)

    def _to_column(self, column_type, kwargs):
        kwargs['obj'] = self.comodel
        kwargs['domain'] = self.domain or []
        return super(Many2one, self)._to_column(column_type, kwargs)

    def null(self):
        return scope.model(self.comodel).null()

    def convert_value(self, value):
        if value is None or value is False:
            return self.null()
        if isinstance(value, Record) and value._name == self.comodel:
            return value.scoped()
        raise ValueError("Wrong value for %s.%s: %r" % (self.model, self.name, value))

    def convert_from_read(self, value):
        if isinstance(value, tuple):
            value = value[0]
        return scope.model(self.comodel).record(value)

    def convert_to_read(self, value):
        return bool(value) and value.name_get()

    def convert_to_write(self, value):
        return value._record_id

    def compute_default(self, record):
        super(Many2one, self).compute_default(record)
        if self.inherits:
            # special case: fields that implement inheritance between models
            value = record[self.name]
            if value.is_null() and not value.is_draft():
                # put a draft record instead of the null record
                record[self.name] = scope.model(self.comodel).draft()


class One2many(Field):
    """ One2many field. """
    type = 'one2many'
    relational = True
    comodel = None                      # model of values
    inverse = None                      # name of inverse field
    domain = None
    context = None

    def __init__(self, comodel, inverse=None, string=None, **kwargs):
        super(One2many, self).__init__(
            comodel=comodel, inverse=inverse, string=string, **kwargs)

    def get_description(self):
        desc = super(One2many, self).get_description()
        desc['relation'] = self.comodel
        desc['relation_field'] = self.inverse
        desc['domain'] = self.domain(model) if callable(self.domain) else self.domain
        desc['context'] = self.context
        return desc

    @classmethod
    def _from_column(cls, column):
        kwargs = dict((attr, getattr(column, attr)) for attr in cls._attrs)
        # beware when getting parameters: column may be a function field
        kwargs['comodel'] = column._obj
        kwargs['inverse'] = getattr(column, '_fields_id', None)
        return cls(**kwargs)

    def _to_column(self, column_type, kwargs):
        kwargs['obj'] = self.comodel
        kwargs['fields_id'] = self.inverse
        kwargs['domain'] = self.domain or []
        return super(One2many, self)._to_column(column_type, kwargs)

    def null(self):
        return scope.model(self.comodel).recordset()

    def convert_value(self, value):
        if value is None or value is False:
            return self.null()
        if isinstance(value, Recordset) and value._name == self.comodel:
            return value.scoped()
        raise ValueError("Wrong value for %s.%s: %s" % (self.model, self.name, value))

    def convert_from_read(self, value):
        return scope.model(self.comodel).recordset(value or ())

    def convert_to_read(self, value):
        return value.unbrowse()

    def convert_to_write(self, value):
        result = [(5,)]
        for record in value:
            if record.is_draft():
                result.append((0, 0, record.get_draft_values()))
            else:
                result.append((4, record._record_id))
        return result


class Many2many(Field):
    """ Many2many field. """
    type = 'many2many'
    relational = True
    comodel = None                      # model of values
    relation = None                     # name of table
    column1 = None                      # column of table referring to model
    column2 = None                      # column of table referring to comodel
    domain = None
    context = None

    def __init__(self, comodel, relation=None, column1=None, column2=None,
                string=None, **kwargs):
        super(Many2many, self).__init__(comodel=comodel, relation=relation,
            column1=column1, column2=column2, string=string, **kwargs)

    @lazy_property
    def inverse(self):
        if not self.compute:
            # retrieve the name of the inverse field, if it exists
            comodel = scope.model(self.comodel)
            expected = (self.relation, self.column2, self.column1)
            for field in comodel._fields.itervalues():
                if isinstance(field, Many2many) and \
                        (field.relation, field.column1, field.column2) == expected:
                    return field.name
        return None

    def get_description(self):
        desc = super(Many2many, self).get_description()
        desc['relation'] = self.comodel
        desc['domain'] = self.domain(model) if callable(self.domain) else self.domain
        desc['context'] = self.context
        return desc

    @classmethod
    def _from_column(cls, column):
        kwargs = dict((attr, getattr(column, attr)) for attr in cls._attrs)
        # beware when getting parameters: column may be a function field
        kwargs['comodel'] = column._obj
        kwargs['relation'] = getattr(column, '_rel', None)
        kwargs['column1'] = getattr(column, '_id1', None)
        kwargs['column2'] = getattr(column, '_id2', None)
        return cls(**kwargs)

    def _to_column(self, column_type, kwargs):
        kwargs['obj'] = self.comodel
        kwargs['rel'] = self.relation
        kwargs['id1'] = self.column1
        kwargs['id2'] = self.column2
        kwargs['domain'] = self.domain or []
        return super(Many2many, self)._to_column(column_type, kwargs)

    def null(self):
        return scope.model(self.comodel).recordset()

    def convert_value(self, value):
        if value is None or value is False:
            return self.null()
        if isinstance(value, Recordset) and value._name == self.comodel:
            return value.scoped()
        raise ValueError("Wrong value for %s.%s: %s" % (self.model, self.name, value))

    def convert_from_read(self, value):
        return scope.model(self.comodel).recordset(value or ())

    def convert_to_read(self, value):
        return value.unbrowse()

    def convert_to_write(self, value):
        result = [(5,)]
        for record in value:
            if record.is_draft():
                result.append((0, 0, record.get_draft_values()))
            else:
                result.append((4, record._record_id))
        return result


class Related(Field):
    """ Related field. """
    store = False               # by default related fields are not stored
    related = None              # sequence of field names

    def __init__(self, *args, **kwargs):
        assert args, "Related field must be given a sequence of field names"
        super(Related, self).__init__(related=args, **kwargs)
        assert not self.store

    @lazy_property
    def related_field(self):
        """ determine the related field corresponding to `self` """
        rec = scope.model(self.model).null()
        for name in self.related[:-1]:
            rec = rec[name].null()
        return rec._fields[self.related[-1]]

    @lazy_property
    def type(self):
        return self.related_field.type

    @lazy_property
    def get_description(self):
        return self.related_field.get_description

    def __getattr__(self, name):
        # delegate getattr on related field
        return getattr(self.related_field, name)

    @classmethod
    def _from_column(cls, column):
        raise NotImplementedError()

    def to_column(self):
        if self.store:
            raise NotImplementedError()

        return super(Related, self).to_column()

    def __get__(self, instance, owner):
        if instance is None:
            return self
        # traverse the caches, and delegate to the last record
        for name in self.related[:-1]:
            instance = instance[name].to_record()
        return instance[self.related[-1]]

    def __set__(self, instance, value):
        # traverse the caches, and delegate to the last record
        for name in self.related[:-1]:
            instance = instance[name].to_record()
        instance[self.related[-1]] = value

    @lazy_property
    def null(self):
        return self.related_field.null

    @lazy_property
    def convert_value(self):
        return self.related_field.convert_value

    @lazy_property
    def convert_from_read(self):
        return self.related_field.convert_from_read

    @lazy_property
    def convert_to_read(self):
        return self.related_field.convert_to_read

    @lazy_property
    def convert_to_write(self):
        return self.related_field.convert_to_write


class Id(Field):
    """ Special case for field 'id'. """
    interface = True            # that field is always created by the ORM
    store = False
    readonly = True

    @classmethod
    def _from_column(cls, column):
        raise NotImplementedError()

    def to_column(self):
        raise NotImplementedError()

    def __get__(self, instance, owner):
        if instance is None:
            return self         # the field is accessed through the class owner
        assert instance.is_record()
        return instance._record_id

    def __set__(self, instance, value):
        raise NotImplementedError()


# imported here to avoid dependency cycle issues
from openerp.osv import fields
from openerp.osv.orm import Record, Recordset
from openerp.osv.scope import proxy as scope
