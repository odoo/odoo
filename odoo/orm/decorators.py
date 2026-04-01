# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""The Odoo API module defines method decorators.
"""
from __future__ import annotations

import logging
import typing
import warnings
from collections.abc import Mapping
from functools import wraps

try:
    # available since python 3.13
    from warnings import deprecated
except ImportError:
    # simplified version
    class deprecated:
        def __init__(
            self,
            message: str,
            /,
            *,
            category: type[Warning] | None = DeprecationWarning,
            stacklevel: int = 1,
        ) -> None:
            self.message = message
            self.category = category
            self.stacklevel = stacklevel

        def __call__(self, obj, /):
            message = self.message
            category = self.category
            stacklevel = self.stacklevel
            if category is None:
                obj.__deprecated__ = message
                return obj
            if callable(obj):
                @wraps(obj)
                def wrapper(*args, **kwargs):
                    warnings.warn(message, category=category, stacklevel=stacklevel + 1)
                    return obj(*args, **kwargs)

                obj.__deprecated__ = wrapper.__deprecated__ = message
                return wrapper
            raise TypeError(f"@deprecated decorator cannot be applied to {obj!r}")

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Collection
    from .types import BaseModel, ValuesType

    T = typing.TypeVar('T')
    C = typing.TypeVar("C", bound=Callable)
    Decorator = Callable[[C], C]

_logger = logging.getLogger('odoo.api')


# The following attributes are used, and reflected on wrapping methods:
#  - method._constrains: set by @constrains, specifies constraint dependencies
#  - method._depends: set by @depends, specifies compute dependencies
#  - method._onchange: set by @onchange, specifies onchange fields
#  - method._ondelete: set by @ondelete, used to raise errors for unlink operations
#
# On wrapping method only:
#  - method._api_*: decorator function, used for re-applying decorator
#

def attrsetter(attr, value) -> Decorator:
    """ Return a function that sets ``attr`` on its argument and returns it. """
    def setter(method):
        setattr(method, attr, value)
        return method

    return setter


@typing.overload
def constrains(func: Callable[[BaseModel], Collection[str]], /) -> Decorator:
    ...


@typing.overload
def constrains(*args: str) -> Decorator:
    ...


def constrains(*args) -> Decorator:
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


def ondelete(*, at_uninstall: bool) -> Decorator:
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


def onchange(*args: str) -> Decorator:
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


@typing.overload
def depends(func: Callable[[BaseModel], Collection[str]], /) -> Decorator:
    ...


@typing.overload
def depends(*args: str) -> Decorator:
    ...


def depends(*args) -> Decorator:
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


def depends_context(*args: str) -> Decorator:
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


def autovacuum(method: C) -> C:
    """
    Decorate a method so that it is called by the daily vacuum cron job (model
    ``ir.autovacuum``).  This is typically used for garbage-collection-like
    tasks that do not deserve a specific cron job.

    A return value can be a tuple (done, remaining) which have simular meaning
    as in :meth:`~odoo.addons.base.models.ir_cron.IrCron._commit_progress`.
    """
    assert method.__name__.startswith('_'), "%s: autovacuum methods must be private" % method.__name__
    method._autovacuum = True  # type: ignore
    return method


def model(method: C) -> C:
    """ Decorate a record-style method where ``self`` is a recordset, but its
        contents is not relevant, only the model is. Such a method::

            @api.model
            def method(self, args):
                ...

    """
    if method.__name__ == 'create':
        return model_create_multi(method)  # type: ignore
    method._api_model = True  # type: ignore
    return method


def private(method: C) -> C:
    """ Decorate a record-style method to indicate that the method cannot be
        called using RPC. Example::

            @api.private
            def method(self, args):
                ...

        If you have business methods that should not be called over RPC, you
        should prefix them with "_". This decorator may be used in case of
        existing public methods that become non-RPC callable or for ORM
        methods.
    """
    method._api_private = True  # type: ignore
    return method


def readonly(method: C) -> C:
    """ Decorate a record-style method where ``self.env.cr`` can be a
        readonly cursor when called trough a rpc call.

            @api.readonly
            def method(self, args):
                ...
    """
    method._readonly = True  # type: ignore
    return method


def model_create_multi(method: Callable[[T, list[ValuesType]], T]) -> Callable[[T, list[ValuesType] | ValuesType], T]:
    """ Decorate a method that takes a list of dictionaries and creates multiple
        records. The method may be called with either a single dict or a list of
        dicts::

            record = model.create(vals)
            records = model.create([vals, ...])
    """
    @wraps(method)
    def create(self: T, vals_list: list[ValuesType] | ValuesType) -> T:
        if isinstance(vals_list, Mapping):
            vals_list = [vals_list]
        return method(self, vals_list)

    create._api_model = True  # type: ignore
    return create
