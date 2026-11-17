from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('gf')
    def _get_gf_template_data(self):
        return {
            'code_digits': '6',
            'parent': 'fr_comp',
        }

    def _get_chart_template_data(self, template_code, demo=False, module=None):
        data = super()._get_chart_template_data(template_code, demo=demo, module=module)
        if template_code == 'gf' and self.env.company.id in data.get('res.company', {}):
            data['res.company'][self.env.company.id].update({
                'account_sale_tax_id': 'tva_sale_good_na',
                'account_purchase_tax_id': 'tva_purchase_good_na',
            })
        return data

    def _deref_account_tags(self, template_code, tax_data):
        if template_code == 'gf':
            template_code = 'fr_comp'
        return super()._deref_account_tags(template_code, tax_data)
