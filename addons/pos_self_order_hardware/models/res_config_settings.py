# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_module_pos_hardware = fields.Boolean(related='pos_config_id.module_pos_hardware', readonly=False)
