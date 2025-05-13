# -*- coding: utf-8 -*-

from odoo import Command, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('bo')
    def _get_bo_template_data(self):
        return {
            'name': 'Kyohei Ltda.',
            'code_digits': '7',
            'visible': True,
            'anglo_saxon_accounting': True,
            'property_account_receivable_id': 'l10n_bo_1120101',
            'property_account_payable_id': 'l10n_bo_2110101',
            'property_account_expense_categ_id': 'l10n_bo_5110101',
            'property_account_income_categ_id': 'l10n_bo_4110101',
            'property_stock_account_input_categ_id': 'l10n_bo_1130601',
            'property_stock_account_output_categ_id': 'l10n_bo_1130602',
            'property_stock_valuation_account_id': 'l10n_bo_1130101',
            'property_stock_account_production_cost_id': 'l10n_bo_1130401',
            'property_cash_basis_base_account_id': 'l10n_bo_6111019',
        }

    @template('bo', 'res.company')
    def _get_bo_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.bo',
                'bank_account_code_prefix': '111030',
                'cash_account_code_prefix': '111010',
                'transfer_account_code_prefix': '111070',
                'account_default_pos_receivable_account_id': 'l10n_bo_1120101',
                'income_currency_exchange_account_id': 'l10n_bo_4180604',
                'expense_currency_exchange_account_id': 'l10n_bo_6130101',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_bo_5410104',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_bo_4180301',
                'account_sale_tax_id': 'l10n_bo_yo_bo_fiscal_debit',
                'account_purchase_tax_id': 'l10n_bo_yo_bo_fiscal_credit',
                'default_cash_difference_income_account_id': 'l10n_bo_4180605',
                'default_cash_difference_expense_account_id': 'l10n_bo_6130102',
                'account_discount_expense_allocation_id':'l10n_bo_4140101',
                'account_discount_income_allocation_id':'l10n_bo_5410102',
                'account_journal_suspense_account_id': 'l10n_bo_1111101',
                'transfer_account_id': 'l10n_bo_1111102',
                # Deferred
                'deferred_expense_account_id': 'l10n_bo_1310201',
                'deferred_revenue_account_id': 'l10n_bo_2170101',
                # Chash basis taxes
                'tax_cash_basis_journal_id': 'caba',
                'account_cash_basis_base_account_id': 'l10n_bo_6111019',
            },
        }

    @template('bo', 'account.journal')
    def _get_bo_account_journal(self):
        return {
            'sale': {
                'refund_sequence': True,
                'code': 'SALE'
            },
            'purchase': {
                'refund_sequence': True,
                'code': 'PURCH'
            },
            'general': {'code': 'MISC'},
            'exch': {'code': 'EXCH'},
            'caba': {
                'name': 'Taxes',
                'code': 'TAXES'
            },
            'def_in' :{
                'name': 'Deferred income',
                'code': 'DFIN',
                'type': 'general'
            },
            'def_out' :{
                'name': 'Deferred expense',
                'code': 'DFOUT',
                'type': 'general'
            },
            'bank': {'default_account_id': 'l10n_bo_1110301'},
            'cash': {'default_account_id': 'l10n_bo_1110101'},
        }

    @template('bo', 'account.reconcile.model')
    def _get_bo_reconcile_model(self):
        return {
            'financial_transaction_tax_template': {
                'name': 'ITF',
                'rule_type': 'writeoff_suggestion',
                'auto_reconcile': True,
                'match_text_location_label': True,
                'match_label': 'contains',
                'match_label_param': 'ITF',
                'line_ids': [
                    Command.create({
                        'account_id': 'l10n_bo_6111006',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'ITF',
                    }),
                ]
            }
        }

    def _load(self, template_code, company, install_demo, force_create=True):
        record = super()._load(template_code, company, install_demo, force_create)
        company.write({'anglo_saxon_accounting': True})
        return record
