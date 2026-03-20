# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('gr')
    def _get_gr_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_gr_30_01_01_01',
            'property_account_payable_id': 'l10n_gr_50_01_01',
            'code_digits': '6',
        }

    @template('gr', 'res.company')
    def _get_gr_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.gr',
                'bank_account_code_prefix': '38.00.0',
                'cash_account_code_prefix': '38.00.0',
                'transfer_account_code_prefix': '38.00.0',
                'account_default_pos_receivable_account_id': 'l10n_gr_38_01',
                'income_currency_exchange_account_id': 'l10n_gr_73_01_01',
                'expense_currency_exchange_account_id': 'l10n_gr_62_01_01',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_gr_64_12_01',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_gr_70_01_03',
                'default_cash_difference_income_account_id': 'l10n_gr_71_06',
                'default_cash_difference_expense_account_id': 'l10n_gr_64_14',
                'account_sale_tax_id': 'l10n_gr_tax_s24_G',
                'account_purchase_tax_id': 'l10n_gr_tax_p24_G',
                'expense_account_id': 'l10n_gr_64_01_01_01',
                'income_account_id': 'l10n_gr_70_01_01',
            },
        }
