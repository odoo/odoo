# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_coop_common')
    def _get_es_coop_common_template_data(self):
        return {
            'name': 'PGCE Cooperativas Común',
            'visible': 0,
            'parent': 'es_common',
        }

    @template('es_coop_common', 'res.company')
    def _get_es_coop_common_res_company(self):
        return {
            self.env.company.id: {
                'bank_account_code_prefix': '572',
                'cash_account_code_prefix': '570',
                'transfer_account_code_prefix': '572999',
            },
        }
