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
    'Scope', 'proxy', 'Cache',
]

from collections import defaultdict
from contextlib import contextmanager
from pprint import pformat
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
        if self.current:
            return self.current(*args, **kwargs)
        else:
            return Scope(*args, **kwargs)

    def invalidate_cache(self, spec=None):
        """ Invalidate the record cache in all scopes.
            See :meth:`Cache.invalidate` for the parameter `spec`.
        """
        for scope in getattr(_local, 'scope_list', ()):
            scope.cache.invalidate(spec)

    def check_cache(self):
        """ Check the record caches in all scopes. """
        for scope in getattr(_local, 'scope_list', ()):
            with scope:
                scope.cache.check()

    @contextmanager
    def recomputing_manager(self, spec):
        """ Create a context manager for recomputing fields.
            See :meth:`Cache.invalidate` for the parameter `spec`.
        """
        # recomputing = {model_name: {field_name: set(ids), ...}, ...}
        recomputing = defaultdict(lambda: defaultdict(set))
        for m, fs, ids in spec:
            assert ids is not None
            for f in fs:
                recomputing[m][f].update(ids)

        try:
            old = getattr(_local, 'recomputing', None)
            _local.recomputing = recomputing
            yield
        finally:
            _local.recomputing = old

    def recomputing(self, model_name):
        """ Return a dictionary associating field names to record ids being
            recomputed for `model_name`.
        """
        recomputing = getattr(_local, 'recomputing', None)
        return recomputing[model_name] if recomputing else {}

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
         - :attr:`cache`, a records cache (see :class:`Cache`).
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
        obj.cache = Cache()
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
            elif isinstance(arg, BaseModel) and arg._name == 'res.users':
                uid = arg.id
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
        """ return the current user (as an instance) """
        with proxy.SUDO():
            return self.registry['res.users'].browse(self.uid)

    @property
    def lang(self):
        """ return the current language code """
        if not hasattr(self, '_lang'):
            self._lang = self.context.get('lang') or 'en_US'
        return self._lang


#
# Records cache
#
def get_values(d, keys):
    """ return the values of dictionary `d` corresponding to `keys`, or all
        values of `d` if `keys` is ``None``
    """
    if keys is None:
        return d.itervalues()
    else:
        return (d[key] for key in keys if key in d)

def drop_values(d, keys):
    """ discard the items of `d` corresponding to `keys`, or all items if `keys`
        is ``None``
    """
    if keys is None:
        d.clear()
    else:
        for key in keys:
            d.pop(key, None)


class ModelCache(defaultdict):
    """ Cache for the records of a given model in a given scope. """
    def __init__(self):
        super(ModelCache, self).__init__(dict)


class Cache(defaultdict):
    """ Cache for records in a given scope. The cache is a set of nested
        dictionaries indexed by model name, record id, and field name (in that
        order)::

            # access the value of a field of a given record
            value = cache[model_name][record_id][field_name]
    """
    def __init__(self):
        super(Cache, self).__init__(ModelCache)

    def invalidate(self, spec=None):
        """ Invalidate the cache.

            :param spec: describes what to invalidate;
                either ``None`` (invalidate everything), or
                a list of triples (`model`, `fields`, `ids`), where
                `model` is a model name,
                `fields` is a list of field names or ``None`` for all fields,
                and `ids` is a list of record ids or ``None`` for all records.
        """
        if spec is None:
            spec = [(model, None, None) for model in self]

        # The invalidation drops data from the records' own cache. However, it
        # never removes records from the cache itself, even if those records
        # have been deleted from the database. Removing records would cause a
        # subtle issue in the cache prefetching: the record instances that are
        # fetched are the ones in the cache, but not necessarily the ones that
        # the program uses to read the records. As a consequence, when using a
        # record out of the cache, its already-fetched data is lost, and the
        # record data has to be fetched again from the database!
        for model, fields, ids in spec:
            model_cache = self[model]
            for record_cache in get_values(model_cache, ids):
                drop_values(record_cache, fields)

    def check(self):
        """ self-check for validating the cache """
        assert proxy.cache is self

        # make a full copy of the cache, and invalidate it
        cache_copy = dict(
            (model_name, dict(
                (record_id, dict(record_cache))
                for record_id, record_cache in model_cache.iteritems()
            ))
            for model_name, model_cache in self.iteritems()
        )
        self.invalidate()

        # re-fetch the records, and compare with their former cache
        invalids = []
        for model_name, model_cache in cache_copy.iteritems():
            model = proxy.model(model_name)
            for record_id, record_cache in model_cache.iteritems():
                record = model.browse(record_id)
                for field, value in record_cache.iteritems():
                    if record[field] != value:
                        invalids.append((record, field, {'cached': value, 'fetched': record[field]}))

        if invalids:
            raise Exception('Invalid cache for records\n' + pformat(invalids))


# keep those imports here in order to handle cyclic dependencies correctly
from openerp import SUPERUSER_ID
from openerp.osv.orm import BaseModel
from openerp.sql_db import Cursor
from openerp.modules.registry import RegistryManager
