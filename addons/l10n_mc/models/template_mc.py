# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mc')
    def _get_mc_template_data(self):
        return {
            'name': 'Monaco',
            'code_digits': '6',
            'parent': 'fr',
        }

    @template('mc', 'account.account')
    def _get_mc_account_account(self):
        return self._parse_csv('fr', 'account.account', module='l10n_fr_account')

    @template('mc', 'account.group')
    def _get_mc_account_group(self):
        return self._parse_csv('fr', 'account.group', module='l10n_fr_account')

    @template('mc', 'account.tax.group')
    def _get_mc_account_tax_group(self):
        return self._parse_csv('fr', 'account.tax.group', module='l10n_fr_account')

    @template('mc', 'account.tax')
    def _get_mc_account_tax(self):
        tax_data = self._parse_csv('fr', 'account.tax', module='l10n_fr_account')
        self._deref_account_tags('fr', tax_data)
        return tax_data
