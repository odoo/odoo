# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('id')
    def _get_id_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_id_11210010',
            'property_account_payable_id': 'l10n_id_21100010',
            'property_stock_valuation_account_id': 'l10n_id_11300180',
            'code_digits': '8',
        }

    @template('id', 'res.company')
    def _get_id_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.id',
                'bank_account_code_prefix': '1112',
                'cash_account_code_prefix': '1111',
                'transfer_account_code_prefix': '1999999',
                'default_cash_difference_income_account_id': 'l10n_id_99900002',
                'default_cash_difference_expense_account_id': 'l10n_id_99900001',
                'account_default_pos_receivable_account_id': 'l10n_id_11210011',
                'income_currency_exchange_account_id': 'l10n_id_81100030',
                'expense_currency_exchange_account_id': 'l10n_id_91100020',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_id_99900003',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_id_99900004',
                'account_sale_tax_id': 'tax_ST4',
                'account_purchase_tax_id': 'tax_PT4',
                'expense_account_id': 'l10n_id_51000010',
                'income_account_id': 'l10n_id_41000010',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': 'l10n_id_11300180',
                'deferred_expense_account_id': 'l10n_id_11210040',
                'deferred_revenue_account_id': 'l10n_id_28110030',
            },
        }

    @template('id', 'account.account')
    def _get_id_account_account(self):
        return {
            'l10n_id_11300180': {
                'account_stock_expense_id': 'l10n_id_51000020',
                'account_stock_variation_id': 'l10n_id_42500010',
            },
        }

    @template('id', 'account.journal')
    def _get_id_account_journal(self):
        return {
            'bank': {'default_account_id': 'l10n_id_11120001'},
            'cash': {
                'name': self.env._("Cash"),
                'type': 'cash',
                'default_account_id': 'l10n_id_11110001',
            },
        }
