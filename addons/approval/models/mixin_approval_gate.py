from odoo import api, fields, models
from odoo.exceptions import UserError

from . import approval_trace as trace

OPERATION_CONTEXT_KEY = "approval_gate_operation"
ENFORCE_PARAM = "approval.gate_enforced"


class MixinApprovalGate(models.AbstractModel):
    _name = "mixin.approval.gate"
    _inherit = ["mixin.approval"]
    _description = "Operation Gated by Approval"

    _approval_operations = ()

    def _run_through_approval(self, operation, run):
        ready, need_approval = self._split_for_approval(operation)
        result = run(ready._admitted_for(operation)) if ready else True
        if not need_approval:
            return result
        trace.MIXIN.note(
            "operation_needs_approval",
            records=need_approval,
            operation=operation,
            ran=len(ready),
        )
        asking = need_approval.with_context(**{OPERATION_CONTEXT_KEY: operation})
        if len(self) == 1:
            return asking.action_create_approval_request()
        for record in asking:
            record.action_create_approval_request()
        return self._get_approval_asked_notification(
            operation, ready, need_approval, result
        )

    def _get_approval_asked_notification(self, operation, ready, need_approval, result):
        params = {
            "type": "warning",
            "title": self.env._("Approval Required"),
            "message": self.env._(
                "%(sent)s sent for approval; %(ran)s went through.",
                sent=len(need_approval),
                ran=len(ready),
            ),
            "sticky": False,
        }
        if isinstance(result, dict):
            params["next"] = result
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": params,
        }

    def _split_for_approval(self, operation):
        ready = need_approval = self.browse()
        for record in self:
            state = record.approval_request_id and record.approval_state
            if state and not record._approval_request_gates(operation):
                state = False
            if state in ("new", "pending"):
                trace.REFUSAL.event(
                    "operation_approval_pending", record=record, operation=operation
                )
                raise UserError(
                    self.env._(
                        "%(name)s is pending approval: wait for the decision, "
                        "or ask an approver to refuse it so the document can change.",
                        name=record.display_name,
                    )
                )
            if state == "approved":
                record._check_approval_covers(operation)
                ready |= record
            elif not record.approval_required:
                ready |= record
            elif state and record._is_approval_reasked_after_refusal(operation):
                record._clear_refused_approval_link()
                need_approval |= record
            elif state:
                trace.REFUSAL.event(
                    "operation_approval_refused", record=record, operation=operation
                )
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

    def _is_approval_reasked_after_refusal(self, operation):
        """Whether a refused request is dropped and asked again, rather than refusing
        the operation until someone resets the document."""
        self.check_singleton()
        return False

    def _approval_request_gates(self, operation):
        """Whether the linked request is the one that decides `operation` here.

        A request that *produced* this document decides whether the document may
        exist, not whether it may go through; gating on it would leave a
        transfer created from an approved request unable to move.
        """
        self.check_singleton()
        request = self.approval_request_id.sudo()
        if request.get_source_document() != self:
            return False
        asked_for = request.operation
        return not asked_for or asked_for == operation

    def _get_approval_snapshot(self, operation):
        """What the approver is being shown, as far as the grant covers it.

        Empty means the grant covers the document whatever it becomes, which is
        what a document says by not describing itself.
        """
        self.check_singleton()
        return {}

    def _check_approval_covers(self, operation):
        """Raise when the grant no longer covers what the operation would do."""
        self.check_singleton()
        approved = self.approval_request_id.operation_snapshot
        if not approved:
            return
        if approved != self._get_approval_snapshot(operation):
            trace.REFUSAL.event(
                "operation_snapshot_moved", record=self, operation=operation
            )
            raise UserError(
                self.env._(
                    "What was approved is no longer what is there: %(name)s changed "
                    "after its approval was granted. Ask for approval again.",
                    name=self.display_name,
                )
            )

    def _admitted_for(self, operation):
        return self.env["approval.binding"]._admit(self, operation)

    def _get_admitted_ids(self, operation):
        return self.env["approval.binding"]._get_admitted_ids(self, operation)

    def _check_approval_admits(self, operation):
        """Hold `operation`'s gate on a path that did not come through it.

        A checkpoint can raise no request, so a record the gate would send for
        approval is refused here -- or, while the gate is only watching, recorded.
        A grant that no longer covers its document is refused either way: that is
        the approval speaking, not the path.
        """
        admitted = self._get_admitted_ids(operation)
        blocked = self.browse()
        for record in self.filtered(lambda r: r.id not in admitted):
            state = record.approval_request_id and record.approval_state
            if state == "approved" and record._approval_request_gates(operation):
                record._check_approval_covers(operation)
                continue
            if record.approval_required or state in ("new", "pending"):
                blocked |= record
        if not blocked:
            return
        self.env["approval.observation"].sudo().create(
            [
                {
                    "model_name": record._name,
                    "operation": operation,
                    "res_id": record.id,
                    "user_id": self.env.uid,
                    "elevation": "superuser" if self.env.su else "none",
                    "would_block": True,
                }
                for record in blocked
            ]
        )
        if not self._is_approval_gate_enforced(operation):
            trace.MIXIN.note(
                "gate_observed", records=blocked, operation=operation, enforced=False
            )
            return
        trace.REFUSAL.event("gate_bypassed", records=blocked, operation=operation)
        raise UserError(
            self.env._(
                "%(records)s need an approval before %(operation)s can run, and this "
                "way of running it cannot ask for one. Use %(operation)s itself, "
                "which raises the request.",
                records=", ".join(blocked.mapped("display_name")),
                operation=operation,
            )
        )

    @api.model
    def _is_approval_gate_enforced(self, operation):
        return (
            self.env["ir.config_parameter"].sudo().get_param(ENFORCE_PARAM, "") == "1"
        )

    def _is_operation_run_on_approval(self, operation):
        self.check_singleton()
        return True

    def _on_approval_approved(self):
        super()._on_approval_approved()
        self._run_operation_on_approval()

    def _run_operation_on_approval(self):
        self.check_singleton()
        request = self.approval_request_id.sudo()
        operation = request.operation or self._get_gated_operation()
        if not operation or request.date_operation_run:
            return
        if not self._is_operation_run_on_approval(operation):
            return
        trace.MIXIN.note("operation_on_approval", record=self, operation=operation)
        request.date_operation_run = fields.Datetime.now()
        with self._approval_side_effect(self._get_operation_failure_note(operation)):
            getattr(self.sudo(), operation)()

    def _get_operation_failure_note(self, operation):
        self.check_singleton()
        return self.env._(
            "Approval was granted, but the document could not go through: %(error)s"
        )

    def _get_gated_operation(self):
        self.check_singleton()
        return self._approval_operations[0] if self._approval_operations else False

    def _prepare_approval_request_values(self, category):
        values = super()._prepare_approval_request_values(category)
        operation = self.env.context.get(OPERATION_CONTEXT_KEY) or (
            self._get_gated_operation()
        )
        if operation:
            values["operation"] = operation
            values["operation_snapshot"] = self._get_approval_snapshot(operation)
        return values

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
