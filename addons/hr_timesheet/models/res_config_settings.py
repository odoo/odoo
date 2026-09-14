from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    module_project_timesheet_holidays = fields.Boolean(
        string="Time Off",
        compute="_compute_timesheet_modules",
        store=True,
        readonly=False,
    )
    reminder_user_allow = fields.Boolean(string="Employee Reminder")
    reminder_allow = fields.Boolean(string="Approver Reminder")
    project_time_mode_id = fields.Many2one(
        comodel_name="uom.uom",
        related="company_id.project_time_mode_id",
        string="Project Time Unit",
        readonly=False,
        help="This will set the unit of measure used in projects and tasks.\n"
        "If you use the timesheet linked to projects, don't "
        "forget to setup the right unit of measure in your employees.",
    )
    is_encode_uom_days = fields.Boolean(
        export_string_translation=False,
        compute="_compute_is_encode_uom_days",
    )
    timesheet_encode_method = fields.Selection(
        selection=[
            ("hours", "Hours / Minutes"),
            ("days", "Days / Half-Days"),
        ],
        string="Encoding Method",
        compute="_compute_timesheet_encode_method",
        inverse="_inverse_timesheet_encode_method",
        required=True,
    )

    @api.depends("company_id")
    def _compute_timesheet_encode_method(self):
        uom_day = self.env.ref("uom.product_uom_day", raise_if_not_found=False)
        for settings in self:
            settings.timesheet_encode_method = (
                "days"
                if settings.company_id.timesheet_encode_uom_id == uom_day
                else "hours"
            )

    def _inverse_timesheet_encode_method(self):
        uom_day = self.env.ref("uom.product_uom_day", raise_if_not_found=False)
        uom_hour = self.env.ref("uom.product_uom_hour", raise_if_not_found=False)
        for settings in self:
            _debug.lifecycle(
                "timesheet_encode_method_set",
                company=settings.company_id,
                method=settings.timesheet_encode_method,
            )
            settings.company_id.timesheet_encode_uom_id = (
                uom_day if settings.timesheet_encode_method == "days" else uom_hour
            )

    @api.depends("timesheet_encode_method")
    def _compute_is_encode_uom_days(self):
        for settings in self:
            settings.is_encode_uom_days = settings.timesheet_encode_method == "days"

    @api.depends("module_hr_timesheet")
    def _compute_timesheet_modules(self):
        self.filtered(lambda config: not config.module_hr_timesheet).update(
            {
                "module_project_timesheet_holidays": False,
            }
        )
