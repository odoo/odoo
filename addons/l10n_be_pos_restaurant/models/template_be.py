# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

from odoo.addons.account.models.chart_template import template

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('be', 'account.tax')
    def _get_be_pos_restaurant_account_tax(self):
        be_restaurant_tax = self._parse_csv('be', 'account.tax', module='l10n_be_pos_restaurant')
        existing_taxes = self.env['account.tax'].search([('company_id', 'child_of', self.env.company.root_id.id)])
        # Filter out taxes that already exist
        existing_tax_names = set(existing_taxes.mapped('name'))
        taxes_to_create = {name: tax for name, tax in be_restaurant_tax.items() if tax['name'] not in existing_tax_names}
        self._deref_account_tags('be_comp', be_restaurant_tax)
        return taxes_to_create
