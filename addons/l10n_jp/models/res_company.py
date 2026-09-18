# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_jp_hide_zero_decimals(self, amounts):
        """
        Whether a report column holding ``amounts`` prints without decimals.

        A unit price in Japan is all but always a whole yen, and the ``.00`` it
        prints carries nothing. A column reads as one number though, so it only
        loses its decimals when every amount in it can spare them: one price of
        101.50 keeps the 202.00 above it in full rather than leaving the column
        to line up 202 against 101.50.
        """
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'JP':
            return False
        return all(amount.is_integer() for amount in amounts)
