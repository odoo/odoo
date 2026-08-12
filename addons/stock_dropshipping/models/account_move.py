from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _should_use_related_analytic_distribution(self, source):
        # EXTENDS 'account'
        res = super()._should_use_related_analytic_distribution(source)
        stock_move = self.move_id.stock_move_id
        if stock_move.sale_line_id and stock_move.purchase_line_id and source._name == 'sale.order.line':
            # Dropship move: it's linked to both a sale line and a purchase line, and the
            # purchase line distribution already covers the case, so
            # don't also add the sale line's on top of it (that would go over 100%).
            return False
        return res
