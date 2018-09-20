# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit='pos.config'

    printer_ids = fields.Many2many('restaurant.printer', 'pos_config_printer_rel', 'config_id', 'printer_id', string='Order Printers')

    @api.onchange('module_pos_restaurant_iot')
    def _onchange_module_pos_restaurant_iot(self):
        if not self.module_pos_restaurant_iot:
            self.printer_ids = [(5, 0, 0)]
