from odoo.addons.account.models.chart_template import template
from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('gr', 'res.company')
    def _get_gr_reports_res_company(self):
        default_accounts = {}
        if self.ref('l10n_gr_69_02', False):
            default_accounts['deferred_expense_account_id'] = 'l10n_gr_69_02'
        if self.ref('l10n_gr_78_02', False):
            default_accounts['deferred_revenue_account_id'] = 'l10n_gr_78_02'

        return {self.env.company.id: default_accounts}
