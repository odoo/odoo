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

""" This module provides the elements for managing two different API styles,
    namely the "traditional" and "record" styles.

    In the "traditional" style, parameters like the database cursor, user id,
    context dictionary and record ids (usually denoted as ``cr``, ``uid``,
    ``context``, ``ids``) are passed explicitly to all methods. In the "record"
    style, those parameters are hidden into model instances, which gives it a
    more object-oriented feel.

    For instance, the statements::

        model = self.pool.get(MODEL)
        ids = model.search(cr, uid, DOMAIN, context=context)
        for rec in model.browse(cr, uid, ids, context=context):
            print rec.name
        model.write(cr, uid, ids, VALUES, context=context)

    may also be written as::

        env = Env(cr, uid, context)         # cr, uid, context wrapped in env
        recs = env[MODEL]                   # retrieve an instance of MODEL
        recs = recs.search(DOMAIN)          # search returns a recordset
        for rec in recs:                    # iterate over the records
            print rec.name
        recs.write(VALUES)                  # update all records in recs

    Methods written in the "traditional" style are automatically decorated,
    following some heuristics based on parameter names.
"""

__all__ = [
    'Environment',
    'Meta', 'guess', 'noguess',
    'model', 'multi', 'one',
    'cr', 'cr_context', 'cr_uid', 'cr_uid_context',
    'cr_uid_id', 'cr_uid_id_context', 'cr_uid_ids', 'cr_uid_ids_context',
    'constrains', 'depends', 'onchange', 'returns',
]

import logging

from inspect import currentframe, getargspec
from collections import defaultdict, MutableMapping
from contextlib import contextmanager
from pprint import pformat
from weakref import WeakSet
from werkzeug.local import Local, release_local

from openerp.tools import frozendict

_logger = logging.getLogger(__name__)

# The following attributes are used, and reflected on wrapping methods:
#  - method._api: decorator function, used for re-applying decorator
#  - method._constrains: set by @constrains, specifies constraint dependencies
#  - method._depends: set by @depends, specifies compute dependencies
#  - method._returns: set by @returns, specifies return model
#  - method._onchange: set by @onchange, specifies onchange fields
#  - method.clear_cache: set by @ormcache, used to clear the cache
#
# On wrapping method only:
#  - method._orig: original method
#

WRAPPED_ATTRS = ('__module__', '__name__', '__doc__', '_api', '_constrains',
                 '_depends', '_onchange', '_returns', 'clear_cache')

INHERITED_ATTRS = ('_returns',)


class Meta(type):
    """ Metaclass that automatically decorates traditional-style methods by
        guessing their API. It also implements the inheritance of the
        :func:`returns` decorators.
    """

    def __new__(meta, name, bases, attrs):
        # dummy parent class to catch overridden methods decorated with 'returns'
        parent = type.__new__(meta, name, bases, {})

        for key, value in attrs.items():
            if not key.startswith('__') and callable(value):
                # make the method inherit from decorators
                value = propagate(getattr(parent, key, None), value)

                # guess calling convention if none is given
                if not hasattr(value, '_api'):
                    try:
                        value = guess(value)
                    except TypeError:
                        pass

                attrs[key] = value

        return type.__new__(meta, name, bases, attrs)


identity = lambda x: x

def decorate(method, attr, value):
    """ Decorate `method` or its original method. """
    # decorate the original method, and re-apply the api decorator, if any
    orig = getattr(method, '_orig', method)
    setattr(orig, attr, value)
    return getattr(method, '_api', identity)(orig)

def propagate(from_method, to_method):
    """ Propagate decorators from `from_method` to `to_method`, and return the
        resulting method.
    """
    if from_method:
        for attr in INHERITED_ATTRS:
            if hasattr(from_method, attr) and not hasattr(to_method, attr):
                to_method = decorate(to_method, attr, getattr(from_method, attr))
    return to_method


