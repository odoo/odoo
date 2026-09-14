from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    repair_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Repair Operation Type",
        copy=False,
        check_company=True,
    )
    repair_mto_pull_id = fields.Many2one(
        comodel_name="stock.rule",
        string="Repair MTO Rule",
        copy=False,
    )

    def _get_picking_type_codes(self):
        codes = super()._get_picking_type_codes()
        codes["repair_type_id"] = "RO"
        return codes

    def _prepare_picking_type_create_vals(self):
        _debug.lifecycle("repair_picking_type_vals", warehouses=self)
        data = super()._prepare_picking_type_create_vals()
        prod_location = self._get_production_location()
        scrap_location = self.env["stock.location"].search(
            [
                ("usage", "=", "inventory"),
                ("company_id", "in", [self.company_id.id, False]),
            ],
            limit=1,
        )
        if not scrap_location:
            raise UserError(_("No location of type Inventory Loss found"))

        data.update(
            {
                "repair_type_id": {
                    "name": _("Repairs"),
                    "code": "repair_operation",
                    "default_location_src_id": self.lot_stock_id.id,
                    "default_location_dest_id": prod_location.id,
                    "default_remove_location_dest_id": scrap_location.id,
                    "default_recycle_location_dest_id": self.lot_stock_id.id,
                    "company_id": self.company_id.id,
                    "use_create_lots": True,
                    "use_existing_lots": True,
                },
            }
        )
        return data

    def _prepare_picking_type_update_vals(self):
        data = super()._prepare_picking_type_update_vals()
        data.update(
            {
                "repair_type_id": {
                    "active": self.active,
                },
            }
        )
        return data

    def _create_missing_locations(self, vals):
        _debug.lifecycle("repair_locations_create", warehouses=self)
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

    def _get_fields_route_trigger(self):
        return super()._get_fields_route_trigger() | {"repair_type_id"}

    def _get_global_rule_fields(self):
        return super()._get_global_rule_fields() | {"repair_mto_pull_id"}

    def _prepare_global_route_rule_vals(self):
        rules = super()._prepare_global_route_rule_vals()
        production_location = self._get_production_location()
        rules.update(
            {
                "repair_mto_pull_id": {
                    "depends": ["repair_type_id"],
                    "create_values": {
                        "procure_method": "make_to_order",
                        "company_id": self.company_id.id,
                        "action": "pull",
                        "auto": "manual",
                        "route_id": self._get_or_create_global_route(
                            "stock.route_warehouse0_mto", _("Replenish on Order (MTO)")
                        ).id,
                        "location_dest_id": self.repair_type_id.default_location_dest_id.id,
                        "location_src_id": self.repair_type_id.default_location_src_id.id,
                        "picking_type_id": self.repair_type_id.id,
                    },
                    "update_values": {
                        "name": self._format_rulename(
                            self.lot_stock_id, production_location, "MTO"
                        ),
                        "active": True,
                    },
                },
            }
        )
        return rules
