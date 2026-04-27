# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
from odoo.addons.l10n_br_edi.models.account_move import PAYMENT_METHOD_SELECTION


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    l10n_br_edi_payment_method = fields.Selection(
        PAYMENT_METHOD_SELECTION,
        string="Payment Method Brazil",
        default="99",
        help="Brazil: expected payment method to be used.",
    )
