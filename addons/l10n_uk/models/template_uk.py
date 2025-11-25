# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('uk')
    def _get_uk_template_data(self):
        return {
            'property_account_receivable_id': '110000',
            'property_account_payable_id': '210000',
            'code_digits': '6',
            'country': 'gb',
        }

    @template('uk', 'res.company')
    def _get_uk_res_company(self):
        return {
            self.env.company.id: {
                'anglo_saxon_accounting': True,
                'account_fiscal_country_id': 'base.uk',
                'bank_account_code_prefix': '1200',
                'cash_account_code_prefix': '1210',
                'transfer_account_code_prefix': '1220',
                'account_default_pos_receivable_account_id': '110400',
                'income_currency_exchange_account_id': '770000',
                'expense_currency_exchange_account_id': '770000',
                'account_sale_tax_id': 'ST11',
                'account_purchase_tax_id': 'PT_20_G',
                'expense_account_id': '500000',
                'income_account_id': '400000',
                'deferred_expense_account_id': '110300',
                'deferred_revenue_account_id': '210900',
                'account_stock_valuation_id': '100100',
            },
        }

    def _post_load_data(self, template_code, company, template_data):
        """If the company is located in Northern Ireland, activate the relevant taxes and fiscal postions."""
        result = super()._post_load_data(template_code, company, template_data)

        is_ni_state = {
            'base.state_uk18', 'base.state_uk19', 'base.state_uk20', 'base.state_uk21',
            'base.state_uk22', 'base.state_uk23', 'base.state_uk24',
        }.intersection(
            company.state_id._get_external_ids().get(company.state_id.id, [])
        )

        if is_ni_state or company.country_id.code == 'XI':
            for xmlid in ['PT8', 'ST4', 'PT7', 'account_fiscal_position_ni_to_eu_b2b']:
                self.ref(xmlid).active = True

        return result

    @template('uk', 'account.account')
    def _get_uk_account_account(self):
        return {
            '100100': {
                'account_stock_variation_id': '630000',
            },
            '001000': {'asset_depreciation_account_id': '001100', 'asset_expense_account_id': '751000'},
            '002000': {'asset_depreciation_account_id': '002100', 'asset_expense_account_id': '800000'},
            '003000': {'asset_depreciation_account_id': '003100', 'asset_expense_account_id': '800100'},
            '004001': {'asset_depreciation_account_id': '004101', 'asset_expense_account_id': '800100'},
            '005000': {'asset_depreciation_account_id': '005100', 'asset_expense_account_id': '800100'},
            '006000': {'asset_depreciation_account_id': '006100', 'asset_expense_account_id': '750600'},
            '007000': {'asset_depreciation_account_id': '007100', 'asset_expense_account_id': '800100'},
            '008000': {'asset_depreciation_account_id': '008100', 'asset_expense_account_id': '800100'},
            '009000': {'asset_depreciation_account_id': '009100', 'asset_expense_account_id': '800100'},
        }
