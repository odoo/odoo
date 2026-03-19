from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    spread_id = fields.Many2one("account.spread", ondelete="set null", copy=False)

    def action_create_spread(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "gov_account_spread_cost_revenue.account_spread_invoice_wizard_action"
        )
        action["context"] = {
            "default_move_line_id": self.id,
            "default_estimated_amount": abs(self.balance),
            "default_date_start": self.move_id.invoice_date or self.move_id.date,
        }
        return action

