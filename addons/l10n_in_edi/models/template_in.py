from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('in', 'res.company')
    def _get_in_res_company_edi(self):
        return {
            self.env.company.id: {
                'tax_calculation_rounding_method': 'round_per_line',
            },
        }
