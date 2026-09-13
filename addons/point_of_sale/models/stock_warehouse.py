from odoo import _, api, fields, models

from ..tools import debug_log as dbg


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    pos_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Point of Sale Operation Type",
        copy=False,
    )

    def _prepare_picking_type_update_vals(self):
        picking_type_update_values = super()._prepare_picking_type_update_vals()
        picking_type_update_values.update(
            {"pos_type_id": {"default_location_src_id": self.lot_stock_id.id}}
        )
        return picking_type_update_values

    def _get_picking_type_codes(self):
        codes = super()._get_picking_type_codes()
        codes["pos_type_id"] = "POS"
        return codes

    def _prepare_picking_type_create_vals(self):
        picking_type_create_values = super()._prepare_picking_type_create_vals()
        picking_type_create_values.update(
            {
                "pos_type_id": {
                    "name": _("PoS Orders"),
                    "code": "outgoing",
                    "default_location_src_id": self.lot_stock_id.id,
                    "default_location_dest_id": self.env.ref(
                        "stock.stock_location_customers"
                    ).id,
                    "company_id": self.company_id.id,
                }
            }
        )
        return picking_type_create_values

    @api.model
    def _create_missing_pos_picking_types(self):
        warehouses = self.env["stock.warehouse"].search([("pos_type_id", "=", False)])
        dbg.lifecycle.debug(
            "warehouses missing a POS picking type: %s", dbg.rec(warehouses)
        )
        for warehouse in warehouses:
            new_vals = warehouse._create_or_update_picking_types()
            warehouse.write(new_vals)
