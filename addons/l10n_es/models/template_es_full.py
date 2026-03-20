# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_full')
    def _get_es_full_template_data(self):
        return {
            'name': _('Complete (2008)'),
            'parent': 'es_common_mainland',
        }

    @template('es_full', 'res.company')
    def _get_es_full_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.es',
                'bank_account_code_prefix': '572',
                'cash_account_code_prefix': '570',
                'transfer_account_code_prefix': '57299',
                'account_sale_tax_id': 'account_tax_template_s_iva21b',
                'account_purchase_tax_id': 'account_tax_template_p_iva21_bc',
            },
        }

    @template('es_full', 'account.account')
    def _get_es_full_account_account(self):
        return {
            'account_full_204': {
                'asset_depreciation_account_id': 'account_common_2800',
                'asset_expense_account_id': 'account_common_682',
            },
        }
