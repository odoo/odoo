# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('at')
    def _get_at_template_data(self):
        return {
            'visible': True,
            'property_account_receivable_id': 'chart_at_template_2000',
            'property_account_payable_id': 'chart_at_template_3300',
            'property_account_income_categ_id': 'chart_at_template_4000',
            'property_account_expense_categ_id': 'chart_at_template_5010',
            'property_stock_account_input_categ_id': 'chart_at_template_3740',
            'property_stock_account_output_categ_id': 'chart_at_template_5000',
            'property_stock_valuation_account_id': 'chart_at_template_1600',
            'code_digits': '4',
        }

    @template('at', 'res.company')
    def _get_at_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.at',
                'bank_account_code_prefix': '280',
                'cash_account_code_prefix': '270',
                'transfer_account_code_prefix': '288',
                'account_default_pos_receivable_account_id': 'chart_at_template_2099',
                'income_currency_exchange_account_id': 'chart_at_template_4860',
                'expense_currency_exchange_account_id': 'chart_at_template_7860',
                'account_journal_early_pay_discount_loss_account_id': 'chart_at_template_5800',
                'account_journal_early_pay_discount_gain_account_id': 'chart_at_template_8350',
                'external_report_layout_id': 'l10n_din5008.external_layout_din5008',
                'paperformat_id': 'l10n_din5008.paperformat_euro_din',
                'account_sale_tax_id': 'account_tax_template_sales_20_code022',
                'account_purchase_tax_id': 'account_tax_template_purchase_20_code060',
            },
        }

    def _setup_utility_bank_accounts(self, template_code, company, template_data):
        super()._setup_utility_bank_accounts(template_code, company, template_data)
        if template_code == "at":
            company.account_journal_suspense_account_id.tag_ids = self.env.ref('l10n_at.account_tag_external_code_2300')
            company.account_journal_payment_debit_account_id.tag_ids = self.env.ref('l10n_at.account_tag_external_code_2300')
            company.account_journal_payment_credit_account_id.tag_ids = self.env.ref('l10n_at.account_tag_external_code_2300')
            company.transfer_account_id.tag_ids = self.env.ref('l10n_at.account_tag_external_code_2885')
