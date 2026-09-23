import json
from collections import defaultdict

from odoo import api, models
from odoo.fields import Domain
from odoo.tools import format_date, format_datetime

from ..tools import debug_log as dbg
from .stock_picking import (
    DONE_CANCEL_STATES,
    FORECAST_PICKING_CODES,
    OPEN_PICKING_STATES,
    UNRESERVED_MOVE_STATES,
)


class StockPickingAvailability(models.Model):
    _inherit = "stock.picking"

    @api.depends(
        "state",
        "move_ids.state",
        "move_ids.picked",
        "move_ids.quantity",
        "move_ids.product_uom_qty",
    )
    def _compute_show_check_availability(self):
        for picking in self:
            if picking.state not in OPEN_PICKING_STATES:
                picking.show_check_availability = False
                continue
            if all(
                m.picked or m.product_uom_id.compare(m.product_uom_qty, m.quantity) == 0
                for m in picking.move_ids
            ):
                picking.show_check_availability = False
                continue
            picking.show_check_availability = any(
                move.state in UNRESERVED_MOVE_STATES
                and move.product_uom_id.compare(move.product_uom_qty, 0) > 0
                for move in picking.move_ids
            )

    @api.depends("state", "move_ids", "picking_type_id")
    @api.depends_context("uid")
    def _compute_show_allocation(self):
        self.show_allocation = False
        if not self.env.user.has_group("stock.group_reception_report"):
            return
        show_by_picking = self._get_show_allocation_map()
        for picking in self:
            picking.show_allocation = show_by_picking.get(picking, False)

    def _get_allocatable_demand_lines(self):
        lines_by_picking = {}
        for picking in self:
            if (
                not picking.picking_type_id
                or picking.picking_type_id.code == "outgoing"
            ):
                continue
            lines = picking.move_ids.filtered(
                lambda m: m.product_id.is_storable and m.state != "cancel",
            )
            if lines:
                lines_by_picking[picking] = lines
        return lines_by_picking

    def _has_allocatable_demand(self, lines, excluded_ids, candidates_by_product):
        self.check_singleton()
        line_ids = set(lines.ids)
        return any(
            move.picking_id.id not in excluded_ids
            and (
                not move.move_orig_ids
                or not line_ids.isdisjoint(move.move_orig_ids.ids)
            )
            for product_id in set(lines.product_id.ids)
            for move in candidates_by_product.get(product_id, ())
        )

    def _get_allocatable_demand_candidates(
        self, view_location, include_assigned, lines
    ):
        Move = self.env["stock.move"]
        candidates = Move.search(
            Move._get_domain_allocatable_demand(
                self.env["stock.location"]._get_allocation_source_ids(
                    view_location.ids,
                ),
                lines.product_id.ids,
                include_assigned=include_assigned,
            ),
        )
        candidates_by_product = defaultdict(list)
        for move in candidates:
            candidates_by_product[move.product_id.id].append(move)
        return candidates_by_product

    @dbg.timed
    def _get_show_allocation_map(self, excluded_pickings=None, stop_at_first=False):
        result = dict.fromkeys(self, False)
        base_excluded_ids = set(excluded_pickings.ids) if excluded_pickings else set()
        lines_by_picking = self._get_allocatable_demand_lines()
        batches = defaultdict(dict)
        for picking, lines in lines_by_picking.items():
            key = (
                picking.picking_type_id.warehouse_id.view_location_id,
                picking.state == "done",
            )
            batches[key][picking] = lines
        for (view_location, include_assigned), members in batches.items():
            candidates_by_product = self._get_allocatable_demand_candidates(
                view_location,
                include_assigned,
                self.env["stock.move"].union(*members.values()),
            )
            if not candidates_by_product:
                continue
            dbg.logic.debug(
                "_get_show_allocation_map: view %s include_assigned=%s, %d pickings, "
                "%d products with candidates",
                view_location.id,
                include_assigned,
                len(members),
                len(candidates_by_product),
            )
            for picking, lines in members.items():
                excluded_ids = base_excluded_ids | {picking._origin.id}
                excluded_ids.discard(False)
                result[picking] = picking._has_allocatable_demand(
                    lines,
                    excluded_ids,
                    candidates_by_product,
                )
                if stop_at_first and result[picking]:
                    return result
        return result

    def _is_allocation_shown(self, picking_type_id):
        if not picking_type_id or picking_type_id.code == "outgoing":
            return False
        return any(
            self._get_show_allocation_map(
                excluded_pickings=self,
                stop_at_first=True,
            ).values(),
        )

    @api.depends(
        "state",
        "picking_type_code",
        "date_planned",
        "move_ids",
        "move_ids.forecast_availability",
        "move_ids.date_planned_forecast",
    )
    @dbg.timed
    @api.depends_context("lang")
    def _compute_availability_status(self):
        pickings = self.filtered(
            lambda picking: (
                picking.state in OPEN_PICKING_STATES
                and picking.picking_type_code in FORECAST_PICKING_CODES
            ),
        )
        pickings.products_availability_state = "available"
        pickings.products_availability = self.env._("Available")
        other_pickings = self - pickings
        other_pickings.products_availability = False
        other_pickings.products_availability_state = False

        all_moves = pickings.move_ids
        all_moves._fields["forecast_availability"].compute_value(all_moves)
        for picking in pickings:
            state, forecast_date = picking.move_ids._get_availability(
                picking.date_planned,
            )
            dbg.logic.debug(
                "[picking:%s] availability %s, forecast date %s",
                picking.id,
                state,
                forecast_date,
            )
            picking.products_availability_state = state
            if forecast_date:
                picking.products_availability = self.env._(
                    "Exp %s",
                    format_date(self.env, forecast_date),
                )
            elif state == "late":
                picking.products_availability = self.env._("Not Available")

    def _search_products_availability_state(self, operator, value):
        if operator != "in":
            return NotImplemented

        value = set(value)
        qualifying = Domain(
            [
                ("state", "in", tuple(OPEN_PICKING_STATES)),
                ("picking_type_id.code", "in", tuple(FORECAST_PICKING_CODES)),
            ],
        )
        if False in value:
            return ~qualifying | self._search_products_availability_state(
                "in",
                value - {False},
            )
        all_states = set(
            self._fields["products_availability_state"].get_values(self.env)
        )
        value = all_states & value
        if not value:
            return Domain.FALSE
        if value == all_states:
            return qualifying

        deciding_moves = self.env["stock.move"].search(
            Domain("picking_id", "any", qualifying)
            & Domain(self._get_domain_availability_deciding_moves()),
        )
        deciding_moves._fields["forecast_availability"].compute_value(deciding_moves)
        matched = self.browse()
        for picking, moves in deciding_moves.grouped("picking_id").items():
            if moves._is_availability_matching_search(
                operator,
                value,
                picking.date_planned,
            ):
                matched |= picking
        if "available" not in value:
            return Domain("id", "in", matched.ids)
        return Domain("id", "in", matched.ids) | (
            qualifying & ~Domain("id", "in", deciding_moves.picking_id.ids)
        )

    @api.model
    def _get_domain_availability_deciding_moves(self):
        return [
            ("state", "not in", tuple(DONE_CANCEL_STATES)),
            ("product_id.is_storable", "=", True),
        ]

    @api.depends("state", "date_delay_alert", "move_ids.date_delay_alert")
    @api.depends_context("lang", "tz")
    def _compute_json_popover(self):
        picking_no_alert = self.filtered(
            lambda p: p.state in DONE_CANCEL_STATES or not p.date_delay_alert,
        )
        picking_no_alert.json_popover = False
        for picking in self - picking_no_alert:
            picking.json_popover = json.dumps(
                {
                    "popoverTemplate": "stock.PopoverStockRescheduling",
                    "date_delay_alert": format_datetime(
                        self.env,
                        picking.date_delay_alert,
                        dt_format=False,
                    ),
                    "late_elements": [
                        {
                            "id": late_move.id,
                            "name": late_move.display_name,
                            "model": late_move._name,
                        }
                        for late_move in picking.move_ids.filtered(
                            lambda m: m.date_delay_alert,
                        ).move_orig_ids._get_delay_alert_documents()
                    ],
                },
            )

    @api.depends("move_ids.date_delay_alert")
    def _compute_date_delay_alert(self):
        saved = self.filtered("id")
        date_delay_alert_by_picking = {}
        if saved:
            date_delay_alert_by_picking = {
                picking.id: date_delay_alert
                for picking, date_delay_alert in self.env["stock.move"]._read_group(
                    [
                        ("picking_id", "in", saved.ids),
                        ("date_delay_alert", "!=", False),
                    ],
                    ["picking_id"],
                    ["date_delay_alert:max"],
                )
            }
        for picking in self:
            if picking.id:
                picking.date_delay_alert = date_delay_alert_by_picking.get(
                    picking.id, False
                )
            else:
                picking.date_delay_alert = max(
                    picking.move_ids.filtered("date_delay_alert").mapped(
                        "date_delay_alert"
                    ),
                    default=False,
                )

    @api.depends("date_deadline", "date_planned")
    def _compute_has_deadline_issue(self):
        for picking in self:
            picking.has_deadline_issue = bool(
                picking.date_deadline
                and picking.date_planned
                and picking.date_deadline < picking.date_planned
            )

    @api.depends("move_ids.move_dest_ids")
    def _compute_show_next_pickings(self):
        for picking in self:
            next_pickings = picking.move_ids.move_dest_ids.picking_id
            picking.show_next_pickings = bool(next_pickings - picking.return_ids)
