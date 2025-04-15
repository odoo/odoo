from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('qa')
    def _get_qa_template_data(self):
        return {
            'property_account_receivable_id': 'qa_account_100201',
            'property_account_payable_id': 'qa_account_200101',
            'property_account_expense_categ_id': 'qa_account_500101',
            'property_account_income_categ_id': 'qa_account_400101',
            'property_account_expense_id': 'qa_account_500101',
            'property_account_income_id': 'qa_account_400101',
            'property_stock_valuation_account_id': 'qa_account_100502',
            'property_stock_account_input_categ_id': 'qa_account_100503',
            'property_stock_account_output_categ_id': 'qa_account_100504',
            'property_stock_account_production_cost_id': 'qa_account_100505',
            'code_digits': '6',
        }

    @template('qa', 'res.company')
    def _get_qa_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.qa',
                'bank_account_code_prefix': '1000',
                'cash_account_code_prefix': '1009',
                'transfer_account_code_prefix': '1001',
                'account_default_pos_receivable_account_id': 'qa_account_100202',
                'income_currency_exchange_account_id': 'qa_account_400301',
                'expense_currency_exchange_account_id': 'qa_account_500903',
                'account_journal_suspense_account_id': 'qa_account_100102',
                'account_journal_early_pay_discount_loss_account_id': 'qa_account_501107',
                'account_journal_early_pay_discount_gain_account_id': 'qa_account_400304',
                'account_journal_payment_debit_account_id': 'qa_account_100103',
                'account_journal_payment_credit_account_id': 'qa_account_100104',
                'default_cash_difference_income_account_id': 'qa_account_400302',
                'default_cash_difference_expense_account_id': 'qa_account_500909',
                'deferred_expense_account_id': 'qa_account_100416',
                'deferred_revenue_account_id': 'qa_account_200401',
            },
        }
