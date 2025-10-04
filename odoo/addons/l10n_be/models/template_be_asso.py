# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

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
