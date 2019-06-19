# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

        env = Environment(cr, uid, context) # cr, uid, context wrapped in env
        model = env[MODEL]                  # retrieve an instance of MODEL
        recs = model.search(DOMAIN)         # search returns a recordset
        for rec in recs:                    # iterate over the records
            print rec.name
        recs.write(VALUES)                  # update all records in recs

    Methods written in the "traditional" style are automatically decorated,
    following some heuristics based on parameter names.
"""

__all__ = [
    'Environment',
    'Meta',
    'model',
    'constrains', 'depends', 'onchange', 'returns',
    'call_kw',
]

import copy
import logging
from collections import defaultdict, Mapping
from contextlib import contextmanager
from inspect import getargspec
from pprint import pformat
from weakref import WeakSet

from decorator import decorate, decorator
from werkzeug.local import Local, release_local

from odoo.tools import frozendict, classproperty, StackMap
from odoo.exceptions import CacheMiss

_logger = logging.getLogger(__name__)

# The following attributes are used, and reflected on wrapping methods:
#  - method._constrains: set by @constrains, specifies constraint dependencies
#  - method._depends: set by @depends, specifies compute dependencies
#  - method._returns: set by @returns, specifies return model
#  - method._onchange: set by @onchange, specifies onchange fields
#  - method.clear_cache: set by @ormcache, used to clear the cache
#
# On wrapping method only:
#  - method._api: decorator function, used for re-applying decorator
#

INHERITED_ATTRS = ('_returns',)


class Params(object):
    def __init__(self, args, kwargs):
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        params = []
        for arg in self.args:
            params.append(repr(arg))
        for item in sorted(self.kwargs.items()):
            params.append("%s=%r" % item)
        return ', '.join(params)


class Meta(type):
    """ Metaclass that automatically decorates traditional-style methods by
        guessing their API. It also implements the inheritance of the
        :func:`returns` decorators.
    """

    def __new__(meta, name, bases, attrs):
        # dummy parent class to catch overridden methods decorated with 'returns'
        parent = type.__new__(meta, name, bases, {})

        for key, value in list(attrs.items()):
            if not key.startswith('__') and callable(value):
                # make the method inherit from decorators
                value = propagate(getattr(parent, key, None), value)

                if (getattr(value, '_api', None) or '').startswith('cr'):
                    _logger.warning("Deprecated method %s.%s in module %s", name, key, attrs.get('__module__'))

                attrs[key] = value

        return type.__new__(meta, name, bases, attrs)


def attrsetter(attr, value):
    """ Return a function that sets ``attr`` on its argument and returns it. """
    return lambda method: setattr(method, attr, value) or method

def propagate(method1, method2):
    """ Propagate decorators from ``method1`` to ``method2``, and return the
        resulting method.
    """
    if method1:
        for attr in INHERITED_ATTRS:
            if hasattr(method1, attr) and not hasattr(method2, attr):
                setattr(method2, attr, getattr(method1, attr))
    return method2


def constrains(*args):
    """ Decorates a constraint checker. Each argument must be a field name
    used in the check::

        @api.constrains('name', 'description')
        def _check_description(self):
            for record in self:
                if record.name == record.description:
                    raise ValidationError("Fields name and description must be different")

    Invoked on the records on which one of the named fields has been modified.

    Should raise :class:`~odoo.exceptions.ValidationError` if the
    validation failed.

    .. warning::

        ``@constrains`` only supports simple field names, dotted names
        (fields of relational fields e.g. ``partner_id.customer``) are not
        supported and will be ignored

        ``@constrains`` will be triggered only if the declared fields in the
        decorated method are included in the ``create`` or ``write`` call.
        It implies that fields not present in a view will not trigger a call
        during a record creation. A override of ``create`` is necessary to make
        sure a constraint will always be triggered (e.g. to test the absence of
        value).

    """
    return attrsetter('_constrains', args)


def onchange(*args):
    """ Return a decorator to decorate an onchange method for given fields.
        Each argument must be a field name::

            @api.onchange('partner_id')
            def _onchange_partner(self):
                self.message = "Dear %s" % (self.partner_id.name or "")

        In the form views where the field appears, the method will be called
        when one of the given fields is modified. The method is invoked on a
        pseudo-record that contains the values present in the form. Field
        assignments on that record are automatically sent back to the client.

        The method may return a dictionary for changing field domains and pop up
        a warning message, like in the old API::

            return {
                'domain': {'other_id': [('partner_id', '=', partner_id)]},
                'warning': {'title': "Warning", 'message': "What is this?"},
            }


        .. warning::

            ``@onchange`` only supports simple field names, dotted names
            (fields of relational fields e.g. ``partner_id.tz``) are not
            supported and will be ignored
    """
    return attrsetter('_onchange', args)


def depends(*args):
    """ Return a decorator that specifies the field dependencies of a "compute"
        method (for new-style function fields). Each argument must be a string
        that consists in a dot-separated sequence of field names::

            pname = fields.Char(compute='_compute_pname')

            @api.depends('partner_id.name', 'partner_id.is_company')
            def _compute_pname(self):
                for record in self:
                    if record.partner_id.is_company:
                        record.pname = (record.partner_id.name or "").upper()
                    else:
                        record.pname = record.partner_id.name

        One may also pass a single function as argument. In that case, the
        dependencies are given by calling the function with the field's model.
    """
    if args and callable(args[0]):
        args = args[0]
    elif any('id' in arg.split('.') for arg in args):
        raise NotImplementedError("Compute method cannot depend on field 'id'.")
    return attrsetter('_depends', args)


def depends_context(*args):
    """ Return a decorator that specifies the context  dependencies of a non-stored "compute"
        method (for new-style function fields). Each argument must be a string
        that consists in a key in the context::

            price = fields.Float(compute='_compute_product_price')

            @api.depends_context('pricelist')
            def _compute_product_price(self):
                for product in self:
                    if product.env.context.get('pricelist'):
                        pricelist = self.env['product.pricelist'].browse(product.env.context['pricelist'])
                    else:
                        pricelist = self.env['product.pricelist'].get_default_pricelist()
                    product.price = pricelist.get_products_price(product).get(product.id, 0.0)
    """
    return attrsetter('_depends_context', args)


def returns(model, downgrade=None, upgrade=None):
    """ Return a decorator for methods that return instances of ``model``.

        :param model: a model name, or ``'self'`` for the current model

        :param downgrade: a function ``downgrade(self, value, *args, **kwargs)``
            to convert the record-style ``value`` to a traditional-style output

        :param upgrade: a function ``upgrade(self, value, *args, **kwargs)``
            to convert the traditional-style ``value`` to a record-style output

        The arguments ``self``, ``*args`` and ``**kwargs`` are the ones passed
        to the method in the record-style.

        The decorator adapts the method output to the api style: ``id``, ``ids`` or
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
    return attrsetter('_returns', (model, downgrade, upgrade))


