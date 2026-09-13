from odoo import models
from odoo.exceptions import UserError

from . import approval_trace as trace

ACCESS_SUBJECT_PREFIX = "access"


class MixinApprovalAccess(models.AbstractModel):
    _name = "mixin.approval.access"
    _inherit = ["mixin.approval.subjects"]
    _description = "Record Whose Access Is Asked For Through Approval"

    _access_approval_category = ""

    def _get_access_subject_key(self, partner, role=False) -> str:
        if role:
            return f"{ACCESS_SUBJECT_PREFIX}:{partner.id}:{role}"
        return f"{ACCESS_SUBJECT_PREFIX}:{partner.id}"

    def _get_access_subject(self, subject_key: str) -> tuple:
        prefix, _separator, rest = (subject_key or "").partition(":")
        partner_id, _separator, role = rest.partition(":")
        if prefix != ACCESS_SUBJECT_PREFIX or not partner_id.isdigit():
            return self.env["res.partner"], False
        partner = self.env["res.partner"].browse(int(partner_id)).exists()
        return partner, role or False

    def _get_approval_subject_category(self, subject_key):
        if not self._access_approval_category:
            return self.env["approval.category"]
        return self.env.ref(self._access_approval_category, raise_if_not_found=False)

    def _get_access_request_name(self, partner, role) -> str:
        return self.env._(
            "Access to %(record)s for %(partner)s",
            record=self.display_name,
            partner=partner.name,
        )

    def _prepare_approval_subject_request_values(self, subject_key, category):
        vals = super()._prepare_approval_subject_request_values(subject_key, category)
        partner, role = self._get_access_subject(subject_key)
        if partner:
            vals["name"] = self._get_access_request_name(partner, role)
        return vals

    def _on_approval_subject_state_changed(self, request, new_state):
        super()._on_approval_subject_state_changed(request, new_state)
        if new_state != "approved":
            return
        partner, role = self._get_access_subject(request.subject_key)
        trace.SUBJECTS.note(
            "access_granted",
            record=self,
            request=request.id,
            partner=partner.id or None,
            role=role,
        )
        if partner:
            self._grant_access(partner, role)

    def _has_access(self, partner, role=False) -> bool:
        raise NotImplementedError

    def _grant_access(self, partner, role=False) -> None:
        raise NotImplementedError

    def _get_live_access_request(self, partner, role=False):
        self.check_singleton()
        return self.sudo()._get_live_approval_request(
            self._get_access_subject_key(partner, role)
        )

    def _request_access(self, partner, role=False):
        self.check_singleton()
        if self._has_access(partner, role):
            trace.REFUSAL.event(
                "access_already_held",
                record=self,
                partner=partner.id,
                role=role,
            )
            raise UserError(
                self.env._(
                    "%(partner)s already has this access to %(record)s.",
                    partner=partner.name,
                    record=self.display_name,
                )
            )
        return self._raise_approval_request(self._get_access_subject_key(partner, role))

    def _decide_access_request(self, partner, role, approve: bool) -> bool:
        self.check_singleton()
        request = self._get_live_access_request(partner, role)
        if not request:
            return False
        rows = request._get_rows_decidable_by(self.env.user)
        trace.SUBJECTS.event(
            "access_decided",
            record=self,
            request=request.id,
            approve=approve,
            as_approver=bool(rows),
            uid=self.env.uid,
        )
        if rows:
            if approve:
                request.action_approve(approver=rows)
            else:
                request.action_refuse(approver=rows)
            return True
        self.check_access("write")
        if approve:
            request._approve_without_decision(
                self.env._(
                    "%(user)s granted %(partner)s access to %(record)s.",
                    user=self.env.user.name,
                    partner=partner.name,
                    record=self.display_name,
                )
            )
        else:
            request._force_terminal(
                "refused",
                self.env._(
                    "%(user)s refused %(partner)s access to %(record)s.",
                    user=self.env.user.name,
                    partner=partner.name,
                    record=self.display_name,
                ),
            )
        return True
