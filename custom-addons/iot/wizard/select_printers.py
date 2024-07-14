# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class SelectPrinter(models.TransientModel):
    _name = "select.printers.wizard"
    _description = "Selection of printers"

    device_ids = fields.Many2many('iot.device', domain=[('type', '=', 'printer')])
    display_device_ids = fields.Many2many('iot.device', relation='display_device_id_select_printer', domain=[('type', '=', 'printer')])

    def select_iot(self):
        return {"type": "ir.actions.act_window_close"}
