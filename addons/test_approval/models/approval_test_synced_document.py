from typing import Any

from odoo import fields, models
from odoo.exceptions import UserError

SYNC_KINDS = {
    "draft": "draft",
    "submitted": "pending",
    "first": "progress",
    "approved": "approved",
    "refused": "refused",
    "cancelled": "cancelled",
}
OUTCOME_STATES = {
    "progress": "first",
    "approved": "approved",
    "refused": "refused",
    "cancelled": "cancelled",
}


class ApprovalTestSyncedDocument(models.Model):
    _name = "approval.test.synced.document"
    _description = "Test Document Whose State Drives Its Approval"
    _inherit = ["mixin.mail.thread", "mixin.approval.state.sync"]

    name = fields.Char(required=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("first", "First Step Approved"),
            ("approved", "Approved"),
            ("refused", "Refused"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    test_category_id = fields.Many2one(comodel_name="approval.category")
    policy_refusal = fields.Char(
        help="When set, the document's own policy refuses every decision with it"
    )
    applied_outcomes = fields.Char(
        default="",
        help="Each outcome the request applied to this document, in order",
    )
    never_requests = fields.Boolean(
        help="The adopter's own exclusion: this document never holds a request"
    )
    asking_activity_type_id = fields.Many2one(
        comodel_name="mail.activity.type",
        help="When set, the activity type this document asks every approver with",
    )
    first_decider_id = fields.Many2one(
        comodel_name="res.users",
        help="Who decided the first step before a request existed, for the backfill",
    )
    blocked_user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="approval_test_synced_document_blocked_user_rel",
        column1="document_id",
        column2="user_id",
        help="Users the document's own policy would refuse, kept off its steps",
    )

    def _get_domain_approval_category(self) -> list[Any]:
        if self.test_category_id:
            return [("id", "=", self.test_category_id.id)]
        return []

    def _get_fields_approval_required(self) -> list[str]:
        return ["name"]

    def _get_approval_sync_kinds(self) -> dict[Any, str]:
        return dict(SYNC_KINDS)

    def _can_raise_approval_request(self) -> bool:
        return super()._can_raise_approval_request() and not self.never_requests

    def _get_approval_activity_type(self, approver, step_type):
        return self.asking_activity_type_id or step_type

    def _get_approval_backfill_decider(self):
        return self.first_decider_id

    def _filter_approval_step_user_ids(self, step, user_ids: set[int]) -> set[int]:
        return user_ids - set(self.blocked_user_ids.ids)

    def _check_approval_sync_policy(self, kind: str) -> None:
        if self.policy_refusal:
            raise UserError(self.policy_refusal)

    def _apply_approval_sync_outcome(self, kind: str) -> None:
        self.check_singleton()
        self.sudo().write(
            {
                "state": OUTCOME_STATES[kind],
                "applied_outcomes": f"{self.applied_outcomes}{kind};",
            }
        )
