from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('bn')
    def _get_bn_template_data(self):
        return {
            'property_account_receivable_id': 'bn_1025',
            'property_account_payable_id': 'bn_2023',
            'property_account_income_categ_id': 'bn_301',
            'property_account_expense_categ_id': 'bn_500',
            'code_digits': '6',
        }

    @template('bn', 'res.company')
    def _get_bn_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.bn',
                'bank_account_code_prefix': '1021',
                'cash_account_code_prefix': '1022',
                'transfer_account_code_prefix': '102300',
                'account_default_pos_receivable_account_id': 'bn_10231',
                'income_currency_exchange_account_id': 'bn_3036',
                'expense_currency_exchange_account_id': 'bn_519',
                'account_journal_early_pay_discount_loss_account_id': 'bn_52206',
                'account_journal_early_pay_discount_gain_account_id': 'bn_3039',
            },
        }
