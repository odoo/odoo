# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ve_nif')
    def _get_ve_nif_template_data(self):
        return {
            'name': _('VEN-NIF (6 digits)'),
            'code_digits': '6',
            'sequence': 20,
        }

    @template('ve_nif', 'res.company')
    def _get_ve_nif_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ve',
                'bank_account_code_prefix': '1014',
                'cash_account_code_prefix': '1015',
                'transfer_account_code_prefix': '1013',
                'account_journal_suspense_account_id': 've_nif_101201',
                'account_journal_early_pay_discount_gain_account_id': 've_nif_430104',
                'account_journal_early_pay_discount_loss_account_id': 've_nif_650106',
                'default_cash_difference_income_account_id': 've_nif_430103',
                'default_cash_difference_expense_account_id': 've_nif_650105',
                'account_default_pos_receivable_account_id': 've_nif_110102',
                'income_currency_exchange_account_id': 've_nif_430101',
                'expense_currency_exchange_account_id': 've_nif_650104',
                'account_sale_tax_id': 've_nif_tax_iva16_sale',
                'account_purchase_tax_id': 've_nif_tax_iva16_purchase',
                'expense_account_id': 've_nif_510101',
                'income_account_id': 've_nif_410101',
                'receivable_account_id': 've_nif_110101',
                'payable_account_id': 've_nif_210101',
                'account_stock_valuation_id': 've_nif_120101',
            },
        }

    @template('ve_nif', 'account.account')
    def _get_ve_nif_account_account(self):
        return {
            've_nif_120101': {
                'account_stock_variation_id': 've_nif_520102',
            },
        }
