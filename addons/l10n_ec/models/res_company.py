# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _localization_use_documents(self):
        self.ensure_one()
        return self.chart_template == 'ec' or self.account_fiscal_country_id.code == "EC" or super()._localization_use_documents()

    def _get_l10n_latam_base_country_codes(self):
        # EXTENDS 'l10n_latam_base' - adds EC
        return super()._get_l10n_latam_base_country_codes() + ['EC']
