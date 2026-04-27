from odoo.addons.account.models.chart_template import template
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('de_skr03', 'res.company')
    def _get_de_skr03_reports_res_company(self):
        return {
            self.env.company.id: {
                'deferred_expense_account_id': 'account_0980',
                'deferred_revenue_account_id': 'account_0990',
            }
        }

    @template('de_skr04', 'res.company')
    def _get_de_skr04_reports_res_company(self):
        return {
            self.env.company.id: {
                'deferred_expense_account_id': 'chart_skr04_1900',
                'deferred_revenue_account_id': 'chart_skr04_3900',
            }
        }
