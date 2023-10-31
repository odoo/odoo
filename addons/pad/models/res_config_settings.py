# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pad_server = fields.Char(config_parameter='pad.pad_server', string="Pad Server")
    pad_key = fields.Char(config_parameter='pad.pad_key', string="Pad API Key")
