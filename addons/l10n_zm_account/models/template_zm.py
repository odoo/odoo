# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template('zm')
    def _get_zm_template_data(self):
        return {
            'code_digits': 7,
            'property_account_receivable_id': 'zm_account_8000000',
            'property_account_payable_id': 'zm_account_9000000',
        }

    @template('zm', 'res.company')
    def _get_zm_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.zm',
                'bank_account_code_prefix': '840000',
                'cash_account_code_prefix': '840000',
                'transfer_account_code_prefix': '840000',
                'income_currency_exchange_account_id': 'zm_account_4210000',
                'expense_currency_exchange_account_id': 'zm_account_4210000',
                'account_default_pos_receivable_account_id': 'zm_account_8100000',
                'account_journal_early_pay_discount_loss_account_id': 'zm_account_3550000',
                'account_journal_early_pay_discount_gain_account_id': 'zm_account_2700000',
                'deferred_expense_account_id': 'zm_account_8900000',
                'deferred_revenue_account_id': 'zm_account_9900000',
                'account_sale_tax_id': 'zm_tax_sale_16',
                'account_purchase_tax_id': 'zm_tax_purchase_16',
                'income_account_id': 'zm_account_1000000',
                'expense_account_id': 'zm_account_3800000',
            }
        }
