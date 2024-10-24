from odoo import models, fields, api

class StockMoveLine(models.Model):
    _inherit = "stock.move"

    remaining_qty = fields.Float('Remaining Quantity', compute='_compute_remaining_qty', store=True)
    is_remaining_qty = fields.Boolean(string='Remaining', default=False)
    delivery_receipt_state = fields.Selection([('draft', 'Draft'),
                                               ('partially_received', 'Partially Received'),
                                               ('fully_received', 'Fully Received')],
                                              string='Delivery Receipt Status', default='draft')

    @api.depends('quantity')
    def _compute_remaining_qty(self):
        """
        Compute remaining quantity based on the quantity ordered (product_uom_qty)
        and the quantity done (quantity). Remaining qty is initially equal to available qty.
        """
        for move in self:
            # Initial remaining qty is the product_uom_qty (expected qty)
            move.remaining_qty = move.quantity
            # move.is_remaining_qty = move.remaining_qty > 0

    @api.depends('remaining_qty')
    def _compute_delivery_receipt_state(self):
        """
        Compute the delivery receipt state based on the remaining quantity.
        If there is any remaining quantity, it is 'Partially Received', otherwise 'Fully Received'.
        """
        for move in self:
            if move.remaining_qty > 0:
                move.delivery_receipt_state = 'partially_received'
            else:
                move.delivery_receipt_state = 'fully_received'
