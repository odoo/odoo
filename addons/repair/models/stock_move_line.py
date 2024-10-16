# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import stock


class StockMoveLine(stock.StockMoveLine):

    def _should_show_lot_in_invoice(self):
        return super()._should_show_lot_in_invoice() or self.move_id.repair_line_type
