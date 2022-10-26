# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockAssignSerialNumbers(models.TransientModel):
    _name = 'stock.assign.serial'
    _description = 'Stock Assign Serial Numbers'

    def _default_next_serial_count(self):
        move = self.env['stock.move'].browse(self.env.context.get('default_move_id'))
        if move.exists():
            filtered_move_lines = move.move_line_ids.filtered(lambda l: not l.lot_name and not l.lot_id)
            return len(filtered_move_lines)

    product_id = fields.Many2one('product.product', 'Product',
        related='move_id.product_id')
    move_id = fields.Many2one('stock.move')
    next_serial_number = fields.Char('First SN', required=True)
    next_serial_count = fields.Integer('Number of SN',
        default=_default_next_serial_count, required=True)

    @api.constrains('next_serial_count')
    def _check_next_serial_count(self):
        for wizard in self:
            if wizard.next_serial_count < 1:
                raise ValidationError(_("The number of Serial Numbers to generate must be greater than zero."))

    def generate_serial_numbers(self):
        self.ensure_one()
        self.move_id.next_serial = self.next_serial_number or ""
        return self.move_id._generate_serial_numbers(next_serial_count=self.next_serial_count)
