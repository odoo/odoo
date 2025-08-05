# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ke')
    def _get_ke_template_data(self):
        return {
            'property_account_receivable_id': 'ke1100',
            'property_account_payable_id': 'ke2100',
            'property_stock_valuation_account_id': 'ke1001',
            'code_digits': '6',
        }

    @template('ke', 'res.company')
    def _get_ke_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.ke',
                'bank_account_code_prefix': '12000',
                'cash_account_code_prefix': '12500',
                'transfer_account_code_prefix': '12100',
                'account_default_pos_receivable_account_id': 'ke110010',
                'income_currency_exchange_account_id': 'ke5144',
                'expense_currency_exchange_account_id': 'ke5144',
                'account_journal_early_pay_discount_loss_account_id': 'ke5147',
                'account_journal_early_pay_discount_gain_account_id': 'ke400710',
                'default_cash_difference_income_account_id': 'ke5146',
                'default_cash_difference_expense_account_id': 'ke5146',
                'account_sale_tax_id': 'ST16',
                'account_purchase_tax_id': 'PT16',
                'tax_exigibility': 'True',
                'expense_account_id': 'ke5001',
                'income_account_id': 'ke4001',
            },
        }
