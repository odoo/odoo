import logging
from ast import literal_eval
from collections import defaultdict

from odoo import api, models
from odoo.exceptions import UserError
from odoo.fields import Command, Domain
from odoo.tools import OrderedSet
from odoo.tools.translate import _

from ..tools import debug_log as dbg
from .stock_orderpoint import ORDERPOINTS_BY_SCOPE

_logger = logging.getLogger(__name__)


class StockMoveProcurement(models.Model):
    _inherit = "stock.move"

    @dbg.timed
    def _run_procurements(self, consumed_from_stock_dict):
        quantities = self.with_context(
            consumed_from_stock_dict=consumed_from_stock_dict,
        )._prepare_procurement_qty()
        dbg.pipeline.debug(
            "_run_procurements: %s -> quantities %s", dbg.rec(self), quantities[:8]
        )
        procurement_requests = [
            self.env["stock.rule"].Procurement(
                move.product_id,
                quantity,
                move.product_uom_id,
                move.location_id,
                (move.rule_id and move.rule_id.name) or "/",
                move._prepare_procurement_origin(),
                move.company_id,
                move._prepare_procurement_vals(),
            )
            for move, quantity in zip(self, quantities, strict=True)
        ]
        self.env["stock.rule"].with_context(
            consumed_from_stock_dict=consumed_from_stock_dict,
        ).run(
            procurement_requests,
            raise_user_error=not self.env.context.get("from_orderpoint"),
        )

    def _reverse_negative_demand(self):
        neg_r_moves = self.filtered(
            lambda move: move.product_uom_id.compare(move.product_uom_qty, 0) < 0,
        )
        if not neg_r_moves:
            return self.browse()
        neg_to_push = neg_r_moves.filtered(
            lambda move: (
                move.location_final_id
                and move.location_dest_id != move.location_final_id
            ),
        )
        dbg.logic.debug(
            "_reverse_negative_demand: negative %s, to push %s",
            dbg.rec(neg_r_moves),
            dbg.rec(neg_to_push),
        )
        new_push_moves = self.browse()
        if neg_to_push:
            new_push_moves = neg_to_push._push_apply()
        neg_r_moves._reverse_negative_moves()
        return new_push_moves

    def _confirm_pushed_moves(self):
        if not self:
            return
        neg_push_moves = self.filtered(
            lambda sm: sm.product_uom_id.compare(sm.product_uom_qty, 0) < 0,
        )
        dbg.pipeline.debug(
            "_confirm_pushed_moves: %s (negative %s)",
            dbg.rec(self),
            dbg.rec(neg_push_moves),
        )
        (self - neg_push_moves).sudo()._action_confirm()
        neg_push_moves._action_confirm(
            merge_into=neg_push_moves.move_orig_ids.move_dest_ids,
        )

    def _update_procure_method(self, picking_type_code=False):
        rule_cache = {}
        for move in self:
            product_id = move.product_id
            warehouse = move.warehouse_id or move.picking_type_id.warehouse_id
            cache_key = (
                move.location_id.id,
                move.location_dest_id.id,
                product_id.id,
                warehouse.id,
                move.packaging_uom_id.id,
            )
            if cache_key in rule_cache:
                rule = rule_cache[cache_key]
            else:
                rule = self.env["stock.rule"]
                location = move.location_id
                while location:
                    domain = [
                        ("location_src_id", "=", location.id),
                        ("location_dest_id", "=", move.location_dest_id.id),
                        ("action", "!=", "push"),
                    ]
                    if picking_type_code:
                        domain.append(("picking_type_id.code", "=", picking_type_code))
                    rule = self.env["stock.rule"]._get_domain_rule_by(
                        False,
                        move.packaging_uom_id,
                        product_id,
                        warehouse,
                        domain,
                    )
                    if rule:
                        break
                    location = location.location_id
                rule_cache[cache_key] = rule
            if not rule:
                dbg.logic.debug(
                    "[move:%s] _update_procure_method: no rule, make_to_stock", move.id
                )
                move.procure_method = "make_to_stock"
                continue

            move.rule_id = rule.id
            if rule.procure_method in ["make_to_stock", "make_to_order"]:
                move.procure_method = rule.procure_method
            else:
                move.procure_method = "make_to_stock"
            dbg.logic.debug(
                "[move:%s] _update_procure_method: rule %s (%s) -> %s",
                move.id,
                rule.id,
                rule.procure_method,
                move.procure_method,
            )
        dbg.performance.debug(
            "_update_procure_method: %d moves, %d rule lookups",
            len(self),
            len(rule_cache),
        )

    def _prepare_procurement_origin(self):
        self.check_singleton()
        return (
            (self.reference_ids and self.reference_ids[0].name)
            or self.origin
            or self.picking_id.display_name
        )

    def _prepare_procurement_qty(self):
        consumed_from_stock_dict = self.env.context.get(
            "consumed_from_stock_dict",
            defaultdict(float),
        )
        quantities = []
        mtso_products_by_locations = defaultdict(list)
        mtso_moves = set()
        for move in self:
            if move.rule_id and move.rule_id.procure_method == "mts_else_mto":
                mtso_moves.add(move.id)
                mtso_products_by_locations[move.location_id].append(move.product_id.id)

        forecasted_qties_by_loc = {}
        for location, product_ids in mtso_products_by_locations.items():
            if location.is_reservation_bypass_required():
                continue
            products = (
                self.env["product.product"]
                .browse(product_ids)
                .with_context(location=location.id)
            )
            forecasted_qties_by_loc[location] = {
                product.id: product.qty_free for product in products
            }
        for move in self:
            if (
                move.id not in mtso_moves
                or move.product_id.uom_id.compare(move.product_qty, 0) <= 0
            ):
                quantities.append(move.product_uom_qty)
                continue

            if move._is_reservation_bypass_required():
                quantities.append(move.product_uom_qty)
                continue

            qty_free = max(
                forecasted_qties_by_loc[move.location_id][move.product_id.id]
                - consumed_from_stock_dict[move.location_id, move.product_id.id],
                0,
            )
            quantity = max(move.product_qty - qty_free, 0)
            product_uom_qty = move.product_id.uom_id._get_quantity_in_unit(
                quantity,
                move.product_uom_id,
                rounding_method="HALF-UP",
            )
            dbg.logic.debug(
                "[move:%s] mts_else_mto: demand %s, free %s -> procure %s",
                move.id,
                move.product_qty,
                qty_free,
                product_uom_qty,
            )
            quantities.append(product_uom_qty)
            consumed_from_stock_dict[move.location_id, move.product_id.id] += min(
                move.product_qty,
                qty_free,
            )

        return quantities

    def _prepare_procurement_vals(self):
        self.check_singleton()

        product_id = self.product_id.with_context(lang=self._get_lang())
        dates_info = {"date_planned": self._get_mto_procurement_date()}
        route = self.route_ids
        if not route and (result_packages := self.move_line_ids.result_package_id):
            related_packages = self.env["stock.package"].search_fetch(
                [("id", "parent_of", result_packages.ids)],
                ["package_type_id"],
            )
            route = related_packages.package_type_id.route_ids
        if (
            self.location_id.warehouse_id
            and self.location_id.warehouse_id.lot_stock_id.parent_path
            in self.location_id.parent_path
        ):
            dates_info = self.product_id._get_dates_info(
                self.date,
                self.location_id,
                route_ids=route,
            )
        warehouse = self.warehouse_id or self.picking_type_id.warehouse_id
        if not self.location_id.warehouse_id:
            warehouse = self.rule_id.route_id.supplier_wh_id

        move_dest_ids = False
        if self.procure_method == "make_to_order":
            move_dest_ids = self
        return {
            "product_description_variants": self.description_picking
            and self.description_picking.replace(
                product_id._get_description(self.picking_type_id),
                "",
            ).replace(
                product_id._get_picking_description(self.picking_type_id) or "",
                "",
            ),
            "never_product_template_attribute_value_ids": self.never_product_template_attribute_value_ids,
            "date_planned": dates_info.get("date_planned"),
            "date_order": dates_info.get("date_order"),
            "date_deadline": self.date_deadline,
            "move_dest_ids": move_dest_ids,
            "partner_id": (
                self._get_partner_id()
                if move_dest_ids or self.rule_id.procure_method == "mts_else_mto"
                else False
            ),
            "route_ids": route,
            "warehouse_id": warehouse,
            "priority": self.priority,
            "reference_ids": self.reference_ids,
            "orderpoint_id": self.orderpoint_id,
            "packaging_uom_id": self.packaging_uom_id,
        }

    def _get_push_rule_cached(self, StockRule, values):
        self.check_singleton()
        cache = self.env.context.get("_push_rule_cache")
        if cache is None:
            return StockRule._get_push_rule(
                self.product_id, self.location_dest_id, values
            )
        routes = values.get("route_ids")
        warehouse = values.get("warehouse_id")
        packaging_uom = values.get("packaging_uom_id")
        key = (
            self.location_dest_id.id,
            tuple(sorted(routes.ids)) if routes else (),
            tuple(sorted(self.product_id.route_ids.ids)),
            tuple(sorted(self.product_id.categ_id.total_route_ids.ids)),
            packaging_uom.id if packaging_uom else False,
            warehouse.id if warehouse else False,
            repr(values.get("domain")),
        )
        if key not in cache:
            cache[key] = StockRule._get_push_rule(
                self.product_id, self.location_dest_id, values
            )
        else:
            dbg.performance.debug("[move:%s] push rule cache hit", self.id)
        return cache[key]

    @dbg.timed
    def _push_apply(self):
        depth = self.env.context.get("_push_apply_depth", 0) + 1
        dbg.pipeline.debug("_push_apply on %s at depth %d", dbg.rec(self), depth)
        if depth > self._MAX_PUSH_DEPTH:
            raise UserError(
                _(
                    "Push rules recursion limit reached. Check for circular push rules in your warehouse configuration."
                )
            )
        moves = self.with_context(
            _push_apply_depth=depth,
            _push_rule_cache=self.env.context.get("_push_rule_cache", {}),
        )
        plan = [move._plan_push() for move in moves]
        moves_by_rule = defaultdict(list)
        for move, rule, foreign in plan:
            if rule:
                moves_by_rule[rule, foreign].append(move.id)
        pushed = {}
        dbg.logic.debug(
            "_push_apply: rules %s",
            {rule.id: move_ids for (rule, _foreign), move_ids in moves_by_rule.items()},
        )
        for (rule, foreign), move_ids in moves_by_rule.items():
            rule_moves = moves.browse(move_ids)
            if foreign:
                rule = rule.sudo()
                rule_moves = rule_moves.with_context(
                    allowed_companies=self.env.user.company_ids.ids,
                )
            pushed.update(rule._run_push(rule_moves))

        new_moves = moves.browse()
        for move, _rule, _foreign in plan:
            new_move = pushed.get(move.id) or moves.browse()
            new_moves |= new_move
            move._update_move_dests_after_push(new_move)
        dbg.pipeline.debug("_push_apply -> confirm pushed %s", dbg.rec(new_moves))
        return new_moves.sudo()._action_confirm()

    def _plan_push(self):
        self.check_singleton()
        move = self
        warehouse_id = move.warehouse_id or move.picking_id.picking_type_id.warehouse_id
        StockRule = self.env["stock.rule"]
        foreign = move.location_dest_id.company_id not in self.env.companies
        if foreign:
            StockRule = StockRule.sudo()
            move = move.with_context(
                allowed_companies=self.env.user.company_ids.ids,
            )
            warehouse_id = False

        related_packages = self.env["stock.package"]
        if result_packages := move.move_line_ids.result_package_id:
            related_packages = related_packages.search_fetch(
                [("id", "parent_of", result_packages.ids)],
                ["package_type_id"],
            )
        push_values = {
            "route_ids": move.route_ids | related_packages.package_type_id.route_ids,
            "warehouse_id": warehouse_id,
            "packaging_uom_id": move.packaging_uom_id,
        }
        rule = move._get_push_rule_cached(StockRule, push_values)
        excluded_rule_ids = []
        while (
            rule
            and rule.push_domain
            and not move.filtered_domain(literal_eval(rule.push_domain))
        ):
            dbg.logic.debug(
                "[move:%s] push rule %s excluded by its push_domain", move.id, rule.id
            )
            excluded_rule_ids.append(rule.id)
            rule = move._get_push_rule_cached(
                StockRule,
                {**push_values, "domain": [("id", "not in", excluded_rule_ids)]},
            )
        if rule and (
            not move.origin_returned_move_id
            or move.origin_returned_move_id.location_dest_id.id
            != rule.location_dest_id.id
        ):
            dbg.logic.debug(
                "[move:%s] _plan_push: rule %s foreign=%s", move.id, rule.id, foreign
            )
            return move, rule, foreign
        dbg.logic.debug(
            "[move:%s] _plan_push: no push (rule %s, returned move %s)",
            move.id,
            rule.id,
            move.origin_returned_move_id.id,
        )
        return move, StockRule.browse(), foreign

    def _update_move_dests_after_push(self, new_move):
        self.check_singleton()
        move_to_propagate_ids = set()
        move_to_mts_ids = set()
        for m in self.move_dest_ids - new_move:
            if (
                new_move
                and self.location_final_id
                and m.location_id == self.location_final_id
            ):
                move_to_propagate_ids.add(m.id)
            elif not m.location_id._is_child_of(self.location_dest_id):
                move_to_mts_ids.add(m.id)
        if move_to_mts_ids or move_to_propagate_ids:
            dbg.logic.debug(
                "[move:%s] after push %s: break mto on %s, propagate to %s",
                self.id,
                new_move.id,
                sorted(move_to_mts_ids),
                sorted(move_to_propagate_ids),
            )
        if move_to_mts_ids:
            self.browse(move_to_mts_ids)._break_mto_link(self)
        if move_to_propagate_ids:
            self.move_dest_ids = [
                Command.unlink(m_id) for m_id in move_to_propagate_ids
            ]
            new_move.move_dest_ids = [
                Command.link(m_id) for m_id in move_to_propagate_ids
            ]

    def _is_excluded_from_push(self):
        return self.is_inventory or (
            self.move_dest_ids
            and any(
                m.location_id._is_child_of(self.location_dest_id)
                or self.location_dest_id._is_child_of(m.location_id)
                for m in self.move_dest_ids
            )
        )

    @dbg.timed
    def _trigger_scheduler(self):
        if not self or self.env["ir.config_parameter"].sudo().get_param(
            "stock.no_auto_scheduler",
        ):
            dbg.logic.debug("_trigger_scheduler: skipped (empty or no_auto_scheduler)")
            return

        seen_domain_keys = set()
        candidate_domains = []
        for move in self:
            domain_key = (
                move.product_id.id,
                move.company_id.id,
                move.location_id.id,
                move.location_dest_id.id,
            )
            if domain_key in seen_domain_keys:
                continue
            seen_domain_keys.add(domain_key)
            candidate_domains.append(
                Domain(
                    [
                        ("product_id", "=", move.product_id.id),
                        ("location_id", "parent_of", move.location_id.id),
                        ("company_id", "=", move.company_id.id),
                        "!",
                        ("location_id", "parent_of", move.location_dest_id.id),
                    ],
                ),
            )
        candidates = self.env["stock.warehouse.orderpoint"].search(
            Domain("trigger", "=", "auto") & Domain.OR(candidate_domains),
        )
        dbg.performance.debug(
            "_trigger_scheduler: %d moves, %d domains, %d candidate orderpoints",
            len(self),
            len(candidate_domains),
            len(candidates),
        )
        candidates_by_key = defaultdict(list)
        for candidate in candidates:
            candidates_by_key[
                candidate.product_id.id,
                candidate.company_id.id,
            ].append(candidate)

        orderpoints_by_company = defaultdict(
            lambda: self.env["stock.warehouse.orderpoint"],
        )
        orderpoints_context_by_company = defaultdict(dict)
        for move in self:
            orderpoint = next(
                (
                    candidate
                    for candidate in candidates_by_key[
                        move.product_id.id,
                        move.company_id.id,
                    ]
                    if move.location_id._is_child_of(candidate.location_id)
                    and not move.location_dest_id._is_child_of(candidate.location_id)
                ),
                self.env["stock.warehouse.orderpoint"],
            )
            if orderpoint:
                orderpoints_by_company[orderpoint.company_id] |= orderpoint
            if (
                orderpoint
                and move.product_id.uom_id.compare(
                    move.product_qty, orderpoint.product_min_qty
                )
                > 0
                and move.reference_ids
            ):
                orderpoints_context_by_company[orderpoint.company_id].setdefault(
                    orderpoint.id,
                    set(),
                )
                orderpoints_context_by_company[orderpoint.company_id][
                    orderpoint.id
                ] |= set(move.reference_ids.ids)
        for company, orderpoints in orderpoints_by_company.items():
            dbg.pipeline.debug(
                "_trigger_scheduler -> _procure_orderpoint_confirm %s for company %s",
                dbg.rec(orderpoints),
                company.id,
            )
            orderpoints.with_context(
                origins=orderpoints_context_by_company[company],
            )._procure_orderpoint_confirm(company_id=company, raise_user_error=False)

    def _get_orderpoints_to_update(self):
        # every write of a move's state, date, quantity or locations asks
        # which orderpoints it reaches; the answer per (product, warehouses)
        # is memoized for the transaction and discarded when an orderpoint's
        # scope changes
        Orderpoint = self.env["stock.warehouse.orderpoint"]
        if not self:
            return Orderpoint
        memo = ORDERPOINTS_BY_SCOPE(self.env)
        keys = OrderedSet()
        for move in self:
            wh_ids = tuple(
                sorted(
                    {
                        *move.location_id.warehouse_id.ids,
                        *move.location_dest_id.warehouse_id.ids,
                    },
                ),
            )
            keys.add((move.product_id.id, wh_ids))
        missing = [key for key in keys if key not in memo]
        if missing:
            domains = []
            for product_id, wh_ids in missing:
                domain_for_move = Domain("product_id", "=", product_id)
                if wh_ids:
                    domain_for_move &= Domain("warehouse_id", "in", list(wh_ids))
                domains.append(domain_for_move)
            found = Orderpoint.sudo().search(Domain.OR(domains), order="id")
            for product_id, wh_ids in missing:
                memo[product_id, wh_ids] = [
                    orderpoint.id
                    for orderpoint in found
                    if orderpoint.product_id.id == product_id
                    and (not wh_ids or orderpoint.warehouse_id.id in wh_ids)
                ]
        ids = OrderedSet()
        for key in keys:
            ids.update(memo[key])
        return Orderpoint.sudo().browse(sorted(ids))

    def _update_orderpoints(self, orderpoints=None):
        if orderpoints is None:
            orderpoints = self._get_orderpoints_to_update()
        if orderpoints:
            dbg.lifecycle.debug(
                "_update_orderpoints from %s: recompute %s",
                dbg.rec(self),
                dbg.rec(orderpoints),
            )
        orderpoints.invalidate_recordset(["qty_to_order", "qty_forecast"])
        self.env.add_to_compute(
            self.env["stock.warehouse.orderpoint"]._fields["qty_to_order_computed"],
            orderpoints,
        )

    def _reverse_negative_moves(self):
        for move in self:
            new_source, new_dest = move.location_dest_id, move.location_id
            move.move_line_ids.filtered(
                lambda ml, src=new_source: not ml.location_id._is_child_of(src),
            ).unlink()
            orig_move_ids, dest_move_ids = [], []
            for m in move.move_orig_ids | move.move_dest_ids:
                from_loc, to_loc = m.location_id, m.location_dest_id
                if m.product_uom_id.compare(m.product_uom_qty, 0) < 0:
                    from_loc, to_loc = to_loc, from_loc
                if to_loc == new_source:
                    orig_move_ids += m.ids
                elif new_dest == from_loc:
                    dest_move_ids += m.ids
            vals = {
                "location_id": new_source.id,
                "location_dest_id": new_dest.id,
                "location_final_id": new_dest.id,
                "move_orig_ids": [Command.set(orig_move_ids)],
                "move_dest_ids": [Command.set(dest_move_ids)],
                "product_uom_qty": -move.product_uom_qty,
                "procure_method": "make_to_stock",
            }
            if move.picking_type_id.return_picking_type_id:
                vals["picking_type_id"] = move.picking_type_id.return_picking_type_id.id
            dbg.logic.debug(
                "[move:%s] _reverse_negative_moves: %s -> %s qty %s, orig %s dest %s",
                move.id,
                new_source.id,
                new_dest.id,
                vals["product_uom_qty"],
                orig_move_ids,
                dest_move_ids,
            )
            move.write(vals)
        if self:
            self._update_picking()

    def _break_mto_link(self, parent_move):
        dbg.logic.debug(
            "_break_mto_link: %s from parent %s", dbg.rec(self), parent_move.id
        )
        self.move_orig_ids = [Command.unlink(parent_move.id)]
        self.procure_method = "make_to_stock"
        self._recompute_state()

    @dbg.timed
    def _push_and_assign_downstream(self):
        moves_to_push = self.filtered(lambda m: not m._is_excluded_from_push())
        dbg.pipeline.debug(
            "_push_and_assign_downstream on %s: push %s",
            dbg.rec(self),
            dbg.rec(moves_to_push),
        )
        if moves_to_push:
            moves_to_push._push_apply()
        move_dests_per_company = defaultdict(lambda: self.env["stock.move"])
        for move_dest in self.sudo().move_dest_ids:
            move_dests_per_company[move_dest.company_id.id] |= move_dest
        for company_id, move_dests in move_dests_per_company.items():
            dbg.pipeline.debug(
                "_push_and_assign_downstream -> _action_assign %s (company %s)",
                dbg.rec(move_dests),
                company_id,
            )
            move_dests.sudo().with_company(company_id)._action_assign()

    @api.model
    def _get_allocation_allowed_states(self, include_assigned=False):
        states = ["confirmed", "partially_available", "waiting"]
        if include_assigned:
            states.append("assigned")
        return states

    @api.model
    def _get_domain_allocatable_demand(
        self,
        location_ids,
        product_ids,
        include_assigned=True,
    ):
        return [
            ("state", "in", self._get_allocation_allowed_states(include_assigned)),
            ("product_qty", ">", 0),
            ("location_id", "in", list(location_ids)),
            ("product_id", "in", list(product_ids)),
        ]
