from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('gp')
    def _get_gp_template_data(self):
        return {
            'code_digits': '6',
            'parent': 'fr_comp',
        }

    def _deref_account_tags(self, template_code, tax_data):
        if template_code == 'gp':
            template_code = 'fr_comp'
        return super()._deref_account_tags(template_code, tax_data)
