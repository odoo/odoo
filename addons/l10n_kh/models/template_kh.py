# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('kh')
    def _get_kh_template_data(self):
        return {
            'code_digits': '5',
            'property_account_receivable_id': 'l10n_kh_account_10500',
            'property_account_payable_id': 'l10n_kh_account_20300',
            'property_stock_valuation_account_id': 'l10n_kh_account_10200',
            'property_stock_account_input_categ_id': 'l10n_kh_account_10210',
            'property_stock_account_output_categ_id': 'l10n_kh_account_10220',
        }

    @template('kh', 'res.company')
    def _get_kh_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.kh',
                'bank_account_code_prefix': '1090',
                'cash_account_code_prefix': '1080',
                'transfer_account_code_prefix': '1100',
                'transfer_account_id': 'l10n_kh_account_10902',
                'account_default_pos_receivable_account_id': 'l10n_kh_account_10501',
                'income_currency_exchange_account_id': 'l10n_kh_account_42800',
                'expense_currency_exchange_account_id': 'l10n_kh_account_61700',
                'account_journal_suspense_account_id': 'l10n_kh_account_10901',
                'default_cash_difference_expense_account_id': 'l10n_kh_account_61910',
                'default_cash_difference_income_account_id': 'l10n_kh_account_42910',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_kh_account_61900',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_kh_account_42900',
                'account_sale_tax_id': 'l10n_kh_tax_sale_10_m_t',
                'account_purchase_tax_id': 'l10n_kh_tax_purchase_10_m',
                'deferred_expense_account_id': 'l10n_kh_account_10700',
                'deferred_revenue_account_id': 'l10n_kh_account_20500',
                'expense_account_id': 'l10n_kh_account_50100',
                'income_account_id': 'l10n_kh_account_40100',
            },
        }

    @template('kh', 'account.journal')
    def _get_kh_account_journal(self):
        return {
            "bank": {"default_account_id": "l10n_kh_account_10900"},
            "cash": {
                "name": self.env._("Cash"),
                "type": "cash",
                "default_account_id": "l10n_kh_account_10800",
            },
        }
