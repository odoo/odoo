from odoo import models
from odoo.exceptions import UserError

from . import approval_trace as trace


class MixinApprovalLifecycle(models.AbstractModel):
    _name = "mixin.approval.lifecycle"
    _inherit = ["mixin.approval", "mixin.lifecycle"]
    _description = "Lifecycle Confirmed Through Approval"

    def action_confirm(self):
        self._check_confirm_allowed()
        return self._confirm_through_approval(lambda records: super().action_confirm())

    def _confirm_through_approval(self, confirm):
        ready, need_approval = self._split_by_approval()
        result = confirm(ready) if ready else True
        if not need_approval:
            return result
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
            state = record.approval_request_id and record.approval_state
            if state in ("new", "pending"):
                trace.REFUSAL.event("confirm_approval_pending", record=record)
                raise UserError(
                    self.env._(
                        "%(name)s is pending approval: wait for the decision, "
                        "or ask an approver to refuse it so the document can change.",
                        name=record.display_name,
                    )
                )
            if state == "approved":
                record._check_approval_still_valid()
                ready |= record
            elif not record.approval_required:
                ready |= record
            elif state:
                trace.REFUSAL.event("confirm_approval_refused", record=record)
                raise UserError(
                    self.env._(
                        "The approval of %(name)s was refused or cancelled. "
                        "Reset it to draft to ask again.",
                        name=record.display_name,
                    )
                )
            else:
                need_approval |= record
        return ready, need_approval

    def _check_approval_still_valid(self):
        self.check_singleton()

    def _on_approval_approved(self):
        super()._on_approval_approved()
        self._confirm_on_approval()

    def _is_confirmed_on_approval(self):
        self.check_singleton()
        return self.state == "draft"

    def _confirm_on_approval(self):
        self.check_singleton()
        if not self._is_confirmed_on_approval():
            return
        with self._approval_side_effect(
            self.env._(
                "Approval was granted, but the document could not be confirmed: "
                "%(error)s"
            )
        ):
            self.sudo().action_confirm()

    def action_cancel(self):
        result = super().action_cancel()
        self._refuse_pending_approval()
        return result

    def _refuse_pending_approval(self):
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

    def action_draft(self):
        result = super().action_draft()
        self._clear_refused_approval_link()
        return result
