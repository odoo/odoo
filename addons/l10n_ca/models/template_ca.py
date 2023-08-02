# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ca_2023')
    def _get_ca_template_data(self):
        return {
            'property_account_receivable_id': 'l10n_ca_112110',
            'property_account_payable_id': 'l10n_ca_221110',
            'property_account_income_categ_id': 'l10n_ca_411100',
            'property_account_expense_categ_id': 'l10n_ca_511210',
            'property_stock_account_input_categ_id': 'l10n_ca_121130',
            'property_stock_account_output_categ_id': 'l10n_ca_121140',
            'property_stock_valuation_account_id': 'l10n_ca_121120',
            'use_anglo_saxon': True,
        }

    @template('ca_2023', 'res.company')
    def _get_ca_res_company(self):

        default_sales_tax, default_purchase_tax = {
            'BC': ('gstpst_sale_tax_12_bc', 'gstpst_purchase_tax_12_bc'),
            'MB': ('gstpst_sale_tax_12_mb', 'gstpst_purchase_tax_12_mb'),
            'QC': ('gstqst_sale_tax_14975', 'gstqst_purchase_tax_14975'),
            'SK': ('gstpst_sale_tax_11', 'gstpst_purchase_tax_11'),
            'ON': ('hst_sale_tax_13', 'hst_purchase_tax_13'),
            'NB': ('hst_sale_tax_15', 'hst_purchase_tax_15'),
            'NL': ('hst_sale_tax_15', 'hst_purchase_tax_15'),
            'NS': ('hst_sale_tax_15', 'hst_purchase_tax_15'),
            'PE': ('hst_sale_tax_15', 'hst_purchase_tax_15'),
        }.get(self.env.company.state_id.code, ('gst_sale_tax_5', 'gst_purchase_tax_5'))

        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ca',
                'bank_account_code_prefix': '11131',
                'cash_account_code_prefix': '11121',
                'transfer_account_code_prefix': '1111',
                'account_default_pos_receivable_account_id': 'l10n_ca_112113',
                'income_currency_exchange_account_id': 'l10n_ca_423100',
                'expense_currency_exchange_account_id': 'l10n_ca_522100',
                'account_journal_early_pay_discount_loss_account_id': 'l10n_ca_522200',
                'account_journal_early_pay_discount_gain_account_id': 'l10n_ca_423200',
                'account_sale_tax_id': default_sales_tax,
                'account_purchase_tax_id': default_purchase_tax,
            },
        }
