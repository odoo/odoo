# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Domain

from odoo.addons.resource.models.utils import HOURS_PER_DAY


class HrLeaveAllocationGenerateMultiWizard(models.TransientModel):
    _name = 'hr.leave.allocation.generate.multi.wizard'
    _inherit = ['hr.mixin']
    _description = 'Generate time off allocations for multiple employees'

    def _get_employee_domain(self):
        domain = Domain([('company_id', 'in', self.env.companies.ids)])
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            domain &= Domain(['|', ('leave_manager_id', '=', self.env.user.id), ('user_id', '=', self.env.user.id)])
        return domain

    name = fields.Char("Description", compute="_compute_name", store=True, readonly=False)
    duration = fields.Float(string="Allocation")
    holiday_status_id = fields.Many2one(
        "hr.leave.type", string="Time Off Type", required=True,
        domain="[('company_id', 'in', [company_id, False])]")
    request_unit = fields.Selection(related="holiday_status_id.request_unit")
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
    allocation_type = fields.Selection([
        ('regular', 'Regular Allocation'),
        ('accrual', 'Based on Accrual Plan')
    ], string="Allocation Type", default="regular", required=True)
    accrual_plan_id = fields.Many2one('hr.leave.accrual.plan',
        domain="['|', ('time_off_type_id', '=', False), ('time_off_type_id', '=', holiday_status_id)]")
    date_from = fields.Date('Start Date', default=fields.Date.context_today, required=True)
    date_to = fields.Date('End Date')
    notes = fields.Text('Reasons')

    @api.depends('holiday_status_id', 'duration')
    def _compute_name(self):
        for allocation_multi in self:
            allocation_multi.name = allocation_multi._get_title()

    def _get_title(self):
        self.ensure_one()
        if not self.holiday_status_id:
            return self.env._("Allocation Request")
        return self.env._(
            '%(name)s (%(duration)s %(request_unit)s(s))',
            name=self.holiday_status_id.name,
            duration=self.duration,
            request_unit=self.request_unit
        )

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

    def _prepare_allocation_values(self, employees):
        self.ensure_one()
        hours_per_day = {
            e.id: e.resource_calendar_id.hours_per_day or self.company_id.resource_calendar_id.hours_per_day or HOURS_PER_DAY
            for e in employees.sudo()
        }
        return [{
            'name': self.name,
            'holiday_status_id': self.holiday_status_id.id,
            'number_of_days': self.duration if self.request_unit != "hour" else self.duration / hours_per_day[employee.id],
            'employee_id': employee.id,
            'state': 'confirm',
            'allocation_type': self.allocation_type,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'accrual_plan_id': self.accrual_plan_id.id,
            'notes': self.notes
        } for employee in employees]

    def action_generate_allocations(self):
        self.ensure_one()
        employees = self._get_employees_from_allocation_mode()
        vals_list = self._prepare_allocation_values(employees)
        if vals_list:
            allocations = self.env['hr.leave.allocation'].with_context(
                mail_notify_force_send=False,
                mail_activity_automation_skip=True,
            ).create(vals_list)
            allocations.filtered(lambda c: c.validation_type not in ('no_validation', 'hr')).action_approve()
            if self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
                allocations.filtered(lambda c: c.validation_type == 'hr').action_approve()

            return {
                'type': 'ir.actions.act_window',
                'name': self.env._('Generated Allocations'),
                "views": [[self.env.ref('hr_holidays.hr_leave_allocation_view_tree').id, "list"], [self.env.ref('hr_holidays.hr_leave_allocation_view_form_manager').id, "form"]],
                'view_mode': 'list',
                'res_model': 'hr.leave.allocation',
                'domain': [('id', 'in', allocations.ids)],
                'context': {
                    'active_id': False,
                },
            }
        return None

    @api.constrains('allocation_mode')
    def _check_allocation_mode(self):
        is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        for record in self:
            if record.allocation_mode != 'employee' and not is_manager:
                raise AccessError(self.env._("As Time Off Responsible, you can only use the allocation mode 'By Employee'."))
