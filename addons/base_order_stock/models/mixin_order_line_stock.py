from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import float_compare, float_is_zero

from .mixin_order_stock import TRANSFER_STATE

_debug = DebugLog(__name__)


class MixinOrderLineStock(models.AbstractModel):
    _name = "mixin.order.line.stock"
    _description = "Order Line Stock Integration"

    qty_to_transfer = fields.Float(
        digits="Product Unit",
        compute="_compute_qty_to_transfer",
        store=True,
    )

    transfer_state = fields.Selection(
        selection=TRANSFER_STATE,
        string="Transfer Status",
        compute="_compute_transfer_state",
        default="no",
        store=True,
    )

    @api.depends("state", "product_qty", "qty_transferred", "qty_to_transfer")
    def _compute_transfer_state(self):
        _debug.perf.count("line_transfer_state_compute", lines=self)
        precision = self.env["decimal.precision"].get_precision("Product Unit")
        self.filtered("display_type").transfer_state = "no"
        for line in self.filtered(lambda l: not l.display_type):
            if line.state != "done" or float_is_zero(
                line.product_qty, precision_digits=precision
            ):
                line.transfer_state = "no"
                continue

            if not float_is_zero(line.qty_to_transfer, precision_digits=precision):
                line.transfer_state = (
                    "to do"
                    if float_is_zero(line.qty_transferred, precision_digits=precision)
                    else "partial"
                )
                continue

            compare = float_compare(
                line.qty_transferred, line.product_qty, precision_digits=precision
            )
            if compare > 0:
                line.transfer_state = "over done"
            elif compare == 0:
                line.transfer_state = "done"
            else:
                line.transfer_state = "partial"

    @api.depends("product_qty", "qty_transferred")
    def _compute_qty_to_transfer(self):
        for line in self:
            line.qty_to_transfer = max(0.0, line.product_qty - line.qty_transferred)

    def _get_stock_moves_outgoing_incoming(self, **kwargs):
        raise NotImplementedError(
            f"{self._name} must implement _get_stock_moves_outgoing_incoming()",
        )

    def _get_procurement_qty(self, previous_product_qty=False):
        _debug.logic("line_procurement_qty", lines=self)
        self.check_singleton()
        procured_moves, returned_moves = self._get_procurement_moves()
        return self._get_moves_qty_sum(procured_moves) - self._get_moves_qty_sum(
            returned_moves
        )

    def _get_procurement_moves(self):
        raise NotImplementedError(
            f"{self._name} must implement _get_procurement_moves()",
        )

    def _get_transferable_moves(self):
        _debug.logic("transferable_moves", lines=self)
        self.check_singleton()
        return self.move_ids.filtered(
            lambda m: (
                m.state != "cancel"
                and m.location_dest_usage != "inventory"
                and m.product_id == self.product_id
            ),
        )

    def _get_moves_qty_sum(self, moves):
        return sum(
            move.product_uom_id._get_quantity_in_unit(
                move.quantity if move.state == "done" else move.product_uom_qty,
                self.product_uom_id,
                rounding_method="HALF-UP",
            )
            for move in moves
        )
