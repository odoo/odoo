# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_jp_hide_zero_decimals(self, amounts):
        """Drop the decimals of a JP report column when all its ``amounts`` are whole."""
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'JP':
            return False
        return all(amount.is_integer() for amount in amounts)
