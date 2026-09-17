from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    # FIELDS
    allow_maintenance = fields.Boolean(
        help="Equipment can be sent out for maintenance and received back through dedicated operations."
    )
    wh_maintenance_stock_loc_id = fields.Many2one(
        comodel_name="stock.location",
        string="Maintenance Location",
        copy=False,
        check_company=True,
    )
    maintenance_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Maintenance Type",
        copy=False,
        check_company=True,
    )
    maintenance_return_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Maintenance Return Type",
        copy=False,
        check_company=True,
    )

    # CRUD METHODS
    def write(self, vals):
        res = super().write(vals)
        if "allow_maintenance" in vals:
            _debug.lifecycle(
                "warehouse_maintenance_toggled",
                warehouses=self,
                allow=vals["allow_maintenance"],
            )
            for warehouse in self:
                warehouse._create_missing_locations(vals)
                warehouse.wh_maintenance_stock_loc_id.active = (
                    warehouse.allow_maintenance
                )
                picking_type_vals = warehouse._create_or_update_picking_types()
                if picking_type_vals:
                    warehouse.write(picking_type_vals)
        return res

    # HELPER METHODS
    def _get_fields_location_step(self):
        return [*super()._get_fields_location_step(), "allow_maintenance"]

    def _prepare_sub_location_vals(self, vals, code=False):
        sub_locations = super()._prepare_sub_location_vals(vals, code=code)
        def_values = self._get_location_step_values(vals, code)
        sub_locations["wh_maintenance_stock_loc_id"] = {
            "name": self.env._("Maintenance"),
            "active": def_values["allow_maintenance"],
            "usage": "internal",
            "barcode": def_values["code"] + "-MNT",
            "maintenance_location": True,
        }
        return sub_locations

    def _get_picking_type_codes(self):
        codes = super()._get_picking_type_codes()
        codes.update(
            {"maintenance_type_id": "MNT", "maintenance_return_type_id": "MRTN"}
        )
        return codes

    def _get_picking_type_barcode_suffixes(self, codes=None):
        suffixes = super()._get_picking_type_barcode_suffixes(codes)
        suffixes.update(
            {"maintenance_type_id": "-MNT", "maintenance_return_type_id": "-MRTN"}
        )
        return suffixes

    def _prepare_picking_type_create_vals(self):
        data = super()._prepare_picking_type_create_vals()
        common = {
            "code": "internal",
            "use_create_lots": False,
            "use_existing_lots": True,
            "company_id": self.company_id.id,
        }
        data["maintenance_type_id"] = {
            **common,
            "name": self.env._("Maintenance"),
            "default_location_src_id": self.lot_stock_id.id,
            "default_location_dest_id": self.wh_maintenance_stock_loc_id.id,
        }
        data["maintenance_return_type_id"] = {
            **common,
            "name": self.env._("Maintenance Return"),
            "default_location_src_id": self.wh_maintenance_stock_loc_id.id,
            "default_location_dest_id": self.lot_stock_id.id,
        }
        return data

    def _prepare_picking_type_update_vals(self):
        data = super()._prepare_picking_type_update_vals()
        active = self.allow_maintenance and self.active
        data["maintenance_type_id"] = {
            "active": active,
            "default_location_src_id": self.lot_stock_id.id,
            "default_location_dest_id": self.wh_maintenance_stock_loc_id.id,
        }
        data["maintenance_return_type_id"] = {
            "active": active,
            "default_location_src_id": self.wh_maintenance_stock_loc_id.id,
            "default_location_dest_id": self.lot_stock_id.id,
        }
        return data

    def _create_or_update_picking_types(self):
        self._create_missing_locations({})
        warehouse_data = super()._create_or_update_picking_types()
        sending = warehouse_data.get("maintenance_type_id")
        returning = warehouse_data.get("maintenance_return_type_id")
        if sending and returning:
            PickingType = self.env["stock.picking.type"]
            PickingType.browse(sending).return_picking_type_id = returning
            PickingType.browse(returning).return_picking_type_id = sending
        return warehouse_data
