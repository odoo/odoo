# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from datetime import date, datetime

from odoo.tests import tagged, loaded_demo_data
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install', 'eco_vouchers')
class TestEcoVouchers(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='be_comp'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].country_id = cls.env.ref('base.be')

    def test_eco_vouchers(self):
        # The reference year is 2021, so the reference period is 01/06/2020 -> 31/05/2021 (12 months)
        # Employee is working on:
        # - Full time from 01/06/2020 to 31/10/2020 -> 5 months
        # - Part time from 01/11/2020 to 31/12/2021 -> 7 months
        # Employees is on unpaid time off from the 01/04/2021 to 21/04/2021 (9 working days over 2.5 weeks)

        # Expected result = 250*5/12 + 200*(7-1)/12 = 104.67 + 100 = 204.17
        employee = self.env['hr.employee'].create({'name': 'Test Employee'})

        full_time_calendar = self.env['resource.calendar'].create([{
            'name': "Test Calendar : 38 Hours/Week",
            'company_id': self.env.company.id,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 38.0,
            'full_time_required_hours': 38.0,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 12.0, 13.0, "lunch"),
                ("0", 13.0, 16.6, "afternoon"),
                ("1", 8.0, 12.0, "morning"),
                ("1", 12.0, 13.0, "lunch"),
                ("1", 13.0, 16.6, "afternoon"),
                ("2", 8.0, 12.0, "morning"),
                ("2", 12.0, 13.0, "lunch"),
                ("2", 13.0, 16.6, "afternoon"),
                ("3", 8.0, 12.0, "morning"),
                ("3", 12.0, 13.0, "lunch"),
                ("3", 13.0, 16.6, "afternoon"),
                ("4", 8.0, 12.0, "morning"),
                ("4", 12.0, 13.0, "lunch"),
                ("4", 13.0, 16.6, "afternoon"),
            ]],
        }])

        part_time_calendar_3_5 = self.env['resource.calendar'].create([{
            'name': "Test Calendar: 3/5 Tuesday/Wednesday Off",
            'company_id': self.env.company.id,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 22.8,
            'full_time_required_hours': 38.0,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 12.0, 13.0, "lunch"),
                ("0", 13.0, 16.6, "afternoon"),
                ("3", 8.0, 12.0, "morning"),
                ("3", 12.0, 13.0, "lunch"),
                ("3", 13.0, 16.6, "afternoon"),
                ("4", 8.0, 12.0, "morning"),
                ("4", 12.0, 13.0, "lunch"),
                ("4", 13.0, 16.6, "afternoon"),
            ]],
        }])


        dummy = self.env['hr.contract'].create({
            'name': 'Full Time Contract',
            'date_start': date(2020, 6, 1),
            'date_end': date(2020, 10, 31),
            'employee_id': employee.id,
            'resource_calendar_id': full_time_calendar.id,
            'state': 'open',
            'wage': 1000,
        })
        contract_2 = self.env['hr.contract'].create({
            'name': 'Part Time Contract',
            'date_start': date(2020, 11, 1),
            'date_end': date(2021, 12, 31),
            'employee_id': employee.id,
            'resource_calendar_id': part_time_calendar_3_5.id,
            'standard_calendar_id': full_time_calendar.id,
            'time_credit': True,
            'work_time_rate': 0.6,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
            'state': 'open',
            'wage': 1000,
        })

        unpaid_time_off_type = self.env['hr.leave.type'].create({
            'name': 'Unpaid',
            'requires_allocation': 'no',
            'leave_validation_type': 'both',
            'request_unit': 'hour',
            'unpaid': True,
            'company_id': self.env.company.id,
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id,
        })

        unpaid_leave_2019 = self.env['hr.leave'].create({
            'name': 'Unpaid Time Off 2021',
            'holiday_status_id': unpaid_time_off_type.id,
            'request_date_from': date(2021, 4, 1),
            'request_date_to': date(2021, 4, 21),
            'employee_id': employee.id,
        })
        unpaid_leave_2019.action_approve()
        unpaid_leave_2019.action_validate()

        april_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip Apr 2021',
            'contract_id': contract_2.id,
            'date_from': datetime(2021, 4, 1),
            'date_to': datetime(2021, 4, 30),
            'employee_id': employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.env.company.id,
        })
        april_payslip.action_refresh_from_work_entries()
        april_payslip.action_payslip_done()

        wizard = self.env['l10n.be.eco.vouchers.wizard'].create({
            'reference_year': '2021',
        })
        employee_line = wizard.line_ids.filtered(lambda l: l.employee_id == employee)
        expected_result = 211.1 if loaded_demo_data(self.env) else 213.29
        self.assertAlmostEqual(employee_line.amount, expected_result)
