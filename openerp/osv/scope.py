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

from collections import defaultdict, MutableMapping
from contextlib import contextmanager
from pprint import pformat
from werkzeug.local import Local, release_local


class ScopeProxy(object):
    """ This a proxy object to the current scope. """
    def __init__(self):
        self._local = Local()

    def release(self):
        """ release the werkzeug local variable """
        release_local(self._local)

    @property
    def stack(self):
        """ return the stack of scopes (as a list) """
        try:
            return self._local.stack
        except AttributeError:
            self._local.stack = stack = []
            return stack

    @property
    def root(self):
        stack = self.stack
        return stack[0] if stack else None

    @property
    def current(self):
        stack = self.stack
        return stack[-1] if stack else None

    def __getitem__(self, name):
        return self.current[name]

    def __getattr__(self, name):
        return getattr(self.current, name)

    def __call__(self, *args, **kwargs):
        # apply current scope or instantiate one
        return (self.current or Scope)(*args, **kwargs)

    @property
    def all_scopes(self):
        """ return the list of known scopes """
        try:
            return self._local.scopes
        except AttributeError:
            self._local.scopes = scopes = []
            return scopes

    def invalidate(self, spec):
        """ Invalidate some fields for some records in the caches.

            :param spec: what to invalidate, a list of `(field, ids)` pair,
                where `field` is a field object, and `ids` is a list of record
                ids or ``None`` (to invalidate all records).
        """
        for scope in self.all_scopes:
            scope.invalidate(spec)

    def invalidate_all(self):
        """ Invalidate the record caches in all scopes. """
        for scope in self.all_scopes:
            scope.invalidate_all()

    def check_cache(self):
        """ Check the record caches in all scopes. """
        for scope in self.all_scopes:
            scope.check_cache()

    @property
    def shared(self):
        """ Return the shared object. """
        try:
            return self._local.shared
        except AttributeError:
            self._local.shared = shared = Shared()
            return shared

proxy = ScopeProxy()


