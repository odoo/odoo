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
import logging

from openerp.tools import float_round, ustr, html_sanitize, lazy_property
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


def _invoke_model(func, model):
    """ hack for invoking a callable with a model in both API styles """
    try:
        return func(model)
    except TypeError:
        return func(model, *scope.args)


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
    model_name = None           # name of the model of this field
    type = None                 # type of the field (string)
    relational = False          # whether the field is a relational one
    inverse_field = None        # inverse field (object), if it exists

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

    def set_model_name(self, model_name, name):
        """ assign the model and field names of `self` """
        self.model_name = model_name
        self.name = name
        if not self.string:
            self.string = name.replace('_', ' ').capitalize()

    def __str__(self):
        return "%s.%s" % (self.model_name, self.name)

    @lazy_property
    def model(self):
        """ return the model instance of `self` """
        return scope.model(self.model_name)

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
        assert self.store
        kwargs = self._to_column()
        return getattr(fields, self.type)(**kwargs)

    def _to_column(self):
        """ return a kwargs dictionary to pass to the column class """
        return dict((attr, getattr(self, attr)) for attr in self._attrs)

    def __get__(self, instance, owner):
        """ read the value of field `self` for the record `instance` """
        if instance is None:
            return self         # the field is accessed through the class owner
        assert instance._name == self.model_name
        return instance._get_field(self.name)

    def __set__(self, instance, value):
        """ set the value of field `self` for the record `instance` """
        assert instance._name == self.model_name
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

    def convert_from_write(self, value):
        """ convert `value` from method :meth:`openerp.osv.orm.BaseModel.write`
            the cache level
        """
        return self.convert_from_read(value)

    def convert_to_write(self, value):
        """ convert `value` from the cache to a valid value for method
            :meth:`openerp.osv.orm.BaseModel.write`
        """
        return self.convert_to_read(value)

    def convert_to_export(self, value):
        """ convert `value` from the cache to a valid value for export. """
        return bool(value) and ustr(value)

    def compute_default(self, record):
        """ assign the default value of field `self` to `record` """
        if self.compute:
            getattr(record, self.compute)()
        else:
            # None means "no value" in the case of draft records
            record._set_field(self.name, None)

    #
    # Management of the recomputation of computed fields.
    #
    # Each field stores a set of triggers (`field`, `path`); when the field is
    # modified, it invalidates the cache of `field` and registers the records to
    # recompute based on `path`. See method `modified` below for details.
    #

    def manage_dependencies(self):
        """ Make `self` process its own dependencies and store triggers on other
            fields to be recomputed.
        """
        if self.compute:
            method = getattr(type(self.model), self.compute)
            self.depends = getattr(method, '_depends', ())
        for path in self.depends:
            self._depends_on_model(self.model, [], path.split('.'))

    def _depends_on_model(self, model, path0, path1):
        """ Make `self` depend on `model`; `path0 + path1` is a dependency of
            `self`, and `path0` is the sequence of field names from `self.model`
            to `model`.
        """
        name, tail = path1[0], path1[1:]
        if name == '*':
            # special case: add triggers on all fields of model
            fields = model._fields.values()
        else:
            fields = (model._fields[name],)

        for field in fields:
            field._add_trigger_for(self, path0, tail)

    @lazy_property
    def _triggers(self):
        """ List of pairs (`field`, `path`), where `field` is a field to
            recompute, and `path` is the dependency between `field` and `self`
            (dot-separated sequence of field names between `field.model` and
            `self.model`).
        """
        return []

    def _add_trigger_for(self, field, path0, path1):
        """ Add a trigger on `self` to recompute `field`; `path0` is the
            sequence of field names from `field.model` to `self.model`; ``path0
            + [self.name] + path1`` is a dependency of `field`.
        """
        self._triggers.append((field, '.'.join(path0) if path0 else 'id'))
        _logger.debug("Add trigger on field %s to recompute field %s", self, field)

    def modified(self, records):
        """ Notify that field `self` has been modified on `records`: invalidate
            the cache, and return a sequence of triples (`model_name`,
            `field_name`, `record_ids`) to recompute.
        """
        # invalidate cache for self
        ids = records.unbrowse()
        records.invalidate_cache((self.name,), ids)
        # invalidate dependent fields, and prepare their recomputation
        for field, path in self._triggers:
            if field.store:
                with scope.SUDO():
                    target = field.model.search([(path, 'in', ids)])
                scope.invalidate(field.model_name, field.name, target.unbrowse())
                scope.recomputation.todo(field, target)
            else:
                scope.invalidate(field.model_name, field.name, None)

    def modified_draft(self, records):
        """ Same as :meth:`modified`, but in the case where `records` is a draft
            instance.
        """
        # invalidate cache for self
        ids = records.unbrowse()
        scope.invalidate(self.model_name, self.name, ids)
        # invalidate dependent fields of records only
        for field, _path in self._triggers:
            if field.model_name == records._name:
                scope.invalidate(field.model_name, field.name, ids)


