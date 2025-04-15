# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    l10n_ec_sri_payment_id = fields.Many2one(
        comodel_name="l10n_ec.sri.payment",
        string="SRI Payment Method",
    )

    fiscal_country_codes = fields.Char(compute="_compute_fiscal_country_codes")

    @api.depends_context('allowed_company_ids')
    def _compute_fiscal_country_codes(self):
        for record in self:
            record.fiscal_country_codes = ",".join(self.env.companies.mapped('account_fiscal_country_id.code'))
