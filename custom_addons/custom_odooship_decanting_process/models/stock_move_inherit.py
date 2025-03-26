from odoo import models, fields, api
from odoo.exceptions import ValidationError

class StockMoveLine(models.Model):
    _inherit = "stock.move"

    remaining_qty = fields.Float('Remaining Quantity', compute='_compute_remaining_qty', store=True)
    is_remaining_qty = fields.Boolean(string='Remaining', default=False)
    delivery_receipt_state = fields.Selection([('draft', 'Draft'),
                                               ('partially_received', 'Partially Received'),
                                               ('fully_received', 'Fully Received')],
                                              string='Delivery Receipt Status', default='draft')
    packed = fields.Boolean('Packed', default=False)
    released_manual = fields.Boolean('Released', default=False)
    xdock_qty = fields.Float(string='XDOCk Quantity', compute='_compute_xdock_packaging_quantity')
    xdock_remaining_qty = fields.Float(string='XDOCk Remaining Quantity')
    product_packaging_id = fields.Many2one('product.packaging', 'Packaging', domain="[('product_id', '=', product_id)]",
                                           check_company=True)
    xdock_packaging_qty = fields.Float(
        string="Xdock Packaging Quantity")

    @api.depends('product_packaging_id', 'xdock_packaging_qty')
    def _compute_xdock_packaging_quantity(self):
        """
        Computes xdock_qty by converting the xdock_packaging_qty using the packaging's conversion factor.
        """
        for move in self:
            if move.product_packaging_id and move.xdock_packaging_qty:
                move.xdock_qty = move.product_packaging_id.qty * move.xdock_packaging_qty
            else:
                move.xdock_qty = 0.0

    @api.depends('xdock_qty')
    def _compute_xdock_qty_remaining_qty(self):
        """
        Compute Xdock remaining quantity based on the XDOCK quantity ordered
        """
        for move in self:
            move.xdock_remaining_qty = move.xdock_qty

    @api.depends('quantity')
    def _compute_remaining_qty(self):
        """
        Compute remaining quantity based on the quantity ordered (product_uom_qty)
        and the quantity done (quantity). Remaining qty is initially equal to available qty.
        """
        for move in self:
            # Initial remaining qty is the product_uom_qty (expected qty)
            move.remaining_qty = move.quantity

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

    @api.onchange('packed')
    def _onchange_packed(self):
        """
        Prevent unpacking if the item is already marked as manually released.
        """
        for move in self:
            if not move.packed and move.released_manual:
                raise ValidationError("This item has already been delivered manually and cannot be unpacked.")
