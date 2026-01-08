# -*- coding: utf-8 -*-
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_demo_data(self, company=False):
        result = super()._post_load_demo_data(company)
        if company == self.env.ref('l10n_ar.company_ri', raise_if_not_found=False):
            # Because in demo we want to skip the config, while in data we want to require them to configure
            self.env['account.tax'].search([('l10n_ar_withholding_payment_type', '!=', False)]).write({'amount_type': 'percent', 'amount' : 1})
        return result
