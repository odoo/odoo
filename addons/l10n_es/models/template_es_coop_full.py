# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_coop_full')
    def _get_es_coop_full_template_data(self):
        return {
            'name': 'PGCE Cooperativas Completo 2008',
            'parent': 'es_coop_pymes',
        }

    @template('es_coop_full', 'res.company')
    def _get_es_coop_full_res_company(self):
        return {
            self.env.company.id: {
                'bank_account_code_prefix': '572',
                'cash_account_code_prefix': '570',
                'transfer_account_code_prefix': '572999',
            },
        }
