from odoo import fields, models
from odoo.exceptions import UserError


class SuiteDashboardAiRun(models.Model):
    _name = "suite.dashboard.ai.run"
    _description = "Suite Dashboard AI Run"
    _order = "create_date desc, id desc"

    provider_id = fields.Many2one("suite.dashboard.ai.provider", ondelete="set null")
    workspace_id = fields.Many2one("suite.dashboard.workspace", ondelete="set null")
    prompt = fields.Text()
    response = fields.Text()
    tokens_used = fields.Integer()
    duration_ms = fields.Integer()
    state = fields.Selection(
        [
            ("success", "Success"),
            ("error", "Error"),
        ],
        default="success",
        required=True,
    )
    error_msg = fields.Text()

    def write(self, vals):
        if not self.env.user.has_group("suite_dashboard_core.group_suite_dashboard_admin"):
            raise UserError("Only dashboard administrators can modify AI run logs.")
        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group("suite_dashboard_core.group_suite_dashboard_admin"):
            raise UserError("Only dashboard administrators can delete AI run logs.")
        return super().unlink()
