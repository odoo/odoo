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

""" These method decorators aim at managing two different API styles, namely the
    "traditional" and "record" styles.

    In the "traditional" style, parameters like the database cursor, user id,
    context dictionary and record ids (usually denoted as ``cr``, ``uid``,
    ``context``, ``ids``) are passed explicitly to all methods. In the "record"
    style, those parameters are encapsulated in the model instance, which gives
    it a more object-oriented feel.

    For instance, the statements::

        model = self.pool.get(MODEL)
        ids = model.search(cr, uid, DOMAIN, context=context)
        model.write(cr, uid, ids, VALUES, context=context)

    may be written as::

        # model and records both carry the (cr, uid, context) attached to self
        model = self.session.model(MODEL)
        records = model.query(DOMAIN)
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

from functools import wraps


class Meta(type):
    """ Metaclass that automatically decorates methods with :func:`versatile`. """

    def __new__(meta, name, bases, attrs):
        for key, value in attrs.items():
            if not key.startswith('__') and callable(value):
                attrs[key] = versatile(value)
        return type.__new__(meta, name, bases, attrs)


def _wrapper(method, old_api, new_api):
    """ return a wrapper for a method that combines both api styles
        :param method: the original method
        :param old_api: the function that implements the traditional-style api
        :param new_api: the function that implements the record-style api
    """
    from openerp.sql_db import Cursor

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        cr = kwargs.get('cr') or kwargs.get('cursor') or (args and args[0])
        if isinstance(cr, Cursor):
            return old_api(self, *args, **kwargs)
        else:
            return new_api(self, *args, **kwargs)

    wrapper.versatile = True
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
    """ Decorate a record-style method where `self` is any instance with session
        data (model, record or recordset). Such a method::

            @api.model
            def method(self, args):
                ...

        may be called in both record and traditional styles, like::

            model.method(args)
            model.method(cr, uid, args, context=context)
    """
    nargs = method.func_code.co_argcount - 1

    def old_api(self, cr, uid, *args, **kwargs):
        context, args, kwargs = _split_context_args(nargs, args, kwargs)
        m = self.browse(cr, uid, [], context)
        return method(m, *args, **kwargs)

    return _wrapper(method, old_api, method)


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
    nargs = method.func_code.co_argcount - 1

    def old_api(self, cr, uid, ids, *args, **kwargs):
        context, args, kwargs = _split_context_args(nargs, args, kwargs)
        obj = self.browse(cr, uid, ids, context)
        return new_api(obj, *args, **kwargs)

    def new_api(self, *args, **kwargs):
        if self.is_record():
            return method(self, *args, **kwargs)
        else:
            return dict((x.id, method(x, *args, **kwargs)) for x in self)

    return _wrapper(method, old_api, new_api)


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
    nargs = method.func_code.co_argcount - 1

    def old_api(self, cr, uid, ids, *args, **kwargs):
        context, args, kwargs = _split_context_args(nargs, args, kwargs)
        obj = self.browse(cr, uid, ids, context)
        return new_api(obj, *args, **kwargs)

    def new_api(self, *args, **kwargs):
        if self.is_record():
            return _map_record(self.id, method(self.recordset, *args, **kwargs))
        else:
            return method(self, *args, **kwargs)

    return _wrapper(method, old_api, new_api)


def cr(method):
    """ Decorate a traditional-style method that takes `cr` as a parameter.
        Such a method::

            @api.cr
            def method(self, cr, args):
                ...

        may be called in both record and traditional styles, like::

            obj.method(args)            # record style
            obj.method(cr, args)        # traditional style

        This decorator is generally not necessary, see :func:`versatile`.
    """
    def new_api(self, *args, **kwargs):
        return method(self, self.session.cr, *args, **kwargs)

    return _wrapper(method, method, new_api)


def cr_uid(method):
    """ Decorate a traditional-style method that takes `cr`, `uid` as
        parameters. Such a method::

            @api.cr_uid
            def method(self, cr, uid, args, context=None):
                ...

        may be called in both record and traditional styles, like::

            obj.method(args)
            obj.method(cr, uid, args, context=context)

        This decorator is generally not necessary, see :func:`versatile`.
    """
    argnames = method.func_code.co_varnames[:method.func_code.co_argcount]
    if 'context' in argnames:
        def new_api(self, *args, **kwargs):
            cr, uid, context = self.session
            if 'context' not in kwargs:
                kwargs = dict(kwargs, context=context)
            return method(self, cr, uid, *args, **kwargs)
    else:
        def new_api(self, *args, **kwargs):
            cr, uid, context = self.session
            return method(self, cr, uid, *args, **kwargs)

    return _wrapper(method, method, new_api)


def cr_uid_id(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `id`, and
        possibly `context` as parameters. The resulting method follows the
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

        This decorator is generally not necessary, see :func:`versatile`.
    """
    argnames = method.func_code.co_varnames[:method.func_code.co_argcount]
    if 'context' in argnames:
        def new_api(self, *args, **kwargs):
            cr, uid, context = self.session
            if 'context' not in kwargs:
                kwargs = dict(kwargs, context=context)
            if self.is_record():
                return method(self, cr, uid, self.id, *args, **kwargs)
            else:
                return dict((x.id, method(self, cr, uid, x.id, *args, **kwargs)) for x in self)
    else:
        def new_api(self, *args, **kwargs):
            cr, uid, context = self.session
            if self.is_record():
                return method(self, cr, uid, self.id, *args, **kwargs)
            else:
                return dict((x.id, method(self, cr, uid, x.id, *args, **kwargs)) for x in self)

    return _wrapper(method, method, new_api)


