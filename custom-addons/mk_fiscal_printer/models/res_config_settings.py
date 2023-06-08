# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    fiscal_printer_ip = fields.Char(compute='_compute_fiscal_printer_ip', store=True, readonly=False)

    @api.depends('pos_other_devices', 'pos_config_id')
    def _compute_fiscal_printer_ip(self):
        for res_config in self:
            res_config.fiscal_printer_ip = res_config.pos_config_id.fiscal_printer_ip