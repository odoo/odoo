from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_related_pickings(self):
        return self.invoice_line_ids.purchase_line_id.move_ids.picking_id or super()._get_related_pickings()
