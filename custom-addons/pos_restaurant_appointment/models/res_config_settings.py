  # -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_appointment_type_ids = fields.Many2many(related="pos_config_id.appointment_type_ids", readonly=False)
