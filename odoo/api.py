# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""The Odoo API module defines Odoo Environments and method decorators.

.. todo:: Document this module
"""

__all__ = [
    'Environment',
    'Meta',
    'model',
    'constrains', 'depends', 'onchange', 'returns',
    'call_kw',
]

import logging
import warnings
import operator
from collections import defaultdict
from collections.abc import Mapping
from contextlib import contextmanager
from inspect import signature
from pprint import pformat
from weakref import WeakSet

try:
    from decorator import decoratorx as decorator
except ImportError:
    from decorator import decorator

from .exceptions import AccessError
from .tools import frozendict, lazy_property, OrderedSet, Query, SQL, StackMap
from .tools.translate import _

_logger = logging.getLogger(__name__)

# The following attributes are used, and reflected on wrapping methods:
#  - method._constrains: set by @constrains, specifies constraint dependencies
#  - method._depends: set by @depends, specifies compute dependencies
#  - method._returns: set by @returns, specifies return model
#  - method._onchange: set by @onchange, specifies onchange fields
#  - method.clear_cache: set by @ormcache, used to clear the cache
#  - method._ondelete: set by @ondelete, used to raise errors for unlink operations
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
    """Decorate a constraint checker.

    Each argument must be a field name used in the check::

        @api.constrains('name', 'description')
        def _check_description(self):
            for record in self:
                if record.name == record.description:
                    raise ValidationError("Fields name and description must be different")

    Invoked on the records on which one of the named fields has been modified.

    Should raise :exc:`~odoo.exceptions.ValidationError` if the
    validation failed.

    .. warning::

        ``@constrains`` only supports simple field names, dotted names
        (fields of relational fields e.g. ``partner_id.customer``) are not
        supported and will be ignored.

        ``@constrains`` will be triggered only if the declared fields in the
        decorated method are included in the ``create`` or ``write`` call.
        It implies that fields not present in a view will not trigger a call
        during a record creation. A override of ``create`` is necessary to make
        sure a constraint will always be triggered (e.g. to test the absence of
        value).

    One may also pass a single function as argument.  In that case, the field
    names are given by calling the function with a model instance.

    """
    if args and callable(args[0]):
        args = args[0]
    return attrsetter('_constrains', args)


def ondelete(*, at_uninstall):
    """
    Mark a method to be executed during :meth:`~odoo.models.BaseModel.unlink`.

    The goal of this decorator is to allow client-side errors when unlinking
    records if, from a business point of view, it does not make sense to delete
    such records. For instance, a user should not be able to delete a validated
    sales order.

    While this could be implemented by simply overriding the method ``unlink``
    on the model, it has the drawback of not being compatible with module
    uninstallation. When uninstalling the module, the override could raise user
    errors, but we shouldn't care because the module is being uninstalled, and
    thus **all** records related to the module should be removed anyway.

    This means that by overriding ``unlink``, there is a big chance that some
    tables/records may remain as leftover data from the uninstalled module. This
    leaves the database in an inconsistent state. Moreover, there is a risk of
    conflicts if the module is ever reinstalled on that database.

    Methods decorated with ``@ondelete`` should raise an error following some
    conditions, and by convention, the method should be named either
    ``_unlink_if_<condition>`` or ``_unlink_except_<not_condition>``.

    .. code-block:: python

        @api.ondelete(at_uninstall=False)
        def _unlink_if_user_inactive(self):
            if any(user.active for user in self):
                raise UserError("Can't delete an active user!")

        # same as above but with _unlink_except_* as method name
        @api.ondelete(at_uninstall=False)
        def _unlink_except_active_user(self):
            if any(user.active for user in self):
                raise UserError("Can't delete an active user!")

    :param bool at_uninstall: Whether the decorated method should be called if
        the module that implements said method is being uninstalled. Should
        almost always be ``False``, so that module uninstallation does not
        trigger those errors.

    .. danger::
        The parameter ``at_uninstall`` should only be set to ``True`` if the
        check you are implementing also applies when uninstalling the module.

        For instance, it doesn't matter if when uninstalling ``sale``, validated
        sales orders are being deleted because all data pertaining to ``sale``
        should be deleted anyway, in that case ``at_uninstall`` should be set to
        ``False``.

        However, it makes sense to prevent the removal of the default language
        if no other languages are installed, since deleting the default language
        will break a lot of basic behavior. In this case, ``at_uninstall``
        should be set to ``True``.
    """
    return attrsetter('_ondelete', at_uninstall)


def onchange(*args):
    """Return a decorator to decorate an onchange method for given fields.

    In the form views where the field appears, the method will be called
    when one of the given fields is modified. The method is invoked on a
    pseudo-record that contains the values present in the form. Field
    assignments on that record are automatically sent back to the client.

    Each argument must be a field name::

        @api.onchange('partner_id')
        def _onchange_partner(self):
            self.message = "Dear %s" % (self.partner_id.name or "")

    .. code-block:: python

        return {
            'warning': {'title': "Warning", 'message': "What is this?", 'type': 'notification'},
        }

    If the type is set to notification, the warning will be displayed in a notification.
    Otherwise it will be displayed in a dialog as default.

    .. warning::

        ``@onchange`` only supports simple field names, dotted names
        (fields of relational fields e.g. ``partner_id.tz``) are not
        supported and will be ignored

    .. danger::

        Since ``@onchange`` returns a recordset of pseudo-records,
        calling any one of the CRUD methods
        (:meth:`create`, :meth:`read`, :meth:`write`, :meth:`unlink`)
        on the aforementioned recordset is undefined behaviour,
        as they potentially do not exist in the database yet.

        Instead, simply set the record's field like shown in the example
        above or call the :meth:`update` method.

    .. warning::

        It is not possible for a ``one2many`` or ``many2many`` field to modify
        itself via onchange. This is a webclient limitation - see `#2693 <https://github.com/odoo/odoo/issues/2693>`_.

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
    """ Return a decorator that specifies the context dependencies of a
    non-stored "compute" method.  Each argument is a key in the context's
    dictionary::

        price = fields.Float(compute='_compute_product_price')

        @api.depends_context('pricelist')
        def _compute_product_price(self):
            for product in self:
                if product.env.context.get('pricelist'):
                    pricelist = self.env['product.pricelist'].browse(product.env.context['pricelist'])
                else:
                    pricelist = self.env['product.pricelist'].get_default_pricelist()
                product.price = pricelist._get_products_price(product).get(product.id, 0.0)

    All dependencies must be hashable.  The following keys have special
    support:

    * `company` (value in context or current company id),
    * `uid` (current user id and superuser flag),
    * `active_test` (value in env.context or value in field.context).
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
    if convert and len(signature(convert).parameters) > 1:
        return convert(self, value, *args, **kwargs)
    elif convert:
        return convert(value)
    else:
        return value.ids


def split_context(method, args, kwargs):
    """ Extract the context from a pair of positional and keyword arguments.
        Return a triple ``context, args, kwargs``.
    """
    # altering kwargs is a cause of errors, for instance when retrying a request
    # after a serialization error: the retry is done without context!
    kwargs = kwargs.copy()
    return kwargs.pop('context', None), args, kwargs


def autovacuum(method):
    """
    Decorate a method so that it is called by the daily vacuum cron job (model
    ``ir.autovacuum``).  This is typically used for garbage-collection-like
    tasks that do not deserve a specific cron job.
    """
    assert method.__name__.startswith('_'), "%s: autovacuum methods must be private" % method.__name__
    method._autovacuum = True
    return method


def model(method):
    """ Decorate a record-style method where ``self`` is a recordset, but its
        contents is not relevant, only the model is. Such a method::

            @api.model
            def method(self, args):
                ...

    """
    if method.__name__ == 'create':
        return model_create_single(method)
    method._api = 'model'
    return method


_create_logger = logging.getLogger(__name__ + '.create')


@decorator
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
    _create_logger.warning("The model %s is not overriding the create method in batch", method.__module__)
    wrapper = _model_create_single(method) # pylint: disable=no-value-for-parameter
    wrapper._api = 'model_create'
    return wrapper


@decorator
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
    wrapper = _model_create_multi(method) # pylint: disable=no-value-for-parameter
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
    model.env.flush_all()
    return result


class Environment(Mapping):
    """ The environment stores various contextual data used by the ORM:

    - :attr:`cr`: the current database cursor (for database queries);
    - :attr:`uid`: the current user id (for access rights checks);
    - :attr:`context`: the current context dictionary (arbitrary metadata);
    - :attr:`su`: whether in superuser mode.

    It provides access to the registry by implementing a mapping from model
    names to models. It also holds a cache for records, and a data
    structure to manage recomputations.
    """
    def reset(self):
        """ Reset the transaction, see :meth:`Transaction.reset`. """
        self.transaction.reset()

    def __new__(cls, cr, uid, context, su=False):
        if uid == SUPERUSER_ID:
            su = True
        assert context is not None
        args = (cr, uid, context, su)

        # determine transaction object
        transaction = cr.transaction
        if transaction is None:
            transaction = cr.transaction = Transaction(Registry(cr.dbname))

        # if env already exists, return it
        for env in transaction.envs:
            if env.args == args:
                return env

        # otherwise create environment, and add it in the set
        self = object.__new__(cls)
        args = (cr, uid, frozendict(context), su)
        self.cr, self.uid, self.context, self.su = self.args = args

        self.transaction = self.all = transaction
        self.registry = transaction.registry
        self.cache = transaction.cache
        self._cache_key = {}                    # memo {field: cache_key}
        self._protected = transaction.protected
        transaction.envs.add(self)
        return self

    #
    # Mapping methods
    #

    def __contains__(self, model_name):
        """ Test whether the given model exists. """
        return model_name in self.registry

    def __getitem__(self, model_name):
        """ Return an empty recordset from the given model. """
        return self.registry[model_name](self, (), ())

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
        :type cursor: :class:`~odoo.sql_db.Cursor`
        :param user: optional user/user id to change the current user
        :type user: int or :class:`res.users record<~odoo.addons.base.models.res_users.Users>`
        :param dict context: optional context dictionary to change the current context
        :param bool su: optional boolean to change the superuser mode
        :returns: environment with specified args (new or existing one)
        :rtype: :class:`Environment`
        """
        cr = self.cr if cr is None else cr
        uid = self.uid if user is None else int(user)
        context = self.context if context is None else context
        su = (user is None and self.su) if su is None else su
        return Environment(cr, uid, context, su)

    def ref(self, xml_id, raise_if_not_found=True):
        """ Return the record corresponding to the given ``xml_id``.

        :param str xml_id: record xml_id, under the format ``<module.id>``
        :param bool raise_if_not_found: whether the method should raise if record is not found
        :returns: Found record or None
        :raise ValueError: if record wasn't found and ``raise_if_not_found`` is True
        """
        res_model, res_id = self['ir.model.data']._xmlid_to_res_model_res_id(
            xml_id, raise_if_not_found=raise_if_not_found
        )

        if res_model and res_id:
            record = self[res_model].browse(res_id)
            if record.exists():
                return record
            if raise_if_not_found:
                raise ValueError('No record found for unique ID %s. It may have been deleted.' % (xml_id))
        return None

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

    @lazy_property
    def user(self):
        """Return the current user (as an instance).

        :returns: current user - sudoed
        :rtype: :class:`res.users record<~odoo.addons.base.models.res_users.Users>`"""
        return self(su=True)['res.users'].browse(self.uid)

    @lazy_property
    def company(self):
        """Return the current company (as an instance).

        If not specified in the context (`allowed_company_ids`),
        fallback on current user main company.

        :raise AccessError: invalid or unauthorized `allowed_company_ids` context key content.
        :return: current company (default=`self.user.company_id`), with the current environment
        :rtype: :class:`res.company record<~odoo.addons.base.models.res_company.Company>`

        .. warning::

            No sanity checks applied in sudo mode!
            When in sudo mode, a user can access any company,
            even if not in his allowed companies.

            This allows to trigger inter-company modifications,
            even if the current user doesn't have access to
            the targeted company.
        """
        company_ids = self.context.get('allowed_company_ids', [])
        if company_ids:
            if not self.su:
                user_company_ids = self.user._get_company_ids()
                if set(company_ids) - set(user_company_ids):
                    raise AccessError(_("Access to unauthorized or invalid companies."))
            return self['res.company'].browse(company_ids[0])
        return self.user.company_id.with_env(self)

    @lazy_property
    def companies(self):
        """Return a recordset of the enabled companies by the user.

        If not specified in the context(`allowed_company_ids`),
        fallback on current user companies.

        :raise AccessError: invalid or unauthorized `allowed_company_ids` context key content.
        :return: current companies (default=`self.user.company_ids`), with the current environment
        :rtype: :class:`res.company recordset<~odoo.addons.base.models.res_company.Company>`

        .. warning::

            No sanity checks applied in sudo mode !
            When in sudo mode, a user can access any company,
            even if not in his allowed companies.

            This allows to trigger inter-company modifications,
            even if the current user doesn't have access to
            the targeted company.
        """
        company_ids = self.context.get('allowed_company_ids', [])
        user_company_ids = self.user._get_company_ids()
        if company_ids:
            if not self.su:
                if set(company_ids) - set(user_company_ids):
                    raise AccessError(_("Access to unauthorized or invalid companies."))
            return self['res.company'].browse(company_ids)
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
        return self['res.company'].browse(user_company_ids)

    @property
    def lang(self):
        """Return the current language code.

        :rtype: str
        """
        lang = self.context.get('lang')
        # _lang_get_id is cached and used to validate lang before return,
        # because 'env.lang' may be injected in SQL queries
        return lang if lang and self['res.lang']._lang_get_id(lang) else None

    def clear(self):
        """ Clear all record caches, and discard all fields to recompute.
            This may be useful when recovering from a failed ORM operation.
        """
        lazy_property.reset_all(self)
        self.transaction.clear()

    def invalidate_all(self, flush=True):
        """ Invalidate the cache of all records.

        :param flush: whether pending updates should be flushed before invalidation.
            It is ``True`` by default, which ensures cache consistency.
            Do not use this parameter unless you know what you are doing.
        """
        if flush:
            self.flush_all()
        self.cache.invalidate()

    def _recompute_all(self):
        """ Process all pending computations. """
        for field in list(self.fields_to_compute()):
            self[field.model_name]._recompute_field(field)

    def flush_all(self):
        """ Flush all pending computations and updates to the database. """
        self._recompute_all()
        for model_name in OrderedSet(field.model_name for field in self.cache.get_dirty_fields()):
            self[model_name].flush_model()

    def is_protected(self, field, record):
        """ Return whether `record` is protected against invalidation or
            recomputation for `field`.
        """
        return record.id in self._protected.get(field, ())

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
            if records is not None:  # Handle first signature
                ids_by_field = {field: records._ids for field in what}
            else:  # Handle second signature
                ids_by_field = defaultdict(list)
                for fields, what_records in what:
                    for field in fields:
                        ids_by_field[field].extend(what_records._ids)

            for field, rec_ids in ids_by_field.items():
                ids = protected.get(field)
                protected[field] = ids.union(rec_ids) if ids else frozenset(rec_ids)
            yield
        finally:
            protected.popmap()

    def fields_to_compute(self):
        """ Return a view on the field to compute. """
        return self.all.tocompute.keys()

    def records_to_compute(self, field):
        """ Return the records to compute for ``field``. """
        ids = self.all.tocompute.get(field, ())
        return self[field.model_name].browse(ids)

    def is_to_compute(self, field, record):
        """ Return whether ``field`` must be computed on ``record``. """
        return record.id in self.all.tocompute.get(field, ())

    def not_to_compute(self, field, records):
        """ Return the subset of ``records`` for which ``field`` must not be computed. """
        ids = self.all.tocompute.get(field, ())
        return records.browse(id_ for id_ in records._ids if id_ not in ids)

    def add_to_compute(self, field, records):
        """ Mark ``field`` to be computed on ``records``. """
        if not records:
            return records
        assert field.store and field.compute, "Cannot add to recompute no-store or no-computed field"
        self.all.tocompute[field].update(records._ids)

    def remove_to_compute(self, field, records):
        """ Mark ``field`` as computed on ``records``. """
        if not records:
            return
        ids = self.all.tocompute.get(field, None)
        if ids is None:
            return
        ids.difference_update(records._ids)
        if not ids:
            del self.all.tocompute[field]

    @contextmanager
    def norecompute(self):
        """ Deprecated: It does nothing, recomputation is delayed by default. """
        warnings.warn("`norecompute` is useless. Deprecated since 17.0.", DeprecationWarning, 2)
        yield

    def cache_key(self, field):
        """ Return the cache key of the given ``field``. """
        try:
            return self._cache_key[field]

        except KeyError:
            def get(key, get_context=self.context.get):
                if key == 'company':
                    return self.company.id
                elif key == 'uid':
                    return (self.uid, self.su)
                elif key == 'lang':
                    return get_context('lang') or None
                elif key == 'active_test':
                    return get_context('active_test', field.context.get('active_test', True))
                else:
                    val = get_context(key)
                    if type(val) is list:
                        val = tuple(val)
                    try:
                        hash(val)
                    except TypeError:
                        raise TypeError(
                            "Can only create cache keys from hashable values, "
                            "got non-hashable value {!r} at context key {!r} "
                            "(dependency of field {})".format(val, key, field)
                        ) from None  # we don't need to chain the exception created 2 lines above
                    else:
                        return val

            result = tuple(get(key) for key in self.registry.field_depends_context[field]) or None
            self._cache_key[field] = result
            return result