def downgrade(method, value, self, args, kwargs):
    """ Convert ``value`` returned by ``method`` on ``self`` to traditional style. """
    spec = getattr(method, '_returns', None)
    if not spec:
        return value
    _, convert, _ = spec
    if convert and len(getargspec(convert).args) > 1:
        return convert(self, value, *args, **kwargs)
    elif convert:
        return convert(value)
    else:
        return value.ids


def split_context(method, args, kwargs):
    """ Extract the context from a pair of positional and keyword arguments.
        Return a triple ``context, args, kwargs``.
    """
    return kwargs.pop('context', None), args, kwargs


def model(method):
    """ Decorate a record-style method where ``self`` is a recordset, but its
        contents is not relevant, only the model is. Such a method::

            @api.model
            def method(self, args):
                ...

        may be called in both record and traditional styles, like::

            # recs = model.browse(cr, uid, ids, context)
            recs.method(args)

            model.method(cr, uid, args, context=context)

        Notice that no ``ids`` are passed to the method in the traditional style.
    """
    if method.__name__ == 'create':
        return model_create_single(method)
    method._api = 'model'
    return method


_create_logger = logging.getLogger(__name__ + '.create')


def _model_create_single(create, self, arg):
    # 'create' expects a dict and returns a record
    if isinstance(arg, Mapping):
        return create(self, arg)
    if len(arg) > 1:
        _create_logger.debug("%s.create() called with %d dicts", self, len(arg))
    return self.browse().concat(*(create(self, vals) for vals in arg))


