# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('jp')
    def _get_jp_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'l10n_jp_126000',
            'property_account_payable_id': 'l10n_jp_220000',
            'property_stock_valuation_account_id': 'l10n_jp_121100',
        }

    @template('jp', 'res.company')
    def _get_jp_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.jp',
                'bank_account_code_prefix': '1202',
                'cash_account_code_prefix': '1201',
                'transfer_account_code_prefix': '1236',
                'transfer_account_id': 'l10n_jp_123600',
                'account_default_pos_receivable_account_id': 'l10n_jp_126200',
                'income_currency_exchange_account_id': 'l10n_jp_425700',
                'expense_currency_exchange_account_id': 'l10n_jp_513500',
                'account_journal_suspense_account_id': 'l10n_jp_123900',
                'default_cash_difference_expense_account_id': 'l10n_jp_510100',
                'default_cash_difference_income_account_id': 'l10n_jp_999002',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_jp_510200',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_jp_425000',
                'account_sale_tax_id': 'l10n_jp_tax_sale_exc_10',
                'account_purchase_tax_id': 'l10n_jp_tax_purchase_exc_10',
                'expense_account_id': 'l10n_jp_510000',
                'income_account_id': 'l10n_jp_410000',
                'tax_calculation_rounding_method': 'round_globally',
            },
        }
