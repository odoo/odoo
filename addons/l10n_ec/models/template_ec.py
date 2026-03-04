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
            'property_stock_valuation_account_id': 'ec110306',
            'code_digits': '4',
        }

    def _get_account_parent_xmlid(self, code_prefix, template_code):
        if template_code == 'ec':
            return {
                '11010201': 'ec110102',
                '1101030': 'ec110103',
            }.get(code_prefix)

        return super()._get_account_parent_xmlid(code_prefix, template_code)

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
                'expense_account_id': 'ec110307',
                'income_account_id': 'ec410101',
                'tax_calculation_rounding_method': 'round_per_line',
                'account_stock_valuation_id': 'ec110306',
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
            'purchase': {
                'default_account_id': 'ec52022816',
            },
        }

    @template('ec', 'account.account')
    def _get_ec_account_account(self):
        return {
            'ec110306': {
                'account_stock_expense_id': 'ec510106',
                'account_stock_variation_id': 'ec110310',
            },
            'ec120102': {'asset_depreciation_account_id': 'ec12011201', 'asset_expense_account_id': 'ec51040101'},
            'ec120104': {'asset_depreciation_account_id': 'ec12011203', 'asset_expense_account_id': 'ec51040103'},
            'ec120105': {'asset_depreciation_account_id': 'ec12011204', 'asset_expense_account_id': 'ec51040104'},
            'ec120106': {'asset_depreciation_account_id': 'ec12011205', 'asset_expense_account_id': 'ec51040105'},
            'ec120107': {'asset_depreciation_account_id': 'ec12011206', 'asset_expense_account_id': 'ec51040106'},
            'ec120108': {'asset_depreciation_account_id': 'ec12011207', 'asset_expense_account_id': 'ec51040107'},
            'ec120109': {'asset_depreciation_account_id': 'ec12011208', 'asset_expense_account_id': 'ec51040108'},
            'ec120110': {'asset_depreciation_account_id': 'ec12011209', 'asset_expense_account_id': 'ec51040109'},
            'ec120111': {'asset_depreciation_account_id': 'ec12011210', 'asset_expense_account_id': 'ec51040110'},
        }

    @template('ec', 'stock.location')
    def _get_ec_stock_location(self):
        if 'stock.location' not in self.env:
            return {}
        loss_locs = self.env['stock.location'].search([('usage', '=', 'inventory'), ('company_id', '=', self.env.company.id)])  # noqa: OLS03001
        prod_locs = self.env['stock.location'].search([('usage', '=', 'production'), ('company_id', '=', self.env.company.id)])  # noqa: OLS03001
        return {
            loc.id: {'valuation_account_id': 'ec510112'}
            for loc in loss_locs
        } | {
            loc.id: {'valuation_account_id': 'ec110302'}
            for loc in prod_locs
        }