class Transaction:
    """ A object holding ORM data structures for a transaction. """
    def __init__(self, registry):
        self.registry = registry
        # weak set of environments
        self.envs = WeakSet()
        self.envs.data = OrderedSet()  # make the weakset OrderedWeakSet
        # cache for all records
        self.cache = Cache()
        # fields to protect {field: ids}
        self.protected = StackMap()
        # pending computations {field: ids}
        self.tocompute = defaultdict(OrderedSet)

    def flush(self):
        """ Flush pending computations and updates in the transaction. """
        env_to_flush = None
        for env in self.envs:
            if isinstance(env.uid, int) or env.uid is None:
                env_to_flush = env
                if env.uid is not None:
                    break
        if env_to_flush is not None:
            env_to_flush.flush_all()

    def clear(self):
        """ Clear the caches and pending computations and updates in the translations. """
        self.cache.clear()
        self.tocompute.clear()

    def reset(self):
        """ Reset the transaction.  This clears the transaction, and reassigns
            the registry on all its environments.  This operation is strongly
            recommended after reloading the registry.
        """
        self.registry = Registry(self.registry.db_name)
        for env in self.envs:
            env.registry = self.registry
            lazy_property.reset_all(env)
        self.clear()


# sentinel value for optional parameters
class CacheDefault:
    def __bool__(self):
        return False


