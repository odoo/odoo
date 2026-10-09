# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_jp_currency_in_headers = fields.Boolean(
        string="Currency in Headers",
        default=True,
        help="Add the currency to the Unit Price and Amount column headers of the Japanese Business layout, "
             "e.g. Amount (円) or Amount (USD).",
    )

    def _l10n_jp_hide_zero_decimals(self, amounts):
        """Drop the decimals of a JP report column when all its ``amounts`` are whole."""
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'JP':
            return False
        return all(amount.is_integer() for amount in amounts)
