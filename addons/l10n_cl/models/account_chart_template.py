# -*- coding: utf-8 -*-
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cl', 'res.company')
    def _get_cl_res_company(self):
        company_data = super()._get_cl_res_company()
        company_data[self.env.company.id].update({
            'tax_calculation_rounding_method': 'round_globally',
        })
        return company_data
