# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('se_K3')
    def _get_se_K3_template_data(self):
        return {
            'name': 'Swedish BAS Chart of Account complete K3',
            'parent': 'se_K2',
            'code_digits': '4',
        }

    @template('se_K3', 'res.company')
    def _get_se_K3_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.se',
                'bank_account_code_prefix': '193',
                'cash_account_code_prefix': '191',
                'transfer_account_code_prefix': '194',
            },
        }
