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

from functools import wraps


def _wrapper(method, old_api, new_api):
    """ return a wrapper for a method that combines both api styles
        :param method: the original method
        :param old_api: the function that implements the old-style api
        :param new_api: the function that implements the new-style api
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
    """ extract the context argument out of ``args`` and ``kwargs``
        :param nargs: expected number of arguments in ``args``
        :param args: arguments (tuple)
        :param kwargs: named arguments (dictionary)
        :return: tuple ``(context, args, kwargs)``
                where both ``args`` and ``kwargs`` are free of context argument
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


def model(method):
    """ Decorate a model method with the new-style API.  Such a method::

            @model
            def method(self, args):
                ...

        may be called in both new and old styles, like::

            obj.method(args)            # new style, obj must have session data
            obj.method(cr, uid, args, context=context)          # old style
    """
    nargs = method.func_code.co_argcount - 1

    def old_api(self, cr, uid, *args, **kwargs):
        context, args, kwargs = _split_context_args(nargs, args, kwargs)
        m = self._make_instance(cr, uid, context)
        return method(m, *args, **kwargs)

    return _wrapper(method, old_api, method)


def recordset(method):
    """ Decorate a recordset method with the new-style API.  Such a method::

            @recordset
            def method(self, args):
                ...

        may be called in both new and old styles, like::

            obj.method(args)            # new style, obj must be a recordset
            obj.method(cr, uid, ids, args, context=context)     # old style
    """
    nargs = method.func_code.co_argcount - 1

    def old_api(self, cr, uid, ids, *args, **kwargs):
        ids = ids if isinstance(ids, list) else [ids]
        context, args, kwargs = _split_context_args(nargs, args, kwargs)
        y = self.browse(cr, uid, ids, context)
        return method(y, *args, **kwargs)

    return _wrapper(method, old_api, method)


def old_cr(method):
    """ Decorate a method with the old-style API.  Such a method::

            @old_cr
            def method(self, cr, args):
                ...

        may be called in both new and old styles, like::

            obj.method(args)            # new style, obj must have session data
            obj.method(cr, args)        # old style

        This decorator is not necessary, see decorator ``versatile``.
    """
    def new_api(self, *args, **kwargs):
        return method(self, self.session.cr, *args, **kwargs)

    return _wrapper(method, method, new_api)


def old_cr_uid(method):
    """ Decorate a method with the old-style API.  Such a method::

            @old_cr_uid
            def method(self, cr, uid, args, context=None):
                ...

        may be called in both new and old styles, like::

            obj.method(args)            # new style, obj must have session data
            obj.method(cr, uid, args, context=context)          # old style

        This decorator is not necessary, see decorator ``versatile``.
    """
    argnames = method.func_code.co_varnames[:method.func_code.co_argcount]
    if 'context' in argnames:
        def new_api(self, *args, **kwargs):
            kwargs = dict(kwargs, context=self.session.context)
            return method(self, self.session.cr, self.session.uid, *args, **kwargs)
    else:
        def new_api(self, *args, **kwargs):
            return method(self, self.session.cr, self.session.uid, *args, **kwargs)

    return _wrapper(method, method, new_api)


def old_cr_uid_id(method):
    """ Decorate a method with the old-style API.  Such a method::

            @old_cr_uid_id
            def method(self, cr, uid, id, args, context=None):
                ...

        may be called in both new and old styles, like::

            obj.method(args)            # new style, obj must be a recordset
            obj.method(cr, uid, id, args, context=context)      # old style

        This decorator is not necessary, see decorator ``versatile``.
    """
    argnames = method.func_code.co_varnames[:method.func_code.co_argcount]
    if 'context' in argnames:
        def new_api(self, *args, **kwargs):
            ids = map(int, self)
            cr, uid = self.session.cr, self.session.uid
            kwargs = dict(kwargs, context=self.session.context)
            return dict((id, method(self, cr, uid, id, *args, **kwargs)) for id in ids)
    else:
        def new_api(self, *args, **kwargs):
            ids = map(int, self)
            cr, uid = self.session.cr, self.session.uid
            return dict((id, method(self, cr, uid, id, *args, **kwargs)) for id in ids)

    return _wrapper(method, method, new_api)


def old_cr_uid_ids(method):
    """ Decorate a method with the old-style API.  Such a method::

            @old_cr_uid_ids
            def method(self, cr, uid, ids, args, context=None):
                ...

        may be called in both new and old styles, like::

            obj.method(args)            # new style, obj must be a recordset
            obj.method(cr, uid, ids, args, context=context)     # old style

        This decorator is not necessary, see decorator ``versatile``.
    """
    argnames = method.func_code.co_varnames[:method.func_code.co_argcount]
    if 'context' in argnames:
        def new_api(self, *args, **kwargs):
            ids = map(int, self)
            kwargs = dict(kwargs, context=self.session.context)
            return method(self, self.session.cr, self.session.uid, ids, *args, **kwargs)
    else:
        def new_api(self, *args, **kwargs):
            ids = map(int, self)
            return method(self, self.session.cr, self.session.uid, ids, *args, **kwargs)

    return _wrapper(method, method, new_api)


def versatile(method):
    """ Decorate a method to make it callable in both old and new styles.
        This decorator is applied automatically by the model's metaclass.

        The API style is determined by heuristics on the parameter names ('cr'
        or 'cursor' for the cursor, 'uid' or 'user' for the user id, 'id' or
        'ids' for a list of record ids, and 'context' for the context dictionary.)

        Method calls are considered old style when their first parameter is
        an instance of Cursor.
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
                    return old_cr_uid_ids(method)
                elif argnames[3] == 'id':
                    return old_cr_uid_id(method)
                else:
                    return old_cr_uid(method)
            else:
                return old_cr(method)

    # no versatile wrapping by default
    method.versatile = False
    return method


def notversatile(method):
    """ Decorate a method to disable any 'versatile' wrapping. """
    method.versatile = False
    return method
