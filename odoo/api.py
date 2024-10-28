# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""The Odoo API module defines Odoo Environments and method decorators.

.. todo:: Document this module
"""
from __future__ import annotations

__all__ = [
    'Environment',
    'Meta',
    'model',
    'constrains', 'depends', 'onchange', 'returns',
    'call_kw',
]

import logging
import warnings
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

from .exceptions import AccessError, UserError, CacheMiss
from .tools import clean_context, frozendict, lazy_property, OrderedSet, Query, SQL
from .tools.translate import get_translation, get_translated_module, LazyGettext
from odoo.tools.misc import StackMap

import typing
if typing.TYPE_CHECKING:
    from collections.abc import Callable
    from odoo.sql_db import BaseCursor
    from odoo.models import BaseModel
    try:
        from typing_extensions import Self  # noqa: F401
    except ImportError:
        from typing import Self  # noqa: F401
    M = typing.TypeVar("M", bound=BaseModel)
else:
    Self = None
    M = typing.TypeVar("M")

DomainType = list[str | tuple[str, str, typing.Any]]
ContextType = Mapping[str, typing.Any]
ValuesType = dict[str, typing.Any]
T = typing.TypeVar('T')

_logger = logging.getLogger(__name__)


class NewId:
    """ Pseudo-ids for new records, encapsulating an optional origin id (actual
        record id) and an optional reference (any value).
    """
    __slots__ = ['origin', 'ref']

    def __init__(self, origin=None, ref=None):
        self.origin = origin
        self.ref = ref

    def __bool__(self):
        return False

    def __eq__(self, other):
        return isinstance(other, NewId) and (
            (self.origin and other.origin and self.origin == other.origin)
            or (self.ref and other.ref and self.ref == other.ref)
        )

    def __hash__(self):
        return hash(self.origin or self.ref or id(self))

    def __repr__(self):
        return (
            "<NewId origin=%r>" % self.origin if self.origin else
            "<NewId ref=%r>" % self.ref if self.ref else
            "<NewId 0x%x>" % id(self)
        )

    def __str__(self):
        if self.origin or self.ref:
            id_part = repr(self.origin or self.ref)
        else:
            id_part = hex(id(self))
        return "NewId_%s" % id_part


IdType: typing.TypeAlias = int | NewId


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

def attrsetter(attr, value):
    """ Return a function that sets ``attr`` on its argument and returns it. """
    return lambda method: setattr(method, attr, value) or method


def propagate(method1, method2):
    """ Propagate decorators from ``method1`` to ``method2``, and return the
        resulting method.
    """
    if method1:
        for attr in ('_returns',):
            if hasattr(method1, attr) and not hasattr(method2, attr):
                setattr(method2, attr, getattr(method1, attr))
    return method2


def constrains(*args: str) -> Callable[[T], T]:
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


def depends(*args: str) -> Callable[[T], T]:
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


def autovacuum(method):
    """
    Decorate a method so that it is called by the daily vacuum cron job (model
    ``ir.autovacuum``).  This is typically used for garbage-collection-like
    tasks that do not deserve a specific cron job.
    """
    assert method.__name__.startswith('_'), "%s: autovacuum methods must be private" % method.__name__
    method._autovacuum = True
    return method


def model(method: T) -> T:
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


def readonly(method: T) -> T:
    """ Decorate a record-style method where ``self.env.cr`` can be a
        readonly cursor when called trough a rpc call.

            @api.readonly
            def method(self, args):
                ...

    """
    method._readonly = True
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


def model_create_single(method: T) -> T:
    """ Decorate a method that takes a dictionary and creates a single record.
        The method may be called with either a single dict or a list of dicts::

            record = model.create(vals)
            records = model.create([vals, ...])
    """
    warnings.warn(
        f"The model {method.__module__} is not overriding the create method in batch",
        DeprecationWarning
    )
    wrapper = _model_create_single(method) # pylint: disable=no-value-for-parameter
    wrapper._api = 'model_create'
    return wrapper


@decorator
def _model_create_multi(create, self, arg):
    # 'create' expects a list of dicts and returns a recordset
    if isinstance(arg, Mapping):
        return create(self, [arg])
    return create(self, arg)


def model_create_multi(method: T) -> T:
    """ Decorate a method that takes a list of dictionaries and creates multiple
        records. The method may be called with either a single dict or a list of
        dicts::

            record = model.create(vals)
            records = model.create([vals, ...])
    """
    wrapper = _model_create_multi(method) # pylint: disable=no-value-for-parameter
    wrapper._api = 'model_create'
    return wrapper


def call_kw(model, name, args, kwargs):
    """ Invoke the given method ``name`` on the recordset ``model``. """
    method = getattr(model, name, None)
    if not method:
        raise AttributeError(f"The method '{name}' does not exist on the model '{model._name}'")
    api = getattr(method, '_api', None)

    if api:
        # @api.model, @api.model_create -> no ids
        recs = model
    else:
        ids, args = args[0], args[1:]
        recs = model.browse(ids)

    # altering kwargs is a cause of errors, for instance when retrying a request
    # after a serialization error: the retry is done without context!
    kwargs = dict(kwargs)
    context = kwargs.pop('context', None) or {}
    recs = recs.with_context(context)

    _logger.debug("call %s.%s(%s)", recs, method.__name__, Params(args, kwargs))
    result = getattr(recs, name)(*args, **kwargs)
    if api == "model_create":
        # special case for method 'create'
        result = result.id if isinstance(args[0], Mapping) else result.ids
    else:
        result = downgrade(method, result, recs, args, kwargs)

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

    cr: BaseCursor
    uid: int
    context: frozendict
    su: bool
    registry: Registry
    cache: Cache
    transaction: Transaction

    def reset(self):
        """ Reset the transaction, see :meth:`Transaction.reset`. """
        self.transaction.reset()

    def __new__(cls, cr, uid, context, su=False, uid_origin=None):
        assert isinstance(cr, BaseCursor)
        if uid == SUPERUSER_ID:
            su = True

        # isinstance(uid, int) is to handle `RequestUID`
        uid_origin = uid_origin or (uid if isinstance(uid, int) else None)
        if uid_origin == SUPERUSER_ID:
            uid_origin = None

        # determine transaction object
        transaction = cr.transaction
        if transaction is None:
            transaction = cr.transaction = Transaction(Registry(cr.dbname))

        # if env already exists, return it
        for env in transaction.envs:
            if (env.cr, env.uid, env.su, env.uid_origin, env.context) == (cr, uid, su, uid_origin, context):
                return env

        # otherwise create environment, and add it in the set
        self = object.__new__(cls)
        self.cr, self.uid, self.su, self.uid_origin = cr, uid, su, uid_origin
        self.context = frozendict(context)
        self.transaction = transaction
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

    def __getitem__(self, model_name: str) -> BaseModel:
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
        if context is None:
            context = clean_context(self.context) if su and not self.su else self.context
        su = (user is None and self.su) if su is None else su
        return Environment(cr, uid, context, su, self.uid_origin)

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
                    raise AccessError(self._("Access to unauthorized or invalid companies."))
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
                    raise AccessError(self._("Access to unauthorized or invalid companies."))
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

    @lazy_property
    def lang(self):
        """Return the current language code.

        :rtype: str
        """
        lang = self.context.get('lang')
        if lang and lang != 'en_US' and not self['res.lang']._get_data(code=lang):
            # cannot translate here because we do not have a valid language
            raise UserError(f'Invalid language code: {lang}')  # pylint: disable
        return lang or None

    @lazy_property
    def _lang(self):
        """Return the technical language code of the current context for **model_terms** translated field

        :rtype: str
        """
        context = self.context
        lang = self.lang or 'en_US'
        if context.get('edit_translations') or context.get('check_translations'):
            lang = '_' + lang
        return lang

    def _(self, source: str | LazyGettext, *args, **kwargs) -> str:
        """Translate the term using current environment's language.

        Usage:

        ```
        self.env._("hello world")  # dynamically get module name
        self.env._("hello %s", "test")
        self.env._(LAZY_TRANSLATION)
        ```

        :param source: String to translate or lazy translation
        :param ...: args or kwargs for templating
        :return: The transalted string
        """
        lang = self.lang or 'en_US'
        if isinstance(source, str):
            assert not (args and kwargs), "Use args or kwargs, not both"
            args = args or kwargs
        elif isinstance(source, LazyGettext):
            # translate a lazy text evaluation
            assert not args and not kwargs, "All args should come from the lazy text"
            return source._translate(lang)
        else:
            raise TypeError(f"Cannot translate {source!r}")
        if lang == 'en_US':
            # we ignore the module as en_US is not translated
            return get_translation('base', 'en_US', source, args)
        try:
            module = get_translated_module(2)
            return get_translation(module, lang, source, args)
        except Exception:  # noqa: BLE001
            _logger.debug('translation went wrong for "%r", skipped', source, exc_info=True)
        return source

    def clear(self):
        """ Clear all record caches, and discard all fields to recompute.
            This may be useful when recovering from a failed ORM operation.
        """
        lazy_property.reset_all(self)
        self._cache_key.clear()
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
        return self.transaction.tocompute.keys()

    def records_to_compute(self, field):
        """ Return the records to compute for ``field``. """
        ids = self.transaction.tocompute.get(field, ())
        return self[field.model_name].browse(ids)

    def is_to_compute(self, field, record):
        """ Return whether ``field`` must be computed on ``record``. """
        return record.id in self.transaction.tocompute.get(field, ())

    def not_to_compute(self, field, records):
        """ Return the subset of ``records`` for which ``field`` must not be computed. """
        ids = self.transaction.tocompute.get(field, ())
        return records.browse(id_ for id_ in records._ids if id_ not in ids)

    def add_to_compute(self, field, records):
        """ Mark ``field`` to be computed on ``records``. """
        if not records:
            return records
        assert field.store and field.compute, "Cannot add to recompute no-store or no-computed field"
        self.transaction.tocompute[field].update(records._ids)

    def remove_to_compute(self, field, records):
        """ Mark ``field`` as computed on ``records``. """
        if not records:
            return
        ids = self.transaction.tocompute.get(field, None)
        if ids is None:
            return
        ids.difference_update(records._ids)
        if not ids:
            del self.transaction.tocompute[field]

    def cache_key(self, field):
        """ Return the cache key of the given ``field``. """
        try:
            return self._cache_key[field]

        except KeyError:
            def get(key, get_context=self.context.get):
                if key == 'company':
                    return self.company.id
                elif key == 'uid':
                    return self.uid if field.compute_sudo else (self.uid, self.su)
                elif key == 'lang':
                    return get_context('lang') or None
                elif key == 'active_test':
                    return get_context('active_test', field.context.get('active_test', True))
                elif key.startswith('bin_size'):
                    return bool(get_context(key))
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

            result = tuple(get(key) for key in self.registry.field_depends_context[field])
            self._cache_key[field] = result
            return result

    def flush_query(self, query: SQL):
        """ Flush all the fields in the metadata of ``query``. """
        fields_to_flush = tuple(query.to_flush)
        if not fields_to_flush:
            return

        fnames_to_flush = defaultdict(OrderedSet)
        for field in fields_to_flush:
            fnames_to_flush[field.model_name].add(field.name)
        for model_name, field_names in fnames_to_flush.items():
            self[model_name].flush_model(field_names)

    def execute_query(self, query: SQL) -> list[tuple]:
        """ Execute the given query, fetch its result and it as a list of tuples
        (or an empty list if no result to fetch).  The method automatically
        flushes all the fields in the metadata of the query.
        """
        assert isinstance(query, SQL)
        self.flush_query(query)
        self.cr.execute(query)
        return [] if self.cr.description is None else self.cr.fetchall()

    def execute_query_dict(self, query: SQL) -> list[dict]:
        """ Execute the given query, fetch its results as a list of dicts.
        The method automatically flushes fields in the metadata of the query.
        """
        rows = self.execute_query(query)
        if not rows:
            return rows
        description = self.cr.description
        return [
            {column.name: row[index] for index, column in enumerate(description)}
            for row in rows
        ]


class Transaction:
    """ A object holding ORM data structures for a transaction. """
    __slots__ = ('_Transaction__file_open_tmp_paths', 'cache', 'envs', 'protected', 'registry', 'tocompute')

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
        # temporary directories (managed in odoo.tools.file_open_temporary_directory)
        self.__file_open_tmp_paths = ()  # noqa: PLE0237

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
            env._cache_key.clear()
        self.clear()


# sentinel value for optional parameters
NOTHING = object()
EMPTY_DICT = frozendict()


class Cache:
    """ Implementation of the cache of records.

    For most fields, the cache is simply a mapping from a record and a field to
    a value.  In the case of context-dependent fields, the mapping also depends
    on the environment of the given record.  For the sake of performance, the
    cache is first partitioned by field, then by record.  This makes some
    common ORM operations pretty fast, like determining which records have a
    value for a given field, or invalidating a given field on all possible
    records.

    The cache can also mark some entries as "dirty".  Dirty entries essentially
    marks values that are different from the database.  They represent database
    updates that haven't been done yet.  Note that dirty entries only make
    sense for stored fields.  Note also that if a field is dirty on a given
    record, and the field is context-dependent, then all the values of the
    record for that field are considered dirty.  For the sake of consistency,
    the values that should be in the database must be in a context where all
    the field's context keys are ``None``.
    """
    __slots__ = ('_data', '_dirty', '_patches')

    def __init__(self):
        # {field: {record_id: value}, field: {context_key: {record_id: value}}}
        self._data = defaultdict(dict)

        # {field: set[id]} stores the fields and ids that are changed in the
        # cache, but not yet written in the database; their changed values are
        # in `_data`
        self._dirty = defaultdict(OrderedSet)

        # {field: {record_id: ids}} record ids to be added to the values of
        # x2many fields if they are not in cache yet
        self._patches = defaultdict(lambda: defaultdict(list))

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

    def _get_field_cache(self, model, field):
        """ Return the field cache of the given field, but not for modifying it. """
        field_cache = self._data.get(field, EMPTY_DICT)
        if field_cache and field in model.pool.field_depends_context:
            field_cache = field_cache.get(model.env.cache_key(field), EMPTY_DICT)
        return field_cache

    def _set_field_cache(self, model, field):
        """ Return the field cache of the given field for modifying it. """
        field_cache = self._data[field]
        if field in model.pool.field_depends_context:
            field_cache = field_cache.setdefault(model.env.cache_key(field), {})
        return field_cache

    def contains(self, record, field):
        """ Return whether ``record`` has a value for ``field``. """
        field_cache = self._get_field_cache(record, field)
        if field.translate:
            cache_value = field_cache.get(record.id, EMPTY_DICT)
            if cache_value is None:
                return True
            lang = (record.env.lang or 'en_US') if field.translate is True else record.env._lang
            return lang in cache_value

        return record.id in field_cache

    def contains_field(self, field):
        """ Return whether ``field`` has a value for at least one record. """
        cache = self._data.get(field)
        if not cache:
            return False
        # 'cache' keys are tuples if 'field' is context-dependent, record ids otherwise
        if isinstance(next(iter(cache)), tuple):
            return any(value for value in cache.values())
        return True

    def get(self, record, field, default=NOTHING):
        """ Return the value of ``field`` for ``record``. """
        try:
            field_cache = self._get_field_cache(record, field)
            cache_value = field_cache[record._ids[0]]
            if field.translate and cache_value is not None:
                lang = (record.env.lang or 'en_US') if field.translate is True else record.env._lang
                return cache_value[lang]
            return cache_value
        except KeyError:
            if default is NOTHING:
                raise CacheMiss(record, field) from None
            return default

    def set(self, record, field, value, dirty=False, check_dirty=True):
        """ Set the value of ``field`` for ``record``.
        One can normally make a clean field dirty but not the other way around.
        Updating a dirty field without ``dirty=True`` is a programming error and
        raises an exception.

        :param dirty: whether ``field`` must be made dirty on ``record`` after
            the update
        :param check_dirty: whether updating a dirty field without making it
            dirty must raise an exception
        """
        field_cache = self._set_field_cache(record, field)
        record_id = record.id

        if field.translate and value is not None:
            # only for model translated fields
            lang = record.env.lang or 'en_US'
            cache_value = field_cache.get(record_id) or {}
            cache_value[lang] = value
            value = cache_value

        field_cache[record_id] = value

        if not check_dirty:
            return

        if dirty:
            assert field.column_type and field.store and record_id
            self._dirty[field].add(record_id)
            if field in record.pool.field_depends_context:
                # put the values under conventional context key values {'context_key': None},
                # in order to ease the retrieval of those values to flush them
                record = record.with_env(record.env(context={}))
                field_cache = self._set_field_cache(record, field)
                field_cache[record_id] = value
        elif record_id in self._dirty.get(field, ()):
            _logger.error("cache.set() removing flag dirty on %s.%s", record, field.name, stack_info=True)

    def update(self, records, field, values, dirty=False, check_dirty=True):
        """ Set the values of ``field`` for several ``records``.
        One can normally make a clean field dirty but not the other way around.
        Updating a dirty field without ``dirty=True`` is a programming error and
        raises an exception.

        :param dirty: whether ``field`` must be made dirty on ``record`` after
            the update
        :param check_dirty: whether updating a dirty field without making it
            dirty must raise an exception
        """
        if field.translate:
            # only for model translated fields
            lang = records.env.lang or 'en_US'
            field_cache = self._get_field_cache(records, field)
            cache_values = []
            for id_, value in zip(records._ids, values):
                if value is None:
                    cache_values.append(None)
                else:
                    cache_value = field_cache.get(id_) or {}
                    cache_value[lang] = value
                    cache_values.append(cache_value)
            values = cache_values

        self.update_raw(records, field, values, dirty, check_dirty)

    def update_raw(self, records, field, values, dirty=False, check_dirty=True):
        """ This is a variant of method :meth:`~update` without the logic for
        translated fields.
        """
        field_cache = self._set_field_cache(records, field)
        field_cache.update(zip(records._ids, values))
        if not check_dirty:
            return
        if dirty:
            assert field.column_type and field.store and all(records._ids)
            self._dirty[field].update(records._ids)
            if not field.company_dependent and field in records.pool.field_depends_context:
                # put the values under conventional context key values {'context_key': None},
                # in order to ease the retrieval of those values to flush them
                records = records.with_env(records.env(context={}))
                field_cache = self._set_field_cache(records, field)
                field_cache.update(zip(records._ids, values))
        else:
            dirty_ids = self._dirty.get(field)
            if dirty_ids and not dirty_ids.isdisjoint(records._ids):
                _logger.error("cache.update() removing flag dirty on %s.%s", records, field.name, stack_info=True)

    def insert_missing(self, records, field, values):
        """ Set the values of ``field`` for the records in ``records`` that
        don't have a value yet.  In other words, this does not overwrite
        existing values in cache.
        """
        field_cache = self._set_field_cache(records, field)
        env = records.env
        if field.translate:
            if env.context.get('prefetch_langs'):
                installed = [lang for lang, _ in env['res.lang'].get_installed()]
                langs = OrderedSet(installed + ['en_US'])
                _langs = [f'_{l}' for l in langs] if field.translate is not True and env._lang.startswith('_') else []
                for id_, val in zip(records._ids, values):
                    if val is None:
                        field_cache.setdefault(id_, None)
                    else:
                        if _langs:  # fallback missing _lang to lang if exists
                            val.update({f'_{k}': v for k, v in val.items() if k in langs and f'_{k}' not in val})
                        field_cache[id_] = {
                            **dict.fromkeys(langs, val['en_US']),  # fallback missing lang to en_US
                            **dict.fromkeys(_langs, val.get('_en_US')),  # fallback missing _lang to _en_US
                            **val
                        }
            else:
                lang = (env.lang or 'en_US') if field.translate is True else env._lang
                for id_, val in zip(records._ids, values):
                    if val is None:
                        field_cache.setdefault(id_, None)
                    else:
                        cache_value = field_cache.setdefault(id_, {})
                        if cache_value is not None:
                            cache_value.setdefault(lang, val)
        else:
            for id_, val in zip(records._ids, values):
                field_cache.setdefault(id_, val)

    def patch(self, records, field, new_id):
        """ Apply a patch to an x2many field on new records. The patch consists
        in adding new_id to its value in cache. If the value is not in cache
        yet, it will be applied once the value is put in cache with method
        :meth:`patch_and_set`.
        """
        assert not new_id, "Cache.patch can only be called with a new id"
        field_cache = self._set_field_cache(records, field)
        for id_ in records._ids:
            assert not id_, "Cache.patch can only be called with new records"
            if id_ in field_cache:
                field_cache[id_] = tuple(dict.fromkeys(field_cache[id_] + (new_id,)))
            else:
                self._patches[field][id_].append(new_id)

    def patch_and_set(self, record, field, value):
        """ Set the value of ``field`` for ``record``, like :meth:`set`, but
        apply pending patches to ``value`` and return the value actually put
        in cache.
        """
        field_patches = self._patches.get(field)
        if field_patches:
            ids = field_patches.pop(record.id, ())
            if ids:
                value = tuple(dict.fromkeys(value + tuple(ids)))
        self.set(record, field, value)
        return value

    def remove(self, record, field):
        """ Remove the value of ``field`` for ``record``. """
        assert record.id not in self._dirty.get(field, ())
        try:
            field_cache = self._set_field_cache(record, field)
            del field_cache[record._ids[0]]
        except KeyError:
            pass

    def get_values(self, records, field):
        """ Return the cached values of ``field`` for ``records``. """
        field_cache = self._get_field_cache(records, field)
        for record_id in records._ids:
            try:
                yield field_cache[record_id]
            except KeyError:
                pass

    def get_until_miss(self, records, field):
        """ Return the cached values of ``field`` for ``records`` until a value is not found. """
        field_cache = self._get_field_cache(records, field)
        if field.translate:
            lang = (records.env.lang or 'en_US') if field.translate is True else records.env._lang

            def get_value(id_):
                cache_value = field_cache[id_]
                return None if cache_value is None else cache_value[lang]
        else:
            get_value = field_cache.__getitem__

        vals = []
        for record_id in records._ids:
            try:
                vals.append(get_value(record_id))
            except KeyError:
                break
        return vals

    def get_records_different_from(self, records, field, value):
        """ Return the subset of ``records`` that has not ``value`` for ``field``. """
        field_cache = self._get_field_cache(records, field)
        if field.translate:
            lang = records.env.lang or 'en_US'

            def get_value(id_):
                cache_value = field_cache[id_]
                return None if cache_value is None else cache_value[lang]
        else:
            get_value = field_cache.__getitem__

        ids = []
        for record_id in records._ids:
            try:
                val = get_value(record_id)
            except KeyError:
                ids.append(record_id)
            else:
                if field.type == "monetary":
                    value = field.convert_to_cache(value, records.browse(record_id))
                if val != value:
                    ids.append(record_id)
        return records.browse(ids)

    def get_fields(self, record):
        """ Return the fields with a value for ``record``. """
        for name, field in record._fields.items():
            if name != 'id' and record.id in self._get_field_cache(record, field):
                yield field

    def get_records(self, model, field, all_contexts=False):
        """ Return the records of ``model`` that have a value for ``field``.
        By default the method checks for values in the current context of ``model``.
        But when ``all_contexts`` is true, it checks for values *in all contexts*.
        """
        if all_contexts and field in model.pool.field_depends_context:
            field_cache = self._data.get(field, EMPTY_DICT)
            ids = OrderedSet(id_ for sub_cache in field_cache.values() for id_ in sub_cache)
        else:
            ids = self._get_field_cache(model, field)
        return model.browse(ids)

    def get_missing_ids(self, records, field):
        """ Return the ids of ``records`` that have no value for ``field``. """
        field_cache = self._get_field_cache(records, field)
        if field.translate:
            lang = (records.env.lang or 'en_US') if field.translate is True else records.env._lang
            for record_id in records._ids:
                cache_value = field_cache.get(record_id, False)
                if cache_value is False or not (cache_value is None or lang in cache_value):
                    yield record_id
        else:
            for record_id in records._ids:
                if record_id not in field_cache:
                    yield record_id

    def get_dirty_fields(self):
        """ Return the fields that have dirty records in cache. """
        return self._dirty.keys()

    def get_dirty_records(self, model, field):
        """ Return the records that for which ``field`` is dirty in cache. """
        return model.browse(self._dirty.get(field, ()))

    def has_dirty_fields(self, records, fields=None):
        """ Return whether any of the given records has dirty fields.

        :param fields: a collection of fields or ``None``; the value ``None`` is
            interpreted as any field on ``records``
        """
        if fields is None:
            return any(
                not ids.isdisjoint(records._ids)
                for field, ids in self._dirty.items()
                if field.model_name == records._name
            )
        else:
            return any(
                field in self._dirty and not self._dirty[field].isdisjoint(records._ids)
                for field in fields
            )

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
                caches = cache.values() if isinstance(next(iter(cache)), tuple) else [cache]
                for field_cache in caches:
                    for id_ in ids:
                        field_cache.pop(id_, None)

    def clear(self):
        """ Invalidate the cache and its dirty flags. """
        self._data.clear()
        self._dirty.clear()
        self._patches.clear()

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
            query = Query(env, model._table, model._table_sql)
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
            if not field.store or not field.column_type or field.translate or field.company_dependent:
                continue

            model = env[field.model_name]
            if field in depends_context:
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

    def _get_grouped_company_dependent_field_cache(self, field):
        """
        get a field cache proxy to group up field cache value for a company
        dependent field
        cache data: {field: {(company_id,): {id: value}}}

        :param field: a company dependent field
        :return: a dict like field cache proxy which is logically similar to
              {id: {company_id, value}}
        """
        field_caches = self._data.get(field, EMPTY_DICT)
        company_field_cache = {
            context_key[0]: field_cache
            for context_key, field_cache in field_caches.items()
        }
        return GroupedCompanyDependentFieldCache(company_field_cache)


class GroupedCompanyDependentFieldCache:
    def __init__(self, company_field_cache):
        self._company_field_cache = company_field_cache

    def __getitem__(self, id_):
        return {
            company_id: field_cache[id_]
            for company_id, field_cache in self._company_field_cache.items()
            if id_ in field_cache
        }


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
from .sql_db import BaseCursor
