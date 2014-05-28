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
    'Meta', 'guess', 'noguess',
    'model', 'multi', 'one',
    'cr', 'cr_context', 'cr_uid', 'cr_uid_context',
    'cr_uid_id', 'cr_uid_id_context', 'cr_uid_ids', 'cr_uid_ids_context',
    'constrains', 'depends', 'onchange', 'returns',
]

from inspect import getargspec
import logging

_logger = logging.getLogger(__name__)


#
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


def v7(new_method):
    """ Define manually the mapping between api's by decorating the old-style
        implementation of a new-style method.::

            def stuff(self):
                ...

            @api.v7(stuff)
            def stuff(self, cr, uid, context=None):
                ...

        The method name, doc, etc. are copied from `new_method` to the result.
        This is convenient for keeping backward compatibility with methods that
        do not follow the predefined mappings.
    """
    return lambda old_method: make_wrapper(new_method, old_method, new_method)


def v8(old_method):
    """ Define manually the mapping between api's by decorating the new-style
        implementation of an old-style method.::

            def stuff(self, cr, uid, context=None):
                ...

            @api.v8(stuff)
            def stuff(self):
                ...

        The method name, doc, etc. are copied from `old_method` to the result.
        This is convenient for keeping backward compatibility with methods that
        do not follow the predefined mappings.
    """
    return lambda new_method: make_wrapper(old_method, old_method, new_method)


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

