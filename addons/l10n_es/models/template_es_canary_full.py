# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_canary_full')
    def _get_es_canary_full_template_data(self):
        return {
            'name': _('Canary Islands - Complete (2008)'),
            'parent': 'es_canary_common',
        }

    @template('es_canary_full', 'res.company')
    def _get_es_canary_full_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.es',
                'bank_account_code_prefix': '572',
                'cash_account_code_prefix': '570',
                'transfer_account_code_prefix': '572999',
            },
        }

    @template('es_canary_full', 'account.account')
    def _get_es_canary_full_account_account(self):
        return self._parse_csv('es_full', 'account.account', module='l10n_es')
