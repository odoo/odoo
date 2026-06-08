from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('bh')
    def _get_bh_template_data(self):
        return {
            'code_digits': '6',
        }

    @template('bh', 'res.company')
    def _get_bh_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.bh',
                'bank_account_code_prefix': '1000',
                'cash_account_code_prefix': '1009',
                'transfer_account_code_prefix': '1001',
                'account_default_pos_receivable_account_id': 'bh_account_100202',
                'income_currency_exchange_account_id': 'bh_account_400301',
                'expense_currency_exchange_account_id': 'bh_account_500903',
                'account_journal_suspense_account_id': 'bh_account_100102',
                'account_journal_early_pay_discount_loss_account_id': 'bh_account_501107',
                'account_journal_early_pay_discount_gain_account_id': 'bh_account_400304',
                'default_cash_difference_income_account_id': 'bh_account_400302',
                'default_cash_difference_expense_account_id': 'bh_account_500909',
                'deferred_expense_account_id': 'bh_account_100416',
                'deferred_revenue_account_id': 'bh_account_200401',
                'expense_account_id': 'bh_account_500101',
                'income_account_id': 'bh_account_400101',
                'receivable_account_id': 'bh_account_100201',
                'payable_account_id': 'bh_account_200101',
                'account_stock_valuation_id': 'bh_account_100502',
                'stock_account_production_cost_id': 'bh_account_100505',
            },
        }
