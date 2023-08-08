# Copyright 2022, Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def action_pos_session_closing_control(self):

        amove_search = self.env["account.move"].search(
            [
                ("state", "=", "draft"),
                ("move_type", "=", "out_invoice"),
                ("amount_total", "=", 0.00),
            ]
        )
        amove_search.unlink()
        return super().action_pos_session_closing_control()

    def action_open_reconcile(self):
        # Open reconciliation view for this account
        # action_context = {"show_mode_selector": False, "mode": "accounts", "account_ids": [self.id]}
        default_operating_unit_id = self.user_id.default_operating_unit_id.id
        action_context = {
            "default_operating_unit_id": default_operating_unit_id,
        }
        return {
            "type": "ir.actions.client",
            "tag": "manual_reconciliation_view",
            "context": action_context,
        }
