from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    spread_ids = fields.One2many("account.spread", "move_id", string="Spreads")
    spread_count = fields.Integer(compute="_compute_spread_count", string="Spread Count")

    def _compute_spread_count(self):
        for move in self:
            move.spread_count = len(move.spread_ids)

    def action_open_spreads(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "gov_account_spread_cost_revenue.account_spread_action"
        )
        action["domain"] = [("id", "in", self.spread_ids.ids)]
        action["context"] = {"default_move_line_id": False}
        return action

