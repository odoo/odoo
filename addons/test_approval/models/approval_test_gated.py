from typing import Any

from odoo import fields, models
from odoo.exceptions import UserError


class ApprovalTestGated(models.Model):
    _name = "approval.test.gated"
    _description = "Test Document Gated on Its Own Operations"
    _inherit = ["mixin.mail.thread", "mixin.approval.gate"]
    _operation_checkpoints = {"action_ship": "_check_ship"}
    _approval_operations = ("action_ship", "action_bill")

    name = fields.Char(required=True)
    partner_id = fields.Many2one(comodel_name="res.partner")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    amount_total = fields.Monetary(currency_field="currency_id")
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    test_category_id = fields.Many2one(comodel_name="approval.category")
    state = fields.Selection(
        selection=[("draft", "Draft"), ("shipped", "Shipped"), ("billed", "Billed")],
        default="draft",
    )
    ship_count = fields.Integer(default=0)
    bill_count = fields.Integer(default=0)
    runs_on_approval = fields.Boolean(default=True)
    shipped_amount = fields.Monetary(currency_field="currency_id")

    def action_ship(self) -> Any:
        return self._run_through_approval("action_ship", self._ship)

    def action_ship_from_elsewhere(self) -> None:
        self._ship(self)

    def action_bill(self) -> Any:
        return self._run_through_approval("action_bill", self._bill)

    def _ship(self, records) -> bool:
        records._check_ship()
        for record in records:
            record.sudo().write(
                {
                    "ship_count": record.ship_count + 1,
                    "shipped_amount": record.amount_total,
                    "state": "shipped",
                }
            )
        return True

    def _bill(self, records) -> bool:
        for record in records:
            record.sudo().write(
                {"bill_count": record.bill_count + 1, "state": "billed"}
            )
        return True

    def _check_ship(self) -> None:
        self._check_approval_admits("action_ship")

    def _check_approval_covers(self, operation: str) -> None:
        super()._check_approval_covers(operation)
        approved = self.approval_request_id.amount
        if approved and self.currency_id.compare_amounts(self.amount_total, approved):
            raise UserError(
                self.env._(
                    "%(name)s changed after its approval: %(approved)s was approved, "
                    "%(current)s is there now.",
                    name=self.display_name,
                    approved=approved,
                    current=self.amount_total,
                )
            )

    def _is_operation_run_on_approval(self, operation: str) -> bool:
        return self.runs_on_approval

    def _get_domain_approval_category(self) -> list[Any]:
        return [("id", "=", self.test_category_id.id)] if self.test_category_id else []

    def _get_fields_approval_required(self) -> list[str]:
        return ["name", "partner_id"]

    def _prepare_approval_request_values(self, category) -> dict[str, Any]:
        values = super()._prepare_approval_request_values(category)
        values["amount"] = self.amount_total
        return values
