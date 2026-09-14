from odoo import Command, _, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrExpenseApproveDuplicate(models.TransientModel):
    _name = "hr.expense.approve.duplicate"
    _description = "Expense Approve Duplicate"

    expense_ids = fields.Many2many(
        comodel_name="hr.expense",
        readonly=True,
    )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if "duplicate_expense_ids" in fields:
            res["expense_ids"] = [
                Command.set(self.env.context.get("default_expense_ids", []))
            ]
        return res

    def action_approve(self):
        _debug.pipeline(
            "duplicate_wizard", outcome="approve", expenses=self.expense_ids
        )
        self.expense_ids.filtered(
            lambda expense: expense.state == "submitted"
        )._do_approve()
        return {"type": "ir.actions.act_window_close"}

    def action_refuse(self):
        _debug.pipeline("duplicate_wizard", outcome="refuse", expenses=self.expense_ids)
        self.expense_ids.filtered(
            lambda expense: expense.state == "submitted"
        )._do_refuse(_("Duplicate Expense"))
        return {"type": "ir.actions.act_window_close"}
