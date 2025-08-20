# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('us')
    def _get_us_template_data(self):
        return {
            'property_account_receivable_id': 'account_account_us_receivable',
            'property_account_payable_id': 'account_account_us_payable',
        }

    @template('us', 'res.company')
    def _get_us_res_company(self):
        # Default to the right state taxes. If the company doesn't have their state
        # selected at the time the localization is installed, then it will default
        # to 6% as that is the most common tax (both by #states and population).
        default_sales_tax, default_purchase_tax = {
            'AL': ('account_tax_us_sale_4', 'account_tax_us_purchase_4'),
            'AK': ('account_tax_us_sale_0', 'account_tax_us_purchase_0'),
            'AZ': ('account_tax_us_sale_5_6', 'account_tax_us_purchase_5_6'),
            'AR': ('account_tax_us_sale_6_5', 'account_tax_us_purchase_6_5'),
            'CA': ('account_tax_us_sale_7_25', 'account_tax_us_purchase_7_25'),
            'CO': ('account_tax_us_sale_2_9', 'account_tax_us_purchase_2_9'),
            'CT': ('account_tax_us_sale_6_35', 'account_tax_us_purchase_6_35'),
            'DE': ('account_tax_us_sale_0', 'account_tax_us_purchase_0'),
            'FL': ('account_tax_us_sale_6', 'account_tax_us_purchase_6'),
            'GA': ('account_tax_us_sale_4', 'account_tax_us_purchase_4'),
            'HI': ('account_tax_us_sale_4', 'account_tax_us_purchase_4'),
            'ID': ('account_tax_us_sale_6', 'account_tax_us_purchase_6'),
            'IL': ('account_tax_us_sale_6_25', 'account_tax_us_purchase_6_25'),
            'IN': ('account_tax_us_sale_7', 'account_tax_us_purchase_7'),
            'IA': ('account_tax_us_sale_6', 'account_tax_us_purchase_6'),
            'KS': ('account_tax_us_sale_6_5', 'account_tax_us_purchase_6_5'),
            'KY': ('account_tax_us_sale_6', 'account_tax_us_purchase_6'),
            'LA': ('account_tax_us_sale_5', 'account_tax_us_purchase_5'),
            'ME': ('account_tax_us_sale_5_5', 'account_tax_us_purchase_5_5'),
            'MD': ('account_tax_us_sale_6', 'account_tax_us_purchase_6'),
            'MA': ('account_tax_us_sale_6_25', 'account_tax_us_purchase_6_25'),
            'MI': ('account_tax_us_sale_6', 'account_tax_us_purchase_6'),
            'MN': ('account_tax_us_sale_6_875', 'account_tax_us_purchase_6_875'),
            'MS': ('account_tax_us_sale_7', 'account_tax_us_purchase_7'),
            'MO': ('account_tax_us_sale_4_225', 'account_tax_us_purchase_4_225'),
            'MT': ('account_tax_us_sale_0', 'account_tax_us_purchase_0'),
            'NE': ('account_tax_us_sale_5_5', 'account_tax_us_purchase_5_5'),
            'NV': ('account_tax_us_sale_6_85', 'account_tax_us_purchase_6_85'),
            'NH': ('account_tax_us_sale_0', 'account_tax_us_purchase_0'),
            'NJ': ('account_tax_us_sale_6_625', 'account_tax_us_purchase_6_625'),
            'NM': ('account_tax_us_sale_4_875', 'account_tax_us_purchase_4_875'),
            'NY': ('account_tax_us_sale_4', 'account_tax_us_purchase_4'),
            'NC': ('account_tax_us_sale_4_75', 'account_tax_us_purchase_4_75'),
            'ND': ('account_tax_us_sale_5', 'account_tax_us_purchase_5'),
            'OH': ('account_tax_us_sale_5_75', 'account_tax_us_purchase_5_75'),
            'OK': ('account_tax_us_sale_4_5', 'account_tax_us_purchase_4_5'),
            'OR': ('account_tax_us_sale_0', 'account_tax_us_purchase_0'),
            'PA': ('account_tax_us_sale_6', 'account_tax_us_purchase_6'),
            'RI': ('account_tax_us_sale_7', 'account_tax_us_purchase_7'),
            'SC': ('account_tax_us_sale_6', 'account_tax_us_purchase_6'),
            'SD': ('account_tax_us_sale_4_2', 'account_tax_us_purchase_4_2'),
            'TN': ('account_tax_us_sale_7', 'account_tax_us_purchase_7'),
            'TX': ('account_tax_us_sale_6_25', 'account_tax_us_purchase_6_25'),
            'UT': ('account_tax_us_sale_6_1', 'account_tax_us_purchase_6_1'),
            'VT': ('account_tax_us_sale_6', 'account_tax_us_purchase_6'),
            'VA': ('account_tax_us_sale_5_3', 'account_tax_us_purchase_5_3'),
            'WA': ('account_tax_us_sale_6_5', 'account_tax_us_purchase_6_5'),
            'WV': ('account_tax_us_sale_6', 'account_tax_us_purchase_6'),
            'WI': ('account_tax_us_sale_5', 'account_tax_us_purchase_5'),
            'WY': ('account_tax_us_sale_4', 'account_tax_us_purchase_4'),
            'DC': ('account_tax_us_sale_6', 'account_tax_us_purchase_6'),
        }.get(self.env.company.state_id.code, ('account_tax_us_sale_6', 'account_tax_us_purchase_6'))
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.us',
                'bank_account_code_prefix': '1014',
                'cash_account_code_prefix': '1015',
                'transfer_account_code_prefix': '1017',
                'account_default_pos_receivable_account_id': 'account_account_us_pos_receivable',
                'income_currency_exchange_account_id': 'account_account_us_income_currency_exchange',
                'expense_currency_exchange_account_id': 'account_account_us_expense_currency_exchange',
                'default_cash_difference_income_account_id': 'account_account_us_cash_diff_income',
                'default_cash_difference_expense_account_id': 'account_account_us_cash_diff_expense',
                'account_journal_early_pay_discount_loss_account_id': 'account_account_us_cash_discount_loss',
                'account_journal_early_pay_discount_gain_account_id': 'account_account_us_cash_discount_gain',
                'expense_account_id': 'account_account_us_expense',
                'income_account_id': 'account_account_us_income',
                'account_sale_tax_id': default_sales_tax,
                'account_purchase_tax_id': default_purchase_tax,
            },
        }

    def _get_accounts_data_values(self, company, template_data, bank_prefix='', code_digits=0):
        accounts_data = super()._get_accounts_data_values(company, template_data, bank_prefix=bank_prefix, code_digits=code_digits)
        if company.account_fiscal_country_id.code == 'US':
            accounts_data['transfer_account_id'].update({
                'name': self.env._('Funds in Transit'),
            })
        return accounts_data
