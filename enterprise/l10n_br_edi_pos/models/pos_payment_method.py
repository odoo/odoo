# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons.l10n_br_edi.models.account_move import PAYMENT_METHOD_SELECTION


class POSPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    l10n_br_payment_method = fields.Selection(
        PAYMENT_METHOD_SELECTION,
        string="Payment Method Brazil",
        default="99",  # Others
        help="Brazil: payment method to be used.",
    )
    l10n_br_country_code = fields.Char(
        related="company_id.account_fiscal_country_id.code",
        string="Country Code (BR)",  # to avoid duplicate string warning with l10n_ec_edi_pos, TODO: master
    )
