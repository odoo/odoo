# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from pytz import timezone, UTC

from odoo import fields, models


class HrLeaveGenerateMultiWizard(models.TransientModel):
    _name = 'hr.leave.generate.multi.wizard'
    _description = 'Generate time off for multiple employees'

    name = fields.Char("Description")
    holiday_status_id = fields.Many2one(
        "hr.leave.type", string="Time Off Type", required=True,
        domain="[('company_id', 'in', [company_id, False])]")
    allocation_mode = fields.Selection([
        ('employee', 'By Employee'),
        ('company', 'By Company'),
        ('department', 'By Department'),
        ('category', 'By Employee Tag')],
        string='Allocation Mode', readonly=False, required=True, default='employee',
        help="Allow to create requests in batchs:\n- By Employee: for a specific employee"
             "\n- By Company: all employees of the specified company"
             "\n- By Department: all employees of the specified department"
             "\n- By Employee Tag: all employees of the specific employee group category")
    employee_ids = fields.Many2many('hr.employee', string='Employees', domain="[('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    department_id = fields.Many2one('hr.department')
    category_id = fields.Many2one('hr.employee.category', string='Employee Tag')
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)

    def _get_employees_from_allocation_mode(self):
        self.ensure_one()
        if self.allocation_mode == 'employee':
            employees = self.employee_ids
        elif self.allocation_mode == 'category':
            employees = self.category_id.employee_ids.filtered(lambda e: e.company_id in self.env.companies)
        elif self.allocation_mode == 'company':
            employees = self.env['hr.employee'].search([('company_id', '=', self.company_id.id)])
        else:
            employees = self.department_id.member_ids
        return employees

    def _prepare_employees_holiday_values(self, employees, date_from_tz, date_to_tz):
        self.ensure_one()
        work_days_data = employees._get_work_days_data_batch(date_from_tz, date_to_tz)
        return [{
            'name': self.name,
            'holiday_status_id': self.holiday_status_id.id,
            'date_from': date_from_tz,
            'date_to': date_to_tz,
            'request_date_from': self.date_from,
            'request_date_to': self.date_to,
            'number_of_days': work_days_data[employee.id]['days'],
            'employee_id': employee.id,
            'state': 'validate',
        } for employee in employees if work_days_data[employee.id]['days']]

    def action_generate_time_off(self):
        self.ensure_one()
        employees = self._get_employees_from_allocation_mode()
        if not employees:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'title': self.env._('No Employees Found'),
                    'message': self.env._('No employees found for the selected criteria.'),
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }

        tz = timezone(self.company_id.resource_calendar_id.tz or self.env.user.tz or 'UTC')
        date_from_tz = tz.localize(datetime.combine(self.date_from, datetime.min.time())).astimezone(UTC).replace(tzinfo=None)
        date_to_tz = tz.localize(datetime.combine(self.date_to, datetime.max.time())).astimezone(UTC).replace(tzinfo=None)

        conflicting_leaves = self.env['hr.leave'].with_context(
            tracking_disable=True,
            mail_activity_automation_skip=True,
            leave_fast_create=True
        ).search([
            ('date_from', '<=', date_to_tz),
            ('date_to', '>', date_from_tz),
            ('state', 'not in', ['cancel', 'refuse']),
            ('employee_id', 'in', employees.ids)])
        employees_with_conflicts = conflicting_leaves.employee_id
        employees_without_conflicts = employees - employees_with_conflicts

        vals_list = self._prepare_employees_holiday_values(employees_without_conflicts, date_from_tz, date_to_tz)
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
        ).create(vals_list)
        leaves._validate_leave_request()

        notification_type = 'success'
        notification_title = self.env._('Time Off Generated')
        notification_message = self.env._('%(success_count)s time off request(s) created successfully.', success_count=len(leaves))

        if employees_with_conflicts:
            next_action = {'type': 'ir.actions.act_window_close'}
            if leaves:
                notification_type = 'warning'
                notification_message = self.env._('%(success_count)s time off request(s) created successfully. %(failure_count)s employee(s) skipped due to overlapping time off: %(employees)s',
                                        success_count=len(leaves),
                                        failure_count=len(employees_with_conflicts),
                                        employees=', '.join(employees_with_conflicts.mapped('name')))
            else:
                notification_type = 'danger'
                notification_title = self.env._('Time Off Generation Failed')
                notification_message = self.env._('No time off requests were created. %(failure_count)s employee(s) have overlapping time off: %(employees)s',
                                        failure_count=len(employees_with_conflicts),
                                        employees=', '.join(employees_with_conflicts.mapped('name')))
        else:
            next_action = {
                'type': 'ir.actions.act_window',
                'name': self.env._('Generated Time Off'),
                'views': [
                    [self.env.ref('hr_holidays.hr_leave_view_tree').id, "list"],
                    [self.env.ref('hr_holidays.hr_leave_view_form_manager').id, "form"]
                ],
                'view_mode': 'list',
                'res_model': 'hr.leave',
                'domain': [('id', 'in', leaves.ids)],
                'context': {'active_id': False},
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': notification_type,
                'title': notification_title,
                'message': notification_message,
                'sticky': False,
                'next': next_action,
            },
        }
