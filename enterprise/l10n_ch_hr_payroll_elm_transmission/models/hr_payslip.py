# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo import _, api, fields, models, Command
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round

from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    l10n_ch_laa_group = fields.Many2one("l10n.ch.accident.group", compute="_compute_l10n_ch_laa_group", store=True)
    laa_solution_number = fields.Selection(selection=[
        ('0', '0 - Not insured'),
        ('1', '1 - Occupational and Non-Occupational Insured, with deductions'),
        ('2', '2 - Occupational and Non-Occupational Insured, without deductions'),
        ('3', '3 - Only Occupational Insured')], compute="_compute_laa_solution_number", store=True)
    l10n_ch_location_unit_id = fields.Many2one("l10n.ch.location.unit", compute="_compute_l10n_ch_location_unit_id", store=True)
    l10n_ch_txb_code = fields.Char(compute="_compute_l10n_ch_is_code", store=True)
    l10n_ch_is_correction = fields.Many2one('hr.employee.is.line', compute="_compute_l10n_ch_is_correction", store=True)
    l10n_ch_monthly_snapshot = fields.Many2one('l10n.ch.employee.monthly.values', compute="_compute_l10n_ch_monthly_snapshot", store=True)
    l10n_ch_swiss_wage_ids = fields.One2many('l10n.ch.swiss.wage.component', 'payslip_id', compute="_compute_l10n_ch_swiss_wage_ids", store=True)
    l10n_ch_validation_errors = fields.Json(related="l10n_ch_monthly_snapshot.validation_errors")

    @api.model_create_multi
    def create(self, vals_list):
        swiss_employees = self.env['hr.employee'].browse([val["employee_id"] for val in vals_list if "employee_id" in val]).filtered(lambda e: e.company_id.country_id.code == 'CH')
        swiss_employees._create_or_update_snapshot()
        return super().create(vals_list)

    def _get_schedule_period_start(self):
        if self.struct_id.code == "CHMONTHLYELM":
            today = date.today()
            return today.replace(day=1)
        else:
            return super()._get_schedule_period_start()

    def _get_schedule_timedelta(self):
        self.ensure_one()
        if self.struct_id.code == "CHMONTHLYELM":
            return relativedelta(months=1, days=-1)
        else:
            return super()._get_schedule_timedelta()

    @api.depends('date_from', 'contract_id', 'struct_id')
    def _compute_date_to(self):
        swissdec_slips = self.filtered(lambda p: p.struct_id.code == 'CHMONTHLYELM')

        for payslip in swissdec_slips:
            if payslip.struct_id.code == "CHMONTHLYELM":
                payslip.date_to = payslip.date_from + payslip._get_schedule_timedelta()
        super(HrPayslip, self - swissdec_slips)._compute_date_to()

    def _get_contract_days_in_payslip_range(self, date_start, date_end):
        """
        Return the full count of actual calendar days in the payslip
        for which the employee is under contract.
        """
        self.ensure_one()
        if self.company_id.l10n_ch_30_day_method:
            return self._l10n_ch_get_as_days_count(date_start, date_end)

        payslip_start = self.date_from
        payslip_end = self.date_to


        contract_start = date_start
        contract_end = date_end or payslip_end


        overlap_start = max(payslip_start, contract_start)
        overlap_end = min(payslip_end, contract_end)
        if overlap_start > overlap_end:
            return 0

        return (overlap_end - overlap_start).days + 1

    def _get_payroll_impacting_swissdec(self):
        leave_type_refs = [
            'l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_unpaid_lt',
            'l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_illness_lt',
            'l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_accident_lt',
            'l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_maternity_lt',
            'l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_military_lt',
            'l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_interruption_of_work_lt',
        ]
        valid_leave_types = [self.env.ref(ref, raise_if_not_found=False) for ref in leave_type_refs]
        valid_leave_types_ids = [lt.id for lt in valid_leave_types if lt]

        return self.env['hr.leave.type'].browse(valid_leave_types_ids)

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to')
    def _compute_l10n_ch_swiss_wage_ids(self):
        swissdec_slips = self.filtered(lambda p: p.struct_id.code == 'CHMONTHLYELM')
        if not swissdec_slips:
            return
        swissdec_slips.update({'l10n_ch_swiss_wage_ids': [(5, 0, 0)]})

        payroll_impacting_leave_types = self._get_payroll_impacting_swissdec()

        leaves_grouped_by_employee = dict(self.env['hr.leave']._read_group(
            domain=[('employee_id', 'in', swissdec_slips.mapped('employee_id').ids),
                    ('state', 'in', ['validate', 'validate1']),
                    ('holiday_status_id', 'in', payroll_impacting_leave_types.ids)],
            groupby=['employee_id'],
            aggregates=['id:recordset']
        ))

        grouped_recurring_hours = dict(self.env['l10n.ch.hr.contract.wage']._read_group(domain=[('contract_id', 'in', swissdec_slips.contract_id.ids),
                                                                                                ('date_start', '=', False),
                                                                                                ('uom', '=', 'hours')], groupby=['contract_id'], aggregates=['id:recordset']))
        grouped_one_time_hours = self.env['l10n.ch.hr.contract.wage']._read_group(domain=[('contract_id', 'in', swissdec_slips.contract_id.ids),
                                                                                          ('date_start', '!=', False),
                                                                                          ('uom', '=', 'hours')], groupby=['contract_id', 'date_start:year', 'date_start:month'], aggregates=['id:recordset'])
        grouped_one_time_wages_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: self.env['l10n.ch.hr.contract.wage'])))

        for contract, date_y, date_m, wage in grouped_one_time_hours:
            grouped_one_time_wages_dict[contract][date_y.year][date_m.month] += wage


        monthly_work_entry = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_monthly_wt', raise_if_not_found=False)
        hourly_work_entry = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_hourly_wt', raise_if_not_found=False)
        lesson_work_entry = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_lesson_wt', raise_if_not_found=False)
        overtime_work_entry = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_overtime_wt', raise_if_not_found=False)
        overtime_125_work_entry = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_overtime_125_wt', raise_if_not_found=False)
        overtime_150_work_entry = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_overtime_150_wt', raise_if_not_found=False)
        overtime_200_work_entry = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_overtime_200_wt', raise_if_not_found=False)
        on_call_duty_125_work_entry = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_oncall_125_wt', raise_if_not_found=False)
        night_shift_110_work_entry = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_night_110_wt', raise_if_not_found=False)

        mapped_hourly_absence = {
            "CH_ACCIDENT": self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_accident_wt_hourly', raise_if_not_found=False),
            "CH_ILLNESS": self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_illness_wt_hourly', raise_if_not_found=False),
            "CH_MATERNITY": self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_maternity_wt_hourly', raise_if_not_found=False),
            "CH_MILITARY": self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_military_wt_hourly', raise_if_not_found=False),
        }


        for payslip in swissdec_slips:
            if not payslip.contract_id:
                continue
            reccurent_wage_types = grouped_recurring_hours.get(payslip.contract_id, self.env['l10n.ch.hr.contract.wage'])
            one_time_wage_types = grouped_one_time_wages_dict[payslip.contract_id][payslip.date_to.year][payslip.date_to.month]
            grouped_recurring_by_input_wage_types = reccurent_wage_types.grouped(lambda w: w.input_type_id.code)
            grouped_one_time_by_input_wage_types = one_time_wage_types.grouped(lambda w: w.input_type_id.code)

            worked_day_vals = []
            base_days = payslip._get_contract_days_in_payslip_range(payslip.contract_id.date_start, payslip.contract_id.date_end)
            total_days = payslip.date_to.day

            if self.company_id.l10n_ch_30_day_method:
                total_days = 30

            contract = payslip.contract_id
            has_monthly = contract.l10n_ch_has_monthly
            has_hourly = contract.l10n_ch_has_hourly
            has_lesson = contract.l10n_ch_has_lesson

            monthly_wage = contract.wage
            hourly_wage = contract.hourly_wage
            lesson_wage = contract.l10n_ch_lesson_wage



            range_min = max(payslip.date_from, contract.date_start)
            range_max = min(payslip.date_to, contract.date_end or payslip.date_to)

            leaves = leaves_grouped_by_employee.get(payslip.employee_id, self.env['hr.leave']).filtered(lambda l: l.date_from.date() <= range_max and l.date_to.date() >= range_min)

            leave_days_map = {}
            for leave in leaves:
                overlap_start = max(range_min, leave.date_from.date())
                overlap_end = min(range_max, leave.date_to.date())

                overlap_days = payslip._get_contract_days_in_payslip_range(overlap_start, overlap_end)
                leave_type = leave.holiday_status_id
                leave_days_map.setdefault(leave_type, [])
                if leave.request_unit_half:
                    overlap_days = overlap_days / 2
                leave_days_map[leave_type] += [(overlap_days, leave)]

            total_leave_days = 0.0
            for leave_type, all_leaves in leave_days_map.items():
                for leave in all_leaves:
                    nb_days = leave[0]
                    leave_id = leave[1]
                    work_entry_type = leave_type.work_entry_type_id
                    if work_entry_type.code == "CH_Interruption":
                        disability_percentage = 1
                        continued_pay = 0
                    else:
                        disability_percentage = leave_id.l10n_ch_disability_percentage
                        continued_pay = leave_id.l10n_ch_continued_pay_percentage
                    proportion_in_classic_wage = 1 - disability_percentage

                    if has_monthly:
                        if proportion_in_classic_wage > 0:
                            worked_day_vals += [(0, 0, {
                                'name': f"{monthly_work_entry.name} : {nb_days} / {total_days}",
                                'sequence': 5,
                                'work_entry_type_id': monthly_work_entry.id,
                                'salary_base': monthly_wage * proportion_in_classic_wage,
                                'rate': nb_days / total_days
                            })]
                    if (has_hourly or has_lesson) and work_entry_type.code in mapped_hourly_absence:
                        worked_day_vals += [(0, 0, {
                            'name': f"{mapped_hourly_absence[work_entry_type.code].name} : {nb_days} / {total_days}",
                            'sequence': 5,
                            'work_entry_type_id': mapped_hourly_absence[work_entry_type.code].id,
                            'salary_base': hourly_wage or lesson_wage,
                            'rate': 0
                        })]
                    if has_monthly:
                        worked_day_vals += [(0, 0, {
                            'name': f"{work_entry_type.name} : {nb_days} / {total_days}",
                            'sequence': 10,
                            'work_entry_type_id': work_entry_type.id ,
                            'salary_base': monthly_wage * disability_percentage * nb_days / total_days if has_monthly else 0,
                            'rate': continued_pay,
                        })]
                    total_leave_days += nb_days

            regular_days = base_days - total_leave_days
            if regular_days < 0:
                regular_days = 0.0

            if has_monthly:
                worked_day_vals += [(0, 0, {
                    'name': f"{monthly_work_entry.name} : {regular_days} / {total_days}",
                    'sequence': 5,
                    'work_entry_type_id': monthly_work_entry.id,
                    'salary_base': monthly_wage,
                    'rate': regular_days / total_days,
                })]


            if grouped_recurring_by_input_wage_types.get("WT_Hours", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': hourly_work_entry.id,
                    'salary_base': hourly_wage,
                    'rate': sum(grouped_recurring_by_input_wage_types.get("WT_Hours").mapped('amount')) * base_days / total_days,
                })]

            if grouped_one_time_by_input_wage_types.get("WT_Hours", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': hourly_work_entry.id,
                    'salary_base': hourly_wage,
                    'rate': sum(grouped_one_time_by_input_wage_types.get("WT_Hours").mapped('amount')),
                })]

            if not (grouped_recurring_by_input_wage_types.get("WT_Hours", False) or grouped_one_time_by_input_wage_types.get("WT_Hours", False)) and has_hourly:
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': hourly_work_entry.id,
                    'salary_base': hourly_wage,
                    'rate': 0,
                })]

            if grouped_recurring_by_input_wage_types.get("WT_Overtime", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': overtime_work_entry.id,
                    'salary_base': hourly_wage,
                    'rate': sum(grouped_recurring_by_input_wage_types.get("WT_Overtime").mapped('amount')) * base_days / total_days,
                })]

            if grouped_one_time_by_input_wage_types.get("WT_Overtime", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': overtime_work_entry.id,
                    'salary_base': hourly_wage,
                    'rate': sum(grouped_one_time_by_input_wage_types.get("WT_Overtime").mapped('amount')),
                })]

            if grouped_recurring_by_input_wage_types.get("WT_Overtime_125", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': overtime_125_work_entry.id,
                    'salary_base': hourly_wage * 1.25,
                    'rate': sum(grouped_recurring_by_input_wage_types.get("WT_Overtime_125").mapped(
                        'amount')) * base_days / total_days,
                })]

            if grouped_one_time_by_input_wage_types.get("WT_Overtime_125", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': overtime_125_work_entry.id,
                    'salary_base': hourly_wage * 1.25,
                    'rate': sum(grouped_one_time_by_input_wage_types.get("WT_Overtime_125").mapped('amount')),
                })]

            if grouped_recurring_by_input_wage_types.get("WT_Overtime_150", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': overtime_150_work_entry.id,
                    'salary_base': hourly_wage * 1.5,
                    'rate': sum(grouped_recurring_by_input_wage_types.get("WT_Overtime_150").mapped(
                        'amount')) * base_days / total_days,
                })]

            if grouped_one_time_by_input_wage_types.get("WT_Overtime_150", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': overtime_150_work_entry.id,
                    'salary_base': hourly_wage * 1.5,
                    'rate': sum(grouped_one_time_by_input_wage_types.get("WT_Overtime_150").mapped('amount')),
                })]

            if grouped_recurring_by_input_wage_types.get("WT_Overtime_200", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': overtime_200_work_entry.id,
                    'salary_base': hourly_wage * 2.0,
                    'rate': sum(grouped_recurring_by_input_wage_types.get("WT_Overtime_200").mapped(
                        'amount')) * base_days / total_days,
                })]

            if grouped_one_time_by_input_wage_types.get("WT_Overtime_200", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': overtime_200_work_entry.id,
                    'salary_base': hourly_wage * 2.0,
                    'rate': sum(grouped_one_time_by_input_wage_types.get("WT_Overtime_200").mapped('amount')),
                })]

            if grouped_recurring_by_input_wage_types.get("WT_on_call_125", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': on_call_duty_125_work_entry.id,
                    'salary_base': hourly_wage * 1.25,
                    'rate': sum(grouped_recurring_by_input_wage_types.get("WT_on_call_125").mapped(
                        'amount')) * base_days / total_days,
                })]

            if grouped_one_time_by_input_wage_types.get("WT_on_call_125", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': on_call_duty_125_work_entry.id,
                    'salary_base': hourly_wage * 1.25,
                    'rate': sum(grouped_one_time_by_input_wage_types.get("WT_on_call_125").mapped('amount')),
                })]

            if grouped_recurring_by_input_wage_types.get("WT_night_110", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': night_shift_110_work_entry.id,
                    'salary_base': hourly_wage * 1.1,
                    'rate': sum(grouped_recurring_by_input_wage_types.get("WT_night_110").mapped(
                        'amount')) * base_days / total_days,
                })]

            if grouped_one_time_by_input_wage_types.get("WT_night_110", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': night_shift_110_work_entry.id,
                    'salary_base': hourly_wage * 1.1,
                    'rate': sum(grouped_one_time_by_input_wage_types.get("WT_night_110").mapped('amount')),
                })]

            if grouped_recurring_by_input_wage_types.get("WT_Lesson_input", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': lesson_work_entry.id,
                    'salary_base': lesson_wage,
                    'rate': sum(grouped_recurring_by_input_wage_types.get("WT_Lesson_input").mapped(
                        'amount')) * base_days / total_days,
                })]

            if grouped_one_time_by_input_wage_types.get("WT_Lesson_input", False):
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': lesson_work_entry.id,
                    'salary_base': lesson_wage,
                    'rate': sum(grouped_one_time_by_input_wage_types.get("WT_Lesson_input").mapped(
                        'amount'))
                })]

            if not (grouped_recurring_by_input_wage_types.get("WT_Lesson_input", False) or grouped_one_time_by_input_wage_types.get("WT_Lesson_input", False)) and has_lesson:
                worked_day_vals += [(0, 0, {
                    'sequence': 15,
                    'work_entry_type_id': lesson_work_entry.id,
                    'salary_base': lesson_wage,
                    'rate': 0,
                })]

            payslip.update({
                "l10n_ch_swiss_wage_ids": worked_day_vals
            })

    @api.depends('employee_id', "date_from", "date_to")
    def _compute_l10n_ch_monthly_snapshot(self):
        swiss_payslips = self.filtered(lambda p: p.struct_id.code == "CHMONTHLYELM")
        if not swiss_payslips:
            return

        mapped_snapshots = self.env['l10n.ch.employee.yearly.values']._get_mapped_snapshots(
            domain=[('employee_id', 'in', swiss_payslips.mapped('employee_id').ids)]
        )

        slips_grouped_by_date = swiss_payslips.grouped('date_to')

        new_snapshots_created = False

        for date_group, slips in slips_grouped_by_date.items():
            year = date_group.year
            month = date_group.month

            employees_missing_snapshot = slips.employee_id.filtered(
                lambda e: not mapped_snapshots[e][year][month]
            )

            if employees_missing_snapshot:
                employees_missing_snapshot.with_context(l10n_ch_reference_date=date_group)._create_or_update_snapshot()
                new_snapshots_created = True

        if new_snapshots_created:
            mapped_snapshots = self.env['l10n.ch.employee.yearly.values']._get_mapped_snapshots(
                domain=[('employee_id', 'in', swiss_payslips.mapped('employee_id').ids)]
            )

        for payslip in swiss_payslips:
            month = payslip.date_to.month
            year = payslip.date_to.year
            payslip.l10n_ch_monthly_snapshot = mapped_snapshots[payslip.employee_id][year][month]

    @api.depends('employee_id')
    def _compute_l10n_ch_is_correction(self):
        swiss_payslips = self.filtered(lambda p: p.struct_id.code == "CHMONTHLYELM")
        if not swiss_payslips:
            return
        grouped_pending_corrections = dict(self.env['hr.employee.is.line']._read_group(
            domain=[('employee_id', 'in', swiss_payslips.employee_id.ids),
                    ('state', '=', 'pending')],
            groupby=['employee_id'], aggregates=['id:recordset']))

        for payslip in swiss_payslips:
            pending_c = grouped_pending_corrections.get(payslip.employee_id, False)
            if pending_c:
                payslip.l10n_ch_is_correction = pending_c[-1]
            else:
                payslip.l10n_ch_is_correction = False

    @api.depends('line_ids.total')
    def _compute_basic_net(self):
        elm_slips = self.filtered(lambda p: p.struct_id.code == "CHMONTHLYELM")
        if not elm_slips:
            return super()._compute_basic_net()
        line_values = (self._origin)._get_line_values(["WT_1000", "BASICHOURLY", "BASICLESSON", "GROSS_SALARY", 'NET', 'Net_Paid'])
        for payslip in elm_slips:
            payslip.basic_wage = line_values['WT_1000'][payslip._origin.id]['total'] + line_values['BASICHOURLY'][payslip._origin.id]['total'] + line_values['BASICLESSON'][payslip._origin.id]['total']
            payslip.gross_wage = line_values['GROSS_SALARY'][payslip._origin.id]['total']
            payslip.net_wage = line_values['NET'][payslip._origin.id]['total'] + line_values['Net_Paid'][payslip._origin.id]['total']
        super(HrPayslip, self - elm_slips)._compute_basic_net()

    def _get_base_local_dict(self):
        res = super()._get_base_local_dict()
        if self.struct_id.code == "CHMONTHLYELM":
            date_from = date(self.date_from.year, 1, 1)
            date_to = self.date_from

            wage_components = defaultdict(lambda: {
                "base": 0,
                "rate": 0,
                "total": 0
            })

            for work_entry_type, wages in self.l10n_ch_swiss_wage_ids.grouped("work_entry_type_id").items():
                if len(wages) == 1:
                    # We can display base and rate since the components are made of one line
                    wage_components[work_entry_type.code]["base"] = wages.salary_base
                    wage_components[work_entry_type.code]["rate"] = wages.rate * 100
                    wage_components[work_entry_type.code]["total"] = wages.amount
                else:
                    total_sum = sum(wages.mapped('amount'))
                    wage_components[work_entry_type.code]["total"] = total_sum

            res.update({
                'ch_wage_components': wage_components,
            })

            if self.l10n_ch_after_departure_payment:
                reference_payslip = self.env['hr.payslip'].search([
                    ('employee_id', '=', self.employee_id.id),
                    ('state', 'in', ['done', 'paid']),
                    ('struct_id.code', '=', 'CHMONTHLYELM'),
                    ('l10n_ch_after_departure_payment', '=', False),
                ], order="date_from DESC", limit=1)
                if not reference_payslip:
                    raise ValidationError(_("A previous payslip in the system is required for after departure payement to work."))
                if reference_payslip.date_from.year != self.date_from.year:
                    date_from = date(reference_payslip.date_from.year, 1, 1)
                    date_to = self.date_from
                res.update({
                    'reference_is_slip': reference_payslip
                })

            res.update({
                'previous_payslips': self.env['hr.payslip'].search([
                    ('employee_id', '=', self.employee_id.id),
                    ('date_from', '>=', date_from),
                    ('date_to', '<', date_to),
                    ('state', 'in', ['done', 'paid']),
                    ('struct_id.code', '=', 'CHMONTHLYELM'),
                ]),
            })
        return res

    @api.depends('contract_id.l10n_ch_location_unit_id')
    def _compute_l10n_ch_location_unit_id(self):
        for payslip in self:
            if payslip.state not in ['draft', 'verify'] or payslip.company_id.country_id.code != "CH":
                continue
            payslip.l10n_ch_location_unit_id = payslip.contract_id.l10n_ch_location_unit_id

    @api.depends('contract_id.l10n_ch_laa_group')
    def _compute_l10n_ch_laa_group(self):
        for payslip in self:
            if payslip.state not in ['draft', 'verify'] or payslip.company_id.country_id.code != "CH":
                continue
            payslip.l10n_ch_laa_group = payslip.contract_id.l10n_ch_laa_group

    @api.depends('contract_id.laa_solution_number')
    def _compute_laa_solution_number(self):
        for payslip in self:
            if payslip.state not in ['draft', 'verify'] or payslip.company_id.country_id.code != "CH":
                continue
            payslip.laa_solution_number = payslip.contract_id.laa_solution_number

    def compute_sheet(self):
        # Complete compute Sheet override to avoid any overrides from other apps
        payslips = self.filtered(lambda slip: slip.state in ['draft', 'verify'] and slip.struct_id.code == "CHMONTHLYELM")
        if not payslips:
            return super().compute_sheet()
        payslips.line_ids.unlink()
        payslips.l10n_ch_is_log_line_ids.unlink()
        payslips._compute_l10n_ch_monthly_snapshot()
        payslips._compute_l10n_ch_is_correction()
        payslips._compute_l10n_ch_is_code()
        payslips._compute_l10n_ch_is_model()

        self.env.flush_all()
        today = fields.Date.today()
        for payslip in payslips:
            number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
            payslip.write({
                'number': number,
                'state': 'verify',
                'compute_date': today
            })
        self.env['hr.payslip.line'].create(payslips._get_payslip_lines())

        super(HrPayslip, self - payslips).compute_sheet()

    def action_payslip_done(self):
        res = super().action_payslip_done()
        swiss_payslips = self.filtered(lambda p: p.struct_id.country_id.code == "CH")
        if not swiss_payslips:
            return res
        swiss_payslips.l10n_ch_is_correction.action_done()
        for ref_date, payslips_by_date in swiss_payslips.grouped('date_from').items():
            payslips_by_date.employee_id.with_context(
                update_salaries=True,
                l10n_ch_reference_date=ref_date
            )._create_or_update_snapshot()
        return res

    def action_payslip_cancel(self):
        res = super().action_payslip_cancel()
        swiss_payslips = self.filtered(lambda p: p.struct_id.country_id.code == "CH")
        if not swiss_payslips:
            return res
        swiss_payslips.l10n_ch_is_correction.action_pending()
        swiss_payslips.l10n_ch_is_log_line_ids.unlink()
        for ref_date, payslips_by_date in swiss_payslips.grouped('date_from').items():
            payslips_by_date.employee_id.with_context(
                update_salaries=True,
                unlock_pay_period=True,
                l10n_ch_reference_date=ref_date
            )._create_or_update_snapshot()
        return res

    @api.depends('employee_id', 'l10n_ch_monthly_snapshot')
    def _compute_l10n_ch_is_code(self):
        for payslip in self:
            if payslip.state not in ['draft', 'verify'] or payslip.company_id.country_id.code != "CH":
                continue
            valid_source_tax_snapshot = payslip.l10n_ch_monthly_snapshot
            source_tax_code = False
            txb_code = False
            if valid_source_tax_snapshot.employee_meta_data:
                source_tax_canton = valid_source_tax_snapshot.employee_meta_data.get("st-canton", False)
                source_tax_scale = valid_source_tax_snapshot.employee_meta_data.get("st-code", False)
                source_tax_municipality = valid_source_tax_snapshot.employee_meta_data.get("st-municipality", False)
                txb_code = valid_source_tax_snapshot.employee_meta_data.get("txb-code", False)
                if source_tax_canton and source_tax_scale and source_tax_municipality:
                    source_tax_code = f"{source_tax_canton}-{source_tax_scale}-{source_tax_municipality}"
            payslip.l10n_ch_is_code = source_tax_code
            payslip.l10n_ch_txb_code = txb_code

    def _has_lpp_in_percentage(self):
        # To be overriden in ELM 5.3 certification module
        self.ensure_one()
        return False

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to', 'struct_id')
    def _compute_input_line_ids(self):
        swiss_slips = self.filtered(lambda p: p.struct_id.code == "CHMONTHLYELM")
        if not swiss_slips:
            return super()._compute_input_line_ids()
        payroll_impacting_leave_types = self._get_payroll_impacting_swissdec()
        work_interruption_type = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_interruption_of_work_lt',raise_if_not_found=False)
        swiss_slips.update({'input_line_ids': [(5, 0, 0)]})
        leaves_grouped_by_employee = dict(self.env['hr.leave']._read_group(
            domain=[('employee_id', 'in', swiss_slips.mapped('employee_id').ids),
                    ('state', 'in', ['validate', 'validate1']),
                    ('holiday_status_id', 'in', payroll_impacting_leave_types.ids)],
            groupby=['employee_id'],
            aggregates=['id:recordset']
        ))

        lpp_input = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_5050')
        lpp_comp_input = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_hr_elm_input_WT_7050')
        grouped_recurring_wages = dict(self.env['l10n.ch.hr.contract.wage']._read_group(domain=[('contract_id', 'in', swiss_slips.contract_id.ids),
                                                                                                ('date_start', '=', False),
                                                                                                ('uom', '!=', 'hours')], groupby=['contract_id'], aggregates=['id:recordset']))
        grouped_one_time_wages = self.env['l10n.ch.hr.contract.wage']._read_group(domain=[('contract_id', 'in', swiss_slips.contract_id.ids),
                                                                                          ('date_start', '!=', False),
                                                                                          ('uom', '!=', 'hours')], groupby=['contract_id', 'date_start:year', 'date_start:month'], aggregates=['id:recordset'])
        grouped_one_time_wages_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: self.env['l10n.ch.hr.contract.wage'])))

        for contract, date_y, date_m, wage in grouped_one_time_wages:
            grouped_one_time_wages_dict[contract][date_y.year][date_m.month] += wage

        for slip in swiss_slips:
            if not slip.contract_id:
                continue
            range_min = max(slip.date_from, slip.contract_id.date_start)
            range_max = min(slip.date_to, slip.contract_id.date_end or slip.date_to)

            has_pay_interruption = leaves_grouped_by_employee.get(slip.employee_id, self.env['hr.leave']).filtered(lambda l: l.date_from.date() <= range_max and l.date_to.date() >= range_min and l.holiday_status_id.id == work_interruption_type.id)


            input_line_vals = []
            wage_types = grouped_one_time_wages_dict[slip.contract_id][slip.date_to.year][slip.date_to.month]
            recurring_wage_types = grouped_recurring_wages.get(slip.contract_id, self.env['l10n.ch.hr.contract.wage'])

            has_lpp_in_percentage = slip._has_lpp_in_percentage()

            if not slip.l10n_ch_lpp_not_insured and slip.l10n_ch_lpp_insurance_id and not slip.l10n_ch_after_departure_payment and not has_pay_interruption.l10n_ch_lpp_interruption and not has_lpp_in_percentage:
                if slip.contract_id.lpp_employee_amount:
                    input_line_vals.append(Command.create({
                        'amount': slip.contract_id.lpp_employee_amount,
                        'input_type_id': lpp_input.id,
                    }))
                if slip.contract_id.lpp_company_amount:
                    input_line_vals.append(Command.create({
                        'amount': slip.contract_id.lpp_company_amount,
                        'input_type_id': lpp_comp_input.id,
                    }))

            for wage_type in wage_types:
                input_line_vals.append(Command.create({
                    'name': wage_type.description,
                    'amount': wage_type.amount,
                    'input_type_id': wage_type.input_type_id.id,
                }))

            if not has_pay_interruption.l10n_ch_pay_interruption:
                for wage_type in recurring_wage_types:
                    input_line_vals.append(Command.create({
                        'name': wage_type.description,
                        'amount': wage_type.amount,
                        'input_type_id': wage_type.input_type_id.id,
                    }))
            input_line_vals += slip._get_additional_input_line_vals()
            slip.update({'input_line_ids': input_line_vals})

        super(HrPayslip, self - swiss_slips)._compute_input_line_ids()

    def _get_additional_input_line_vals(self):
        # To be overriden in additional Swiss modules
        return []

    def _reverse_log_lines(self, payslip_to_reverse, manual_correction=None):
        # Reversal, this requires heavy logic since one payslip could be corrected multiple times through various payslips
        # The returned result is the total compensation
        self.ensure_one()
        log_lines = self.env['hr.payslip.is.log.line'].search(['|', '&', ('payslip_id', '=', payslip_to_reverse.id), ('is_correction', '=', False), '&', ('corrected_slip_id', '=', payslip_to_reverse.id), ('correction_type', '=', 'new')]).sorted(lambda l: l.payslip_id.date_to)
        total_compensation = 0
        if log_lines:
            grouped_lines = log_lines.grouped('payslip_id')
            old_grouped_lines_key = max(grouped_lines, key=lambda p: p.date_to)
            old_grouped_lines = grouped_lines[old_grouped_lines_key]
            old_grouped_lines_by_code = old_grouped_lines.grouped('code')

            valid_code = old_grouped_lines_by_code['ASDAYS'].is_code
            valid_canton = old_grouped_lines_by_code['ASDAYS'].source_tax_canton
            valid_municipality = old_grouped_lines_by_code['ASDAYS'].source_tax_municipality
            for line in old_grouped_lines:
                self._log_is_line(is_canton=valid_canton, is_code=valid_code, municipality=valid_municipality, code=line.code, amount=-line.amount, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='old')
                if line.code == 'IS':
                    total_compensation += line.amount
            if manual_correction:
                new_canton = manual_correction.l10n_ch_source_tax_canton
                new_municipality = manual_correction.l10n_ch_source_tax_municipality
                new_code = manual_correction.tax_code

                self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ASDAYS', amount=manual_correction.insurance_days, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISWORKEDDAYS', amount=manual_correction.worked_days, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISWORKEDDAYSINCH', amount=manual_correction.worked_days_in_switzerland, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISDTSALARYAPERIODIC', amount=manual_correction.source_tax_periodic_determinant_salary, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISDTSALARYPERIODIC', amount=manual_correction.source_tax_aperiodic_determinant_salary, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISSALARY', amount=manual_correction.source_tax_salary, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISDTSALARY', amount=manual_correction.rate_determinant_salary, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='IS', amount=manual_correction.source_tax_amount, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                total_compensation += manual_correction.source_tax_amount
            else:
                new_canton, new_code, new_municipality = self.l10n_ch_is_code.split('-')
                old_as_days = old_grouped_lines_by_code.get('ASDAYS', self.env['hr.payslip.is.log.line']).amount
                old_is_days = old_grouped_lines_by_code.get('ISWORKEDDAYS', self.env['hr.payslip.is.log.line']).amount
                old_is_ch_days = old_grouped_lines_by_code.get('ISWORKEDDAYSINCH', self.env['hr.payslip.is.log.line']).amount


                self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ASDAYS', amount=old_as_days, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISWORKEDDAYS', amount=old_is_days, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISWORKEDDAYSINCH', amount=old_is_ch_days, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                previous_payslips = self.env['hr.payslip'].search([
                    ('employee_id', '=', self.employee_id.id),
                    ('date_from', '>=', date(payslip_to_reverse.date_from.year, 1, 1)),
                    ('date_to', '<', payslip_to_reverse.date_to),
                    ('state', 'in', ['done', 'paid']),
                    ('struct_id.code', '=', 'CHMONTHLYELM'),
                ])
                if new_code in ['NON', 'NOY']:
                    self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISSALARY', amount=0, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                    self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISDTSALARY', amount=0, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                    self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='IS', amount=0, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                else:

                    line_values = payslip_to_reverse._get_line_values(['ISSALARYDTP', 'ISSALARYDTAP', '13THMONTH', '14THMONTH', '13THMONTH_HOURLY', '14THMONTH_HOURLY', 'ACTIVITYRATE', 'ACTIVITYRATETOTAL', 'ISWORKEDDAYSINCH', 'ISWORKEDDAYS'], compute_sum=True)
                    is_dt_salary_aperiodic = line_values['ISSALARYDTAP']['sum']['total']
                    is_dt_salary_periodic = line_values['ISSALARYDTP']['sum']['total'] / (line_values['ACTIVITYRATE']['sum']['total']/100) * (line_values['ACTIVITYRATETOTAL']['sum']['total']/100)
                    self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISDTSALARYAPERIODIC', amount=is_dt_salary_aperiodic, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                    self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISDTSALARYPERIODIC', amount=is_dt_salary_periodic, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')

                    log_lines = (previous_payslips + payslip_to_reverse)._get_is_log_lines(compute_total=True)["total"][new_canton]
                    year_days = log_lines['ISWORKEDDAYS']
                    year_days_ch = log_lines['ISWORKEDDAYSINCH']

                    # ISSALARY

                    thirteen_m = line_values['13THMONTH']['sum']['total'] + line_values['13THMONTH_HOURLY']['sum']['total'] + line_values['14THMONTH']['sum']['total'] + line_values['14THMONTH_HOURLY']['sum']['total']
                    salary_month = (line_values['ISSALARYDTP']['sum']['total'] - thirteen_m) * line_values['ISWORKEDDAYSINCH']['sum']['total'] / line_values['ISWORKEDDAYS']['sum']['total']
                    salary_year = (line_values['ISSALARYDTAP']['sum']['total'] + thirteen_m) * year_days_ch / year_days
                    is_salary = salary_month + salary_year
                    self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISSALARY', amount=is_salary, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')

                    # ISDTSALARY and IS
                    # Monthly is model
                    if new_canton not in ["GE", "FR", "TI", "VS", "VD"]:
                        as_days = old_as_days
                        is_dt_salary = is_dt_salary_periodic / as_days * 30 + is_dt_salary_aperiodic
                        self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISDTSALARY', amount=is_dt_salary, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')

                        min_is, rate = self._find_rate(f"{new_canton}-{new_code}-{new_municipality}", is_dt_salary)
                        is_amount = max(is_salary * rate / 100, 0)
                        total_compensation -= is_amount
                        self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='IS', amount=is_amount, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')

                    # Yearly IS Model
                    else:
                        total_is_dt_periodic = log_lines['ISDTSALARYPERIODIC']
                        total_is_dt_aperiodic = log_lines['ISDTSALARYAPERIODIC']
                        total_as_days = log_lines['ASDAYS']
                        yearly_is_dt_salary = total_is_dt_periodic / total_as_days * 360 + total_is_dt_aperiodic
                        is_dt_salary = yearly_is_dt_salary / 12.0
                        self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='ISDTSALARY', amount=is_dt_salary, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')

                        is_log_lines = (previous_payslips + payslip_to_reverse)._get_is_log_lines()[new_canton]
                        code_is_salary, code_total_is = is_log_lines[new_code]['ISSALARY'], is_log_lines[new_code]['IS']
                        min_is, rate = self._find_rate(f"{new_canton}-{new_code}-{new_municipality}", is_dt_salary)
                        is_amount = code_is_salary * rate / 100 - code_total_is
                        if is_amount >= 0:
                            is_amount = max(min_is, is_amount)
                        self._log_is_line(is_canton=new_canton, is_code=new_code, municipality=new_municipality, code='IS', amount=is_amount, corrected_payslip_id=payslip_to_reverse.id, is_correction=True, correction_type='new')
                        total_compensation -= is_amount

        return total_compensation

    def _find_rate(self, is_code, x, date_from=False):
        self.ensure_one()
        if not date_from:
            reference_date = self.date_from
        else:
            reference_date = date_from
        if is_code[3:5] in ['HE', 'ME', 'NO', 'SF']:
            canton, tax_code, municipality = is_code.split("-")
            category_code = tax_code[0:2]
            church_tax = tax_code[2]
            parameter_code = f"l10n_ch_withholding_tax_rates_{canton}_{category_code}_{church_tax}"
        else:
            canton, (tax_scale, child_count, church_tax), municipality = is_code.split("-")
            parameter_code = f"l10n_ch_withholding_tax_rates_{canton}_{church_tax}_{tax_scale}_{child_count}"
        rates = self._rule_parameter(parameter_code, reference_date)

        x = float_round(x, precision_rounding=1, rounding_method='DOWN')
        for low, high, min_amount, rate in rates:
            if low <= x <= high:
                return min_amount, rate
        return 0, 0


    def _log_is_line(self, is_canton, is_code, municipality, code, amount, corrected_payslip_id=False, is_correction=False, correction_type=False, is_correction_id=False):
        self.ensure_one()
        if code in ['ASDAYS', 'ISWORKEDDAYSINCH', 'ISWORKEDDAYS']:
            total_is = amount
        else:
            total = float_round(amount, precision_rounding=0.01, rounding_method="HALF-UP")
            if total % 0.05 >= 0.025:
                total_is = total + 0.05 - (total % 0.05)
            else:
                total_is = total - (total % 0.05)
        if total_is or code in ['ISDTSALARY', 'ISSALARY', 'IS']:
            self.env['hr.payslip.is.log.line'].create({
                'source_tax_canton': is_canton,
                'source_tax_municipality': municipality,
                'is_code': is_code,
                'code': code,
                'amount': total_is,
                'payslip_id': self.id,
                'is_correction': is_correction,
                'corrected_slip_id': corrected_payslip_id,
                'correction_type': correction_type,
                'is_correction_id': is_correction_id,
            })

    def _get_is_log_lines(self, compute_total=False):
        result = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        if not self:
            return result

        self.env.flush_all()
        self.env.cr.execute("""
            SELECT
                pl.source_tax_canton,
                pl.is_code,
                pl.code,
                SUM(pl.amount) as total
            FROM hr_payslip_is_log_line pl
            JOIN hr_payslip p
            ON p.id IN %s
            AND ((pl.corrected_slip_id = p.id AND pl.is_correction IS TRUE) OR (pl.payslip_id = p.id AND pl.is_correction IS NOT TRUE))
            GROUP BY pl.source_tax_canton, pl.is_code, pl.code
        """, (tuple(self.ids),))

        request_rows = self.env.cr.dictfetchall()
        result = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        for row in request_rows:
            canton = row['source_tax_canton']
            is_code = row['is_code']
            code = row['code']
            total = row['total']

            result[canton][is_code].update({
                code: total
            })
            if compute_total:
                result["total"][canton][code] += total
        return result

    @api.depends("l10n_ch_is_code")
    def _compute_l10n_ch_is_model(self):
        for payslip in self:
            if payslip.struct_id.code != "CHMONTHLYELM":
                continue
            if payslip.l10n_ch_is_code:
                st_canton = payslip.l10n_ch_is_code.split("-")[0]
                if st_canton in ["GE", "FR", "TI", "VS", "VD"]:
                    payslip.l10n_ch_is_model = "yearly"
                else:
                    payslip.l10n_ch_is_model = "monthly"
            else:
                payslip.l10n_ch_is_model = False

    def action_refresh_from_work_entries(self):
        swiss_slips = self.filtered(lambda p: p.struct_id.code == "CHMONTHLYELM" and p.state in ['draft', 'verify'])
        if not swiss_slips:
            return super().action_refresh_from_work_entries()
        swiss_slips.mapped('l10n_ch_swiss_wage_ids').unlink()
        swiss_slips.mapped('input_line_ids').unlink()

        swiss_slips._compute_l10n_ch_monthly_snapshot()
        swiss_slips._compute_l10n_ch_swiss_wage_ids()
        swiss_slips._compute_input_line_ids()
        swiss_slips._compute_l10n_ch_location_unit_id()
        swiss_slips._compute_l10n_ch_social_insurance_id()
        swiss_slips._compute_l10n_ch_lpp_insurance_id()
        swiss_slips._compute_l10n_ch_laa_group()
        swiss_slips._compute_laa_solution_number()
        swiss_slips._compute_l10n_ch_additional_accident_insurance_line_ids()
        swiss_slips._compute_l10n_ch_sickness_insurance_line_ids()
        swiss_slips._compute_l10n_ch_pay_13th_month()
        swiss_slips._compute_l10n_ch_avs_status()
        swiss_slips._compute_l10n_ch_is_code()
        swiss_slips._compute_l10n_ch_is_model()
        swiss_slips._compute_l10n_ch_lpp_not_insured()
        swiss_slips._compute_l10n_ch_compensation_fund_id()
        swiss_slips.compute_sheet()

        super(HrPayslip, self - swiss_slips).action_refresh_from_work_entries()

    def action_open_source_tax_corrections(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Source-Tax Correction'),
            'res_model': 'hr.employee.is.line',
            'view_mode': 'form',
            'res_id': self.l10n_ch_is_correction.id,
        }

    def action_absence_swiss_employee_from_payslip(self):
        self.ensure_one()
        return self.employee_id.action_absence_swiss_employee()

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_ch_hr_payroll_elm_transmission', [
                'data/hr_payroll_rule_parameters.xml',
                'data/hr_payroll_input_types.xml',
                'data/hr_salary_rule_category_data.xml',
                'data/hr_salary_rule_data.xml',
                'data/hr_swiss_leave_types.xml',
            ])]

    @api.depends('date_from', 'date_to', 'struct_id')
    def _compute_warning_message(self):
        swiss_slips = self.filtered(lambda p: p.struct_id.code == "CHMONTHLYELM")
        super(HrPayslip, self - swiss_slips)._compute_warning_message()

    def _get_third_party_payment_wage_types(self):
        return {
            'WT_2000',
            'WT_2005',
            'WT_2010',
            'WT_2020',
            'WT_2021',
            'WT_2022',
            'WT_2025',
            'WT_2026',
            'WT_2027',
            'WT_2030',
            'WT_2031',
            'WT_2032',
            'WT_2035',
            "WT_2040",
        }
