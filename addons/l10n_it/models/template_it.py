# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('it')
    def _get_it_template_data(self):
        return {
            'property_account_receivable_id': '1501',
            'property_account_payable_id': '2501',
        }

    @template('it', 'res.company')
    def _get_it_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.it',
                'bank_account_code_prefix': '182',
                'cash_account_code_prefix': '180',
                'transfer_account_code_prefix': '183',
                'account_default_pos_receivable_account_id': '1508',
                'income_currency_exchange_account_id': '3220',
                'expense_currency_exchange_account_id': '4920',
                'account_journal_early_pay_discount_loss_account_id': '4111',
                'account_journal_early_pay_discount_gain_account_id': '3111',
                'account_sale_tax_id': '22v',
                'account_purchase_tax_id': '22am',
                'expense_account_id': '4101',
                'income_account_id': '3101',
            },
        }
