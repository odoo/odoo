from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('it', 'account.account')
    def _get_it_withholding_account_account(self):
        return self._parse_csv('it', 'account.account', module='l10n_it_edi')

    @template('it', 'account.tax')
    def _get_it_withholding_account_tax(self):
        additional = self._parse_csv('it', 'account.tax', module='l10n_it_edi')
        self._deref_account_tags('it', additional)
        return additional

    @template('it', 'account.tax.group')
    def _get_it_withholding_account_tax_group(self):
        return self._parse_csv('it', 'account.tax.group', module='l10n_it_edi')
