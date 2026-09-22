from typing import Any

from odoo import fields, models


class ApprovalTestLifecycle(models.Model):
    _name = "approval.test.lifecycle"
    _description = "Test Document Confirmed Through Approval"
    _inherit = ["mixin.mail.thread", "mixin.approval.lifecycle"]
    _STATE_TRANSITIONS = {
        "draft": {"done", "cancel"},
        "done": {"closed", "cancel"},
        "closed": set(),
        "cancel": {"draft"},
    }

    name = fields.Char(required=True)
    partner_id = fields.Many2one(comodel_name="res.partner")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    test_category_id = fields.Many2one(comodel_name="approval.category")
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("done", "Confirmed"),
            ("closed", "Closed"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
    )
    date_confirmed = fields.Datetime()

    def _prepare_confirmation_values(self) -> dict[str, Any]:
        return {"state": "done", "date_confirmed": fields.Datetime.now()}

    def _get_domain_approval_category(self) -> list[Any]:
        return [("id", "=", self.test_category_id.id)] if self.test_category_id else []

    def _get_fields_approval_required(self) -> list[str]:
        return ["name", "partner_id"]
