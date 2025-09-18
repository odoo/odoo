from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    # ------------------------------------------------------------
    # HELPER METHODS
    # ------------------------------------------------------------

    def _create_return(self):
        picking = super()._create_return()
        if len(picking.move_ids.partner_id) == 1 and picking.partner_id != picking.move_ids.partner_id:
            picking.partner_id = picking.move_ids.partner_id
        return picking

    def _prepare_move_default_values(self, return_line, new_picking):
        vals = super()._prepare_move_default_values(return_line, new_picking)
        if self.location_id.usage == "supplier":
            vals["purchase_line_id"], vals["partner_id"] = (
                return_line.move_id._get_purchase_line_and_partner_from_chain()
            )
        return vals
