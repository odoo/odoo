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
    xdock_packaging_qty = fields.Float(
        string="Xdock Packaging Quantity")

    xdock_qty = fields.Float(
        string='XDOCk Quantity',
        compute='_compute_xdock_packaging_quantity',
        inverse='_inverse_xdock_qty',
        store=False  # Do not store since it could be manual or computed
    )
    xdock_remaining_qty = fields.Float(string='XDOCk Remaining Quantity')
    show_xdock_qty_editable = fields.Boolean(
        string='Show XDock Qty Editable', compute='_compute_show_xdock_qty_editable')

    @api.depends('product_packaging_id')
    def _compute_show_xdock_qty_editable(self):
        for move in self:
            move.show_xdock_qty_editable = not bool(move.product_packaging_id)

    @api.depends('product_packaging_id', 'xdock_packaging_qty')
    def _compute_xdock_packaging_quantity(self):
        """
        Computes xdock_qty by converting the xdock_packaging_qty using the packaging's conversion factor.
        If no packaging is selected, user can enter xdock_qty manually (handled via inverse).
        """
        for move in self:
            if move.product_packaging_id and move.xdock_packaging_qty:
                move.xdock_qty = move.product_packaging_id.qty * move.xdock_packaging_qty
            elif not move.product_packaging_id:
                # If no packaging, keep whatever value the user entered manually
                move.xdock_qty = move.xdock_qty or 0.0
            else:
                move.xdock_qty = 0.0

    def _inverse_xdock_qty(self):
        """
        Allow manual entry of xdock_qty when no packaging is selected.
        """
        # No logic required unless you want to reverse-compute xdock_packaging_qty
        # Not needed unless you want to update packaging_qty from manually set xdock_qty
        pass

    @api.depends('xdock_qty')
    def _compute_xdock_qty_remaining_qty(self):
        for move in self:
            move.xdock_remaining_qty = move.xdock_qty

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
