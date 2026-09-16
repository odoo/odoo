from odoo import fields, models
from odoo.exceptions import UserError

from . import approval_trace as trace
from .approval_utils import ApprovalStepUnstaffed

OPERATION_CONTEXT_KEY = "approval_gate_operation"


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
        asked, blocked = asking._ask_approval_each()
        return self._get_approval_asked_notification(
            operation, ready, asked, result, blocked
        )

    def _ask_approval_each(self):
        """Raise one request per record, and keep the batch when a company staffs none.

        A batch is one transaction, so a refusal here rolls back every record that
        already ran -- including the ones that needed no approval at all and were
        done before the first request was raised. A document's own refusal earns
        that: something about that document is wrong, and the person asked for it by
        acting on it. A step whose approvers all work in another company does not.
        That configuration is nobody-in-this-batch's doing and nobody in it can fix
        it, so the record is reported and the rest stand.

        Returns the records whose request was raised, and a list of
        ``(record, error)`` for the ones it could not be raised for.
        """
        # Flush before the first savepoint. A savepoint flushes on entry, and that
        # flush checks each record's constraints in the environment that produced
        # them, so a later iteration is otherwise handed a failure belonging to work
        # done before this loop began.
        self.env.flush_all()
        asked = self.browse()
        blocked = []
        for record in self:
            try:
                with self.env.cr.savepoint():
                    record.action_create_approval_request()
            except ApprovalStepUnstaffed as error:
                trace.MIXIN.event(
                    "approval_not_asked_unstaffed",
                    record=record,
                    step=error.step.id if error.step else None,
                    company=error.company.id if error.company else None,
                )
                blocked.append((record, error))
            else:
                asked |= record
        return asked, blocked

    def _get_approval_asked_headline(self, ready, need_approval, blocked=()):
        """The first line of the batch's notification, in this document's words.

        A model that says it in its own vocabulary overrides this rather than
        `_get_approval_asked_notification`, so the lines naming what could not be
        asked at all are still appended after it -- and a reason added later
        appears without that model having to know about it.
        """
        if blocked:
            return self.env._(
                "%(sent)s sent for approval; %(ran)s went through; "
                "%(blocked)s could not be sent.",
                sent=len(need_approval),
                ran=len(ready),
                blocked=len(blocked),
            )
        return self.env._(
            "%(sent)s sent for approval; %(ran)s went through.",
            sent=len(need_approval),
            ran=len(ready),
        )

    def _get_approval_unstaffed_note(self, error):
        """One line for a record nobody could be asked for, naming what to configure."""
        self.check_singleton()
        step = error.step
        company = error.company
        if not step or not company:
            return self.env._(
                "%(name)s could not be sent for approval: no approver is configured.",
                name=self.display_name,
            )
        return self.env._(
            "%(name)s could not be sent for approval: nobody in %(company)s can "
            "approve step %(step)s.",
            name=self.display_name,
            company=company.display_name,
            step=step.name,
        )

    def _get_approval_asked_notification(
        self, operation, ready, need_approval, result, blocked=()
    ):
        params = {
            "type": "warning",
            "title": self.env._("Approval Required"),
            "message": "\n".join(
                [
                    self._get_approval_asked_headline(ready, need_approval, blocked),
                    *(
                        record._get_approval_unstaffed_note(error)
                        for record, error in blocked
                    ),
                ]
            ),
            "sticky": bool(blocked),
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

    def _is_approval_gate_enforced(self, operation):
        return self.env["approval.gate"]._is_enforced(self, operation)

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