def cr_uid_ids(method):
    """ Decorate a traditional-style method that takes `cr`, `uid`, `ids`, and
        possibly `context` as parameters. Such a method::

            @api.cr_uid_ids
            def method(self, cr, uid, ids, args, context=None):
                ...

        may be called in both record and traditional styles, like::

            y = model.browse(ids)               # y is a recordset

            # call on recordset
            y.method(args)
            model.method(cr, uid, ids, args, context=context)

        This decorator supports the :ref:`record-map-convention`.
        It is generally not necessary, see :func:`versatile`.
    """
    argnames = method.func_code.co_varnames[:method.func_code.co_argcount]
    if 'context' in argnames:
        def new_api(self, *args, **kwargs):
            cr, uid, context = self.session
            if 'context' not in kwargs:
                kwargs = dict(kwargs, context=context)
            if self.is_record():
                return _map_record(self.id, method(self, cr, uid, [self.id], *args, **kwargs))
            else:
                return method(self, cr, uid, map(int, self), *args, **kwargs)
    else:
        def new_api(self, *args, **kwargs):
            cr, uid, context = self.session
            if self.is_record():
                return _map_record(self.id, method(self, cr, uid, [self.id], *args, **kwargs))
            else:
                return method(self, cr, uid, map(int, self), *args, **kwargs)

    return _wrapper(method, method, new_api)


def versatile(method):
    """ Decorate `method` to make it callable in both traditional and record
        styles. This decorator is applied automatically by the model's
        metaclass, and has no effect on already-decorated methods.

        The API style is determined by heuristics on the parameter names: ``cr``
        or ``cursor`` for the cursor, ``uid`` or ``user`` for the user id,
        ``id`` or ``ids`` for a list of record ids, and ``context`` for the
        context dictionary. If a traditional API is recognized, one of the
        decorators :func:`cr`, :func:`cr_uid`, :func:`cr_uid_id`,
        :func:`cr_uid_ids` is applied on the method.

        Method calls are considered traditional style when their first parameter
        is a database cursor.
    """
    if hasattr(method, 'versatile'):
        return method

    # introspection on argument names to determine api style
    argnames = method.func_code.co_varnames[:method.func_code.co_argcount]
    if len(argnames) < 4:
        argnames = argnames + (None,) * (4 - len(argnames))

    if argnames[0] == 'self':
        if argnames[1] in ('cr', 'cursor'):
            if argnames[2] in ('uid', 'user'):
                if argnames[3] == 'ids':
                    return cr_uid_ids(method)
                elif argnames[3] == 'id':
                    return cr_uid_id(method)
                else:
                    return cr_uid(method)
            else:
                return cr(method)

    # no versatile wrapping by default
    method.versatile = False
    return method


def notversatile(method):
    """ Decorate a method to disable any effect from :func:`versatile`. """
    method.versatile = False
    return method
