# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('il')
    def _get_il_template_data(self):
        return {
            'property_account_receivable_id': 'il_account_101200',
            'property_account_payable_id': 'il_account_111100',
            'property_account_expense_categ_id': 'il_account_212200',
            'property_account_income_categ_id': 'il_account_200000',
            'property_stock_account_input_categ_id': 'il_account_101120',
            'property_stock_account_output_categ_id': 'il_account_101130',
            'property_stock_valuation_account_id': 'il_account_101110',
            'code_digits': '6',
        }

    @template('il', 'res.company')
    def _get_il_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.il',
                'bank_account_code_prefix': '1014',
                'cash_account_code_prefix': '1015',
                'transfer_account_code_prefix': '1017',
                'account_default_pos_receivable_account_id': 'il_account_101201',
                'income_currency_exchange_account_id': 'il_account_201000',
                'expense_currency_exchange_account_id': 'il_account_202100',
                'account_sale_tax_id': 'il_vat_sales_18',
                'account_purchase_tax_id': 'il_vat_inputs_18',
            },
        }
    
    def try_loading(self, template_code, company, install_demo=False):
        # During company creation load account tags translations
        res = super().try_loading(template_code, company, install_demo)
        if not company:
            return res
        if isinstance(company, int):
            company = self.env['res.company'].browse([company])
        if company.country_code == 'IL' and company.chart_template == 'il':
            TAG_PAIRS = [
                ('VAT SALES (BASE)', 'הכנסות חייבות במע"מ'),
                ('VAT Exempt Sales (BASE)', 'הכנסות פטורות ממע"מ'),
                ('VAT Sales', 'מע"מ עסקאות'),
                ('VAT PA Sales', 'מע"מ עסקאות רש"פ'),
                ('VAT Inputs 18%','מע"מ תשומות 18%'),
                ('VAT Inputs 17%', 'מע"מ תשומות 17%'),
                ('VAT Inputs PA 16%', 'מע"מ תשומות רש"פ 16%'),
                ('VAT Inputs 2/3', 'מע"מ תשומות 2/3'),
                ('VAT Inputs 1/4', 'מע"מ תשומות 1/4'),
                ('VAT INPUTS (fixed assets)', 'מע"מ תשומות (רכוש קבוע)')
            ]
            for EN_TAG, HE_TAG in TAG_PAIRS:
                for sign in ['+','-']:
                    FULL_EN_TAG = f"{sign}{EN_TAG}"
                    FULL_HE_TAG = f"{sign}{HE_TAG}"
                    tag_ids = self.env['account.account.tag'].with_context(lang='en_US').search([
                        ('name', '=', FULL_EN_TAG),
                        ('applicability', '=', 'taxes')
                    ])
                    tag_ids.with_context(lang='he_IL').write({'name': FULL_HE_TAG})
        return res