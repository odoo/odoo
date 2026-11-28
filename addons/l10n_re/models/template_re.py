from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('re', 'account.fiscal.position')
    def _get_re_account_fiscal_position(self):
        return self._parse_csv('re', 'account.fiscal.position', module='l10n_re')

    @template('re', 'account.tax')
    def _get_re_account_tax(self):
        return self._parse_csv('re', 'account.tax', module='l10n_re')
