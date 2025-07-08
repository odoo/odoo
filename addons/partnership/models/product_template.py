# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_tracking = fields.Selection(
        selection_add=[('partnership', 'Membership / Partnership')], ondelete={'partnership': 'set default'}
    )
    grade_id = fields.Many2one('res.partner.grade', string="Assigned Level")

    @api.model
    def _get_saleable_tracking_types(self):
        return super()._get_saleable_tracking_types() + ['partnership']
