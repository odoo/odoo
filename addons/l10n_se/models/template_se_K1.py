# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Swedish chart of accounts for simplified annual accounts (K1).

Based on: BAS Förenklat årsbokslut (K1) 2018
Source: https://www.bas.se/kontoplaner/
SRU mapping: BAS kopplingsschema NE K1 (rev. 2020-10-02)
"""
from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('se_K1')
    def _get_se_K1_template_data(self):
        return {
            'name': 'Swedish BAS Chart of Accounts K1 (Simplified annual report)',
            'parent': 'se',
            'code_digits': '4',
        }

    @template('se_K1', 'res.company')
    def _get_se_K1_res_company(self):
        return {
            self.env.company.id: {
                'account_default_pos_receivable_account_id': 'a1686',
                'income_currency_exchange_account_id': 'a8330',
                'expense_currency_exchange_account_id': 'a8430',
                'expense_account_id': 'a4000',
                'income_account_id': 'a3011',
                'receivable_account_id': 'a1500',
                'payable_account_id': 'a2440',
                'account_stock_valuation_id': 'a1400',
            },
        }