NOTHING = CacheDefault()
EMPTY_DICT = frozendict()


class Cache:
    """ Implementation of the cache of records.

    The cache can be treated as a three level nested dictionary with dirty flags
    self._data: {field: {context_key: {record_id: cache_value}}}
    self._dirty: {field: set[record_id]}

    The context_key for context-dependent fields is a tuple of their context keys
    from the environment. For non-context-independent fields, the context_key
    is ``None``. For the sake of performance, the cache is first  partitioned by
    field, then by context_key, then by record_id. This makes some common ORM
    operations pretty fast, like determining which records have a value for a
    given field, or invalidating a given field on all possible records.

    The cache can also mark some entries as "dirty".  Dirty entries essentially
    marks values that are different from the database.  They represent database
    updates that haven't been done yet.  Note that dirty entries only make
    sense for stored fields.

    Note that since the database doesn't have context. The cache value for
    context_key ``None`` reflects the data in the database. When flushing stored
    context-dependent fields, the ORM will only flush the cache value for context_key
    ``None``.
    """

    def __init__(self):
        # field: {context_key: {record_id: value}}}
        self._data = defaultdict(dict)

        # {field: set[record_id]} stores the fields and ids that are changed in the
        # cache, but not yet written in the database; their changed values are
        # in `_data`
        self._dirty = defaultdict(OrderedSet)

    def __repr__(self):
        # for debugging: show the cache content and dirty flags as stars
        data = {}
        for field, field_cache in sorted(self._data.items(), key=lambda item: str(item[0])):
            dirty_ids = self._dirty.get(field, ())
            if field_cache and isinstance(next(iter(field_cache)), tuple):
                data[field] = {
                    key: {
                        Starred(id_) if id_ in dirty_ids else id_: val if field.type != 'binary' else '<binary>'
                        for id_, val in key_cache.items()
                    }
                    for key, key_cache in field_cache.items()
                }
            else:
                data[field] = {
                    Starred(id_) if id_ in dirty_ids else id_: val if field.type != 'binary' else '<binary>'
                    for id_, val in field_cache.items()
                }
        return repr(data)

    def _get_field_cache(self, field, context):
        """ Return the field cache of the given field, but not for modifying it. """
        return self._data.get(field, EMPTY_DICT).get(context, EMPTY_DICT)

    def _set_field_cache(self, field, context):
        """ Return the field cache of the given field for modifying it. """
        return self._data[field].setdefault(context, {})

    def contains(self, field, context, id_, validator=None):
        """ Return whether ``record`` has a value for ``field``. """
        field_cache = self._get_field_cache(field, context)
        if id_ not in field_cache:
            return False
        if validator:
            return validator(field_cache[id_])
        return True

    def contains_field(self, field):
        """ Return whether ``field`` has a value for at least one record. """
        return any(self._data.get(field, EMPTY_DICT).values())

    def get(self, field, context, id_):
        """ Return the value of ``field`` for ``record``. """
        field_cache = self._get_field_cache(field, context)
        return field_cache.get(id_, NOTHING)

    def set(self, field, context, id_, value, dirty=False, check_dirty=True, setter=None):
        """ Set the value of ``field`` for ``record``.
        One can normally make a clean field dirty but not the other way around.
        Updating a dirty field without ``dirty=True`` is a programming error and
        raises an exception.

        :param dirty: whether ``field`` must be made dirty on ``record`` after
            the update
        :param check_dirty: whether updating a dirty field without making it
            dirty must raise an exception
        :param setter: a function to set the cache
            setter(field_cache, id_, value)
            if not provided, the setter will be logically equivalent to
            dict.__setitem__
        """
        field_cache = self._set_field_cache(field, context)
        if setter:
            setter(field_cache, id_, value)
        else:
            # if condition + key lookup is faster than dict.__setitem__
            field_cache[id_] = value

        if not check_dirty:
            return
        if dirty:
            assert field.column_type and field.store and id_
            self._dirty[field].add(id_)
        elif id_ in self._dirty.get(field, ()):
            _logger.error("cache.set() removing flag dirty on %s.%s", id_, field.name, stack_info=True)

    def update(self, field, context, ids, values, dirty=False, check_dirty=True, updater=None):
        """ Set the values of ``field`` for several ``records``.
        One can normally make a clean field dirty but not the other way around.
        Updating a dirty field without ``dirty=True`` is a programming error and
        raises an exception.

        :param dirty: whether ``field`` must be made dirty on ``record`` after
            the update
        :param check_dirty: whether updating a dirty field without making it
            dirty must raise an exception
        :param updater: a function to update the cache
            updater(field_cache, id_, value)
            if not provided, the updater will be logically equivalent to
            dict.__setitem__
        """
        field_cache = self._set_field_cache(field, context)
        if updater:
            for id_, val in zip(ids, values):
                updater(field_cache, id_, val)
        else:
            field_cache.update(zip(ids, values))

        if not check_dirty:
            return
        if dirty:
            assert field.column_type and field.store and all(ids)
            self._dirty[field].update(ids)
        else:
            dirty_ids = self._dirty.get(field)
            if dirty_ids and not dirty_ids.isdisjoint(ids):
                _logger.error("cache.update() removing flag dirty on %s.%s", str(ids), field.name, stack_info=True)

    def remove(self, field, context, id_):
        """ Remove the value of ``field`` for ``record``. """
        assert id_ not in self._dirty.get(field, ())
        field_cache = self._set_field_cache(field, context)
        field_cache.pop(id_, NOTHING)

    def get_values(self, field, context, ids, getter=None, on_cache_miss=None):
        """ Return the cached values of ``field`` for ``records``.

        :param getter: a function to get the value from cache value
            getter(field_cache, id_, default)
            if not provided, the getter will logically be equivalent to
            lambda field_cache, _id, default: field_cache.get(_id, NOTHING)
        :param on_cache_miss: a function to return value if cache miss
            on_cache_miss(field_cache, id_)
            if not provided, the on_cache_miss will be logically equivalent to
            lambda field_cache, id_: NOTHING
        """
        field_cache = self._get_field_cache(field, context) if on_cache_miss is None else self._set_field_cache(field, context)
        if getter is None:
            getter = dict.get
        if on_cache_miss is None:
            for id_ in ids:
                yield getter(field_cache, id_, NOTHING)
        else:
            for id_ in ids:
                value = getter(field_cache, id_, NOTHING)
                if value is NOTHING:
                    yield on_cache_miss(field_cache, id_)
                else:
                    yield value

    def get_ids_different_from(self, field, context, ids, value, cmp=operator.ne):
        """ Return the subset of ``records`` that has not ``value`` for ``field``.

        :param cmp: a cmp function to return if the cache value is the same as value
            on_cache_miss(cache_value, value)
            if not provided, the on_cache_miss will be logically equivalent to
            operator.ne
        """
        field_cache = self._get_field_cache(field, context)
        return [
            id_
            for id_ in ids
            if (value_ := field_cache.get(id_, NOTHING)) is NOTHING or cmp(value_, value)
        ]

    def get_missing_ids(self, field, context, ids, validator=None):
        """ Return the ids of ``records`` that have no value for ``field``.

        :param validator: a function to check if the cache value is valid
            validator(value)
            if not provided, the validator will be logically equivalent to
            lambda value: True
        """
        field_cache = self._get_field_cache(field, context)
        if validator:
            for id_ in ids:
                value = field_cache.get(id_, NOTHING)
                if value is NOTHING or not validator(value):
                    yield id_
        else:
            for id_ in ids:
                if id_ not in field_cache:
                    yield id_

    def get_dirty_fields(self):
        """ Return the fields that have dirty records in cache. """
        return self._dirty.keys()

    def get_dirty_ids(self, field):
        """ Return the records that for which ``field`` is dirty in cache. """
        return self._dirty.get(field, ())

    def clear_dirty_field(self, field):
        """ Make the given field clean on all records, and return the ids of the
        formerly dirty records for the field.
        """
        return self._dirty.pop(field, ())

    def invalidate(self, spec=None):
        """ Invalidate the cache, partially or totally depending on ``spec``.

        If a field is context-dependent, invalidating it for a given record
        actually invalidates all the values of that field on the record.  In
        other words, the field is invalidated for the record in all
        environments.

        This operation is unsafe by default, and must be used with care.
        Indeed, invalidating a dirty field on a record may lead to an error,
        because doing so drops the value to be written in database.

            spec = [(field, ids), (field, None), ...]
        """
        if spec is None:
            self._data.clear()
        elif spec:
            for field, ids in spec:
                if ids is None:
                    self._data.pop(field, None)
                    continue
                cache = self._data.get(field)
                if not cache:
                    continue
                for field_cache in cache.values():
                    for id_ in ids:
                        field_cache.pop(id_, None)

    def clear(self):
        """ Invalidate the cache and its dirty flags. """
        self._data.clear()
        self._dirty.clear()

    def check(self, env):
        """ Check the consistency of the cache for the given environment. """
        depends_context = env.registry.field_depends_context
        invalids = []

        def process(model, field, field_cache):
            # ignore new records and records to flush
            dirty_ids = self._dirty.get(field, ())
            ids = [id_ for id_ in field_cache if id_ and id_ not in dirty_ids]
            if not ids:
                return

            # select the column for the given ids
            query = Query(env.cr, model._table, model._table_query)
            sql_id = SQL.identifier(model._table, 'id')
            sql_field = model._field_to_sql(model._table, field.name, query)
            if field.type == 'binary' and (
                model.env.context.get('bin_size') or model.env.context.get('bin_size_' + field.name)
            ):
                sql_field = SQL('pg_size_pretty(length(%s)::bigint)', sql_field)
            query.add_where(SQL("%s IN %s", sql_id, tuple(ids)))
            env.cr.execute(query.select(sql_id, sql_field))

            # compare returned values with corresponding values in cache
            for id_, value in env.cr.fetchall():
                cached = field_cache[id_]
                if value == cached or (not value and not cached):
                    continue
                invalids.append((model.browse(id_), field, {'cached': cached, 'fetched': value}))

        for field, field_cache in self._data.items():
            # check column fields only
            if not field.store or not field.column_type or callable(field.translate):
                continue

            model = env[field.model_name]
            if depends_context[field]:
                for context_keys, inner_cache in field_cache.items():
                    context = dict(zip(depends_context[field], context_keys))
                    if 'company' in context:
                        # the cache key 'company' actually comes from context
                        # key 'allowed_company_ids' (see property env.company
                        # and method env.cache_key())
                        context['allowed_company_ids'] = [context.pop('company')]
                    process(model.with_context(context), field, inner_cache)
            else:
                process(model, field, field_cache)

        if invalids:
            _logger.warning("Invalid cache: %s", pformat(invalids))


class Starred:
    """ Simple helper class to ``repr`` a value with a star suffix. """
    __slots__ = ['value']

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"{self.value!r}*"


# keep those imports here in order to handle cyclic dependencies correctly
from odoo import SUPERUSER_ID
from odoo.modules.registry import Registry
