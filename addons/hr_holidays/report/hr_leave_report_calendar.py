# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.fields import Domain

from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError


class HrLeaveReportCalendar(models.Model):
    _name = 'hr.leave.report.calendar'
    _description = 'Time Off Calendar'
    _auto = False
    _order = "request_date_from DESC, employee_id"

    name = fields.Char(string='Name', readonly=True, compute="_compute_name")
    request_date_from = fields.Date(string='Request Start Date', readonly=True)
    request_date_to = fields.Date(string='Request End Date', readonly=True)
    # what the views draw: the request's wall clock, restamped for the reader, so a day
    # off falls on the days it was asked for. See hr.leave request_date_hour_from.
    request_date_hour_from = fields.Datetime(
        compute='_compute_request_date_hours', compute_sudo=True,
        search='_search_request_date_hour_from')
    request_date_hour_to = fields.Datetime(
        compute='_compute_request_date_hours', compute_sudo=True,
        search='_search_request_date_hour_to')
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
            hl.request_date_from AS request_date_from,
            hl.request_date_to AS request_date_to,
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

    def _compute_display_name(self):
        if self.env.context.get('hide_employee_name') and 'employee_id' in self.env.context.get('group_by', []):
            for record in self:
                record.display_name = record.name.removeprefix(f"{record.employee_id.name}").lstrip(": ")
        else:
            super()._compute_display_name()

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id._get_unusual_days(date_from, date_to)

    @api.depends('leave_id.request_date_hour_from', 'leave_id.request_date_hour_to')
    @api.depends_context('uid')
    def _compute_request_date_hours(self):
        for report in self:
            report.request_date_hour_from = report.leave_id.request_date_hour_from
            report.request_date_hour_to = report.leave_id.request_date_hour_to

    def _search_request_date_hour_from(self, operator, value):
        return self._search_on_request('request_date_hour_from', operator, value)

    def _search_request_date_hour_to(self, operator, value):
        return self._search_on_request('request_date_hour_to', operator, value)

    @api.model
    def _search_on_request(self, field_name, operator, value):
        """ Asked of the request itself, as superuser: hr.leave's own rules already
        say which of its rows the reader may see. """
        return Domain('id', 'in', self.env['hr.leave'].sudo()._search(
            Domain(field_name, operator, value)))

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
