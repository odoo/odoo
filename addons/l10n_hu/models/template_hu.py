# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('hu')
    def _get_hu_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_hu_311',
            'property_account_payable_id': 'l10n_hu_454',
            'property_account_expense_categ_id': 'l10n_hu_811',
            'property_account_income_categ_id': 'l10n_hu_911',
            'code_digits': '6',
        }

    @template('hu', 'res.company')
    def _get_hu_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.hu',
                'bank_account_code_prefix': '384',
                'cash_account_code_prefix': '381',
                'transfer_account_code_prefix': '389',
                'income_currency_exchange_account_id': 'l10n_hu_976',
                'expense_currency_exchange_account_id': 'l10n_hu_876',
            },
        }
