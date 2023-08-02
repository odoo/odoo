# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ar_ri')
    def _get_ar_ri_template_data(self):
        return {
            'name': 'Argentine Generic Chart of Accounts for Registered Accountants',
            'parent': 'ar_ex',
            'code_digits': '12',
            'property_tax_payable_account_id': 'ri_iva_saldo_a_pagar',
            'property_tax_receivable_account_id': 'ri_iva_saldo_tecnico_favor',
        }

    @template('ar_ri', 'res.company')
    def _get_ar_ri_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ar',
                'bank_account_code_prefix': '1.1.1.02.',
                'cash_account_code_prefix': '1.1.1.01.',
                'transfer_account_code_prefix': '6.0.00.00.',
                'account_default_pos_receivable_account_id': 'base_deudores_por_ventas_pos',
                'income_currency_exchange_account_id': 'base_diferencias_de_cambio',
                'expense_currency_exchange_account_id': 'base_diferencias_de_cambio',
                'account_sale_tax_id': 'ri_tax_vat_21_ventas',
                'account_purchase_tax_id': 'ri_tax_vat_21_compras',
            },
        }
