# -*- coding: utf-8 -*-
from odoo.addons import point_of_sale
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class PosConfig(models.Model, point_of_sale.PosConfig):

    epson_printer_ip = fields.Char(string='Epson Printer IP', help="Local IP address of an Epson receipt printer.")
