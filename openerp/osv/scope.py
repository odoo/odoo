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

""" This module provides the elements for managing execution environments or
    "scopes". Scopes are nestable and provides convenient access to shared
    objects. The object :obj:`proxy` is a proxy object to the current scope.
"""

__all__ = [
    'Scope', 'proxy', 'RecordCache',
]

from collections import defaultdict
from werkzeug.local import Local, release_local

# werkzeug "context" variable to store the stack of scopes
_local = Local()


class ScopeProxy(object):
    """ This a proxy object to the current scope. """
    @property
    def root(self):
        stack = getattr(_local, 'scope_stack', None)
        return stack[0] if stack else None

    @property
    def current(self):
        stack = getattr(_local, 'scope_stack', None)
        return stack[-1] if stack else None

    def push(self, value):
        stack = getattr(_local, 'scope_stack', None)
        if stack is None:
            _local.scope_stack = stack = []
        stack.append(value)

    def pop(self):
        res = _local.scope_stack.pop()
        if not _local.scope_stack:
            release_local(_local)
        return res

    def __getattr__(self, name):
        return getattr(self.current, name)

    def __iter__(self):
        return iter(self.current)

    def __call__(self, *args, **kwargs):
        return self.current(*args, **kwargs)

    def invalidate_cache(self, spec=None):
        """ Invalidate the record cache in all scopes.
            See :meth:`RecordCache.invalidate` for the parameter `spec`.
        """
        for s in getattr(_local, 'scope_list', ()):
            s.cache.invalidate(spec)

proxy = ScopeProxy()


