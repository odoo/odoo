from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockMoveLine(models.Model):
    _inherit = "stock.move"


    packed = fields.Boolean('Packed', default=False)
    released_manual_orders = fields.Selection([('partially_released','Partially Released'),
                                        ('fully_released','Fully Released')],
                                       string='Released Orders')
    remaining_packed_qty = fields.Float('Packed Remaining Quantity', compute='_compute_remaining_packed_qty',
                                        store=True)
    released_manual = fields.Boolean('Released', default=False)



    @api.depends('quantity')
    def _compute_remaining_packed_qty(self):
        """
        Compute remaining quantity based on the quantity ordered (product_uom_qty)
        and the quantity done (quantity). Remaining qty is initially equal to available qty.
        """
        for move in self:
            # Initial remaining qty is the product_uom_qty (expected qty)
            move.remaining_packed_qty = move.quantity
            # move.is_remaining_qty = move.remaining_qty > 0

    @api.onchange('packed')
    def _onchange_packed(self):
        """
        Prevent unpacking if the item is already marked as manually released.
        """
        for move in self:
            if not move.packed and move.released_manual:
                raise ValidationError("This item has already been delivered manually and cannot be unpacked.")
