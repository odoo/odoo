from odoo import fields, models


class ReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    # Added new field #T7157
    return_reason = fields.Html()

    def _create_returns(self):
        """Inherited to write() the return_reason in stock.picking()
        after the creation of a new stock.picking record with its picking_type set to
        return #T7157"""
        new_picking_id, picking_type_id = super()._create_returns()
        # getting the picking_id from the returned values and then writing the
        # return_reason field in it according to return_reason in the wizard #T7157
        self.env["stock.picking"].browse(new_picking_id).write(
            {"return_reason": self.return_reason}
        )
        return (new_picking_id, picking_type_id)
