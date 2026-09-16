import itertools
import logging
from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import OrderedSet
from odoo.tools.translate import _

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)


class StockMoveForecast(models.Model):
    _inherit = "stock.move"

    @api.depends(
        "product_id",
        "product_qty",
        "picking_type_id",
        "quantity",
        "priority",
        "state",
        "product_uom_qty",
        "location_id",
    )
    @dbg.timed
    def _compute_forecast_information(self):
        self.forecast_availability = False
        self.date_planned_forecast = False

        self.product_id.fetch(["type", "uom_id"])

        not_product_moves = self.filtered(lambda move: not move.product_id.is_storable)
        for move in not_product_moves:
            move.forecast_availability = move.product_qty

        product_moves = self - not_product_moves
        now = fields.Datetime.now()
        virtual_available_dict = product_moves._get_forecast_virtual_available(now)

        def get_virtual_qty(key, product_id, idx):
            entry = virtual_available_dict.get(key, {}).get(product_id)
            return entry[idx] if entry else 0.0

        outgoing_unreserved_moves_per_warehouse = defaultdict(set)
        for move in product_moves:
            if move.state == "assigned":
                move.forecast_availability = move.product_uom_id._get_quantity_in_unit(
                    move.quantity,
                    move.product_id.uom_id,
                    rounding_method="HALF-UP",
                )
                continue
            key = move._get_forecast_virtual_key(now)
            qty_free = get_virtual_qty(key, move.product_id.id, 1)
            if (
                move.state == "draft"
                and move._is_consuming()
                and move.product_id.uom_id.compare(qty_free, move.product_qty) >= 0
            ):
                move.forecast_availability = qty_free
                continue
            if move._is_consuming():
                if move.state == "draft":
                    virtual_available = get_virtual_qty(key, move.product_id.id, 0)
                    if (
                        move.product_id.uom_id.compare(
                            virtual_available, move.product_qty
                        )
                        >= 0
                    ):
                        move.forecast_availability = virtual_available
                        continue
                    move.forecast_availability = virtual_available - move.product_qty
                elif move.state in ("waiting", "confirmed", "partially_available"):
                    outgoing_unreserved_moves_per_warehouse[
                        move.location_id.warehouse_id
                    ].add(move.id)
            elif move.picking_type_id.code == "incoming":
                forecast_availability = get_virtual_qty(key, move.product_id.id, 0)
                if move.state == "draft":
                    forecast_availability += move.product_qty
                move.forecast_availability = forecast_availability

        dbg.logic.debug(
            "_compute_forecast_information: %d moves, %d storable, outgoing per warehouse %s",
            len(self),
            len(product_moves),
            {
                wh.id: len(ids)
                for wh, ids in outgoing_unreserved_moves_per_warehouse.items()
            },
        )
        self._update_forecast_availability_outgoing(
            outgoing_unreserved_moves_per_warehouse
        )

    def _get_forecast_warehouse_date_key(self, now, incoming=False):
        warehouse_id = (
            self.location_dest_id.warehouse_id.id
            if incoming
            else self.location_id.warehouse_id.id
        )
        return warehouse_id, max(self.date or now, now)

    def _get_forecast_virtual_key(self, now):
        self.check_singleton()
        if self.state == "assigned":
            return None
        if self._is_consuming():
            if self.state != "draft":
                return None
            return self._get_forecast_warehouse_date_key(now)
        if self.picking_type_id.code == "incoming":
            return self._get_forecast_warehouse_date_key(now, incoming=True)
        return None

    def _get_forecast_virtual_available(self, now):
        prefetch_virtual_available = defaultdict(set)
        for move in self:
            if (key := move._get_forecast_virtual_key(now)) is not None:
                prefetch_virtual_available[key].add(move.product_id.id)
        virtual_available_dict = {}
        for key_context, product_ids in prefetch_virtual_available.items():
            read_res = (
                self.env["product.product"]
                .browse(product_ids)
                .with_context(warehouse_id=key_context[0], to_date=key_context[1])
                .read(
                    [
                        "qty_available_virtual",
                        "qty_free",
                    ],
                )
            )
            virtual_available_dict[key_context] = {
                res["id"]: (res["qty_available_virtual"], res["qty_free"])
                for res in read_res
            }
        dbg.performance.debug(
            "_get_forecast_virtual_available: %d (warehouse, date) contexts read",
            len(prefetch_virtual_available),
        )
        return virtual_available_dict

    def _update_forecast_availability_outgoing(
        self, outgoing_unreserved_moves_per_warehouse
    ):
        for warehouse, moves_ids in outgoing_unreserved_moves_per_warehouse.items():
            if not warehouse:
                continue
            moves_per_location = self.browse(moves_ids).grouped("location_id")
            for location, mvs in moves_per_location.items():
                forecast_info = mvs._get_forecast_availability_outgoing(
                    warehouse,
                    location,
                )
                for move in mvs:
                    move.forecast_availability, move.date_planned_forecast = (
                        forecast_info[move]
                    )

    @dbg.timed
    def _get_forecast_availability_outgoing(self, warehouse, location_id=False):
        wh_location_query = self.env["stock.location"]._search(
            [("id", "child_of", warehouse.view_location_id.id)],
        )
        forecast_lines = self.env["stock.forecasted_product_product"]._get_report_lines(
            False,
            self.product_id.ids,
            wh_location_query,
            location_id or warehouse.lot_stock_id,
            read=False,
        )
        result = defaultdict(lambda: (0.0, False))
        for line in forecast_lines:
            move_out = line.get("move_out")
            if not move_out or not line["quantity"]:
                continue
            move_in = line.get("move_in")
            qty_expected = (
                line["quantity"] + result[move_out][0]
                if line["replenishment_filled"]
                else -line["quantity"]
            )
            date_expected = False
            if move_in:
                date_expected = (
                    max(move_in.date, result[move_out][1])
                    if result[move_out][1]
                    else move_in.date
                )
            result[move_out] = (qty_expected, date_expected)

        dbg.logic.debug(
            "_get_forecast_availability_outgoing warehouse=%s: %d report lines, %d moves resolved",
            warehouse.id,
            len(forecast_lines),
            len(result),
        )
        return result

    @api.depends("move_orig_ids.date", "move_orig_ids.state", "state", "date")
    def _compute_date_delay_alert(self):
        for move in self:
            if move.state in ("done", "cancel"):
                move.date_delay_alert = False
                continue
            prev_moves = move.move_orig_ids.filtered(
                lambda m: m.state not in ("done", "cancel") and m.date,
            )
            prev_max_date = max(prev_moves.mapped("date"), default=False)
            if prev_max_date and prev_max_date > move.date:
                move.date_delay_alert = prev_max_date
            else:
                move.date_delay_alert = False

    def _get_delay_alert_documents(self):
        return list(self.mapped("picking_id"))

    def _filtered_availability_relevant(self):
        return self.filtered(lambda move: move.state not in ("cancel", "done"))

    def _is_availability_short(self):
        return any(
            move.product_id
            and move.product_id.uom_id.compare(
                move.forecast_availability,
                0 if move.state == "draft" else move.product_qty,
            )
            == -1
            for move in self._filtered_availability_relevant()
        )

    def _get_availability(self, comparison_date):
        if not self:
            return "available", False
        if self._is_availability_short():
            return "late", False
        forecast_date = max(
            self._filtered_availability_relevant()
            .filtered("date_planned_forecast")
            .mapped("date_planned_forecast"),
            default=False,
        )
        if not forecast_date:
            return "available", False
        state = (
            "late"
            if comparison_date and comparison_date < forecast_date
            else "expected"
        )
        return state, forecast_date

    def _get_availability_state(self, comparison_date):
        return self._get_availability(comparison_date)[0]

    def _is_availability_matching_search(self, operator, value, comparison_date):
        if not value:
            raise UserError(_("Search not supported without a value."))
        if operator not in ("=", "!=", "in", "not in"):
            raise UserError(_("Operation not supported"))
        values = set(value) if isinstance(value, (list, tuple, set)) else {value}
        matched = self._get_availability_state(comparison_date) in values
        return matched == (operator in ("=", "in"))

    def _get_upstream_documents_and_responsibles(self, visited):
        walk = self.env.context.get("_upstream_walk")
        if walk is not None:
            return self._walk_upstream_documents(walk)
        walk = {"seen": set(), "visited": visited}
        documents = self._walk_upstream_documents(walk)
        return {
            (document, responsible, walk["visited"])
            for document, responsible, __ in documents
        }

    def _walk_upstream_documents(self, walk):
        if self.id in walk["seen"]:
            return set()
        walk["seen"].add(self.id)
        depth = self.env.context.get("_upstream_depth", 0)
        if depth >= self._MAX_UPSTREAM_DEPTH:
            _logger.warning(
                "stopped looking for upstream documents of move %s after %s moves; "
                "responsibles further up the chain will not be notified",
                self.id,
                depth,
            )
            return set()
        if self in walk["visited"]:
            return set()
        live_origins = self.move_orig_ids.filtered(
            lambda m: m.state not in ("done", "cancel"),
        )
        if not live_origins:
            return set()
        dbg.logic.debug(
            "[move:%s] _walk_upstream_documents depth %d -> %s",
            self.id,
            depth,
            dbg.rec(live_origins),
        )
        walk["visited"] |= self
        return set(
            itertools.chain.from_iterable(
                move._get_upstream_documents_and_responsibles(walk["visited"])
                for move in live_origins.with_context(
                    _upstream_walk=walk,
                    _upstream_depth=depth + 1,
                )
            ),
        )

    @api.depends("picking_type_id", "date", "priority", "state")
    def _compute_date_reservation(self):
        for move in self:
            if move.picking_type_id.reservation_method == "by_date" and move.state in [
                "draft",
                "confirmed",
                "waiting",
                "partially_available",
            ]:
                move.date_reservation = move._get_date_reservation()
            elif move.picking_type_id.reservation_method == "manual":
                move.date_reservation = False
            else:
                move.date_reservation = move.date_reservation

    def _get_date_reservation(self, common_days=None, priority_days=None):
        self.check_singleton()
        picking_type = self.picking_type_id
        if common_days is None:
            common_days = picking_type.reservation_days_before
        if priority_days is None:
            priority_days = picking_type.reservation_days_before_priority
        days = priority_days if self.priority == "1" else common_days
        return fields.Date.to_date(self.date) - timedelta(days=days)

    def _update_date_reservation_from_days(self, common_days, priority_days):
        for move in self:
            move.date_reservation = move._get_date_reservation(
                common_days, priority_days
            )

    def _update_date_deadline(self, new_deadline):
        visited = self.env.context.get("date_deadline_propagate_ids")
        if visited is None:
            visited = set()
        self._propagate_date_deadline(new_deadline, visited)

    def _propagate_date_deadline(self, new_deadline, visited):
        deadlines = self._plan_date_deadline(new_deadline, visited)
        if not deadlines:
            return
        dbg.pipeline.debug(
            "_propagate_date_deadline from %s to %s: %d chained moves",
            dbg.rec(self),
            new_deadline,
            len(deadlines),
        )
        by_value = defaultdict(OrderedSet)
        for move_id, value in deadlines.items():
            by_value[value].add(move_id)
        for value, move_ids in by_value.items():
            self.browse(move_ids).with_context(
                date_deadline_propagate_ids=visited,
            ).date_deadline = value

    def _plan_date_deadline(self, new_deadline, visited):
        planned = {}
        frontier = [(self, fields.Datetime.to_datetime(new_deadline))]
        while frontier:
            next_frontier = defaultdict(OrderedSet)
            for moves, deadline_dt in frontier:
                visited.update(moves.ids)
                for move in moves:
                    if move.date_deadline and deadline_dt:
                        delta = move.date_deadline - deadline_dt
                    else:
                        delta = 0
                    for other in move.move_dest_ids | move.move_orig_ids:
                        if other.state in ("done", "cancel") or other.id in visited:
                            continue
                        if other.date_deadline and delta:
                            value = other.date_deadline - delta
                        elif (
                            not other.date_deadline
                            or other.date_deadline != deadline_dt
                        ):
                            value = deadline_dt
                        else:
                            continue
                        planned[other.id] = value
                        next_frontier[value].add(other.id)
            for move_ids in next_frontier.values():
                visited.update(move_ids)
            frontier = [
                (self.browse(move_ids), value)
                for value, move_ids in next_frontier.items()
            ]
        return planned

    def _get_mto_procurement_date(self):
        return self.date
