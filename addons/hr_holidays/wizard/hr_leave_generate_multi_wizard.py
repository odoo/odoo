# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from pytz import UTC, timezone

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain


class HrLeaveGenerateMultiWizard(models.TransientModel):
    _name = 'hr.leave.generate.multi.wizard'
    _inherit = ['hr.mixin']
    _description = 'Generate time off for multiple employees'

    def _get_employee_domain(self):
        domain = Domain([('company_id', 'in', self.env.companies.ids)])
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            domain &= Domain(['|', ('leave_manager_id', '=', self.env.user.id), ('user_id', '=', self.env.user.id)])
        return domain

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
    employee_ids = fields.Many2many('hr.employee', string='Employees', domain=lambda self: self._get_employee_domain())
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    department_id = fields.Many2one('hr.department')
    category_id = fields.Many2one('hr.employee.category', string='Employee Tag')
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)

    def _get_employees_from_allocation_mode(self):
        self.ensure_one()
        if self.allocation_mode == 'employee':
            employees = self.employee_ids or self.env['hr.employee'].search(self._get_employee_domain())
        elif self.allocation_mode == 'category':
            employees = self.category_id.employee_ids.filtered(lambda e: e.company_id in self.env.companies)
        elif self.allocation_mode == 'company':
            employees = self.env['hr.employee'].search([('company_id', '=', self.company_id.id)])
        else:
            employees = self.department_id.member_ids
        return employees

    def _prepare_employees_holiday_values(self, employees, date_from_tz, date_to_tz):
        self.ensure_one()
        work_days_data = employees.sudo()._get_work_days_data_batch(date_from_tz, date_to_tz)
        validated = self.env.user.has_group('hr_holidays.group_hr_holidays_user') or self.holiday_status_id.leave_validation_type == 'no_validation'
        return [{
            'name': self.name,
            'holiday_status_id': self.holiday_status_id.id,
            'date_from': date_from_tz,
            'date_to': date_to_tz,
            'request_date_from': self.date_from,
            'request_date_to': self.date_to,
            'number_of_days': work_days_data[employee.id]['days'],
            'employee_id': employee.id,
            'state': 'validate' if validated else 'confirm',
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
                    'sticky': False,
                    'title': self.env._('No Employees Found'),
                    'message': self.env._('No employees found for the selected criteria.'),
                },
            }

        tz = timezone(self.company_id.resource_calendar_id.tz or self.env.user.tz or 'UTC')
        date_from_tz = tz.localize(datetime.combine(self.date_from, datetime.min.time())).astimezone(UTC).replace(tzinfo=None)
        date_to_tz = tz.localize(datetime.combine(self.date_to, datetime.max.time())).astimezone(UTC).replace(tzinfo=None)

        conflicting_leaves = self.env['hr.leave'].with_context(
            tracking_disable=True,
            mail_activity_automation_skip=True,
            leave_fast_create=True,
        ).search([
            ('date_from', '<=', date_to_tz),
            ('date_to', '>', date_from_tz),
            ('state', 'not in', ['cancel', 'refuse']),
            ('employee_id', 'in', employees.ids)])

        employees_with_blocking_conflicts = self.env['hr.employee']
        if conflicting_leaves:
            splittable_leaves = conflicting_leaves.filtered(lambda leave: leave.holiday_status_id.allow_request_on_top)
            blocking_leaves = conflicting_leaves - splittable_leaves

            if splittable_leaves:
                # YTI: More complex use cases could be managed later
                invalid_time_off = splittable_leaves.filtered(lambda leave: leave.leave_type_request_unit == 'hour')
                if invalid_time_off:
                    raise UserError(self.env._('Automatic time off splitting during batch generation is not managed for overlapping time off declared in hours. Conflicting time off:\n%s', '\n'.join(f"- {leave.display_name}" for leave in invalid_time_off)))
                one_day_leaves = splittable_leaves.filtered(lambda leave: leave.request_date_from == leave.request_date_to)
                one_day_leaves.action_refuse()
                split_leaves = (splittable_leaves - one_day_leaves)
                split_leaves._split_leaves(self.date_from, self.date_to + timedelta(days=1))

            if blocking_leaves:
                employees_with_blocking_conflicts = blocking_leaves.employee_id

        employees_to_process = employees - employees_with_blocking_conflicts
        vals_list = self._prepare_employees_holiday_values(employees_to_process, date_from_tz, date_to_tz)
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

        notify_type = notify_title = notify_message = None
        next_action = {'type': 'ir.actions.act_window_close'}
        if employees_with_blocking_conflicts and not leaves:
            notify_type = 'danger'
            notify_title = self.env._('Time Off Generation Failed')
            notify_message = self.env._(
                'No time off requests were created. %(failure_count)s employee(s) have overlapping time off that does not allow requests on top: %(employees)s',
                failure_count=len(employees_with_blocking_conflicts),
                employees=', '.join(employees_with_blocking_conflicts.mapped('name')),
            )
        elif employees_with_blocking_conflicts:
            notify_type = 'warning'
            notify_title = self.env._('Time Off Partially Generated')
            notify_message = self.env._(
                '%(success_count)s time off request(s) created successfully. %(failure_count)s employee(s) skipped due to overlapping time off that does not allow requests on top: %(employees)s',
                success_count=len(leaves),
                failure_count=len(employees_with_blocking_conflicts),
                employees=', '.join(employees_with_blocking_conflicts.mapped('name')),
            )
        elif leaves:
            notify_type = 'success'
            notify_title = self.env._('Time Off Generated')
            next_action = {'type': 'ir.actions.client', 'tag': 'reload'}
            if conflicting_leaves:
                notify_message = self.env._(
                    '%(success_count)s time off request(s) created successfully. Some overlapping time off was automatically split to accommodate the new requests.',
                    success_count=len(leaves),
                )
            else:
                notify_message = self.env._(
                    '%(success_count)s time off request(s) created successfully.',
                    success_count=len(leaves),
                )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': notify_type,
                'sticky': False,
                'title': notify_title,
                'message': notify_message,
                'next': next_action,
            },
        }

    @api.constrains('allocation_mode')
    def _check_allocation_mode(self):
        is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        for record in self:
            if record.allocation_mode != 'employee' and not is_manager:
                raise AccessError(self.env._("As Time Off Responsible, you can only use the allocation mode 'By Employee'."))
