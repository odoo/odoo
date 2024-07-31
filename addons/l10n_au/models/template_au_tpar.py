# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('au_tpar')
    def _get_au_tpar_template_data(self):
        return {
            'name': _('Taxable payments annual report (TPAR)'),
            'parent': 'au',
        }
