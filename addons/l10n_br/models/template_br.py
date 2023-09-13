# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api
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
            'property_tax_payable_account_id': 'account_template_202011003',
            'property_tax_receivable_account_id': 'account_template_102010802',
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
            'sale': {'l10n_br_invoice_serial': '1'},
        }

    @api.model
    def _get_demo_data_move(self, company=False):
        move_data = super()._get_demo_data_move(company)
        if company.account_fiscal_country_id.code == 'BR':
            number = 0
            for move in move_data.values():
                # vendor bills must be manually numbered (l10n_br uses the standard AccountMove._is_manual_document_number())
                if move['move_type'] == 'in_invoice':
                    move['l10n_latam_document_number'] = f'{number:08d}'
                    number += 1

        return move_data
