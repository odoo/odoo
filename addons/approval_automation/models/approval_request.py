from odoo import fields, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    has_automation = fields.Selection(related="category_id.has_automation")
    automation_id = fields.Many2one(related="category_id.automation_id")
    automation_runtime_id = fields.Many2one(
        comodel_name="automation.runtime",
        index="btree_not_null",
    )