def model_create_single(method):
    """ Decorate a method that takes a dictionary and creates a single record.
        The method may be called with either a single dict or a list of dicts::

            record = model.create(vals)
            records = model.create([vals, ...])
    """
    wrapper = decorate(method, _model_create_single)
    wrapper._api = 'model_create'
    return wrapper


def _model_create_multi(create, self, arg):
    # 'create' expects a list of dicts and returns a recordset
    if isinstance(arg, Mapping):
        return create(self, [arg])
    return create(self, arg)


def model_create_multi(method):
    """ Decorate a method that takes a list of dictionaries and creates multiple
        records. The method may be called with either a single dict or a list of
        dicts::

            record = model.create(vals)
            records = model.create([vals, ...])
    """
    wrapper = decorate(method, _model_create_multi)
    wrapper._api = 'model_create'
    return wrapper


def _call_kw_model(method, self, args, kwargs):
    context, args, kwargs = split_context(method, args, kwargs)
    recs = self.with_context(context or {})
    _logger.debug("call %s.%s(%s)", recs, method.__name__, Params(args, kwargs))
    result = method(recs, *args, **kwargs)
    return downgrade(method, result, recs, args, kwargs)


def _call_kw_model_create(method, self, args, kwargs):
    # special case for method 'create'
    context, args, kwargs = split_context(method, args, kwargs)
    recs = self.with_context(context or {})
    _logger.debug("call %s.%s(%s)", recs, method.__name__, Params(args, kwargs))
    result = method(recs, *args, **kwargs)
    return result.id if isinstance(args[0], Mapping) else result.ids


def _call_kw_multi(method, self, args, kwargs):
    ids, args = args[0], args[1:]
    context, args, kwargs = split_context(method, args, kwargs)
    recs = self.with_context(context or {}).browse(ids)
    _logger.debug("call %s.%s(%s)", recs, method.__name__, Params(args, kwargs))
    result = method(recs, *args, **kwargs)
    return downgrade(method, result, recs, args, kwargs)


def call_kw(model, name, args, kwargs):
    """ Invoke the given method ``name`` on the recordset ``model``. """
    method = getattr(type(model), name)
    api = getattr(method, '_api', None)
    if api == 'model':
        result = _call_kw_model(method, model, args, kwargs)
    elif api == 'model_create':
        result = _call_kw_model_create(method, model, args, kwargs)
    else:
        result = _call_kw_multi(method, model, args, kwargs)
    model.recompute()
    return result


