from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template('generic_coa', 'account.tax')
    def _get_us_account_tax(self):
        return self._parse_csv('generic_coa', 'account.tax', module='l10n_us_account')

    @template('generic_coa', 'account.tax.group')
    def _get_us_account_tax_group(self):
        return self._parse_csv('generic_coa', 'account.tax.group', module='l10n_us_account')

    @template('generic_coa', 'res.company')
    def _get_us_default_taxes_res_company(self):
        default_sales_tax, default_purchase_tax = 'sale_tax_template', 'purchase_tax_template'

        if self.env.company.account_fiscal_country_id.code == 'US':
            # For US companies the 15% default tax is not related to anything
            # in the country or home state, so this better represents the state
            # sales tax as of July 2025. If the company doesn't have their state
            # selected at time of Chart of Account generation then it will default
            # to 6% as that is the most common tax currently.
            default_sales_tax, default_purchase_tax = {
                'AL': ('sale_tax_4', 'purchase_tax_4'),
                'AK': ('sale_tax_0', 'purchase_tax_0'),
                'AZ': ('sale_tax_5_6', 'purchase_tax_5_6'),
                'AR': ('sale_tax_6_5', 'purchase_tax_6_5'),
                'CA': ('sale_tax_7_25', 'purchase_tax_7_25'),
                'CO': ('sale_tax_2_9', 'purchase_tax_2_9'),
                'CT': ('sale_tax_6_35', 'purchase_tax_6_35'),
                'DE': ('sale_tax_0', 'purchase_tax_0'),
                'FL': ('sale_tax_6', 'purchase_tax_6'),
                'GA': ('sale_tax_4', 'purchase_tax_4'),
                'HI': ('sale_tax_4', 'purchase_tax_4'),
                'ID': ('sale_tax_6', 'purchase_tax_6'),
                'IL': ('sale_tax_6_25', 'purchase_tax_6_25'),
                'IN': ('sale_tax_7', 'purchase_tax_7'),
                'IA': ('sale_tax_6', 'purchase_tax_6'),
                'KS': ('sale_tax_6_5', 'purchase_tax_6_5'),
                'KY': ('sale_tax_6', 'purchase_tax_6'),
                'LA': ('sale_tax_5', 'purchase_tax_5'),
                'ME': ('sale_tax_5_5', 'purchase_tax_5_5'),
                'MD': ('sale_tax_6', 'purchase_tax_6'),
                'MA': ('sale_tax_6_25', 'purchase_tax_6_25'),
                'MI': ('sale_tax_6', 'purchase_tax_6'),
                'MN': ('sale_tax_6_875', 'purchase_tax_6_875'),
                'MS': ('sale_tax_7', 'purchase_tax_7'),
                'MO': ('sale_tax_4_225', 'purchase_tax_4_225'),
                'MT': ('sale_tax_0', 'purchase_tax_0'),
                'NE': ('sale_tax_5_5', 'purchase_tax_5_5'),
                'NV': ('sale_tax_6_85', 'purchase_tax_6_85'),
                'NH': ('sale_tax_0', 'purchase_tax_0'),
                'NJ': ('sale_tax_6_625', 'purchase_tax_6_625'),
                'NM': ('sale_tax_4_875', 'purchase_tax_4_875'),
                'NY': ('sale_tax_4', 'purchase_tax_4'),
                'NC': ('sale_tax_4_75', 'purchase_tax_4_75'),
                'ND': ('sale_tax_5', 'purchase_tax_5'),
                'OH': ('sale_tax_5_75', 'purchase_tax_5_75'),
                'OK': ('sale_tax_4_5', 'purchase_tax_4_5'),
                'OR': ('sale_tax_0', 'purchase_tax_0'),
                'PA': ('sale_tax_6', 'purchase_tax_6'),
                'RI': ('sale_tax_7', 'purchase_tax_7'),
                'SC': ('sale_tax_6', 'purchase_tax_6'),
                'SD': ('sale_tax_4_2', 'purchase_tax_4_2'),
                'TN': ('sale_tax_7', 'purchase_tax_7'),
                'TX': ('sale_tax_6_25', 'purchase_tax_6_25'),
                'UT': ('sale_tax_6_1', 'purchase_tax_6_1'),
                'VT': ('sale_tax_6', 'purchase_tax_6'),
                'VA': ('sale_tax_5_3', 'purchase_tax_5_3'),
                'WA': ('sale_tax_6_5', 'purchase_tax_6_5'),
                'WV': ('sale_tax_6', 'purchase_tax_6'),
                'WI': ('sale_tax_5', 'purchase_tax_5'),
                'WY': ('sale_tax_4', 'purchase_tax_4'),
                'DC': ('sale_tax_6', 'purchase_tax_6'),
            }.get(self.env.company.state_id.code, ('sale_tax_6', 'purchase_tax_6'))
        return {
            self.env.company.id: {
                'account_sale_tax_id': default_sales_tax,
                'account_purchase_tax_id': default_purchase_tax,
            }
        }
