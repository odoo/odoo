# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('co', 'account.tax')
    def _get_co_edi_account_tax(self):
        return self._parse_csv('co', 'account.tax', module='l10n_co_edi')

    @template('co', 'account.tax.group')
    def _get_co_edi_account_tax_group(self):
        return self._parse_csv('co', 'account.tax.group', module='l10n_co_edi')