class Environment(Mapping):
    """ An environment wraps data for ORM records:

        - :attr:`cr`, the current database cursor;
        - :attr:`uid`, the current user id;
        - :attr:`context`, the current context dictionary;
        - :attr:`su`, whether in superuser mode.

        It provides access to the registry by implementing a mapping from model
        names to new api models. It also holds a cache for records, and a data
        structure to manage recomputations.
    """
    _local = Local()

    @classproperty
    def envs(cls):
        return cls._local.environments

    @classmethod
    @contextmanager
    def manage(cls):
        """ Context manager for a set of environments. """
        if hasattr(cls._local, 'environments'):
            yield
        else:
            try:
                cls._local.environments = Environments()
                yield
            finally:
                release_local(cls._local)

    @classmethod
    def reset(cls):
        """ Clear the set of environments.
            This may be useful when recreating a registry inside a transaction.
        """
        cls._local.environments = Environments()

    def __new__(cls, cr, uid, context, su=False):
        if uid == SUPERUSER_ID:
            su = True
        assert context is not None
        args = (cr, uid, context, su)

        # if env already exists, return it
        env, envs = None, cls.envs
        for env in envs:
            if env.args == args:
                return env

        # otherwise create environment, and add it in the set
        self = object.__new__(cls)
        args = (cr, uid, frozendict(context), su)
        self.cr, self.uid, self.context, self.su = self.args = args
        self.registry = Registry(cr.dbname)
        self.cache = envs.cache
        self._protected = StackMap()                # {field: ids, ...}
        self.all = envs
        envs.add(self)
        return self

    #
    # Mapping methods
    #

    def __contains__(self, model_name):
        """ Test whether the given model exists. """
        return model_name in self.registry

    def __getitem__(self, model_name):
        """ Return an empty recordset from the given model. """
        return self.registry[model_name]._browse(self, (), ())

    def __iter__(self):
        """ Return an iterator on model names. """
        return iter(self.registry)

    def __len__(self):
        """ Return the size of the model registry. """
        return len(self.registry)

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other

    def __hash__(self):
        return object.__hash__(self)

    def __call__(self, cr=None, user=None, context=None, su=None):
        """ Return an environment based on ``self`` with modified parameters.

            :param cr: optional database cursor to change the current cursor
            :param user: optional user/user id to change the current user
            :param context: optional context dictionary to change the current context
            :param su: optional boolean to change the superuser mode
        """
        cr = self.cr if cr is None else cr
        uid = self.uid if user is None else int(user)
        context = self.context if context is None else context
        su = (user is None and self.su) if su is None else su
        return Environment(cr, uid, context, su)

    def ref(self, xml_id, raise_if_not_found=True):
        """ return the record corresponding to the given ``xml_id`` """
        return self['ir.model.data'].xmlid_to_object(xml_id, raise_if_not_found=raise_if_not_found)

    def is_superuser(self):
        """ Return whether the environment is in superuser mode. """
        return self.su

    def is_admin(self):
        """ Return whether the current user has group "Access Rights", or is in
            superuser mode. """
        return self.su or self.user._is_admin()

    def is_system(self):
        """ Return whether the current user has group "Settings", or is in
            superuser mode. """
        return self.su or self.user._is_system()

    @property
    def user(self):
        """ return the current user (as an instance) """
        return self(su=True)['res.users'].browse(self.uid)

    @property
    def company(self):
        """ return the company in which the user is logged in (as an instance) """
        try:
            company_id = int(self.context.get('allowed_company_ids')[0])
            if company_id in self.user.company_ids.ids:
                return self['res.company'].browse(company_id)
            return self.user.company_id
        except Exception:
            return self.user.company_id

    @property
    def companies(self):
        """ return a recordset of the enabled companies by the user """
        try:  # In case the user tries to bidouille the url (eg: cids=1,foo,bar)
            allowed_company_ids = self.context.get('allowed_company_ids')
            # Prevent the user to enable companies for which he doesn't have any access
            users_company_ids = self.user.company_ids.ids
            allowed_company_ids = [company_id for company_id in allowed_company_ids if company_id in users_company_ids]
        except Exception:
            # By setting the default companies to all user companies instead of the main one
            # we save a lot of potential trouble in all "out of context" calls, such as
            # /mail/redirect or /web/image, etc. And it is not unsafe because the user does
            # have access to these other companies. The risk of exposing foreign records
            # (wrt to the context) is low because all normal RPCs will have a proper
            # allowed_company_ids.
            # Examples:
            #   - when printing a report for several records from several companies
            #   - when accessing to a record from the notification email template
            #   - when loading an binary image on a template
            allowed_company_ids = self.user.company_ids.ids
        return self['res.company'].browse(allowed_company_ids)

    @property
    def lang(self):
        """ return the current language code """
        return self.context.get('lang')

    def clear(self):
        """ Clear all record caches, and discard all fields to recompute.
            This may be useful when recovering from a failed ORM operation.
        """
        self.cache.invalidate()
        self.all.todo.clear()
        # DLE P17: needs to empty towrite on exception/rollback,
        # otherwise there are pending write transaction which make no sense after the rollback/exception occured.
        self.all.towrite.clear()

    @contextmanager
    def clear_upon_failure(self):
        """ Context manager that clears the environments (caches and fields to
            recompute) upon exception.
        """
        # DLE P14: Not really sure about this one.
        # Basically it's for the self.assertRaises of tests,
        # which can happen in the middle of a test, and it should not rollback the transaction.
        # Before it was enough to empty the todo and invalidate the cache, but now
        # that the computation is done when necessary, the todo list and to write list must be preserved.
        # The only way I see to do that is to copy the cache, todo and towrite somehow, and to apply it back after the "With"
        # test `test_auto_join`
        # with self.assertRaises(NotImplementedError):
        #     partner_obj.search([('category_id.name', '=', 'foo')])
        todo = dict(self.all.todo)
        towrite = copy.deepcopy(self.all.towrite)
        try:
            yield
        except Exception:
            self.clear()
            self.all.todo = todo
            self.all.towrite = towrite
            raise

    def protected(self, field):
        """ Return the recordset for which ``field`` should not be invalidated or recomputed. """
        return self[field.model_name].browse(self._protected.get(field, ()))

    @contextmanager
    def protecting(self, what, records=None):
        """ Prevent the invalidation or recomputation of fields on records.
            The parameters are either:
             - ``what`` a collection of fields and ``records`` a recordset, or
             - ``what`` a collection of pairs ``(fields, records)``.
        """
        protected = self._protected
        try:
            protected.pushmap()
            what = what if records is None else [(what, records)]
            for fields, records in what:
                for field in fields:
                    ids = protected.get(field, frozenset())
                    protected[field] = ids.union(records._ids)
            yield
        finally:
            protected.popmap()

    def field_todo(self, field):
        """ Return a recordset with all records to recompute for ``field``. """
        rec_lists = self.all.todo.get(field, ())
        if not rec_lists:
            return ()
        result = rec_lists[0]
        for records in rec_lists[1:]:
            result += records
        return result

    def check_todo(self, field, record):
        """ Check whether ``field`` must be recomputed on ``record``, and if so,
            return the corresponding recordset to recompute.
        """
        for recs in self.all.todo.get(field, []):
            if recs & record:
                return recs

    def add_todo(self, field, records):
        """ Mark ``field`` to be recomputed on ``records``, return newly added records. """
        if not records:
            return records
        recs_list = self.all.todo.setdefault(field, [])
        result = records
        for i, recs in enumerate(recs_list):
            if recs.env == records.env:
                # only add records if not already in the recordset, much much
                # cheaper in case recs is big and records is a singleton
                # already present
                result -= recs_list[i]
                try:
                    if not records <= recs:
                        recs_list[i] |= result
                    break
                except TypeError:
                    # same field of another object already exists
                    pass
        else:
            recs_list.append(records)
        return result

    # FP NOTE: why is this so complex, rewrite it?
    def remove_todo(self, field, records):
        """ Mark ``field`` as recomputed on ``records``. """
        try:
            recs_list = [recs - records for recs in self.all.todo.pop(field, [])]
        except TypeError:
            recs_list = []
        recs_list = [r for r in recs_list if r]
        if recs_list:
            self.all.todo[field] = recs_list

    def has_todo(self):
        """ Return whether some fields must be recomputed. """
        return bool(self.all.todo)

    def get_todo(self):
        """ Return a pair ``(field, records)`` to recompute.
            The field is such that none of its dependencies must be recomputed.
        """
        field = next(iter(self.all.todo))
        return field

    @property
    def recompute(self):
        return self.all.recompute

    @contextmanager
    def norecompute(self):
        tmp = self.all.recompute
        self.all.recompute = False
        try:
            yield
        finally:
            self.all.recompute = tmp


