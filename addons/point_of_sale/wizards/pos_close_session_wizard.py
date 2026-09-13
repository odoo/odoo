from odoo import fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class PosCloseSessionWizard(models.TransientModel):
    _name = "pos.close.session.wizard"
    _description = "Close Session Wizard"

    amount_to_balance = fields.Float(string="Amount to balance")
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="Destination account",
    )
    account_readonly = fields.Boolean(string="Destination account is readonly")
    message = fields.Text(string="Information message")

    def action_close_session(self):
        self.check_singleton()
        active_model = self.env.context.get("active_model")
        if active_model and active_model != "pos.session":
            raise UserError(self.env._("Select exactly one session to close."))
        session = self.env["pos.session"].browse(self.env.context.get("active_ids"))
        if len(session) != 1 or not session.exists():
            raise UserError(self.env._("Select exactly one session to close."))
        dbg.lifecycle.debug(
            "[wizard:close.session][session:%s] force close: balance %s on %s",
            dbg.names(session, "name"),
            self.amount_to_balance,
            dbg.rec(self.account_id),
        )
        return session.action_pos_session_closing_control(
            self.account_id,
            self.amount_to_balance,
            {
                int(payment_method_id): diff
                for payment_method_id, diff in (
                    self.env.context.get("bank_payment_method_diffs") or {}
                ).items()
            },
        )
