# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
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

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        res.update(
            {
                "l10n_br_edi_transporter_id": self.l10n_br_edi_transporter_id.id,
                "l10n_br_edi_freight_model": self.l10n_br_edi_freight_model,
                "l10n_br_edi_payment_method": self.l10n_br_edi_payment_method,
            }
        )
        return res
