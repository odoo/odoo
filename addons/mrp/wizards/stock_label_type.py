from odoo import _, fields, models


class PickingLabelType(models.TransientModel):
    _inherit = "picking.label.type"

    production_ids = fields.Many2many(comodel_name="mrp.production")

    def process(self):
        if not self.production_ids:
            return super().process()
        if self.label_type == "products":
            return self.production_ids.action_view_label_layout()
        view = self.env.ref("stock.lot_label_layout_form_picking")
        return {
            "name": _("Choose Labels Layout"),
            "type": "ir.actions.act_window",
            "res_model": "lot.label.layout",
            "views": [(view.id, "form")],
            "target": "new",
            "context": {
                "default_move_line_ids": self.production_ids.move_finished_ids.move_line_ids.ids
            },
        }
