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

""" This module provides execution environments for ORM records. """

from collections import defaultdict, MutableMapping
from contextlib import contextmanager
from pprint import pformat
from weakref import WeakSet
from werkzeug.local import Local, release_local

from openerp.tools import frozendict


class Environment(object):
    """ An environment wraps data for ORM records:

         - :attr:`cr`, the current database cursor;
         - :attr:`uid`, the current user id;
         - :attr:`context`, the current context dictionary.

        It also provides access to the registry, a cache for records, and a data
        structure to manage recomputations.
    """
    _local = Local()

    @classmethod
    @contextmanager
    def manage(cls):
        """ Context manager for a set of environments. """
        if hasattr(cls._local, 'environments'):
            yield
        else:
            try:
                cls._local.environments = WeakSet()
                yield
            finally:
                release_local(cls._local)

    def __new__(cls, cr, uid, context):
        assert context is not None
        args = (cr, uid, context)

        # if env already exists, return it
        env, envs = None, cls._local.environments
        for env in envs:
            if env.args == args:
                return env

        # otherwise create environment, and add it in the set
        self = object.__new__(cls)
        self.cr, self.uid, self.context = self.args = (cr, uid, frozendict(context))
        self.registry = RegistryManager.get(cr.dbname)
        self.cache = defaultdict(dict)      # {field: {id: value, ...}, ...}
        self.prefetch = defaultdict(set)    # {model_name: set(id), ...}
        self.computed = defaultdict(set)    # {field: set(id), ...}
        self.dirty = set()                  # set(record)
        self.todo = {}                      # {field: records, ...}
        self.draft = env.draft if env else Draft()
        self.all = envs
        envs.add(self)
        return self

    def __getitem__(self, model_name):
        """ return a given model """
        return self.registry[model_name]._browse(self, ())

    def __call__(self, cr=None, user=None, context=None):
        """ Return an environment based on `self` with modified parameters.

            :param cr: optional database cursor to change the current cursor
            :param user: optional user/user id to change the current user
            :param context: optional context dictionary to change the current context
        """
        cr = self.cr if cr is None else cr
        uid = self.uid if user is None else int(user)
        context = self.context if context is None else context
        return Environment(cr, uid, context)

    def ref(self, xml_id, raise_if_not_found=True):
        """ return the record corresponding to the given `xml_id` """
        return self['ir.model.data'].xmlid_to_object(xml_id, raise_if_not_found=raise_if_not_found)

    @property
    def user(self):
        """ return the current user (as an instance) """
        return self(user=SUPERUSER_ID)['res.users'].browse(self.uid)

    @property
    def lang(self):
        """ return the current language code """
        return self.context.get('lang')

    @contextmanager
    def do_in_draft(self):
        """ Context-switch to draft mode. """
        if self.draft:
            yield
        else:
            try:
                self.draft.set(True)
                yield
            finally:
                self.draft.set(False)
                self.dirty.clear()

    def invalidate(self, spec):
        """ Invalidate some fields for some records in the cache of all
            environments.

            :param spec: what to invalidate, a list of `(field, ids)` pair,
                where `field` is a field object, and `ids` is a list of record
                ids or ``None`` (to invalidate all records).
        """
        if not spec:
            return
        for env in list(self.all):
            for field, ids in spec:
                if ids is None:
                    env.cache.pop(field, None)
                else:
                    field_cache = env.cache[field]
                    for id in ids:
                        field_cache.pop(id, None)

    def invalidate_all(self):
        """ Clear the cache of all environments. """
        for env in list(self.all):
            env.cache.clear()
            env.prefetch.clear()
            env.computed.clear()
            env.dirty.clear()

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
                    cached = field_dump[record.id]
                    fetched = record[field.name]
                    if fetched != cached:
                        info = {'cached': cached, 'fetched': fetched}
                        invalids.append((field, record, info))
                except (AccessError, MissingError):
                    pass

        if invalids:
            raise Warning('Invalid cache for fields\n' + pformat(invalids))


class Draft(object):
    """ A boolean flag shared among environments. """
    _state = False

    def __nonzero__(self):
        return self._state

    def set(self, value):
        self._state = bool(value)


# keep those imports here in order to handle cyclic dependencies correctly
from openerp import SUPERUSER_ID
from openerp.exceptions import Warning, AccessError, MissingError
from openerp.modules.registry import RegistryManager
