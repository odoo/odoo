# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('ec')
    def _get_ec_template_data(self):
        return {
            'property_account_receivable_id': 'ec1102050101',
            'property_account_payable_id': 'ec210301',
            'property_account_expense_categ_id': 'ec110307',
            'journal_account_expense_categ_id': 'ec52022816',
            'property_account_income_categ_id': 'ec410101',
            'property_stock_account_input_categ_id': 'ec110307',
            'property_stock_account_output_categ_id': 'ec510102',
            'property_stock_valuation_account_id': 'ec110306',
            'loss_stock_valuation_account': 'ec510112',
            'production_stock_valuation_account': 'ec110302',
            'code_digits': '4',
        }

    @template('ec', 'res.company')
    def _get_ec_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.ec',
                'bank_account_code_prefix': '11010201',
                'cash_account_code_prefix': '1101010',
                'transfer_account_code_prefix': '1101030',
                'account_default_pos_receivable_account_id': 'ec1102050103',
                'income_currency_exchange_account_id': 'ec430501',
                'expense_currency_exchange_account_id': 'ec520304',
                'account_journal_early_pay_discount_loss_account_id': 'ec_early_pay_discount_loss',
                'account_journal_early_pay_discount_gain_account_id': 'ec_early_pay_discount_gain',
                'default_cash_difference_income_account_id': 'ec_income_cash_difference',
                'default_cash_difference_expense_account_id': 'ec_expense_cash_difference',
                'account_sale_tax_id': 'tax_vat_15_411_goods',
                'account_purchase_tax_id': 'tax_vat_15_510_sup_01',
            },
        }

    @template('ec', 'account.journal')
    def _get_ec_account_journal(self):
        """ In case of an Ecuador, we modified the sales journal"""
        return {
            'sale': {
                'name': "001-001 Facturas de cliente",
                'l10n_ec_entity': '001',
                'l10n_ec_emission': '001',
                'l10n_ec_emission_address_id': self.env.company.partner_id.id,
            },
        }

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        # Setup default Income/Expense Accounts on Sale/Purchase journals
        if (purchase_journal := self.ref("purchase", raise_if_not_found=False)) and (expense_account_ref := template_data.get('journal_account_expense_categ_id')):
            purchase_journal.default_account_id = self.ref(expense_account_ref, raise_if_not_found=False)
