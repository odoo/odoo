from odoo.addons.account.models.chart_template import template
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('au', 'res.company')
    def _get_au_reports_res_company(self):
        return {
            self.env.company.id: {
                'deferred_expense_account_id': 'au_12200',
                'deferred_revenue_account_id': 'au_21760',
            }
        }
