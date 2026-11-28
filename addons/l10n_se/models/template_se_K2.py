# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Swedish chart of accounts K2.

Based on: BAS 2026 (v2, 2026-04), all accounts not marked [Not K2], except the
partner equity accounts 2010-2050 (HB/KB template) and the equity accounts
for non-profit associations and foundations 2060-2072 (NPO template). Bank and cash
accounts (19xx) are created by Odoo from the code prefixes in the base template.
Accounts 3011-3042 split domestic sales into goods and services so the fiscal
positions can map them to the BAS export/EU accounts.
Source: https://www.bas.se/kontoplaner/
SRU mapping: BAS kopplingsschema INK2 P1 (rev. 2024-11-19)
"""
from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('se_K2')
    def _get_se_K2_template_data(self):
        return {
            'name': 'Swedish BAS Chart of Accounts K2 (Recommended)',
            'parent': 'se',
            'code_digits': '4',
        }

    @template('se_K2', 'res.company')
    def _get_se_K2_res_company(self):
        return {
            self.env.company.id: {
                'account_default_pos_receivable_account_id': 'a1686',
                'income_currency_exchange_account_id': 'a3960',
                'expense_currency_exchange_account_id': 'a7960',
                'account_journal_early_pay_discount_loss_account_id': 'a3731',
                'account_journal_early_pay_discount_gain_account_id': 'a4731',
                'expense_account_id': 'a4000',
                'income_account_id': 'a3011',
                'receivable_account_id': 'a1510',
                'payable_account_id': 'a2440',
                'account_stock_valuation_id': 'a1410',
            },
        }
