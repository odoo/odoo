# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _update_company_before_loading(self, loaded_data):
        # OVERRIDE
        # Set tax calculation rounding method required in Chilean localization.
        res = super()._update_company_before_loading(loaded_data)

        company = self.env.company
        if company.account_fiscal_country_id.code == 'CL':
            company.tax_calculation_rounding_method = 'round_globally'

        return res
