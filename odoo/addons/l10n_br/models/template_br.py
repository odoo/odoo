# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('br')
    def _get_br_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'account_template_101010401',
            'property_account_payable_id': 'account_template_201010301',
            'property_account_expense_categ_id': 'account_template_30101030101',
            'property_account_income_categ_id': 'account_template_30101010105',
        }

    @template('br', 'res.company')
    def _get_br_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.br',
                'bank_account_code_prefix': '1.01.01.02.00',
                'cash_account_code_prefix': '1.01.01.01.00',
                'transfer_account_code_prefix': '1.01.01.12.00',
                'account_default_pos_receivable_account_id': 'account_template_101010402',
                'income_currency_exchange_account_id': 'br_3_01_01_05_01_47',
                'expense_currency_exchange_account_id': 'br_3_11_01_09_01_40',
                'account_journal_early_pay_discount_loss_account_id': 'account_template_31101010202',
                'account_journal_early_pay_discount_gain_account_id': 'account_template_30101050148',
                'account_sale_tax_id': 'tax_template_out_icms_interno17',
                'account_purchase_tax_id': 'tax_template_in_icms_interno17',
            },
        }

    @template('br', 'account.journal')
    def _get_br_account_journal(self):
        return {
            'sale': {
                'l10n_br_invoice_serial': '1',
                'refund_sequence': False,
            },
        }