class Environments(object):
    """ A common object for all environments in a request. """
    def __init__(self):
        self.envs = WeakSet()           # weak set of environments
        self.cache = Cache()            # cache for all records
        self.todo = {}                  # recomputations {field: [records]}  FP NOTE: should be renamed to "tocompute"
        self.recompute = True
        self.towrite = defaultdict(lambda : defaultdict(dict))  # {model: {id: {field: value}}}

    def add(self, env):
        """ Add the environment ``env``. """
        self.envs.add(env)

    def __iter__(self):
        """ Iterate over environments. """
        return iter(self.envs)


class Cache(object):
    """ Implementation of the cache of records. """
    def __init__(self):
        # {field: {record_id: value}}
        self._data = defaultdict(dict)

    def _get_context_key(self, env, field):
        return tuple(env.context.get(key) for key in (field.depends_context or []))

    def contains(self, record, field):
        """ Return whether ``record`` has a value for ``field``. """
        if field.depends_context:
            key = self._get_context_key(record.env, field)
            return key in self._data.get(field, {}).get(record.id, {})
        return record.id in self._data.get(field, ())

    def get_all_values(self, record, field):
        """ Return the value of ``field`` for ``record``. """
        # DLE P7: Dictionary changed of size during iteration
        if field.depends_context:
            key = self._get_context_key(record.env, field)
            return self._data.get(field, {}).get(key, {}).values()
        return self._data.get(field, {}).values()

    def get(self, record, field):
        """ Return the value of ``field`` for ``record``. """
        try:
            value = self._data[field][record._ids[0]]
            if field.depends_context:
                key = self._get_context_key(record.env, field)
                value = value[key]
        except KeyError:
            raise CacheMiss(record, field)

        return value.get() if isinstance(value, SpecialValue) else value

    def set(self, record, field, value):
        """ Set the value of ``field`` for ``record``. """
        if field.depends_context:
            key = self._get_context_key(record.env, field)
            self._data[field].setdefault(record._ids[0], {})[key] = value
        else:
            self._data[field][record._ids[0]] = value

    def update(self, records, field, values):
        """ Set the values of ``field`` for several ``records``. """
        if field.depends_context:
            key = self._get_context_key(records.env, field)
            self._data[field].update(zip(records._ids, map(lambda e: {key: e}, values)))
        else:
            self._data[field].update(zip(records._ids, values))

    def remove(self, record, field):
        """ Remove the value of ``field`` for ``record``. """
        try:
            del self._data[field][record.id]
        except KeyError:
            pass

    def contains_value(self, record, field):
        """ Return whether ``record`` has a regular value for ``field``. """
        if field.depends_context:
            key = self._get_context_key(record.env, field)
            value = self._data[field].get(record.id, {}).get(key, SpecialValue(None))
        else:
            value = self._data[field].get(record.id, SpecialValue(None))
        return not isinstance(value, SpecialValue)

    def get_value(self, record, field, default=None):
        """ Return the regular value of ``field`` for ``record``. """
        if field.depends_context:
            key = self._get_context_key(record.env, field)
            value = self._data[field].get(record.id, {}).get(key, SpecialValue(None))
        else:
            value = self._data[field].get(record.id, SpecialValue(None))
        return default if isinstance(value, SpecialValue) else value

    def get_values(self, records, field, default=None):
        """ Return the regular values of ``field`` for ``records``. """
        field_cache = self._data[field]
        key = self._get_context_key(records.env, field) if field.depends_context else None
        for record_id in records._ids:
            if key:
                value = field_cache.get(record_id, {}).get(key, SpecialValue(None))
            else:
                value = field_cache.get(record_id, SpecialValue(None))
            yield default if isinstance(value, SpecialValue) else value

    def get_special(self, record, field, default=None):
        """ Return the special value of ``field`` for ``record``. """
        if field.depends_context:
            key = self._get_context_key(record.env, field)
            value = self._data[field].get(record.id, {}).get(key)
        else:
            value = self._data[field].get(record.id)
        return value.get if isinstance(value, SpecialValue) else default

    def set_special(self, record, field, getter):
        """ Set the value of ``field`` for ``record`` to return ``getter()``. """
        if field.depends_context:
            key = self._get_context_key(record.env, field)
            self._data[field].setdefault(record.id, {})[key] = SpecialValue(getter)
        else:
            self._data[field][record.id] = SpecialValue(getter)

    def set_failed(self, records, fields, exception):
        """ Mark ``fields`` on ``records`` with the given exception. """
        def getter():
            raise exception
        for field in fields:
            for record in records:
                self.set_special(record, field, getter)

    def get_fields(self, record):
        """ Return the fields with a value for ``record``. """
        for name, field in record._fields.items():
            values = self._data.get(field, ())
            key = self._get_context_key(record.env, field) if field.depends_context else None
            if name != 'id' and record.id in values and (not key or key in values[record.id]):
                yield field

    def get_records(self, model, field):
        """ Return the records of ``model`` that have a value for ``field``. """
        ids = list(self._data[field])
        return model.browse(ids)

    def get_present_records(self, records, field):
        """ Return the subset of ``records`` that have a value for ``field``. """
        ids = self._data[field]
        return records.browse([it for it in records._ids if it in ids])

    def get_missing_ids(self, records, field):
        """ Return the ids of ``records`` that have no value for ``field``. """
        field_cache = self._data[field]
        for record_id in records._ids:
            if record_id not in field_cache:
                yield record_id

    def copy(self, records, env):
        """ Copy the cache of ``records`` to ``env``. """
        pass

    def invalidate(self, spec=None):
        """ Invalidate the cache, partially or totally depending on ``spec``. """
        if spec is None:
            self._data.clear()
        elif spec:
            for field, ids in spec:
                if ids is None:
                    self._data.pop(field, None)
                else:
                    field_cache = self._data.get(field)
                    if field_cache:
                        for id in ids:
                            field_cache.pop(id, None)

    def check(self, env):
        """ Check the consistency of the cache for the given environment. """
        # flush fields to be recomputed before evaluating the cache
        env['res.partner'].recompute()

        # make a full copy of the cache, and invalidate it
        dump = defaultdict(dict)
        key_cache = self._data
        for field, field_cache in key_cache.items():
            for record_id, value in field_cache.items():
                if record_id:
                    dump[field][record_id] = value

        self.invalidate()

        # re-fetch the records, and compare with their former cache
        invalids = []
        for field, field_dump in dump.items():
            records = env[field.model_name].browse(field_dump)
            for record in records:
                try:
                    cached = field_dump[record.id]
                    cached = cached.get() if isinstance(cached, SpecialValue) else cached
                    if field.depends_context:
                        key = self._get_context_key(env, field)
                        cached = cached[key]
                    value = field.convert_to_record(cached, record)
                    fetched = record[field.name]
                    if fetched != value:
                        info = {'cached': value, 'fetched': fetched}
                        invalids.append((record, field, info))
                except (AccessError, MissingError):
                    pass

        if invalids:
            raise UserError('Invalid cache for fields\n' + pformat(invalids))


class SpecialValue(object):
    """ Wrapper for a function to get the cached value of a field. """
    __slots__ = ['get']

    def __init__(self, getter):
        self.get = getter


# keep those imports here in order to handle cyclic dependencies correctly
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError, AccessError, MissingError
from odoo.modules.registry import Registry
