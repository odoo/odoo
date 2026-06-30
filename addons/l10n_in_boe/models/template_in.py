from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('in', 'account.account')
    def _get_in_boe_account_account(self):
        return self._parse_csv('in', 'account.account', module='l10n_in_boe')