def constrains(*args):
    """ Return a decorator that specifies the field dependencies of a method
        implementing a constraint checker. Each argument must be a field name.
    """
    return lambda method: decorate(method, '_constrains', args)


def onchange(*args):
    """ Return a decorator to decorate an onchange method for given fields.
        Each argument must be a field name.
    """
    return lambda method: decorate(method, '_onchange', args)


def depends(*args):
    """ Return a decorator that specifies the field dependencies of a "compute"
        method (for new-style function fields). Each argument must be a string
        that consists in a dot-separated sequence of field names.

        One may also pass a single function as argument. In that case, the
        dependencies are given by calling the function with the field's model.
    """
    if args and callable(args[0]):
        args = args[0]
    return lambda method: decorate(method, '_depends', args)


def returns(model, downgrade=None):
    """ Return a decorator for methods that return instances of `model`.

        :param model: a model name, or ``'self'`` for the current model

        :param downgrade: a function `downgrade(value)` to convert the
            record-style `value` to a traditional-style output

        The decorator adapts the method output to the api style: `id`, `ids` or
        ``False`` for the traditional style, and recordset for the record style::

            @model
            @returns('res.partner')
            def find_partner(self, arg):
                ...     # return some record

            # output depends on call style: traditional vs record style
            partner_id = model.find_partner(cr, uid, arg, context=context)

            # recs = model.browse(cr, uid, ids, context)
            partner_record = recs.find_partner(arg)

        Note that the decorated method must satisfy that convention.

        Those decorators are automatically *inherited*: a method that overrides
        a decorated existing method will be decorated with the same
        ``@returns(model)``.
    """
    return lambda method: decorate(method, '_returns', (model, downgrade))


def make_wrapper(method, old_api, new_api):
    """ Return a wrapper method for `method`. """
    def wrapper(self, *args, **kwargs):
        # avoid hasattr(self, '_ids') because __getattr__() is overridden
        if '_ids' in self.__dict__:
            return new_api(self, *args, **kwargs)
        else:
            return old_api(self, *args, **kwargs)

    # propagate specific openerp attributes from method to wrapper
    for attr in WRAPPED_ATTRS:
        if hasattr(method, attr):
            setattr(wrapper, attr, getattr(method, attr))
    wrapper._orig = method

    return wrapper


def get_downgrade(method):
    """ Return a function `downgrade(value)` that adapts `value` from
        record-style to traditional-style, following the convention of `method`.
    """
    spec = getattr(method, '_returns', None)
    if spec:
        model, downgrade = spec
        return downgrade or (lambda value: value.ids)
    else:
        return lambda value: value


def get_upgrade(method):
    """ Return a function `upgrade(self, value)` that adapts `value` from
        traditional-style to record-style, following the convention of `method`.
    """
    spec = getattr(method, '_returns', None)
    if spec:
        model, downgrade = spec
        if model == 'self':
            return lambda self, value: self.browse(value)
        else:
            return lambda self, value: self.env[model].browse(value)
    else:
        return lambda self, value: value


def get_aggregate(method):
    """ Return a function `aggregate(self, value)` that aggregates record-style
        `value` for a method decorated with ``@one``.
    """
    spec = getattr(method, '_returns', None)
    if spec:
        # value is a list of instances, concatenate them
        model, downgrade = spec
        if model == 'self':
            return lambda self, value: sum(value, self.browse())
        else:
            return lambda self, value: sum(value, self.env[model].browse())
    else:
        return lambda self, value: value


def get_context_split(method):
    """ Return a function `split` that extracts the context from a pair of
        positional and keyword arguments::

            context, args, kwargs = split(args, kwargs)
    """
    pos = len(getargspec(method).args) - 1

    def split(args, kwargs):
        if pos < len(args):
            return args[pos], args[:pos], kwargs
        else:
            return kwargs.pop('context', None), args, kwargs

    return split


