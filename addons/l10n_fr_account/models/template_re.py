from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('re')
    def _get_re_template_data(self):
        return {
            'code_digits': '6',
            'parent': 'fr',
        }

    def _deref_account_tags(self, template_code, tax_data):
        if template_code == 're':
            template_code = 'fr'
        return super()._deref_account_tags(template_code, tax_data)
