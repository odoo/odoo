# Copyright 2026 Ignacio Ibeas <ignacio@acysos.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# Los datos provienen del Plan General de Contabilidad de España para Empresas Públicas https://www.boe.es/buscar/act.php?id=BOE-A-2010-6710
from odoo import _, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_public_company')
    def _get_es_public_company_template_data(self):
        return {
            'name': _('Public Entities (2008)'),
            'parent': 'es_common_mainland',
        }

    @template('es_public_company', 'res.company')
    def _get_es_public_company_res_company(self):
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
