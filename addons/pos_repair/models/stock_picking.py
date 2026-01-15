# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _create_move_from_pos_order_lines(self, lines):
        return super()._create_move_from_pos_order_lines(lines.filtered(lambda line: not line.sale_order_line_id or not line.sale_order_line_id.is_repair_line))
