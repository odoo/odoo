from odoo.addons.account.models.chart_template import template
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('generic_coa', 'res.company')
    def _get_us_reports_res_company(self):
        return {
            self.env.company.id: {
                'deferred_expense_account_id': 'prepaid_expenses',
                'deferred_revenue_account_id': 'deferred_revenue',
            }
        }
