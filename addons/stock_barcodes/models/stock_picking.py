# Copyright 2019 Sergio Teruel <sergio.teruel@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _prepare_barcode_wiz_vals(self, option_group):
        vals = {
            "picking_id": self.id,
            "res_model_id": self.env.ref("stock.model_stock_picking").id,
            "res_id": self.id,
            "picking_type_code": self.picking_type_code,
            "option_group_id": option_group.id,
            "manual_entry": option_group.manual_entry,
            "picking_mode": "picking",
        }
        if self.picking_type_id.code == "outgoing":
            vals["location_dest_id"] = self.location_dest_id.id
        elif self.picking_type_id.code == "incoming":
            vals["location_id"] = self.location_id.id

        if option_group.get_option_value("location_id", "filled_default"):
            vals["location_id"] = self.location_id.id
        if option_group.get_option_value("location_dest_id", "filled_default"):
            vals["location_dest_id"] = self.location_dest_id.id
        return vals

    def action_barcode_scan(self, option_group=False):
        option_group = option_group or self.picking_type_id.barcode_option_group_id
        wiz = self.env["wiz.stock.barcodes.read.picking"].create(
            self._prepare_barcode_wiz_vals(option_group)
        )
        wiz.fill_pending_moves()
        wiz.determine_todo_action()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock_barcodes.action_stock_barcodes_read_picking"
        )
        action["res_id"] = wiz.id
        return action

    def button_validate(self):
        put_in_pack_picks = self.filtered(
            lambda p: p.picking_type_id.barcode_option_group_id.auto_put_in_pack
            and not p.move_line_ids.result_package_id
        )
        if put_in_pack_picks:
            put_in_pack_picks.action_put_in_pack()
        if self.env.context.get("stock_barcodes_validate_picking", False):
            res = super(
                StockPicking, self.with_context(skip_backorder=True)
            ).button_validate()
        else:
            res = super().button_validate()
        if res is True and self.env.context.get("show_picking_type_action_tree", False):
            return self[:1].picking_type_id.get_action_picking_tree_ready()
        return res
