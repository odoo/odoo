# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.resource.models.resource import Intervals
from datetime import datetime, timedelta
import pytz


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee'

    slip_ids = fields.One2many('hr.payslip', 'employee_id', string='Payslips', readonly=True)
    payslip_count = fields.Integer(compute='_compute_payslip_count', string='Payslip Count', groups="hr_payroll.group_hr_payroll_user")

    registration_number = fields.Char('Registration Number of the Employee', copy=False)

    _sql_constraints = [
        ('unique_registration_number', 'UNIQUE(registration_number, company_id)', 'No duplication of registration numbers is allowed')
    ]

    @api.multi
    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = len(employee.slip_ids)


    @api.multi
    def generate_benefit(self, date_start, date_stop):

        date_start = date_start.replace(tzinfo=pytz.utc)
        date_stop = date_stop.replace(tzinfo=pytz.utc)

        for employee in self:

            # Approved leaves
            emp_leaves = employee.resource_calendar_id.leave_ids.filtered(
                lambda r:
                    r.resource_id == employee.resource_id and
                    r.date_from.replace(tzinfo=pytz.utc) <= date_stop and
                    r.date_to.replace(tzinfo=pytz.utc) >= date_start
                )
            global_leaves = employee.resource_calendar_id.global_leave_ids
            for calendar_leave in emp_leaves | global_leaves:
                hr_leave = calendar_leave.holiday_id
                hr_leave.copy_to_benefits()

            new_benefits = self.env['hr.benefit']
            for contract in employee._get_contracts(date_start, date_stop):

                date_start_benefits = max(date_start, datetime.combine(contract.date_start, datetime.min.time()).replace(tzinfo=pytz.utc))
                date_stop_benefits = min(date_stop, datetime.combine(contract.date_end or datetime.max.date(), datetime.max.time()).replace(tzinfo=pytz.utc))

                calendar = contract.resource_calendar_id
                resource = employee.resource_id
                attendances = calendar._work_intervals(date_start_benefits, date_stop_benefits, resource=resource)
                # Attendances
                for interval in attendances:
                    benefit_type_id = interval[2].mapped('benefit_type_id')[:1] or self.env.ref('hr_payroll.benefit_type_attendance')
                    new_benefits |= self.env['hr.benefit'].safe_duplicate_create({
                        'name': "%s: %s" % (benefit_type_id.name, employee.name),
                        'date_start': interval[0].astimezone(pytz.utc),
                        'date_stop': interval[1].astimezone(pytz.utc),
                        'benefit_type_id': benefit_type_id.id,
                        'employee_id': employee.id,
                        'state': 'confirmed',
                    })

            new_benefits.compute_conflicts_leaves_to_approve()
