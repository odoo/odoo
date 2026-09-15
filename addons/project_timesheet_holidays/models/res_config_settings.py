from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    internal_project_id = fields.Many2one(
        related="company_id.internal_project_id",
        string="Internal Project",
        readonly=False,
        required=True,
        domain="[('company_id', '=', company_id), ('is_template', '=', False)]",
        help="The default project used when automatically generating timesheets via time off requests."
        " You can specify another project on each time off type individually.",
    )
    leave_timesheet_task_id = fields.Many2one(
        related="company_id.leave_timesheet_task_id",
        string="Time Off Task",
        readonly=False,
        domain="[('company_id', '=', company_id), ('project_id', '=?', internal_project_id), ('has_template_ancestor', '=', False)]",
        help="The default task used when automatically generating timesheets via time off requests."
        " You can specify another task on each time off type individually.",
    )

    @api.onchange("internal_project_id")
    def _onchange_timesheet_project_id(self):
        if self.internal_project_id != self.leave_timesheet_task_id.project_id:
            _debug.logic(
                "leave_timesheet_task_cleared",
                reason="internal_project_changed",
                project=self.internal_project_id,
                task=self.leave_timesheet_task_id,
            )
            self.leave_timesheet_task_id = False

    @api.onchange("leave_timesheet_task_id")
    def _onchange_timesheet_task_id(self):
        if self.leave_timesheet_task_id:
            _debug.logic(
                "internal_project_followed_task",
                task=self.leave_timesheet_task_id,
                project=self.leave_timesheet_task_id.project_id,
            )
            self.internal_project_id = self.leave_timesheet_task_id.project_id
