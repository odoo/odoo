from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ke', 'res.company')
    def _get_ke_res_company(self):
        companies = super()._get_ke_res_company()
        for company in companies.values():
            company['point_of_sale_update_stock_quantities'] = 'real'
        return companies
