import logging
from copy import deepcopy

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class WooStockPickingRefundBatchImporter(Component):
    _name = "woo.stock.picking.refund.batch.importer"
    _inherit = "woo.delayed.batch.importer"
    _apply_on = "woo.stock.picking.refund"


class WooStockPickingRefundImportMapper(Component):
    _name = "woo.stock.picking.refund.import.mapper"
    _inherit = "woo.import.mapper"
    _apply_on = "woo.stock.picking.refund"


class WooStockPickingRefundImporter(Component):
    _name = "woo.stock.picking.refund.importer"
    _inherit = "woo.importer"
    _apply_on = "woo.stock.picking.refund"

    def _must_skip(self, **kwargs):
        """Skipped Record which are already imported."""
        if self.binder.to_internal(self.external_id):
            return _("Already imported")
        return super(WooStockPickingRefundImporter, self)._must_skip()

    def _get_remote_data(self, **kwargs):
        """Retrieve remote data related to an refunded order."""
        attributes = {}
        attributes["order_id"] = kwargs.get("order_id")
        data = self.backend_adapter.read(self.external_id, attributes=attributes)
        if not data.get(self.backend_adapter._woo_ext_id_key):
            data[self.backend_adapter._woo_ext_id_key] = self.external_id
        data["refund_order_status"] = kwargs["refund_order_status"]
        return data

    def _check_lot_tracking(self, product_id, delivery_order, return_id):
        """
        Check if lot tracking is consistent between the original delivery order and
        the return picking.
        """
        product = self.env["product.product"].browse(product_id)
        picking_id = self.env["stock.picking"].browse([return_id])
        if product.tracking == "lot":
            original_move = delivery_order.move_ids.filtered(
                lambda move: move.product_id.id == product_id
            )
            original_lots = original_move.mapped("move_line_ids.lot_id")
            return_lots = picking_id.move_ids.mapped("move_line_ids.lot_id")
            original_lots = set(original_lots)
            return_lots = set(return_lots)
            if not return_lots.issubset(original_lots):
                message = (
                    "Lot differs from original delivery order so please verify and "
                    "validate manually for product: %s." % (product.name)
                )
                _logger.info(message)
                user_id = self.backend_record.activity_user_id or delivery_order.user_id
                self.env["woo.backend"].create_activity(
                    record=picking_id,
                    message=message,
                    user=user_id,
                )
                return False
        return True

    def _find_original_moves(self, pickings, product_id, return_qty):
        """Find original moves associated with a product for return."""
        moves = pickings.move_ids.filtered(
            lambda move: move.product_id.id == product_id
        )
        to_return_moves = {}
        for move in moves:
            returned_qty = sum(
                move.returned_move_ids.filtered(
                    lambda r_move: r_move.product_id.id == product_id
                ).mapped("product_qty")
            )
            remaining_qty = move.product_qty - returned_qty
            if remaining_qty <= 0:
                continue
            if return_qty <= remaining_qty:
                to_return_moves[move] = return_qty
                break
            else:
                to_return_moves[move] = remaining_qty
                return_qty -= remaining_qty
        else:
            # Add this condition to handle cases where the price_unit at the sale order
            # line level is 0
            if not move.sale_line_id.price_unit:
                to_return_moves[move] = move.product_qty
        return to_return_moves

    def _update_return_line(self, return_line, quantity, move_external_id):
        """Update the return line."""
        return_line.update(
            {
                "quantity": quantity,
                "move_external_id": move_external_id,
            }
        )

    def _process_return_moves(self, to_return_moves, returns):
        """Process return moves and update return lines."""
        moves = [(6, 0, [])]
        for returned in returns:
            if not returned[-1] or "move_external_id" not in returned[-1]:
                continue
            new_return = deepcopy(returned)
            self._update_return_line(
                new_return[-1],
                new_return[-1]["quantity"],
                new_return[-1]["move_external_id"],
            )
            moves.append(new_return)
        return moves

    def _get_return_pickings(self, original_pickings):
        """Retrieve information about return pickings based on original pickings."""
        to_return_moves = {}
        all_return_move = []
        for line in self.remote_record.get("line_items", []):
            original_quantity = abs(line.get("quantity"))
            binder = self.binder_for(model="woo.product.product")
            product_id = binder.to_internal(line.get("product_id"), unwrap=True).id
            to_return_moves = self._find_original_moves(
                original_pickings, product_id, original_quantity
            )
            line_id = line.get("id")
            all_return_move.append(
                {
                    "move": to_return_moves,
                    "product_id": product_id,
                    "line_id": line_id,
                }
            )
        return all_return_move

    def _process_return_picking(self, picking_moves_dict):
        """Process return picking based on the provided picking moves dictionary."""
        delivery_order = next(iter(picking_moves_dict))
        return_wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=delivery_order.id, active_model="stock.picking")
            .new({})
        )
        self.env["stock.return.picking"].with_context(
            active_ids=delivery_order.ids,
            active_id=delivery_order.ids[0],
            active_model="stock.picking",
        )
        return_wizard._onchange_picking_id()
        for picking_move in picking_moves_dict[delivery_order]:
            return_line = return_wizard.product_return_moves.filtered(
                lambda r: r.product_id.id == picking_move.get("product_id")
            )
            self._update_return_line(
                return_line,
                picking_move.get("quantity"),
                picking_move.get("line_id"),
            )
        picking_returns = return_wizard._convert_to_write(
            {name: return_wizard[name] for name in return_wizard._cache}
        )
        picking_returns["product_return_moves"] = self._process_return_moves(
            picking_moves_dict, picking_returns["product_return_moves"]
        )
        picking_returns["return_reason"] = self.remote_record.get("reason")
        stock_return_picking = self.env["stock.return.picking"].create(picking_returns)
        return_id, return_type = stock_return_picking._create_returns()
        return picking_returns, return_id

    def _create(self, data, **kwargs):
        """Create a refund for the WooCommerce stock picking in Odoo."""
        binder = self.binder_for(model="woo.sale.order")
        sale_order = binder.to_internal(self.remote_record.get("order_id"), unwrap=True)
        if not sale_order:
            raise ValidationError(
                _(
                    "Sale order is missing for order_id: %s"
                    % self.remote_record.get("order_id")
                )
            )
        if not sale_order.picking_ids.filtered(lambda picking: picking.state == "done"):
            raise ValidationError(
                _(
                    "The delivery order has not been validated, therefore, we cannot "
                    "proceed with the creation of the return available."
                )
            )
        original_pickings = sale_order.picking_ids.filtered(
            lambda picking: picking.picking_type_id.code == "outgoing"
        )
        to_return_moves = self._get_return_pickings(original_pickings)
        return_picking_data = {}
        for to_return_move in to_return_moves:
            picking_id = None
            line_id_counter = {}
            for move, quantity in to_return_move["move"].items():
                picking_id = move.picking_id
                if picking_id not in return_picking_data:
                    return_picking_data[picking_id] = {
                        "product_moves": [],
                        "line_id_counter": line_id_counter,
                    }
                line_id_base = to_return_move["line_id"]
                if line_id_base not in line_id_counter:
                    line_id_counter[line_id_base] = 0
                line_id_counter[line_id_base] += 1
                line_id = f"{line_id_base}_{line_id_counter[line_id_base]}"
                return_picking_data[picking_id]["product_moves"].append(
                    {
                        "move": move,
                        "product_id": to_return_move["product_id"],
                        "quantity": quantity,
                        "line_id": line_id,
                    }
                )
        picking_moves = []
        for picking_id, value in return_picking_data.items():
            product_ids = list({move["product_id"] for move in value["product_moves"]})
            picking_data = {}
            picking_data[picking_id] = value["product_moves"]
            picking_data["product_ids"] = product_ids
            picking_moves.append(picking_data)
        picking_bindings = self.env["woo.stock.picking.refund"]
        for picking in picking_moves:
            (picking_returns, return_id,) = self._process_return_picking(
                picking,
            )
            data["odoo_id"] = return_id
            res = super(WooStockPickingRefundImporter, self)._create(data)
            picking_bindings |= res
            for product_id in picking.get("product_ids"):
                picking = next(iter(picking))
                self._check_lot_tracking(product_id, picking, return_id)
        return picking_bindings

    def _after_import(self, binding, **kwargs):
        """
        Inherit Method: inherit method to check if the refund order status is
        'refunded'. If so, it updates the corresponding sale order's status to
        'refunded' in the local system, if the delivered quantity of all order lines is
        not zero.
        """
        res = super(WooStockPickingRefundImporter, self)._after_import(
            binding, **kwargs
        )

        line_items = self.remote_record.get("line_items")
        product_line_mapping = {item["product_id"]: item["id"] for item in line_items}
        for bind in binding:
            for move in bind.odoo_id.move_ids:
                woo_product_id = move.product_id.woo_bind_ids.filtered(
                    lambda a: a.backend_id == self.backend_record
                )
                ext_id = int(woo_product_id.external_id)
                if (
                    move.quantity_done == move.product_uom_qty
                    and ext_id not in product_line_mapping
                ):
                    continue
                elif ext_id not in product_line_mapping:
                    raise ValidationError(
                        _("External ID not found of Product: %s" % move.product_id.name)
                    )
                move.external_move = product_line_mapping[ext_id]
                move.quantity_done = move.product_uom_qty
            if not self.backend_record.process_return_automatically:
                continue
            bind.odoo_id.button_validate()
        return res
