# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

from odoo.addons.account.models.chart_template import template

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('be', 'account.tax')
    def _get_be_pos_restaurant_account_tax(self):
        pos_taxes = self._parse_csv('be', 'account.tax', module='l10n_be_pos_restaurant')
        self._deref_account_tags('be_comp', pos_taxes)
        return pos_taxes
