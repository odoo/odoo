# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cr')
    def _get_cr_template_data(self):
        return {
            'property_account_receivable_id': 'account_account_template_0_112001',
            'property_account_payable_id': 'account_account_template_0_211001',
            'property_account_income_categ_id': 'account_account_template_0_410001',
            'property_account_expense_categ_id': 'account_account_template_0_511301',
        }

    @template('cr', 'res.company')
    def _get_cr_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cr',
                'bank_account_code_prefix': '0.1112',
                'cash_account_code_prefix': '0.1111',
                'transfer_account_code_prefix': '0.1114',
                'account_default_pos_receivable_account_id': 'account_account_template_0_112011',
                'income_currency_exchange_account_id': 'account_account_template_0_450001',
                'expense_currency_exchange_account_id': 'account_account_template_0_530004',
                'account_sale_tax_id': 'account_tax_template_IV_0',
                'account_purchase_tax_id': 'account_tax_template_IV_1',
            },
        }
