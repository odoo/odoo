# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # pos.config fields
    pos_employee_ids = fields.Many2many(related='pos_config_id.employee_ids', readonly=False)
