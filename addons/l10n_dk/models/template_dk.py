# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('dk')
    def _get_dk_template_data(self):
        return {
            'property_account_receivable_id': 'dk_coa_5960',
            'property_account_payable_id': 'dk_coa_7180',
            'property_account_expense_categ_id': 'dk_coa_1610',
            'property_account_income_categ_id': 'dk_coa_1010',
            'property_tax_payable_account_id': 'dk_coa_7840',
            'property_tax_receivable_account_id': 'dk_coa_6320',
            'use_anglo_saxon': True,
            'code_digits': '4',
        }

    @template('dk', 'res.company')
    def _get_dk_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.dk',
                'bank_account_code_prefix': '682',
                'cash_account_code_prefix': '681',
                'transfer_account_code_prefix': '683',
                'account_default_pos_receivable_account_id': 'dk_coa_5961',
                'income_currency_exchange_account_id': 'dk_coa_3610',
                'expense_currency_exchange_account_id': 'dk_coa_3610',
                'account_journal_early_pay_discount_loss_account_id': 'dk_coa_3790',
                'account_journal_early_pay_discount_gain_account_id': 'dk_coa_3570',
                'account_sale_tax_id': 'tax110',
                'account_purchase_tax_id': 'tax400',
            },
        }
