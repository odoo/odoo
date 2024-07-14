# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipEmployeeDepartureHoliday(models.TransientModel):
    _name = 'hr.payslip.employee.depature.holiday.attests'
    _description = 'Manage the Employee Departure Holiday Attests'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        return super().default_get(field_list)

    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env.context.get('active_id'))

    payslip_n_ids = fields.Many2many(
        'hr.payslip', string='Payslips N',
        compute='_compute_history', readonly=False, store=False)
    payslip_n1_ids = fields.Many2many(
        'hr.payslip', string='Payslips N-1',
        compute='_compute_history', readonly=False, store=False)

    net_n = fields.Monetary(
        'Gross Annual Remuneration Current Year',
        compute='_compute_net_n', store=True, readonly=False)
    net_n1 = fields.Monetary(
        'Gross Annual Remuneration Previous Year',
        compute='_compute_net_n1', store=True, readonly=False)
    currency_id = fields.Many2one(related='employee_id.contract_id.currency_id')

    time_off_n_ids = fields.Many2many(
        'hr.leave', string='Time Off N', compute='_compute_history', readonly=False, store=False)
    time_off_allocation_n_ids = fields.Many2many(
        'hr.leave.allocation', string='Allocations N',
        compute='_compute_history', readonly=False, store=False)

    time_off_taken = fields.Float(
        'Time off taken during current year',
        compute='_compute_time_off_taken', store=True, readonly=False)
    time_off_allocated = fields.Float(
        'Time off allocated during current year',
        compute='_compute_time_off_allocated', store=True, readonly=False)

    unpaid_time_off_n = fields.Float('Days Unpaid time off current year', help="Number of days of unpaid time off taken during current year")
    unpaid_time_off_n1 = fields.Float('Days Unpaid time off previous year', help="Number of days of unpaid time off taken during previous year")

    unpaid_average_remunaration_n = fields.Monetary('Average remuneration by month current year', help="Average remuneration for the 12 months preceding unpaid leave")
    unpaid_average_remunaration_n1 = fields.Monetary('Average remuneration by month previous year', help="Average remuneration for the 12 months preceding unpaid leave")

    fictitious_remuneration_n = fields.Monetary('Remuneration fictitious current year', compute='_compute_fictitious_remuneration_n')
    fictitious_remuneration_n1 = fields.Monetary('Remuneration fictitious previous year', compute='_compute_fictitious_remuneration_n1')

    @api.depends('employee_id')
    def _compute_history(self):
        for record in self:
            if record.employee_id and (not record.employee_id.start_notice_period or not record.employee_id.end_notice_period):
                raise UserError(_("Notice period not set for %s. Please, set the departure notice period first.", record.employee_id.name))

            if not record.employee_id:
                record.update({
                    'time_off_n_ids': [(5, 0, 0)],
                    'time_off_allocation_n_ids': [(5, 0, 0)],
                    'payslip_n_ids': [(5, 0, 0)],
                    'payslip_n1_ids': [(5, 0, 0)],
                })
            else:
                current_year = record.employee_id.end_notice_period.replace(month=1, day=1)
                previous_year = current_year + relativedelta(years=-1)
                next_year = current_year + relativedelta(years=+1)

                structure_warrant = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_structure_warrant')
                structure_double_holidays = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday')
                structure_termination = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_termination_fees')
                structure_holidays_n = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n_holidays')
                structure_holidays_n1 = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n1_holidays')

                payslip_n_ids = self.env['hr.payslip'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('date_to', '>=', current_year),
                    ('state', 'in', ['done', 'paid', 'verify']),
                    ('struct_id', 'not in', (structure_warrant + structure_double_holidays + structure_termination + structure_holidays_n + structure_holidays_n1).ids)])
                payslip_n1_ids = self.env['hr.payslip'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('date_to', '>=', previous_year),
                    ('date_from', '<', current_year),
                    ('state', 'in', ['done', 'paid']),
                    ('struct_id', 'not in', (structure_warrant + structure_double_holidays + structure_termination + structure_holidays_n + structure_holidays_n1).ids)])

                record.payslip_n_ids = [(4, p._origin.id) for p in payslip_n_ids]
                record.payslip_n1_ids = [(4, p._origin.id) for p in payslip_n1_ids]

                work_entry_type_legal_leave = self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave')

                time_off_n_ids = self.env['hr.leave'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('date_to', '>=', current_year),
                    ('date_from', '<', next_year),
                    ('state', '=', 'validate'),
                    ('holiday_status_id.work_entry_type_id', '=', work_entry_type_legal_leave.id)])

                time_off_allocation_n_ids = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('date_from', '>=', current_year),
                    ('state', '=', 'validate'),
                    ('holiday_status_id.work_entry_type_id', '=', work_entry_type_legal_leave.id)])

                record.time_off_n_ids = [(4, t.id) for t in time_off_n_ids]
                record.time_off_allocation_n_ids = [(4, t.id) for t in time_off_allocation_n_ids]

    @api.depends('payslip_n_ids')
    def _compute_net_n(self):
        for wizard in self:
            if wizard.payslip_n_ids:
                wizard.net_n = wizard.payslip_n_ids._origin._get_line_values(['SALARY'], compute_sum=True)['SALARY']['sum']['total']
            else:
                wizard.net_n = 0

    @api.depends('payslip_n1_ids')
    def _compute_net_n1(self):
        for wizard in self:
            if wizard.payslip_n1_ids:
                wizard.net_n1 = wizard.payslip_n1_ids._origin._get_line_values(['SALARY'], compute_sum=True)['SALARY']['sum']['total']
            else:
                wizard.net_n1 = 0

    @api.depends('time_off_n_ids')
    def _compute_time_off_taken(self):
        for wizard in self:
            if wizard.time_off_n_ids:
                wizard.time_off_taken = sum(time_off.number_of_days for time_off in wizard.time_off_n_ids)
            else:
                wizard.time_off_taken = 0

    @api.depends('time_off_allocation_n_ids')
    def _compute_time_off_allocated(self):
        for wizard in self:
            if wizard.time_off_allocation_n_ids:
                wizard.time_off_allocated = sum(allocation.number_of_days for allocation in wizard.time_off_allocation_n_ids)
            else:
                wizard.time_off_allocated = 0

    @api.depends('unpaid_average_remunaration_n', 'unpaid_time_off_n')
    def _compute_fictitious_remuneration_n(self):
        for attest in self:
            attest.fictitious_remuneration_n = (
                attest.unpaid_time_off_n * attest.unpaid_average_remunaration_n * 3 / (13 * 5))

    @api.depends('unpaid_average_remunaration_n1', 'unpaid_time_off_n1')
    def _compute_fictitious_remuneration_n1(self):
        for attest in self:
            attest.fictitious_remuneration_n1 = (
                attest.unpaid_time_off_n1 * attest.unpaid_average_remunaration_n1 * 3 / (13 * 5))

    def compute_termination_holidays(self):
        struct_n1_id = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n1_holidays')
        struct_n_id = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n_holidays')

        termination_payslip_n = self.env['hr.payslip'].create({
            'name': '%s - %s' % (struct_n_id.payslip_name, self.employee_id.display_name),
            'employee_id': self.employee_id.id,
            'contract_id': self.employee_id.contract_id.id,
            'struct_id': struct_n_id.id,
            'date_from': (self.employee_id.contract_id.date_end or fields.Date.today) + relativedelta(day=1),
            'date_to': (self.employee_id.contract_id.date_end or fields.Date.today) + relativedelta(day=31),
        })
        termination_payslip_n.worked_days_line_ids = [(5, 0, 0)]

        monthly_payslips = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['done', 'paid']),
            ('credit_note', '=', False),
            ('struct_id', '=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id)
        ], order="date_from desc").filtered(
            lambda p: 'OUT' not in p.worked_days_line_ids.mapped('code'))

        if monthly_payslips:
            slip = monthly_payslips[0]
            annual_gross = slip._get_line_values(['GROSS'])['GROSS'][slip.id]['total'] * 12
        else:
            annual_gross = 0

        # As regards the recovery of amounts for European holidays (“additional holidays”), the
        # amount paid in advance is
        # - or recovered from the double vacation pay (part 85%) for the following year;
        # - or, when the worker leaves, on the amount of the exit pay. The legislation does not
        # specifically state whether, in the event of an exit, the recovery is on the single or
        # the double, but, in order to be consistent, I would do the recovery on the double
        # (85% of 7.67 %).
        # In addition, when "additional" vacation has been taken, the vacation certificate must
        # mention: the number of days already granted + the related gross allowance.
        current_year_start = self.employee_id.end_notice_period.replace(month=1, day=1)
        current_year_end = self.employee_id.end_notice_period.replace(month=12, day=31)
        payslips_n = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_from', '>=', current_year_start),
            ('date_to', '<=', current_year_end),
            ('state', 'in', ['done', 'paid'])])
        european_wds = payslips_n.worked_days_line_ids.filtered(lambda wd: wd.code == 'LEAVE216')
        european_leaves_amount = sum(european_wds.mapped('amount'))
        european_leaves_days = sum(european_wds.mapped('number_of_days'))
        european_amount_to_deduct = max(european_leaves_amount, 0)

        self.env['hr.payslip.input'].create([{
            'payslip_id': termination_payslip_n.id,
            'sequence': 2,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_gross_ref').id,
            'amount': self.net_n + self.fictitious_remuneration_n,
            'contract_id': termination_payslip_n.contract_id.id
        }, {
            'payslip_id': termination_payslip_n.id,
            'sequence': 3,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_allocation').id,
            'amount': 0,
            'contract_id': termination_payslip_n.contract_id.id
        }, {
            'payslip_id': termination_payslip_n.id,
            'sequence': 4,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_time_off_taken').id,
            'amount': 0,
            'contract_id': termination_payslip_n.contract_id.id
        }, {
            'payslip_id': termination_payslip_n.id,
            'sequence': 5,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_annual_taxable_amount').id,
            'amount': annual_gross,
            'contract_id': termination_payslip_n.contract_id.id
        }, {
            'payslip_id': termination_payslip_n.id,
            'sequence': 6,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_european_leave').id,
            'amount': european_amount_to_deduct,
            'contract_id': termination_payslip_n.contract_id.id
        }, {
            'payslip_id': termination_payslip_n.id,
            'sequence': 7,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_european_leave_days').id,
            'amount': european_leaves_days,
            'contract_id': termination_payslip_n.contract_id.id
        }])
        termination_payslip_n.compute_sheet()
        termination_payslip_n.name = '%s - %s' % (struct_n_id.payslip_name, self.employee_id.display_name)

        termination_payslip_n1 = self.env['hr.payslip'].create({
            'name': '%s - %s' % (struct_n1_id.payslip_name, self.employee_id.display_name),
            'employee_id': self.employee_id.id,
            'contract_id': self.employee_id.contract_id.id,
            'struct_id': struct_n1_id.id,
            'date_from': (self.employee_id.contract_id.date_end or fields.Date.today) + relativedelta(day=1),
            'date_to': (self.employee_id.contract_id.date_end or fields.Date.today) + relativedelta(day=31),
        })
        termination_payslip_n1.worked_days_line_ids = [(5, 0, 0)]

        # As regards the recovery of amounts for European holidays (“additional holidays”), the
        # amount paid in advance is
        # - or recovered from the double vacation pay (part 85%) for the following year;
        # - or, when the worker leaves, on the amount of the exit pay. The legislation does not
        # specifically state whether, in the event of an exit, the recovery is on the single or
        # the double, but, in order to be consistent, I would do the recovery on the double
        # (85% of 7.67 %).
        # In addition, when "additional" vacation has been taken, the vacation certificate must
        # mention: the number of days already granted + the related gross allowance.
        current_year = self.employee_id.end_notice_period.replace(month=1, day=1)
        previous_year = current_year + relativedelta(years=-1)
        double_structure = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday')
        double_holiday_n = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_to', '>=', current_year),
            ('state', 'in', ['done', 'paid', 'verify']),
            ('struct_id', '=', double_structure.id)])
        # Part already deducted on the double holiday for year N
        double_amount_n = -double_holiday_n._get_line_values(['EU.LEAVE.DEDUC'], compute_sum=True)['EU.LEAVE.DEDUC']['sum']['total']
        # Original Amount to deduct
        payslip_n1 = self.env['hr.payslip'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_to', '>=', previous_year),
            ('date_from', '<', current_year),
            ('state', 'in', ['done', 'paid'])])
        european_wds = payslip_n1.mapped('worked_days_line_ids').filtered(lambda wd: wd.code == 'LEAVE216')
        european_leaves_amount = sum(european_wds.mapped('amount'))
        european_leaves_days = sum(european_wds.mapped('number_of_days'))
        european_amount_to_deduct = max(european_leaves_amount - double_amount_n, 0)

        self.env['hr.payslip.input'].create([{
            'payslip_id': termination_payslip_n1.id,
            'sequence': 1,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_gross_ref').id,
            'amount': self.net_n1 + self.fictitious_remuneration_n1,
            'contract_id': termination_payslip_n1.contract_id.id
        }, {
            'payslip_id': termination_payslip_n1.id,
            'sequence': 3,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_allocation').id,
            'amount': self.time_off_allocated,
            'contract_id': termination_payslip_n1.contract_id.id
        }, {
            'payslip_id': termination_payslip_n1.id,
            'sequence': 4,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_time_off_taken').id,
            'amount': self.time_off_taken,
            'contract_id': termination_payslip_n1.contract_id.id
        }, {
            'payslip_id': termination_payslip_n1.id,
            'sequence': 5,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_annual_taxable_amount').id,
            'amount': annual_gross,
            'contract_id': termination_payslip_n1.contract_id.id
        }, {
            'payslip_id': termination_payslip_n1.id,
            'sequence': 6,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_european_leave').id,
            'amount': european_amount_to_deduct,
            'contract_id': termination_payslip_n1.contract_id.id
        }, {
            'payslip_id': termination_payslip_n1.id,
            'sequence': 7,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_european_leave_days').id,
            'amount': european_leaves_days,
            'contract_id': termination_payslip_n1.contract_id.id
        }])
        termination_payslip_n1.compute_sheet()
        termination_payslip_n1.name = '%s - %s' % (struct_n1_id.payslip_name, self.employee_id.display_name)

        return {
            'name': _('Termination'),
            'domain': [('id', 'in', [termination_payslip_n.id, termination_payslip_n1.id])],
            'res_model': 'hr.payslip',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
        }
