# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pk')
    def _get_pk_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_pk_1121001',
            'property_account_payable_id': 'l10n_pk_2221001',
            'code_digits': '7',
        }

    @template('pk', 'res.company')
    def _get_pk_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.pk',
                'bank_account_code_prefix': '112600',
                'cash_account_code_prefix': '112600',
                'transfer_account_code_prefix': '112600',
                'account_default_pos_receivable_account_id': 'l10n_pk_1121001',
                'account_journal_suspense_account_id': 'l10n_pk_2226000',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_pk_4411003',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_pk_3112004',
                'account_sale_tax_id': 'pk_sales_tax_17',
                'account_purchase_tax_id': 'purchases_tax_17',
                'income_account_id': 'l10n_pk_3111001',
                'expense_account_id': 'l10n_pk_4111001',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'l10n_pk_1125001',
            },
        }

    @template('pk', 'account.account')
    def _get_pk_account_account(self):
        return {
            'l10n_pk_1125001': {
                'account_stock_variation_id': 'l10n_pk_4111001',
            },
        }
