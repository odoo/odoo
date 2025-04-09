# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    extra_hours_leave_type_id = fields.Many2one(related='company_id.extra_hours_leave_type_id', readonly=False)
