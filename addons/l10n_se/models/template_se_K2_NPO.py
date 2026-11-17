# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Swedish chart of accounts K2 for non-profit associations and foundations.

K2 extended with the BAS 2026 equity accounts for non-profit associations,
foundations and registered religious communities (2060-2072). These accounts are
kept out of K2 so limited companies do not see them. The template also selects
the INK3 SRU form.
Source: https://www.bas.se/kontoplaner/
SRU mapping: BAS kopplingsschema INK3 (rev. 2024-11-19)
"""
from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('se_K2_NPO')
    def _get_se_K2_NPO_template_data(self):
        return {
            'name': 'Swedish BAS Chart of Accounts K2 for Non-profit Associations and Foundations',
            'parent': 'se_K2',
            'code_digits': '4',
        }
