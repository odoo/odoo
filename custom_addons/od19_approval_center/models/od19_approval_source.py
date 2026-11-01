from odoo import fields, models


class Od19ApprovalSource(models.Model):
    _name = "od19.approval.source"
    _description = "Approval Center Source"
    _order = "sequence, id"

    OD19_MAX_RECORDS = 500

    name = fields.Char(required=True)
    model_id = fields.Many2one(
        "ir.model", string="Model", required=True, ondelete="cascade"
    )
    model_name = fields.Char(related="model_id.model", store=True, string="Model Name")
    icon = fields.Char(default="fa-inbox")
    action_xmlid = fields.Char(string="Action XML ID")
    sequence = fields.Integer(default=10)
    requester_field = fields.Char(default="create_uid")
    requester_kind = fields.Selection(
        [("user", "User"), ("employee", "Employee")], default="user", required=True
    )
    submitted_date_field = fields.Char(default="create_date")
    decided_date_field = fields.Char()
    rejected_states = fields.Char(help="Comma separated state values meaning rejected.")
    success_states = fields.Char(help="Comma separated state values meaning success.")
    strategy = fields.Selection(
        [("field", "Field"), ("tier_validation", "Tier Validation")],
        default="field",
        required=True,
    )
    sla_days = fields.Integer(default=0, help="0 = no SLA warning.")
    active = fields.Boolean(default=True)
    step_ids = fields.One2many("od19.approval.step", "source_id", string="Steps")
