# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ch')
    def _get_ch_template_data(self):
        return {
            'code_digits': '4',
            'property_account_receivable_id': 'ch_coa_1100',
            'property_account_payable_id': 'ch_coa_2000',
            'property_account_expense_categ_id': 'ch_coa_4200',
            'property_account_income_categ_id': 'ch_coa_3200',
        }

    @template('ch', 'res.company')
    def _get_ch_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ch',
                'bank_account_code_prefix': '102',
                'cash_account_code_prefix': '100',
                'transfer_account_code_prefix': '1090',
                'account_default_pos_receivable_account_id': 'ch_coa_1101',
                'income_currency_exchange_account_id': 'ch_coa_3806',
                'expense_currency_exchange_account_id': 'ch_coa_4906',
                'account_journal_early_pay_discount_loss_account_id': 'ch_coa_4901',
                'account_journal_early_pay_discount_gain_account_id': 'ch_coa_3801',
                'default_cash_difference_expense_account_id': 'ch_coa_4991',
                'default_cash_difference_income_account_id': 'ch_coa_4992',
                'account_sale_tax_id': 'vat_sale_81',
                'account_purchase_tax_id': 'vat_purchase_81',
                'external_report_layout_id': 'l10n_din5008.external_layout_din5008',
                'paperformat_id': 'l10n_din5008.paperformat_euro_din',
            },
        }