def model(method):
    """ Decorate a record-style method where `self` is a recordset. Such a
        method::

            @api.model
            def method(self, args):
                ...

        may be called in both record and traditional styles, like::

            # recs = model.browse(cr, uid, ids, context)
            recs.method(args)

            model.method(cr, uid, args, context=context)
    """
    method._api = model
    split = get_context_split(method)
    downgrade = get_downgrade(method)

    def old_api(self, cr, uid, *args, **kwargs):
        context, args, kwargs = split(args, kwargs)
        recs = self.browse(cr, uid, [], context)
        result = method(recs, *args, **kwargs)
        return downgrade(result)

    return make_wrapper(method, old_api, method)


def multi(method):
    """ Decorate a record-style method where `self` is a recordset. Such a
        method::

            @api.multi
            def method(self, args):
                ...

        may be called in both record and traditional styles, like::

            # recs = model.browse(cr, uid, ids, context)
            recs.method(args)

            model.method(cr, uid, ids, args, context=context)
    """
    method._api = multi
    split = get_context_split(method)
    downgrade = get_downgrade(method)

    def old_api(self, cr, uid, ids, *args, **kwargs):
        context, args, kwargs = split(args, kwargs)
        recs = self.browse(cr, uid, ids, context)
        result = method(recs, *args, **kwargs)
        return downgrade(result)

    return make_wrapper(method, old_api, method)


def one(method):
    """ Decorate a record-style method where `self` is expected to be a
        singleton instance. The decorated method automatically loops on records,
        and makes a list with the results. In case the method is decorated with
        @returns, it concatenates the resulting instances. Such a method::

            @api.one
            def method(self, args):
                return self.name

        may be called in both record and traditional styles, like::

            # recs = model.browse(cr, uid, ids, context)
            names = recs.method(args)

            names = model.method(cr, uid, ids, args, context=context)
    """
    method._api = one
    split = get_context_split(method)
    downgrade = get_downgrade(method)
    aggregate = get_aggregate(method)

    def old_api(self, cr, uid, ids, *args, **kwargs):
        context, args, kwargs = split(args, kwargs)
        recs = self.browse(cr, uid, ids, context)
        result = new_api(recs, *args, **kwargs)
        return downgrade(result)

    def new_api(self, *args, **kwargs):
        result = [method(rec, *args, **kwargs) for rec in self]
        return aggregate(self, result)

    return make_wrapper(method, old_api, new_api)


def cr(method):
    """ Decorate a traditional-style method that takes `cr` as a parameter.
        Such a method may be called in both record and traditional styles, like::

            # recs = model.browse(cr, uid, ids, context)
            recs.method(args)

            model.method(cr, args)
    """
    method._api = cr
    upgrade = get_upgrade(method)

    def new_api(self, *args, **kwargs):
        cr, uid, context = self.env.args
        result = method(self._model, cr, *args, **kwargs)
        return upgrade(self, result)

    return make_wrapper(method, method, new_api)


def cr_context(method):
    """ Decorate a traditional-style method that takes `cr`, `context` as parameters. """
    method._api = cr_context
    upgrade = get_upgrade(method)

    def new_api(self, *args, **kwargs):
        cr, uid, context = self.env.args
        kwargs['context'] = context
        result = method(self._model, cr, *args, **kwargs)
        return upgrade(self, result)

    return make_wrapper(method, method, new_api)


def cr_uid(method):
    """ Decorate a traditional-style method that takes `cr`, `uid` as parameters. """
    method._api = cr_uid
    upgrade = get_upgrade(method)

    def new_api(self, *args, **kwargs):
        cr, uid, context = self.env.args
        result = method(self._model, cr, uid, *args, **kwargs)
        return upgrade(self, result)

    return make_wrapper(method, method, new_api)


