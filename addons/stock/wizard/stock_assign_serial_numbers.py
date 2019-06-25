# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockAssignSerialNumbers(models.TransientModel):
    _name = 'stock.assign.serial'
    _description = 'Stock Assign Serial Numbers'

    product_id = fields.Many2one('product.product', 'Product',
        related='move_id.product_id', required=True)
    move_id = fields.Many2one('stock.move', required=True)
    next_serial_number = fields.Char('Next Serial Number')

    def generate_serial_numbers(self):
        self.ensure_one()
        self.move_id.next_serial = self.next_serial_number or ""
        return self.move_id._generate_serial_numbers()
