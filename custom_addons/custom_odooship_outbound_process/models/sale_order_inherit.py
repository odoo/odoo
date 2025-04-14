# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo import models, fields

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    serial_number = fields.Char(string="Serial Number")
    line_item_id = fields.Char(string="Line Item ID")
