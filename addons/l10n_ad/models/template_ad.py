# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ad')
    def _get_ad_template_data(self):
        return {
            'property_account_receivable_id': 'account_account_430',
            'property_account_payable_id': 'account_account_410',
            'property_account_expense_categ_id': 'account_account_600',
            'property_account_income_categ_id': 'account_account_700',
        }

    @template('ad', 'res.company')
    def _get_ad_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ad',
                'bank_account_code_prefix': '572',
                'cash_account_code_prefix': '570',
                'transfer_account_code_prefix': '57299',
                'account_default_pos_receivable_account_id': '430',
                'income_currency_exchange_account_id': '768',
                'expense_currency_exchange_account_id': '668',
                'account_journal_suspense_account_id': '572998',
                'account_journal_early_pay_discount_loss_account_id': '606',
                'account_journal_early_pay_discount_gain_account_id': '706',
                'account_journal_payment_debit_account_id': '4312',
                'account_journal_payment_credit_account_id': '411',
                'default_cash_difference_income_account_id': '778',
                'default_cash_difference_expense_account_id': '678',
                'account_sale_tax_id': 'account_tax_template_s_igi4-5',
                'account_purchase_tax_id': 'account_tax_template_p_igi4-5',
                'deferred_expense_account_id': '480',
                'deferred_revenue_account_id': '485',
            },
        }
