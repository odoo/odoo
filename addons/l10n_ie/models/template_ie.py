# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ie')
    def _get_ie_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_ie_a9999',
            'property_account_payable_id': 'l10n_ie_a9998',
            'property_account_expense_categ_id': 'l10n_ie_a9995',
            'property_account_income_categ_id': 'l10n_ie_a9996',
            'code_digits': '6',
        }

    @template('ie', 'res.company')
    def _get_ie_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ie',
                'bank_account_code_prefix': '1200',
                'cash_account_code_prefix': '1210',
                'transfer_account_code_prefix': '1220',
                'account_default_pos_receivable_account_id': 'l10n_ie_a9990',
                'income_currency_exchange_account_id': 'l10n_ie_a7700',
                'expense_currency_exchange_account_id': 'l10n_ie_a7700',
            },
        }
