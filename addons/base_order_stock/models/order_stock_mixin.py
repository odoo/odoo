"""
Order Stock Integration Mixins

Bridge mixins connecting order types with stock/delivery tracking.
Consolidates the transfer status computation and effective date logic
shared between sale_stock and purchase_stock.

The order-level ``_compute_transfer_state`` is IDENTICAL between both
modules.  Only ``_compute_date_effective`` differs — sale filters to
customer-destination pickings, purchase to non-supplier-destination.

Field naming matches actual sale_stock/purchase_stock conventions:
``transfer_state``, ``date_effective``, ``qty_to_transfer``.
"""

from odoo import api, fields, models


TRANSFER_STATE = [
    ("no", "Nothing to transfer"),
    ("to do", "To transfer"),
    ("partial", "Partially transferred"),
    ("done", "Fully transferred"),
    ("over done", "Over transferred"),
]


# ════════════════════════════════════════════════════════════════════
# ORDER-LEVEL STOCK MIXIN
# ════════════════════════════════════════════════════════════════════


class OrderStockMixin(models.AbstractModel):
    """Order-level delivery/receipt tracking.

    Provides ``transfer_state``, ``date_effective``, incoterm fields,
    and the ``_get_action_view_picking()`` helper shared between
    sale_stock and purchase_stock.

    Requires from concrete model:
        ``picking_ids`` — One2many to ``stock.picking``
        ``line_ids`` — One2many to order lines (with ``qty_transferred``)
    """

    _name = "order.stock.mixin"
    _description = "Order Stock Integration"

    # ─── Transfer Status ─────────────────────────────────────────

    transfer_state = fields.Selection(
        selection=TRANSFER_STATE,
        string="Transfer Status",
        compute="_compute_transfer_state",
        store=True,
    )

    # ─── Effective Date ──────────────────────────────────────────

    date_effective = fields.Datetime(
        string="Effective Date",
        compute="_compute_date_effective",
        store=True,
        copy=False,
    )

    # ─── Incoterms ───────────────────────────────────────────────

    incoterm_id = fields.Many2one(
        comodel_name="account.incoterms",
        string="Incoterm",
    )
    incoterm_location = fields.Char(string="Incoterm Location")

    # ─── Compute: Transfer State ─────────────────────────────────

    @api.depends("picking_ids", "picking_ids.state")
    def _compute_transfer_state(self):
        """Compute transfer status from picking states.

        IDENTICAL in sale_stock and purchase_stock.  The logic:
        - No pickings or all canceled → ``False``
        - All done/canceled → ``'done'``
        - Some done with transferred qty → ``'partial'``
        - Some done without transferred qty → ``'partial'``
        - Otherwise → ``'to do'``
        """
        for order in self:
            if not order.picking_ids or all(
                p.state == "cancel" for p in order.picking_ids
            ):
                order.transfer_state = False
            elif all(
                p.state in ["done", "cancel"] for p in order.picking_ids
            ):
                order.transfer_state = "done"
            elif any(
                p.state == "done" for p in order.picking_ids
            ) and any(l.qty_transferred for l in order.line_ids):
                order.transfer_state = "partial"
            elif any(p.state == "done" for p in order.picking_ids):
                order.transfer_state = "partial"
            else:
                order.transfer_state = "to do"

    # ─── Compute: Effective Date ─────────────────────────────────

    @api.depends("picking_ids.date_done")
    def _compute_date_effective(self):
        """Compute completion date from first done picking.

        Delegates filtering to ``_filter_effective_pickings()`` hook:
        - Sale: customer-destination pickings
        - Purchase: non-supplier-destination pickings
        """
        for order in self:
            pickings = order._filter_effective_pickings(order.picking_ids)
            dates = [d for d in pickings.mapped("date_done") if d]
            order.date_effective = min(dates, default=False)

    def _filter_effective_pickings(self, pickings):
        """Filter pickings for effective date computation.

        Default: done pickings with ``date_done`` set.

        Sale overrides: ``location_dest_id.usage == 'customer'``
        Purchase overrides: ``location_dest_id.usage != 'supplier'``
        """
        return pickings.filtered(
            lambda p: p.state == "done" and p.date_done,
        )

    # ─── Actions ─────────────────────────────────────────────────

    def _get_action_view_picking(self, pickings):
        """Build action dict to display pickings in list/form view.

        Nearly identical in sale_stock and purchase_stock.
        Both use ``stock.action_picking_tree_all`` as the base action.

        :param pickings: recordset of ``stock.picking``
        :returns: action dict
        """
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock.action_picking_tree_all",
        )
        if len(pickings) == 1:
            form_view = [
                (self.env.ref("stock.view_picking_form").id, "form"),
            ]
            action["views"] = form_view
            action["res_id"] = pickings.id
        elif pickings:
            action["domain"] = [("id", "in", pickings.ids)]
        return action


# ════════════════════════════════════════════════════════════════════
# LINE-LEVEL STOCK MIXIN
# ════════════════════════════════════════════════════════════════════


class OrderLineStockMixin(models.AbstractModel):
    """Line-level stock move tracking.

    Provides ``qty_to_transfer`` and the ``_get_stock_moves_outgoing_incoming``
    hook shared between sale_stock and purchase_stock.

    The ``_compute_qty_transferred`` implementations differ too much to unify:
    - Sale: simple outgoing/incoming classification by location dest
    - Purchase: complex return + BOM kit + dropship handling

    Both compute ``qty_to_transfer`` inside ``_compute_qty_transferred``.

    Requires from concrete model:
        ``move_ids`` — One2many to ``stock.move`` (different inverse per model)
        ``product_qty`` — ordered quantity
        ``qty_transferred`` — transferred quantity
        ``product_uom_id`` — UoM for quantity conversion
    """

    _name = "order.line.stock.mixin"
    _description = "Order Line Stock Integration"

    # ─── Fields ───────────────────────────────────────────────────

    qty_to_transfer = fields.Float(
        string="To Transfer",
        digits="Product Unit",
        compute="_compute_qty_transferred",
        store=True,
    )

    # ─── Helpers ──────────────────────────────────────────────────

    def _get_stock_moves_outgoing_incoming(self):
        """Classify stock moves as outgoing and incoming.

        THE KEY DIFFERENCE between sale and purchase:
        - Sale: outgoing = customer destination, incoming = returns
        - Purchase: outgoing = returns to supplier, incoming = receipts

        :returns: ``(outgoing_moves, incoming_moves)`` tuple of recordsets
        """
        raise NotImplementedError(
            f"{self._name} must implement _get_stock_moves_outgoing_incoming()",
        )
