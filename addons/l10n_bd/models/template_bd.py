# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('bd')
    def _get_bd_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_bd_100201',
            'property_account_payable_id': 'l10n_bd_200101',
        }

    @template('bd', 'res.company')
    def _get_bd_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.bd',
                'bank_account_code_prefix': '10010',
                'cash_account_code_prefix': '10010',
                'account_default_pos_receivable_account_id': 'l10n_bd_100202',
                'account_journal_suspense_account_id': 'l10n_bd_100102',
                'default_cash_difference_income_account_id': 'l10n_bd_400302',
                'default_cash_difference_expense_account_id': 'l10n_bd_500909',
                'income_currency_exchange_account_id': 'l10n_bd_400301',
                'expense_currency_exchange_account_id': 'l10n_bd_500903',
                'transfer_account_id': 'l10n_bd_100101',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_bd_501107',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_bd_400304',
                'account_sale_tax_id': 'VAT_S_IN_BD_10',
                'account_purchase_tax_id': 'VAT_P_IN_BD_10',
                'income_account_id': 'l10n_bd_400100',
                'expense_account_id': 'l10n_bd_500200',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'l10n_bd_100502',
            },
        }

    @template('bd', 'account.journal')
    def _get_bd_account_journal(self):
        return {
            "tax_adjustment": {
                "name": "Tax Adjustments",
                "code": "TA",
                "type": "general",
                "show_on_dashboard": True,
            },
        }

    @template('bd', 'account.account')
    def _get_bd_account_account(self):
        return {
            'l10n_bd_100502': {
                'account_stock_expense_id': 'l10n_bd_500907',
                'account_stock_variation_id': 'l10n_bd_500905',
            },
        }
