# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('nz')
    def _get_nz_template_data(self):
        return {
            'code_digits': '5',
            'use_anglo_saxon': True,
            'property_account_receivable_id': 'nz_11200',
            'property_account_payable_id': 'nz_21200',
            'property_account_expense_categ_id': 'nz_51110',
            'property_account_income_categ_id': 'nz_41110',
            'property_stock_account_input_categ_id': 'nz_21210',
            'property_stock_account_output_categ_id': 'nz_11340',
            'property_stock_valuation_account_id': 'nz_11330',
        }

    @template('nz', 'res.company')
    def _get_nz_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.nz',
                'bank_account_code_prefix': '1111',
                'cash_account_code_prefix': '1113',
                'transfer_account_code_prefix': '11170',
                'account_default_pos_receivable_account_id': 'nz_11220',
                'income_currency_exchange_account_id': 'nz_61630',
                'expense_currency_exchange_account_id': 'nz_61630',
                'account_journal_early_pay_discount_loss_account_id': 'nz_61610',
                'account_journal_early_pay_discount_gain_account_id': 'nz_61620',
            },
        }
