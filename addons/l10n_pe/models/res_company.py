# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _localization_use_documents(self):
        # OVERRIDE
        self.ensure_one()
        return self.chart_template == 'pe' or self.account_fiscal_country_id.code == "PE" or super()._localization_use_documents()
