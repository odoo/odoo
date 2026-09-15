from odoo import models
from odoo.exceptions import UserError

from . import approval_trace as trace


class MixinApprovalLifecycle(models.AbstractModel):
    _name = "mixin.approval.lifecycle"
    _inherit = ["mixin.approval", "mixin.lifecycle"]
    _description = "Lifecycle Confirmed Through Approval"

    def action_confirm(self):
        self._check_confirm_allowed()
        ready, need_approval = self._split_by_approval()
        if ready:
            super(MixinApprovalLifecycle, ready).action_confirm()
        if not need_approval:
            return True
        trace.MIXIN.note(
            "confirm_needs_approval",
            records=need_approval,
            confirmed=len(ready),
        )
        if len(self) == 1:
            return need_approval.action_create_approval_request()
        for record in need_approval:
            record.action_create_approval_request()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "warning",
                "title": self.env._("Approval Required"),
                "message": self.env._(
                    "%(sent)s sent for approval; %(confirmed)s confirmed.",
                    sent=len(need_approval),
                    confirmed=len(ready),
                ),
                "sticky": False,
            },
        }

    def _split_by_approval(self):
        ready = self.browse()
        need_approval = self.browse()
        for record in self:
            if not record.approval_request_id:
                if record.approval_required:
                    need_approval |= record
                else:
                    ready |= record
                continue
            state = record.approval_state
            if state == "approved":
                ready |= record
            elif state in ("new", "pending"):
                raise UserError(
                    self.env._(
                        "%(name)s is waiting for approval.",
                        name=record.display_name,
                    )
                )
            else:
                raise UserError(
                    self.env._(
                        "The approval of %(name)s was refused or cancelled. "
                        "Reset it to draft to ask again.",
                        name=record.display_name,
                    )
                )
        return ready, need_approval

    def _on_approval_approved(self):
        super()._on_approval_approved()
        if self.state == "draft":
            self.sudo().action_confirm()

    def action_cancel(self):
        for record in self.filtered(
            lambda r: r.approval_request_id and r.approval_state in ("new", "pending")
        ):
            if record.approval_request_id._refuse_cascade():
                record.message_post(
                    body=self.env._(
                        "Approval request refused: the document was cancelled."
                    ),
                    message_type="notification",
                )
        return super().action_cancel()

    def action_draft(self):
        result = super().action_draft()
        self._clear_refused_approval_link()
        return result
