# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    khmer_receipt = fields.Boolean(related="pos_config_id.khmer_receipt", readonly=False)
