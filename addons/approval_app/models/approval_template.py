from typing import Any

from odoo import fields, models

from odoo.addons.approval.models import approval_trace as trace
from odoo.addons.base.models.mixin_catalog import name_uniq_index


class ApprovalTemplate(models.Model):
    _name = "approval.template"
    _inherit = ["mixin.catalog"]
    _description = "Approval Request Template"
    _order = "sequence, name"

    _name_src_uniq = name_uniq_index(
        "company_id",
        message="An approval template with this name already exists for this company.",
    )

    name = fields.Char(
        string="Template Name",
        help="Name of this template (e.g., 'Weekly Expense Report')",
    )
    sequence = fields.Integer(default=10)
    description = fields.Text(
        translate=True,
        help="Description shown to users when selecting this template",
    )
    category_id = fields.Many2one(
        comodel_name="approval.category",
        index=True,
        required=True,
        ondelete="cascade",
        help="Category this template creates requests for",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    default_reason = fields.Html(
        string="Default Description",
        translate=True,
        help="Pre-filled reason/description for the request",
    )
    default_amount = fields.Float()
    default_quantity = fields.Float()
    default_location = fields.Char()
    default_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Default Contact",
    )
    default_reference = fields.Char()
    default_priority = fields.Selection(
        selection=[
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Urgent"),
        ],
        default="1",
    )

    has_amount = fields.Selection(related="category_id.has_amount")
    has_quantity = fields.Selection(related="category_id.has_quantity")
    has_location = fields.Selection(related="category_id.has_location")
    has_partner = fields.Selection(related="category_id.has_partner")
    has_reference = fields.Selection(related="category_id.has_reference")

    usage_count = fields.Integer(
        string="Times Used",
        compute="_compute_usage_count",
        help="Number of requests created from this template",
    )

    def _compute_usage_count(self) -> None:
        if not self.ids:
            self.usage_count = 0
            return
        data = self.env["approval.request"]._read_group(
            domain=[("template_id", "in", self.ids)],
            groupby=["template_id"],
            aggregates=["__count"],
        )
        counts = {template.id: count for template, count in data}
        for template in self:
            template.usage_count = counts.get(template.id, 0)
        trace.TEMPLATE.event(
            "usage_count", n=len(self), used=len(counts), requests=sum(counts.values())
        )

    def action_create_request(self) -> dict[str, Any]:
        self.check_singleton()
        context = {
            "default_category_id": self.category_id.id,
            "default_template_id": self.id,
            "default_priority": self.default_priority,
        }

        if self.default_reason:
            context["default_reason"] = self.default_reason

        if self.category_id.has_amount != "no":
            context["default_amount"] = self.default_amount

        if self.category_id.has_quantity != "no":
            context["default_quantity"] = self.default_quantity

        if self.category_id.has_location != "no" and self.default_location:
            context["default_location"] = self.default_location

        if self.category_id.has_partner != "no" and self.default_partner_id:
            context["default_partner_id"] = self.default_partner_id.id

        if self.category_id.has_reference != "no" and self.default_reference:
            context["default_reference"] = self.default_reference

        trace.TEMPLATE.note(
            "request_defaults",
            template=self.id,
            category=self.category_id.id,
            defaults=sorted(context),
        )
        return {
            "name": self.env._("New Request from: %s", self.name),
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "view_mode": "form",
            "target": "current",
            "context": context,
        }

    def action_view_requests(self) -> dict[str, Any]:
        self.check_singleton()
        trace.TEMPLATE.note("view_requests", template=self.id)
        return {
            "name": self.env._("Requests from: %s", self.name),
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "view_mode": "list,form",
            "domain": [("template_id", "=", self.id)],
        }
