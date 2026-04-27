from odoo.addons.account.models.chart_template import template
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('lu', 'res.company')
    def _get_lu_reports_res_company(self):
        return {
            self.env.company.id: {
                'deferred_expense_account_id': 'lu_2011_account_481',
                'deferred_revenue_account_id': 'lu_2011_account_482',
            }
        }
