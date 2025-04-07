from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_landed_cost_picking_ids(self):
        self.ensure_one()
        landed_cost_picking_ids = super()._get_landed_cost_picking_ids()
        landed_cost_picking_ids |= self.line_ids.purchase_order_id.picking_ids.filtered(lambda p: any(m.is_subcontract and m.state == 'done' for m in p.move_ids))

        return landed_cost_picking_ids
