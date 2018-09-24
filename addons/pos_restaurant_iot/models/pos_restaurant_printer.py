# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class RestaurantPrinter(models.Model):

    _name = 'restaurant.printer'

    name = fields.Char('Printer Name', required=True, default='Printer', help='An internal identification of the printer')
    iot_box_id = fields.Many2one('iot.box', string="IoTBox")
    proxy_ip = fields.Char(string='IP Address', related="iot_box_id.ip", store=True)
    product_categories_ids = fields.Many2many('pos.category', 'printer_category_rel', 'printer_id', 'category_id', string='Printed Product Categories')
