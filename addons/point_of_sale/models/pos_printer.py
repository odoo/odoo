# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class PosPrinter(models.Model):

    _name = 'pos.printer'
    _description = 'Point of Sale Printer'

    name = fields.Char('Printer Name', required=True, default='Printer', help='An internal identification of the printer')
    printer_type = fields.Selection(string='Printer Type', default='iot',
        selection=[('iot', ' Use a printer connected to an IoT System')])
    proxy_ip = fields.Char('Proxy IP Address', help="The IP Address or hostname of the Printer's hardware proxy")
    product_categories_ids = fields.Many2many('pos.category', 'printer_category_rel', 'printer_id', 'category_id', string='Printed Product Categories')
