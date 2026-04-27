# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    iface_fiscal_data_module = fields.Many2one(
        related="pos_config_id.iface_fiscal_data_module", readonly=False
    )