class Scope(object):
    """ A scope wraps environment data for the ORM instances:

         - :attr:`cr`, the current database cursor;
         - :attr:`uid`, the current user id;
         - :attr:`context`, the current context dictionary.

        An execution environment is created by a statement ``with``::

            with Scope(cr, uid, context):
                # statements execute in given scope

                # iterating over a scope returns cr, uid, context
                cr, uid, context = scope

        The scope provides extra attributes:

         - :attr:`registry`, the model registry of the current database,
         - :attr:`cache`, a records cache (see :class:`RecordCache`).
    """
    def __new__(cls, cr, uid, context):
        args = (cr, int(uid), context if context is not None else {})
        # get the list of all scopes in the current context
        scope_list = getattr(_local, 'scope_list', None)
        if scope_list is None:
            _local.scope_list = scope_list = []
        # if scope already exists, return it
        for obj in scope_list:
            if obj == args:
                return obj
        # otherwise create scope, and add it in the list
        obj = object.__new__(cls)
        obj.cr, obj.uid, obj.context = args
        obj.registry = RegistryManager.get(cr.dbname)
        obj.cache = RecordCache()
        scope_list.append(obj)
        return obj

    def __iter__(self):
        yield self.cr
        yield self.uid
        yield self.context

    def __eq__(self, other):
        return isinstance(other, (Scope, tuple)) and tuple(self) == tuple(other)

    def __ne__(self, other):
        return not self == other

    def __enter__(self):
        proxy.push(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        proxy.pop()

    def __call__(self, *args, **kwargs):
        """ Return a scope based on `self` with modified parameters.

            :param args: contains a database cursor to change the current
                cursor, a user id or record to change the current user, a
                context dictionary to change the current context
            :param kwargs: a set of key-value pairs to update the context
        """
        cr, uid, context = self
        for arg in args:
            if isinstance(arg, dict):
                context = arg
            elif isinstance(arg, (int, long)):
                uid = arg
            elif isinstance(arg, Record) and arg._name == 'res.users':
                uid = int(arg)
            elif isinstance(arg, Cursor):
                cr = arg
            else:
                raise Exception("Unexpected argument: %r", arg)
        context = dict(context, **kwargs)
        return Scope(cr, uid, context)

    def SUDO(self):
        """ Return a scope based on `self`, with the superuser. """
        return self(SUPERUSER_ID)

    def model(self, model_name):
        """ return a given model """
        return self.registry[model_name]

    def ref(self, xml_id):
        """ return the record corresponding to the given `xml_id` """
        module, name = xml_id.split('.')
        return self.model('ir.model.data').get_object(module, name)

    @property
    def user(self):
        """ return the current user (as a record) """
        return self.model('res.users').record(self.uid, scope=proxy.SUDO())

    @property
    def lang(self):
        """ return the current language code """
        if not hasattr(self, '_lang'):
            self._lang = self.context.get('lang') or 'en_US'
        return self._lang


#
# Records cache
#
class ModelCache(defaultdict):
    """ Cache for records in a given model. The cache is a dictionary that
        associates `field` names to `id-value` dictionaries.

        It also  refers to a set of record ids (attribute :attr:`ids`), which is
        used for prefetching.
    """
    def __init__(self):
        super(ModelCache, self).__init__(dict)
        self.ids = set()

    def update(self, field, values):
        """ update the cache for the given field

            :param values: a dictionary associating record ids to values
        """
        self.ids.update(values.iterkeys())
        self[field].update(values)

    def invalidate(self, fields=None, ids=None):
        """ invalidate the given fields for the given ids

            :param fields: the list of fields to invalidate, ``None`` for all
            :param ids: the list of record ids to invalidate, ``None`` for all
        """
        if fields is None:
            if ids is None:
                self.ids.clear()
                self.clear()
            else:
                self.ids.difference_update(ids)
                for field_cache in self.itervalues():
                    for id in ids:
                        field_cache.pop(id, None)
        else:
            if ids is None:
                for field in fields:
                    self.pop(field, None)
            else:
                for field in fields:
                    field_cache = self[field]
                    for id in ids:
                        field_cache.pop(id, None)


class RecordCache(defaultdict):
    """ Cache for records of any model. The cache is organized as a set of
        nested dictionaries, where the keys are: the model name, the field name,
        and the record id, respectively. The cache of a model is updated field
        by field, and provides a set of record ids that is for prefetching::

            # access the value of a field of a record in a model
            value = cache[model_name][field_name][record_id]

            # update the values of a field for multiple records
            cache[model_name].update(field_name, {record_id: value, ...})

            # access/modify the set of record ids used for prefetching
            cache[model_name].ids
    """
    def __init__(self):
        super(RecordCache, self).__init__(ModelCache)

    def invalidate(self, spec=None):
        """ Invalidate the record cache.

            :param spec: describes what to invalidate;
                either ``None`` (invalidate everything), or
                a list of triples (`model`, `fields`, `ids`), where
                `model` is a model name,
                `fields` is a list of field names or ``None`` for all fields,
                and `ids` is a list of record ids or ``None`` for all records.
        """
        if spec is None:
            for model_cache in self.itervalues():
                model_cache.invalidate()
        else:
            for model, fields, ids in spec:
                self[model].invalidate(fields, ids)

    def check(self):
        """ self-check for validating the cache """
        cr, uid, context = proxy
        invalids = []

        for model_name, model_cache in self.items():
            # read the fields that are present in the cache
            model = proxy.model(model_name)
            ids = list(model_cache.ids)
            field_names = model_cache.keys()
            result = model.read(cr, uid, ids, field_names, context=context, load="_classic_write")

            # compare the result with the content of the cache
            for field in field_names:
                field_cache = model_cache[field]
                clean = lambda v: v
                if model._all_columns[field].column._type == 'many2one':
                    clean = lambda v: v[0] if isinstance(v, (tuple, list)) else v
                for data in result:
                    id = data['id']
                    if id in field_cache and field_cache[id] != clean(data[field]):
                        invalids.append((model_name, field))
                        break

        if invalids:
            raise Exception('Invalid cache for %s' % invalids)


# keep those imports here in order to handle cyclic dependencies correctly
from openerp import SUPERUSER_ID
from openerp.osv.orm import Record
from openerp.sql_db import Cursor
from openerp.modules.registry import RegistryManager
