# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('dk')
    def _get_dk_template_data(self):
        return {
            'property_account_receivable_id': 'a6610',
            'property_account_payable_id': 'a8440',
            'property_account_expense_categ_id': 'a2010',
            'property_account_income_categ_id': 'a1010',
            'property_stock_account_input_categ_id': 'a8450',
            'property_stock_account_output_categ_id': 'a6670',
            'property_stock_valuation_account_id': 'a6530',
            'property_tax_payable_account_id': 'a8798',
            'property_tax_receivable_account_id': 'a8798',
            'code_digits': '4',
        }

    @template('dk', 'res.company')
    def _get_dk_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.dk',
                'bank_account_code_prefix': '682',
                'cash_account_code_prefix': '681',
                'transfer_account_code_prefix': '683',
                'account_default_pos_receivable_account_id': 'a6611',
                'income_currency_exchange_account_id': 'a4670',
                'expense_currency_exchange_account_id': 'a4770',
                'account_journal_early_pay_discount_loss_account_id': 'a4760',
                'account_journal_early_pay_discount_gain_account_id': 'a4660',
            },
        }
