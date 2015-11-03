# -*- coding: utf-8 -*-
from odoo import fields, models


class RestaurantPrinter(models.Model):
    _name = 'restaurant.printer'

    name = fields.Char(string='Printer Name', required=True, help='An internal identification of the printer', default='Printer')
    proxy_ip = fields.Char(string='Proxy IP Address', size=32, help="The IP Address or hostname of the Printer's hardware proxy")
    product_categories_ids = fields.Many2many('pos.category', 'printer_category_rel', 'printer_id', 'category_id', string='Printed Product Categories')
