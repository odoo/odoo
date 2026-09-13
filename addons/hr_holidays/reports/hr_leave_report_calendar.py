from odoo import api, fields, models
from odoo.db.schema import drop_view_if_exists
from odoo.exceptions import ValidationError

from odoo.addons.base.models.res_partner import _selection_timezones


class HrLeaveReportCalendar(models.Model):
    _name = "hr.leave.report.calendar"
    _description = "Time Off Calendar"
    _auto = False
    _order = "start_datetime DESC, employee_id"

    name = fields.Char(
        compute="_compute_name",
        readonly=True,
    )
    start_datetime = fields.Datetime(
        string="From",
        readonly=True,
    )
    stop_datetime = fields.Datetime(
        string="To",
        readonly=True,
    )
    duration_display = fields.Char(
        related="leave_id.duration_display",
        readonly=True,
    )
    tz = fields.Selection(
        selection=_selection_timezones,
        string="Timezone",
        readonly=True,
    )
    duration = fields.Float(readonly=True)
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        readonly=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        readonly=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        readonly=True,
    )
    job_id = fields.Many2one(
        comodel_name="hr.job",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ("cancel", "Cancelled"),
            ("confirm", "To Approve"),
            ("refuse", "Refused"),
            ("validate1", "Second Approval"),
            ("validate", "Approved"),
        ],
        readonly=True,
    )
    description = fields.Char(
        readonly=True,
        groups="hr_holidays.group_hr_holidays_user",
    )
    holiday_status_id = fields.Many2one(
        comodel_name="hr.leave.type",
        string="Time Off Type",
        readonly=True,
        groups="hr_holidays.group_hr_holidays_user",
    )

    is_hatched = fields.Boolean(
        string="Hatched",
        readonly=True,
    )
    is_striked = fields.Boolean(
        string="Striked",
        readonly=True,
    )

    is_absent = fields.Boolean(related="employee_id.is_absent")
    member_of_department = fields.Boolean(related="employee_id.member_of_department")
    leave_manager_id = fields.Many2one(related="employee_id.leave_manager_id")
    leave_id = fields.Many2one(
        comodel_name="hr.leave",
        readonly=True,
        groups="hr_holidays.group_hr_holidays_user",
    )
    is_manager = fields.Boolean(
        string="Manager",
        compute="_compute_is_manager",
    )

    def init(self):
        drop_view_if_exists(self.env.cr, "hr_leave_report_calendar")
        self.env.cr.execute("""CREATE OR REPLACE VIEW hr_leave_report_calendar AS
        (SELECT
            hl.id AS id,
            hl.id AS leave_id,
            hl.date_from AS start_datetime,
            hl.date_to AS stop_datetime,
            hl.employee_id AS employee_id,
            hl.state AS state,
            hl.department_id AS department_id,
            hl.number_of_days as duration,
            hl.private_name AS description,
            hl.holiday_status_id AS holiday_status_id,
            em.company_id AS company_id,
            v.job_id AS job_id,
            em.user_id AS user_id,
            COALESCE(
                rr.tz,
                rc.tz,
                cc.tz,
                'UTC'
            ) AS tz,
            hl.state = 'refuse' as is_striked,
            hl.state not in ('validate', 'refuse') as is_hatched
        FROM hr_leave hl
            LEFT JOIN hr_employee em
                ON em.id = hl.employee_id
            LEFT JOIN hr_version v ON v.id = em.current_version_id
            LEFT JOIN resource_resource rr
                ON rr.id = em.resource_id
            LEFT JOIN resource_calendar rc
                ON rc.id = v.resource_calendar_id
            LEFT JOIN res_company co
                ON co.id = em.company_id
            LEFT JOIN resource_calendar cc
                ON cc.id = co.resource_calendar_id
        WHERE
            hl.state IN ('confirm', 'validate', 'validate1', 'refuse')
        );
        """)

    @api.depends("name", "employee_id.name")
    @api.depends_context("hide_employee_name", "group_by")
    def _compute_display_name(self):
        if self.env.context.get(
            "hide_employee_name"
        ) and "employee_id" in self.env.context.get("group_by", []):
            for record in self:
                record.display_name = record.name.removeprefix(
                    f"{record.employee_id.name}: "
                )
        else:
            super()._compute_display_name()

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id._get_unusual_days(date_from, date_to)

    @api.depends("employee_id.name", "leave_id")
    @api.depends_context("uid")
    def _compute_name(self):
        is_holidays_user = self.env.user.has_group("hr_holidays.group_hr_holidays_user")
        for leave in self:
            leave.name = leave.employee_id.name
            if is_holidays_user:
                leave.name += f" {leave.leave_id.holiday_status_id.name}"
                leave.name += f": {leave.sudo().leave_id.duration_display}"

    @api.depends("leave_manager_id")
    @api.depends_context("uid")
    def _compute_is_manager(self):
        for leave in self:
            leave.is_manager = (
                self.env.user.has_group("hr_holidays.group_hr_holidays_user")
                or leave.leave_manager_id == self.env.user
            )

    def action_approve(self):
        current_user = self.env.user
        if current_user.has_group("hr_holidays.group_hr_holidays_user"):
            self.leave_id.action_approve()
        elif (
            self.leave_manager_id == current_user
            and self.sudo().holiday_status_id.leave_validation_type
            in ("manager", "both")
        ):
            self.sudo().leave_id.sudo(False).action_approve()
        else:
            raise ValidationError(
                self.env._("You are not allowed to approve this leave request.")
            )

    def action_refuse(self):
        current_user = self.env.user
        if current_user.has_group("hr_holidays.group_hr_holidays_user"):
            self.leave_id.action_refuse()
        elif (
            self.leave_manager_id == current_user
            and self.sudo().holiday_status_id.leave_validation_type
            in ("manager", "both")
        ):
            self.sudo().leave_id.sudo(False).action_refuse()
        else:
            raise ValidationError(
                self.env._("You are not allowed to refuse this leave request.")
            )
