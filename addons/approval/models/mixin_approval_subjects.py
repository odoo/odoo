from typing import Any

from odoo import fields, models
from odoo.exceptions import UserError

from . import approval_trace as trace

LIVE_REQUEST_STATES = ("new", "pending")


class MixinApprovalSubjects(models.AbstractModel):
    """A record holding one approval request per subject, rather than one in all.

    A course holds a request for each partner asking to join it; an engineering change
    holds a request for each stage it passes. A request carries its subject in
    ``subject_key``, and only one request per subject is waiting at a time.
    """

    _name = "mixin.approval.subjects"
    _inherit = ["mixin.approval.source"]
    _description = "Record Holding One Approval Request per Subject"

    approval_request_ids = fields.One2many(
        comodel_name="approval.request",
        inverse_name="res_id",
        string="Approval Requests",
        copy=False,
        readonly=True,
        domain=lambda self: [
            ("res_model", "=", self._name),
            ("subject_key", "!=", False),
        ],
    )

    def _get_approval_subject_category(self, subject_key: str):
        """The category a request for `subject_key` belongs to."""
        raise NotImplementedError

    def _prepare_approval_subject_request_values(
        self, subject_key: str, category
    ) -> dict[str, Any]:
        self.check_singleton()
        vals = {
            "name": self.display_name,
            "category_id": category.id,
            "request_owner_id": self.env.user.id,
            "res_model": self._name,
            "res_id": self.id,
            "subject_key": subject_key,
        }
        if "company_id" in self._fields and self.company_id:
            vals["company_id"] = self.company_id.id
        return vals

    def _get_approval_request(self, subject_key: str):
        """The latest request raised for `subject_key`, whatever its state."""
        self.check_singleton()
        request = (
            self.env["approval.request"]
            .sudo()
            .search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", self.id),
                    ("subject_key", "=", subject_key),
                ],
                order="id desc",
                limit=1,
            )
        )
        trace.SUBJECTS.event(
            "request_lookup",
            record=self,
            subject=subject_key,
            request=request.id or None,
            state=request.state if request else None,
        )
        return request

    def _get_live_approval_request(self, subject_key: str):
        request = self._get_approval_request(subject_key)
        return request if request.state in LIVE_REQUEST_STATES else request.browse()

    def _raise_approval_request(self, subject_key: str):
        """Raise and submit the request for `subject_key`, as the current user.

        Refused while a request for the same subject is still waiting.
        """
        self.check_singleton()
        if self._get_live_approval_request(subject_key):
            trace.REFUSAL.event(
                "subject_already_waiting",
                record=self,
                subject=subject_key,
            )
            raise UserError(
                self.env._(
                    "%(record)s already has an approval request waiting for this.",
                    record=self.display_name,
                )
            )
        category = self._get_approval_subject_category(subject_key)
        if not category:
            trace.REFUSAL.event(
                "subject_no_category",
                record=self,
                subject=subject_key,
            )
            raise UserError(
                self.env._(
                    "No approval category applies to %(record)s.",
                    record=self.display_name,
                )
            )
        request = (
            self.env["approval.request"]
            .sudo()
            .create(
                self._prepare_approval_subject_request_values(subject_key, category)
            )
        )
        trace.SUBJECTS.note(
            "request_raised",
            record=self,
            subject=subject_key,
            category=category.id,
            request=request.id,
        )
        request.action_confirm()
        return request

    def _on_approval_subject_state_changed(self, request, new_state: str) -> None:
        """`request`, raised for one of this record's subjects, reached `new_state`."""
        self.check_singleton()

    def _on_approval_subject_progress(self, request) -> None:
        """A decision met a step of `request`, which is still pending."""
        self.check_singleton()
