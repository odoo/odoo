# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_floor_ids = fields.Many2many(related='pos_config_id.floor_ids', readonly=False)
    pos_default_screen = fields.Selection(related="pos_config_id.default_screen", readonly=False)
    pos_use_course_allocation = fields.Boolean(related='pos_config_id.use_course_allocation', readonly=False)
