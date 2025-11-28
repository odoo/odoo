# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _localization_use_documents(self):
        self.ensure_one()
        return self.chart_template == 'ec' or self.account_fiscal_country_id.code == "EC" or super()._localization_use_documents()

    def _is_latam(self):
        return super()._is_latam() or self.country_code == 'EC'
