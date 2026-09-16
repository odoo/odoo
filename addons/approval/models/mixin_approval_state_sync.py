from typing import Any

from odoo import SUPERUSER_ID, api, models

from . import approval_trace as trace
from .approval_utils import ApprovalStepUnstaffed

SYNC_CONTEXT_KEY = "approval_state_sync"


class MixinApprovalStateSync(models.AbstractModel):
    _name = "mixin.approval.state.sync"
    _inherit = ["mixin.approval"]
    _description = "Approval Request Following Its Document's State"
    _approval_request_follows_document = True

    def _get_approval_sync_state_field(self) -> str:
        return "state"

    def _get_approval_sync_kinds(self) -> dict[Any, str]:
        """Each value of the state field, mapped to what it means for the request.

        Kinds: ``pending`` (awaiting approval), ``progress`` (a first step approved),
        ``approved``, ``refused``, ``cancelled`` and ``draft`` (not submitted).
        """
        raise NotImplementedError

    def _get_approval_sync_kind(self) -> str | None:
        self.check_singleton()
        field = self._get_approval_sync_state_field()
        kinds = self._get_approval_sync_kinds()
        value = self[field]
        kind = kinds.get(value)
        if kind is None:
            trace.DEGRADED.event(
                "sync_state_unmapped",
                record=self,
                field=field,
                value=value,
                mapped=sorted(kinds, key=repr),
            )
        return kind

    def _check_approval_sync_policy(self, kind: str) -> None:
        return

    def _apply_approval_sync_outcome(self, kind: str) -> None:
        raise NotImplementedError

    def _get_approval_category_xmlid(self) -> str | None:
        return None

    def _get_domain_approval_category(self) -> list[Any]:
        xmlid = self._get_approval_category_xmlid()
        category = xmlid and self.env.ref(xmlid, raise_if_not_found=False)
        if category:
            trace.SYNC.event(
                "category_by_xmlid", record=self, xmlid=xmlid, category=category.id
            )
            return [("id", "=", category.id)]
        if xmlid:
            trace.DEGRADED.event("category_xmlid_missing", record=self, xmlid=xmlid)
        return super()._get_domain_approval_category()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._create_approval_requests()
        return records

    def write(self, vals):
        field = self._get_approval_sync_state_field()
        if field not in vals:
            return super().write(vals)
        previous = {record.id: record[field] for record in self.sudo()}
        result = super().write(vals)
        synced = self.env.context.get(SYNC_CONTEXT_KEY, ())
        moved = self.browse(
            [
                record.id
                for record in self.sudo()
                if record[field] != previous[record.id]
            ]
        )
        with_request = moved.filtered(
            lambda record: (
                record.sudo().approval_request_id
                and record.sudo().approval_request_id.id not in synced
            )
        )
        trace.SYNC.event(
            "document_moved",
            record=self,
            field=field,
            moved=moved.ids,
            with_request=with_request.ids,
            already_synced=list(synced),
        )
        with_request._sync_approval_request()
        (
            moved.filtered(lambda record: not record.sudo().approval_request_id)
        )._create_approval_requests()
        return result

    def unlink(self):
        for record in self.sudo().filtered(
            lambda record: record.approval_request_id.state == "pending"
        ):
            record._get_synced_approval_request()._force_terminal(
                "cancelled",
                self.env._(
                    "%(user)s deleted %(record)s.",
                    user=self.env.user.name,
                    record=record.display_name,
                ),
            )
        return super().unlink()

    def _is_approval_request_required(self) -> bool:
        self.check_singleton()
        kind = self._get_approval_sync_kind()
        can_raise = kind == "pending" and self._can_raise_approval_request()
        trace.SYNC.event(
            "request_needed",
            record=self,
            kind=kind,
            has_request=bool(self.approval_request_id),
            needed=can_raise,
        )
        return can_raise

    def _can_raise_approval_request(self) -> bool:
        """Whether this document may hold a request at all; adopters add their own
        exclusions here, whatever state the document is in."""
        self.check_singleton()
        return not self.approval_request_id and self.approval_required

    def _get_legacy_approval_activity_xmlids(self) -> tuple[str, ...]:
        """The review activities the document scheduled itself before it adopted the
        engine, which a backfilled request replaces."""
        return ()

    def _get_approval_backfill_decider(self):
        """Who decided the first step of a document in progress before its request
        existed."""
        return self.env["res.users"]

    def _backfill_approval_requests(self):
        """Raise the request each document already in flight would have raised.

        For an upgrade: it runs as the superuser, whom _create_approval_requests
        skips. A document that cannot request approval is left alone rather than
        failing the upgrade. Returns the documents that got a request.
        """
        backfilled = self.browse()
        for record in self.sudo():
            kind = record._get_approval_sync_kind()
            if (
                kind not in ("pending", "progress")
                or not record._can_raise_approval_request()
                or not record.can_request_approval
            ):
                trace.SYNC.event(
                    "backfill_skipped",
                    record=record,
                    kind=kind,
                    can_raise=record._can_raise_approval_request(),
                    can_request=record.can_request_approval,
                )
                continue
            xmlids = record._get_legacy_approval_activity_xmlids()
            if xmlids and "activity_ids" in record._fields:
                record.activity_unlink(list(xmlids))
            record.action_create_approval_request()
            if kind == "progress":
                record._backfill_approval_progress()
            backfilled |= record
        trace.SYNC.note(
            "backfilled",
            records=self,
            raised=len(backfilled),
        )
        trace.annotate(work=len(backfilled))
        return backfilled

    def _backfill_approval_progress(self) -> None:
        self.check_singleton()
        request = self._get_synced_approval_request()
        decider = self._get_approval_backfill_decider()
        trace.SYNC.event(
            "backfill_progress",
            record=self,
            request=request.id,
            decider=decider.id if decider else None,
        )
        steps = request._get_open_steps()
        rows = (
            request._get_rows_decidable_by(decider).filtered(
                lambda row: steps <= row.step_ids
            )
            if decider
            else request.approver_ids.browse()
        )
        if rows:
            request.action_approve(approver=rows, steps=steps)
            return
        self.message_post(
            body=self.env._(
                "%(user)s decided the first step before this approval request existed "
                "and holds no row on it, so that step is open again.",
                user=decider.name or self.env._("An approver"),
            ),
            message_type="notification",
        )

    def _create_approval_requests(self) -> None:
        # The superuser is the system: what it creates or moves (crons, fast paths,
        # data) keeps the direct flow. A user's sudo() keeps their uid, so it still asks.
        if self.env.uid == SUPERUSER_ID or self.env.context.get("import_file"):
            return
        for record in self.sudo():
            needs = record._is_approval_request_required()
            trace.SYNC.event(
                "raise_on_create",
                model=record._name,
                res_id=record.id,
                kind=record._get_approval_sync_kind(),
                raises=needs,
            )
            if needs:
                record._raise_approval_request_on_create()

    def _raise_approval_request_on_create(self) -> None:
        """Raise this record's request, and survive a company that staffs no step.

        Whoever creates a document rarely governs who may approve it: an employee
        asking for time off in a company that has named no time-off officer cannot
        appoint one. A step every one of whose approvers works in another company
        is that gap, and it belongs to the configuration, not to the document being
        recorded -- the refusal used to travel out of the automatic create and
        refuse the document itself. The document is kept, says why it has no
        request yet, and the backfill raises one once the company staffs the step.

        Every other refusal still reaches the caller, the document's own approval
        policy emptying a step included: that one is the document's to answer for.
        """
        self.check_singleton()
        # Flush before the savepoint, so what is already pending is checked in the
        # env that produced it rather than by the savepoint's own flush.
        self.env.flush_all()
        try:
            with self.env.cr.savepoint():
                self.action_create_approval_request()
        except ApprovalStepUnstaffed as error:
            trace.SYNC.event(
                "raise_on_create_refused",
                record=self,
                kind=self._get_approval_sync_kind(),
                reason=str(error),
            )
            self.message_post(
                body=self.env._(
                    "No approval request could be raised for this document yet: "
                    "%(reason)s",
                    reason=str(error),
                ),
                message_type="notification",
            )

    def _get_synced_approval_request(self):
        self.check_singleton()
        request = self.sudo().approval_request_id
        synced = self.env.context.get(SYNC_CONTEXT_KEY, ())
        return request.with_context(**{SYNC_CONTEXT_KEY: (*synced, request.id)})

    def _is_synced_with_approval_request(self) -> bool:
        self.check_singleton()
        synced = self.env.context.get(SYNC_CONTEXT_KEY, ())
        reentrant = self.approval_request_id.id in synced
        if reentrant:
            trace.SYNC.event(
                "sync_reentry_blocked",
                record=self,
                request=self.approval_request_id.id,
                depth=len(synced),
            )
        return reentrant

    def _restart_approval_request(self, request) -> None:
        trace.SYNC.note(
            "restart_request",
            record=self,
            request=request.id,
            was=request.state,
            forced_draft=request.state != "new",
        )
        if request.state != "new":
            request._force_draft()
        request.action_confirm()

    def _sync_approval_request(self) -> None:
        user = self.env.user
        decides = self.env.uid != SUPERUSER_ID
        for record in self:
            request = record._get_synced_approval_request()
            kind = record._get_approval_sync_kind()
            trace.SYNC.note(
                "sync_request",
                model=record._name,
                res_id=record.id,
                request=request.id,
                kind=kind,
                request_state=request.state,
                decides=decides,
            )
            if kind == "pending":
                record._restart_approval_request(request)
            elif kind == "draft":
                if request.state != "new":
                    request._force_draft()
            elif kind in ("progress", "approved"):
                record._sync_approval_request_approval(request, user, decides, kind)
            elif kind in ("refused", "cancelled"):
                record._sync_approval_request_ending(request, user, decides, kind)

    def _sync_approval_request_approval(self, request, user, decides, kind) -> None:
        self.check_singleton()
        if request.state in ("new", "refused", "cancelled"):
            self._restart_approval_request(request)
        if request.state != "pending":
            return
        rows = (
            request._get_rows_decidable_by(user)
            if decides
            else request.approver_ids.browse()
        )
        if kind == "progress":
            steps = request._get_open_steps()
            rows = rows.filtered(lambda row: steps <= row.step_ids)
            trace.SYNC.event(
                "sync_progress",
                request=request.id,
                steps=steps.ids,
                rows=rows.ids,
                user=user.id,
            )
            if rows:
                request.action_approve(approver=rows, steps=steps)
            return
        if rows:
            request.action_approve(approver=rows)
        trace.SYNC.event(
            "sync_approved",
            request=request.id,
            rows=rows.ids,
            state=request.state,
            grants=request.state == "pending",
        )
        if request.state == "pending":
            request._approve_without_decision(
                self.env._(
                    "%(user)s approved %(record)s without an approver's decision.",
                    user=user.name,
                    record=self.display_name,
                )
            )

    def _sync_approval_request_ending(self, request, user, decides, kind) -> None:
        self.check_singleton()
        refused = kind == "refused"
        target = "refused" if refused else "cancelled"
        note = self.env.context.get("approval_refusal_note") if refused else None
        if request.state == "approved":
            request._revoke(
                target,
                self.env._(
                    "%(user)s refused %(record)s after it was approved.",
                    user=user.name,
                    record=self.display_name,
                )
                if refused
                else self.env._(
                    "%(user)s cancelled %(record)s after it was approved.",
                    user=user.name,
                    record=self.display_name,
                ),
                refusal_note=note,
            )
            return
        if request.state not in ("new", "pending"):
            return
        rows = (
            request._get_current_pending_approver(user)
            if decides and refused and request.state == "pending"
            else request.approver_ids.browse()
        )
        trace.SYNC.event(
            "sync_ending",
            request=request.id,
            target=target,
            state=request.state,
            rows=rows.ids,
            noted=bool(note),
        )
        if rows:
            request.action_refuse(approver=rows)
            if note:
                request._stamp_refusal_metadata(None, note)
            return
        request._force_terminal(
            target,
            self.env._(
                "%(user)s refused %(record)s.", user=user.name, record=self.display_name
            )
            if refused
            else self.env._(
                "%(user)s cancelled %(record)s.",
                user=user.name,
                record=self.display_name,
            ),
            refusal_note=note,
        )

    def _apply_approval_outcome(self, kind: str, decided: bool = True) -> None:
        self.check_singleton()
        trace.SYNC.note(
            "apply_outcome",
            record=self,
            kind=kind,
            decided=decided,
            request=self.approval_request_id.id,
        )
        checks_policy = decided and self.env.uid != SUPERUSER_ID
        trace.SYNC.event(
            "sync_policy",
            record=self,
            kind=kind,
            checked=checks_policy,
            uid=self.env.uid,
        )
        if checks_policy:
            self.sudo(False)._check_approval_sync_policy(kind)
        synced = self.env.context.get(SYNC_CONTEXT_KEY, ())
        self.with_context(
            **{SYNC_CONTEXT_KEY: (*synced, self.approval_request_id.id)}
        )._apply_approval_sync_outcome(kind)

    def _on_approval_progress(self) -> None:
        if (
            not self._is_synced_with_approval_request()
            and self._get_approval_sync_kind() == "pending"
        ):
            self._apply_approval_outcome("progress")

    def _on_approval_approved(self) -> None:
        if (
            not self._is_synced_with_approval_request()
            and self._get_approval_sync_kind() != "approved"
        ):
            self._apply_approval_outcome("approved")

    def _on_approval_refused(self) -> None:
        if (
            not self._is_synced_with_approval_request()
            and self._get_approval_sync_kind() != "refused"
        ):
            self._apply_approval_outcome("refused")

    def _on_approval_cancelled(self) -> None:
        if not self._is_synced_with_approval_request() and (
            self._get_approval_sync_kind() not in ("cancelled", "refused")
        ):
            self._apply_approval_outcome("cancelled", decided=False)

    def _on_approval_reset(self) -> None:
        if not self._is_synced_with_approval_request():
            super()._on_approval_reset()

    def _on_approval_revoked(self) -> None:
        if not self._is_synced_with_approval_request():
            super()._on_approval_revoked()
