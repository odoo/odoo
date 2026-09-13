from odoo import _, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    closing_return_id = fields.Many2one(
        comodel_name="account.return",
        index="btree_not_null",
        copy=False,
    )

    @_debug.perf.timed
    def action_view_tax_return(self):
        _debug.lifecycle("action_view_tax_return", records=self)
        return {
            "type": "ir.actions.act_window",
            "name": self.closing_return_id.name,
            "res_model": "account.return.check",
            "view_mode": "kanban",
            "context": {
                "active_model": "account.return",
                "active_id": self.closing_return_id.id,
                "active_ids": self.closing_return_id.ids,
                "account_return_view_id": self.env.ref(
                    "account.account_return_kanban_view"
                ).id,
            },
            "domain": [["return_id", "=", self.closing_return_id.id]],
            "views": [
                (
                    self.env.ref("account.account_return_check_kanban_view").id,
                    "kanban",
                )
            ],
        }

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        for move in self:
            if move.closing_return_id:
                _debug.logic(
                    "closing_entry_unlinked",
                    move=move,
                    tax_return=move.closing_return_id,
                )
                if len(move.closing_return_id.company_ids) == 1:
                    move.closing_return_id.message_post(
                        body=_("Closing entry deleted"),
                        message_type="comment",
                    )
                else:
                    move.closing_return_id.message_post(
                        body=_(
                            "Closing entry deleted for company %s",
                            move.closing_return_id.company_id,
                        ),
                        message_type="comment",
                    )
        return super().unlink()

    @_debug.perf.timed
    def _post_entries(self):
        _debug.lifecycle("_post_entries", records=self)
        posted_moves = super()._post_entries()
        posted_moves._update_accounts_audit_status()
        return posted_moves

    @_debug.perf.timed
    def action_draft(self):
        _debug.lifecycle("action_draft", records=self)
        posted_moves = self.filtered(lambda move: move.state == "posted")
        res = super().action_draft()
        posted_moves._update_accounts_audit_status()
        return res

    @_debug.perf.timed
    def _update_accounts_audit_status(self):
        if not self:
            return

        all_statuses = (
            self.env["account.audit.account.status"]
            .sudo()
            .search(
                [
                    ("account_id", "in", self.line_ids.account_id.ids),
                    ("status", "in", (False, "reviewed", "supervised")),
                    ("audit_id.company_ids", "in", self.company_id.ids),
                ]
            )
        )

        _debug.logic("audit_statuses_found", moves=self, statuses=all_statuses)
        if not all_statuses:
            return

        account_to_statuses = all_statuses.grouped("account_id")
        audits = all_statuses.mapped("audit_id")
        audit_id_to_dates = {
            audit.id: {"date_from": audit.date_from, "date_to": audit.date_to}
            for audit in audits
        }

        statuses_to_update = self.env["account.audit.account.status"]
        empty_status = self.env["account.audit.account.status"]

        for line in self.line_ids:
            matching_statuses = account_to_statuses.get(
                line.account_id, empty_status
            ).filtered(
                lambda status, line=line: (
                    audit_id_to_dates[status.audit_id.id]["date_from"]
                    <= line.date
                    <= audit_id_to_dates[status.audit_id.id]["date_to"]
                )
            )
            statuses_to_update |= matching_statuses

        _debug.pipeline(
            "audit_statuses_reset",
            moves=self,
            audits=audits,
            statuses=statuses_to_update,
        )
        if statuses_to_update:
            statuses_to_update.status = "todo"
