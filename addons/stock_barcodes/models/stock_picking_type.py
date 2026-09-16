# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    barcode_option_group_id = fields.Many2one(
        comodel_name="stock.barcodes.option.group"
    )

    new_picking_barcode_option_group_id = fields.Many2one(
        comodel_name="stock.barcodes.option.group",
        help="This Barcode Option Group will be selected when clicking the 'New' button"
        " in an operation type. It will be used to create a non planned picking.",
    )

    def action_barcode_scan(self):
        vals = {
            "res_model_id": self.env.ref("stock.model_stock_picking_type").id,
            "res_id": self.id,
            "picking_type_code": self.code,
            "option_group_id": self.barcode_option_group_id.id,
            "manual_entry": self.barcode_option_group_id.manual_entry,
            "picking_mode": "picking",
        }
        if self.code == "outgoing":
            vals["location_dest_id"] = (
                self.default_location_dest_id.id
                or self.env.ref("stock.stock_location_customers").id
            )
        elif self.code == "incoming":
            vals["location_id"] = (
                self.default_location_src_id.id
                or self.env.ref("stock.stock_location_suppliers").id
            )
        if self.barcode_option_group_id.get_option_value(
            "location_id", "filled_default"
        ):
            vals["location_id"] = self.default_location_src_id.id
        if self.barcode_option_group_id.get_option_value(
            "location_dest_id", "filled_default"
        ):
            vals["location_dest_id"] = self.default_location_dest_id.id
        wiz = self.env["wiz.stock.barcodes.read.picking"].create(vals)
        wiz.fill_pending_moves()
        wiz.determine_todo_action()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock_barcodes.action_stock_barcodes_read_picking"
        )
        action["res_id"] = wiz.id
        return action

    def action_barcode_new_picking(self):
        self.ensure_one()
        picking = (
            self.env["stock.picking"]
            .with_context(default_immediate_transfer=True)
            .create(
                {
                    "picking_type_id": self.id,
                    "location_id": self.default_location_src_id.id,
                    "location_dest_id": self.default_location_dest_id.id,
                }
            )
        )
        option_group = self.new_picking_barcode_option_group_id
        return picking.action_barcode_scan(option_group=option_group)
