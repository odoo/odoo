# -*- coding: utf-8 -*-

from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template('ug')
    def _get_ug_template_data(self):
        return {
            'name': "Uganda Generic Chart of Accounts",
            'code_digits': 6,
            'property_account_receivable_id': '3528',
            'property_account_payable_id': '4117',
        }

    @template('ug', 'res.company')
    def _get_ug_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.ug',
                'bank_account_code_prefix': '3528',
                'cash_account_code_prefix': '3528',
                'transfer_account_code_prefix': '3528',
                'account_default_pos_receivable_account_id': '3528',
                'income_currency_exchange_account_id': '221018',
                'expense_currency_exchange_account_id': '221018',
                'account_journal_early_pay_discount_loss_account_id': '221019',
                'account_journal_early_pay_discount_gain_account_id': '191001',
                'account_sale_tax_id': 'sale_vat_18',
                'account_purchase_tax_id': 'purchase_vat_18',
                'fiscalyear_last_day': '30',
                'fiscalyear_last_month': '6',
                'deferred_expense_account_id': '352809',
                'deferred_revenue_account_id': '411726',
                'expense_account_id': '2240',
                'income_account_id': '1420',
                'account_stock_journal_id': 'inventory_valuation',
                'account_stock_valuation_id': '320114',
            }
        }

    @template('ug', 'account.account')
    def _get_ug_account_account(self):
        return {
            '320114': {
                'account_stock_variation_id': '2291',
            },
        }
