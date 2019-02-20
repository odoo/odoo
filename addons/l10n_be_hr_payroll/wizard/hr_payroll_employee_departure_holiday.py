# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class HrPayslipEmployeeDepartureHoliday(models.TransientModel):
    _name = 'hr.payslip.employee.depature.holiday.attests'
    _description = 'Manage the Employee Departure Holiday Attests'

    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env.context.get('active_id'))

    payslip_n_ids = fields.Many2many('hr.payslip', string='Payslips N', compute='_compute_payslip_ids')
    payslip_n1_ids = fields.Many2many('hr.payslip', string='Payslips N-1', compute='_compute_payslip_ids')

    net_n = fields.Monetary('Gross Annual Remuneration Current Year')
    net_n1 = fields.Monetary('Gross Annual Remuneration Previous Year')
    currency_id = fields.Many2one(related='employee_id.contract_id.currency_id')

    time_off_n_ids = fields.Many2many('hr.leave', string='Time Off N', compute='_compute_leave_ids')
    time_off_allocation_n_ids = fields.Many2many('hr.leave.allocation', string='Allocations N', compute='_compute_leave_ids')

    time_off_taken = fields.Float('Time off taken during current year')
    time_off_allocated = fields.Float('Time off allocated during current year')


    unpaid_time_off_n = fields.Float('Days Unpaid time off current year', help="Number of days of unpaid time off taken during current year")
    unpaid_time_off_n1 = fields.Float('Days Unpaid time off previous year', help="Number of days of unpaid time off taken during previous year")

    unpaid_average_remunaration_n = fields.Monetary('Average remuneration by month current year', help="Average remuneration for the 12 months preceding unpaid leave")
    unpaid_average_remunaration_n1 = fields.Monetary('Average remuneration by month previous year', help="Average remuneration for the 12 months preceding unpaid leave")

    fictitious_remuneration_n = fields.Monetary('Remuneration fictitious current year', compute='_compute_fictitious_remuneration_n')
    fictitious_remuneration_n1 = fields.Monetary('Remuneration fictitious previous year', compute='_compute_fictitious_remuneration_n1')


    @api.one
    @api.depends('employee_id')
    def _compute_payslip_ids(self):
        """ get all payslip """

        current_year = self.employee_id.end_notice_period.replace(month=1, day=1)
        previous_year = current_year + relativedelta(years=-1)

        self.payslip_n_ids = self.env['hr.payslip'].search(
            [('employee_id', '=', self.employee_id.id),('date_to', '>=', current_year)])
        self.payslip_n1_ids = self.env['hr.payslip'].search(
            [('employee_id', '=', self.employee_id.id), ('date_to', '>=', previous_year),
            ('date_from', '<', current_year)])

        self.net_n = sum(payslip.basic_wage for payslip in self.payslip_n_ids)
        self.net_n1 = sum(payslip.basic_wage for payslip in self.payslip_n1_ids)

    @api.one
    @api.depends('employee_id')
    def _compute_leave_ids(self):
        """ get all Time Off """

        current_year = self.employee_id.end_notice_period.replace(month=1, day=1)
        next_year = current_year + relativedelta(years=+1)

        self.time_off_n_ids = self.env['hr.leave'].search(
            [('employee_id', '=', self.employee_id.id), ('date_to', '>=', current_year),
            ('date_from', '<', next_year)])

        self.time_off_allocation_n_ids = self.env['hr.leave.allocation'].search(
            [('employee_id', '=', self.employee_id.id)])

        self.time_off_taken = sum(time_off.number_of_days for time_off in self.time_off_n_ids)
        self.time_off_allocated = sum(allocation.number_of_days for allocation in self.time_off_allocation_n_ids)

    @api.one
    @api.depends('unpaid_average_remunaration_n', 'unpaid_time_off_n')
    def _compute_fictitious_remuneration_n(self):
        self.fictitious_remuneration_n = self.unpaid_time_off_n * self.unpaid_average_remunaration_n * 3 / (13 * 5)

    @api.one
    @api.depends('unpaid_average_remunaration_n1', 'unpaid_time_off_n1')
    def _compute_fictitious_remuneration_n1(self):
        self.fictitious_remuneration_n1 = self.unpaid_time_off_n1 * self.unpaid_average_remunaration_n1 * 3 / (13 * 5)


    def compute_termination_holidays(self):
        struct_n1_id = self.env.ref('l10n_be_hr_payroll.hr_payroll_salary_structure_departure_n1_holidays')
        struct_n_id = self.env.ref('l10n_be_hr_payroll.hr_payroll_salary_structure_departure_n_holidays')

        termination_payslip_n = self.env['hr.payslip'].create({
            'name': '%s - %s' % (struct_n_id.payslip_name, self.employee_id.display_name),
            'employee_id': self.employee_id.id,
            'date_from': max(self.employee_id.first_contract_in_company, self.employee_id.end_notice_period.replace(month=1, day=1)),
            'date_to': self.employee_id.end_notice_period,
        })
        termination_payslip_n.onchange_employee()
        termination_payslip_n.struct_id = struct_n_id.id
        termination_payslip_n.worked_days_line_ids = ''
        self.env['hr.payslip.input'].create({
            'name' : 'Gross reference remuneration N',
            'payslip_id': termination_payslip_n.id,
            'sequence': 2,
            'code': 'GROSS_REF',
            'amount': self.net_n + self.fictitious_remuneration_n,
            'contract_id': termination_payslip_n.contract_id.id
        })
        self.env['hr.payslip.input'].create({
            'name' : 'Right to time off',
            'payslip_id': termination_payslip_n.id,
            'sequence': 3,
            'code': 'ALLOCATION',
            'amount': 0,
            'contract_id': termination_payslip_n.contract_id.id
        })
        self.env['hr.payslip.input'].create({
            'name' : 'Time off already taken',
            'payslip_id': termination_payslip_n.id,
            'sequence': 4,
            'code': 'TIME_OFF_TAKEN',
            'amount': 0,
            'contract_id': termination_payslip_n.contract_id.id
        })
        termination_payslip_n.compute_sheet()


        termination_payslip_n1 = self.env['hr.payslip'].create({
            'name': '%s - %s' % (struct_n1_id.payslip_name, self.employee_id.display_name),
            'employee_id': self.employee_id.id,
            'date_from': max(self.employee_id.first_contract_in_company, (self.employee_id.end_notice_period + relativedelta(years=-1)).replace(month=1, day=1)),
            'date_to': max(self.employee_id.first_contract_in_company, (self.employee_id.end_notice_period + relativedelta(years=-1)).replace(month=12, day=31)),
        })
        termination_payslip_n1.onchange_employee()
        termination_payslip_n1.struct_id = struct_n1_id.id
        termination_payslip_n1.worked_days_line_ids = ''
        self.env['hr.payslip.input'].create({
            'name' : 'Gross reference remuneration N-1',
            'payslip_id': termination_payslip_n1.id,
            'sequence': 1,
            'code': 'GROSS_REF',
            'amount': self.net_n1 + self.fictitious_remuneration_n1,
            'contract_id': termination_payslip_n1.contract_id.id
        })
        self.env['hr.payslip.input'].create({
            'name' : 'Right to time off',
            'payslip_id': termination_payslip_n1.id,
            'sequence': 3,
            'code': 'ALLOCATION',
            'amount': self.time_off_allocated,
            'contract_id': termination_payslip_n1.contract_id.id
        })
        self.env['hr.payslip.input'].create({
            'name' : 'Time off already taken',
            'payslip_id': termination_payslip_n1.id,
            'sequence': 4,
            'code': 'TIME_OFF_TAKEN',
            'amount': self.time_off_taken,
            'contract_id': termination_payslip_n1.contract_id.id
        })
        termination_payslip_n1.compute_sheet()

        return {
            'name': _('Termination'),
            'domain': [('id', 'in', [termination_payslip_n.id, termination_payslip_n1.id])],
            'view_type': 'form',
            'res_model': 'hr.payslip',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }
