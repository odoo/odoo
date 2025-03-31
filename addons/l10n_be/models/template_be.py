# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, _, models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('be')
    def _get_be_template_data(self):
        return {
            'name': _('Base'),
            'visible': False,
            'code_digits': '6',
            'property_account_receivable_id': 'a400',
            'property_account_payable_id': 'a440',
            'property_account_expense_categ_id': 'a600',
            'property_account_income_categ_id': 'a7000',
        }

    @template('be', 'res.company')
    def _get_be_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.be',
                'bank_account_code_prefix': '550',
                'cash_account_code_prefix': '570',
                'transfer_account_code_prefix': '580',
                'account_default_pos_receivable_account_id': 'a4001',
                'income_currency_exchange_account_id': 'a754',
                'expense_currency_exchange_account_id': 'a654',
                'account_journal_suspense_account_id': 'a499',
                'account_journal_early_pay_discount_loss_account_id': 'a657000',
                'account_journal_early_pay_discount_gain_account_id': 'a757000',
                'account_sale_tax_id': 'attn_VAT-OUT-21-L',
                'account_purchase_tax_id': 'attn_VAT-IN-V81-21',
                'default_cash_difference_income_account_id': 'a757100',
                'default_cash_difference_expense_account_id': 'a657100',
                'transfer_account_id': 'a58',
            },
        }

    @template('be', 'account.journal')
    def _get_be_account_journal(self):
        return {
            'sale': {'refund_sequence': True},
            'purchase': {'refund_sequence': True},
        }

    @template('be', 'account.reconcile.model')
    def _get_be_reconcile_model(self):
        return {
            'escompte_template': {
                'name': 'Cash Discount',
                'line_ids': [
                    Command.create({
                        'account_id': 'a653',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Cash Discount Granted',
                    }),
                ],
                'name@fr': 'Escompte',
                'name@nl': 'Betalingskorting',
                'name@de': 'Skonto',
            },
            'frais_bancaires_htva_template': {
                'name': 'Bank Fees (No VAT)',
                'line_ids': [
                    Command.create({
                        'account_id': 'a6560',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Bank Fees (No VAT)',
                    }),
                ],
                'name@fr': 'Frais bancaires (Hors TVA)',
                'name@nl': 'Bankkosten (Geen BTW)',
                'name@de': 'Bankgebühren (Ohne MwSt.)',
            },
        }
