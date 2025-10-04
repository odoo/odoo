# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('lu')
    def _get_lu_template_data(self):
        return {
            'property_account_receivable_id': 'lu_2011_account_4011',
            'property_account_payable_id': 'lu_2011_account_44111',
            'property_account_expense_categ_id': 'lu_2011_account_6061',
            'property_account_income_categ_id': 'lu_2020_account_703001',
            'property_stock_account_input_categ_id': 'lu_2011_account_321',
            'property_stock_account_output_categ_id': 'lu_2011_account_321',
            'property_stock_valuation_account_id': 'lu_2020_account_60761',
            'code_digits': '6',
        }

    @template('lu', 'res.company')
    def _get_lu_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.lu',
                'bank_account_code_prefix': '513',
                'cash_account_code_prefix': '516',
                'transfer_account_code_prefix': '517',
                'account_default_pos_receivable_account_id': 'lu_2011_account_40111',
                'income_currency_exchange_account_id': 'lu_2020_account_7561',
                'expense_currency_exchange_account_id': 'lu_2020_account_6561',
                'account_journal_suspense_account_id': 'lu_2011_account_485',
                'account_journal_early_pay_discount_loss_account_id': 'lu_2020_account_65562',
                'account_journal_early_pay_discount_gain_account_id': 'lu_2020_account_75562',
                'account_sale_tax_id': 'lu_2015_tax_VP-PA-17',
                'account_purchase_tax_id': 'lu_2015_tax_AP-PA-17',
            },
        }

    @template('lu', 'account.journal')
    def _get_lu_account_journal(self):
        return {
            'sale': {'refund_sequence': True},
            'purchase': {'refund_sequence': True},
        }

    @template('lu', 'account.reconcile.model')
    def _get_lu_reconcile_model(self):
        return {
            'bank_fees_template': {
                'name': 'Bank Fees',
                'rule_type': 'writeoff_button',
                'line_ids': [
                    Command.create({
                        'account_id': 'lu_2011_account_61333',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Bank Fees',
                    }),
                ],
            },
            'cash_discount_template': {
                'name': 'Cash Discount',
                'rule_type': 'writeoff_button',
                'line_ids': [
                    Command.create({
                        'account_id': 'lu_2020_account_65562',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Cash Discount',
                    }),
                ],
            },
        }
