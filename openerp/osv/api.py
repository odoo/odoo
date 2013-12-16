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
        for rec in model.browse(cr, uid, ids, context=context):
            print rec.name
        model.write(cr, uid, ids, VALUES, context=context)

    may also be written as::

        with scope(cr, uid, context):       # cr, uid, context introduced once
            model = scope[MODEL]            # scope proxies the current scope
            recs = model.search(DOMAIN)     # search returns a recordset
            for rec in recs:                # iterate over the records
                print rec.name
            recs.write(VALUES)              # update all records in recs

    Methods written in the "traditional" style are automatically decorated,
    following some heuristics based on parameter names.
"""

__all__ = [
    'Meta', 'guess', 'noguess',
    'model', 'multi', 'one',
    'cr', 'cr_context', 'cr_uid', 'cr_uid_context',
    'cr_uid_id', 'cr_uid_id_context', 'cr_uid_ids', 'cr_uid_ids_context',
    'constrains', 'depends', 'returns',
]

from functools import update_wrapper
from inspect import getargspec
import logging

_logger = logging.getLogger(__name__)


#
# The following attributes are used, and reflected on wrapping methods:
#  - method._api: decorator function, used for re-applying decorator
#  - method._constrains: set by @constrains, specifies constraint dependencies
#  - method._depends: set by @depends, specifies compute dependencies
#  - method._returns: set by @returns, specifies return model
#  - method.clear_cache: set by @ormcache, used to clear the cache
#
# On wrapping method only:
#  - method._orig: original method
#

_WRAPPED_ATTRS = ('_api', '_constrains', '_depends', '_returns', 'clear_cache')


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
                if not _returns(value) and _returns(getattr(parent, key, None)):
                    value = returns(getattr(parent, key))(value)
                    _logger.debug("Method %s.%s inherited @returns%r",
                                  name, value.__name__, _returns(value))

                # guess calling convention if none is given
                if not hasattr(value, '_api'):
                    value = guess(value)

                attrs[key] = value

        return type.__new__(meta, name, bases, attrs)


def constrains(*args):
    """ Return a decorator that specifies the field dependencies of a method
        implementing a constraint checker. Each argument must be a field name.
    """
    def decorate(method):
        method._constrains = args
        return method

    return decorate


def depends(*args):
    """ Return a decorator that specifies the field dependencies of a "compute"
        method (for new-style function fields). Each argument must be a string
        that consists in a dot-separated sequence of field names.

        One may also pass a single function as argument. In that case, the
        dependencies are given by calling the function with the field's model.
    """
    if args and callable(args[0]):
        args = args[0]

    def decorate(method):
        method._depends = args
        return method

    return decorate


def returns(model, traditional=None):
    """ Return a decorator for methods that return instances of `model`.

        :param model: a model name, ``'self'`` for the current model, or a method
            (in which case the model is taken from that method's decorator)

        :param traditional: a function `convert(self, value)` to convert the
            record-style value to the traditional-style output

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
    """
    if callable(model):
        # model is a method, check its own @returns decoration
        spec = _returns(model)
        if not spec:
            return lambda method: method
    else:
        spec = model, traditional

    def decorate(method):
        if hasattr(method, '_orig'):
            # decorate the original method, and re-apply the api decorator
            origin = method._orig
            origin._returns = spec
            return origin._api(origin)
        else:
            method._returns = spec
            return method

    return decorate


def _returns(method):
    return getattr(method, '_returns', None)


# constant converters
_CONVERT_PASS = lambda self, value: value
_CONVERT_BROWSE = lambda self, value: self.browse(value)
_CONVERT_UNBROWSE = lambda self, value: value.unbrowse()


def _converter_to_old(method):
    """ Return a function `convert(self, value)` that adapts `value` from
        record-style to traditional-style returning convention of `method`.
    """
    spec = _returns(method)
    if spec:
        model, traditional = spec
        return traditional or _CONVERT_UNBROWSE
    else:
        return _CONVERT_PASS


def _converter_to_new(method):
    """ Return a function `convert(self, value)` that adapts `value` from
        traditional-style to record-style returning convention of `method`.
    """
    spec = _returns(method)
    if spec:
        model, traditional = spec
        if model == 'self':
            return _CONVERT_BROWSE
        else:
            return lambda self, value: self.pool[model].browse(value)
    else:
        return _CONVERT_PASS


def _aggregator_one(method):
    """ Return a function `convert(self, value)` that aggregates record-style
        `value` for a method decorated with ``@one``.
    """
    spec = _returns(method)
    if spec:
        # value is a list of instances, concatenate them
        model, traditional = spec
        if model == 'self':
            return lambda self, value: sum(value, self.browse())
        else:
            return lambda self, value: sum(value, self.pool[model].browse())
    else:
        return _CONVERT_PASS


def wraps(method):
    """ Return a decorator for an api wrapper of `method`. """
    def decorate(wrapper):
        # propagate '__module__', '__name__', '__doc__' to wrapper
        update_wrapper(wrapper, method)
        # propagate specific openerp attributes to wrapper
        for attr in _WRAPPED_ATTRS:
            if hasattr(method, attr):
                setattr(wrapper, attr, getattr(method, attr))
        wrapper._orig = method
        return wrapper

    return decorate


def _has_cursor(args, kwargs):
    """ test whether `args` or `kwargs` contain a cursor argument """
    cr = args[0] if args else kwargs.get('cr')
    return isinstance(cr, Cursor)


def _cr_uid_context_splitter(method):
    """ return a function that splits scope parameters from the other arguments """
    names = getargspec(method).args[1:]
    ctx_pos = len(names) + 2

    def split(args, kwargs):
        cr, uid = args[:2]
        if ctx_pos < len(args):
            return cr, uid, args[ctx_pos], args[2:ctx_pos], kwargs
        else:
            return cr, uid, kwargs.pop('context', None), args[2:], kwargs

    return split


def _cr_uid_ids_context_splitter(method):
    """ return a function that splits scope parameters from the other arguments """
    names = getargspec(method).args[1:]
    ctx_pos = len(names) + 3

    def split(args, kwargs):
        cr, uid, ids = args[:3]
        if ctx_pos < len(args):
            return cr, uid, ids, args[ctx_pos], args[3:ctx_pos], kwargs
        else:
            return cr, uid, ids, kwargs.pop('context', None), args[3:], kwargs

    return split


def _scope_getter(method):
    """ return a function that gets the scope corresponding to parameters """
    names = getargspec(method).args[1:]
    cr_name = names[0]
    uid_name = len(names) > 1 and names[1] in ('uid', 'user') and names[1]
    ctx_pos = 'context' in names and names.index('context')

    if uid_name:
        if ctx_pos:
            def get(args, kwargs):
                nargs = len(args)
                cr = args[0] if nargs else kwargs[cr_name]
                uid = args[1] if 1 < nargs else kwargs[uid_name]
                context = args[ctx_pos] if ctx_pos < nargs else kwargs.get('context')
                return Scope(cr, uid, context)
        else:
            def get(args, kwargs):
                nargs = len(args)
                cr = args[0] if nargs else kwargs[cr_name]
                uid = args[1] if 1 < nargs else kwargs[uid_name]
                return Scope(cr, uid, kwargs.get('context'))
    else:
        if ctx_pos:
            def get(args, kwargs):
                nargs = len(args)
                cr = args[0] if nargs else kwargs[cr_name]
                context = args[ctx_pos] if ctx_pos < nargs else kwargs.get('context')
                return Scope(cr, SUPERUSER_ID, context)
        else:
            def get(args, kwargs):
                cr = args[0] if args else kwargs[cr_name]
                return Scope(cr, SUPERUSER_ID, kwargs.get('context'))

    return get


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
    split_args = _cr_uid_context_splitter(method)
    new_to_old = _converter_to_old(method)

    @wraps(method)
    def model_wrapper(self, *args, **kwargs):
        if _has_cursor(args, kwargs):
            cr, uid, context, args, kwargs = split_args(args, kwargs)
            with Scope(cr, uid, context):
                value = method(self, *args, **kwargs)
                return new_to_old(self, value)
        else:
            return method(self, *args, **kwargs)

    return model_wrapper


def multi(method):
    """ Decorate a record-style method where `self` is a recordset. Such a
        method::

            @api.multi
            def method(self, args):
                ...

        may be called in both record and traditional styles, like::

            recs = model.browse(ids)

            # the following calls are equivalent
            recs.method(args)
            model.method(cr, uid, ids, args, context=context)
    """
    method._api = multi
    split_args = _cr_uid_ids_context_splitter(method)
    new_to_old = _converter_to_old(method)

    @wraps(method)
    def multi_wrapper(self, *args, **kwargs):
        if _has_cursor(args, kwargs):
            cr, uid, ids, context, args, kwargs = split_args(args, kwargs)
            with Scope(cr, uid, context):
                # There is this feature for the backward-compatiblity with the
                # previous version of OpenERP, and we give the capability to use
                # one identifier for the read method
                if method.func_name == 'read' and isinstance(ids, (long, int)):
                    _logger.warning(
                        "Call to %s with an integer instead of a list of integers is deprecated.",
                        method.func_name
                    )
                    values = method(self.browse([ids]), *args, **kwargs)
                    return new_to_old(self, values)[0]
                else:
                    value = method(self.browse(ids), *args, **kwargs)
                    return new_to_old(self, value)
        else:
            return method(self, *args, **kwargs)

    return multi_wrapper


def one(method):
    """ Decorate a record-style method where `self` is expected to be a
        singleton instance. The decorated method automatically loops on records,
        and makes a list with the results. In case the method is decorated with
        @returns, it concatenates the resulting instances. Such a method::

            @api.one
            def method(self, args):
                return self.name

        may be called in both record and traditional styles, like::

            recs = model.browse(ids)

            # the following calls are equivalent and return a list of names
            recs.method(args)
            model.method(cr, uid, recs.unbrowse(), args, context=context)
    """
    method._api = one
    split_args = _cr_uid_ids_context_splitter(method)
    new_to_old = _converter_to_old(method)
    aggregate = _aggregator_one(method)

    @wraps(method)
    def one_wrapper(self, *args, **kwargs):
        if _has_cursor(args, kwargs):
            cr, uid, ids, context, args, kwargs = split_args(args, kwargs)
            with Scope(cr, uid, context):
                value = [method(rec, *args, **kwargs) for rec in self.browse(ids)]
                return new_to_old(self, aggregate(self, value))
        else:
            value = [method(rec, *args, **kwargs) for rec in self]
            return aggregate(self, value)

    return one_wrapper


def cr(method):
    """ Decorate a traditional-style method that takes `cr` as a parameter.
        Such a method may be called in both record and traditional styles, like::

            obj.method(args)            # record style
            obj.method(cr, args)        # traditional style
    """
    method._api = cr
    get_scope = _scope_getter(method)
    old_to_new = _converter_to_new(method)

    @wraps(method)
    def cr_wrapper(self, *args, **kwargs):
        if _has_cursor(args, kwargs):
            with get_scope(args, kwargs):
                return method(self, *args, **kwargs)
        else:
            value = method(self, scope.cr, *args, **kwargs)
            return old_to_new(self, value)

    return cr_wrapper


def cr_context(method):
    """ Decorate a traditional-style method that takes `cr`, `context` as parameters. """
    method._api = cr_context
    get_scope = _scope_getter(method)
    old_to_new = _converter_to_new(method)

    @wraps(method)
    def cr_context_wrapper(self, *args, **kwargs):
        if _has_cursor(args, kwargs):
            with get_scope(args, kwargs):
                return method(self, *args, **kwargs)
        else:
            cr, _, context = scope.args
            kwargs['context'] = context
            value = method(self, cr, *args, **kwargs)
            return old_to_new(self, value)

    return cr_context_wrapper


def cr_uid(method):
    """ Decorate a traditional-style method that takes `cr`, `uid` as parameters. """
    method._api = cr_uid
    get_scope = _scope_getter(method)
    old_to_new = _converter_to_new(method)

    @wraps(method)
    def cr_uid_wrapper(self, *args, **kwargs):
        if _has_cursor(args, kwargs):
            with get_scope(args, kwargs):
                return method(self, *args, **kwargs)
        else:
            cr, uid, _ = scope.args
            value = method(self, cr, uid, *args, **kwargs)
            return old_to_new(self, value)

    return cr_uid_wrapper


def cr_uid_context(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `context` as
        parameters. Such a method may be called in both record and traditional
        styles, like::

            obj.method(args)
            obj.method(cr, uid, args, context=context)
    """
    method._api = cr_uid_context
    get_scope = _scope_getter(method)
    old_to_new = _converter_to_new(method)

    @wraps(method)
    def cr_uid_context_wrapper(self, *args, **kwargs):
        if _has_cursor(args, kwargs):
            with get_scope(args, kwargs):
                return method(self, *args, **kwargs)
        else:
            cr, uid, context = scope.args
            kwargs['context'] = context
            value = method(self, cr, uid, *args, **kwargs)
            return old_to_new(self, value)

    return cr_uid_context_wrapper


def cr_uid_id(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `id` as
        parameters. Such a method may be called in both record and traditional
        styles. In the record style, the method automatically loops on records.
    """
    method._api = cr_uid_id
    get_scope = _scope_getter(method)
    old_to_new = _converter_to_new(method)

    @wraps(method)
    def cr_uid_id_wrapper(self, *args, **kwargs):
        if _has_cursor(args, kwargs):
            with get_scope(args, kwargs):
                return method(self, *args, **kwargs)
        else:
            cr, uid, _ = scope.args
            value = [method(self, cr, uid, id, *args, **kwargs) for id in self.unbrowse()]
            return old_to_new(self, value)

    return cr_uid_id_wrapper


def cr_uid_id_context(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `id`,
        `context` as parameters. Such a method::

            @api.cr_uid_id
            def method(self, cr, uid, id, args, context=None):
                ...

        may be called in both record and traditional styles, like::

            rec = model.browse(id)

            # the following calls are equivalent
            rec.method(args)
            model.method(cr, uid, id, args, context=context)
    """
    method._api = cr_uid_id_context
    get_scope = _scope_getter(method)
    old_to_new = _converter_to_new(method)

    @wraps(method)
    def cr_uid_id_context_wrapper(self, *args, **kwargs):
        if _has_cursor(args, kwargs):
            with get_scope(args, kwargs):
                return method(self, *args, **kwargs)
        else:
            cr, uid, context = scope.args
            kwargs['context'] = context
            value = [method(self, cr, uid, id, *args, **kwargs) for id in self.unbrowse()]
            return old_to_new(self, value)

    return cr_uid_id_context_wrapper


def cr_uid_ids(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `ids` as
        parameters. Such a method may be called in both record and traditional
        styles.
    """
    method._api = cr_uid_ids
    get_scope = _scope_getter(method)
    old_to_new = _converter_to_new(method)

    @wraps(method)
    def cr_uid_ids_wrapper(self, *args, **kwargs):
        if _has_cursor(args, kwargs):
            with get_scope(args, kwargs):
                return method(self, *args, **kwargs)
        else:
            cr, uid, _ = scope.args
            value = method(self, cr, uid, self.unbrowse(), *args, **kwargs)
            return old_to_new(self, value)

    return cr_uid_ids_wrapper


def cr_uid_ids_context(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `ids`,
        `context` as parameters. Such a method::

            @api.cr_uid_ids_context
            def method(self, cr, uid, ids, args, context=None):
                ...

        may be called in both record and traditional styles, like::

            recs = model.browse(ids)

            # the following calls are equivalent
            recs.method(args)
            model.method(cr, uid, ids, args, context=context)

        It is generally not necessary, see :func:`guess`.
    """
    method._api = cr_uid_ids_context
    get_scope = _scope_getter(method)
    old_to_new = _converter_to_new(method)

    @wraps(method)
    def cr_uid_ids_context_wrapper(self, *args, **kwargs):
        if _has_cursor(args, kwargs):
            with get_scope(args, kwargs):
                return method(self, *args, **kwargs)
        else:
            cr, uid, context = scope.args
            kwargs['context'] = context
            value = method(self, cr, uid, self.unbrowse(), *args, **kwargs)
            return old_to_new(self, value)

    return cr_uid_ids_context_wrapper


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
    names = tuple(getargspec(method).args) + (None,) * 4

    if names[0] == 'self':
        if names[1] in ('cr', 'cursor'):
            if names[2] in ('uid', 'user'):
                if names[3] == 'ids':
                    if 'context' in names:
                        return cr_uid_ids_context(method)
                    else:
                        return cr_uid_ids(method)
                elif names[3] == 'id':
                    if 'context' in names:
                        return cr_uid_id_context(method)
                    else:
                        return cr_uid_id(method)
                elif 'context' in names:
                    return cr_uid_context(method)
                else:
                    return cr_uid(method)
            elif 'context' in names:
                return cr_context(method)
            else:
                return cr(method)

    # no wrapping by default
    return noguess(method)


# keep those imports here in order to handle cyclic dependencies correctly
from openerp import SUPERUSER_ID
from openerp.osv.scope import Scope, proxy as scope
from openerp.sql_db import Cursor
