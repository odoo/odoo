from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ar_ri', 'account.tax.group')
    def _get_ar_withholding_account_tax_group(self):
        return self._parse_csv('ar_ri', 'account.tax.group', module='l10n_ar_withholding')

    @template('ar_ri', 'account.tax')
    def _get_ar_withholding_account_tax(self):
        additionnal = self._parse_csv('ar_ri', 'account.tax', module='l10n_ar_withholding')
        self._deref_account_tags('ar_ri', additionnal)
        return additionnal
