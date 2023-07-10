# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('it', 'account.tax')
    def _get_it_split_payment_account_tax(self):
        additionnal = self._parse_csv('it', 'account.tax', module='l10n_it_edi_split_payment')
        self._deref_account_tags('it', additionnal)
        return additionnal

    @template('it', 'account.tax.group')
    def _get_it_split_payment_account_tax_group(self):
        return self._parse_csv('it', 'account.tax.group', module='l10n_it_edi_split_payment')

    @template('it', 'account.fiscal.position')
    def _get_it_split_payment_account_fiscal_position(self):
        return self._parse_csv('it', 'account.fiscal.position', module='l10n_it_edi_split_payment')
