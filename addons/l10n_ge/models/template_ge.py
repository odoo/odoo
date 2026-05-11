from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ge', 'account.journal')
    def _get_ge_account_journal(self):
        return {
            'bank': {
                'default_account_id': 'ge_account_120110',
            },
        }

    @template('ge', 'account.account')
    def _get_ge_coa_account_account(self):
        return {
            'ge_account_161003': {
                'account_stock_variation_id': 'ge_account_820510',
            },
        }

    @template('ge', 'res.company')
    def _get_ge_res_company(self):
        return {
            self.env.company.id: {
                'account_sale_tax_id': 'ge_vat_sale_18',
                'account_purchase_tax_id': 'ge_vat_purchase_18',
                'account_fiscal_country_id': 'base.ge',
                'bank_account_code_prefix': '120',
                'transfer_account_id': 'ge_account_100001',
                'account_journal_suspense_account_id': 'ge_account_120210',
                'receivable_account_id': 'ge_account_140110',
                'account_default_pos_receivable_account_id': 'ge_account_140120',
                'account_production_wip_account_id': 'ge_account_160230',
                'account_production_wip_overhead_account_id': 'ge_account_160610',
                'account_stock_valuation_id': 'ge_account_161003',
                'deferred_expense_account_id': 'ge_account_170910',
                'payable_account_id': 'ge_account_310110',
                'deferred_revenue_account_id': 'ge_account_310610',
                'income_account_id': 'ge_account_611101',
                'account_journal_early_pay_discount_loss_account_id': 'ge_account_710400',
                'expense_account_id': 'ge_account_749000',
                'income_currency_exchange_account_id': 'ge_account_810110',
                'default_cash_difference_income_account_id': 'ge_account_810210',
                'account_journal_early_pay_discount_gain_account_id': 'ge_account_810710',
                'expense_currency_exchange_account_id': 'ge_account_820110',
                'default_cash_difference_expense_account_id': 'ge_account_820210',
                'tax_exigibility': 'True',
            },
        }

    @template('ge')
    def _get_ge_template_data(self):
        return {
            'name': self.env._('Georgian Chart of Accounts (IFRS)'),
            'code_digits': 6,
        }

    def _get_account_parent_xmlid(self, code_prefix, template_code):
        if template_code == 'ge':
            return {
                '120': 'ge_account_120000',
            }.get(code_prefix)

        return super()._get_account_parent_xmlid(code_prefix, template_code)
