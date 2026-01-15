# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('tn')
    def _get_tn_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_tn_4111',
            'property_account_payable_id': 'l10n_tn_4011',
            'code_digits': '6',
        }

    @template('tn', 'res.company')
    def _get_tn_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.tn',
                'bank_account_code_prefix': '5321',
                'cash_account_code_prefix': '5411',
                'transfer_account_code_prefix': '58',
                'account_default_pos_receivable_account_id': 'l10n_tn_5411',
                'income_currency_exchange_account_id': 'l10n_tn_756',
                'expense_currency_exchange_account_id': 'l10n_tn_655',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_tn_609',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_tn_709',
                'default_cash_difference_income_account_id': 'l10n_tn_756',
                'default_cash_difference_expense_account_id': 'l10n_tn_655',
                'account_sale_tax_id': 'l10n_tn_tax_vat_sale_19',
                'account_purchase_tax_id': 'l10n_tn_tax_vat_purchase_19_other_local',
                'expense_account_id': 'l10n_tn_607',
                'income_account_id': 'l10n_tn_707',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'l10n_tn_311',
            },
        }

    @template('tn', 'account.account')
    def _get_tn_account_account(self):
        return {
            'l10n_tn_311': {
                'account_stock_expense_id': 'l10n_tn_601',
                'account_stock_variation_id': 'l10n_tn_6031',
            },
        }
