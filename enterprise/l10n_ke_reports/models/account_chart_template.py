from odoo.addons.account.models.chart_template import template
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ke', 'res.company')
    def _get_ke_reports_res_company(self):
        return {
            self.env.company.id: {
                'deferred_expense_account_id': 'ke120011',
                'deferred_revenue_account_id': 'ke211000',
            }
        }
