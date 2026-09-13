from typing import Any

from odoo import fields, models


class ApprovalTestDocument(models.Model):
    _name = "approval.test.document"
    _description = "Test Document for Approval Mixin"
    _inherit = ["mixin.mail.thread", "mixin.approval"]
    _operation_checkpoints = {"action_record_operation": "_check_record_operation"}

    name = fields.Char(
        required=True,
        tracking=True,
    )
    description = fields.Text()
    amount = fields.Float(tracking=True)
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    amount_total = fields.Monetary(currency_field="currency_id")
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    hook_call_count = fields.Integer(
        default=0,
        help="Tracks how many times _on_approval_state_changed was called",
    )
    last_approval_state = fields.Char(
        help="Records the last state received by _on_approval_state_changed"
    )
    progress_call_count = fields.Integer(
        default=0,
        help="How many times _on_approval_progress was called",
    )
    test_category_id = fields.Many2one(
        comodel_name="approval.category",
        help="Category to use for approval (for testing)",
    )
    protected_field_names = fields.Char(
        help="Comma-separated fields this document protects, for the tests"
    )
    keeps_approval_on_change = fields.Boolean()
    operation_count = fields.Integer(
        default=0,
        help="How many times action_record_operation actually ran",
    )

    def action_record_operation(self) -> None:
        self._record_operation()

    def action_record_operation_from_list(self) -> dict[str, Any]:
        self._record_operation()
        return {"type": "ir.actions.act_window_close"}

    def _record_operation(self) -> None:
        self._check_record_operation()
        for document in self:
            document.sudo().operation_count += 1

    def _check_record_operation(self) -> None:
        return

    def _get_domain_approval_category(self) -> list[Any]:
        if self.test_category_id:
            return [("id", "=", self.test_category_id.id)]
        return []

    def _get_fields_approval_protected(self) -> list[str]:
        return (self.protected_field_names or "").split(",") if self else []

    def _is_approval_invalidated_by_changes(self, fields_changed) -> bool:
        return not self.keeps_approval_on_change

    def _get_fields_approval_required(self) -> list[str]:
        return ["name", "partner_id"]

    def _get_approval_request_name(self) -> str:
        return f"Test Document Approval: {self.name}"

    def _on_approval_state_changed(self, new_state: str) -> None:
        self.sudo().write(
            {
                "hook_call_count": self.hook_call_count + 1,
                "last_approval_state": new_state,
            }
        )

        if new_state == "approved":
            self.sudo().state = "approved"
        elif new_state == "refused":
            self.sudo().state = "rejected"

        super()._on_approval_state_changed(new_state)

    def _on_approval_progress(self) -> None:
        self.sudo().progress_call_count += 1