class Scope(object):
    """ A scope wraps environment data for the ORM instances:

         - :attr:`cr`, the current database cursor;
         - :attr:`uid`, the current user id;
         - :attr:`context`, the current context dictionary;
         - :attr:`args`, a tuple containing the three values above.

        An execution environment is created by a statement ``with``::

            with Scope(cr, uid, context):
                # statements execute in given scope

                # retrieve environment data
                cr, uid, context = scope.args

        The scope provides extra attributes:

         - :attr:`registry`, the model registry of the current database,
         - :attr:`cache`, the records cache for this scope,

        The records cache is a set of nested dictionaries, indexed by model
        name, record id, and field name (in that order).
    """
    def __new__(cls, cr, uid, context):
        if context is None:
            context = {}
        args = (cr, uid, context)

        # if scope already exists, return it
        scope_list = proxy.all_scopes
        for scope in scope_list:
            if scope.args == args:
                return scope

        # otherwise create scope, and add it in the list
        scope = object.__new__(cls)
        scope.cr, scope.uid, scope.context = scope.args = args
        scope.registry = RegistryManager.get(cr.dbname)
        scope.cache = defaultdict(dict)     # cache[field] = {id: value}
        scope.cache_ids = defaultdict(set)  # cache_ids[model_name] = set(ids)
        scope.dirty = set()                 # set of dirty records
        scope.shared = proxy.shared         # shared state object
        scope_list.append(scope)
        return scope

    def __eq__(self, other):
        if isinstance(other, Scope):
            other = other.args
        return self.args == tuple(other)

    def __ne__(self, other):
        return not self == other

    def __enter__(self):
        proxy.stack.append(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        stack = proxy.stack
        stack.pop()
        if not stack:
            proxy.release()

    def __getitem__(self, model_name):
        """ return a given model """
        return self.registry[model_name]._browse(self, ())

    def __call__(self, cr=None, user=None, context=(), **kwargs):
        """ Return a scope based on `self` with modified parameters.

            :param cr: optional database cursor to change the current cursor
            :param user: optional user/user id to change the current user
            :param context: optional context dictionary to change the current context
            :param kwargs: a set of key-value pairs to update the context
        """
        # determine cr, uid, context
        if cr is None:
            cr = self.cr

        if user is None:
            uid = self.uid
        elif isinstance(user, BaseModel):
            assert user._name == 'res.users'
            uid = user.id
        else:
            uid = user

        if context == ():
            context = self.context
        context = dict(context or {}, **kwargs)

        return Scope(cr, uid, context)

    def sudo(self):
        """ Return a scope based on `self`, with the superuser. """
        return self(user=SUPERUSER_ID)

    def ref(self, xml_id):
        """ return the record corresponding to the given `xml_id` """
        module, name = xml_id.split('.')
        return self['ir.model.data'].get_object(module, name)

    @property
    def user(self):
        """ return the current user (as an instance) """
        with proxy.sudo():
            return self['res.users'].browse(self.uid)

    @property
    def lang(self):
        """ return the current language code """
        return self.context.get('lang')

    @property
    def draft(self):
        """ Return whether we are in draft mode. """
        return self.shared.draft

    @contextmanager
    def in_draft(self):
        """ Context-switch to draft mode. """
        if self.shared.draft:
            yield
        else:
            try:
                self.shared.draft = True
                yield
            finally:
                self.shared.draft = False
                self.dirty.clear()

    @property
    def recomputation(self):
        """ Return the recomputation object. """
        return Recomputation(self)

    @contextmanager
    def in_recomputation(self):
        """ Context-switch to recomputation mode. """
        if self.shared.recomputing:
            yield {}
        else:
            try:
                self.shared.recomputing = True
                yield self.recomputation
            finally:
                self.shared.recomputing = False

    def invalidate(self, spec):
        """ Invalidate some fields for some records in the cache of `self`.

            :param spec: what to invalidate, a list of `(field, ids)` pair,
                where `field` is a field object, and `ids` is a list of record
                ids or ``None`` (to invalidate all records).
        """
        for field, ids in spec:
            if ids is None:
                self.cache.pop(field, None)
            else:
                field_cache = self.cache[field]
                for id in ids:
                    field_cache.pop(id, None)

    def invalidate_all(self):
        """ Invalidate the cache. """
        self.cache.clear()
        self.cache_ids.clear()
        self.dirty.clear()

    def check_cache(self):
        """ Check the cache consistency. """
        with self:
            # make a full copy of the cache, and invalidate it
            cache_dump = dict(
                (field, dict(field_cache))
                for field, field_cache in self.cache.iteritems()
            )
            self.invalidate_all()

            # re-fetch the records, and compare with their former cache
            invalids = []
            for field, field_dump in cache_dump.iteritems():
                ids = filter(None, list(field_dump))
                records = self[field.model_name].browse(ids)
                for record in records:
                    try:
                        cached = field_dump[record._id]
                        fetched = record[field.name]
                        if fetched != cached:
                            info = {'cached': cached, 'fetched': fetched}
                            invalids.append((field, record, info))
                    except (AccessError, MissingError):
                        pass

            if invalids:
                raise Warning('Invalid cache for fields\n' + pformat(invalids))


class Shared(object):
    """ An object shared by all scopes in a thread/request. """

    def __init__(self):
        self.draft = False
        self.recomputing = False
        self.todo = {}


class Recomputation(MutableMapping):
    """ Proxy object mapping `field` to `records` to recompute. """

    def __init__(self, scope):
        self._scope = scope
        self._todo = scope.shared.todo

    def __getitem__(self, field):
        """ Return the records to recompute for `field` (may be empty). """
        return self._todo.get(field) or self._scope[field.model_name]

    def __setitem__(self, field, records):
        """ Set the records to recompute for `field`. It automatically discards
            the item if `records` is empty.
        """
        if records:
            self._todo[field] = records
        else:
            self._todo.pop(field, None)

    def __delitem__(self, field):
        """ Empty the records to recompute for `field`. """
        self._todo.pop(field, None)

    def __iter__(self):
        return iter(self._todo)

    def __len__(self):
        return len(self._todo)


# keep those imports here in order to handle cyclic dependencies correctly
from openerp import SUPERUSER_ID
from openerp.exceptions import Warning, AccessError, MissingError
from openerp.osv.orm import BaseModel
from openerp.modules.registry import RegistryManager
