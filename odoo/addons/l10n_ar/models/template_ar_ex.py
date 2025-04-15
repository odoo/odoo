# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ar_ex')
    def _get_ar_ex_template_data(self):
        return {
            'name': _('Argentine Generic Chart of Accounts for Exempt Individuals'),
            'parent': 'ar_base',
            'code_digits': '12',
        }

    @template('ar_ex', 'res.company')
    def _get_ar_ex_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ar',
                'bank_account_code_prefix': '1.1.1.02.',
                'cash_account_code_prefix': '1.1.1.01.',
                'transfer_account_code_prefix': '6.0.00.00.',
                'account_default_pos_receivable_account_id': 'base_deudores_por_ventas_pos',
                'income_currency_exchange_account_id': 'base_diferencias_de_cambio',
                'expense_currency_exchange_account_id': 'base_diferencias_de_cambio',
            },
        }
