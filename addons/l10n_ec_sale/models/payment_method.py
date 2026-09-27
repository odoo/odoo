# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    def _get_fiscal_country_codes(self):
        return ','.join(self.env.companies.mapped('account_fiscal_country_id.code'))

    l10n_ec_sri_payment_id = fields.Many2one(
        comodel_name="l10n_ec.sri.payment",
        string="SRI Payment Method",
        compute='_compute_l10n_ec_sri_payment_id',
        store=True,
        readonly=False,
    )

    fiscal_country_codes = fields.Char(store=False, default=_get_fiscal_country_codes)

    @api.depends('code')
    def _compute_l10n_ec_sri_payment_id(self):
        for method in self:
            if method.code == 'card':
                method.l10n_ec_sri_payment_id = self.env.ref('l10n_ec.P19', raise_if_not_found=False)
            elif method.code == 'bank_transfer':
                method.l10n_ec_sri_payment_id = self.env.ref('l10n_ec.P20', raise_if_not_found=False)
            elif method.code == 'bank_account':
                method.l10n_ec_sri_payment_id = self.env.ref('l10n_ec.P21', raise_if_not_found=False)
            else:
                method.l10n_ec_sri_payment_id = False
