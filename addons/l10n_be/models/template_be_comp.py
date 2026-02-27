# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('be_comp', 'account.cash.rounding')
    def _get_be_comp_account_cash_rounding(self):
        return {
            'cash_rounding_be_comp_05': {
                'name': "Round to 0.05",
                'name@fr': "Arrondi à 0.05",
                'name@nl': "Afronding tot 0.05",
                'name@de': "Rundung auf 0,05",
                'rounding': 0.05,
                'strategy': 'add_invoice_line',
                'company_id': self.env.company.id,
                'rounding_method': 'HALF-UP',
                'profit_account_id': 'a743',
                'loss_account_id': 'a643',
            },
        }

    @template('be_comp')
    def _get_be_comp_template_data(self):
        return {
            'name': _('Companies'),
            'visible': False,
            'parent': 'be',
            'code_digits': '6',
            'sequence': 0,
        }

    @template('be_comp_abbr')
    def _get_be_comp_abbr_template_data(self):
        return {
            'name': _('Companies (Abbreviated)'),
            'visible': False,
            'parent': 'be_comp',
            'code_digits': '6',
            'sequence': 0,
        }

    @template('be_comp_cap_abbr')
    def _get_be_comp_cap_abbr_template_data(self):
        return {
            'name': _('Companies with Share Capital (Abbreviated)'),
            'parent': 'be_comp_abbr',
            'code_digits': '6',
            'sequence': 0,
        }

    @template('be_comp_con_abbr')
    def _get_be_comp_con_abbr_template_data(self):
        return {
            'name': _('Companies with Contributions (Abbreviated)'),
            'parent': 'be_comp_abbr',
            'code_digits': '6',
            'sequence': 0,
        }

    @template('be_comp_full')
    def _get_be_comp_full_template_data(self):
        return {
            'name': _('Companies (Full)'),
            'visible': False,
            'parent': 'be_comp',
            'code_digits': '6',
            'sequence': 0,
        }

    @template('be_comp_cap_full')
    def _get_be_comp_cap_full_template_data(self):
        return {
            'name': _('Companies with Share Capital (Full)'),
            'parent': 'be_comp_full',
            'code_digits': '6',
            'sequence': 0,
        }

    @template('be_comp_con_full')
    def _get_be_comp_con_full_template_data(self):
        return {
            'name': _('Companies with Contributions (Full)'),
            'parent': 'be_comp_full',
            'code_digits': '6',
            'sequence': 0,
        }
