# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pa')
    def _get_pa_template_data(self):
        return {
            'code_digits': '9',
        }

    @template('pa', 'res.company')
    def _get_pa_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.pa',
                'bank_account_code_prefix': '1.1.01.1',
                'cash_account_code_prefix': '1.1.01.2',
                'transfer_account_code_prefix': '1.1.01.9',
                'account_default_pos_receivable_account_id': '1_1_02_02',
                'income_currency_exchange_account_id': '4_2_04_01',
                'expense_currency_exchange_account_id': '5_4_01_02',
                'account_sale_tax_id': 'itbms_7_sale',
                'account_purchase_tax_id': 'itbms_7_purchase',
                'expense_account_id': '5_1_01_02',
                'income_account_id': '4_1_01_01',
                'receivable_account_id': '1_1_02_01',
                'payable_account_id': '2_1_01_01',
            },
        }

    @template('pa', 'account.account')
    def _get_pa_account_account(self):
        asset_accounts = {
            'asset_depreciation_account_id': '1_2_02_99',
            'asset_expense_account_id': '5_3_01_01',
        }
        return {
            '1_2_02_01': asset_accounts,
            '1_2_02_02': asset_accounts,
            '1_2_02_03': asset_accounts,
            '1_2_02_04': asset_accounts,
            '1_2_02_05': asset_accounts,
            '1_2_02_07': asset_accounts,
            '1_2_02_08': asset_accounts,
            '1_2_02_09': asset_accounts,
        }
