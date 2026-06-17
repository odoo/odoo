from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template('np')
    def _get_np_template_data(self):
        return {
            'name': _("Nepal Chart of Accounts"),
            'code_digits': '6',
        }

    @template('np', 'res.company')
    def _get_np_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.np',
                'bank_account_code_prefix': '1014',
                'cash_account_code_prefix': '1015',
                'transfer_account_code_prefix': '1017',
                'account_default_pos_receivable_account_id': 'pos_receivable',
                'income_currency_exchange_account_id': 'income_currency_exchange',
                'expense_currency_exchange_account_id': 'expense_currency_exchange',
                'default_cash_difference_income_account_id': 'cash_diff_income',
                'default_cash_difference_expense_account_id': 'cash_diff_expense',
                'account_journal_early_pay_discount_loss_account_id': 'cash_discount_loss',
                'account_journal_early_pay_discount_gain_account_id': 'cash_discount_gain',
                'expense_account_id': 'expense',
                'income_account_id': 'income',
                'receivable_account_id': 'receivable',
                'payable_account_id': 'payable',
                'deferred_expense_account_id': 'prepayments',
                'account_stock_valuation_id': 'stock_valuation',
                'account_production_wip_account_id': 'wip',
                'account_production_wip_overhead_account_id': 'cost_of_production',
            },
        }

    @template('np', 'account.account')
    def _get_np_account_account(self):
        return {
            'stock_valuation': {
                'account_stock_variation_id': 'stock_variation',
            },
        }
