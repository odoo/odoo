# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError


class HrLeaveReportCalendar(models.Model):
    _name = 'hr.leave.report.calendar'
    _description = 'Time Off Calendar'
    _inherit = 'hr.leave.display.name.mixin'
    _auto = False
    _order = "start_datetime DESC, employee_id"

    name = fields.Char(string='Name', readonly=True, compute="_compute_name")
    start_datetime = fields.Datetime(string='From', readonly=True)
    stop_datetime = fields.Datetime(string='To', readonly=True)
    duration_display = fields.Char(related='leave_id.duration_display', readonly=True)
    tz = fields.Selection(_tz_get, string="Timezone", readonly=True)
    duration = fields.Float(string='Duration', readonly=True)
    employee_id = fields.Many2one('hr.employee', readonly=True)
    user_id = fields.Many2one('res.users', readonly=True)
    department_id = fields.Many2one('hr.department', readonly=True)
    job_id = fields.Many2one('hr.job', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    state = fields.Selection([
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
    ], readonly=True)
    description = fields.Char("Description", readonly=True, groups='hr_holidays.group_hr_holidays_user')
    work_entry_type_id = fields.Many2one('hr.work.entry.type', readonly=True, string="Time Type",
        groups='hr_holidays.group_hr_holidays_user')

    is_hatched = fields.Boolean('Hatched', readonly=True)
    is_striked = fields.Boolean('Striked', readonly=True)

    is_absent = fields.Boolean(related='employee_id.is_absent')
    member_of_department = fields.Boolean(related='employee_id.member_of_department')
    leave_manager_id = fields.Many2one(related='employee_id.leave_manager_id')
    leave_id = fields.Many2one(comodel_name='hr.leave', readonly=True, groups='hr_holidays.group_hr_holidays_user')
    is_manager = fields.Boolean("Manager", compute="_compute_is_manager")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'hr_leave_report_calendar')
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
            hl.work_entry_type_id AS work_entry_type_id,
            em.company_id AS company_id,
            v.job_id AS job_id,
            em.user_id AS user_id,
            COALESCE(
                rr.tz,
                p.tz,
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
            LEFT JOIN res_users u
                ON u.id = em.user_id
            LEFT JOIN res_partner p
                ON p.id = u.partner_id
        WHERE
            hl.state IN ('confirm', 'validate', 'validate1', 'refuse')
        );
        """)

    @api.depends(
        'tz', 'leave_id.date_from', 'leave_id.date_to', 'employee_id',
        'leave_id.work_entry_type_id', 'leave_id.number_of_hours',
        'leave_id.work_entry_type_request_unit', 'leave_id.number_of_days',
    )
    @api.depends_context('short_name', 'hide_employee_name', 'group_by', 'scale')
    def _compute_display_name(self):
        is_hr_user = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        for record in self:
            leave = record.sudo().leave_id
            work_entry_type_display = ''

            # Only show work_entry_type if user has access rights
            if is_hr_user:
                work_entry_type_display = (
                    leave.work_entry_type_id.display_code
                    or leave.work_entry_type_id.name
                )

            record.display_name = self._build_leave_display_name({
                'tz': record.tz,
                'date_from': leave.date_from,
                'date_to': leave.date_to,
                'name': leave.name,
                'employee_name': record.employee_id.name or '',
                'work_entry_type_display': work_entry_type_display,
                'request_unit': leave.work_entry_type_request_unit,
                'number_of_hours': leave.number_of_hours,
                'number_of_days': leave.number_of_days,
                'duration_display': record.duration_display,
            })

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id._get_unusual_days(date_from, date_to)

    @api.depends('employee_id.name', 'leave_id')
    def _compute_name(self):
        for leave in self:
            leave.name = leave.employee_id.name
            if self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
                # Include the time type name
                leave.name += f" {leave.leave_id.work_entry_type_id.display_code or leave.leave_id.work_entry_type_id.name}"
            # Include the time off duration.
            leave.name += f": {leave.sudo().leave_id.duration_display}"

    @api.depends('leave_manager_id')
    def _compute_is_manager(self):
        for leave in self:
            leave.is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_user') or leave.leave_manager_id == self.env.user

    def action_approve(self):
        current_user = self.env.user
        if current_user.has_group('hr_holidays.group_hr_holidays_user'):
            # If the user is a leave manager, approve the leave
            self.leave_id.action_approve()
        elif self.leave_manager_id == current_user and self.sudo().work_entry_type_id.leave_validation_type in ('manager', 'both'):
            # If the user is the employee's time off approver, approve the leave
            self.sudo().leave_id.sudo(False).action_approve()
        else:
            # If the user is not a leave manager, raise an error
            raise ValidationError(self.env._("You are not allowed to approve this leave request."))

    def action_refuse(self):
        current_user = self.env.user
        if current_user.has_group('hr_holidays.group_hr_holidays_user'):
            # If the user is a leave manager, refuse the leave
            self.leave_id.action_refuse()
        elif self.leave_manager_id == current_user and self.sudo().work_entry_type_id.leave_validation_type in ('manager', 'both'):
            # If the user is the employee's time off approver, refuse the leave
            self.sudo().leave_id.sudo(False).action_refuse()
        else:
            # If the user is not a leave manager, raise an error
            raise ValidationError(self.env._("You are not allowed to refuse this leave request."))
