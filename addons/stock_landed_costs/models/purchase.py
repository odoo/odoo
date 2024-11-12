from odoo import api,models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move)
        res.update({'is_landed_costs_line': self.product_id.landed_cost_ok})
        return res
