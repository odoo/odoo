# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    use_expiration_date = fields.Boolean(
        string='Use Expiration Date', related='product_id.use_expiration_date')

    def _generate_serial_move_line_commands(self, lot_names, origin_move_line=None):
        """Override to add a default `expiration_date` into the move lines values."""
        move_lines_commands = super()._generate_serial_move_line_commands(lot_names, origin_move_line=origin_move_line)
        if self.product_id.use_expiration_date:
            date = fields.Datetime.today() + datetime.timedelta(days=self.product_id.expiration_time)
            for move_line_command in move_lines_commands:
                move_line_vals = move_line_command[2]
                move_line_vals['expiration_date'] = date
        return move_lines_commands
