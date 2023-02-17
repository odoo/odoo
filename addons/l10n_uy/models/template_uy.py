# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('uy')
    def _get_uy_template_data(self):
        return {
            'property_account_receivable_id': 'uy_code_11300',
            'property_account_payable_id': 'uy_code_21100',
            'property_account_income_categ_id': 'uy_code_4100',
            'property_account_expense_categ_id': 'uy_code_5100',
            'code_digits': '6',
        }

    @template('uy', 'res.company')
    def _get_uy_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.uy',
                'bank_account_code_prefix': '1111',
                'cash_account_code_prefix': '1112',
                'transfer_account_code_prefix': '11120',
                'account_default_pos_receivable_account_id': 'uy_code_11307',
                'income_currency_exchange_account_id': 'uy_code_4302',
                'expense_currency_exchange_account_id': 'uy_code_5302',
                'account_journal_early_pay_discount_loss_account_id': 'uy_code_5303',
                'account_journal_early_pay_discount_gain_account_id': 'uy_code_4303',
            },
        }
