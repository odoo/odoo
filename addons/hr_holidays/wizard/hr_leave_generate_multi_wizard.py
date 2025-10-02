# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, UTC
from zoneinfo import ZoneInfo

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class HrLeaveGenerateMultiWizard(models.TransientModel):
    _name = 'hr.leave.generate.multi.wizard'
    _inherit = ['hr.mixin']
    _description = 'Generate time off for multiple employees'

    def _get_employee_domain(self):
        domain = (
            Domain([("company_id", "=", self.company_id.id)])
            if self.company_id
            else Domain([("company_id", "in", self.env.companies.ids)])
        )
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            domain &= Domain(['|', ('leave_manager_id', '=', self.env.user.id), ('user_id', '=', self.env.user.id)])
        return domain

    name = fields.Char("Description")
    holiday_status_id = fields.Many2one(
        "hr.leave.type", string="Time Off Type", required=True,
        domain="[('company_id', 'in', [company_id, False])]")
    employee_ids = fields.Many2many('hr.employee', string='Employees', domain=lambda self: self._get_employee_domain())
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    date_from = fields.Date('Start Date', required=True, default=lambda self: fields.Date.today())
    date_to = fields.Date('End Date', required=True, default=lambda self: fields.Date.today())
    hour_from = fields.Float(string='Hour from')
    hour_to = fields.Float(string='Hour to')
    leave_type_request_unit = fields.Selection(related='holiday_status_id.request_unit')
    date_from_period = fields.Selection([
        ('am', 'Morning'), ('pm', 'Afternoon')],
        string="Date Period Start", default='am')
    date_to_period = fields.Selection([
        ('am', 'Morning'), ('pm', 'Afternoon')],
        string="Date Period End", default='pm')

    def _prepare_employees_holiday_values(self, employees, date_from_tz, date_to_tz):
        self.ensure_one()
        work_days_data = employees.sudo()._get_work_days_data_batch(date_from_tz, date_to_tz)
        validated = self.env.user.has_group('hr_holidays.group_hr_holidays_user') or self.holiday_status_id.leave_validation_type == 'no_validation'
        values = []
        for employee in employees:
            if work_days_data[employee.id]['days'] > 0:
                employee_values = {
                    'name': self.name,
                    'holiday_status_id': self.holiday_status_id.id,
                    'request_date_from': self.date_from,
                    'request_date_to': self.date_to,
                    'employee_id': employee.id,
                    'state': 'validate' if validated else 'confirm',
                }
                if self.leave_type_request_unit == 'hour':
                    employee_values['request_hour_from'] = self.hour_from
                    employee_values['request_hour_to'] = self.hour_to
                if self.leave_type_request_unit == 'half_day':
                    employee_values['request_date_from_period'] = self.date_from_period
                    employee_values['request_date_to_period'] = self.date_to_period
                values.append(employee_values)
        return values

    def action_generate_time_off(self):
        self.ensure_one()
        employees = self.employee_ids or self.env['hr.employee'].search(self._get_employee_domain())

        tz = ZoneInfo(self.company_id.tz or self.env.user.tz or 'UTC')
        if self.leave_type_request_unit == 'hour':
            date_from_tz = (datetime.combine(self.date_from, datetime.min.time(), tzinfo=tz) + timedelta(hours=self.hour_from)).astimezone(UTC).replace(tzinfo=None)
            date_to_tz = (datetime.combine(self.date_to, datetime.min.time(), tzinfo=tz) + timedelta(hours=self.hour_to)).astimezone(UTC).replace(tzinfo=None)
        else:
            date_from_tz = datetime.combine(self.date_from, datetime.min.time(), tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
            date_to_tz = datetime.combine(self.date_to, datetime.max.time(), tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
        conflicting_leaves = self.env['hr.leave'].with_context(
            tracking_disable=True,
            mail_activity_automation_skip=True,
            leave_fast_create=True,
        ).search([
            ('date_from', '<=', date_to_tz),
            ('date_to', '>', date_from_tz),
            ('state', 'not in', ['cancel', 'refuse']),
            ('employee_id', 'in', employees.ids)])

        if conflicting_leaves:
            # YTI: More complex use cases could be managed later
            invalid_time_off = conflicting_leaves.filtered(lambda leave: leave.leave_type_request_unit == 'hour')
            if invalid_time_off:
                raise UserError(self.env._('Some employees already have time off requests in hours that overlap with the selected period, Odoo cannot automatically adjust or split hourly leaves during batch generation. Conflicting time off:\n%s', '\n'.join(f"- {l.display_name}" for l in invalid_time_off)))
            one_day_leaves = conflicting_leaves.filtered(lambda leave: leave.request_date_from == leave.request_date_to)
            one_day_leaves.action_refuse()
            (conflicting_leaves - one_day_leaves)._split_leaves(self.date_from, self.date_to + timedelta(days=1))

        vals_list = self._prepare_employees_holiday_values(employees, date_from_tz, date_to_tz)
        leaves = self.env['hr.leave'].with_context(
            tracking_disable=True,
            mail_activity_automation_skip=True,
            leave_fast_create=True,
            no_calendar_sync=True,
            leave_skip_state_check=True,
            # date_from and date_to are computed based on the employee tz
            # If _compute_date_from_to is used instead, it will trigger _compute_number_of_days
            # and create a conflict on the number of days calculation between the different leaves
            leave_compute_date_from_to=True,
            multi_leave_request=True,
        ).create(vals_list)
        leaves._validate_leave_request()

        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Generated Time Off'),
            "views": [[self.env.ref('hr_holidays.hr_leave_view_tree').id, "list"], [self.env.ref('hr_holidays.hr_leave_view_form_manager').id, "form"]],
            'view_mode': 'list',
            'res_model': 'hr.leave',
            'domain': [('id', 'in', leaves.ids)],
            'context': {
                'active_id': False,
            },
        }
