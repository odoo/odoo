from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('syscohada')
    def _get_syscohada_template_data(self):
        return {
            'property_account_receivable_id': 'pcg_4111',
            'property_account_payable_id': 'pcg_4011',
            'name': 'SYSCOHADA - Revised',
            'code_digits': '6',
        }

    @template('syscohada', 'res.company')
    def _get_syscohada_res_company(self):
        return {
            self.env.company.id: {
                'bank_account_code_prefix': '521',
                'cash_account_code_prefix': '571',
                'transfer_account_code_prefix': '585',
                'account_default_pos_receivable_account_id': 'pcg_4113',
                'income_currency_exchange_account_id': 'pcg_776',
                'expense_currency_exchange_account_id': 'pcg_676',
                'account_journal_early_pay_discount_loss_account_id': 'pcg_6019',
                'account_journal_early_pay_discount_gain_account_id': 'pcg_7019',
                'expense_account_id': 'pcg_6011',
                'income_account_id': 'pcg_7011',
            },
        }
