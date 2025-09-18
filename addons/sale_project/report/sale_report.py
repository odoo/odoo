# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SaleReport(models.Model):
    _inherit = 'sale.report'

    project_id = fields.Many2one(comodel_name='project.project', readonly=True)

    def _get_select_fields(self):
        fields = super()._get_select_fields()
        fields['project_id'] = 'o.project_id'
        return fields
