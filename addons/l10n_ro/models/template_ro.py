# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ro')
    def _get_ro_template_data(self):
        return {
            'property_account_receivable_id': 'ro_pcg_recv',
            'property_account_payable_id': 'pcg_4011',
            'property_account_expense_categ_id': 'ro_pcg_expense',
            'property_account_income_categ_id': 'ro_pcg_sale',
            'code_digits': '6',
            'use_storno_accounting': True,
        }

    @template('ro', 'res.company')
    def _get_ro_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ro',
                'bank_account_code_prefix': '5121',
                'cash_account_code_prefix': '5311',
                'transfer_account_code_prefix': '581',
                'account_default_pos_receivable_account_id': 'ro_pcg_recv',
                'income_currency_exchange_account_id': 'pcg_7651',
                'expense_currency_exchange_account_id': 'pcg_6651',
                'account_journal_suspense_account_id': 'pcg_5125',
                'account_journal_early_pay_discount_loss_account_id': 'pcg_6092',
                'account_journal_early_pay_discount_gain_account_id': 'pcg_709',
                'account_sale_tax_id': 'tvac_21',
                'account_purchase_tax_id': 'tvad_21',
            },
        }

    @template('ro', 'account.reconcile.model')
    def _get_ro_reconcile_model(self):
        return {
            'suppadvance_template': {
                'name': 'Avans Furnizor - Imobilizări Necorporale',
                'line_ids': [
                    Command.create({
                        'account_id': 'pcg_4094',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Supplier Advance - Intangible Assets',
                    }),
                ],
            },
            'custadvance_template': {
                'name': 'Customer Advances',
                'line_ids': [
                    Command.create({
                        'account_id': 'pcg_419',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Customer Advances',
                    }),
                ],
            },
            'bankcomm_template': {
                'name': 'Bank Commission',
                'line_ids': [
                    Command.create({
                        'account_id': 'pcg_627',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Bank Commission',
                    }),
                ],
            },
            'interest_template': {
                'name': 'Interests',
                'line_ids': [
                    Command.create({
                        'account_id': 'pcg_766',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Interests',
                    }),
                ],
            },
            'inttransfer_template': {
                'name': 'Internal transfer',
                'line_ids': [
                    Command.create({
                        'account_id': 'pcg_581',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Internal transfer',
                    }),
                ],
            },
            'payroll_template': {
                'name': 'Wages',
                'line_ids': [
                    Command.create({
                        'account_id': 'pcg_421',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Wages',
                    }),
                ],
            },
            'pendsettl_template': {
                'name': 'Operations being clarified',
                'line_ids': [
                    Command.create({
                        'account_id': 'pcg_473',
                        'amount_type': 'percentage',
                        'amount_string': '100',
                        'label': 'Operations being clarified',
                    }),
                ],
            },
        }
