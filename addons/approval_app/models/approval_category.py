from typing import Any

from odoo import fields, models

from odoo.addons.approval.models import approval_trace as trace
from odoo.addons.approval.models.approval_category import CATEGORY_SELECTION


class ApprovalCategory(models.Model):
    _inherit = "approval.category"

    has_date = fields.Selection(
        selection=CATEGORY_SELECTION,
        default="no",
        required=True,
        tracking=True,
    )
    has_date_deadline = fields.Selection(
        selection=CATEGORY_SELECTION,
        default="no",
        required=True,
        tracking=True,
    )
    has_date_planned = fields.Selection(
        selection=CATEGORY_SELECTION,
        default="no",
        required=True,
        tracking=True,
    )
    has_date_range = fields.Selection(
        selection=CATEGORY_SELECTION,
        default="no",
        required=True,
        tracking=True,
    )
    has_partner = fields.Selection(
        selection=CATEGORY_SELECTION,
        string="Has Contact",
        default="no",
        required=True,
        tracking=True,
    )
    has_quantity = fields.Selection(
        selection=CATEGORY_SELECTION,
        default="no",
        required=True,
        tracking=True,
    )
    has_amount = fields.Selection(
        selection=CATEGORY_SELECTION,
        default="no",
        required=True,
        tracking=True,
    )
    has_reference = fields.Selection(
        selection=CATEGORY_SELECTION,
        default="no",
        required=True,
        tracking=True,
        help="An additional reference that should be specified on the request.",
    )
    has_location = fields.Selection(
        selection=CATEGORY_SELECTION,
        default="no",
        required=True,
        tracking=True,
    )
    has_document = fields.Selection(
        selection=[
            ("required", "Required"),
            ("optional", "Optional"),
        ],
        string="Documents",
        default="optional",
        required=True,
        tracking=True,
    )
    document_requirement_ids = fields.One2many(
        comodel_name="approval.document.requirement",
        inverse_name="category_id",
        string="Document Requirements",
    )
    template_count = fields.Integer(
        compute="_compute_template_count",
        help="Number of active templates",
    )

    def _compute_template_count(self) -> None:
        data = self.env["approval.template"]._read_group(
            [("category_id", "in", self.ids), ("active", "=", True)],
            ["category_id"],
            ["__count"],
        )
        mapped = {cat.id: count for cat, count in data}
        for category in self:
            category.template_count = mapped.get(category.id, 0)
        trace.TEMPLATE.event(
            "template_count",
            n=len(self),
            with_templates=len(mapped),
            templates=sum(mapped.values()),
        )

    def view_templates(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "name": self.env._("Templates: %s", self.name),
            "type": "ir.actions.act_window",
            "res_model": "approval.template",
            "view_mode": "list,form",
            "domain": [("category_id", "=", self.id)],
            "context": {"default_category_id": self.id},
        }
