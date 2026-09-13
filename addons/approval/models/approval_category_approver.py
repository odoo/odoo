from odoo import api, fields, models
from odoo.exceptions import ValidationError

from . import approval_trace as trace


class ApprovalCategoryApprover(models.Model):
    _name = "approval.category.approver"
    _description = "Approval Category Approver"
    _order = "sequence"
    _rec_name = "user_id"

    _category_user_uniq = models.Constraint(
        "unique(category_id, user_id)",
        "A user may not be in the approver list of a category multiple times.",
    )

    category_id = fields.Many2one(
        comodel_name="approval.category",
        string="Approval Category",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="category_id.company_id",
        store=True,
        index=True,
        readonly=True,
        help="Mirrors the category's company; scopes the "
        "multi-company ir.rule on this model.",
    )
    existing_user_ids = fields.Many2many(
        comodel_name="res.users",
        compute="_compute_existing_user_ids",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        index=True,
        required=True,
        domain="[('id', 'not in', existing_user_ids)]",
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    required = fields.Boolean(default=False)

    @api.constrains("category_id", "user_id", "required", "sequence")
    def _check_category_routes_by_its_list(self):
        for row in self:
            if row.category_id.step_ids:
                trace.REFUSAL.event(
                    "category_approver_on_steps",
                    row=row.id,
                    category=row.category_id.id,
                    user=row.user_id.id,
                )
                raise ValidationError(
                    self.env._(
                        "'%(category)s' routes its requests by steps, so its approver "
                        "list is not read: add %(user)s to one of its steps instead.",
                        category=row.category_id.name,
                        user=row.user_id.name,
                    ),
                )

    @api.constrains("category_id", "user_id", "required")
    def _check_category_coherence(self):
        self.category_id._constrains_approval_minimum()

    @api.constrains("category_id", "user_id")
    def _check_user_in_category_company(self):
        for row in self:
            company = row.category_id.company_id
            if company and company not in row.user_id.company_ids:
                trace.REFUSAL.event(
                    "category_approver_other_company",
                    row=row.id,
                    category=row.category_id.id,
                    user=row.user_id.id,
                    company=company.id,
                )
                raise ValidationError(
                    self.env._(
                        "%(user)s does not belong to company %(company)s, so "
                        "they cannot approve requests of category "
                        "'%(category)s'. Add the company to the user or "
                        "choose another approver.",
                        user=row.user_id.name,
                        company=company.name,
                        category=row.category_id.name,
                    ),
                )

    @api.depends("category_id", "category_id.approver_ids.user_id")
    def _compute_existing_user_ids(self):
        for record in self:
            if record.category_id:
                record.existing_user_ids = record.category_id.approver_ids.user_id
            else:
                record.existing_user_ids = self.env["res.users"]
