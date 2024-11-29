# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""The Odoo API module defines method decorators.
"""
from __future__ import annotations

import logging
import typing
import warnings
from collections.abc import Mapping
from inspect import signature

try:
    from decorator import decoratorx as decorator
except ImportError:
    from decorator import decorator

if typing.TYPE_CHECKING:
    from collections.abc import Callable
    from .types import BaseModel, ValuesType

    # not sure Self can work outside of a class?
    S = typing.TypeVar("S", bound=BaseModel)
    CreateCaller = Callable[[S, ValuesType | list[ValuesType]], S]
    CreateCallee = Callable[[S, list[ValuesType]], S]
    CreateLegacyCallee = Callable[[S, ValuesType], S]
    T = typing.TypeVar('T')

_logger = logging.getLogger('odoo.api')


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
def _model_create_single(create: CreateLegacyCallee[S], self: S, arg: ValuesType | list[ValuesType]) -> S:
    # 'create' expects a dict and returns a record
    if isinstance(arg, Mapping):
        return create(self, arg)
    if len(arg) > 1:
        _create_logger.debug("%s.create() called with %d dicts", self, len(arg))
    return self.browse().concat(*(create(self, vals) for vals in arg))


def model_create_single(method: CreateLegacyCallee[S]) -> CreateCaller[S]:
    """ Decorate a method that takes a dictionary and creates a single record.
        The method may be called with either a single dict or a list of dicts::

            record = model.create(vals)
            records = model.create([vals, ...])
    """
    warnings.warn(
        f"Since 18.0, `create` must be batched, an override in {method.__module__} is in single mode",
        DeprecationWarning,
        stacklevel=3,
    )
    wrapper = typing.cast('CreateCaller[S]', _model_create_single(method))  # pylint: disable=no-value-for-parameter
    wrapper._api = 'model_create'
    return wrapper


@decorator
def _model_create_multi(create: CreateCallee[S], self: S, arg: ValuesType | list[ValuesType]) -> S:
    # 'create' expects a list of dicts and returns a recordset
    if isinstance(arg, Mapping):
        return create(self, [arg])
    return create(self, arg)


def model_create_multi(method: CreateCallee[S]) -> CreateCaller[S]:
    """ Decorate a method that takes a list of dictionaries and creates multiple
        records. The method may be called with either a single dict or a list of
        dicts::

            record = model.create(vals)
            records = model.create([vals, ...])
    """
    wrapper = typing.cast('CreateCaller[S]', _model_create_multi(method))  # pylint: disable=no-value-for-parameter
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
