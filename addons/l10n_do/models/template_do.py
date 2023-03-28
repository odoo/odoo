# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('do')
    def _get_do_template_data(self):
        return {
            'code_digits': '8',
            'use_anglo_saxon': True,
            'property_account_receivable_id': 'l10n_do_11030201',
            'property_account_payable_id': 'l10n_do_21010200',
            'property_account_income_categ_id': 'l10n_do_41010100',
            'property_account_expense_categ_id': 'l10n_do_51010100',
            'property_stock_account_input_categ_id': 'l10n_do_21021200',
            'property_stock_account_output_categ_id': 'l10n_do_11050600',
            'property_stock_valuation_account_id': 'l10n_do_11050100',
        }

    @template('do', 'res.company')
    def _get_do_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.do',
                'bank_account_code_prefix': '110102',
                'cash_account_code_prefix': '110101',
                'transfer_account_code_prefix': '11010100',
                'account_default_pos_receivable_account_id': 'l10n_do_11030210',
                'income_currency_exchange_account_id': 'l10n_do_42040100',
                'expense_currency_exchange_account_id': 'l10n_do_61070800',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_do_61081000',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_do_42040400',
                'default_cash_difference_income_account_id': 'l10n_do_42040400',
                'default_cash_difference_expense_account_id': 'l10n_do_61081000',
            },
        }
