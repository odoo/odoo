# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_canary_assoc')
    def _get_es_canary_assoc_template_data(self):
        return {
            'name': _('Canary Islands - PGCE non-profit entities (2008)'),
            'parent': 'es_canary_common',
        }

    @template('es_canary_assoc', 'res.company')
    def _get_es_canary_assoc_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.es',
                'bank_account_code_prefix': '572',
                'cash_account_code_prefix': '570',
                'transfer_account_code_prefix': '572999',
            },
        }

    @template('es_canary_assoc', 'account.account')
    def _get_es_canary_assoc_account_account(self):
        res = self._parse_csv('es_assec', 'account.account', module='l10n_es')

        # Voluntarily remove the `tax_ids` since those are defined for the mainland and not the canaries
        for data in res.values():
            if 'tax_ids' in data:
                del data['tax_ids']

        return res

    @template('es_canary_assoc', 'account.asset')
    def _get_es_canary_assoc_account_asset(self):
        return self._parse_csv('es_assec', 'account.asset', module='l10n_es')
