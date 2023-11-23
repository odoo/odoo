from odoo import api,models

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_invoice_line(self, move=False, **optional_values):
        res = super()._prepare_invoice_line(move, **optional_values)
        res.update({'is_landed_costs_line': self.product_id.landed_cost_ok})
        return res
