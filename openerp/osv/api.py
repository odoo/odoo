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
    style, those parameters are hidden in an execution environment (a "scope")
    and the methods only refer to model instances, which gives it a more object-
    oriented feel.

    For instance, the statements::

        model = self.pool.get(MODEL)
        ids = model.search(cr, uid, DOMAIN, context=context)
        model.write(cr, uid, ids, VALUES, context=context)

    may also be written as::

        with Scope(cr, uid, context):
            model = scope.model(MODEL)          # scope is a proxy to the current scope
            records = model.search(DOMAIN)
            records.write(VALUES)

    Methods written in the "traditional" style are automatically decorated,
    following some heuristics based on parameter names.


    .. _record-map-convention:

    Record-map convention
    ---------------------

    The decorators also provides support for "record-map" methods, i.e., methods
    with a specific calling convention: when called on a recordset, they return
    a dictionary that associates record ids to values. Function fields use that
    convention, for instance.

    When a method is called on a single record, the actual method is called with
    a recordset made from that record. The result is then inspected to see
    whether it is a record-map. If that is the case, the value is extracted from
    the dictionary.

    The following example illustrates the case::

        y = model.browse([42, 43])              # y is a recordset
        y.method(args)                          # => {42: 'foo', 43: 'bar'}

        x = model.browse(42)                    # x is a single record
        x.method(args)                          # => 'foo'

"""

__all__ = [
    'Scope', 'scope', 'Meta', 'guess', 'noguess',
    'model', 'record', 'recordset',
    'cr', 'cr_context', 'cr_uid', 'cr_uid_context',
    'cr_uid_id', 'cr_uid_id_context', 'cr_uid_ids', 'cr_uid_ids_context',
    'returns',
]

from functools import wraps
import logging
from werkzeug.local import Local, release_local

_logger = logging.getLogger(__name__)

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

scope = ScopeProxy()


class Scope(object):
    """ A scope wraps environment data for the ORM instances:

         - :attr:`cr`, the current database cursor;
         - :attr:`uid`, the current user id;
         - :attr:`context`, the current context dictionary.

        An execution environment is created by a statement ``with``::

            with Scope(cr, uid, context):
                # statements execute in given scope

        Iterating over a scope returns the three attributes above, in that
        order. This is useful to retrieve data in a destructuring assignment::

            cr, uid, context = scope
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
        scope.push(self)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        scope.pop()

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
            elif isinstance(arg, (BaseModel, int, long)):
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
        with scope.SUDO():
            return self.model('res.users').browse(self.uid)

    @property
    def lang(self):
        """ return the current language code """
        if not hasattr(self, '_lang'):
            self._lang = self.context.get('lang') or 'en_US'
        return self._lang

    @property
    def language(self):
        """ return the current language (as a record) """
        try:
            with scope.SUDO():
                languages = self.model('res.lang').search([('code', '=', self.lang)])
                return languages.record()
        except Exception:
            raise Exception(_('Language with code "%s" is not defined in your system !\nDefine it through the Administration menu.') % (self.lang,))


#
# The following attributes are used on methods:
#    method._api: decorator function, both on original and wrapping method
#    method._returns: set by @returns, both on original and wrapping method
#    method._orig: original method, on wrapping method only
#

def _get_returns(method):
    return getattr(method, '_returns', None)


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
                # make the method inherit from @returns decorators
                if not _get_returns(value) and _get_returns(getattr(parent, key, None)):
                    value = returns(getattr(parent, key))(value)
                    _logger.debug("Method %s.%s inherited @returns(%r)",
                                  name, value.__name__, _get_returns(value))

                # guess calling convention if none is given
                if not hasattr(value, '_api'):
                    value = guess(value)

                attrs[key] = value

        return type.__new__(meta, name, bases, attrs)


def returns(model):
    """ Return a decorator for methods that return instances of `model`.

        :param model: a model name, ``'self'`` for the current model, or a method
            (in which case the model is taken from that method's decorator)

        The decorator adapts the method output to the api style: `id`, `ids` or
        ``False`` for the traditional style, and record, recordset or null for
        the record style::

            @model
            @returns('res.partner')
            def find_partner(self, arg):
                ...     # return some record

            # output depends on call style: traditional vs record style
            partner_id = model.find_partner(cr, uid, arg, context=context)
            partner_record = model.find_partner(arg)

        Note that the decorated method must satisfy that convention.

        Those decorators are automatically *inherited*: a method that overrides
        a decorated existing method will be decorated with the same
        ``@returns(model)``.
        They also supports the :ref:`record-map-convention`.
    """
    if callable(model):
        # model is a method, check its own @returns decoration
        model = _get_returns(model)
        if not model:
            return lambda method: method

    def decorate(method):
        if hasattr(method, '_orig'):
            # decorate the original method, and re-apply the api decorator
            origin = method._orig
            origin._returns = model
            return origin._api(origin)
        else:
            method._returns = model
            return method

    return decorate


