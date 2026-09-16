import logging
from typing import Any

from odoo import fields, models
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.fields import Command
from odoo.libs.text import nl2br

from . import approval_trace as trace
from .approval_utils import ApprovalStepUnstaffed, is_approval_manager

_logger = logging.getLogger(__name__)


class ApprovalRequestLifecycle(models.Model):
    _inherit = "approval.request"

    def _check_bulk_decision_allowed(self) -> None:
        for request in self:
            if request.state != "pending":
                trace.REFUSAL.event(
                    "bulk_request_not_pending",
                    request=request.id,
                    state=request.state,
                )
                raise UserError(
                    self.env._(
                        "Request '%(request)s' is not in pending state (current: %(state)s).",
                        request=request.name,
                        state=request.state,
                    ),
                )
            if not request._get_current_pending_approver():
                trace.REFUSAL.event(
                    "bulk_no_pending_row", request=request.id, uid=self.env.uid
                )
                raise UserError(
                    self.env._(
                        "You don't have pending approval rights for request: %s",
                        request.name,
                    ),
                )

    def _action_bulk_decision(
        self,
        action_method: str,
        action_label: str,
        past_tense: str,
        before: Any = None,
    ) -> dict[str, Any]:
        self._check_bulk_decision_allowed()

        success_count = 0
        failed_requests = []
        for request in self:
            try:
                with self.env.cr.savepoint():
                    if before is not None:
                        before(request)
                    getattr(request.with_context(skip_wizard=True), action_method)()
                success_count += 1
            except (UserError, ValidationError) as e:
                trace.LIFECYCLE.event(
                    "bulk_refused",
                    request=request.id,
                    action=action_label,
                    error=type(e).__name__,
                )
                failed_requests.append((request.name, str(e)))
                request.message_post(
                    body=self.env._(
                        "Bulk %(action)s failed: %(error)s",
                        action=action_label,
                        error=str(e),
                    ),
                    message_type="notification",
                )
            except Exception as e:
                _logger.exception(
                    "Unexpected error in bulk %s for request %s",
                    action_label,
                    request.name,
                )
                failed_requests.append(
                    (request.name, self.env._("Unexpected error occurred"))
                )
                request.message_post(
                    body=self.env._(
                        "Bulk %(action)s failed with unexpected error: %(error)s",
                        action=action_label,
                        error=str(e),
                    ),
                    message_type="notification",
                )

        trace.annotate(work=len(self))
        trace.LIFECYCLE.note(
            "bulk_done",
            action=action_label,
            asked=len(self),
            ok=success_count,
            failed=len(failed_requests),
        )
        if failed_requests:
            failure_details = "\n".join(
                [f"• {name}: {error}" for name, error in failed_requests],
            )
            message = self.env._(
                "%(success)s of %(total)s request(s) %(action)s successfully.\n\nFailed requests:\n%(failures)s",
                success=success_count,
                total=len(self),
                action=past_tense,
                failures=failure_details,
            )
            notification_type = "warning" if success_count > 0 else "danger"
        else:
            message = self.env._(
                "%(count)s approval request(s) %(action)s successfully",
                count=success_count,
                action=past_tense,
            )
            notification_type = "success"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": notification_type,
                "message": message,
                "sticky": bool(failed_requests),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def action_approve_bulk(self) -> dict[str, Any]:
        return self._action_bulk_decision("action_approve", "approval", "approved")

    def _raise_not_assigned_approver(self) -> None:
        # No campaign refusal event here on purpose: three callers reach this one
        # message for four different reasons, and one event would collapse them.
        # Each caller reports its own kind before calling (decision_without_a_row,
        # change_request_without_a_row, wizard_without_a_row).
        raise UserError(
            self.env._(
                "You are not assigned as an approver for this request, "
                "or your approval has already been processed.",
            ),
        )

    def _apply_decision(
        self,
        decision: str,
        approver: models.BaseModel | None = None,
        steps: models.BaseModel | None = None,
    ) -> None:
        self.check_singleton()
        assert decision in ("approve", "refuse")
        self._lock_and_reload(with_approvers=True)
        if self.state != "pending":
            trace.REFUSAL.event(
                "decision_state", request=self.id, state=self.state, decision=decision
            )
            raise UserError(
                self.env._(
                    "This request can no longer be %(decision)s: it is "
                    "in state '%(state)s'.",
                    decision=self.env._("approved")
                    if decision == "approve"
                    else self.env._("refused"),
                    state=self.state,
                ),
            )
        old_state = self.state
        unmet_before = (
            set(self._get_blocking_unmet_steps().ids)
            if self.approver_ids.step_ids
            else None
        )
        if not isinstance(approver, models.BaseModel):
            candidate = self.approver_ids.filtered(
                lambda a: a._get_effective_approver() == self.env.user,
            )
        else:
            candidate = approver.filtered(lambda a: a.request_id == self)
        if steps:
            approver = candidate.filtered(
                lambda a: (
                    a.state in ("pending", "waiting", "approved")
                    and steps <= a.step_ids
                )
            )
            trace.DECISION.event(
                "rows_for_steps",
                request=self.id,
                steps=steps.ids,
                candidates=candidate.ids,
                rows=approver.ids,
            )
        else:
            approver = candidate.filtered(
                lambda a: (
                    a.state == "pending"
                    or (a.state == "waiting" and a.step_ids)
                    or (
                        decision == "approve"
                        and a.state == "approved"
                        and a.step_ids - a.decided_step_ids
                    )
                )
            )
        self._check_decision_actor(approver)
        if not approver:
            trace.REFUSAL.event(
                "decision_without_a_row",
                request=self.id,
                decision=decision,
                uid=self.env.uid,
                candidates=candidate.ids,
            )
            self._raise_not_assigned_approver()
        self._check_steps_decidable(approver, steps)
        self._check_step_turn(approver, steps)
        acting_user = approver[:1]._get_effective_approver()
        trace.DECISION.event(
            "actor",
            request=self.id,
            decision=decision,
            rows=approver.ids,
            acting=acting_user.id,
            asked_steps=steps.ids if steps else None,
        )
        now = fields.Datetime.now()
        logged_steps = {}
        for row in approver.sudo():
            if steps:
                decided = steps
            elif decision == "approve":
                decided = self._get_steps_for_decision(row)
            else:
                decided = row.step_ids
            if decision == "approve" and row.state == "approved":
                decided |= row.decided_step_ids
            if decision == "approve" and row.state == "approved":
                # Link rather than set: the row's decided steps read without an
                # archived one, which a set would forget.
                decided_steps = [Command.link(step.id) for step in decided]
            else:
                decided_steps = [Command.set(decided.ids)]
            row.write(
                {
                    "decision_date": now,
                    "decided_by_user_id": acting_user.id,
                    "decided_step_ids": decided_steps,
                },
            )
            logged_steps[row.id] = decided
        self._append_decision_log(
            "approved" if decision == "approve" else "refused",
            rows=approver,
            actor=acting_user,
            steps_by_row=logged_steps,
        )
        if decision == "approve":
            body = self.env._(
                "The request created on %(create_date)s by %(request_owner)s has been accepted.",
                create_date=self.create_date.date(),
                request_owner=self.request_owner_id.name,
            )
            subject = self.env._(
                "The request %(request_name)s for %(request_owner)s has been accepted",
                request_name=self.display_name,
                request_owner=self.request_owner_id.name,
            )
        elif all(row._is_advisory_only() for row in approver):
            body = self.env._(
                "%(approver)s advised against the request created on %(create_date)s by "
                "%(request_owner)s. The advice decides nothing.",
                approver=acting_user.name,
                create_date=self.create_date.date(),
                request_owner=self.request_owner_id.name,
            )
            subject = self.env._(
                "Advice against %(request_name)s for %(request_owner)s",
                request_name=self.display_name,
                request_owner=self.request_owner_id.name,
            )
        else:
            body = self.env._(
                "The request created on %(create_date)s by %(request_owner)s has been refused.",
                create_date=self.create_date.date(),
                request_owner=self.request_owner_id.name,
            )
            subject = self.env._(
                "The request %(request_name)s for %(request_owner)s has been refused",
                request_name=self.display_name,
                request_owner=self.request_owner_id.name,
            )
        self.with_user(acting_user).sudo().message_post(
            body=body,
            subject=subject,
            author_id=acting_user.partner_id.id,
            message_type="notification",
            partner_ids=self.request_owner_id.partner_id.ids,
        )
        self._notify_step_decision(approver, acting_user, decision, steps)
        if decision == "refuse" and not all(
            row._is_advisory_only() for row in approver
        ):
            self._flip_unsettled_approvers("refused")
        self._get_user_approval_activities(user=acting_user).sudo().action_feedback()
        if decision == "approve" and self.state == "pending":
            self._refresh_turn_states()
            self.approver_ids.filtered(
                lambda a: a.state == "pending" and a.step_ids,
            ).sudo()._create_activity()
            self._retire_unasked_approval_activities()
        if self.state in self._TERMINAL_STATES:
            self._cancel_activities()
        if self.state == "approved":
            self.approver_ids.sudo().filtered(
                lambda a: a.state == "pending",
            ).write({"flow_state": "waiting"})
        self._notify_if_terminal_transition(old_state)
        if (
            unmet_before is not None
            and decision == "approve"
            and self.state == "pending"
            and set(self._get_blocking_unmet_steps().ids) < unmet_before
        ):
            self._notify_source_document_progress()
        trace.DECISION.note(
            "decided",
            request=self.id,
            decision=decision,
            actor=acting_user.id,
            was=old_state,
            state=self.state,
            rows=len(approver),
        )
        self._log_cycle("decide", decision=decision, actor=acting_user.login)
        if decision == "refuse" and self.state == "refused":
            self._refuse_approval_request()

    def action_approve(
        self,
        approver: models.BaseModel | None = None,
        steps: models.BaseModel | None = None,
    ) -> dict[str, Any] | None:
        self.check_singleton()
        self._check_no_pending_change("approve")
        self._apply_decision("approve", approver, steps)

    def _get_steps_for_decision(self, approver):
        """The steps an approval naming none is given for.

        Every undecided step of the row, unless one of the row's steps is exclusive:
        then the first still short of its quorum, exclusive steps first within a
        sequence. Deciding that here, not when counting, keeps who decided which step
        fixed as later approvals come in.
        """
        self.check_singleton()
        undecided = (approver.step_ids - approver.decided_step_ids).filtered(
            lambda step: self._is_row_turn(approver, step)
        )
        if not any(approver.step_ids.mapped("exclusive")):
            trace.DECISION.event(
                "steps_for_decision",
                request=self.id,
                approver=approver.id,
                undecided=undecided.ids,
                exclusive=False,
                chosen=undecided.ids,
            )
            return undecided
        counts = self._get_step_counts()
        ordered = undecided.sorted(
            lambda step: (step.sequence, not step.exclusive, step.id)
        )
        short = ordered.filtered(lambda step: counts.get(step.id, 0) < step.minimum)
        chosen = short[:1] or ordered[:1]
        trace.DECISION.event(
            "steps_for_decision",
            request=self.id,
            approver=approver.id,
            undecided=undecided.ids,
            exclusive=True,
            short_of_quorum=short.ids,
            chosen=chosen.ids,
        )
        return chosen

    def _check_steps_decidable(self, approvers, steps=None) -> None:
        """Refuse deciding a step twice, or a step beside an exclusive decided one."""
        self.check_singleton()
        for approver in approvers:
            decided = approver.decided_step_ids
            if not decided:
                continue
            if steps and steps & decided:
                trace.REFUSAL.event(
                    "step_decided_twice",
                    request=self.id,
                    approver=approver.id,
                    steps=(steps & decided).ids,
                )
                raise UserError(
                    self.env._(
                        "%(user)s has already decided %(steps)s on %(name)s.",
                        user=approver._get_effective_approver().name,
                        steps=", ".join((steps & decided).mapped("name")),
                        name=self.display_name,
                    ),
                )
            wanted = steps or approver.step_ids - decided
            if any((decided | wanted).mapped("exclusive")):
                trace.REFUSAL.event(
                    "step_exclusive",
                    request=self.id,
                    approver=approver.id,
                    decided=decided.ids,
                    wanted=wanted.ids,
                )
                raise UserError(
                    self.env._(
                        "This approval or the one you already submitted limits you "
                        "to a single approval on %(name)s. Another user is required "
                        "to decide the other steps.",
                        name=self.display_name,
                    ),
                )

    def _check_step_turn(self, approvers, steps=None) -> None:
        """Refuse a decision on a step whose members decide in order, out of turn."""
        self.check_singleton()
        for approver in approvers:
            wanted = steps or (approver.step_ids - approver.decided_step_ids)
            if not wanted:
                continue
            waiting = wanted.filtered(
                lambda step, row=approver: not self._is_row_turn(row, step)
            )
            if not waiting or (not steps and waiting != wanted):
                continue
            trace.REFUSAL.event(
                "step_out_of_turn",
                request=self.id,
                approver=approver.id,
                steps=waiting.ids,
            )
            raise UserError(
                self.env._(
                    "%(user)s cannot decide %(steps)s on %(name)s yet: its members "
                    "decide in order, and an earlier one has not approved it.",
                    user=approver._get_effective_approver().name,
                    steps=", ".join(waiting.mapped("name")),
                    name=self.display_name,
                ),
            )

    def _notify_step_decision(
        self, approvers, acting_user, decision: str, steps=None
    ) -> None:
        """Post an internal note to the notify list of every step this decision is for."""
        self.check_singleton()
        steps = steps or approvers.decided_step_ids
        partners = steps.notify_user_ids.partner_id
        trace.DECISION.event(
            "step_notify",
            request=self.id,
            decision=decision,
            steps=steps.ids,
            partners=partners.ids,
        )
        if not partners:
            return
        if decision == "approve":
            body = self.env._(
                "%(user)s approved step(s) %(steps)s of %(request)s.",
                user=acting_user.name,
                steps=", ".join(steps.mapped("name")),
                request=self.display_name,
            )
        else:
            body = self.env._(
                "%(user)s refused step(s) %(steps)s of %(request)s.",
                user=acting_user.name,
                steps=", ".join(steps.mapped("name")),
                request=self.display_name,
            )
        self.sudo().message_post(
            body=body,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
            partner_ids=partners.ids,
        )

    def _refuse_cascade(self) -> bool:
        self.check_singleton()
        if self.state in self._TERMINAL_STATES or self.state == "new":
            return False
        target_state = self._get_parent_cancel_state()
        trace.LIFECYCLE.event(
            "cascade", request=self.id, was=self.state, target=target_state
        )
        if target_state == "refused":
            self._force_terminal(
                "refused",
                body=self.env._(
                    "Refused automatically because the parent document was cancelled.",
                ),
                refusal_reason=self.env.ref("approval.refusal_reason_parent_cancelled"),
                refusal_note=self.env._("Parent document was cancelled."),
            )
        else:
            self._force_terminal(
                target_state,
                body=self.env._(
                    "Cancelled automatically because the parent document "
                    "was cancelled.",
                ),
            )
        return True

    def _get_parent_cancel_state(self) -> str:
        return "refused"

    def _check_no_pending_change(self, action_verb: str) -> None:
        if any(self.mapped("pending_change_field")):
            trace.REFUSAL.event(
                "blocked_by_pending_change", requests=self.ids, action=action_verb
            )
            raise UserError(
                self.env._(
                    "You cannot %(verb)s this request while a change is "
                    "pending. Wait for the requester to update the "
                    "requested field and re-submit.",
                    verb=action_verb,
                ),
            )

    def _check_change_request_allowed(self) -> None:
        self.check_singleton()
        self._check_moved_from_source_document()
        if self.state != "pending":
            trace.REFUSAL.event(
                "change_request_not_pending", request=self.id, state=self.state
            )
            raise UserError(
                self.env._(
                    "A change can only be requested while the approval is "
                    "pending. Current state: %(state)s",
                    state=self.state,
                ),
            )
        if self.pending_change_field:
            trace.REFUSAL.event(
                "change_already_pending",
                request=self.id,
                field=self.pending_change_field,
            )
            raise UserError(
                self.env._(
                    "A change is already pending on this request (field "
                    "%(field)s). Wait for the requester to re-submit.",
                    field=self.pending_change_field,
                ),
            )

    def action_request_change(
        self,
        approver: models.BaseModel | None = None,
    ) -> dict[str, Any] | None:
        self.check_singleton()

        self._check_change_request_allowed()

        if approver is None and not self.env.context.get("skip_wizard"):
            return self._get_decision_wizard_action("change")

        if not isinstance(approver, models.BaseModel):
            approver = self._get_current_pending_approver()
        else:
            approver = approver.filtered(
                lambda a: a.request_id == self and a.state == "pending",
            )
        self._check_decision_actor(approver)
        if not approver:
            trace.REFUSAL.event(
                "change_request_without_a_row", request=self.id, uid=self.env.uid
            )
            self._raise_not_assigned_approver()

        self._lock_and_reload()
        self._check_change_request_allowed()

        requested_field = self.env.context.get("requested_change_field")
        if requested_field not in self._PENDING_CHANGE_EDITABLE:
            trace.REFUSAL.event(
                "change_field_not_editable", request=self.id, field=requested_field
            )
            raise UserError(
                self.env._(
                    "Internal: requested_change_field context value must "
                    "be one of %(allowed)s.",
                    allowed=", ".join(sorted(self._PENDING_CHANGE_EDITABLE)),
                ),
            )
        candidates = self._get_pending_change_candidates()
        if requested_field not in candidates:
            trace.REFUSAL.event(
                "change_field_not_on_category",
                request=self.id,
                field=requested_field,
                category=self.category_id.id,
                candidates=sorted(candidates),
            )
            raise UserError(
                self.env._(
                    "The '%(field)s' field is not available on category "
                    "'%(category)s', so the requester would have nothing "
                    "to change.\n\nAsk for a change on: %(allowed)s — or "
                    "refuse the request instead.",
                    field=requested_field,
                    category=self.category_id.name,
                    allowed=", ".join(sorted(candidates)),
                ),
            )
        self.sudo().write({"pending_change_field": requested_field})
        trace.LIFECYCLE.note(
            "change_requested",
            request=self.id,
            field=requested_field,
            approver=approver.id,
        )
        self._schedule_change_request_activity(
            requested_field,
            self.env.context.get("requested_change_note") or "",
        )
        return None

    def _schedule_change_request_activity(self, field_name: str, note: str) -> None:
        self.check_singleton()
        field_label = dict(
            self._fields["pending_change_field"]._description_selection(self.env)
        )[field_name]
        trace.ACTIVITY.note(
            "change_request_scheduled",
            request=self.id,
            field=field_name,
            owner=self.request_owner_id.id,
            has_note=bool(note),
        )
        self.activity_schedule(
            "approval.mail_activity_data_change_request",
            user_id=self.request_owner_id.id,
            summary=self.env._("Change requested on %s", field_label),
            note=nl2br(note) if note else False,
        )

    def action_resubmit(self) -> None:
        self.check_singleton()
        if not self.pending_change_field:
            trace.REFUSAL.event("resubmit_without_pending_change", request=self.id)
            raise UserError(
                self.env._(
                    "There is no pending change on this request.",
                ),
            )
        is_owner = self.request_owner_id == self.env.user
        is_manager = is_approval_manager(self.env)
        if not (is_owner or is_manager or self.user_approver_state):
            trace.REFUSAL.event(
                "resubmit_not_owner_nor_approver", request=self.id, uid=self.env.uid
            )
            raise UserError(
                self.env._(
                    "Only the request owner or an approver can re-submit "
                    "after a requested change.",
                ),
            )
        previous_field = self.pending_change_field
        self.sudo().write({"pending_change_field": False})
        self._get_change_request_activities().sudo().action_feedback()
        added = self._extend_approvers_live()
        undone = self.approver_ids.filtered(lambda a: a.state == "approved")
        if undone:
            self._append_decision_log(
                "withdrawn",
                rows=undone,
                steps_by_row={row.id: row.decided_step_ids for row in undone},
                note=self.env._("The requested change was applied."),
            )
            undone.sudo().write(
                {
                    "flow_state": "waiting",
                    "decision_date": False,
                    "decided_by_user_id": False,
                    "decided_step_ids": [Command.clear()],
                },
            )
            self._cancel_activities()
            self._open_approval_round(
                self.approver_ids.filtered(
                    lambda a: a.state in ("pending", "waiting"),
                ),
            )
        self.message_post(
            body=self.env._(
                "Re-submitted after the requested change to %(field)s.",
                field=previous_field,
            )
            if not undone
            else self.env._(
                "Re-submitted after the requested change to %(field)s. "
                "%(count)d earlier approval(s) were reset: they were given "
                "on the previous value.",
                field=previous_field,
                count=len(undone),
            ),
            message_type="notification",
        )
        self._log_cycle(
            "resubmit",
            field=previous_field,
            reset=len(undone),
            added=len(added),
        )

    def action_confirm(self) -> None:
        self._sync_approvers()
        to_open = self.env["approval.approver"]
        confirmed = self.env["approval.request"]
        for request in self:
            request._lock_and_reload()

            if request.state != "new":
                trace.REFUSAL.event(
                    "confirm_not_draft", request=request.id, state=request.state
                )
                raise UserError(
                    self.env._(
                        "Only requests in draft state can be confirmed. "
                        "Request '%(name)s' is currently in state "
                        "'%(state)s'.",
                        name=request._label(),
                        state=request.state,
                    ),
                )

            old_state = request.state
            request._check_confirm()

            if not request.name:
                request.name = request.category_id.sequence_id.next_by_id()

            request.category_snapshot = request._prepare_category_snapshot()

            request.write({"date_confirmed": fields.Datetime.now()})

            auto_action = request._check_auto_action_rules()
            if auto_action:
                trace.RULES.note(
                    "auto_action",
                    request=request.id,
                    was=old_state,
                    state=request.state,
                )
                request._notify_if_terminal_transition(old_state)
                continue

            to_open |= request.approver_ids.filtered(lambda a: a.state == "new")
            confirmed |= request

        self._open_approval_round(to_open)

        for request in confirmed:
            trace.LIFECYCLE.note(
                "confirmed",
                request=request.id,
                category=request.category_id.id,
                approvers=len(request.approver_ids),
                minimum=request.approval_minimum,
            )
            request._log_cycle("confirm")

    def _open_approval_round(self, approvers: models.BaseModel) -> None:
        rows_by_request: dict[int, list[int]] = {}
        for approver in approvers:
            rows_by_request.setdefault(approver.request_id.id, []).append(approver.id)

        to_open = self.env["approval.approver"]
        for request in self:
            row_ids = rows_by_request.get(request.id)
            if row_ids:
                to_open |= approvers.browse(row_ids)

        trace.annotate(work=len(to_open))
        trace.LIFECYCLE.event("round_opened", requests=self.ids, opened=len(to_open))
        trace.LIFECYCLE.items(
            "round_row",
            lambda: [
                {
                    "request": row.request_id.id,
                    "user": row.user_id.id,
                    "seq": row.sequence,
                }
                for row in to_open
            ],
        )
        to_open._create_activity()
        to_open.sudo().write({"flow_state": "pending"})
        self.filtered(
            lambda request: request.approver_ids.step_ids
        )._refresh_turn_states()

    def action_cancel(self) -> None:
        self._check_moved_from_source_document()
        self._check_owner_or_manager(self.env._("cancel"))
        for request in self:
            request._lock_and_reload()
            if request.state != "pending":
                trace.REFUSAL.event(
                    "cancel_not_pending", request=request.id, state=request.state
                )
                raise UserError(
                    self.env._(
                        "Only submitted requests can be cancelled. "
                        "Request '%(name)s' is in state '%(state)s' — "
                        "draft requests can simply be deleted.",
                        name=request.display_name,
                        state=request.state,
                    ),
                )
            request._force_terminal(
                "cancelled",
                body=self.env._(
                    "Request cancelled by %(user)s.",
                    user=self.env.user.name,
                ),
            )

    def action_reset_to_draft(self) -> None:
        for request in self:
            request._lock_and_reload()
            if request.state not in self._TERMINAL_STATES:
                trace.REFUSAL.event(
                    "reset_not_decided", request=request.id, state=request.state
                )
                raise UserError(
                    self.env._(
                        "Only decided requests can be reset to draft. "
                        "Request '%(name)s' is in state '%(state)s'.",
                        name=request.display_name,
                        state=request.state,
                    ),
                )
            if request.state == "approved":
                if not (self.env.su or is_approval_manager(self.env)):
                    trace.REFUSAL.event(
                        "reset_approved_not_manager",
                        request=request.id,
                        uid=self.env.uid,
                    )
                    raise AccessError(
                        self.env._(
                            "Only an approval manager can reset an approved "
                            "request. Request: %(name)s",
                            name=request.display_name,
                        ),
                    )
                request._check_withdraw_allowed()
            else:
                request._check_reset_actor()
            request._check_reset_allowed()
            request._force_draft()

    def _force_draft(self, note: str | None = None) -> None:
        """Clear every decision and send the request back to draft, whatever its state.

        action_reset_to_draft is the guarded way in for a user; an approval binding
        whose record returns to its reset condition resets a request still waiting too,
        so a decision given for the document's earlier state does not survive it.
        """
        self.check_singleton()
        request = self
        previous_state = request.state
        request._append_decision_log("reset", note=note)
        request._close_pending_change()
        request.approver_ids.sudo().write(
            {
                "flow_state": "new",
                "refusal_reason_id": False,
                "note": False,
                "decision_date": False,
                "decided_by_user_id": False,
                "decided_step_ids": [Command.clear()],
                "pending_since": False,
            },
        )
        request.sudo().write(
            {
                "revoked_state": False,
                "revoked_by_user_id": False,
                "date_revoked": False,
                "granted_by_user_id": False,
                "refusal_reason_id": False,
                "refusal_note": False,
                "date_confirmed": False,
                "category_snapshot": False,
                "last_reminder_date": False,
                "reminder_count": 0,
                "escalated_to_manager": False,
                "applied_rule_ids": [Command.clear()],
            },
        )
        request._sync_approvers()
        if previous_state in self._TERMINAL_STATES:
            request.with_context(
                approval_reset_from=previous_state
            )._notify_source_document_state_change("new")
        trace.LIFECYCLE.note("reset", request=request.id, was=previous_state)
        request._log_cycle("reset", was=previous_state)
        request.message_post(
            body=self.env._(
                "Reset to draft from '%(state)s' by %(user)s.",
                state=previous_state,
                user=self.env.user.name,
            ),
            message_type="notification",
        )

    def action_refuse_bulk(self) -> dict[str, Any]:
        self._check_bulk_decision_allowed()
        return {
            "name": self.env._("Refuse Requests"),
            "type": "ir.actions.act_window",
            "res_model": "approval.decision.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_request_ids": [Command.set(self.ids)],
                "default_decision_type": "refuse",
            },
        }

    def action_refuse(
        self,
        approver: models.BaseModel | None = None,
        steps: models.BaseModel | None = None,
    ) -> dict[str, Any] | None:
        self.check_singleton()
        self._check_no_pending_change("refuse")

        if (
            approver is None
            and steps is None
            and not self.env.context.get("skip_wizard")
        ):
            return self._get_decision_wizard_action("refuse")

        self._apply_decision("refuse", approver, steps)
        return None

    def _get_decision_wizard_action(self, decision_type: str) -> dict[str, Any]:
        self.check_singleton()
        current_approver = self._get_current_pending_approver()[:1]
        if not current_approver:
            trace.REFUSAL.event(
                "wizard_without_a_row",
                request=self.id,
                uid=self.env.uid,
                decision=decision_type,
            )
            self._raise_not_assigned_approver()
        titles = {
            "refuse": self.env._("Refuse Request"),
            "change": self.env._("Request a Change"),
        }
        return {
            "name": titles[decision_type],
            "type": "ir.actions.act_window",
            "res_model": "approval.decision.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_approver_id": current_approver.id,
                "default_decision_type": decision_type,
            },
        }

    def _refuse_approval_request(self) -> None:
        return

    def action_withdraw(
        self, approver: models.BaseModel | None = None
    ) -> dict[str, Any] | None:
        self._lock_and_reload(with_approvers=True)
        current_user = self.env.user
        explicit_approver = approver if isinstance(approver, models.BaseModel) else None
        for request in self:
            if request.state not in ("pending", "approved"):
                trace.REFUSAL.event(
                    "withdraw_state", request=request.id, state=request.state
                )
                raise UserError(
                    self.env._(
                        "You cannot withdraw an approval on a %(state)s "
                        "request. Use Reset to Draft to reopen it.",
                        state=request.state,
                    ),
                )
            if request.granted_by_user_id:
                trace.REFUSAL.event(
                    "withdraw_granted_request",
                    request=request.id,
                    granted_by=request.granted_by_user_id.id,
                )
                raise UserError(
                    self.env._(
                        "You cannot withdraw an approval on %(name)s: it was approved "
                        "without a decision. Use Reset to Draft to reopen it.",
                        name=request.display_name,
                    ),
                )
            if explicit_approver is not None:
                req_approver = explicit_approver.filtered(
                    lambda a, req=request: (
                        a.request_id == req and a.state == "approved"
                    ),
                )
            else:
                req_approver = request.approver_ids.filtered(
                    lambda a, user=current_user: (
                        a._get_effective_approver() == user and a.state == "approved"
                    ),
                )

            if not req_approver:
                trace.REFUSAL.event(
                    "withdraw_not_approver",
                    request=request.id,
                    uid=current_user.id,
                )
                raise UserError(
                    self.env._(
                        "You cannot withdraw this approval.\n\n"
                        "You are not assigned as an approver for this request, "
                        "or you have not approved it.",
                    ),
                )

            request._check_withdraw_allowed()

            old_state = request.state

            request._append_decision_log(
                "withdrawn",
                rows=req_approver,
                steps_by_row={row.id: row.decided_step_ids for row in req_approver},
            )
            req_approver.sudo().write(
                {
                    "flow_state": "pending",
                    "decision_date": False,
                    "decided_by_user_id": False,
                    "decided_step_ids": [Command.clear()],
                },
            )

            still_approved = request.state == "approved"

            if still_approved:
                req_approver.sudo().write({"flow_state": "waiting"})
            else:
                req_approver._create_activity()

                if old_state == "approved":
                    parked = request.approver_ids.filtered(
                        lambda a: a.state == "waiting",
                    )
                    parked.sudo().write({"flow_state": "pending"})
                    parked._create_activity()
                if request.approver_ids.step_ids:
                    # A withdrawal can hand a turn back: whoever it passed to is no
                    # longer asked.
                    request._refresh_turn_states()
                    request._retire_unasked_approval_activities()

            acting_user = req_approver[:1]._get_effective_approver()
            request.with_user(acting_user).sudo().message_post(
                body=self.env._(
                    "%(user)s withdrew their approval. The request is pending review again.",
                    user=acting_user.name,
                )
                if not still_approved
                else self.env._(
                    "%(user)s withdrew their approval. The request stays "
                    "approved: the remaining approvals still satisfy it.",
                    user=acting_user.name,
                ),
                author_id=acting_user.partner_id.id,
                message_type="notification",
            )

            trace.DECISION.note(
                "withdrawn",
                request=request.id,
                actor=acting_user.id,
                rows=req_approver.ids,
                was=old_state,
                reopened=not still_approved,
            )
            request._log_cycle(
                "withdraw",
                actor=acting_user.login,
                was=old_state,
                reopened=not still_approved,
            )

            if old_state == "approved" and request.state != "approved":
                request._notify_source_document_state_change("pending")

    def _check_confirm(self) -> None:
        self._check_enough_approvers()

    def _check_enough_approvers(self) -> None:
        self.check_singleton()
        steps = self._get_applicable_steps()
        if steps:
            self._check_steps_can_be_met(steps)
            return
        if len(self.approver_ids) < self.approval_minimum:
            trace.REFUSAL.event(
                "too_few_approvers",
                request=self.id,
                rows=len(self.approver_ids),
                minimum=self.approval_minimum,
            )
            raise UserError(
                self.env._(
                    "You have to add at least %(count)d approver(s) to "
                    "confirm your request.",
                    count=self.approval_minimum,
                ),
            )

    def _check_steps_can_be_met(self, steps) -> None:
        self.check_singleton()
        document = self.get_source_document()
        for step in steps.filtered(lambda step: not step.advisory):
            pool = step._get_pool_user_ids(document, self.company_id, self)
            if step.counts_added_approvers:
                pool |= set(
                    self.approver_ids.filtered(
                        lambda row: not row.source_synced
                    ).user_id.ids
                )
                if not self._allows_self_approval() and not self.binding_id:
                    pool.discard(self.request_owner_id.id)
            if len(pool) < step.minimum:
                candidates = step._get_candidate_user_ids(document, self)
                unstaffed = bool(candidates) and not step._filter_company_user_ids(
                    candidates, self.company_id
                )
                message = self.env._(
                    "Step '%(step)s' needs %(minimum)d approval(s) but only "
                    "%(count)d user(s) can give one, so this request could never "
                    "be approved. Add members to the step or lower its quorum.",
                    step=step.name,
                    minimum=step.minimum,
                    count=len(pool),
                )
                trace.REFUSAL.event(
                    "step_unmeetable",
                    request=self.id,
                    step=step.id,
                    pool=len(pool),
                    minimum=step.minimum,
                    unstaffed=unstaffed,
                )
                raise (
                    ApprovalStepUnstaffed(message, step=step, company=self.company_id)
                    if unstaffed
                    else UserError(message)
                )

    def action_withdraw_approver(
        self, approver_id: int, step_id: int | bool = False
    ) -> None:
        self.check_singleton()
        approver = self.approver_ids.filtered(lambda a: a.id == approver_id)
        if not approver:
            trace.REFUSAL.event(
                "approver_not_on_request", request=self.id, approver=approver_id
            )
            raise UserError(
                self.env._(
                    "That approver is not on request %(name)s.",
                    name=self.display_name,
                ),
            )
        steps = approver.decided_step_ids
        if step_id:
            steps = steps.filtered(lambda step: step.id == int(step_id))
            if not steps:
                trace.REFUSAL.event(
                    "no_decision_for_that_step",
                    request=self.id,
                    approver=approver.id,
                    step=int(step_id),
                )
                raise UserError(
                    self.env._(
                        "%(approver)s gave no decision for that step on %(name)s.",
                        approver=approver._get_effective_approver().name,
                        name=self.display_name,
                    ),
                )
        self._check_withdraw_actor(approver, steps)
        if approver.state == "approved" and approver.decided_step_ids - steps:
            self._withdraw_decided_steps(approver, steps)
        else:
            self.action_withdraw(approver)

    def _withdraw_decided_steps(self, approver, steps) -> None:
        """Take a decision back from some of its steps; it stands for the others."""
        self.check_singleton()
        self._lock_and_reload(with_approvers=True)
        if self.state not in ("pending", "approved"):
            trace.REFUSAL.event(
                "withdraw_steps_state", request=self.id, state=self.state
            )
            raise UserError(
                self.env._(
                    "You cannot withdraw an approval on a %(state)s request.",
                    state=self.state,
                ),
            )
        self._check_withdraw_allowed()
        old_state = self.state
        self._append_decision_log(
            "withdrawn", rows=approver, steps_by_row={approver.id: steps}
        )
        approver.sudo().write(
            {"decided_step_ids": [Command.unlink(step.id) for step in steps]},
        )
        if old_state == "approved" and self.state == "pending":
            parked = self.approver_ids.filtered(lambda a: a.state == "waiting")
            parked.sudo().write({"flow_state": "pending"})
            parked._create_activity()
        self._refresh_turn_states()
        self._retire_unasked_approval_activities()
        acting_user = self.env.user
        self.sudo().message_post(
            body=self.env._(
                "%(user)s withdrew %(approver)s's approval of %(steps)s.",
                user=acting_user.name,
                approver=approver._get_effective_approver().name,
                steps=", ".join(steps.mapped("name")),
            ),
            author_id=acting_user.partner_id.id,
            message_type="notification",
        )
        trace.DECISION.note(
            "withdrawn_steps",
            request=self.id,
            approver=approver.id,
            steps=steps.ids,
            was=old_state,
            state=self.state,
        )
        self._log_cycle(
            "withdraw",
            actor=acting_user.login,
            was=old_state,
            reopened=self.state != old_state,
        )

    def _check_withdraw_allowed(self) -> None:
        self._check_moved_from_source_document()

    def _check_moved_from_source_document(self) -> None:
        for request in self:
            model = request.res_model and self.env.get(request.res_model)
            if model is not None and getattr(
                model, "_approval_request_follows_document", False
            ):
                trace.REFUSAL.event(
                    "moved_from_document",
                    request=request.id,
                    model=request.res_model,
                )
                raise UserError(
                    self.env._(
                        "%(request)s follows its document: approve or refuse it here, "
                        "and move it otherwise from %(document)s itself.",
                        request=request.display_name,
                        document=request.res_name or request.res_model,
                    )
                )

    def _check_reset_allowed(self) -> None:
        self.check_singleton()
        self._check_moved_from_source_document()
        if not self.res_model or not self.res_id:
            return
        source_doc = self.get_source_document()
        if not source_doc or not source_doc.exists():
            return
        linked_request_id = getattr(source_doc, "approval_request_id", None)
        if linked_request_id is not None and linked_request_id.id != self.id:
            trace.REFUSAL.event(
                "reset_document_relinked",
                request=self.id,
                model=self.res_model,
                res_id=self.res_id,
                links=linked_request_id.id,
            )
            raise UserError(
                self.env._(
                    "This request cannot be reset: the source document "
                    "%(doc)s no longer references it. Request a new "
                    "approval from the document instead.",
                    doc=source_doc.display_name,
                ),
            )

    def _raise_withdraw_blocked(self, active_descendants, doc_label):
        if not active_descendants:
            return
        trace.REFUSAL.event(
            "withdraw_has_descendants",
            request=self.id,
            label=doc_label,
            descendants=len(active_descendants),
        )
        raise UserError(
            self.env._(
                "You cannot withdraw this approval because it has "
                "%(count)d active %(label)s(s) linked.\n\n"
                "Cancel the related %(label)s(s) first, then withdraw.",
                count=len(active_descendants),
                label=doc_label,
            ),
        )

    def _retire_unasked_approval_activities(self) -> None:
        """Remove the approval activities of rows no longer asked, once their steps are met.

        Unlinked, not marked done: their approver decided nothing.
        """
        self.check_singleton()
        stale = self._get_approval_activities().filtered(
            lambda activity: (
                activity.approver_id.state in ("pending", "waiting")
                and activity.approver_id.step_ids
                and not activity.approver_id._is_notifiable()
            )
        )
        trace.ACTIVITY.event("retire_unasked", request=self.id, stale=len(stale))
        stale.sudo().unlink()

    def _get_approval_activities(self, user: Any = None) -> Any:
        """The approval activities asking this request's approvers, wherever they live."""
        domain = [("approver_id.request_id", "in", self.ids)]
        if user:
            domain.append(("user_id", "=", user.id))
        return self.env["mail.activity"].sudo().search(domain)

    def _cancel_activities(self) -> None:
        activities = self._get_approval_activities()
        trace.ACTIVITY.event("cancel", requests=self.ids, activities=len(activities))
        activities.unlink()

    def _get_request_activities(self, activity_xmlid: str, user: Any = None) -> Any:
        domain = [
            ("res_model", "=", "approval.request"),
            ("res_id", "in", self.ids),
            ("activity_type_id", "=", self.env.ref(activity_xmlid).id),
        ]
        if user:
            domain.append(("user_id", "=", user.id))
        return self.env["mail.activity"].search(domain)

    def _get_user_approval_activities(self, user: Any) -> Any:
        return self._get_approval_activities(user=user)

    def _get_change_request_activities(self) -> Any:
        return self._get_request_activities(
            "approval.mail_activity_data_change_request"
        )

    def _lock_for_approval_action(self) -> None:
        if not self.ids:
            return

        self.env.cr.execute(
            """
            SELECT id FROM approval_request
            WHERE id = ANY(%s)
            ORDER BY id
            FOR UPDATE
            """,
            [list(self.ids)],
        )

    def _lock_and_reload(self, with_approvers: bool = False) -> None:
        with trace.LIFECYCLE.span(
            "lock_and_reload", n=len(self), with_approvers=with_approvers
        ):
            self._lock_for_approval_action()
            if with_approvers:
                self.approver_ids.invalidate_recordset(["state"])
            self.invalidate_recordset(["state"])

    def _flip_unsettled_approvers(self, new_state: str) -> None:
        self.check_singleton()
        settled = self.approver_ids._SETTLED_STATES
        unsettled = self.approver_ids.sudo().filtered(
            lambda a: a.state not in settled,
        )
        trace.DECISION.event(
            "flip_unsettled", request=self.id, to=new_state, rows=unsettled.ids
        )
        unsettled.write({"flow_state": new_state})

    def _stamp_refusal_metadata(
        self,
        refusal_reason: models.BaseModel | None,
        refusal_note: str | None,
    ) -> None:
        self.check_singleton()
        vals: dict[str, Any] = {}
        if refusal_reason and not self.refusal_reason_id:
            vals["refusal_reason_id"] = refusal_reason.id
        if refusal_note and not self.refusal_note:
            vals["refusal_note"] = refusal_note
        trace.LIFECYCLE.event(
            "refusal_metadata",
            request=self.id,
            stamped=sorted(vals),
            kept_reason=bool(refusal_reason and self.refusal_reason_id),
            kept_note=bool(refusal_note and self.refusal_note),
        )
        if vals:
            self.sudo().write(vals)

    def _force_terminal(
        self,
        new_state: str,
        body: str,
        refusal_reason: models.BaseModel | None = None,
        refusal_note: str | None = None,
        subtype_xmlid: str | None = None,
    ) -> None:
        if new_state not in self._TERMINAL_STATES - {"approved"}:
            raise ValueError(
                f"_force_terminal() accepts only non-approved terminal "
                f"states, got {new_state!r}",
            )
        self._lock_and_reload()
        for request in self:
            if request.state in request._TERMINAL_STATES:
                continue
            old_state = request.state
            request._flip_unsettled_approvers(new_state)
            request._stamp_refusal_metadata(refusal_reason, refusal_note)
            request._cancel_activities()
            request._close_pending_change()
            request._notify_if_terminal_transition(old_state)
            trace.LIFECYCLE.note(
                "forced_terminal",
                request=request.id,
                was=old_state,
                now=new_state,
                reason=refusal_reason.id if refusal_reason else None,
            )
            request._log_cycle("terminal", was=old_state, forced=new_state)
            request._append_decision_log(
                new_state, reason=refusal_reason, note=refusal_note
            )
            post_kwargs = {"message_type": "notification"}
            if subtype_xmlid:
                post_kwargs["subtype_xmlid"] = subtype_xmlid
            request.message_post(body=body, **post_kwargs)
            if request.state == "refused":
                request._refuse_approval_request()

    def _revoke(
        self,
        new_state: str,
        body: str,
        refusal_reason: models.BaseModel | None = None,
        refusal_note: str | None = None,
        subtype_xmlid: str | None = None,
    ) -> None:
        if new_state not in self._TERMINAL_STATES - {"approved"}:
            raise ValueError(
                f"_revoke() overturns an approval into refused or cancelled, got "
                f"{new_state!r}",
            )
        self._lock_and_reload()
        for request in self:
            if request.state != "approved":
                trace.REFUSAL.event(
                    "revoke_not_approved", request=request.id, state=request.state
                )
                raise UserError(
                    self.env._(
                        "Only an approved request can be revoked: %(name)s is "
                        "%(state)s.",
                        name=request.display_name,
                        state=request.state,
                    ),
                )
            request.sudo().write(
                {
                    "revoked_state": new_state,
                    "revoked_by_user_id": self.env.user.id,
                    "date_revoked": fields.Datetime.now(),
                },
            )
            request._stamp_refusal_metadata(refusal_reason, refusal_note)
            request._cancel_activities()
            request._notify_if_terminal_transition("approved")
            trace.LIFECYCLE.note(
                "revoked", request=request.id, into=new_state, actor=self.env.uid
            )
            request._log_cycle("revoke", forced=new_state)
            request._append_decision_log(
                "revoked", reason=refusal_reason, note=refusal_note
            )
            post_kwargs = {"message_type": "notification"}
            if subtype_xmlid:
                post_kwargs["subtype_xmlid"] = subtype_xmlid
            request.message_post(body=body, **post_kwargs)
            if request.state == "refused":
                request._refuse_approval_request()

    def _approve_without_decision(
        self, body: str, subtype_xmlid: str | None = None
    ) -> None:
        self._lock_and_reload(with_approvers=True)
        for request in self:
            if request.state != "pending":
                trace.REFUSAL.event(
                    "grant_not_pending", request=request.id, state=request.state
                )
                raise UserError(
                    self.env._(
                        "Only a pending request can be approved without a decision: "
                        "%(name)s is %(state)s.",
                        name=request.display_name,
                        state=request.state,
                    ),
                )
            request.sudo().write({"granted_by_user_id": self.env.user.id})
            request.approver_ids.sudo().filtered(
                lambda a: a.state == "pending",
            ).write({"flow_state": "waiting"})
            request._cancel_activities()
            request._close_pending_change()
            request._notify_if_terminal_transition("pending")
            trace.LIFECYCLE.note(
                "granted_without_decision", request=request.id, actor=self.env.uid
            )
            request._log_cycle("grant", actor=self.env.user.login)
            request._append_decision_log("granted")
            post_kwargs = {"message_type": "notification"}
            if subtype_xmlid:
                post_kwargs["subtype_xmlid"] = subtype_xmlid
            request.message_post(body=body, **post_kwargs)

    def _close_pending_change(self) -> None:
        self.check_singleton()
        if not self.pending_change_field:
            return
        activities = self._get_change_request_activities()
        trace.LIFECYCLE.note(
            "pending_change_closed",
            request=self.id,
            field=self.pending_change_field,
            activities=activities.ids,
        )
        activities.sudo().action_feedback()
        self.sudo().write({"pending_change_field": False})

    def _notify_if_terminal_transition(self, old_state: str) -> None:
        self.check_singleton()
        terminal = self.state != old_state and self.state in self._TERMINAL_STATES
        trace.LIFECYCLE.event(
            "terminal_transition",
            request=self.id,
            was=old_state,
            now=self.state,
            notifies=terminal,
        )
        if terminal:
            self._notify_source_document_state_change(self.state)
            if self.state == "approved":
                self._replay_bound_operation()

    def _replay_bound_operation(self) -> None:
        """Run the operation an approval.binding raised this request for.

        After the source document has been told, so a document implementing
        mixin.approval sees itself approved before the operation it gated
        runs. Once only: a withdrawal and a second approval do not run it again.
        """
        self.check_singleton()
        request = self.sudo()
        if (
            not request.binding_id
            or not request.binding_id.run_on_approval
            or request.date_binding_replayed
            or not request.res_model
            or not request.res_id
            or self.env.context.get("approval_binding_invoking")
        ):
            trace.BINDING.event(
                "replay_skipped",
                request=request.id,
                binding=request.binding_id.id,
                run_on_approval=request.binding_id.run_on_approval,
                replayed=bool(request.date_binding_replayed),
                invoking=bool(self.env.context.get("approval_binding_invoking")),
            )
            return
        trace.BINDING.note("replay", request=request.id, binding=request.binding_id.id)
        request.binding_id._replay(request)

    def _get_notifiable_source_document(self):
        """The adopting record to tell about this request, or None.

        A mixin.approval document is told only when it references this request back,
        so a stale res_id cannot drive a foreign record's workflow. A
        mixin.approval.subjects record is told about a request raised for one of its
        subjects, which carries its subject_key.
        """
        self.check_singleton()
        if not self.res_model or not self.res_id:
            trace.SYNC.event(
                "no_notifiable_source",
                request=self.id,
                why="no_reference",
                model=self.res_model or None,
                res_id=self.res_id or None,
            )
            return None
        try:
            source_doc = self.env[self.res_model].browse(self.res_id)
            mixin_cls = self.env.registry["mixin.approval"]
            subjects_cls = self.env.registry["mixin.approval.subjects"]
        except KeyError:
            _logger.debug(
                "Source model %s not in registry; skipping approval state notification",
                self.res_model,
            )
            return None
        if isinstance(source_doc, subjects_cls):
            if not self.subject_key or not source_doc.exists():
                trace.SYNC.event(
                    "no_notifiable_source",
                    request=self.id,
                    why="subject_key_missing" if not self.subject_key else "gone",
                    model=self.res_model,
                    res_id=self.res_id,
                )
                return None
            return source_doc.sudo().with_context(approval_acting_user_id=self.env.uid)
        if not isinstance(source_doc, mixin_cls):
            trace.SYNC.event(
                "no_notifiable_source",
                request=self.id,
                why="not_an_adopter",
                model=self.res_model,
                res_id=self.res_id,
            )
            return None
        if source_doc.approval_request_id != self:
            _logger.warning(
                "Approval request %s points at %s#%s but that document does "
                "not reference it back; skipping source notification.",
                self.id,
                self.res_model,
                self.res_id,
            )
            return None
        return source_doc.sudo().with_context(approval_acting_user_id=self.env.uid)

    def _is_subject_source(self, source_doc) -> bool:
        return isinstance(source_doc, self.env.registry["mixin.approval.subjects"])

    def _notify_source_document_state_change(self, new_state: str) -> None:
        self.check_singleton()
        source_doc = self._get_notifiable_source_document()
        if source_doc is None:
            trace.SYNC.event(
                "no_notifiable_source",
                request=self.id,
                model=self.res_model,
                res_id=self.res_id,
                state=new_state,
            )
            return
        trace.SYNC.note(
            "notify_state",
            request=self.id,
            model=self.res_model,
            res_id=self.res_id,
            state=new_state,
            subject=self.subject_key or None,
        )
        try:
            if self._is_subject_source(source_doc):
                source_doc._on_approval_subject_state_changed(self, new_state)
            else:
                source_doc._on_approval_state_changed(new_state)
        except MissingError:
            _logger.debug(
                "Could not notify source document %s#%s of approval state change",
                self.res_model,
                self.res_id,
            )

    def _notify_source_document_progress(self) -> None:
        self.check_singleton()
        source_doc = self._get_notifiable_source_document()
        if source_doc is None:
            return
        trace.SYNC.event(
            "notify_progress",
            request=self.id,
            model=self.res_model,
            res_id=self.res_id,
        )
        try:
            if self._is_subject_source(source_doc):
                source_doc._on_approval_subject_progress(self)
            else:
                source_doc._on_approval_progress()
        except MissingError:
            _logger.debug(
                "Could not notify source document %s#%s of approval progress",
                self.res_model,
                self.res_id,
            )

    _CYCLE_LOG_PREFIX = "approval-cycle"

    def _log_cycle(self, event: str, **details) -> None:
        if not _logger.isEnabledFor(logging.DEBUG):
            return
        self.check_singleton()
        rows = " ".join(
            f"{approver.user_id.login}={approver.state}"
            for approver in self.approver_ids.sorted(lambda a: (a.sequence, a.id))
        )
        extra = "".join(f" {key}={value}" for key, value in details.items())
        _logger.debug(
            "%s %s request=%s (%s) state=%s minimum=%s rows=[%s]%s",
            self._CYCLE_LOG_PREFIX,
            event,
            self.id,
            self.name or "draft",
            self.state,
            self.approval_minimum,
            rows,
            extra,
        )