class Boolean(Field):
    """ Boolean field. """
    type = 'boolean'

    def convert_value(self, value):
        return bool(value)

    def convert_to_export(self, value):
        return ustr(value)


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

    def _to_column(self):
        kwargs = super(Selection, self)._to_column()
        if isinstance(self.selection, basestring):
            method = self.selection
            kwargs['selection'] = lambda self, *args, **kwargs: getattr(self, method)(*args, **kwargs)
        return kwargs

    def get_selection(self):
        """ return the selection list (pairs (value, string)) """
        value = self.selection
        if isinstance(value, basestring):
            value = getattr(self.model, value)()
        elif callable(value):
            value = _invoke_model(value, self.model)
        return value

    def get_values(self):
        """ return a list of the possible values """
        return [item[0] for item in self.get_selection()]

    def convert_value(self, value):
        if value is None or value is False:
            return False
        if value in self.get_values():
            return value
        raise ValueError("Wrong value for %s: %r" % (self, value))

    def convert_to_export(self, value):
        if not isinstance(self.selection, list):
            # FIXME: this reproduces an existing buggy behavior!
            return value
        for item in self.get_selection():
            if item[0] == value:
                return item[1]
        return False


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
        if isinstance(value, BaseModel) and value._name in self.get_values() and len(value) == 1:
            return value.scoped()
        raise ValueError("Wrong value for %s: %r" % (self, value))

    def convert_from_read(self, value):
        if value:
            res_model, res_id = value.split(',')
            return scope.model(res_model).browse(int(res_id))
        return False

    def convert_to_read(self, value):
        return "%s,%s" % (value._name, value.id) if value else False

    def convert_to_export(self, value):
        return bool(value) and value.name_get()[0][1]


class _Relational(Field):
    """ Abstract class for relational fields. """
    relational = True
    comodel_name = None                 # name of model of values
    domain = None                       # domain for searching values
    context = None                      # context for searching values

    @lazy_property
    def comodel(self):
        """ return the comodel instance of `self` """
        return scope.model(self.comodel_name)

    def get_description(self):
        desc = super(_Relational, self).get_description()
        desc['relation'] = self.comodel_name
        desc['domain'] = self.domain(self.model) if callable(self.domain) else self.domain
        desc['context'] = self.context
        return desc

    def null(self):
        return self.comodel.browse()

    def _add_trigger_for(self, field, path0, path1):
        # overridden to traverse relations and manage inverse fields
        Field._add_trigger_for(self, field, path0, [])

        if self.inverse_field:
            # add trigger on inverse field, too
            Field._add_trigger_for(self.inverse_field, field, path0 + [self.name], [])

        if path1:
            # recursively traverse the dependency
            field._depends_on_model(self.comodel, path0 + [self.name], path1)


class Many2one(_Relational):
    """ Many2one field. """
    type = 'many2one'
    ondelete = None                     # defaults to 'set null' in ORM

    _attrs = Field._attrs + ('ondelete',)

    def __init__(self, comodel_name, string=None, **kwargs):
        super(Many2one, self).__init__(comodel_name=comodel_name, string=string, **kwargs)

    @lazy_property
    def inverse_field(self):
        for field in self.comodel._fields.itervalues():
            if isinstance(field, One2many) and field.inverse_field == self:
                return field
        return None

    @lazy_property
    def inherits(self):
        """ Whether `self` implements inheritance between model and comodel. """
        return self.name in self.model._inherits.itervalues()

    @classmethod
    def _from_column(cls, column):
        kwargs = dict((attr, getattr(column, attr)) for attr in cls._attrs)
        kwargs['comodel_name'] = column._obj
        return cls(**kwargs)

    def _to_column(self):
        kwargs = super(Many2one, self)._to_column()
        kwargs['obj'] = self.comodel_name
        kwargs['domain'] = self.domain or []
        return kwargs

    def convert_value(self, value):
        if value is None or value is False:
            return self.null()
        if isinstance(value, BaseModel) and value._name == self.comodel_name and len(value) <= 1:
            return value.scoped()
        raise ValueError("Wrong value for %s: %r" % (self, value))

    def convert_from_read(self, value):
        if isinstance(value, tuple):
            value = value[0]
        return self.comodel.browse(value)

    def convert_to_read(self, value):
        return bool(value) and value.name_get()[0]

    def convert_from_write(self, value):
        if isinstance(value, dict):
            # convert values to the cache level
            return self.comodel.draft(dict(
                (k, self.comodel._fields[k].convert_from_write(v))
                for k, v in value.iteritems()
            ))
        return self.comodel.browse(value)

    def convert_to_write(self, value):
        if value.is_draft():
            return False
        return value.id

    def convert_to_export(self, value):
        return bool(value) and value.name_get()[0][1]

    def compute_default(self, record):
        super(Many2one, self).compute_default(record)
        if self.inherits:
            # special case: fields that implement inheritance between models
            value = record[self.name]
            if not value:
                # the default value cannot be null, use a draft record instead
                record[self.name] = self.comodel.draft()


