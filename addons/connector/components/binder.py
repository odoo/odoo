# Copyright 2013 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

"""
Binders
=======

Binders are components that know how to find the external ID for an
Odoo ID, how to find the Odoo ID for an external ID and how to
create the binding between them.

"""

from odoo import fields, models, tools

from odoo.addons.component.core import AbstractComponent


class Binder(AbstractComponent):
    """For one record of a model, capable to find an external or
    internal id, or create the binding (link) between them

    This is a default implementation that can be inherited or reimplemented
    in the connectors.

    This implementation assumes that binding models are ``_inherits`` of
    the models they are binding.

    """

    _name = "base.binder"
    _inherit = "base.connector"
    _usage = "binder"

    _external_field = "external_id"  # override in sub-classes
    _backend_field = "backend_id"  # override in sub-classes
    _odoo_field = "odoo_id"  # override in sub-classes
    _sync_date_field = "sync_date"  # override in sub-classes

    def to_internal(self, external_id, unwrap=False):
        """Give the Odoo recordset for an external ID

        :param external_id: external ID for which we want
                            the Odoo ID
        :param unwrap: if True, returns the normal record
                       else return the binding record
        :return: a recordset, depending on the value of unwrap,
                 or an empty recordset if the external_id is not mapped
        :rtype: recordset
        """
        context = self.env.context
        bindings = self.model.with_context(active_test=False).search(
            [
                (self._external_field, "=", tools.ustr(external_id)),
                (self._backend_field, "=", self.backend_record.id),
            ]
        )
        if not bindings:
            if unwrap:
                return self.model.browse()[self._odoo_field]
            return self.model.browse()
        bindings.ensure_one()
        if unwrap:
            bindings = bindings[self._odoo_field]
        bindings = bindings.with_context(**context)
        return bindings

    def to_external(self, binding, wrap=False):
        """Give the external ID for an Odoo binding ID

        :param binding: Odoo binding for which we want the external id
        :param wrap: if True, binding is a normal record, the
                     method will search the corresponding binding and return
                     the external id of the binding
        :return: external ID of the record
        """
        if isinstance(binding, models.BaseModel):
            binding.ensure_one()
        else:
            binding = self.model.browse(binding)
        if wrap:
            binding = self.model.with_context(active_test=False).search(
                [
                    (self._odoo_field, "=", binding.id),
                    (self._backend_field, "=", self.backend_record.id),
                ]
            )
            if not binding:
                return None
            binding.ensure_one()
            return binding[self._external_field]
        return binding[self._external_field]

    def bind(self, external_id, binding):
        """Create the link between an external ID and an Odoo ID

        :param external_id: external id to bind
        :param binding: Odoo record to bind
        :type binding: int
        """
        # Prevent False, None, or "", but not 0
        assert (
            external_id or external_id == 0
        ) and binding, "external_id or binding missing, " "got: %s, %s" % (
            external_id,
            binding,
        )
        # avoid to trigger the export when we modify the `external_id`
        now_fmt = fields.Datetime.now()
        if isinstance(binding, models.BaseModel):
            binding.ensure_one()
        else:
            binding = self.model.browse(binding)
        binding.with_context(connector_no_export=True).write(
            {
                self._external_field: tools.ustr(external_id),
                self._sync_date_field: now_fmt,
            }
        )

    def unwrap_binding(self, binding):
        """For a binding record, gives the normal record.

        Example: when called with a ``magento.product.product`` id,
        it will return the corresponding ``product.product`` id.

        :param browse: when True, returns a browse_record instance
                       rather than an ID
        """
        if isinstance(binding, models.BaseModel):
            binding.ensure_one()
        else:
            binding = self.model.browse(binding)

        return binding[self._odoo_field]

    def unwrap_model(self):
        """For a binding model, gives the normal model.

        Example: when called on a binder for ``magento.product.product``,
        it will return ``product.product``.
        """
        try:
            column = self.model._fields[self._odoo_field]
        except KeyError as err:
            raise ValueError(
                "Cannot unwrap model %s, because it has no %s fields"
                % (self.model._name, self._odoo_field)
            ) from err
        return column.comodel_name
