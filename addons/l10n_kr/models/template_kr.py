# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('kr')
    def _get_kr_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'l10n_kr_111301',
            'property_account_payable_id': 'l10n_kr_212001',
            'property_stock_valuation_account_id': 'l10n_kr_112101',
            'property_stock_account_production_cost_id': 'l10n_kr_112704',
        }

    @template('kr', 'res.company')
    def _get_kr_res_company(self):
        return {
            self.env.company.id: {
                'account_price_include': 'tax_included',
                'account_fiscal_country_id': 'base.kr',
                'transfer_account_code_prefix': '1116',
                'bank_account_code_prefix': '1111',
                'account_default_pos_receivable_account_id': 'l10n_kr_111303',
                'income_currency_exchange_account_id': 'l10n_kr_420007',
                'expense_currency_exchange_account_id': 'l10n_kr_620007',
                'transfer_account_id': 'l10n_kr_111611',
                'account_journal_suspense_account_id': 'l10n_kr_111610',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_kr_410003',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_kr_410008',
                'account_sale_tax_id': 'l10n_kr_sale_10',
                'account_purchase_tax_id': 'l10n_kr_purchase_10',
                'deferred_expense_account_id': 'l10n_kr_111401',
                'deferred_revenue_account_id': 'l10n_kr_216005',
                'account_production_wip_account_id': 'l10n_kr_112401',
                'account_production_wip_overhead_account_id': 'l10n_kr_610013',
                'default_cash_difference_income_account_id': 'l10n_kr_420013',
                'default_cash_difference_expense_account_id': 'l10n_kr_620014',
                'expense_account_id': 'l10n_kr_510001',
                'income_account_id': 'l10n_kr_410001',
            },
        }
