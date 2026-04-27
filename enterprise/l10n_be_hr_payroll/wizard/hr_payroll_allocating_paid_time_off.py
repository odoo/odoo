# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY

from odoo import api, fields, models, _
from odoo.tools import float_round
from odoo.exceptions import UserError


class HrPayrollAllocPaidLeave(models.TransientModel):
    _name = 'hr.payroll.alloc.paid.leave'
    _description = 'Manage the Allocation of Paid Time Off'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        return super().default_get(field_list)

    def _get_range_of_years(self):
        current_year = fields.Date.today().year
        return [(year, year) for year in range(current_year - 5, current_year + 1)]

    year = fields.Selection(string='Reference Period', selection='_get_range_of_years', required=True, help="Year of the period to consider", default=lambda self: fields.Date.today().year)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Structure Type")

    employee_ids = fields.Many2many('hr.employee', string='Employees', help="Use this to limit the employees to compute")
    alloc_employee_ids = fields.One2many('hr.payroll.alloc.employee', 'alloc_paid_leave_id',
        compute='_compute_alloc_employee_ids', readonly=False)

    holiday_status_id = fields.Many2one(
        "hr.leave.type", string="Time Off Type", required=True,
        domain=[('requires_allocation', '=', 'yes')])

    company_id = fields.Many2one(
        'res.company', string='Company', required=True, default=lambda self: self.env.company)
    department_id = fields.Many2one('hr.department', 'Department', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    @api.depends('structure_type_id', 'year', 'holiday_status_id', 'department_id')
    def _compute_alloc_employee_ids(self):
        if not self.env.user.has_group('hr_payroll.group_hr_payroll_user'):
            raise UserError(_("You don't have the right to do this. Please contact your administrator!"))
        self.alloc_employee_ids = False
        if not self.year or not self.company_id or not self.holiday_status_id:
            return

        period_start = date(int(self.year), 1, 1)
        period_end = date(int(self.year), 12, 31)
        calendar_of_company = self.company_id.resource_calendar_id
        max_leaves_count = 20 * calendar_of_company.hours_per_day  # 20 days * (number of hours per day) for belgian company

        period_work_days_count = len(list(rrule(DAILY, dtstart=period_start, until=period_end, byweekday=[0, 1, 2, 3, 4, 5])))

        if self.structure_type_id:
            structure = "AND c.structure_type_id = %(structure)s"
        else:
            structure = ""

        employee_check = ""
        if self.department_id:
            employee_check = "AND e.department_id = %(department)s"

        if self.employee_ids:
            employee_check += "AND e.id in %(employee_ids)s "

        query = """
            SELECT c.id AS contract_id,
                   c.employee_id AS employee_id,
                   c.date_start AS date_start,
                   c.date_end AS date_end,
                   c.resource_calendar_id AS resource_calendar_id
              FROM hr_contract c
              JOIN hr_employee e ON c.employee_id = e.id
             WHERE c.state IN ('open', 'pending', 'close')
               AND c.date_start <= %(stop)s
               AND (c.date_end IS NULL OR c.date_end >= %(start)s)
               AND e.active IS TRUE
               AND e.employee_type = 'employee'
               AND c.company_id IN %(company)s
                   {where_structure}
                   {where_employee_in_department}
        """.format(where_structure=structure, where_employee_in_department=employee_check)

        self.env.cr.execute(query, {
            'start': fields.Date.to_string(period_start),
            'stop': fields.Date.to_string(period_end),
            'structure': self.structure_type_id.id,
            'company': tuple(self.env.companies.ids),
            'department': self.department_id.id,
            'employee_ids': tuple(self.employee_ids.ids),
        })

        alloc_employees = defaultdict(lambda: (0, None))  # key = employee_id and value contains paid_time_off and contract_id in Tuple
        for vals in self.env.cr.dictfetchall():
            paid_time_off, contract_id = alloc_employees[vals['employee_id']]

            date_start = vals['date_start']
            date_end = vals['date_end']
            calendar = self.env['resource.calendar'].browse(vals['resource_calendar_id'])
            work_time_rate = calendar.work_time_rate / 100

            if date_start < period_start:
                date_start = period_start
            if date_end is None or date_end > period_end:
                if date_end is None:
                    contract_id = vals['contract_id']
                date_end = period_end

            work_days_count = len(list(rrule(DAILY, dtstart=date_start, until=date_end, byweekday=[0, 1, 2, 3, 4, 5])))
            work_days_ratio = work_days_count / period_work_days_count  # In case the employee didn't work over the whole period
            paid_time_off += work_days_ratio * work_time_rate * max_leaves_count

            alloc_employees[vals['employee_id']] = (paid_time_off, contract_id)

        # Add employee attestation days to the paid time off

        employees = self.env['hr.employee'].browse(alloc_employees.keys())  # prefetch the employee records

        for employee_id, (paid_time_off, contract_id) in alloc_employees.items():
            employee = employees.browse(employee_id)

            if self.year == employee.first_contract_date.year:
                for double_pay_line in employee.double_pay_line_n_ids:
                    work_months_ratio = double_pay_line.months_count / 12
                    work_months_rate = double_pay_line.occupation_rate / 100
                    paid_time_off += work_months_ratio * work_months_rate * max_leaves_count

                alloc_employees[employee_id] = (paid_time_off, contract_id)

        alloc_employee_ids = []

        for employee_id, value in alloc_employees.items():
            max_hours_to_allocate, contract_next_period = value
            paid_time_off_to_allocate = 0
            if contract_next_period is None:
                next_period_start = period_start + relativedelta(years=1)
                next_period_end = period_end + relativedelta(years=1)
                domains = [
                    ('employee_id', '=', employee_id),
                    ('company_id', 'in', self.env.companies.ids),
                    ('date_start', '<=', next_period_end),
                    '|',
                        ('date_end', '=', False),
                        ('date_end', '>=', next_period_start),
                    '|',
                        ('state', 'in', ('open', 'pending')),
                        '&',  # domain to seach state = 'incoming'
                            ('state', '=', 'draft'),
                            ('kanban_state', '=', 'done')
                ]
                if self.structure_type_id:
                    domains.append(('structure_type_id', '=', self.structure_type_id.id))
                # We need the contract currently active for the next period for each employee to allocate the correct time off based on this contract.
                contract_next_period = self.env['hr.contract'].search(domains, limit=1, order='date_start desc')
            else:
                contract_next_period = self.env['hr.contract'].browse(contract_next_period)

            if contract_next_period.id:
                calendar = self.env.context.get('forced_calendar', contract_next_period.resource_calendar_id)
                allocation_hours = max_hours_to_allocate
                # An employee should never have more than 4 weeks of annual time off.
                allocation_hours = min(max_hours_to_allocate, 4 * calendar.hours_per_week)
                paid_time_off_to_allocate = allocation_hours / calendar_of_company.hours_per_day if calendar_of_company.hours_per_day else 0
                # Make sure we do not give more time than we should due to rounding
                # (example: 2020 fulltime and starts 2021 with a part time contract would have 10.5 days which is not right)
                # * 4 for weeks, * 2 for two week calendars, / 2 for 2 half days composing a full day (morning, afternoon)
                max_days_for_calendar = (len(calendar.attendance_ids) * 4) / 2 if not calendar.two_weeks_calendar\
                    else (len(calendar.attendance_ids) * 2 / 2)
                if paid_time_off_to_allocate > max_days_for_calendar:
                    paid_time_off_to_allocate = max_days_for_calendar
                else:
                    paid_time_off_to_allocate = float_round(paid_time_off_to_allocate, precision_rounding=0.5)

            paid_time_off = float_round(max_hours_to_allocate / calendar_of_company.hours_per_day if calendar_of_company.hours_per_day else 0, 0)

            alloc_employee_ids.append((0, 0, {
                'employee_id': employee_id,
                'paid_time_off': paid_time_off,
                'paid_time_off_to_allocate': paid_time_off_to_allocate,
                'contract_next_year_id': contract_next_period.id,
                'alloc_paid_leave_id': self.id}))

        self.alloc_employee_ids = alloc_employee_ids

    def generate_allocation(self):
        allocation_values = []
        calendar_of_company = self.company_id.resource_calendar_id
        for alloc in self.alloc_employee_ids.filtered(lambda alloc: alloc.paid_time_off_to_allocate):
            max_leaves_allocated = alloc.paid_time_off * calendar_of_company.hours_per_day
            number_of_days = alloc.paid_time_off_to_allocate

            if alloc.paid_time_off_to_allocate * alloc.resource_calendar_id.hours_per_day > max_leaves_allocated:
                number_of_days = alloc.paid_time_off

            number_of_days = round(number_of_days * 2) / 2  # round the paid time off until x.5
            if number_of_days:
                allocation_values.append({
                    'name': _('Paid Time Off Allocation'),
                    'holiday_status_id': self.holiday_status_id.id,
                    'employee_id': alloc.employee_id.id,
                    'number_of_days': number_of_days,
                    'max_leaves_allocated': max_leaves_allocated,
                    'date_from': '%d-01-01' % (int(self.year) + 1),
                    'date_to': '%d-12-31' % (int(self.year) + 1),
                })
        allocations = self.env['hr.leave.allocation'].create(allocation_values)

        return {
            'name': 'Paid Time Off Allocation',
            'domain': [('id', 'in', allocations.ids)],
            'res_model': 'hr.leave.allocation',
            'view_id': False,
            'view_mode': 'list,form',
            'type': 'ir.actions.act_window',
        }


class HrPayrollAllocEmployee(models.TransientModel):
    _name = 'hr.payroll.alloc.employee'
    _description = 'Manage the Allocation of Paid Time Off Employee'

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    paid_time_off = fields.Float("Paid Time Off For The Period", required=True, help="1 day is 7 hours and 36 minutes")
    paid_time_off_to_allocate = fields.Float("Paid Time Off To Allocate", required=True, help="1 day is the number of the amount of hours per day in the working schedule")
    contract_next_year_id = fields.Many2one('hr.contract', string="Contract Active Next Year")
    resource_calendar_id = fields.Many2one(related='contract_next_year_id.resource_calendar_id', string="Current Working Schedule", readonly=True)
    alloc_paid_leave_id = fields.Many2one('hr.payroll.alloc.paid.leave')