def _returns_old(method, func):
    """ adapts `func` to the traditional-style returning convention of `method`;
        `func` must follow the record-style returning convention
    """
    if _get_returns(method):
        def wrapper(self, *args, **kwargs):
            res = func(self, *args, **kwargs)
            if isinstance(res, dict):
                return dict((k, v.unbrowse()) for k, v in res.iteritems())
            return res.unbrowse()
        return wrapper
    else:
        return func


def _returns_new(method, func):
    """ adapts `func` to the record-style returning convention of `method`;
        `func` must follow the traditional-style returning convention
    """
    model = _get_returns(method)
    if model == 'self':
        def wrapper(self, *args, **kwargs):
            res = func(self, *args, **kwargs)
            if isinstance(res, dict):
                return dict((k, self.browse(v)) for k, v in res.iteritems())
            return self.browse(res)
        return wrapper
    elif model:
        def wrapper(self, *args, **kwargs):
            mod = scope.model(model)
            res = func(self, *args, **kwargs)
            if isinstance(res, dict):
                return dict((k, mod.browse(v)) for k, v in res.iteritems())
            return mod.browse(res)
        return wrapper
    else:
        return func


def _make_wrapper(method, old_api, new_api):
    """ return a wrapper for a method that combines both api styles
        :param method: the original method
        :param old_api: the function that implements the traditional-style api
        :param new_api: the function that implements the record-style api
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        cr = kwargs.get('cr', args and args[0])
        if isinstance(cr, Cursor):
            return old_api(self, *args, **kwargs)
        else:
            return new_api(self, *args, **kwargs)

    # propagate some openerp attributes to the wrapper
    for attr in ('_api', '_returns', 'clear_cache'):
        if hasattr(method, attr):
            setattr(wrapper, attr, getattr(method, attr))
    wrapper._orig = method
    return wrapper


def _split_context_args(nargs, args, kwargs):
    """ extract the context argument out of `args` and `kwargs`
        :param nargs: expected number of arguments in `args`
        :param args: arguments (tuple)
        :param kwargs: named arguments (dictionary)
        :return: tuple `(context, args, kwargs)`
                where both `args` and `kwargs` are free of context argument
    """
    if 'context' in kwargs:
        context = kwargs['context']
        del kwargs['context']
        return context, args, kwargs
    elif len(args) + len(kwargs) > nargs:
        # heuristics: context is given as an extra argument in args
        return args[-1], args[:-1], kwargs
    else:
        # context defaults to None
        return None, args, kwargs


def _map_record(id, value):
    """ if `value` is a record map for the given record `id`, return the
        corresponding value; otherwise return `value`
    """
    if isinstance(value, dict) and value.keys() == [id]:
        return value[id]
    return value


def model(method):
    """ Decorate a record-style method where `self` is any instance with scope
        (model, record or recordset). Such a method::

            @api.model
            def method(self, args):
                ...

        may be called in both record and traditional styles, like::

            model.method(args)
            model.method(cr, uid, args, context=context)
    """
    method._api = model
    nargs = method.func_code.co_argcount - 1

    def old_api(self, cr, uid, *args, **kwargs):
        context, args, kwargs = _split_context_args(nargs, args, kwargs)
        with Scope(cr, uid, context):
            return method(self, *args, **kwargs)

    return _make_wrapper(method, _returns_old(method, old_api), method)


def record(method):
    """ Decorate a record-style method where `self` is a single record. The
        resulting method follows the :ref:`record-map-convention`.
        Such a method::

            @api.record
            def method(self, args):
                return self.name

        may be called in both record and traditional styles, like::

            y = model.browse([id, ...])         # y is a recordset
            x = y[0]                            # x is a record

            # call on record => x.name
            x.method(args)
            model.method(cr, uid, id, args, context=context)

            # call on recordset => {id: ..., ...}
            y.method(args)
            model.method(cr, uid, [id, ...], args, context=context)
    """
    method._api = record
    nargs = method.func_code.co_argcount - 1

    def old_api(self, cr, uid, ids, *args, **kwargs):
        context, args, kwargs = _split_context_args(nargs, args, kwargs)
        with Scope(cr, uid, context):
            return new_api(self.browse(ids), *args, **kwargs)

    def new_api(self, *args, **kwargs):
        if self.is_record():
            return method(self, *args, **kwargs)
        else:
            return dict((x.id, method(x, *args, **kwargs)) for x in self)

    return _make_wrapper(method, _returns_old(method, old_api), new_api)


def recordset(method):
    """ Decorate a record-style method where `self` is a recordset. Such a
        method::

            @api.recordset
            def method(self, args):
                ...

        may be called in both record and traditional styles, like::

            y = model.browse(ids)               # y is a recordset

            y.method(args)
            model.method(cr, uid, ids, args, context=context)

        This decorator supports the :ref:`record-map-convention`.
    """
    method._api = recordset
    nargs = method.func_code.co_argcount - 1

    def old_api(self, cr, uid, ids, *args, **kwargs):
        context, args, kwargs = _split_context_args(nargs, args, kwargs)
        with Scope(cr, uid, context):
            return new_api(self.browse(ids), *args, **kwargs)

    def new_api(self, *args, **kwargs):
        if self.is_record():
            return _map_record(self.id, method(self.recordset(), *args, **kwargs))
        else:
            return method(self, *args, **kwargs)

    return _make_wrapper(method, _returns_old(method, old_api), new_api)


def _kwargs_context(kwargs, context):
    """ add the `context` parameter in `kwargs` """
    return dict(kwargs, context=context) if 'context' not in kwargs else kwargs


def cr(method):
    """ Decorate a traditional-style method that takes `cr` as a parameter.
        Such a method may be called in both record and traditional styles, like::

            obj.method(args)            # record style
            obj.method(cr, args)        # traditional style
    """
    method._api = cr

    def old_api(self, cr, *args, **kwargs):
        with Scope(cr, SUPERUSER_ID, None):
            return method(self, cr, *args, **kwargs)

    def new_api(self, *args, **kwargs):
        cr, uid, context = scope
        return method(self, cr, *args, **kwargs)

    return _make_wrapper(method, old_api, _returns_new(method, new_api))


def cr_context(method):
    """ Decorate a traditional-style method that takes `cr`, `context` as parameters. """
    method._api = cr_context

    def old_api(self, cr, *args, **kwargs):
        with Scope(cr, SUPERUSER_ID, kwargs.get('context')):
            return method(self, cr, *args, **kwargs)

    def new_api(self, *args, **kwargs):
        cr, uid, context = scope
        kwargs = _kwargs_context(kwargs, context)
        return method(self, cr, *args, **kwargs)

    return _make_wrapper(method, old_api, _returns_new(method, new_api))


def cr_uid(method):
    """ Decorate a traditional-style method that takes `cr`, `uid` as parameters. """
    method._api = cr_uid

    def old_api(self, cr, uid, *args, **kwargs):
        with Scope(cr, uid, None):
            return method(self, cr, uid, *args, **kwargs)

    def new_api(self, *args, **kwargs):
        cr, uid, context = scope
        return method(self, cr, uid, *args, **kwargs)

    return _make_wrapper(method, old_api, _returns_new(method, new_api))


def cr_uid_context(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `context` as
        parameters. Such a method may be called in both record and traditional
        styles, like::

            obj.method(args)
            obj.method(cr, uid, args, context=context)
    """
    method._api = cr_uid_context

    def old_api(self, cr, uid, *args, **kwargs):
        with Scope(cr, uid, kwargs.get('context')):
            return method(self, cr, uid, *args, **kwargs)

    def new_api(self, *args, **kwargs):
        cr, uid, context = scope
        kwargs = _kwargs_context(kwargs, context)
        return method(self, cr, uid, *args, **kwargs)

    return _make_wrapper(method, old_api, _returns_new(method, new_api))


