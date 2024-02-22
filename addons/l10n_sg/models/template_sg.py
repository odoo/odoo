# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('sg')
    def _get_sg_template_data(self):
        return {
            'code_digits': '6',
            'property_account_receivable_id': 'account_account_735',
            'property_account_payable_id': 'account_account_777',
            'property_account_expense_categ_id': 'account_account_819',
            'property_account_income_categ_id': 'account_account_803',
        }

    @template('sg', 'res.company')
    def _get_sg_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.sg',
                'bank_account_code_prefix': '10141',
                'cash_account_code_prefix': '10140',
                'transfer_account_code_prefix': '101100',
                'account_default_pos_receivable_account_id': 'account_account_737',
                'income_currency_exchange_account_id': 'account_account_853',
                'expense_currency_exchange_account_id': 'account_account_853',
                'account_journal_early_pay_discount_loss_account_id': 'account_account_800',
                'account_journal_early_pay_discount_gain_account_id': 'account_account_856',
                'account_sale_tax_id': 'sg_sale_tax_sr_8',
                'account_purchase_tax_id': 'sg_purchase_tax_tx8_8',
            },
        }
