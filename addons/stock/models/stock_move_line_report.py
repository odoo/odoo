from collections import defaultdict

from odoo import models

from ..tools import debug_log as dbg


class StockMoveLineReport(models.Model):
    _inherit = "stock.move.line"

    def _get_aggregated_properties(self, move_line=False, move=False):
        move = move or move_line.move_id
        uom = move.product_uom_id or move_line.product_uom_id
        packaging_uom = move.packaging_uom_id
        name = move.product_id.display_name
        description = move.description_picking or ""
        product = move.product_id
        if description.startswith(name):
            description = description.removeprefix(name).strip()
        elif description.startswith(product.name):
            description = description.removeprefix(product.name).strip()
        line_key = f"{product.id}_{product.display_name}_{description or ''}_{uom.id}_{packaging_uom.id}"
        properties = {
            "line_key": line_key,
            "name": name,
            "description": description,
            "product_uom_id": uom,
            "packaging_uom_id": packaging_uom,
            "move": move,
        }
        if move_line and move_line.result_package_id:
            properties["package"] = move_line.result_package_id
            properties["package_history"] = move_line.package_history_id
            properties["line_key"] += f"_{move_line.result_package_id.id}"
        return properties

    @dbg.timed
    def _get_aggregated_product_quantities(
        self, *, strict=False, except_package=False, **kwargs
    ):
        aggregated_move_lines = {}
        backorders = self._get_backorders()
        dbg.logic.debug(
            "_get_aggregated_product_quantities on %s strict=%s except_package=%s "
            "backorders %s",
            dbg.rec(self),
            strict,
            except_package,
            dbg.rec(backorders),
        )
        base_key_by_move = {}

        def get_line_key(move):
            key = base_key_by_move.get(move.id)
            if key is None:
                key = base_key_by_move[move.id] = self._get_aggregated_properties(
                    move=move
                )["line_key"]
            return key

        agg_keys_by_base = defaultdict(list)
        undelivered_key = {}
        backorder_lines_by_base = defaultdict(lambda: self.env["stock.move.line"])
        for bo_line in backorders.move_line_ids:
            backorder_lines_by_base[get_line_key(bo_line.move_id)] |= bo_line

        for move_line in self:
            if except_package and move_line.result_package_id:
                continue
            aggregated_properties = self._get_aggregated_properties(move_line=move_line)
            line_key, uom = (
                aggregated_properties["line_key"],
                aggregated_properties["product_uom_id"],
            )
            quantity = move_line.product_uom_id._get_quantity_in_unit(
                move_line.quantity, uom
            )
            packaging_quantity = uom._get_quantity_in_unit(
                quantity, move_line.move_id.packaging_uom_id
            )
            undelivered_key.setdefault(move_line.move_id, line_key)
            if line_key not in aggregated_move_lines:
                agg_keys_by_base[get_line_key(move_line.move_id)].append(line_key)
                aggregated_move_lines[line_key] = {
                    **aggregated_properties,
                    "quantity": quantity,
                    "packaging_quantity": packaging_quantity,
                    "qty_ordered": quantity,
                    "packaging_qty_ordered": packaging_quantity,
                    "product": move_line.product_id,
                }
            else:
                aggregated_move_lines[line_key]["qty_ordered"] += quantity
                aggregated_move_lines[line_key]["packaging_qty_ordered"] += (
                    packaging_quantity
                )
                aggregated_move_lines[line_key]["quantity"] += quantity
                aggregated_move_lines[line_key]["packaging_quantity"] += (
                    packaging_quantity
                )

        if strict:
            return aggregated_move_lines
        self._add_undelivered_quantities(
            aggregated_move_lines,
            undelivered_key,
            backorder_lines_by_base,
            get_line_key,
        )
        self._aggregate_empty_moves(
            aggregated_move_lines, agg_keys_by_base, self.picking_id | backorders
        )
        dbg.logic.debug(
            "_get_aggregated_product_quantities -> %d aggregated keys",
            len(aggregated_move_lines),
        )
        return aggregated_move_lines

    def _add_undelivered_quantities(
        self,
        aggregated_move_lines,
        undelivered_key,
        backorder_lines_by_base,
        get_line_key,
    ):
        for move, line_key in undelivered_key.items():
            entry = aggregated_move_lines[line_key]
            uom = entry["product_uom_id"]
            backorder_lines = backorder_lines_by_base.get(
                get_line_key(move), self.env["stock.move.line"]
            )
            undelivered = move.product_uom_qty + sum(
                backorder_lines.move_id.mapped("product_uom_qty")
            )
            undelivered -= sum(
                line.product_uom_id._get_quantity_in_unit(line.quantity, uom)
                for line in move.move_line_ids
            )
            if uom.is_zero(undelivered):
                continue
            dbg.logic.debug(
                "[move:%s] undelivered %s added to ordered qty", move.id, undelivered
            )
            entry["qty_ordered"] += undelivered
            entry["packaging_qty_ordered"] += uom._get_quantity_in_unit(
                undelivered, move.packaging_uom_id
            )

    def _get_backorders(self):
        backorders = self.env["stock.picking"]
        pickings = self.picking_id
        while unvisited := pickings.backorder_ids - backorders - self.picking_id:
            backorders |= unvisited
            pickings = unvisited
        return backorders

    def _aggregate_empty_moves(self, aggregated_move_lines, agg_keys_by_base, pickings):
        for empty_move in pickings.move_ids:
            to_bypass = False
            if not (
                empty_move.product_uom_qty
                and empty_move.product_uom_id.is_zero(empty_move.quantity)
            ):
                continue
            if empty_move.state != "cancel":
                if empty_move.state != "confirmed" or empty_move.move_line_ids:
                    continue
                to_bypass = True
            aggregated_properties = self._get_aggregated_properties(move=empty_move)
            line_key = aggregated_properties["line_key"]

            matching_keys = agg_keys_by_base.get(line_key, ())
            if not matching_keys and not to_bypass:
                agg_keys_by_base.setdefault(line_key, []).append(line_key)
                aggregated_move_lines[line_key] = {
                    **aggregated_properties,
                    "quantity": False,
                    "packaging_quantity": 0,
                    "packaging_qty_ordered": 0,
                    "qty_ordered": empty_move.product_uom_qty,
                    "product": empty_move.product_id,
                }
            elif line_key in aggregated_move_lines:
                aggregated_move_lines[line_key]["qty_ordered"] += (
                    empty_move.product_uom_qty
                )
            elif matching_keys:
                aggregated_move_lines[matching_keys[0]]["qty_ordered"] += (
                    empty_move.product_uom_qty
                )

    def _compute_sale_price(self):
        pass

    def _is_lot_display_in_invoice_required(self):
        self.check_singleton()
        return False
