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

from openerp.tools import float_round, ustr, html_sanitize
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


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

    name = None                 # name of the field
    model = None                # name of the model of this field
    type = None                 # type of the field (string)

    store = True                # whether the field is stored in database
    compute = None              # name of model method that computes value
    depends = ()                # collection of field dependencies

    string = None               # field label
    help = None                 # field tooltip
    readonly = False
    required = False

    # attributes passed when converting from/to a column
    _attrs = ('string', 'help', 'readonly', 'required')

    def __init__(self, string=None, **kwargs):
        kwargs['string'] = string
        for attr in kwargs:
            setattr(self, attr, kwargs[attr])

    def copy(self):
        """ make a copy of `self` (used for field inheritance among models) """
        return copy(self)

    def set_model_name(self, model, name):
        """ assign the model and field names of `self` """
        self.model = model
        self.name = name
        if not self.string:
            self.string = name.replace('_', ' ').capitalize()

    @classmethod
    def from_column(cls, column):
        """ return a field for the low-level field `column` """
        # delegate to the subclass corresponding to the column type, or Field
        # for unknown column types
        field_class = cls._class_by_type.get(column._type, Field)
        return field_class._from_column(column)

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
        return getattr(fields, self.type)(**kwargs)

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
            value = self.record_to_cache(value)
        return instance._set_field(self.name, value)

    def null(self):
        """ return the null value for this field """
        return False

    def record_to_cache(self, value):
        """ convert `value` from the record level to the cache level """
        return value

    def record_to_read(self, value):
        """ convert `value` from the record level to a value as returned by
            :meth:`openerp.osv.orm.BaseModel.read`
        """
        return value


class Boolean(Field):
    """ Boolean field. """
    type = 'boolean'

    def record_to_cache(self, value):
        return bool(value)


class Integer(Field):
    """ Integer field. """
    type = 'integer'

    def record_to_cache(self, value):
        return int(value or 0)


class Float(Field):
    """ Float field. """
    type = 'float'
    digits = None                       # None, (precision, scale), or callable
    _attrs = Field._attrs + ('digits',)

    @classmethod
    def _from_column(cls, column):
        column.digits_change(scope.cr)      # determine column.digits
        kwargs = dict((attr, getattr(column, attr)) for attr in cls._attrs)
        return cls(**kwargs)

    def to_column(self):
        if callable(self.digits):
            self.digits = self.digits(scope.cr)
        return super(Float, self).to_column()

    def record_to_cache(self, value):
        # apply rounding here, otherwise value in cache may be wrong!
        if self.digits:
            return float_round(float(value or 0.0), precision_digits=self.digits[1])
        else:
            return float(value or 0.0)


class _String(Field):
    """ Abstract class for string fields. """
    translate = False
    _attrs = Field._attrs + ('translate',)

    def record_to_cache(self, value):
        return bool(value) and ustr(value)


class Char(_String):
    """ Char field. """
    type = 'char'
    size = None
    _attrs = _String._attrs + ('size',)

    def record_to_cache(self, value):
        return bool(value) and ustr(value)[:self.size]


class Text(_String):
    """ Text field. """
    type = 'text'


class Html(_String):
    """ Html field. """
    type = 'html'

    def record_to_cache(self, value):
        return bool(value) and html_sanitize(value)


class Date(Field):
    """ Date field. """
    type = 'date'

    def record_to_cache(self, value):
        if isinstance(value, (date, datetime)):
            value = value.strftime(DEFAULT_SERVER_DATE_FORMAT)
        elif value:
            datetime.strptime(value, DEFAULT_SERVER_DATE_FORMAT)    # check format
        return value or False


class Datetime(Field):
    """ Datetime field. """
    type = 'datetime'

    def record_to_cache(self, value):
        if isinstance(value, (date, datetime)):
            value = value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        elif value:
            datetime.strptime(value, DEFAULT_SERVER_DATETIME_FORMAT)    # check format
        return value or False


class Binary(Field):
    """ Binary field. """
    type = 'binary'

    def record_to_cache(self, value):
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

    def to_column(self):
        kwargs = dict((attr, getattr(self, attr)) for attr in self._attrs)
        if isinstance(self.selection, basestring):
            method = self.selection
            kwargs['selection'] = lambda self, *args, **kwargs: getattr(self, method)(*args, **kwargs)
        return getattr(fields, self.type)(**kwargs)

    def get_values(self):
        """ return a list of the possible values """
        value = self.selection
        if isinstance(value, basestring):
            value = getattr(scope.model(self.model), value)()
        elif callable(value):
            value = value(scope.model(self.model))
        return [item[0] for item in value]

    def record_to_cache(self, value):
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

    def record_to_cache(self, value):
        if value is None or value is False:
            return False
        if isinstance(value, Record) and value._name in self.get_values():
            return value.scoped()
        raise ValueError("Wrong value for %s.%s: %r" % (self.model, self.name, value))


