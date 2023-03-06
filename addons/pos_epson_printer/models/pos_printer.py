# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class PosPrinter(models.Model):

    _inherit = 'pos.printer'

    printer_type = fields.Selection(selection_add=[('epson_epos', 'Use an Epson printer')])
    epson_printer_ip = fields.Char(string='Epson Printer IP Address', help="Local IP address of an Epson receipt printer.", default="0.0.0.0")

    @api.constrains('epson_printer_ip')
    def _constrains_epson_printer_ip(self):
        for record in self:
            if record.printer_type == 'epson_epos' and not record.epson_printer_ip:
                raise ValidationError(_("Epson Printer IP Address cannot be empty."))
