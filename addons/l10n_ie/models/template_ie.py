# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ie')
    def _get_ie_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_ie_account_2100',
            'property_account_payable_id': 'l10n_ie_account_34',
            'property_account_expense_categ_id': 'l10n_ie_account_60',
            'property_account_income_categ_id': 'l10n_ie_account_70',
            'property_stock_valuation_account_id': 'l10n_ie_account_630',
            'property_advance_tax_payment_account_id': 'l10n_ie_account_2132',
            'property_tax_payable_account_id': 'l10n_ie_account_3804',
            'property_tax_receivable_account_id': 'l10n_ie_account_2131',
            'use_anglo_saxon': False,
            'code_digits': '6',
        }

    @template('ie', 'res.company')
    def _get_ie_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ie',
                'bank_account_code_prefix': '230',
                'cash_account_code_prefix': '231',
                'transfer_account_code_prefix': '232',
                'account_default_pos_receivable_account_id': 'l10n_ie_account_2101',
                'income_currency_exchange_account_id': 'l10n_ie_account_761',
                'expense_currency_exchange_account_id': 'l10n_ie_account_661',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_ie_account_640',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_ie_account_730',
                'default_cash_difference_expense_account_id': 'l10n_ie_account_641',
                'default_cash_difference_income_account_id': 'l10n_ie_account_731',
                'account_sale_tax_id': 'ie_tax_sale_goods_23',
                'account_purchase_tax_id': 'ie_tax_purchase_goods_23',
            },
        }
