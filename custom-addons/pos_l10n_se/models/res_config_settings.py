# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_iface_sweden_fiscal_data_module = fields.Many2one(
        "iot.device",
        compute="_compute_pos_iface_sweden_fiscal_data_module",
        store=True,
        readonly=False,
    )

    @api.depends("pos_is_posbox", "pos_config_id")
    def _compute_pos_iface_sweden_fiscal_data_module(self):
        for res_config in self:
            if not res_config.pos_is_posbox:
                res_config.pos_iface_sweden_fiscal_data_module = False
            else:
                res_config.pos_iface_sweden_fiscal_data_module = (
                    res_config.pos_config_id.iface_sweden_fiscal_data_module
                )
