from odoo import fields, models


class SuiteDashboardSchedule(models.Model):
    _name = "suite.dashboard.schedule"
    _description = "Suite Dashboard Snapshot Schedule"
    _order = "next_run, id"

    name = fields.Char(required=True)
    workspace_id = fields.Many2one(
        "suite.dashboard.workspace",
        required=True,
        ondelete="cascade",
    )
    owner_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
    )
    filter_state = fields.Text(help="JSON-serialized filters for scheduled runs.")
    frequency = fields.Selection(
        [
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
        ],
        default="weekly",
        required=True,
    )
    next_run = fields.Datetime(required=True, default=fields.Datetime.now)
    recipient_ids = fields.Many2many("res.partner", string="Recipients")
    active = fields.Boolean(default=True)
