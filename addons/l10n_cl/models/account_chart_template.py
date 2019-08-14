# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    def load_for_current_company(self, sale_tax_rate, purchase_tax_rate):
        """ Set tax calculation rounding method required in Chilean localization"""
        self.ensure_one()
        res = super().load_for_current_company(sale_tax_rate, purchase_tax_rate)
        company = self.env.company
        if company.country_id.code == 'CL':
            company.write({'tax_calculation_rounding_method': 'round_globally'})
        return res
