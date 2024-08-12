# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = ['account.chart.template']

    @template('kr')
    def _get_kr_template_data(self):
        return {
            'code_digits': '4',
            'property_account_receivable_id': 'l10n_kr_1089',
            'property_account_payable_id': 'l10n_kr_2519',
            'property_account_expense_categ_id': 'l10n_kr_5018',
            'property_account_income_categ_id': 'l10n_kr_4011',
        }

    @template('kr', 'res.company')
    def _get_kr_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.kr',
                'transfer_account_code_prefix': '130',
                'bank_account_code_prefix': '101',
                'account_default_pos_receivable_account_id': 'l10n_kr_1099',
                'income_currency_exchange_account_id': 'l10n_kr_9089',
                'expense_currency_exchange_account_id': 'l10n_kr_9339',
                'account_sale_tax_id': 'l10n_kr_sale_10',
            },
        }
