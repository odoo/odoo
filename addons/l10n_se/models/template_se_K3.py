# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Swedish chart of accounts K3: K2 extended with the accounts BAS marks [Not K2].

Based on: BAS 2026 (v2, 2026-04) - K3 extension accounts
Source: https://www.bas.se/kontoplaner/
"""
from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('se_K3')
    def _get_se_K3_template_data(self):
        return {
            'name': 'Swedish BAS Chart of Accounts K3 (Complete)',
            'parent': 'se_K2',
            'code_digits': '4',
        }
