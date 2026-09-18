from odoo import api, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    @api.depends("default_location_dest_id")
    def _compute_print_label(self):
        super()._compute_print_label()
        for picking_type in self:
            if (
                picking_type.code == "internal"
                and picking_type.default_location_dest_id.is_subcontract()
            ):
                picking_type.print_label = True
