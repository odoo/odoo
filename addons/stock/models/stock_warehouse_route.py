import logging
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import ormcache
from odoo.tools.translate import _

from ..tools import debug_log as dbg
from .stock_warehouse import ROUTE_NAMES

_logger = logging.getLogger(__name__)


class StockWarehouseRoute(models.Model):
    _inherit = "stock.warehouse"

    @ormcache()
    def _get_route_field_names(self):
        return tuple(
            name
            for name, field in self._fields.items()
            if field.type == "many2one" and field.comodel_name == "stock.route"
        )

    def _get_fields_route_trigger(self):
        return frozenset({"reception_steps", "delivery_steps"})

    def _get_global_rule_fields(self):
        return frozenset({"mto_pull_id"})

    @dbg.timed
    def _create_or_update_route(self):
        self.check_singleton()
        routes = []
        field_vals = {}
        rules_dict = self._prepare_rule_routings()
        for route_field, route_data in self._prepare_route_vals().items():
            dbg.lifecycle.debug(
                "[warehouse:%s] route %s: %s",
                self.id,
                route_field,
                "update" if self[route_field] else "create",
            )
            if self[route_field]:
                route = self[route_field]
                if "route_update_values" in route_data:
                    route.write(route_data["route_update_values"])
                route.rule_ids.write({"active": False})
            else:
                if "route_update_values" in route_data:
                    route_data["route_create_values"].update(
                        route_data["route_update_values"]
                    )
                route = self.env["stock.route"].create(
                    route_data["route_create_values"]
                )
                field_vals[route_field] = route.id
            routing_key = route_data.get("routing_key")
            if routing_key not in rules_dict[self.id]:
                raise ValueError(
                    "stock.warehouse route %r declares routing_key %r, which "
                    "_prepare_rule_routings does not answer. Every entry of "
                    "_prepare_route_vals needs a routing_key that "
                    "_prepare_rule_routings knows, and a module adding a route extends "
                    "both." % (route_field, routing_key)
                )
            rules = rules_dict[self.id][routing_key]
            if "rules_values" in route_data:
                route_data["rules_values"].update({"route_id": route.id})
            else:
                route_data["rules_values"] = {"route_id": route.id}
            rules_list = self._prepare_rule_vals(
                rules, values=route_data["rules_values"]
            )
            self._sync_rules(rules_list)
            if route_data["route_create_values"].get(
                "warehouse_selectable", False
            ) or route_data.get("route_update_values", {}).get(
                "warehouse_selectable", False
            ):
                routes.append(route)
        linked = self.with_context(active_test=False).route_ids
        new_links = [route for route in routes if route not in linked]
        if new_links:
            field_vals["route_ids"] = [
                fields.Command.link(route.id) for route in new_links
            ]
        dbg.logic.debug(
            "[warehouse:%s] _create_or_update_route writes %s",
            self.id,
            dbg.keys(field_vals),
        )
        if field_vals:
            self.write(field_vals)
        return field_vals

    def _prepare_route_vals(self):
        return {
            "reception_route_id": {
                "routing_key": self.reception_steps,
                "depends": ["reception_steps"],
                "route_update_values": {
                    "name": self._format_routename(route_type=self.reception_steps),
                    "active": self.active,
                },
                "route_create_values": {
                    "product_categ_selectable": True,
                    "warehouse_selectable": True,
                    "product_selectable": False,
                    "company_id": self.company_id.id,
                    "sequence": 50,
                },
                "rules_values": {
                    "active": True,
                    "propagate_cancel": True,
                },
            },
            "delivery_route_id": {
                "routing_key": self.delivery_steps,
                "depends": ["delivery_steps"],
                "route_update_values": {
                    "name": self._format_routename(route_type=self.delivery_steps),
                    "active": self.active,
                },
                "route_create_values": {
                    "product_categ_selectable": True,
                    "warehouse_selectable": True,
                    "product_selectable": False,
                    "company_id": self.company_id.id,
                    "sequence": 60,
                },
                "rules_values": {"active": True, "propagate_carrier": True},
            },
        }

    def _prepare_receive_route_vals(self, installed_depends):
        return {
            "reception_route_id": {
                "routing_key": self.reception_steps,
                "depends": ["reception_steps", installed_depends],
                "route_update_values": {
                    "name": self._format_routename(route_type=self.reception_steps),
                    "active": self.active,
                },
                "route_create_values": {
                    "product_categ_selectable": True,
                    "warehouse_selectable": True,
                    "product_selectable": False,
                    "company_id": self.company_id.id,
                    "sequence": 9,
                },
                "rules_values": {
                    "active": True,
                    "propagate_cancel": True,
                    "procure_method": "make_to_order",
                },
            }
        }

    def _create_or_update_global_routes_rules(self):
        new_rule_ids = {}
        for (
            rule_field,
            rule_details,
        ) in self._prepare_routable_global_route_rule_vals().items():
            values = rule_details.get("update_values", {})
            if self[rule_field]:
                self[rule_field].write(values)
            else:
                values.update(rule_details["create_values"])
                values.update({"warehouse_id": self.id})
                new_rule_ids[rule_field] = self.env["stock.rule"].create(values).id
        dbg.lifecycle.debug(
            "[warehouse:%s] global route rules created: %s", self.id, new_rule_ids
        )
        if new_rule_ids:
            self.with_context(stock_no_global_route_refresh=True).write(new_rule_ids)
        return True

    def _get_or_create_global_route(
        self,
        xml_id,
        route_name,
        create=True,
        raise_if_not_found=False,
    ):
        data_route = route = self.env.ref(xml_id, raise_if_not_found=False)
        company = self.company_id[:1] or self.env.company
        if not route or (
            route.sudo().company_id and route.sudo().company_id != company
        ):
            route = (
                self.env["stock.route"]
                .with_context(active_test=False)
                .search(
                    [
                        ("name", "=", route_name),
                        ("company_id", "in", [False, company.id]),
                    ],
                    order="company_id",
                    limit=1,
                )
            )
        if not route:
            if raise_if_not_found:
                raise UserError(_("Can't find any generic route %s.", route_name))
            if data_route and create:
                dbg.lifecycle.debug(
                    "_get_or_create_global_route: copying %s for company %s",
                    xml_id,
                    company.id,
                )
                route = data_route.copy(
                    {
                        "name": route_name,
                        "company_id": company.id,
                        "rule_ids": False,
                    },
                )
        return route

    def _prepare_routable_global_route_rule_vals(self):
        vals = self._prepare_global_route_rule_vals()
        return {
            k: v
            for k, v in vals.items()
            if v.get("create_values", {}).get("route_id", True)
            and v.get("update_values", {}).get("route_id", True)
        }

    def _prepare_global_route_rule_vals(self):
        delivery_rules = self._prepare_rule_routings()[self.id][self.delivery_steps]
        rule = next(
            (r for r in delivery_rules if r.from_loc == self.lot_stock_id), None
        )
        if not rule:
            raise UserError(
                _(
                    "The delivery configuration of warehouse %s has no rule "
                    "starting from its stock location, so its MTO rule can't be "
                    "generated.",
                    self.display_name,
                )
            )
        location_id = rule.from_loc
        location_dest_id = rule.dest_loc
        picking_type_id = rule.picking_type
        return {
            "mto_pull_id": {
                "depends": ["delivery_steps"],
                "create_values": {
                    "active": True,
                    "procure_method": "make_to_order",
                    "company_id": self.company_id.id,
                    "action": "pull",
                    "auto": "manual",
                    "propagate_carrier": True,
                    "route_id": self._get_or_create_global_route(
                        "stock.route_warehouse0_mto", _("Replenish on Order (MTO)")
                    ).id,
                },
                "update_values": {
                    "name": self._format_rulename(location_id, location_dest_id, "MTO"),
                    "location_dest_id": location_dest_id.id,
                    "location_src_id": location_id.id,
                    "picking_type_id": picking_type_id.id,
                },
            }
        }

    def _prepare_rule_routings(self):
        customer_loc, supplier_loc = self._get_partner_locations()
        return {
            warehouse.id: {
                **self._prepare_reception_routings(warehouse, supplier_loc),
                **self._prepare_delivery_routings(warehouse, customer_loc),
            }
            for warehouse in self
        }

    def _prepare_reception_routings(self, warehouse, supplier_loc):
        return {
            "one_step": [
                self.Routing(
                    supplier_loc,
                    warehouse.lot_stock_id,
                    warehouse.in_type_id,
                    "pull",
                )
            ],
            "two_steps": [
                self.Routing(
                    supplier_loc,
                    warehouse.lot_stock_id,
                    warehouse.in_type_id,
                    "pull",
                ),
                self.Routing(
                    warehouse.wh_input_stock_loc_id,
                    warehouse.lot_stock_id,
                    warehouse.store_type_id,
                    "push",
                ),
            ],
            "three_steps": [
                self.Routing(
                    supplier_loc,
                    warehouse.lot_stock_id,
                    warehouse.in_type_id,
                    "pull",
                ),
                self.Routing(
                    warehouse.wh_input_stock_loc_id,
                    warehouse.wh_qc_stock_loc_id,
                    warehouse.qc_type_id,
                    "push",
                ),
                self.Routing(
                    warehouse.wh_qc_stock_loc_id,
                    warehouse.lot_stock_id,
                    warehouse.store_type_id,
                    "push",
                ),
            ],
        }

    def _prepare_delivery_routings(self, warehouse, customer_loc):
        return {
            "ship_only": [
                self.Routing(
                    warehouse.lot_stock_id,
                    customer_loc,
                    warehouse.out_type_id,
                    "pull",
                )
            ],
            "pick_ship": [
                self.Routing(
                    warehouse.lot_stock_id,
                    customer_loc,
                    warehouse.pick_type_id,
                    "pull",
                ),
                self.Routing(
                    warehouse.wh_output_stock_loc_id,
                    customer_loc,
                    warehouse.out_type_id,
                    "push",
                ),
            ],
            "pick_pack_ship": [
                self.Routing(
                    warehouse.lot_stock_id,
                    customer_loc,
                    warehouse.pick_type_id,
                    "pull",
                ),
                self.Routing(
                    warehouse.wh_pack_stock_loc_id,
                    warehouse.wh_output_stock_loc_id,
                    warehouse.pack_type_id,
                    "push",
                ),
                self.Routing(
                    warehouse.wh_output_stock_loc_id,
                    customer_loc,
                    warehouse.out_type_id,
                    "push",
                ),
            ],
        }

    def _prepare_internal_reception_routings(self):
        return {
            "one_step": [],
            "two_steps": [
                self.Routing(
                    self.wh_input_stock_loc_id,
                    self.lot_stock_id,
                    self.store_type_id,
                    "push",
                )
            ],
            "three_steps": [
                self.Routing(
                    self.wh_input_stock_loc_id,
                    self.wh_qc_stock_loc_id,
                    self.qc_type_id,
                    "push",
                ),
                self.Routing(
                    self.wh_qc_stock_loc_id,
                    self.lot_stock_id,
                    self.store_type_id,
                    "push",
                ),
            ],
        }

    def _sync_rules(self, rules_list):
        Rule = self.env["stock.rule"]
        if not rules_list:
            return
        identity = (
            "picking_type_id",
            "location_src_id",
            "location_dest_id",
            "route_id",
        )
        wanted = {
            tuple(rule_vals[name] for name in identity) + (rule_vals["action"],)
            for rule_vals in rules_list
        }
        candidates = Rule.with_context(active_test=False).search(
            [
                (name, "in", list({key[position] for key in wanted}))
                for position, name in enumerate(identity)
            ]
        )
        existing = {}
        for rule in candidates:
            key = (
                rule.picking_type_id.id,
                rule.location_src_id.id,
                rule.location_dest_id.id,
                rule.route_id.id,
                rule.action,
            )
            existing.setdefault(key, rule)
        to_create = []
        for rule_vals in rules_list:
            key = tuple(rule_vals[name] for name in identity) + (rule_vals["action"],)
            rule = existing.get(key)
            if not rule:
                to_create.append(rule_vals)
                continue
            changed = {
                name: value
                for name, value in rule_vals.items()
                if name not in identity
                and self._is_rule_value_different(rule, name, value)
            }
            if changed:
                dbg.lifecycle.debug(
                    "[rule:%s] _sync_rules updates %s", rule.id, dbg.keys(changed)
                )
                rule.write(changed)
        dbg.logic.debug(
            "_sync_rules: %d wanted, %d candidates, %d to create",
            len(wanted),
            len(candidates),
            len(to_create),
        )
        if to_create:
            Rule.create(to_create)

    @api.model
    def _is_rule_value_different(self, rule, field_name, value):
        current = rule[field_name]
        if isinstance(current, models.BaseModel):
            return current.id != (value or False)
        return current != value

    def _prepare_rule_vals(self, routings, values=None, name_suffix=""):
        first_rule = True
        rules_list = []
        for routing in routings:
            route_rule_values = {
                "name": self._format_rulename(
                    routing.from_loc, routing.dest_loc, name_suffix
                ),
                "location_src_id": routing.from_loc.id,
                "location_dest_id": routing.dest_loc.id,
                "action": routing.action,
                "auto": "manual",
                "picking_type_id": routing.picking_type.id,
                "procure_method": "make_to_stock" if first_rule else "make_to_order",
                "warehouse_id": self.id,
                "company_id": self.company_id.id,
            }
            route_rule_values.update(values or {})
            rules_list.append(route_rule_values)
            first_rule = False
        if values and values.get("propagate_cancel") and rules_list:
            rules_list[-1]["propagate_cancel"] = False
        return rules_list

    def _prepare_supply_pull_rule_vals(self, routings, values=None):
        pull_values = dict(values or {})
        pull_values["active"] = True
        rules_list = self._prepare_rule_vals(routings, values=pull_values)
        for pull_rules in rules_list:
            pull_rules["procure_method"] = (
                "make_to_order"
                if self.lot_stock_id.id != pull_rules["location_src_id"]
                else "make_to_stock"
            )
        return rules_list

    def _get_all_routes(self):
        routes = self.route_ids | self.mto_pull_id.route_id
        routes |= (
            self.env["stock.route"]
            .with_context(active_test=False)
            .search([("supplied_wh_id", "in", self.ids)])
        )
        return routes

    def _get_route_name(self, route_type):
        if route_type not in ROUTE_NAMES:
            raise UserError(
                _(
                    "No route name is declared for the routing configuration %s.",
                    route_type,
                )
            )
        return self.env._(ROUTE_NAMES[route_type])  # pylint: disable=gettext-variable

    def _sync_resupply_routes(self, previous_resupply_whs):
        self.check_singleton()
        Route = self.env["stock.route"]
        new_resupply_whs = self.resupply_wh_ids
        to_add = new_resupply_whs - previous_resupply_whs
        to_remove = previous_resupply_whs - new_resupply_whs
        dbg.logic.debug(
            "[warehouse:%s] _sync_resupply_routes: add %s remove %s",
            self.id,
            dbg.rec(to_add),
            dbg.rec(to_remove),
        )
        if to_add:
            existing_routes = Route.search(
                [
                    ("supplied_wh_id", "=", self.id),
                    ("supplier_wh_id", "in", to_add.ids),
                    ("active", "=", False),
                ]
            )
            existing_routes.action_unarchive()
            remaining_to_add = to_add - existing_routes.supplier_wh_id
            dbg.logic.debug(
                "_sync_resupply_routes: unarchived %s, creating for %s",
                dbg.rec(existing_routes),
                dbg.rec(remaining_to_add),
            )
            if remaining_to_add:
                self._create_resupply_routes(remaining_to_add)
        if to_remove:
            to_disable_route_ids = Route.search(
                [
                    ("supplied_wh_id", "=", self.id),
                    ("supplier_wh_id", "in", to_remove.ids),
                    ("active", "=", True),
                ]
            )
            to_disable_route_ids.action_archive()

    def _create_resupply_routes(self, supplier_warehouses):
        self.check_singleton()
        Route = self.env["stock.route"]
        Rule = self.env["stock.rule"]

        internal_transit_location, external_transit_location = (
            self._get_transit_locations()
        )

        for supplier_wh in supplier_warehouses:
            transit_location = (
                internal_transit_location
                if supplier_wh.company_id == self.company_id
                else external_transit_location
            )
            if not transit_location:
                dbg.logic.debug(
                    "[warehouse:%s] no transit location for supplier %s, skipped",
                    self.id,
                    supplier_wh.id,
                )
                continue
            transit_location.active = True
            output_location = (
                supplier_wh.lot_stock_id
                if supplier_wh.delivery_steps == "ship_only"
                else supplier_wh.wh_output_stock_loc_id
            )
            output_to_transit = self.Routing(
                output_location, transit_location, supplier_wh.out_type_id, "pull"
            )
            if supplier_wh.delivery_steps == "ship_only":
                supplier_wh._create_resupply_mto_rules([output_to_transit])

            inter_wh_route = Route.create(
                self._prepare_inter_warehouse_route_vals(supplier_wh)
            )
            dbg.lifecycle.debug(
                "[warehouse:%s] resupply route %s from %s via transit %s",
                self.id,
                inter_wh_route.id,
                supplier_wh.id,
                transit_location.id,
            )

            pull_rules_list = supplier_wh._prepare_supply_pull_rule_vals(
                [output_to_transit],
                values={"route_id": inter_wh_route.id, "location_dest_from_rule": True},
            )
            if supplier_wh.delivery_steps != "ship_only":
                pull_rules_list += supplier_wh._prepare_supply_pull_rule_vals(
                    [
                        self.Routing(
                            supplier_wh.lot_stock_id,
                            output_location,
                            supplier_wh.pick_type_id,
                            "pull",
                        )
                    ],
                    values={"route_id": inter_wh_route.id},
                )
            pull_rules_list += self._prepare_supply_pull_rule_vals(
                [
                    self.Routing(
                        transit_location, self.lot_stock_id, self.in_type_id, "pull"
                    )
                ],
                values={"route_id": inter_wh_route.id},
            )
            Rule.create(pull_rules_list)

    def _create_resupply_mto_rules(self, routings):
        self.check_singleton()
        if not routings:
            return
        mto_vals = self._prepare_routable_global_route_rule_vals().get("mto_pull_id")
        if not mto_vals:
            return
        self._sync_rules(
            self._prepare_rule_vals(
                routings, mto_vals["create_values"], name_suffix="MTO"
            )
        )

    def _prepare_inter_warehouse_route_vals(self, supplier_warehouse):
        return {
            "name": self._format_resupply_routename(self.name, supplier_warehouse.name),
            "warehouse_selectable": True,
            "product_selectable": True,
            "product_categ_selectable": True,
            "supplied_wh_id": self.id,
            "supplier_wh_id": supplier_warehouse.id,
            "company_id": (self.company_id & supplier_warehouse.company_id).id,
        }

    def _update_delivery_steps_resupply(self, delivery_new):
        if not delivery_new:
            return
        for warehouse in self:
            if warehouse.delivery_steps == delivery_new:
                continue
            if "ship_only" not in (warehouse.delivery_steps, delivery_new):
                continue
            change_to_multiple = warehouse.delivery_steps == "ship_only"
            output_loc = (
                warehouse.lot_stock_id
                if delivery_new == "ship_only"
                else warehouse.wh_output_stock_loc_id
            )
            dbg.logic.debug(
                "[warehouse:%s] delivery steps %s -> %s, resupply output %s",
                warehouse.id,
                warehouse.delivery_steps,
                delivery_new,
                output_loc.id,
            )
            warehouse._update_delivery_resupply(output_loc, change_to_multiple)

    def _get_resupply_routes(self):
        self.check_singleton()
        return self.env["stock.route"].search([("supplier_wh_id", "=", self.id)])

    def _get_domain_resupply_pick_leg(self, routes):
        self.check_singleton()
        return [
            ("route_id", "in", routes.ids),
            ("action", "!=", "push"),
            ("location_dest_id", "=", self.wh_output_stock_loc_id.id),
            ("picking_type_id", "=", self.pick_type_id.id),
        ]

    def _get_domain_resupply_mto_leg(self):
        self.check_singleton()
        mto_route = self._get_or_create_global_route(
            "stock.route_warehouse0_mto",
            _("Replenish on Order (MTO)"),
            create=False,
        )
        if not mto_route:
            return False
        return [
            ("route_id", "=", mto_route.id),
            ("action", "!=", "push"),
            ("location_dest_id.usage", "=", "transit"),
            ("location_src_id", "=", self.lot_stock_id.id),
            ("warehouse_id", "=", self.id),
        ]

    def _update_delivery_resupply(self, new_location, change_to_multiple):
        self.check_singleton()
        Rule = self.env["stock.rule"]
        routes = self._get_resupply_routes()
        if not routes:
            return
        dbg.pipeline.debug(
            "[warehouse:%s] _update_delivery_resupply on routes %s multi=%s",
            self.id,
            dbg.rec(routes),
            change_to_multiple,
        )
        transit_legs = Rule.search(
            [
                ("route_id", "in", routes.ids),
                ("action", "!=", "push"),
                ("location_dest_id.usage", "=", "transit"),
            ]
        )
        transit_legs.write(
            {
                "location_src_id": new_location.id,
                "procure_method": "make_to_order"
                if change_to_multiple
                else "make_to_stock",
            }
        )
        if change_to_multiple:
            existing = Rule.with_context(active_test=False).search(
                self._get_domain_resupply_pick_leg(routes)
            )
            missing_rule_vals = []
            for route in routes - existing.route_id:
                missing_rule_vals += self._prepare_supply_pull_rule_vals(
                    [
                        self.Routing(
                            self.lot_stock_id, new_location, self.pick_type_id, "pull"
                        )
                    ],
                    values={"route_id": route.id},
                )
            Rule.create(missing_rule_vals)
        else:
            self._create_resupply_mto_rules(
                [
                    self.Routing(self.lot_stock_id, location, self.out_type_id, "pull")
                    for location in transit_legs.location_dest_id
                ]
            )
        self._update_resupply_rule_activity(multi_step=change_to_multiple)

    def _update_resupply_rule_activity(self, multi_step=None):
        self.check_singleton()
        Rule = self.env["stock.rule"].with_context(active_test=False)
        routes = self._get_resupply_routes()
        if not routes:
            return
        if multi_step is None:
            multi_step = self.delivery_steps != "ship_only"
        dbg.lifecycle.debug(
            "[warehouse:%s] resupply rule activity: pick legs active=%s",
            self.id,
            multi_step,
        )
        Rule.search(self._get_domain_resupply_pick_leg(routes)).write(
            {"active": multi_step}
        )
        mto_domain = self._get_domain_resupply_mto_leg()
        if mto_domain:
            Rule.search(mto_domain).write({"active": not multi_step})

    def _update_resupply_route_activity(self, active):
        self.check_singleton()
        routes = (
            self.env["stock.route"]
            .with_context(active_test=False)
            .search(
                [
                    "|",
                    ("supplied_wh_id", "=", self.id),
                    ("supplier_wh_id", "=", self.id),
                ]
            )
        )
        if not active:
            routes.filtered("active").write({"active": False})
            return routes
        revivable = routes.filtered(
            lambda route: (
                not route.active
                and route.supplied_wh_id.active
                and route.supplier_wh_id.active
                and route.supplier_wh_id in route.supplied_wh_id.resupply_wh_ids
            )
        )
        dbg.lifecycle.debug(
            "[warehouse:%s] resupply routes %s: revivable %s",
            self.id,
            dbg.rec(routes),
            dbg.rec(revivable),
        )
        if revivable:
            revivable.write({"active": True})
        return routes

    def _update_route_names(self, new_name):
        new_prefix = "%s: " % new_name
        for warehouse in self:
            old_prefix = "%s: " % warehouse.name
            for route in warehouse.route_ids:
                if route.name and route.name.startswith(old_prefix):
                    route.name = new_prefix + route.name[len(old_prefix) :]
        resupply_routes = (
            self.env["stock.route"]
            .with_context(active_test=False)
            .search(
                [
                    "|",
                    ("supplied_wh_id", "in", self.ids),
                    ("supplier_wh_id", "in", self.ids),
                ]
            )
        )
        for route in resupply_routes:
            supplied, supplier = route.supplied_wh_id, route.supplier_wh_id
            if not (supplied and supplier):
                continue
            route.name = self._format_resupply_routename(
                new_name if supplied in self else supplied.name,
                new_name if supplier in self else supplier.name,
            )

    def _update_rule_names(self, new_code):
        rules = (
            self.env["stock.rule"]
            .with_context(active_test=False)
            .search([("warehouse_id", "in", self.ids)])
        )
        new_prefix = "%s: " % new_code
        old_prefixes = {warehouse.id: "%s: " % warehouse.code for warehouse in self}
        by_new_name = defaultdict(list)
        for rule in rules:
            old_prefix = old_prefixes.get(rule.warehouse_id.id)
            if old_prefix and rule.name and rule.name.startswith(old_prefix):
                by_new_name[new_prefix + rule.name[len(old_prefix) :]].append(rule.id)
        Rule = self.env["stock.rule"].with_context(active_test=False)
        dbg.lifecycle.debug(
            "_update_rule_names(%s): %d rules renamed", new_code, len(by_new_name)
        )
        for name, rule_ids in by_new_name.items():
            Rule.browse(rule_ids).write({"name": name})

    def _format_rulename(self, from_loc, dest_loc, suffix):
        rulename = "%s: %s" % (self._get_normalized_code(), from_loc.name)
        if dest_loc:
            rulename += " → %s" % (dest_loc.name)
        if suffix:
            rulename += " (" + suffix + ")"
        return rulename

    def _format_routename(self, name=None, route_type=None):
        if route_type:
            name = self._get_route_name(route_type)
        if not name:
            raise ValueError("_format_routename needs either a name or a route_type")
        return "%s: %s" % (self.name, name)

    @api.model
    def _format_resupply_routename(self, supplied_name, supplier_name):
        return _(
            "%(warehouse)s: Supply Product from %(supplier)s",
            warehouse=supplied_name,
            supplier=supplier_name,
        )

    def action_view_all_routes(self):
        routes = self._get_all_routes()
        return {
            "name": _("Warehouse's Routes"),
            "domain": [("id", "in", routes.ids)],
            "res_model": "stock.route",
            "type": "ir.actions.act_window",
            "view_id": False,
            "view_mode": "list,form",
            "limit": 20,
            "context": dict(
                self.env.context,
                default_warehouse_selectable=True,
                default_warehouse_ids=self.ids,
            ),
        }
