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
            'downpayment_account_id': 'a46',
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
                'account_purchase_receipt_fiscal_position_id': 'fiscal_position_template_6',
                'default_cash_difference_income_account_id': 'a757100',
                'default_cash_difference_expense_account_id': 'a657100',
                'transfer_account_id': 'a58',
                'expense_account_id': 'a600',
                'income_account_id': 'a7000',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'a300',
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
        }

    def _get_bank_fees_reco_account(self, company):
        # Belgian account for the bank fees reco model. We need to be as precise
        # as possible in case it's modified so it's missing and not replaced.
        be_account = self.with_company(company).ref('a6560', raise_if_not_found=False)
        return be_account or super()._get_bank_fees_reco_account(company)

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        if template_code in ('be_comp', 'be_asso') and \
                (purchase_journal := self.ref('purchase', raise_if_not_found=False)) and \
                (non_deductible_account := self.ref('a416', raise_if_not_found=False)):
            purchase_journal.non_deductible_account_id = non_deductible_account

    @template('be', 'account.account')
    def _get_be_account_account(self):
        return {
            'a300': {
                'account_stock_expense_id': 'a600',
                'account_stock_variation_id': 'a6090',
            },
        }
