# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_common')
    def _get_es_common_template_data(self):
        return {
            'name': _('Common'),
            'visible': 0,
            'property_account_receivable_id': 'account_common_4300',
            'property_account_payable_id': 'account_common_4100',
        }

    @template('es_common', 'res.company')
    def _get_es_common_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.es',
                'bank_account_code_prefix': '572',
                'cash_account_code_prefix': '570',
                'transfer_account_code_prefix': '57299',
                'account_default_pos_receivable_account_id': 'account_common_4301',
                'income_currency_exchange_account_id': 'account_common_768',
                'expense_currency_exchange_account_id': 'account_common_668',
                'account_journal_suspense_account_id': 'account_common_572998',
                'account_journal_early_pay_discount_loss_account_id': 'account_common_6060',
                'account_journal_early_pay_discount_gain_account_id': 'account_common_7060',
                'default_cash_difference_income_account_id': 'account_common_778',
                'default_cash_difference_expense_account_id': 'account_common_678',
                'deferred_expense_account_id': 'account_common_480',
                'deferred_revenue_account_id': 'account_common_485',
                'expense_account_id': 'account_common_600',
                'income_account_id': 'account_common_7000',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'account_common_310',
            },
        }

    @template('es_common', 'account.account')
    def _get_es_common_account_account(self):
        return {
            'account_common_310': {
                'account_stock_expense_id': 'account_common_601',
                'account_stock_variation_id': 'account_common_611',
            },
        }
