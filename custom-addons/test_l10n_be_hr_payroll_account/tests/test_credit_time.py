# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import datetime
from odoo.tools.float_utils import float_compare
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

@tagged('post_install', '-at_install', 'credit_time')
class TestCreditTime(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='be_comp'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env.company.partner_id.tz = "Europe/Brussels"
        cls.env['resource.calendar'].search([]).tz = "Europe/Brussels"
        cls.env.user.tz = "Europe/Brussels"

        cls.company_data['company'].country_id = cls.env.ref('base.be')

        cls.env.company.resource_calendar_id = cls.env['resource.calendar'].create({
            'name': 'Standard 38 hours/week',
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
            'full_time_required_hours': 38,
            'attendance_ids': [
                (5, 0, 0),
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'})
            ],
        })
        cls.classic_38h_calendar = cls.env.company.resource_calendar_id
        cls.env.ref('hr_contract.structure_type_employee_cp200').default_resource_calendar_id = cls.classic_38h_calendar

        cls.employee = cls.env['hr.employee'].create({
            'name': 'My Credit Time Employee',
            'company_id': cls.env.company.id,
            'resource_calendar_id': cls.classic_38h_calendar.id,
        })

        cls.car = cls.env['fleet.vehicle'].create({
            'model_id': cls.env.ref("fleet.model_a3").id,
            'license_plate': '1-JFC-095',
            'acquisition_date': time.strftime('%Y-01-01'),
            'co2': 88,
            'driver_id': cls.env['res.partner'].create({'name': 'Roger'}).id,
            'car_value': 38000,
            'company_id': cls.env.company.id,
        })

        cls.original_contract = cls.env['hr.contract'].create({
            'employee_id': cls.employee.id,
            'company_id': cls.env.company.id,
            'name': 'My Original Contract',
            'state': 'open',
            'date_start': datetime.date(2015, 1, 1),
            'resource_calendar_id': cls.classic_38h_calendar.id,
            'structure_type_id': cls.env.ref('hr_contract.structure_type_employee_cp200').id,
            'wage': 3000,
            'wage_on_signature': 3000,
            'fuel_card': 150,
            'meal_voucher_amount': 7.45,
            'representation_fees': 150,
            'commission_on_target': 1000,
            'ip_wage_rate': 25,
            'ip': True,
            'transport_mode_car': True,
            'car_id': cls.car.id,
            'transport_mode_train': True,
            'train_transport_employee_amount': 30,
            'transport_mode_private_car': True,
            'km_home_work': 30,
            'internet': 38,
            'mobile': 30,
            'has_laptop': True,
        })


    def test_full_time_credit_time(self):
        # Test case:369.23
        # Classic 38h/week until 4th of March 2020 included --> 3 normal days
        # Full Time Credit Time from the 5th of March 2020 to 30th of April 2020
        # Generate work entries for March and check both payslips

        new_calendar = self.env['resource.calendar'].create({
            'name': 'Credit Time Calendar',
            'company_id': self.env.company.id,
            'hours_per_day': 0,
            'full_time_required_hours': 0,
            'attendance_ids': [(5, 0, 0)],
        })

        wizard = self.env['l10n_be.hr.payroll.schedule.change.wizard'].with_context(allowed_company_ids=self.env.company.ids).new({
            'contract_id': self.original_contract.id,
            'absence_work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
            'date_start': datetime.date(2020, 3, 5),
            'date_end': datetime.date(2020, 4, 30),
            'resource_calendar_id': new_calendar.id,
            'part_time': True,
            'previous_contract_creation': True,
        })
        wizard.action_validate()

        contracts = self.env['hr.contract'].search([('employee_id', '=', self.employee.id)])
        new_contract = contracts[1]
        self.assertEqual(len(contracts), 3)
        self.assertEqual(self.original_contract.date_end, datetime.date(2020, 3, 4))
        self.assertEqual(new_contract.date_start, datetime.date(2020, 3, 5))
        self.assertEqual(new_contract._get_contract_wage(), 0)

        new_contract.state = 'open'

        # Generate Work Entries
        date_start = datetime.date(2020, 3, 1)
        date_stop = datetime.date(2020, 3, 31)
        work_entries = (self.original_contract | new_contract).generate_work_entries(date_start, date_stop)
        # The work entries are generated until today, so only take those from march
        work_entries = work_entries.filtered(lambda w: w.date_start.month == 3)

        work_entries_1 = work_entries.filtered(lambda w: w.contract_id == self.original_contract)
        work_entries_2 = work_entries.filtered(lambda w: w.contract_id == new_contract)
        self.assertEqual(len(work_entries_1), 6) # 2, 3, 4 March Morning - Afternoon
        self.assertEqual(len(work_entries_2), 38) # 5-6 (2), 9-13 (5), 16-20 (5), 23-27 (5), 30-31 (2) March Morning - Afternoon

        # Generate Payslip
        payslip_run_id = self.env['hr.payslip.employees'].with_context(
            default_date_start='2020-03-01',
            default_date_end='2020-03-31',
            allowed_company_ids=self.env.company.ids,
        ).create({}).compute_sheet()['res_id']

        payslip_run = self.env['hr.payslip.run'].browse(payslip_run_id)

        self.assertEqual(len(payslip_run.slip_ids), 2)

        payslip_original_contract = payslip_run.slip_ids[0]
        payslip_new_contract = payslip_run.slip_ids[1]

        # Check Payslip 1
        self.assertEqual(payslip_original_contract.contract_id, self.original_contract)
        self.assertEqual(len(payslip_original_contract.worked_days_line_ids), 2) # One attendance line, One out of contract
        attendance_line = payslip_original_contract.worked_days_line_ids[0]
        self.assertAlmostEqual(attendance_line.amount, 415.38, places=2)
        self.assertEqual(attendance_line.number_of_days, 3.0)
        self.assertAlmostEqual(attendance_line.number_of_hours, 22.8, places=2)
        out_of_contract_line = payslip_original_contract.worked_days_line_ids[1]
        self.assertEqual(out_of_contract_line.amount, 0)
        self.assertEqual(out_of_contract_line.number_of_days, 19.0)
        self.assertEqual(float_compare(out_of_contract_line.number_of_hours, 144.4, 2), 0)

        # Check Payslip 2
        self.assertEqual(payslip_new_contract.contract_id, new_contract)
        self.assertEqual(len(payslip_new_contract.worked_days_line_ids), 2) # One credit time, one out of contract
        out_of_contract_line = payslip_new_contract.worked_days_line_ids[0]
        self.assertEqual(out_of_contract_line.amount, 0)
        self.assertEqual(out_of_contract_line.number_of_days, 3)
        self.assertEqual(float_compare(out_of_contract_line.number_of_hours, 22.8, 2), 0)
        credit_time_line = payslip_new_contract.worked_days_line_ids[1]
        self.assertEqual(credit_time_line.amount, 0)
        self.assertEqual(credit_time_line.number_of_days, 19.0)
        self.assertEqual(float_compare(credit_time_line.number_of_hours, 144.4, 2), 0)

        payslip_results = {
            'BASIC': 0.0,
            'ATN.INT': 0.0,
            'ATN.MOB': 0.0,
            'ATN.LAP': 0.0,
            'SALARY': 0.0,
            'ONSS': -0.0,
            'EmpBonus.1': 0.0,
            'ATN.CAR': 0.0,
            'GROSSIP': 0.0,
            'IP.PART': 0.0,
            'GROSS': 0.0,
            'P.P': 0.0,
            'P.P.DED': 0.0,
            'ATN.CAR.2': 0.0,
            'ATN.INT.2': 0.0,
            'ATN.MOB.2': 0.0,
            'ATN.LAP.2': 0.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': 0.0,
            'PUB.TRANS': 0.0,
            'CAR.PRIV': 0.0,
            'REP.FEES': 0.0,
            'IP': 0.0,
            'IP.DED': 0.0,
            'NET': 0.0,
        }
        error = []
        line_values = payslip_new_contract._get_line_values(payslip_results.keys())
        for code, value in payslip_results.items():
            payslip_line_value = line_values[code][payslip_new_contract.id]['total']
            if float_compare(payslip_line_value, value, 2):
                error.append("Computed line %s should have an amount = %s instead of %s" % (code, value, payslip_line_value))
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))

    def test_4_5_time_credit_time(self):
        # Test case:
        # Classic 38h/week until 4th of March 2020 included --> 3 normal days
        # 4/5 Credit Time from the 5th of March 2020 to 30th of April 2020
        # The employee won't work on wednesday
        # Generate work entries for March and check both payslips

        new_calendar = self.env['resource.calendar'].create({
            'name': 'Credit Time Calendar',
            'company_id': self.env.company.id,
            'hours_per_day': 7.6,
            'full_time_required_hours': 38,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'})
            ],
        })

        wizard = self.env['l10n_be.hr.payroll.schedule.change.wizard'].with_context(allowed_company_ids=self.env.company.ids).new({
            'contract_id': self.original_contract.id,
            'absence_work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
            'date_start': datetime.date(2020, 3, 5),
            'date_end': datetime.date(2020, 4, 30),
            'resource_calendar_id': new_calendar.id,
            'part_time': True,
            'previous_contract_creation': True,
        })
        wizard.action_validate()

        contracts = self.env['hr.contract'].search([('employee_id', '=', self.employee.id)])
        new_contract = contracts[1]
        self.assertEqual(len(contracts), 3)
        self.assertEqual(self.original_contract.date_end, datetime.date(2020, 3, 4))
        self.assertEqual(new_contract.date_start, datetime.date(2020, 3, 5))
        self.assertEqual(new_contract._get_contract_wage(), 2400)

        new_contract.state = 'open'

        # Generate Work Entries
        date_start = datetime.date(2020, 3, 1)
        date_stop = datetime.date(2020, 3, 31)
        work_entries = (self.original_contract | new_contract).generate_work_entries(date_start, date_stop)
        # The work entries are generated until today, so only take those from march
        work_entries = work_entries.filtered(lambda w: w.date_start.month == 3)

        work_entries_1 = work_entries.filtered(lambda w: w.contract_id == self.original_contract)
        work_entries_2 = work_entries - work_entries_1
        self.assertEqual(len(work_entries_1), 6) # 2, 3, 4 March Morning - Afternoon
        self.assertEqual(work_entries_1.mapped('work_entry_type_id'), self.env.ref('hr_work_entry.work_entry_type_attendance'))
        self.assertEqual(len(work_entries_2), 38) # 5-6 (2), 9-13 (5), 16-20 (5), 23-27 (5), 30-31 (2) March Morning - Afternoon
        attendance_we = work_entries_2.filtered(lambda w: w.work_entry_type_id == self.env.ref('hr_work_entry.work_entry_type_attendance'))
        credit_time_we = work_entries_2.filtered(lambda w: w.work_entry_type_id == self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time'))
        self.assertEqual(len(credit_time_we), 6) # 11,18,25 Morning - Afternoon
        self.assertEqual(len(attendance_we), 32) # Remaining days

        # Generate Payslip
        payslip_run_id = self.env['hr.payslip.employees'].with_context(
            default_date_start='2020-03-01',
            default_date_end='2020-03-31',
            allowed_company_ids=self.env.company.ids,
        ).create({}).compute_sheet()['res_id']

        payslip_run = self.env['hr.payslip.run'].browse(payslip_run_id)

        self.assertEqual(len(payslip_run.slip_ids), 2)

        payslip_original_contract = payslip_run.slip_ids[0]
        payslip_new_contract = payslip_run.slip_ids[1]

        # Check Payslip 1 - Note: Same as for full time
        self.assertEqual(payslip_original_contract.contract_id, self.original_contract)
        self.assertEqual(len(payslip_original_contract.worked_days_line_ids), 2) # One attendance line, One out of contract
        attendance_line = payslip_original_contract.worked_days_line_ids[0]
        self.assertAlmostEqual(attendance_line.amount, 415.38, places=2)
        self.assertEqual(attendance_line.number_of_days, 3.0)
        self.assertAlmostEqual(attendance_line.number_of_hours, 22.8, places=2)
        out_of_contract_line = payslip_original_contract.worked_days_line_ids[1]
        self.assertEqual(out_of_contract_line.amount, 0.0)
        self.assertEqual(out_of_contract_line.number_of_days, 19.0)
        self.assertEqual(float_compare(out_of_contract_line.number_of_hours, 144.4, 2), 0)

        payslip_results = {
            'BASIC': 415.38,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'ATN.LAP': 6.0,
            'SALARY': 430.38,
            'ONSS': -56.25,
            'EmpBonus.1': 0.0,
            'ATN.CAR': 141.14,
            'GROSSIP': 515.27,
            'IP.PART': -103.85,
            'GROSS': 411.43,
            'P.P': 0.0,
            'P.P.DED': 0.0,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'ATN.LAP.2': -6.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -3.27,
            'PUB.TRANS': 24.0,
            'CAR.PRIV': 7.02,
            'REP.FEES': 18.46,
            'IP': 103.85,
            'IP.DED': -7.79,
            'NET': 397.55
        }
        error = []
        line_values = payslip_original_contract._get_line_values(payslip_results.keys())
        for code, value in payslip_results.items():
            payslip_line_value = line_values[code][payslip_original_contract.id]['total']
            if float_compare(payslip_line_value, value, 2):
                error.append("Computed line %s should have an amount = %s instead of %s" % (code, value, payslip_line_value))
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))

        # Check Payslip 2
        self.assertEqual(payslip_new_contract.contract_id, new_contract)
        self.assertEqual(len(payslip_new_contract.worked_days_line_ids), 3) # Attendance, credit time, out of contract
        attendance_line = payslip_new_contract.worked_days_line_ids[0]
        self.assertAlmostEqual(attendance_line.amount, 2067.69, places=2)
        self.assertEqual(attendance_line.number_of_days, 16.0)
        self.assertEqual(float_compare(attendance_line.number_of_hours, 121.6, 2), 0)
        out_of_contract_line = payslip_new_contract.worked_days_line_ids[1]
        self.assertEqual(out_of_contract_line.amount, 0.0)
        self.assertEqual(out_of_contract_line.number_of_days, 3)
        self.assertEqual(float_compare(out_of_contract_line.number_of_hours, 22.8, 2), 0)
        credit_time_line = payslip_new_contract.worked_days_line_ids[2]
        self.assertEqual(credit_time_line.amount, 0)
        self.assertEqual(credit_time_line.number_of_days, 3)
        self.assertEqual(float_compare(credit_time_line.number_of_hours, 22.8, 2), 0)

        payslip_results = {
            'BASIC': 2067.69,
            'ATN.INT': 0.0,
            'ATN.MOB': 0.0,
            'ATN.LAP': 0.0,
            'SALARY': 2067.69,
            'ONSS': -270.25,
            'EmpBonus.1': 28.9,
            'ATN.CAR': 0,
            'GROSSIP': 1826.35,
            'IP.PART': -516.92,
            'GROSS': 1309.42,
            'P.P': -69.59,
            'P.P.DED': 9.58,
            'ATN.CAR.2': 0.0,
            'ATN.INT.2': 0.0,
            'ATN.MOB.2': 0.0,
            'ATN.LAP.2': 0.0,
            'M.ONSS': -9.3,
            'MEAL_V_EMP': -17.44,
            'PUB.TRANS': 0.0,
            'CAR.PRIV': 29.82,
            'REP.FEES': 98.08,
            'IP': 516.92,
            'IP.DED': -38.77,
            'NET': 1828.73,
        }
        error = []
        line_values = payslip_new_contract._get_line_values(payslip_results.keys())
        for code, value in payslip_results.items():
            payslip_line_value = line_values[code][payslip_new_contract.id]['total']
            if float_compare(payslip_line_value, value, 2):
                error.append("Computed line %s should have an amount = %s instead of %s" % (code, value, payslip_line_value))
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))
