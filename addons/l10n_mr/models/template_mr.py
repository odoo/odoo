from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mr')
    def _get_mr_template_data(self):
        return {
            'code_digits': '8',
            'property_account_receivable_id': 'mr_4150',
            'property_account_payable_id': 'mr_4050',
        }

    @template('mr', 'res.company')
    def _get_mr_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.mr',
                'bank_account_code_prefix': '5500',
                'cash_account_code_prefix': '5600',
                'transfer_account_code_prefix': '58',
                'income_currency_exchange_account_id': 'mr_7780',
                'expense_currency_exchange_account_id': 'mr_6780',
                'account_sale_tax_id': 'vat_out_10_16',
                'account_purchase_tax_id': 'vat_in_60_16',
                'expense_account_id': 'mr_6000',
                'income_account_id': 'mr_7000',
            },
        }

    @template('mr', 'account.account')
    def _get_mr_account_account(self):
        return {
            'mr_210681': {'asset_depreciation_account_id': 'mr_2811', 'asset_expense_account_id': 'mr_68012'},
            'mr_2120': {'asset_depreciation_account_id': 'mr_2812', 'asset_expense_account_id': 'mr_68012'},
            'mr_21205': {'asset_depreciation_account_id': 'mr_2812', 'asset_expense_account_id': 'mr_68012'},
            'mr_21208': {'asset_depreciation_account_id': 'mr_2813', 'asset_expense_account_id': 'mr_68012'},
            'mr_2122': {'asset_depreciation_account_id': 'mr_28122', 'asset_expense_account_id': 'mr_68012'},
            'mr_2125': {'asset_depreciation_account_id': 'mr_28125', 'asset_expense_account_id': 'mr_68012'},
            'mr_2140': {'asset_depreciation_account_id': 'mr_2814', 'asset_expense_account_id': 'mr_68012'},
            'mr_2150': {'asset_depreciation_account_id': 'mr_2815', 'asset_expense_account_id': 'mr_68012'},
            'mr_2160': {'asset_depreciation_account_id': 'mr_2816', 'asset_expense_account_id': 'mr_68012'},
            'mr_2170': {'asset_depreciation_account_id': 'mr_2817', 'asset_expense_account_id': 'mr_68012'},
            'mr_2180': {'asset_depreciation_account_id': 'mr_2818', 'asset_expense_account_id': 'mr_68012'},
            'mr_2181': {'asset_depreciation_account_id': 'mr_28181', 'asset_expense_account_id': 'mr_68012'},
            'mr_2182': {'asset_depreciation_account_id': 'mr_28182', 'asset_expense_account_id': 'mr_68012'},
            'mr_2183': {'asset_depreciation_account_id': 'mr_28183', 'asset_expense_account_id': 'mr_68012'},
            'mr_2200': {'asset_depreciation_account_id': 'mr_2820', 'asset_expense_account_id': 'mr_68012'},
        }
