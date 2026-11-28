# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

from odoo.addons.account.models.chart_template import template

# Accounts of the French chart that only apply in France: payroll and local taxes, CSE, employee
# profit-sharing, tax consolidation, ...
FRENCH_ONLY_ACCOUNTS = {
    'pcg_422', 'pcg_4246', 'pcg_4248', 'pcg_4284', 'pcg_4421', 'pcg_4422', 'pcg_4423', 'pcg_6311',
    'pcg_6314', 'pcg_6331', 'pcg_6332', 'pcg_6333', 'pcg_6334', 'pcg_6335', 'pcg_63511', 'pcg_63512',
    'pcg_63513', 'pcg_63514', 'pcg_6371', 'pcg_6472', 'pcg_691', 'pcg_6952', 'pcg_696', 'pcg_6981', 'pcg_6989',
}


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mc')
    def _get_mc_template_data(self):
        return {'code_digits': 6}

    @template('mc', 'res.company')
    def _get_mc_res_company(self):
        company_values = self._get_fr_comp_res_company()
        company_values[self.env.company.id]['account_fiscal_country_id'] = 'base.mc'
        return company_values

    @template('mc', 'account.journal')
    def _get_mc_account_journal(self):
        return {
            'sale': {'refund_sequence': True},
            'purchase': {'refund_sequence': True},
        }

    def _get_account_account(self, template_code):
        # EXTENDS account: the French chart for companies without the French-only accounts, completed by the CSV
        # of this module. Not a `@template('mc', 'account.account')` function: other modules (e.g. account_accountant)
        # read the whole chart from this method.
        if template_code != 'mc':
            return super()._get_account_account(template_code)
        accounts = self._parse_csv('fr_comp', 'account.account', module='l10n_fr_account')
        for xmlid in FRENCH_ONLY_ACCOUNTS:
            del accounts[xmlid]
        for data in (self._get_fr_account_account(), self._get_fr_comp_account_account(), super()._get_account_account('mc')):
            for xmlid, values in data.items():
                accounts[xmlid].update(values)
        return accounts
