# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from odoo.addons.l10n_br_edi.models.account_move import FREIGHT_MODEL_SELECTION, PAYMENT_METHOD_SELECTION


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_br_edi_transporter_id = fields.Many2one(
        "res.partner",
        "Transporter Brazil",
        help="Brazil: If you use a transport company, add its company contact here.",
    )
    l10n_br_edi_freight_model = fields.Selection(
        FREIGHT_MODEL_SELECTION,
        string="Freight Model",
        help="Brazil: Used to determine the freight model used on this transaction.",
    )
    l10n_br_edi_payment_method = fields.Selection(
        PAYMENT_METHOD_SELECTION,
        string="Payment Method Brazil",
        default="90",  # no payment
        help="Brazil: Expected payment method to be used.",
    )

    @api.depends("order_line.product_id.l10n_br_transport_cost_type", "order_line.product_id.type")
    def _compute_l10n_br_is_service_transaction(self):
        """Override. Set this if all products are only allowed on service invoices. If goods and service lines are mixed
        we default to a goods transaction and raise a ValidationError in _l10n_br_avatax_validate_lines()."""
        for order in self:
            order.l10n_br_is_service_transaction = (
                order.l10n_br_is_avatax
                and order.order_line
                and all(
                    order.order_line.product_id.mapped(
                        lambda product: product.product_tmpl_id._l10n_br_is_only_allowed_on_service_invoice()
                    )
                )
            )

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        res.update(
            {
                "l10n_br_edi_transporter_id": self.l10n_br_edi_transporter_id.id,
                "l10n_br_edi_freight_model": self.l10n_br_edi_freight_model,
                "l10n_br_edi_payment_method": self.l10n_br_edi_payment_method,
            }
        )

        if self.l10n_br_is_service_transaction:
            res["l10n_latam_document_type_id"] = self.env.ref("l10n_br.dt_SE").id

        return res

    def _l10n_br_get_line_uom(self, line_id):
        # Override.
        return self.env['sale.order.line'].browse(line_id).product_uom
