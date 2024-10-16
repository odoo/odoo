from odoo import models
from odoo.addons.account.models.chart_template import template
from odoo.addons import l10n_in


class AccountChartTemplate(l10n_in.AccountChartTemplate):

    @template('in', 'account.account')
    def _get_in_withholding_account_account(self):
        return self._parse_csv('in', 'account.account', module='l10n_in_withholding')

    @template('in', 'account.tax')
    def _get_in_withholding_account_tax(self):
        tax_data = self._parse_csv('in', 'account.tax', module='l10n_in_withholding')
        self._deref_account_tags('in', tax_data)
        return tax_data

    @template('in', 'res.company')
    def _get_in_base_res_company(self):
        return {
            self.env.company.id: {
                'l10n_in_withholding_account_id': 'p100595',
            },
        }
