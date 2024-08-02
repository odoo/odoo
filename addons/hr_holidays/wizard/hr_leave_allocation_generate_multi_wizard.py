# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.resource.models.utils import HOURS_PER_DAY


class HrLeaveAllocationGenerateMultiWizard(models.TransientModel):
    _name = "hr.leave.allocation.generate.multi.wizard"
    _description = 'Generate time off allocations for multiple employees'

    name = fields.Char("Description")
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
    employee_ids = fields.Many2many('hr.employee', string='Employees', domain="[('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    department_id = fields.Many2one('hr.department')
    category_id = fields.Many2one('hr.employee.category', string='Employee Tag')
    allocation_type = fields.Selection(
        selection=[
            ('regular', 'Regular Allocation'),
            ('accrual', 'Accrual Allocation')
        ],
        compute="_compute_allocation_type",
        string="Allocation Type", default="regular", required=True,
        help="""
            Only one allocation type can be set for a given employee and a given time off type.
            If at least one employee already has an allocation of the same leave type, the field is not editable.
        """)
    can_edit_type = fields.Boolean(compute="_compute_allocation_type", export_string_translation=False)
    allocation_type_discrepancy = fields.Boolean(compute='_compute_allocation_type', export_string_translation=False)
    accrual_plan_id = fields.Many2one('hr.leave.accrual.plan',
        domain="['|', ('time_off_type_id', '=', False), ('time_off_type_id', '=', holiday_status_id)]")
    date_from = fields.Date('Start Date', default=fields.Date.context_today, required=True)
    date_to = fields.Date('End Date')

    @api.depends(
        'holiday_status_id',
        'allocation_mode',
        'employee_ids',
        'company_id',
        'department_id',
        'category_id',
        'allocation_type',
    )
    def _compute_allocation_type(self):
        self.allocation_type = 'regular'
        self.can_edit_type = True
        self.allocation_type_discrepancy = False
        employees = self._get_employees_from_allocation_mode()
        existing_allocations_list = self.env['hr.leave.allocation'].search([
            ('employee_id', 'in', employees.ids),
            ('holiday_status_id', 'in', self.holiday_status_id.ids),
        ])
        if not existing_allocations_list:
            return
        for wizard in self:
            existing_allocations = existing_allocations_list.filtered_domain([
                ('employee_id', 'in', employees.ids),
                ('holiday_status_id', '=', wizard.holiday_status_id.id),
            ])
            if not existing_allocations or not employees or not wizard.holiday_status_id:
                continue
            allocation_types = list(set(existing_allocations.mapped('allocation_type')))
            wizard.can_edit_type = False
            wizard.allocation_type = allocation_types[0]
            wizard.allocation_type_discrepancy = len(allocation_types) > 1\
                or wizard.allocation_type != allocation_types[0]

    def _get_employees_from_allocation_mode(self):
        employees = self.env['hr.employee']
        companies = self.env['res.company']
        if self.allocation_mode == 'employee':
            employees |= self.employee_ids
        elif self.allocation_mode == 'category':
            employees |= self.category_id.employee_ids.filtered(lambda e: e.company_id in self.env.companies)
        elif self.allocation_mode == 'company':
            companies |= self.company_id
        else:
            employees |= self.department_id.member_ids
        if companies:
            employees |= self.env['hr.employee'].search([('company_id', 'in', companies.ids)])
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
        } for employee in employees]

    def action_generate_allocations(self):
        self.ensure_one()
        employees = self._get_employees_from_allocation_mode()
        vals_list = self._prepare_allocation_values(employees)
        if vals_list:
            allocations = self.env['hr.leave.allocation'].with_context(
                mail_notify_force_send=False,
                mail_activity_automation_skip=True
            ).create(vals_list)
            allocations.filtered(lambda c: c.validation_type != 'no_validation').action_validate()

            return {
                'type': 'ir.actions.act_window',
                'name': _('Generated Allocations'),
                "views": [[self.env.ref('hr_holidays.hr_leave_allocation_view_tree').id, "tree"], [self.env.ref('hr_holidays.hr_leave_allocation_view_form_manager').id, "form"]],
                'view_mode': 'tree',
                'res_model': 'hr.leave.allocation',
                'domain': [('id', 'in', allocations.ids)]
            }
