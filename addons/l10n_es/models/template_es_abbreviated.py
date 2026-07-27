from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_abbreviated')
    def _get_es_full_template_data(self):
        return {
            'name': _('Abbreviated (2008)'),
            'parent': 'es_full',
        }
