# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('dz')
    def _get_dz_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_dz_413',
            'property_account_payable_id': 'l10n_dz_401',
            'code_digits': 6,
            'display_invoice_amount_total_words': True,
        }

    @template('dz', 'res.company')
    def _get_dz_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.dz',
                'bank_account_code_prefix': '512',
                'cash_account_code_prefix': '53',
                'transfer_account_code_prefix': '58',
                'account_default_pos_receivable_account_id': 'l10n_dz_412',
                'income_currency_exchange_account_id': 'l10n_dz_766',
                'expense_currency_exchange_account_id': 'l10n_dz_666',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_dz_709',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_dz_609',
                'default_cash_difference_income_account_id': 'l10n_dz_758',
                'default_cash_difference_expense_account_id': 'l10n_dz_657',
                'account_sale_tax_id': 'l10n_dz_vat_sale_19_prod',
                'account_purchase_tax_id': 'l10n_dz_vat_purchase_19',
                'expense_account_id': 'l10n_dz_600',
                'income_account_id': 'l10n_dz_700',
            },
        }
