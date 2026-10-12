# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('be_asso', 'account.cash.rounding')
    def _get_be_asso_account_cash_rounding(self):
        return {
            'cash_rounding_be_asso_05': {
                'name': "Round to 0.05",
                'name@fr': "Arrondi à 0.05",
                'name@nl': "Afronding tot 0.05",
                'name@de': "Rundung auf 0,05",
                'rounding': 0.05,
                'strategy': 'add_invoice_line',
                'company_id': self.env.company.id,
                'rounding_method': 'HALF-UP',
                'profit_account_id': 'a743',
                'loss_account_id': 'a644',
            },
        }

    @template('be_asso')
    def _get_be_asso_template_data(self):
        return {
            'name': _('Associations and Foundations'),
            'parent': 'be',
            'code_digits': '6',
        }

    @template('be_asso', 'res.company')
    def _get_be_asso_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.be',
                'bank_account_code_prefix': '550',
                'cash_account_code_prefix': '570',
                'transfer_account_code_prefix': '580',
            },
        }