class Many2one(Field):
    """ Many2one field. """
    type = 'many2one'
    comodel = None                      # model of values

    def __init__(self, comodel, string=None, **kwargs):
        super(Many2one, self).__init__(comodel=comodel, string=string, **kwargs)

    @classmethod
    def _from_column(cls, column):
        kwargs = dict((attr, getattr(column, attr)) for attr in cls._attrs)
        kwargs['comodel'] = column._obj
        return cls(**kwargs)

    def to_column(self):
        kwargs = dict((attr, getattr(self, attr)) for attr in self._attrs)
        kwargs['obj'] = self.comodel
        return fields.many2one(**kwargs)

    def null(self):
        return scope.model(self.comodel).null()

    def record_to_cache(self, value):
        if value is None or value is False:
            return self.null()
        if isinstance(value, Record) and value._name == self.comodel:
            return value.scoped()
        raise ValueError("Wrong value for %s.%s: %r" % (self.model, self.name, value))

    def record_to_read(self, value):
        return bool(value) and value.name_get()


class One2many(Field):
    """ One2many field. """
    type = 'one2many'
    comodel = None                      # model of values
    inverse = None                      # name of inverse field

    def __init__(self, comodel, inverse=None, string=None, **kwargs):
        super(One2many, self).__init__(
            comodel=comodel, inverse=inverse, string=string, **kwargs)

    @classmethod
    def _from_column(cls, column):
        kwargs = dict((attr, getattr(column, attr)) for attr in cls._attrs)
        # beware when getting parameters: column may be a function field
        kwargs['comodel'] = column._obj
        kwargs['inverse'] = getattr(column, '_fields_id', None)
        return cls(**kwargs)

    def to_column(self):
        kwargs = dict((attr, getattr(self, attr)) for attr in self._attrs)
        kwargs['obj'] = self.comodel
        kwargs['fields_id'] = self.inverse
        return fields.one2many(**kwargs)

    def null(self):
        return scope.model(self.comodel).recordset()

    def record_to_cache(self, value):
        if value is None or value is False:
            return self.null()
        if isinstance(value, Recordset) and value._name == self.comodel:
            return value.scoped()
        raise ValueError("Wrong value for %s.%s: %s" % (self.model, self.name, value))


class Many2many(Field):
    """ Many2many field. """
    type = 'many2many'
    comodel = None                      # model of values
    relation = None                     # name of table
    column1 = None                      # column of table referring to model
    column2 = None                      # column of table referring to comodel

    def __init__(self, comodel, relation=None, column1=None, column2=None,
                string=None, **kwargs):
        super(Many2many, self).__init__(comodel=comodel, relation=relation,
            column1=column1, column2=column2, string=string, **kwargs)

    @classmethod
    def _from_column(cls, column):
        kwargs = dict((attr, getattr(column, attr)) for attr in cls._attrs)
        # beware when getting parameters: column may be a function field
        kwargs['comodel'] = column._obj
        kwargs['relation'] = getattr(column, '_rel', None)
        kwargs['column1'] = getattr(column, '_id1', None)
        kwargs['column2'] = getattr(column, '_id2', None)
        return cls(**kwargs)

    def to_column(self):
        kwargs = dict((attr, getattr(self, attr)) for attr in self._attrs)
        kwargs['obj'] = self.comodel
        kwargs['rel'] = self.relation
        kwargs['id1'] = self.column1
        kwargs['id2'] = self.column2
        return fields.many2many(**kwargs)

    def null(self):
        return scope.model(self.comodel).recordset()

    def record_to_cache(self, value):
        if value is None or value is False:
            return self.null()
        if isinstance(value, Recordset) and value._name == self.comodel:
            return value.scoped()
        raise ValueError("Wrong value for %s.%s: %s" % (self.model, self.name, value))


# imported here to avoid dependency cycle issues
from openerp.osv import fields
from openerp.osv.orm import Record, Recordset
from openerp.osv.scope import proxy as scope
