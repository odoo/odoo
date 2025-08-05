# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('bo')
    def _get_bo_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'l10n_bo_1121',
            'property_account_payable_id': 'l10n_bo_2121',
            'property_stock_valuation_account_id': 'l10n_bo_1131',
        }

    @template('bo', 'res.company')
    def _get_bo_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.bo',
                'bank_account_code_prefix': '11130',
                'cash_account_code_prefix': '11110',
                'transfer_account_code_prefix': '11110',
                'account_default_pos_receivable_account_id': 'l10n_bo_11211',
                'income_currency_exchange_account_id': 'l10n_bo_4303',
                'expense_currency_exchange_account_id': 'l10n_bo_5602',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_bo_5104',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_bo_4102',
                'default_cash_difference_income_account_id': 'l10n_bo_4301',
                'default_cash_difference_expense_account_id': 'l10n_bo_5601',
                'account_sale_tax_id': 'l10n_bo_iva_13_sale',
                'account_purchase_tax_id': 'l10n_bo_iva_13_purchase',
                'income_account_id': 'l10n_bo_4101',
                'expense_account_id': 'l10n_bo_53008',
            },
        }
