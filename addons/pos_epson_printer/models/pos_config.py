# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    epson_printer_ip = fields.Char(string='Epson Printer IP', help="Local IP address of an Epson receipt printer.")

    @api.onchange('epson_printer_ip')
    def _onchange_epson_printer_ip(self):
        if self.epson_printer_ip in (False, ''):
            self.iface_cashdrawer = False
