from odoo import _, fields, models

from ..tools import debug_log as dbg


class PickingLabelType(models.TransientModel):
    _name = "picking.label.type"
    _description = "Choose whether to print product or lot/sn labels"

    picking_ids = fields.Many2many(comodel_name="stock.picking")
    label_type = fields.Selection(
        selection=[("products", "Product Labels"), ("lots", "Lot/SN Labels")],
        string="Labels to print",
        default="products",
        required=True,
    )

    def process(self):
        if not self.picking_ids:
            return None
        dbg.logic.debug(
            "label type %s for %s", self.label_type, dbg.rec(self.picking_ids)
        )
        if self.label_type == "products":
            return self.picking_ids.action_view_label_layout()
        view = self.env.ref("stock.lot_label_layout_form_picking")
        return {
            "name": _("Choose Labels Layout"),
            "type": "ir.actions.act_window",
            "res_model": "lot.label.layout",
            "views": [(view.id, "form")],
            "target": "new",
            "context": {"default_move_line_ids": self.picking_ids.move_line_ids.ids},
        }
