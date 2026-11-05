from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('az')
    def _get_az_template_data(self):
        return {
            'name': self.env._('Azerbaijani Chart of Accounts (IFRS)'),
            'code_digits': 5,
        }

    @template('az', 'account.journal')
    def _get_az_account_journal(self):
        return {
            'bank': {
                'default_account_id': 'az_account_22310',
            },
        }

    @template('az', 'account.account')
    def _get_az_account_account(self):
        return {
            'az_account_20500': {
                'account_stock_variation_id': 'az_account_73120',
            },
        }

    @template('az', 'res.company')
    def _get_az_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.az',
                'bank_account_code_prefix': '223',
                'cash_account_code_prefix': '221',
                'transfer_account_code_prefix': '222',
                'account_sale_tax_id': 'az_tax_sale_vat_18_group',
                'account_purchase_tax_id': 'az_tax_purchase_vat_18',
                'tax_exigibility': 'True',
                'receivable_account_id': 'az_account_21100',
                'payable_account_id': 'az_account_53100',
                'account_default_pos_receivable_account_id': 'az_account_21110',
                'transfer_account_id': 'az_account_22200',
                'account_journal_suspense_account_id': 'az_account_22350',
                'income_account_id': 'az_account_60110',
                'expense_account_id': 'az_account_73199',
                'account_journal_early_pay_discount_gain_account_id': 'az_account_60300',
                'account_journal_early_pay_discount_loss_account_id': 'az_account_71150',
                'income_currency_exchange_account_id': 'az_account_61180',
                'expense_currency_exchange_account_id': 'az_account_73180',
                'default_cash_difference_income_account_id': 'az_account_63160',
                'default_cash_difference_expense_account_id': 'az_account_71160',
                'deferred_expense_account_id': 'az_account_24299',
                'deferred_revenue_account_id': 'az_account_54200',
                'account_stock_valuation_id': 'az_account_20500',
                'account_production_wip_account_id': 'az_account_20210',
                'account_production_wip_overhead_account_id': 'az_account_20200',
            },
        }
