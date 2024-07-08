from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('in', 'account.account')
    def _get_in_tcs_account_account(self):
        return self._parse_csv('in', 'account.account', module='l10n_in_tcs')

    @template('in', 'account.tax.group')
    def _get_in_tcs_account_tax_group(self):
        return self._parse_csv('in', 'account.tax.group', module='l10n_in_tcs')

    @template('in', 'account.tax')
    def _get_in_tcs_account_tax(self):
        additional = self._parse_csv('in', 'account.tax', module='l10n_in_tcs')
        self._deref_account_tags('in', additional)
        return additional
