# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ee')
    def _get_ee_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_ee_10200',
            'property_account_payable_id': 'l10n_ee_2010',
            'property_account_income_categ_id': 'l10n_ee_40000',
            'property_account_expense_categ_id': 'l10n_ee_50',
            'code_digits': '6',
        }

    @template('ee', 'res.company')
    def _get_ee_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ee',
                'bank_account_code_prefix': '1001',
                'cash_account_code_prefix': '1000',
                'transfer_account_code_prefix': '1008',
                'account_default_pos_receivable_account_id': 'l10n_ee_10201',
                'income_currency_exchange_account_id': 'l10n_ee_422',
                'expense_currency_exchange_account_id': 'l10n_ee_673',
                'account_journal_suspense_account_id': 'l10n_ee_1009',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_ee_6850',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_ee_430',
                'default_cash_difference_income_account_id': 'l10n_ee_420',
                'default_cash_difference_expense_account_id': 'l10n_ee_671',
                'account_sale_tax_id': 'l10n_ee_vat_out_20_g',
                'account_purchase_tax_id': 'l10n_ee_vat_in_20_g',
            },
        }
