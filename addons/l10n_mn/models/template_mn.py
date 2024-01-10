# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mn')
    def _get_mn_template_data(self):
        return {
            'property_account_receivable_id': 'account_template_1201_0201',
            'property_account_payable_id': 'account_template_3101_0201',
            'property_account_expense_categ_id': 'account_template_6101_0101',
            'property_account_income_categ_id': 'account_template_5101_0101',
            'property_stock_account_input_categ_id': 'account_template_1407_0101',
            'property_stock_account_output_categ_id': 'account_template_1408_0101',
            'property_stock_valuation_account_id': 'account_template_1401_0101',
            'property_tax_payable_account_id': 'account_template_3401_9902',
            'property_tax_receivable_account_id': 'account_template_1204_9902',
            'code_digits': '8',
        }

    @template('mn', 'res.company')
    def _get_mn_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.mn',
                'bank_account_code_prefix': '11',
                'cash_account_code_prefix': '10',
                'transfer_account_code_prefix': '1109',
                'account_default_pos_receivable_account_id': 'account_template_1201_0202',
                'income_currency_exchange_account_id': 'account_template_5301_0201',
                'expense_currency_exchange_account_id': 'account_template_5302_0201',
                'account_journal_early_pay_discount_loss_account_id': 'account_template_5701_0201',
                'account_journal_early_pay_discount_gain_account_id': 'account_template_5701_0101',
                'account_sale_tax_id': 'account_tax_sale_vat1',
                'account_purchase_tax_id': 'account_tax_purchase_vat1',
            },
        }
