# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('xi')
    def _get_mc_template_data(self):
        return {
            'parent': 'uk',
        }

    def _deref_account_tags(self, template_code, tax_data):
        if template_code == 'xi':
            template_code = 'uk'
        return super()._deref_account_tags(template_code, tax_data)
