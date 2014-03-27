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

""" This module provides the elements for managing an execution environment (or
    "scope") for model instances.
"""

from collections import defaultdict, MutableMapping
from contextlib import contextmanager
from pprint import pformat
from weakref import WeakSet
from werkzeug.local import Local, release_local


class Scope(object):
    """ A scope wraps environment data for the ORM instances:

         - :attr:`cr`, the current database cursor;
         - :attr:`uid`, the current user id;
         - :attr:`context`, the current context dictionary;
         - :attr:`args`, a tuple containing the three values above.
    """
    _local = Local()

    @classmethod
    @contextmanager
    def manage(cls):
        """ Context manager for a set of scopes. """
        try:
            assert not hasattr(cls._local, 'scopes')
            cls._local.scopes = WeakSet()
            yield
        finally:
            release_local(cls._local)

    def __new__(cls, cr, uid, context):
        assert context is not None
        args = (cr, uid, context)

        # if scope already exists, return it
        scope, scopes = None, cls._local.scopes
        for scope in scopes:
            if scope.args == args:
                return scope

        # otherwise create scope, and add it in the set
        self = object.__new__(cls)
        self.cr, self.uid, self.context = self.args = args
        self.registry = RegistryManager.get(cr.dbname)
        self.cache = defaultdict(dict)     # cache[field] = {id: value}
        self.cache_ids = defaultdict(set)  # cache_ids[model_name] = set(ids)
        self.dirty = set()                 # set of dirty records
        self.shared = scope.shared if scope else Shared()
        self.all = scopes
        scopes.add(self)
        return self

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
        cr = self.cr if cr is None else cr
        uid = self.uid if user is None else int(user)
        context = self.context if context == () else context
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
        return self.sudo()['res.users'].browse(self.uid)

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
        # invalidate spec in self
        for field, ids in spec:
            if ids is None:
                self.cache.pop(field, None)
            else:
                field_cache = self.cache[field]
                for id in ids:
                    field_cache.pop(id, None)

        # invalidate everything in the other scopes
        self.invalidate_all(self)

    def invalidate_all(self, other=None):
        """ Invalidate the cache of all scopes, except `other`. """
        for scope in list(self.all):
            if scope is not other:
                scope.cache.clear()
                scope.cache_ids.clear()
                scope.dirty.clear()

    def check_cache(self):
        """ Check the cache consistency. """
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
from openerp.modules.registry import RegistryManager
