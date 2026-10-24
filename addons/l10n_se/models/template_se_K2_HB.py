# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Swedish chart of accounts K2 for trading partnerships (HB/KB).

K2 extended with the BAS 2026 partner equity accounts (2010-2049) and the
expansion fund (2050). These accounts are kept out of K2 so limited companies
do not see them. The template also selects the INK4 SRU form.
Source: https://www.bas.se/kontoplaner/
SRU mapping: BAS kopplingsschema INK4 P1 (rev. 2024-08-28)
"""
from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('se_K2_HB')
    def _get_se_K2_HB_template_data(self):
        return {
            'name': 'Swedish BAS Chart of Accounts K2 for Trading Partnerships (HB/KB)',
            'parent': 'se_K2',
            'code_digits': '4',
        }
