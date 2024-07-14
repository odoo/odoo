from odoo import fields, models


class PoSPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])
    l10n_ec_sri_payment_id = fields.Many2one(
        comodel_name="l10n_ec.sri.payment",
        string="SRI Payment Method",
    )
