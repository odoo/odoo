from odoo.addons.account.models.chart_template import template
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('hk', 'res.company')
    def _get_hk_reports_res_company(self):
        return {
            self.env.company.id: {
                'deferred_expense_account_id': 'l10n_hk_1400',
                'deferred_revenue_account_id': 'l10n_hk_2107',
            }
        }
