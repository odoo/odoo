from odoo import fields, models

from . import approval_trace as trace
from odoo.addons.base.models.mixin_catalog import name_uniq_index


class ApprovalRefusalReason(models.Model):
    _name = "approval.refusal.reason"
    _inherit = ["mixin.catalog"]
    _description = "Approval Refusal Reason"
    _order = "sequence, name"
    _check_company_auto = True

    _name_src_uniq = name_uniq_index(
        "company_id",
        message="A refusal reason with this name already exists for this company.",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=False,
        index=True,
        help="Leave empty to make this reason available to all companies. "
        "Set a company to restrict this reason to that company only.",
    )
    name = fields.Char(
        string="Reason",
        help="Short description of the refusal reason (e.g., 'Missing Documentation', 'Budget Exceeded')",
    )
    active = fields.Boolean(
        help="Inactive reasons are hidden but preserved for historical records"
    )
    sequence = fields.Integer(
        default=10,
        help="Order in which reasons appear in selection lists (lower = first)",
    )
    description = fields.Text(
        string="Detailed Description",
        translate=True,
        help="Optional detailed explanation of when this reason should be used",
    )
    category_ids = fields.Many2many(
        comodel_name="approval.category",
        relation="approval_category_refusal_reason_rel",
        column1="reason_id",
        column2="category_id",
        string="Applicable Categories",
        check_company=True,
        help="Leave empty to make this reason available for all categories. "
        "Select specific categories to restrict availability.",
    )

    usage_count = fields.Integer(
        string="Times Used",
        compute="_compute_usage_count",
        help="Number of times this reason has been used",
    )

    def _compute_usage_count(self):
        if not self:
            return
        counts = {
            reason.id: count
            for reason, count in self.env["approval.request"]._read_group(
                domain=[("refusal_reason_id", "in", self.ids)],
                groupby=["refusal_reason_id"],
                aggregates=["__count"],
            )
        }
        for reason in self:
            reason.usage_count = counts.get(reason.id, 0)
        trace.COMPUTE.event(
            "refusal_reason_usage_count",
            n=len(self),
            used=len(counts),
            requests=sum(counts.values()),
        )