def cr_uid_id(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `id` as
        parameters. Such a method may be called in both record and traditional
        styles. The resulting method follows the :ref:`record-map-convention`.
    """
    method._api = cr_uid_id

    def old_api(self, cr, uid, id, *args, **kwargs):
        with Scope(cr, uid, None):
            return method(self, cr, uid, id, *args, **kwargs)

    def new_api(self, *args, **kwargs):
        cr, uid, context = scope
        if self.is_record():
            return method(self, cr, uid, self.id, *args, **kwargs)
        else:
            return dict((x.id, method(self, cr, uid, x.id, *args, **kwargs)) for x in self)

    return _make_wrapper(method, old_api, _returns_new(method, new_api))


def cr_uid_id_context(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `id`,
        `context` as parameters. The resulting method follows the
        :ref:`record-map-convention`. Such a method::

            @api.cr_uid_id
            def method(self, cr, uid, id, args, context=None):
                ...

        may be called in both record and traditional styles, like::

            y = model.browse([id])              # y is a recordset
            x = y[0]                            # x is a record

            # call on record => value
            x.method(args)
            model.method(cr, uid, id, args, context=context)

            # call on recordset => {id: value}
            y.method(args)
    """
    method._api = cr_uid_id_context

    def old_api(self, cr, uid, id, *args, **kwargs):
        with Scope(cr, uid, kwargs.get('context')):
            return method(self, cr, uid, id, *args, **kwargs)

    def new_api(self, *args, **kwargs):
        cr, uid, context = scope
        kwargs = _kwargs_context(kwargs, context)
        if self.is_record():
            return method(self, cr, uid, self.id, *args, **kwargs)
        else:
            return dict((x.id, method(self, cr, uid, x.id, *args, **kwargs)) for x in self)

    return _make_wrapper(method, old_api, _returns_new(method, new_api))


def cr_uid_ids(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `ids` as
        parameters. Such a method may be called in both record and traditional
        styles. This decorator supports the :ref:`record-map-convention`.
    """
    method._api = cr_uid_ids

    def old_api(self, cr, uid, ids, *args, **kwargs):
        with Scope(cr, uid, None):
            return method(self, cr, uid, ids, *args, **kwargs)

    def new_api(self, *args, **kwargs):
        cr, uid, context = scope
        if self.is_record():
            return _map_record(self.id, method(self, cr, uid, [self.id], *args, **kwargs))
        else:
            return method(self, cr, uid, map(int, self), *args, **kwargs)

    return _make_wrapper(method, old_api, _returns_new(method, new_api))


def cr_uid_ids_context(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `ids`,
        `context` as parameters. Such a method::

            @api.cr_uid_ids_context
            def method(self, cr, uid, ids, args, context=None):
                ...

        may be called in both record and traditional styles, like::

            y = model.browse(ids)               # y is a recordset

            # call on recordset
            y.method(args)
            model.method(cr, uid, ids, args, context=context)

        This decorator supports the :ref:`record-map-convention`.
        It is generally not necessary, see :func:`guess`.
    """
    method._api = cr_uid_ids_context

    def old_api(self, cr, uid, ids, *args, **kwargs):
        with Scope(cr, uid, kwargs.get('context')):
            return method(self, cr, uid, ids, *args, **kwargs)

    def new_api(self, *args, **kwargs):
        cr, uid, context = scope
        kwargs = _kwargs_context(kwargs, context)
        if self.is_record():
            return _map_record(self.id, method(self, cr, uid, [self.id], *args, **kwargs))
        else:
            return method(self, cr, uid, map(int, self), *args, **kwargs)

    return _make_wrapper(method, old_api, _returns_new(method, new_api))


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
    # introspection on argument names to determine api style
    argnames = method.func_code.co_varnames[:method.func_code.co_argcount]
    if len(argnames) < 4:
        argnames = argnames + (None,) * (4 - len(argnames))

    if argnames[0] == 'self':
        if argnames[1] in ('cr', 'cursor'):
            if argnames[2] in ('uid', 'user'):
                if argnames[3] == 'ids':
                    if 'context' in argnames:
                        return cr_uid_ids_context(method)
                    else:
                        return cr_uid_ids(method)
                elif argnames[3] == 'id':
                    if 'context' in argnames:
                        return cr_uid_id_context(method)
                    else:
                        return cr_uid_id(method)
                elif 'context' in argnames:
                    return cr_uid_context(method)
                else:
                    return cr_uid(method)
            elif 'context' in argnames:
                return cr_context(method)
            else:
                return cr(method)

    # no wrapping by default
    return noguess(method)


# keep those imports here in order to handle cyclic dependencies correctly
from openerp import SUPERUSER_ID
from openerp.osv.orm import BaseModel
from openerp.sql_db import Cursor
from openerp.tools.translate import _
from openerp.modules.registry import RegistryManager
