from odoo import _, api, fields, models
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    subcontracting_to_resupply = fields.Boolean(
        string="Resupply Subcontractors",
        default=True,
    )
    subcontracting_mto_pull_id = fields.Many2one(
        comodel_name="stock.rule",
        string="Subcontracting MTO Rule",
        copy=False,
    )
    subcontracting_pull_id = fields.Many2one(
        comodel_name="stock.rule",
        string="Subcontracting MTS Rule",
        copy=False,
    )

    subcontracting_route_id = fields.Many2one(
        comodel_name="stock.route",
        string="Resupply Subcontractor",
        copy=False,
        ondelete="restrict",
    )

    subcontracting_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Subcontracting Operation Type",
        copy=False,
        domain=[("code", "=", "mrp_operation")],
    )
    subcontracting_resupply_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Subcontracting Resupply Operation Type",
        copy=False,
        domain=[("code", "=", "internal")],
    )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        if any(vals.get("subcontracting_to_resupply", False) for vals in vals_list):
            res._update_global_route_resupply_subcontractor()
        return res

    def write(self, vals):
        res = super().write(vals)
        if "subcontracting_to_resupply" in vals or "active" in vals:
            if "subcontracting_to_resupply" in vals:
                self._update_resupply_rules()
            self._update_global_route_resupply_subcontractor()
        return res

    def _prepare_rule_routings(self):
        result = super()._prepare_rule_routings()
        subcontract_location_id = self._get_subcontracting_location()
        for warehouse in self:
            result[warehouse.id].update(
                {
                    "subcontract": [
                        self.Routing(
                            warehouse.lot_stock_id,
                            subcontract_location_id,
                            warehouse.subcontracting_resupply_type_id,
                            "pull",
                        ),
                    ]
                }
            )
        return result

    def _update_global_route_resupply_subcontractor(self):
        route_id = self._get_or_create_global_route(
            "mrp_subcontracting.route_resupply_subcontractor_mto",
            _("Resupply Subcontractor on Order"),
        )
        if not route_id.sudo().rule_ids.filtered(lambda r: r.active):
            route_id.active = False
        else:
            route_id.active = True
            self.route_ids = [Command.link(route_id.id)]

    def _prepare_route_vals(self):
        routes = super()._prepare_route_vals()
        routes.update(
            {
                "subcontracting_route_id": {
                    "routing_key": "subcontract",
                    "depends": ["subcontracting_to_resupply"],
                    "route_create_values": {
                        "product_categ_selectable": False,
                        "warehouse_selectable": True,
                        "product_selectable": False,
                        "company_id": self.company_id.id,
                        "sequence": 10,
                        "name": self._format_routename(
                            name=_("Resupply Subcontractor")
                        ),
                    },
                    "route_update_values": {
                        "active": self.subcontracting_to_resupply,
                    },
                    "rules_values": {
                        "active": self.subcontracting_to_resupply,
                    },
                }
            }
        )
        return routes

    def _prepare_global_route_rule_vals(self):
        rules = super()._prepare_global_route_rule_vals()
        subcontract_location_id = self._get_subcontracting_location()
        production_location_id = self._get_production_location()
        rules.update(
            {
                "subcontracting_mto_pull_id": {
                    "depends": ["subcontracting_to_resupply"],
                    "create_values": {
                        "procure_method": "make_to_order",
                        "company_id": self.company_id.id,
                        "action": "pull",
                        "auto": "manual",
                        "route_id": self._get_or_create_global_route(
                            "stock.route_warehouse0_mto", _("Replenish on Order (MTO)")
                        ).id,
                        "name": self._format_rulename(
                            self.lot_stock_id, subcontract_location_id, "MTO"
                        ),
                        "location_dest_id": subcontract_location_id.id,
                        "location_src_id": self.lot_stock_id.id,
                        "picking_type_id": self.subcontracting_resupply_type_id.id,
                    },
                    "update_values": {"active": self.subcontracting_to_resupply},
                },
                "subcontracting_pull_id": {
                    "depends": ["subcontracting_to_resupply"],
                    "create_values": {
                        "procure_method": "make_to_order",
                        "company_id": self.company_id.id,
                        "action": "pull",
                        "auto": "manual",
                        "route_id": self._get_or_create_global_route(
                            "mrp_subcontracting.route_resupply_subcontractor_mto",
                            _("Resupply Subcontractor on Order"),
                        ).id,
                        "name": self._format_rulename(
                            subcontract_location_id, production_location_id, False
                        ),
                        "location_dest_id": production_location_id.id,
                        "location_src_id": subcontract_location_id.id,
                        "picking_type_id": self.subcontracting_resupply_type_id.id,
                    },
                    "update_values": {"active": self.subcontracting_to_resupply},
                },
            }
        )
        return rules

    def _get_fields_route_trigger(self):
        return super()._get_fields_route_trigger() | {"subcontracting_to_resupply"}

    def _get_global_rule_fields(self):
        return super()._get_global_rule_fields() | {
            "subcontracting_pull_id",
            "subcontracting_mto_pull_id",
        }

    def _prepare_picking_type_create_vals(self):
        data = super()._prepare_picking_type_create_vals()
        data.update(
            {
                "subcontracting_type_id": {
                    "name": _("Subcontracting"),
                    "code": "mrp_operation",
                    "use_create_components_lots": True,
                    "company_id": self.company_id.id,
                },
                "subcontracting_resupply_type_id": {
                    "name": _("Resupply Subcontractor"),
                    "code": "internal",
                    "use_create_lots": False,
                    "use_existing_lots": True,
                    "default_location_dest_id": self._get_subcontracting_location().id,
                    "print_label": True,
                    "company_id": self.company_id.id,
                },
            }
        )
        return data

    def _get_picking_type_codes(self):
        codes = super()._get_picking_type_codes()
        code = self._get_normalized_code()
        count = self.env["ir.sequence"].search_count(
            [("prefix", "=like", code + "/SBC%/%")]
        )
        codes.update(
            {
                "subcontracting_type_id": ("SBC" + str(count)) if count else "SBC",
                "subcontracting_resupply_type_id": ("RES" + str(count))
                if count
                else "RES",
            }
        )
        return codes

    def _get_picking_type_barcode_suffixes(self, codes=None):
        suffixes = super()._get_picking_type_barcode_suffixes(codes)
        suffixes["subcontracting_resupply_type_id"] = "RESUP"
        return suffixes

    def _prepare_picking_type_update_vals(self):
        data = super()._prepare_picking_type_update_vals()
        subcontract_location_id = self._get_subcontracting_location()
        production_location_id = self._get_production_location()
        data.update(
            {
                "subcontracting_type_id": {
                    "active": False,
                    "default_location_src_id": subcontract_location_id.id,
                    "default_location_dest_id": production_location_id.id,
                },
                "subcontracting_resupply_type_id": {
                    "default_location_src_id": self.lot_stock_id.id,
                    "default_location_dest_id": subcontract_location_id.id,
                    "active": self.subcontracting_to_resupply and self.active,
                },
            }
        )
        return data

    def _get_subcontracting_location(self):
        return self.company_id.subcontracting_location_id

    def _get_subcontracting_locations(self):
        return self.company_id.subcontracting_location_id.child_internal_location_ids

    def _update_resupply_rules(self):
        subcontracting_locations = self._get_subcontracting_locations()
        warehouses_to_resupply = self.filtered(
            lambda w: w.subcontracting_to_resupply and w.active
        )
        if warehouses_to_resupply:
            self.env["stock.rule"].with_context(active_test=False).search(
                [
                    "&",
                    (
                        "picking_type_id",
                        "in",
                        warehouses_to_resupply.subcontracting_resupply_type_id.ids,
                    ),
                    "|",
                    ("location_src_id", "in", subcontracting_locations.ids),
                    ("location_dest_id", "in", subcontracting_locations.ids),
                ]
            ).action_unarchive()

        warehouses_not_to_resupply = self - warehouses_to_resupply
        if warehouses_not_to_resupply:
            self.env["stock.rule"].search(
                [
                    "&",
                    (
                        "picking_type_id",
                        "in",
                        warehouses_not_to_resupply.subcontracting_resupply_type_id.ids,
                    ),
                    "|",
                    ("location_src_id", "in", subcontracting_locations.ids),
                    ("location_dest_id", "in", subcontracting_locations.ids),
                ]
            ).action_archive()
