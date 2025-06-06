# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError
from datetime import timedelta, datetime


class HrLeaveReportCalendar(models.Model):
    _name = 'hr.leave.report.calendar'
    _description = 'Time Off Calendar'
    _auto = False
    _order = "start_datetime DESC, employee_id"

    name = fields.Char(string='Name', readonly=True, compute="_compute_name")
    start_datetime = fields.Datetime(string='From', readonly=True)
    stop_datetime = fields.Datetime(string='To', readonly=True)
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
    holiday_status_id = fields.Many2one('hr.leave.type', readonly=True, string="Time Off Type",
        groups='hr_holidays.group_hr_holidays_user')

    is_hatched = fields.Boolean('Hatched', readonly=True)
    is_striked = fields.Boolean('Striked', readonly=True)

    is_absent = fields.Boolean(related='employee_id.is_absent')
    leave_manager_id = fields.Many2one(related='employee_id.leave_manager_id')
    leave_id = fields.Many2one(comodel_name='hr.leave', readonly=True, groups='hr_holidays.group_hr_holidays_user')
    is_manager = fields.Boolean("Manager", compute="_compute_is_manager")

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_leave_report_calendar')
        self._cr.execute("""CREATE OR REPLACE VIEW hr_leave_report_calendar AS
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
            em.job_id AS job_id,
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
            LEFT JOIN resource_resource rr
                ON rr.id = em.resource_id
            LEFT JOIN resource_calendar rc
                ON rc.id = em.resource_calendar_id
            LEFT JOIN res_company co
                ON co.id = em.company_id
            LEFT JOIN resource_calendar cc
                ON cc.id = co.resource_calendar_id
        WHERE
            hl.state IN ('confirm', 'validate', 'validate1', 'refuse')
        );
        """)

    def _compute_display_name(self):
        if self.env.context.get('hide_employee_name') and 'employee_id' in self.env.context.get('group_by', []):
            for record in self:
                record.display_name = record.name.removeprefix(f"{record.employee_id.name}: ")
        else:
            super()._compute_display_name()

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id._get_unusual_days(date_from, date_to)

    @api.model
    def get_gantt_data(self, domain, groupby, read_specification, limit=None, offset=0, unavailability_fields=None, progress_bar_fields=None, start_date=None, stop_date=None, scale=None):
        def get_unavailable_employee_intervals(employees_record, start, stop, scale):
            leaves_mapping = employees_record.resource_id._get_unavailable_intervals(start, stop)
            cell_dt = timedelta(hours=1) if scale in ['day', 'week'] else timedelta(hours=12)
            result = {}
            for employee in employees_record:
                # remove intervals smaller than a cell, as they will cause half a cell to turn grey
                # ie: when looking at a week, a employee start everyday at 8, so there is a unavailability
                # like: 2019-05-22 20:00 -> 2019-05-23 08:00 which will make the first half of the 23's cell grey
                notable_intervals = filter(lambda interval: interval[1] - interval[0] >= cell_dt, leaves_mapping.get(employee.resource_id.id, []))
                result[employee.id] = [{'start': interval[0], 'stop': interval[1]} for interval in notable_intervals]
            return result

        gantt_data = super().get_gantt_data(domain, groupby, read_specification, limit=limit, offset=offset, unavailability_fields=unavailability_fields, progress_bar_fields=progress_bar_fields, start_date=start_date, stop_date=stop_date, scale=scale)
        if self.env.context.get('leave_report_show_all_resources') and groupby == ['employee_id']:
            existing_ids = {group['employee_id'][0] for group in gantt_data['groups'] if group.get('employee_id')}
            employee_not_in_gantt_data = self.env['hr.employee'].search([
                ('active', '=', True),
                ('company_id', 'in', self.env.companies.ids),
                ('id', 'not in', existing_ids),
                '|',
                ('user_id', '=', self.env.uid),
                ('parent_id.user_id', '=', self.env.uid),
            ])
            for emp in employee_not_in_gantt_data:
                gantt_data['groups'].append({
                    'employee_id': (emp.id, emp.name),
                    '__record_ids': [],
                })
            employee_not_in_gantt_data_unavailabilities = get_unavailable_employee_intervals(
                employee_not_in_gantt_data,
                datetime.strptime(str(start_date), "%Y-%m-%d %H:%M:%S"),
                datetime.strptime(str(stop_date), "%Y-%m-%d %H:%M:%S"),
                scale,
            )
            gantt_data['unavailabilities']['employee_id'].update(employee_not_in_gantt_data_unavailabilities)
            gantt_data['length'] += len(employee_not_in_gantt_data)
        return gantt_data

    @api.depends('employee_id.name', 'leave_id')
    def _compute_name(self):
        for leave in self:
            leave.name = leave.employee_id.name
            if self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
                # Include the time off type name
                leave.name += f" {leave.leave_id.holiday_status_id.name}"
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
        elif self.leave_manager_id == current_user and self.sudo().holiday_status_id.leave_validation_type in ('manager', 'both'):
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
        elif self.leave_manager_id == current_user and self.sudo().holiday_status_id.leave_validation_type in ('manager', 'both'):
            # If the user is the employee's time off approver, refuse the leave
            self.sudo().leave_id.sudo(False).action_refuse()
        else:
            # If the user is not a leave manager, raise an error
            raise ValidationError(self.env._("You are not allowed to refuse this leave request."))
