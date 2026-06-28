# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('hr')
    def _get_hr_template_data(self):
        return {
            'code_digits': '6',
        }

    @template('hr', 'res.company')
    def _get_hr_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.hr',
                'bank_account_code_prefix': '100',
                'cash_account_code_prefix': '102',
                'transfer_account_code_prefix': '1009',
                'account_default_pos_receivable_account_id': 'hr_120100',
                'income_currency_exchange_account_id': 'hr_772000',
                'expense_currency_exchange_account_id': 'hr_475000',
                'account_sale_tax_id': 'VAT_S_IN_ROC_25',
                'account_purchase_tax_id': 'VAT_P_IN_ROC_25',
                'expense_account_id': 'hr_400000',
                'income_account_id': 'hr_750000',
                'receivable_account_id': 'hr_120000',
                'payable_account_id': 'hr_220000',
            },
        }