class _RelationalMulti(_Relational):
    """ Abstract class for relational fields *2many. """

    def convert_value(self, value):
        if value is None or value is False:
            return self.null()
        if isinstance(value, BaseModel) and value._name == self.comodel_name:
            return value.scoped()
        raise ValueError("Wrong value for %s: %s" % (self, value))

    def convert_from_read(self, value):
        return self.comodel.browse(value or ())

    def convert_to_read(self, value):
        return value.unbrowse()

    def convert_from_write(self, value):
        ids = []
        for command in value:
            if isinstance(command, (int, long)):
                ids.append(command)
            elif command[0] == 0:
                record = self.comodel.draft(dict(
                    (k, self.comodel._fields[k].convert_from_write(v))
                    for k, v in command[2].iteritems()
                ))
                ids.append(record.id)
            elif command[0] == 1:
                raise NotImplementedError()
            elif command[0] == 2:
                pass
            elif command[0] == 3:
                pass
            elif command[0] == 4:
                ids.append(command[1])
            elif command[0] == 5:
                ids = []
            elif command[0] == 6:
                ids = list(command[2])
        return self.comodel.browse(ids)

    def convert_to_write(self, value):
        result = [(5,)]
        for record in value:
            if record.is_draft():
                result.append((0, 0, record.get_draft_values()))
            else:
                result.append((4, record.id))
        return result

    def convert_to_export(self, value):
        return bool(value) and ','.join(name for id, name in value.name_get())


class One2many(_RelationalMulti):
    """ One2many field. """
    type = 'one2many'
    inverse_name = None                 # name of the inverse field

    def __init__(self, comodel_name, inverse_name=None, string=None, **kwargs):
        super(One2many, self).__init__(
            comodel_name=comodel_name, inverse_name=inverse_name, string=string, **kwargs)

    @lazy_property
    def inverse_field(self):
        return self.inverse_name and self.comodel._fields[self.inverse_name]

    def get_description(self):
        desc = super(One2many, self).get_description()
        desc['relation_field'] = self.inverse_name
        return desc

    @classmethod
    def _from_column(cls, column):
        kwargs = dict((attr, getattr(column, attr)) for attr in cls._attrs)
        # beware when getting parameters: column may be a function field
        kwargs['comodel_name'] = column._obj
        kwargs['inverse_name'] = getattr(column, '_fields_id', None)
        return cls(**kwargs)

    def _to_column(self):
        kwargs = super(One2many, self)._to_column()
        kwargs['obj'] = self.comodel_name
        kwargs['fields_id'] = self.inverse_name
        kwargs['domain'] = self.domain or []
        return kwargs


class Many2many(_RelationalMulti):
    """ Many2many field. """
    type = 'many2many'
    relation = None                     # name of table
    column1 = None                      # column of table referring to model
    column2 = None                      # column of table referring to comodel

    def __init__(self, comodel_name, relation=None, column1=None, column2=None,
                string=None, **kwargs):
        super(Many2many, self).__init__(comodel_name=comodel_name, relation=relation,
            column1=column1, column2=column2, string=string, **kwargs)

    @lazy_property
    def inverse_field(self):
        if not self.compute:
            expected = (self.relation, self.column2, self.column1)
            for field in self.comodel._fields.itervalues():
                if isinstance(field, Many2many) and \
                        (field.relation, field.column1, field.column2) == expected:
                    return field
        return None

    @classmethod
    def _from_column(cls, column):
        kwargs = dict((attr, getattr(column, attr)) for attr in cls._attrs)
        # beware when getting parameters: column may be a function field
        kwargs['comodel_name'] = column._obj
        kwargs['relation'] = getattr(column, '_rel', None)
        kwargs['column1'] = getattr(column, '_id1', None)
        kwargs['column2'] = getattr(column, '_id2', None)
        return cls(**kwargs)

    def _to_column(self):
        kwargs = super(Many2many, self)._to_column()
        kwargs['obj'] = self.comodel_name
        kwargs['rel'] = self.relation
        kwargs['id1'] = self.column1
        kwargs['id2'] = self.column2
        kwargs['domain'] = self.domain or []
        return kwargs


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
        rec = self.model
        for name in self.related[:-1]:
            rec = rec[name]
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

    def __get__(self, instance, owner):
        if instance is None:
            return self
        # traverse the caches, and delegate to the last record
        for name in self.related[:-1]:
            instance = instance[name]
        return instance[self.related[-1]]

    def __set__(self, instance, value):
        # traverse the caches, and delegate to the last record
        for name in self.related[:-1]:
            instance = instance[name]
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

    def _add_trigger_for(self, field, path0, path1):
        # special case: expand the path
        field._depends_on_model(self.model, path0, list(self.related) + path1)


class Id(Field):
    """ Special case for field 'id'. """
    interface = True            # that field is always created by the ORM
    store = False
    readonly = True

    @classmethod
    def _from_column(cls, column):
        raise NotImplementedError()

    def __get__(self, instance, owner):
        if instance is None:
            return self         # the field is accessed through the class owner
        return (instance._ids or (False,))[0]

    def __set__(self, instance, value):
        raise NotImplementedError()


# imported here to avoid dependency cycle issues
from openerp.osv import fields
from openerp.osv.orm import BaseModel
from openerp.osv.scope import proxy as scope
