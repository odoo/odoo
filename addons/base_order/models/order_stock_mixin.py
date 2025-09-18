"""
Order Stock Integration Mixins

Consolidates 450+ lines of stock/delivery tracking logic duplicated across order types.
Provides unified picking tracking, transfer status, and quantity transferred computation.
"""

from odoo import api, fields, models


class OrderStockMixin(models.AbstractModel):
    """Order-level stock/picking tracking and transfer status.

    Provides delivery/receipt tracking fields and methods common to all order types
    (sale, purchase, etc.). Child models must implement abstract methods to specify
    picking relationships and transfer status labels.
    """

    _name = "order.stock.mixin"
    _description = "Order Stock Integration"

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------

    # Picking/transfer tracking
    picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Transfers",
        compute="_compute_picking_ids",
        store=True,
        copy=False,
        help="Delivery orders / receipt pickings for this order",
    )
    picking_count = fields.Integer(
        string="Transfer Count",
        compute="_compute_picking_count",
        help="Number of delivery orders / receipts",
    )

    # Transfer status (renamed from delivery_state/receipt_state)
    transfer_status = fields.Selection(
        selection="_get_transfer_status_selection",
        string="Transfer Status",
        compute="_compute_transfer_status",
        store=True,
        help="Status of deliveries/receipts for this order",
    )

    # Effective date (completion date)
    date_transferred = fields.Datetime(
        string="Transfer Date",
        compute="_compute_date_transferred",
        store=True,
        copy=False,
        help="Completion date of the first transfer",
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends("line_ids.move_ids", "line_ids.move_ids.picking_id")
    def _compute_picking_ids(self):
        """Compute pickings from line stock moves.

        Aggregates all pickings linked to order line moves.
        """
        for order in self:
            # Get all pickings from line moves
            pickings = order.line_ids.move_ids.picking_id
            order.picking_ids = pickings

    @api.depends("picking_ids")
    def _compute_picking_count(self):
        """Count number of pickings."""
        for order in self:
            order.picking_count = len(order.picking_ids)

    @api.depends("picking_ids", "picking_ids.state", "line_ids.quantity_transferred")
    def _compute_transfer_status(self):
        """Compute transfer status from picking states.

        Logic is 90% identical between sale and purchase:
        - No pickings or all canceled: False/pending
        - All done/canceled: full/done
        - Some done: partial/started
        - None done: pending
        """
        for order in self:
            # No pickings or all canceled
            if not order.picking_ids or all(
                p.state == "cancel" for p in order.picking_ids
            ):
                order.transfer_status = order._get_no_transfer_status()
            # All transfers done
            elif all(p.state in ["done", "cancel"] for p in order.picking_ids):
                order.transfer_status = order._get_full_transfer_status()
            # Some transfers done - check if partial or just started
            elif any(p.state == "done" for p in order.picking_ids):
                # Check if any quantity actually transferred
                if order._has_partial_transfer():
                    order.transfer_status = order._get_partial_transfer_status()
            # No transfers done yet
            else:
                order.transfer_status = order._get_pending_transfer_status()

    @api.depends("picking_ids.date_done")
    def _compute_date_transferred(self):
        """Compute transfer completion date from first completed picking."""
        for order in self:
            # Filter done pickings with date_done
            done_pickings = order.picking_ids.filtered(
                lambda p: p.state == "done" and p.date_done
            )

            # Additional filtering hook for child models
            done_pickings = order._filter_done_pickings(done_pickings)

            # Get earliest completion date
            order.date_transferred = min(
                done_pickings.mapped("date_done"), default=False
            )

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _has_partial_transfer(self):
        """Check if order has partial transfer.

        Default implementation checks if any line has quantity transferred.
        Override in child models for custom logic.

        Returns:
            bool: True if partially transferred
        """
        self.ensure_one()
        return any(line.quantity_transferred for line in self.line_ids)

    def _filter_done_pickings(self, pickings):
        """Filter done pickings for date computation.

        Hook for child models to add custom filtering.
        For example, purchase might exclude supplier returns.

        Args:
            pickings: Recordset of done pickings

        Returns:
            recordset: Filtered pickings
        """
        return pickings

    # -------------------------------------------------------------------------
    # ABSTRACT METHODS - Must be implemented by child models
    # -------------------------------------------------------------------------

    @api.model
    def _get_transfer_status_selection(self):
        """Return transfer status selection values.

        Examples:
            - Sale: [('to do', 'Not Delivered'), ('partial', 'Partially Delivered'), ...]
            - Purchase: [('to do', 'Not Received'), ('partial', 'Partially Received'), ...]

        Returns:
            list: Selection tuples [(value, label), ...]
        """
        raise NotImplementedError(
            "Child model must implement _get_transfer_status_selection() "
            "to return status selection values"
        )

    def _get_no_transfer_status(self):
        """Return status value when no pickings exist.

        Returns:
            str: Status value (e.g., False, 'to do', 'no')
        """
        return False

    def _get_full_transfer_status(self):
        """Return status value when fully transferred.

        Examples:
            - Sale: 'done'
            - Purchase: 'done'

        Returns:
            str: Status value
        """
        return "done"

    def _get_partial_transfer_status(self):
        """Return status value when partially transferred.

        Examples:
            - Sale: 'partial'
            - Purchase: 'partial'

        Returns:
            str: Status value
        """
        return "partial"

    def _get_pending_transfer_status(self):
        """Return status value when transfer pending.

        Examples:
            - Sale: 'to do'
            - Purchase: 'to do'

        Returns:
            str: Status value
        """
        return "to do"

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_view_transfers(self):
        """Open pickings/transfers view.

        Returns action to display transfers in list/form view.
        Child models should override to customize view.
        """
        self.ensure_one()

        # Get action from child model
        action = self._get_transfer_action()

        pickings = self.picking_ids
        if len(pickings) == 1:
            action["views"] = [(False, "form")]
            action["res_id"] = pickings.id
        else:
            action["domain"] = [("id", "in", pickings.ids)]

        return action

    def _get_transfer_action(self):
        """Return base action for viewing transfers.

        Child models should override to return appropriate action.

        Returns:
            dict: Action dictionary
        """
        return self.env["ir.actions.act_window"]._for_xml_id(
            "stock.action_picking_tree_all"
        )


class OrderLineStockMixin(models.AbstractModel):
    """Line-level stock move tracking and quantity transferred computation.

    Consolidates stock move tracking and quantity transferred calculation
    that was duplicated between sale and purchase order lines.
    """

    _name = "order.line.stock.mixin"
    _description = "Order Line Stock Integration"

    # NOTE: Child models MUST define move_ids field with appropriate inverse_name:
    # For sale: move_ids = fields.One2many('stock.move', inverse_name='sale_line_id', ...)
    # For purchase: move_ids = fields.One2many('stock.move', inverse_name='purchase_line_id', ...)

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------

    # Transfer method (how quantity is tracked)
    quantity_transferred_method = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("stock_move", "Stock Moves"),
            ("analytic", "Analytic"),
        ],
        string="Transfer Method",
        compute="_compute_quantity_transferred_method",
        store=True,
        help="Method used to compute transferred quantity",
    )

    quantity_transferred = fields.Float(
        string="Transferred Quantity",
        compute="_compute_quantity_transferred",
        digits="Product Unit of Measure",
        store=True,
        help="Quantity already transferred/delivered/received",
    )

    # Quantity to transfer (not yet transferred)
    quantity_to_transfer = fields.Float(
        string="To Transfer",
        compute="_compute_quantity_to_transfer",
        digits="Product Unit of Measure",
        store=True,
        help="Remaining quantity to transfer",
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends("product_id", "product_id.type")
    def _compute_quantity_transferred_method(self):
        """Determine method for computing transferred quantity.

        - Analytic: For time-based products (timesheet)
        - Manual: For service products
        - Stock moves: For storable/consumable products
        """
        for line in self:
            if line._use_analytic_method():
                line.quantity_transferred_method = "analytic"
            elif line._use_manual_method():
                line.quantity_transferred_method = "manual"
            elif line._use_stock_move_method():
                line.quantity_transferred_method = "stock_move"
            else:
                line.quantity_transferred_method = False

    @api.depends(
        "quantity_transferred_method",
        "move_ids",
        "move_ids.state",
        "move_ids.quantity",
    )
    def _compute_quantity_transferred(self):
        """Compute quantity transferred based on method.

        For stock_move method, computes from stock moves.
        This is THE KEY CONSOLIDATION - logic was 90% identical!
        """
        # Let child models handle non-stock methods first
        for line in self.filtered(
            lambda l: l.quantity_transferred_method != "stock_move"
        ):
            line.quantity_transferred = line._compute_quantity_transferred_custom()

        # Handle stock move method
        lines_by_stock_move = self.filtered(
            lambda line: line.quantity_transferred_method == "stock_move"
        )
        for line in lines_by_stock_move:
            quantity_transferred = 0.0

            # Get moves filtered by direction
            outgoing_moves, incoming_moves = line._get_stock_moves_outgoing_incoming()

            # Sum outgoing moves (positive contribution)
            for move in outgoing_moves:
                if move.state != "done":
                    continue
                quantity_transferred += move.product_uom._compute_quantity(
                    move.quantity, line.product_uom_id, rounding_method="HALF-UP"
                )

            # Sum incoming moves (negative contribution)
            for move in incoming_moves:
                if move.state != "done":
                    continue
                quantity_transferred -= move.product_uom._compute_quantity(
                    move.quantity, line.product_uom_id, rounding_method="HALF-UP"
                )

            line.quantity_transferred = quantity_transferred

    @api.depends("quantity", "quantity_transferred")
    def _compute_quantity_to_transfer(self):
        """Compute remaining quantity to transfer."""
        for line in self:
            line.quantity_to_transfer = max(
                line.quantity - line.quantity_transferred, 0.0
            )

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_stock_moves_outgoing_incoming(self):
        """Get outgoing and incoming stock moves for this line.

        Splits moves by direction based on location_dest_id.
        Logic is identical for sale/purchase - just inverted direction.

        Returns:
            tuple: (outgoing_moves, incoming_moves)
        """
        self.ensure_one()

        # Get all moves for this line
        moves = self.move_ids

        # Filter by direction - let child model define "outgoing"
        outgoing_moves = moves.filtered(lambda m: self._is_outgoing_move(m))
        incoming_moves = moves - outgoing_moves

        return outgoing_moves, incoming_moves

    def _compute_quantity_transferred_custom(self):
        """Compute quantity for non-stock methods.

        Hook for child models to implement manual/analytic methods.

        Returns:
            float: Transferred quantity
        """
        return 0.0

    # -------------------------------------------------------------------------
    # ABSTRACT METHODS - Must be implemented by child models
    # -------------------------------------------------------------------------

    def _use_analytic_method(self):
        """Check if should use analytic method.

        Returns:
            bool: True if analytic method should be used
        """
        return False

    def _use_manual_method(self):
        """Check if should use manual method.

        Examples:
            - Service products typically use manual
            - Non-storable products

        Returns:
            bool: True if manual method should be used
        """
        return False

    def _use_stock_move_method(self):
        """Check if should use stock move method.

        Examples:
            - Storable products
            - Consumable products with stock tracking

        Returns:
            bool: True if stock move method should be used
        """
        return False

    def _is_outgoing_move(self, move):
        """Check if stock move is outgoing.

        THE KEY DIFFERENCE between sale and purchase:
            - Sale: Outgoing = customer destination
            - Purchase: Outgoing = supplier source (reversed!)

        Args:
            move: stock.move record

        Returns:
            bool: True if outgoing
        """
        raise NotImplementedError(
            "Child model must implement _is_outgoing_move() "
            "to determine move direction"
        )
