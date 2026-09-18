# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pt', 'account.tax')
    def _get_pt_certification_account_tax(self):
        return self._parse_csv('pt', 'account.tax', module='l10n_pt_certification')

    @template('pt', 'account.tax.group')
    def _get_pt_certification_account_tax_group(self):
        return self._parse_csv('pt', 'account.tax.group', module='l10n_pt_certification')
