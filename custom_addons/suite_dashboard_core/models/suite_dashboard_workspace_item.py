from odoo import fields, models


class SuiteDashboardWorkspaceItem(models.Model):
    _name = "suite.dashboard.workspace.item"
    _description = "Dashboard Workspace Item"
    _order = "sequence, id"

    workspace_id = fields.Many2one(
        "suite.dashboard.workspace",
        required=True,
        ondelete="cascade",
    )
    widget_key = fields.Char(required=True)
    visible = fields.Boolean(default=True)
    size = fields.Selection(
        selection=[
            ("sm", "Small"),
            ("md", "Medium"),
            ("lg", "Large"),
            ("xl", "Extra Large"),
        ],
        default="md",
    )
    sequence = fields.Integer(default=10)
    col_span = fields.Integer(default=1)
    row_span = fields.Integer(default=1)

    _widget_uniq = models.Constraint(
        "UNIQUE (workspace_id, widget_key)",
        "Widget already exists in this workspace.",
    )
