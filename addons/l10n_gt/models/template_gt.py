# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('gt')
    def _get_gt_template_data(self):
        return {
            'code_digits': '9',
            'property_account_receivable_id': 'cta110201',
            'property_account_payable_id': 'cta210101',
            'property_account_income_categ_id': 'cta410101',
            'property_account_expense_categ_id': 'cta510101',
        }

    @template('gt', 'res.company')
    def _get_gt_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.gt',
                'bank_account_code_prefix': '1.0.01.0',
                'cash_account_code_prefix': '1.0.02.0',
                'transfer_account_code_prefix': '1.0.03.01',
                'account_default_pos_receivable_account_id': 'cta110205',
                'income_currency_exchange_account_id': 'cta410103',
                'expense_currency_exchange_account_id': 'cta710101',
                'account_sale_tax_id': 'impuestos_plantilla_iva_por_pagar',
                'account_purchase_tax_id': 'impuestos_plantilla_iva_por_cobrar',

            },
        }
