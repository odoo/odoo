# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('be')
    def _get_be_template_data(self):
        return {
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
                'name': 'Cash discount',
                'line_ids': [
                    Command.create({
                        'account_id': 'a653',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Escompte accordé',
                    }),
                ],
                'name@fr': 'Escompte',
                'name@nl': 'Betalingskorting',
                'name@de': 'Skonto',
            },
            'frais_bancaires_htva_template': {
                'name': 'Bank fees VAT excl.',
                'line_ids': [
                    Command.create({
                        'account_id': 'a6560',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Frais bancaires HTVA',
                    }),
                ],
                'name@fr': 'Frais bancaires HTVA',
                'name@nl': 'Bankkosten exclusief btw',
                'name@de': 'Bankgebühren exkl. MwSt.',
            },
            'frais_bancaires_tva21_template': {
                'name': 'Bank fees VAT 21 incl.',
                'line_ids': [
                    Command.create({
                        'account_id': 'a6560',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'attn_TVA-21-inclus-dans-prix',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Frais bancaires TVA21',
                    }),
                ],
                'name@fr': 'Frais bancaires TVA21',
                'name@nl': 'Bankkosten inclusief 21% btw',
                'name@de': 'Bankgebühren inkl. MwSt. 21 %',
            },
            'virements_internes_template': {
                'name': 'Internal transfers',
                'to_check': False,
                'line_ids': [
                    Command.create({
                        'account_id': 'a58',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Virements internes',
                    }),
                ],
                'name@fr': 'Virements internes',
                'name@nl': 'Interne overboekingen',
                'name@de': 'interne Überweisungen',
            },
        }
