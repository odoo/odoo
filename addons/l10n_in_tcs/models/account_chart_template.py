from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('in', 'account.account')
    def _get_in_tcs_account_account(self):
        if self.env.company.l10n_in_tcs:
            return self._parse_csv('in', 'account.account', module='l10n_in_tcs')

    @template('in', 'account.tax')
    def _get_in_tcs_account_tax(self):
        if self.env.company.l10n_in_tcs:
            tax_data = self._parse_csv('in', 'account.tax', module='l10n_in_tcs')
            self._deref_account_tags('in', tax_data)
            return tax_data
