# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mz')
    def _get_mz_template_data(self):
        return {
            'code_digits': '7',
            'property_account_receivable_id': 'l10n_mz_account_411',
            'property_account_payable_id': 'l10n_mz_account_421',
            'property_account_expense_categ_id': 'l10n_mz_account_61161',
            'property_account_income_categ_id': 'l10n_mz_account_711',
        }

    @template('mz', 'res.company')
    def _get_mz_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.mz',
                'bank_account_code_prefix': '12',
                'cash_account_code_prefix': '11',
                'transfer_account_code_prefix': '456',
                'account_default_pos_receivable_account_id': 'l10n_mz_account_413',
                'income_currency_exchange_account_id': 'l10n_mz_account_7841',
                'expense_currency_exchange_account_id': 'l10n_mz_account_6941',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_mz_account_695',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_mz_account_785',
                'account_sale_tax_id': 'vat_sale_16',
                'account_purchase_tax_id': 'vat_purch_16_inventories',
            },
        }
