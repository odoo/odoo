# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _is_latam(self):
        """Return whether the given company belong to latam countries or not."""
        self.ensure_one()
        return self.account_fiscal_country_id.code in self._get_l10n_latam_base_country_codes()

    @api.model
    def _get_l10n_latam_base_country_codes(self):
        # TO OVERRIDE
        return []
