from odoo.exceptions import UserError

from odoo import _, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _check_move_for_group_ungroup_lines_by_tax(self):
        # Extends account.move
        super()._check_move_for_group_ungroup_lines_by_tax()
        if any(line.purchase_order_id for line in self.line_ids):
            raise UserError(_("You can only (un)group lines of an invoice not linked to a purchase order"))
