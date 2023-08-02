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
            'property_account_expense_categ_id': 'account_common_600',
            'property_account_income_categ_id': 'account_common_7000',
            'property_tax_payable_account_id': 'account_common_4750',
            'property_tax_receivable_account_id': 'account_common_4700',
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
                'account_journal_payment_debit_account_id': 'account_common_4312',
                'account_journal_payment_credit_account_id': 'account_common_411',
                'default_cash_difference_income_account_id': 'account_common_778',
                'default_cash_difference_expense_account_id': 'account_common_678',
                'account_sale_tax_id': 'account_tax_template_s_iva21b',
                'account_purchase_tax_id': 'account_tax_template_p_iva21_bc',
            },
        }
