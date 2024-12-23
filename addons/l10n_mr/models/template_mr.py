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
