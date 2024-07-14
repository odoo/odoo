# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.depends("order_line.product_id.l10n_br_transport_cost_type", "order_line.product_id.type")
    def _compute_l10n_br_is_service_transaction(self):
        """Override. Set this if all products are only allowed on service invoices. If goods and service lines are mixed
        we default to a goods transaction and raise a ValidationError in _l10n_br_avatax_validate_lines()."""
        for order in self:
            order.l10n_br_is_service_transaction = (
                order._l10n_br_is_avatax()
                and order.order_line
                and all(
                    order.order_line.product_id.mapped(
                        lambda product: product.product_tmpl_id._l10n_br_is_only_allowed_on_service_invoice()
                    )
                )
            )

    def _prepare_invoice(self):
        """Override."""
        res = super()._prepare_invoice()
        if self.l10n_br_is_service_transaction:
            res["l10n_latam_document_type_id"] = self.env.ref("l10n_br.dt_SE").id

        return res
