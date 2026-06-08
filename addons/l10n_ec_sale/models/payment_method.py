# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    def _get_l10n_ec_sri_payment_id(self):
        if self.code == "card":
            return self.env.ref('l10n_ec.P19', raise_if_not_found=False)
        elif self.code == "bank_transfer":
            return self.env.ref('l10n_ec.P20', raise_if_not_found=False)
        elif self.code == "bank_account":
            return self.env.ref('l10n_ec.P21', raise_if_not_found=False)
        return self.env['l10n_ec.sri.payment']

    def _get_fiscal_country_codes(self):
        return ','.join(self.env.companies.mapped('account_fiscal_country_id.code'))

    l10n_ec_sri_payment_id = fields.Many2one(
        comodel_name="l10n_ec.sri.payment",
        string="SRI Payment Method",
        default=_get_l10n_ec_sri_payment_id,
    )

    fiscal_country_codes = fields.Char(store=False, default=_get_fiscal_country_codes)
