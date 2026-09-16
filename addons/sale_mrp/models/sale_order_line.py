from collections import defaultdict

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import OrderedSet, float_compare

_debug = DebugLog(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_display_qty_widget(self):
        super()._compute_display_qty_widget()
        lines = self.filtered(
            lambda line: line.product_id and line.product_id.is_storable
        )
        boms_per_line = lines._get_phantom_bom_per_line()

        for line in lines:
            if boms_per_line[line][1]:
                line.display_qty_widget = False
                continue

            if line.state == "draft" and line.product_type == "consu":
                components = line.product_id._get_components()
                if components and components != line.product_id:
                    line.display_qty_widget = True

    def _compute_qty_transferred(self):
        boms_per_line = self._get_kit_bom_per_line()
        super()._compute_qty_transferred()

        _debug.perf.count("kit_bom_lines", lines=len(self), kits=len(boms_per_line))
        for line, boms in boms_per_line.items():
            line.qty_transferred += line._get_kit_transferred_qty(*boms)

    def _get_phantom_bom_per_line(self, retry=False):
        products_per_company = defaultdict(OrderedSet)
        for line in self:
            products_per_company[line.company_id].add(line.product_id.id)
        found_per_company = {}

        def get_bom(line):
            company = line.company_id
            if company not in found_per_company:
                found_per_company[company] = self.env["mrp.bom"]._get_bom_by_product(
                    self.env["product.product"].browse(products_per_company[company]),
                    company_id=company.id,
                    bom_type="phantom",
                )
            return found_per_company[company].get(line.product_id, self.env["mrp.bom"])

        result = {}
        for line in self:
            if line.state == "draft":
                boms = get_bom(line)
            elif line.state == "done":
                boms = line.move_ids.filtered(
                    lambda move: move.state != "cancel"
                ).bom_line_id.bom_id
            else:
                boms = self.env["mrp.bom"]
            relevant_bom = boms.filtered(line._is_own_phantom_bom)
            if not relevant_bom and retry:
                relevant_bom = get_bom(line)
                _debug.logic("phantom_bom_retried", line=line, bom=relevant_bom)
            result[line] = (boms, relevant_bom)
        return result

    def _get_relevant_phantom_bom(self, retry=False):
        self.check_singleton()
        return self._get_phantom_bom_per_line(retry=retry)[self]

    def _is_own_phantom_bom(self, bom):
        self.check_singleton()
        return bom.type == "phantom" and (
            bom.product_id == self.product_id
            or (
                bom.product_tmpl_id == self.product_id.product_tmpl_id
                and not bom.product_id
            )
        )

    def _get_kit_bom_per_line(self):
        from_stock = self.filtered(
            lambda line: line.qty_transferred_method == "stock_move"
        )
        from_stock.fetch(["move_ids"])
        candidates = from_stock.filtered("move_ids")
        return {
            line: boms
            for line, boms in candidates._get_phantom_bom_per_line(retry=True).items()
            if any(boms)
        }

    def _get_kit_transferred_qty(self, boms, kit_bom):
        self.check_singleton()
        if any(move._is_dropshipped() for move in self.move_ids):
            _debug.logic("kit_qty", line=self, by="dropship")
            return self._get_dropshipped_kit_qty()

        if not kit_bom:
            moves = self._get_kit_moves(include_cancelled=True)
            delivered = bool(moves) and all(
                move.state == "done" and move.location_dest_id.usage == "customer"
                for move in moves
            )
            _debug.logic("kit_qty", line=self, by="no_bom", delivered=delivered)
            return self.product_qty if delivered else 0.0

        moves = self._get_kit_moves().filtered(
            lambda move: (
                move.state == "done" and move.location_dest_usage != "inventory"
            )
        )
        order_qty = self.product_uom_id._get_quantity_reconcile(
            self.product_qty, kit_bom.product_uom_id
        )
        qty_transferred = moves._get_kit_quantity(
            self.product_id, order_qty, kit_bom, self._get_kit_delivery_moves_filter()
        )
        _debug.logic(
            "kit_qty", line=self, by="bom_components", bom=kit_bom, qty=qty_transferred
        )
        return kit_bom.product_uom_id._get_quantity_reconcile(
            qty_transferred, self.product_uom_id
        )

    def _get_dropshipped_kit_qty(self):
        self.check_singleton()
        moves = self._get_kit_moves()
        if not moves:
            return 0.0
        for move in moves:
            if move.location_dest_id.usage == "customer":
                if move.state != "done":
                    return 0.0
                continue
            returned_qty = sum(
                returned.product_uom_id._get_quantity_reconcile(
                    returned.quantity, move.product_uom_id
                )
                for returned in move.returned_move_ids
                if returned.state == "done"
            )
            if (
                move.state == "done"
                and float_compare(
                    move.quantity,
                    returned_qty,
                    precision_rounding=move.product_uom_id.rounding,
                )
                > 0
            ):
                return 0.0
        return self.product_qty

    def _get_kit_moves(self, include_cancelled=False):
        self.check_singleton()
        moves = self.move_ids
        if not include_cancelled:
            moves = moves.filtered(lambda move: move.state != "cancel")
        accrual_date = self.env.context.get("accrual_entry_date")
        if not accrual_date:
            return moves
        accrual_date = fields.Date.from_string(accrual_date)
        return moves.filtered(
            lambda move: fields.Date.context_today(move, move.date) <= accrual_date
        )

    def _get_kit_delivery_moves_filter(self):
        return {
            "incoming_moves": lambda m: (
                m._is_outgoing() and (not m.origin_returned_move_id or m.to_refund)
            ),
            "outgoing_moves": lambda m: m._is_incoming() and m.to_refund,
        }

    def _prepare_qty_transferred(self):
        delivered_qties = super()._prepare_qty_transferred()
        for line, boms in self._get_kit_bom_per_line().items():
            delivered_qties[line] += line._get_kit_transferred_qty(*boms)
        return delivered_qties

    def compute_uom_qty(self, new_qty, stock_move, rounding=True):
        bom_line = stock_move.bom_line_id
        if not bom_line:
            return super().compute_uom_qty(new_qty, stock_move, rounding)
        kit_qty = self.product_uom_id._get_quantity_in_unit(
            new_qty, bom_line.bom_id.product_uom_id, rounding
        )
        component_qty = kit_qty * bom_line.product_qty / bom_line.bom_id.product_qty
        return bom_line.product_uom_id._get_quantity_in_unit(
            component_qty, stock_move.product_uom_id, rounding
        )

    @api.model
    def _get_incoming_outgoing_moves_filter(self):
        sorted_moves = self.move_ids.sorted("id")
        triggering_rule_ids = []
        seen_wh_ids = set()
        seen_bom_id = set()
        for move in sorted_moves:
            if move.bom_line_id.bom_id.id in seen_bom_id:
                triggering_rule_ids.append(move.rule_id.id)
            elif move.warehouse_id.id not in seen_wh_ids:
                triggering_rule_ids.append(move.rule_id.id)
                seen_wh_ids.add(move.warehouse_id.id)
                if move.bom_line_id and move.bom_line_id.bom_id.type == "phantom":
                    seen_bom_id.add(move.bom_line_id.bom_id.id)

        return {
            "incoming_moves": lambda m: (
                m.state != "cancel"
                and m.location_dest_usage != "inventory"
                and m.rule_id.id in triggering_rule_ids
                and m.location_final_id.usage == "customer"
                and (
                    not m.origin_returned_move_id
                    or (m.origin_returned_move_id and m.to_refund)
                )
            ),
            "outgoing_moves": lambda m: (
                m.state != "cancel"
                and m.location_dest_usage != "inventory"
                and m.location_id.usage == "customer"
                and m.to_refund
            ),
        }

    def _get_procurement_qty(self, previous_product_qty=False):
        self.check_singleton()
        bom = (
            self.env["mrp.bom"]
            .sudo()
            ._get_bom_by_product(
                self.product_id, bom_type="phantom", company_id=self.company_id.id
            )[self.product_id]
        )
        if bom and self.move_ids:
            _debug.logic("procurement_qty", line=self, by="kit_bom", bom=bom)
            moves = self.move_ids.filtered(
                lambda r: r.state != "cancel" and r.location_dest_usage != "inventory"
            )
            filters = self._get_incoming_outgoing_moves_filter()
            order_qty = (
                previous_product_qty.get(self.id, 0)
                if previous_product_qty
                else self.product_qty
            )
            order_qty = self.product_uom_id._get_quantity_in_unit(
                order_qty, bom.product_uom_id
            )
            qty = moves._get_kit_quantity(self.product_id, order_qty, bom, filters)
            return bom.product_uom_id._get_quantity_in_unit(qty, self.product_uom_id)
        elif bom and previous_product_qty:
            return previous_product_qty.get(self.id)
        return super()._get_procurement_qty(previous_product_qty=previous_product_qty)
