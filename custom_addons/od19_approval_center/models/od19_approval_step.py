from odoo import fields, models


class Od19ApprovalStep(models.Model):
    _name = "od19.approval.step"
    _description = "Approval Center Step"
    _order = "source_id, sequence, id"

    source_id = fields.Many2one(
        "od19.approval.source", string="Source", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    label = fields.Char(required=True)
    state_field = fields.Char(
        default="state", help="Field holding the state this step waits on."
    )
    state_value = fields.Char(
        required=True, help="State value while the record waits at this step."
    )
    approver_field = fields.Char(
        help="Field holding the approver on the record. Leave empty for a "
             "shared pool step (visible to every internal user)."
    )
    approver_kind = fields.Selection(
        [("user", "User"), ("employee", "Employee"), ("partner", "Partner")],
        default="user",
        required=True,
    )
