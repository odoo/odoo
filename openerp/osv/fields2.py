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

from datetime import date, datetime


class Field(object):
    """ Base class of all fields. """
    name = None                 # name of the field
    model = None                # name of the model of this field
    store = True                # whether the field is stored in database

    compute = None              # name of model method that computes value
    depends = ()                # collection of field dependencies

    string = None               # field label
    help = None                 # field tooltip
    readonly = False
    required = False

    def __init__(self, **kwargs):
        for attr in kwargs:
            setattr(self, attr, kwargs[attr])

    def set_model_name(self, model, name):
        """ assign the model and field names of `self` """
        self.model = model
        self.name = name
        if not self.string:
            self.string = name.replace('_', ' ').capitalize()

    def make_column(self):
        """ return a low-level field object corresponding to `self` """
        raise NotImplementedError()

    def __get__(self, instance, owner):
        """ read the value of field `self` for the record `instance` """
        if instance is None:
            return self         # the field is accessed through the class owner
        assert instance.is_record_or_null() and instance._name == self.model
        return instance._get_field(self.name)

    def __set__(self, instance, value):
        """ set the value of field `self` for the record `instance` """
        assert instance.is_record() and instance._name == self.model
        value = self.record_to_cache(value)
        if self.store:
            instance.write({self.name: value})
        # store into cache here, since method write() invalidates the cache!
        scope.cache[self.model][self.name][instance._id] = value

    def cache_to_record(self, value):
        """ convert `value` from the cache level to the record level """
        return value

    def record_to_cache(self, value):
        """ convert `value` from the record level to the cache level """
        return value

    def null(self):
        """ return the null value for this field at the record level """
        return False

    def format_read(self, value):
        """ convert the record-level value as returned by method
            :meth:`openerp.osv.orm.BaseModel.read`
        """
        return value


class Integer(Field):
    """ Integer field. """

    def __init__(self, **kwargs):
        super(Integer, self).__init__(**kwargs)

    def make_column(self):
        attrs = ('string', 'help', 'readonly', 'required')
        kwargs = dict((attr, getattr(self, attr)) for attr in attrs)
        return fields.integer(**kwargs)

    def record_to_cache(self, value):
        return int(value or 0)


# imported here to avoid dependency cycle issues
from openerp.osv import fields
from openerp.osv.scope import proxy as scope
