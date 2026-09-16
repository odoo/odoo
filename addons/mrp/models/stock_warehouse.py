from odoo import Command, _, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    manufacture_to_resupply = fields.Boolean(
        string="Manufacture to Resupply",
        compute="_compute_manufacture_to_resupply",
        inverse="_inverse_manufacture_to_resupply",
        default=True,
        help="When products are manufactured, they can be manufactured in this warehouse.",
    )
    manufacture_pull_id = fields.Many2one(
        comodel_name="stock.rule",
        string="Manufacture Rule",
        copy=False,
    )
    manufacture_mto_pull_id = fields.Many2one(
        comodel_name="stock.rule",
        string="Manufacture MTO Rule",
        copy=False,
    )
    pbm_mto_pull_id = fields.Many2one(
        comodel_name="stock.rule",
        string="Picking Before Manufacturing MTO Rule",
        copy=False,
    )
    manu_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Manufacturing Operation Type",
        copy=False,
        domain="[('code', '=', 'mrp_operation'), ('company_id', '=', company_id)]",
        check_company=True,
    )

    pbm_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Picking Before Manufacturing Operation Type",
        copy=False,
        check_company=True,
    )
    sam_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Stock After Manufacturing Operation Type",
        copy=False,
        check_company=True,
    )

    manufacture_steps = fields.Selection(
        selection=[
            ("mrp_one_step", "Manufacture (1 step)"),
            ("pbm", "Pick components then manufacture (2 steps)"),
            ("pbm_sam", "Pick components, manufacture, then store products (3 steps)"),
        ],
        string="Manufacture",
        default="mrp_one_step",
        required=True,
        help="1 Step: Consume components from stock and produce.\n\
              2 Steps: Pick components from stock and then produce.\n\
              3 Steps: Pick components from stock, produce, and then move final product(s) from production area to stock.",
    )

    pbm_route_id = fields.Many2one(
        comodel_name="stock.route",
        string="Picking Before Manufacturing Route",
        copy=False,
        ondelete="restrict",
    )

    pbm_loc_id = fields.Many2one(
        comodel_name="stock.location",
        string="Picking before Manufacturing Location",
        copy=False,
        check_company=True,
    )
    sam_loc_id = fields.Many2one(
        comodel_name="stock.location",
        string="Stock after Manufacturing Location",
        copy=False,
        check_company=True,
    )

    @api.depends("manufacture_pull_id")
    def _compute_manufacture_to_resupply(self):
        for warehouse in self:
            manufacture_route = warehouse.manufacture_pull_id.route_id
            warehouse.manufacture_to_resupply = (
                warehouse.id in manufacture_route.warehouse_ids.ids
            )

    def _inverse_manufacture_to_resupply(self):
        without_pull = self.filtered(lambda wh: not wh.manufacture_pull_id.route_id)
        rules_by_warehouse = {}
        if without_pull:
            rules_by_warehouse = (
                self.env["stock.rule"]
                .search(
                    [
                        ("action", "=", "manufacture"),
                        ("warehouse_id", "in", without_pull.ids),
                    ]
                )
                .grouped("warehouse_id")
            )
        for warehouse in self:
            manufacture_route = warehouse.manufacture_pull_id.route_id
            if not manufacture_route:
                manufacture_route = rules_by_warehouse.get(
                    warehouse, self.env["stock.rule"]
                ).route_id
            if not manufacture_route:
                _debug.logic("manufacture_route_absent", warehouse=warehouse.id)
                continue
            _debug.lifecycle(
                "manufacture_resupply_set",
                warehouse=warehouse.id,
                route=manufacture_route.id,
                enabled=warehouse.manufacture_to_resupply,
            )
            if warehouse.manufacture_to_resupply:
                manufacture_route.warehouse_ids = [Command.link(warehouse.id)]
            else:
                manufacture_route.warehouse_ids = [Command.unlink(warehouse.id)]

    def _create_or_update_route(self):
        manufacture_route = self._get_or_create_global_route(
            "mrp.route_warehouse0_manufacture", _("Manufacture")
        )
        for warehouse in self:
            if warehouse.manufacture_to_resupply:
                manufacture_route.warehouse_ids = [Command.link(warehouse.id)]
        return super()._create_or_update_route()

    def _prepare_rule_routings(self):
        result = super()._prepare_rule_routings()
        production_location_id = self._get_production_location()
        for warehouse in self:
            result[warehouse.id].update(
                {
                    "mrp_one_step": [],
                    "pbm": [
                        self.Routing(
                            warehouse.lot_stock_id,
                            warehouse.pbm_loc_id,
                            warehouse.pbm_type_id,
                            "pull",
                        ),
                        self.Routing(
                            warehouse.pbm_loc_id,
                            production_location_id,
                            warehouse.manu_type_id,
                            "pull",
                        ),
                    ],
                    "pbm_sam": [
                        self.Routing(
                            warehouse.lot_stock_id,
                            warehouse.pbm_loc_id,
                            warehouse.pbm_type_id,
                            "pull",
                        ),
                        self.Routing(
                            warehouse.pbm_loc_id,
                            production_location_id,
                            warehouse.manu_type_id,
                            "pull",
                        ),
                        self.Routing(
                            warehouse.sam_loc_id,
                            warehouse.lot_stock_id,
                            warehouse.sam_type_id,
                            "push",
                        ),
                    ],
                }
            )
            result[warehouse.id].update(
                warehouse._prepare_internal_reception_routings()
            )
        return result

    def _prepare_route_vals(self):
        routes = super()._prepare_route_vals()
        routes.update(
            {
                "pbm_route_id": {
                    "routing_key": self.manufacture_steps,
                    "depends": ["manufacture_steps", "manufacture_to_resupply"],
                    "route_update_values": {
                        "name": self._format_routename(
                            route_type=self.manufacture_steps
                        ),
                        "active": self.manufacture_steps != "mrp_one_step",
                    },
                    "route_create_values": {
                        "product_categ_selectable": True,
                        "warehouse_selectable": True,
                        "product_selectable": False,
                        "company_id": self.company_id.id,
                        "sequence": 10,
                    },
                    "rules_values": {
                        "active": True,
                    },
                }
            }
        )
        routes.update(self._prepare_receive_route_vals("manufacture_to_resupply"))
        return routes

    def _get_fields_route_trigger(self):
        return super()._get_fields_route_trigger() | {
            "manufacture_steps",
            "manufacture_to_resupply",
        }

    def _get_global_rule_fields(self):
        return super()._get_global_rule_fields() | {
            "manufacture_pull_id",
            "manufacture_mto_pull_id",
            "pbm_mto_pull_id",
        }

    def _get_route_name(self, route_type):
        names = {
            "mrp_one_step": _("Manufacture (1 step)"),
            "pbm": _("Pick components and then manufacture"),
            "pbm_sam": _(
                "Pick components, manufacture and then store products (3 steps)"
            ),
        }
        if route_type in names:
            return names[route_type]
        else:
            return super()._get_route_name(route_type)

    def _prepare_global_route_rule_vals(self):
        rules = super()._prepare_global_route_rule_vals()
        production_location = self._get_production_location()
        rules.update(
            {
                "manufacture_pull_id": {
                    "depends": ["manufacture_steps", "manufacture_to_resupply"],
                    "create_values": {
                        "action": "manufacture",
                        "procure_method": "make_to_order",
                        "company_id": self.company_id.id,
                        "picking_type_id": self.manu_type_id.id,
                        "route_id": self._get_or_create_global_route(
                            "mrp.route_warehouse0_manufacture", _("Manufacture")
                        ).id,
                    },
                    "update_values": {
                        "active": self.manufacture_to_resupply,
                        "name": self._format_rulename(
                            self.lot_stock_id, False, "Production"
                        ),
                        "location_dest_id": self.lot_stock_id.id,
                        "propagate_cancel": self.manufacture_steps == "pbm_sam",
                    },
                },
                "manufacture_mto_pull_id": {
                    "depends": ["manufacture_steps", "manufacture_to_resupply"],
                    "create_values": {
                        "procure_method": "make_to_order",
                        "company_id": self.company_id.id,
                        "action": "pull",
                        "auto": "manual",
                        "route_id": self._get_or_create_global_route(
                            "stock.route_warehouse0_mto", _("Replenish on Order (MTO)")
                        ).id,
                        "location_dest_id": production_location.id,
                        "location_src_id": self.lot_stock_id.id,
                        "picking_type_id": self.manu_type_id.id,
                    },
                    "update_values": {
                        "name": self._format_rulename(
                            self.lot_stock_id, production_location, "MTO"
                        ),
                        "active": self.manufacture_to_resupply,
                    },
                },
                "pbm_mto_pull_id": {
                    "depends": ["manufacture_steps", "manufacture_to_resupply"],
                    "create_values": {
                        "procure_method": "make_to_order",
                        "company_id": self.company_id.id,
                        "action": "pull",
                        "auto": "manual",
                        "route_id": self._get_or_create_global_route(
                            "stock.route_warehouse0_mto", _("Replenish on Order (MTO)")
                        ).id,
                        "name": self._format_rulename(
                            self.lot_stock_id, self.pbm_loc_id, "MTO"
                        ),
                        "location_dest_id": self.pbm_loc_id.id,
                        "location_src_id": self.lot_stock_id.id,
                        "picking_type_id": self.pbm_type_id.id,
                    },
                    "update_values": {
                        "active": self.manufacture_steps != "mrp_one_step"
                        and self.manufacture_to_resupply,
                    },
                },
            }
        )
        return rules

    def _get_fields_location_step(self):
        return super()._get_fields_location_step() + ["manufacture_steps"]

    def _prepare_sub_location_vals(self, vals, code=False):
        values = super()._prepare_sub_location_vals(vals, code=code)
        def_values = self._get_location_step_values(vals, code)
        manufacture_steps = def_values["manufacture_steps"]
        code = def_values["code"]
        values.update(
            {
                "pbm_loc_id": {
                    "name": _("Pre-Production"),
                    "active": manufacture_steps in ("pbm", "pbm_sam"),
                    "usage": "internal",
                    "barcode": code + "PREPRODUCTION",
                },
                "sam_loc_id": {
                    "name": _("Post-Production"),
                    "active": manufacture_steps == "pbm_sam",
                    "usage": "internal",
                    "barcode": code + "POSTPRODUCTION",
                },
            }
        )
        return values

    def _get_picking_type_codes(self):
        codes = super()._get_picking_type_codes()
        codes.update({"pbm_type_id": "PC", "manu_type_id": "MO", "sam_type_id": "SFP"})
        return codes

    def _get_picking_type_barcode_suffixes(self, codes=None):
        suffixes = super()._get_picking_type_barcode_suffixes(codes)
        suffixes["manu_type_id"] = "MANUF"
        return suffixes

    def _prepare_picking_type_create_vals(self):
        data = super()._prepare_picking_type_create_vals()
        data.update(
            {
                "pbm_type_id": {
                    "name": _("Pick Components"),
                    "code": "internal",
                    "use_create_lots": True,
                    "use_existing_lots": True,
                    "default_location_src_id": self.lot_stock_id.id,
                    "default_location_dest_id": self.pbm_loc_id.id,
                    "company_id": self.company_id.id,
                },
                "sam_type_id": {
                    "name": _("Store Finished Product"),
                    "code": "internal",
                    "use_create_lots": True,
                    "use_existing_lots": True,
                    "default_location_src_id": self.sam_loc_id.id,
                    "default_location_dest_id": self.lot_stock_id.id,
                    "company_id": self.company_id.id,
                },
                "manu_type_id": {
                    "name": _("Manufacturing"),
                    "code": "mrp_operation",
                    "use_create_lots": True,
                    "use_existing_lots": True,
                    "company_id": self.company_id.id,
                },
            }
        )
        return data

    def _prepare_picking_type_update_vals(self):
        data = super()._prepare_picking_type_update_vals()
        data.update(
            {
                "pbm_type_id": {
                    "active": self.manufacture_to_resupply
                    and self.manufacture_steps in ("pbm", "pbm_sam")
                    and self.active,
                },
                "sam_type_id": {
                    "active": self.manufacture_to_resupply
                    and self.manufacture_steps == "pbm_sam"
                    and self.active,
                },
                "manu_type_id": {
                    "active": self.manufacture_to_resupply and self.active,
                    "default_location_src_id": (
                        self.manufacture_steps in ("pbm", "pbm_sam")
                        and self.pbm_loc_id.id
                    )
                    or self.lot_stock_id.id,
                    "default_location_dest_id": (
                        self.manufacture_steps == "pbm_sam" and self.sam_loc_id.id
                    )
                    or self.lot_stock_id.id,
                },
            }
        )
        return data

    def _create_missing_locations(self, vals):
        super()._create_missing_locations(vals)
        companies_with_production_location = {
            company
            for [company] in self.env["stock.location"]._read_group(
                [
                    ("usage", "=", "production"),
                    ("company_id", "in", self.company_id.ids),
                ],
                ["company_id"],
            )
        }
        for company_id in self.company_id:
            if company_id not in companies_with_production_location:
                company_id._create_production_location()

    def write(self, vals):
        if any(
            field in vals for field in ("manufacture_steps", "manufacture_to_resupply")
        ):
            _debug.lifecycle(
                "manufacture_steps_written", warehouses=self, fields=list(vals)
            )
            for warehouse in self:
                warehouse._update_location_manufacture(
                    vals.get("manufacture_steps", warehouse.manufacture_steps)
                )
        return super().write(vals)

    def _get_all_routes(self):
        routes = super()._get_all_routes()
        routes |= (
            self.filtered(
                lambda wh: (
                    wh.manufacture_to_resupply
                    and wh.manufacture_pull_id
                    and wh.manufacture_pull_id.route_id
                )
            )
            .mapped("manufacture_pull_id")
            .mapped("route_id")
        )
        return routes

    def _update_location_manufacture(self, new_manufacture_step):
        _debug.pipeline(
            "manufacture_locations_toggled",
            warehouses=self,
            step=new_manufacture_step,
        )
        self.mapped("pbm_loc_id").write(
            {"active": new_manufacture_step != "mrp_one_step"}
        )
        self.mapped("sam_loc_id").write({"active": new_manufacture_step == "pbm_sam"})
