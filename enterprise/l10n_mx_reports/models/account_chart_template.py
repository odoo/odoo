from odoo.addons.account.models.chart_template import template
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mx', 'res.company')
    def _get_mx_reports_res_company(self):
        return {
            self.env.company.id: {
                'deferred_revenue_account_id': 'cuenta260_01_01',
            }
        }
