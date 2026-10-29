# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    restrict_zero_price_line = fields.Boolean(string="Restrict Zero Price Order Line")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_restrict_zero_price_line = fields.Boolean(related='pos_config_id.restrict_zero_price_line', readonly=False)