def cr_uid_context(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `context` as
        parameters. Such a method may be called in both record and traditional
        styles, like::

            # recs = model.browse(cr, uid, ids, context)
            recs.method(args)

            model.method(cr, uid, args, context=context)
    """
    method._api = cr_uid_context
    upgrade = get_upgrade(method)

    def new_api(self, *args, **kwargs):
        cr, uid, context = self.env.args
        kwargs['context'] = context
        result = method(self._model, cr, uid, *args, **kwargs)
        return upgrade(self, result)

    return make_wrapper(method, method, new_api)


def cr_uid_id(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `id` as
        parameters. Such a method may be called in both record and traditional
        styles. In the record style, the method automatically loops on records.
    """
    method._api = cr_uid_id
    upgrade = get_upgrade(method)

    def new_api(self, *args, **kwargs):
        cr, uid, context = self.env.args
        result = [method(self._model, cr, uid, id, *args, **kwargs) for id in self.ids]
        return upgrade(self, result)

    return make_wrapper(method, method, new_api)


def cr_uid_id_context(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `id`,
        `context` as parameters. Such a method::

            @api.cr_uid_id
            def method(self, cr, uid, id, args, context=None):
                ...

        may be called in both record and traditional styles, like::

            # rec = model.browse(cr, uid, id, context)
            rec.method(args)

            model.method(cr, uid, id, args, context=context)
    """
    method._api = cr_uid_id_context
    upgrade = get_upgrade(method)

    def new_api(self, *args, **kwargs):
        cr, uid, context = self.env.args
        kwargs['context'] = context
        result = [method(self._model, cr, uid, id, *args, **kwargs) for id in self.ids]
        return upgrade(self, result)

    return make_wrapper(method, method, new_api)


def cr_uid_ids(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `ids` as
        parameters. Such a method may be called in both record and traditional
        styles.
    """
    method._api = cr_uid_ids
    upgrade = get_upgrade(method)

    def new_api(self, *args, **kwargs):
        cr, uid, context = self.env.args
        result = method(self._model, cr, uid, self.ids, *args, **kwargs)
        return upgrade(self, result)

    return make_wrapper(method, method, new_api)


def cr_uid_ids_context(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `ids`,
        `context` as parameters. Such a method::

            @api.cr_uid_ids_context
            def method(self, cr, uid, ids, args, context=None):
                ...

        may be called in both record and traditional styles, like::

            # recs = model.browse(cr, uid, ids, context)
            recs.method(args)

            model.method(cr, uid, ids, args, context=context)

        It is generally not necessary, see :func:`guess`.
    """
    method._api = cr_uid_ids_context
    upgrade = get_upgrade(method)

    def new_api(self, *args, **kwargs):
        cr, uid, context = self.env.args
        kwargs['context'] = context
        result = method(self._model, cr, uid, self.ids, *args, **kwargs)
        return upgrade(self, result)

    return make_wrapper(method, method, new_api)


def v7(method_v7):
    """ Decorate a method that supports the old-style api only. A new-style api
        may be provided by redefining a method with the same name and decorated
        with :func:`~.v8`::

            @api.v7
            def foo(self, cr, uid, ids, context=None):
                ...

            @api.v8
            def foo(self):
                ...

        Note that the wrapper method uses the docstring of the first method.
    """
    # retrieve method_v8 from the caller's frame
    frame = currentframe().f_back
    method = frame.f_locals.get(method_v7.__name__)
    method_v8 = getattr(method, '_v8', method)

    wrapper = make_wrapper(method_v7, method_v7, method_v8)
    wrapper._v7 = method_v7
    wrapper._v8 = method_v8
    return wrapper


def v8(method_v8):
    """ Decorate a method that supports the new-style api only. An old-style api
        may be provided by redefining a method with the same name and decorated
        with :func:`~.v7`::

            @api.v8
            def foo(self):
                ...

            @api.v7
            def foo(self, cr, uid, ids, context=None):
                ...

        Note that the wrapper method uses the docstring of the first method.
    """
    # retrieve method_v7 from the caller's frame
    frame = currentframe().f_back
    method = frame.f_locals.get(method_v8.__name__)
    method_v7 = getattr(method, '_v7', method)

    wrapper = make_wrapper(method_v8, method_v7, method_v8)
    wrapper._v7 = method_v7
    wrapper._v8 = method_v8
    return wrapper


def noguess(method):
    """ Decorate a method to prevent any effect from :func:`guess`. """
    method._api = False
    return method


def guess(method):
    """ Decorate `method` to make it callable in both traditional and record
        styles. This decorator is applied automatically by the model's
        metaclass, and has no effect on already-decorated methods.

        The API style is determined by heuristics on the parameter names: ``cr``
        or ``cursor`` for the cursor, ``uid`` or ``user`` for the user id,
        ``id`` or ``ids`` for a list of record ids, and ``context`` for the
        context dictionary. If a traditional API is recognized, one of the
        decorators :func:`cr`, :func:`cr_context`, :func:`cr_uid`,
        :func:`cr_uid_context`, :func:`cr_uid_id`, :func:`cr_uid_id_context`,
        :func:`cr_uid_ids`, :func:`cr_uid_ids_context` is applied on the method.

        Method calls are considered traditional style when their first parameter
        is a database cursor.
    """
    if hasattr(method, '_api'):
        return method

    # introspection on argument names to determine api style
    args, vname, kwname, defaults = getargspec(method)
    names = tuple(args) + (None,) * 4

    if names[0] == 'self':
        if names[1] in ('cr', 'cursor'):
            if names[2] in ('uid', 'user'):
                if names[3] == 'ids':
                    if 'context' in names or kwname:
                        return cr_uid_ids_context(method)
                    else:
                        return cr_uid_ids(method)
                elif names[3] == 'id':
                    if 'context' in names or kwname:
                        return cr_uid_id_context(method)
                    else:
                        return cr_uid_id(method)
                elif 'context' in names or kwname:
                    return cr_uid_context(method)
                else:
                    return cr_uid(method)
            elif 'context' in names:
                return cr_context(method)
            else:
                return cr(method)

    # no wrapping by default
    return noguess(method)


def expected(decorator, func):
    """ Decorate `func` with `decorator` if `func` is not wrapped yet. """
    return decorator(func) if not hasattr(func, '_orig') else func



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
        self.mode = env.mode if env else Mode()
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
    def _do_in_mode(self, mode):
        if self.mode.value:
            yield
        else:
            try:
                self.mode.value = mode
                yield
            finally:
                self.mode.value = False
                self.dirty.clear()

    def do_in_draft(self):
        """ Context-switch to draft mode, where all field updates are done in
            cache only.
        """
        return self._do_in_mode(True)

    @property
    def in_draft(self):
        """ Return whether we are in draft mode. """
        return bool(self.mode.value)

    def do_in_onchange(self):
        """ Context-switch to 'onchange' draft mode, which is a specialized
            draft mode used during execution of onchange methods.
        """
        return self._do_in_mode('onchange')

    @property
    def in_onchange(self):
        """ Return whether we are in 'onchange' draft mode. """
        return self.mode.value == 'onchange'

    def invalidate(self, spec):
        """ Invalidate some fields for some records in the cache of all
            environments.

            :param spec: what to invalidate, a list of `(field, ids)` pair,
                where `field` is a field object, and `ids` is a list of record
                ids or ``None`` (to invalidate all records).
        """
        if not spec:
            return
        for env in list(iter(self.all)):
            c = env.cache
            for field, ids in spec:
                if ids is None:
                    if field in c:
                        del c[field]
                else:
                    field_cache = c[field]
                    for id in ids:
                        field_cache.pop(id, None)

    def invalidate_all(self):
        """ Clear the cache of all environments. """
        for env in list(iter(self.all)):
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
            ids = filter(None, field_dump)
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


class Mode(object):
    """ A mode flag shared among environments. """
    value = False           # False, True (draft) or 'onchange' (onchange draft)


# keep those imports here in order to handle cyclic dependencies correctly
from openerp import SUPERUSER_ID
from openerp.exceptions import Warning, AccessError, MissingError
from openerp.modules.registry import RegistryManager
