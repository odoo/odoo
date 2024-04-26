from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('cy')
    def _get_cy_template_data(self):
        return {
            'code_digits': '4',
            'property_account_receivable_id': 'cy_1100',
            'property_account_payable_id': 'cy_2100',
        }

    @template('cy', 'res.company')
    def _get_cy_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.cy',
                'bank_account_code_prefix': '1200',
                'cash_account_code_prefix': '1231',
                'transfer_account_code_prefix': '1261',
                'account_default_pos_receivable_account_id': 'cy_1100',
                'income_currency_exchange_account_id': 'cy_7910',
                'expense_currency_exchange_account_id': 'cy_7910',
                'account_sale_tax_id': 'VAT_S_IN_CY_19_G',
                'account_purchase_tax_id': 'VAT_P_IN_CY_19_G',
                'expense_account_id': 'cy_5100',
                'income_account_id': 'cy_4000',
            },
        }
