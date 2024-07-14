# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools.float_utils import float_compare


@tagged('post_install', '-at_install', 'payslips_validation')
class TestPayslipValidation(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='be_comp'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.date_from = datetime.date(2020, 9, 1)
        cls.date_to = datetime.date(2020, 9, 30)

        cls.company_data['company'].country_id = cls.env.ref('base.be')

        cls.env.user.tz = 'Europe/Brussels'

        cls.resource_calendar_38_hours_per_week = cls.env['resource.calendar'].create([{
            'name': "Test Calendar : 38 Hours/Week",
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
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
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

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

        cls.resource_calendar_38_hours_per_week_odoo = cls.env['resource.calendar'].create([{
            'name': "Test Calendar : 38 Hours/Week",
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
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
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 9.0, 12.8, "morning"),
                ("0", 12.8, 13.8, "lunch"),
                ("0", 13.8, 17.6, "afternoon"),
                ("1", 9.0, 12.8, "morning"),
                ("1", 12.8, 13.8, "lunch"),
                ("1", 13.8, 17.6, "afternoon"),
                ("2", 9.0, 12.8, "morning"),
                ("2", 12.8, 13.8, "lunch"),
                ("2", 13.8, 17.6, "afternoon"),
                ("3", 9.0, 12.8, "morning"),
                ("3", 12.8, 13.8, "lunch"),
                ("3", 13.8, 17.6, "afternoon"),
                ("4", 9.0, 12.8, "morning"),
                ("4", 12.8, 13.8, "lunch"),
                ("4", 13.8, 17.6, "afternoon"),

            ]],
        }])

        cls.resource_calendar_4_5_wednesday_off = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: 4/5 Wednesday Off",
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
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
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 12.0, 13.0, "lunch"),
                ("0", 13.0, 16.6, "afternoon"),
                ("1", 8.0, 12.0, "morning"),
                ("1", 12.0, 13.0, "lunch"),
                ("1", 13.0, 16.6, "afternoon"),
                ("3", 8.0, 12.0, "morning"),
                ("3", 12.0, 13.0, "lunch"),
                ("3", 13.0, 16.6, "afternoon"),
                ("4", 8.0, 12.0, "morning"),
                ("4", 12.0, 13.0, "lunch"),
                ("4", 13.0, 16.6, "afternoon"),

            ]],
        }])

        cls.resource_calendar_4_5_thurday_off = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: 4/5 Thursday Off",
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
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
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

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
                ("4", 8.0, 12.0, "morning"),
                ("4", 12.0, 13.0, "lunch"),
                ("4", 13.0, 16.6, "afternoon"),

            ]],
        }])

        cls.resource_calendar_4_5_friday_off = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: 4/5 Friday Off",
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
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
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

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
            ]],
        }])

        cls.resource_calendar_half_time = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: Half Time",
            'company_id': cls.env.company.id,
            'hours_per_day': 6.33,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 19.0,
            'full_time_required_hours': 38.0,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 12.0, 13.0, "lunch"),
                ("0", 13.0, 16.6, "afternoon"),
                ("1", 8.0, 12.0, "morning"),
                ("1", 12.0, 13.0, "lunch"),
                ("1", 13.0, 16.6, "afternoon"),
                ("2", 8.0, 11.8, "morning"),
            ]],
        }])

        cls.resource_calendar_1_5_monday_on = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: 1/5 Monday On",
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 7.6,
            'full_time_required_hours': 38.0,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id
            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 12.0, 13.0, "lunch"),
                ("0", 13.0, 16.6, "afternoon"),
            ]],
        }])

        cls.resource_calendar_0_hours_per_week = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: 0 Hours per week",
            'company_id': cls.env.company.id,
            'hours_per_day': 0,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 0,
            'full_time_required_hours': 38,
            'attendance_ids': [(5, 0, 0)],
        }])

        cls.resource_calendar_19_part_time_sick = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: 19 Hours/Week Part Time Sick PM",
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
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
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id
            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 9.0, 12.8, "morning"),
                ("1", 9.0, 12.8, "morning"),
                ("2", 9.0, 12.8, "morning"),
                ("3", 9.0, 12.8, "morning"),
                ("4", 9.0, 12.8, "morning"),
            ]] + [(0, 0, {
                'name': "Sick Time Off",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
                'work_entry_type_id': cls.env.ref('l10n_be_hr_payroll.work_entry_type_partial_incapacity').id
            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 13.8, 17.6, "afternoon"),
                ("1", 13.8, 17.6, "afternoon"),
                ("2", 13.8, 17.6, "afternoon"),
                ("3", 13.8, 17.6, "afternoon"),
                ("4", 13.8, 17.6, "afternoon"),
            ]],
        }])

        cls.resource_calendar_9_10_monday_off = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: 9/10 Hours/Week 1 Monday over 2 Off",
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': True,
            'hours_per_week': 34.2,
            'work_time_rate': 90,
            'full_time_required_hours': 38.0,
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {
                    'name': 'First week',
                    'dayofweek': '0',
                    'sequence': '0',
                    'hour_from': 0,
                    'day_period': 'morning',
                    'week_type': '0',
                    'hour_to': 0,
                    'display_type': 'line_section'
                }), (0, 0, {
                    'name': 'Second week',
                    'dayofweek': '0',
                    'sequence': '25',
                    'hour_from': 0,
                    'day_period': 'morning',
                    'week_type': '1',
                    'hour_to': 0,
                    'display_type': 'line_section'
                })] + [(0, 0, {
                    'name': "Attendance",
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                    'sequence': sequence,
                    'week_type': week_type,
                    'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id
                }) for dayofweek, hour_from, hour_to, day_period, week_type, sequence in [
                    ("0", 8.0, 12.0, "morning", "0", "1"),
                    ("0", 12.0, 13.0, "lunch", "0", "2"),
                    ("0", 13.0, 16.6, "afternoon", "0", "3"),
                    ("1", 8.0, 12.0, "morning", "0", "4"),
                    ("1", 12.0, 13.0, "lunch", "0", "5"),
                    ("1", 13.0, 16.6, "afternoon", "0", "6"),
                    ("2", 8.0, 12.0, "morning", "0", "7"),
                    ("2", 12.0, 13.0, "lunch", "0", "8"),
                    ("2", 13.0, 16.6, "afternoon", "0", "9"),
                    ("3", 8.0, 12.0, "morning", "0", "10"),
                    ("3", 12.0, 13.0, "lunch", "0", "11"),
                    ("3", 13.0, 16.6, "afternoon", "0", "12"),
                    ("4", 8.0, 12.0, "morning", "0", "13"),
                    ("4", 12.0, 13.0, "lunch", "0", "14"),
                    ("4", 13.0, 16.6, "afternoon", "0", "15"),
                    ("1", 8.0, 12.0, "morning", "1", "26"),
                    ("1", 12.0, 13.0, "lunch", "1", "27"),
                    ("1", 13.0, 16.6, "afternoon", "1", "28"),
                    ("2", 8.0, 12.0, "morning", "1", "29"),
                    ("2", 12.0, 13.0, "lunch", "1", "30"),
                    ("2", 13.0, 16.6, "afternoon", "1", "31"),
                    ("3", 8.0, 12.0, "morning", "1", "32"),
                    ("3", 12.0, 13.0, "lunch", "1", "33"),
                    ("3", 13.0, 16.6, "afternoon", "1", "34"),
                    ("4", 8.0, 12.0, "morning", "1", "35"),
                    ("4", 12.0, 13.0, "lunch", "1", "36"),
                    ("4", 13.0, 16.6, "afternoon", "1", "37")]],
        }])

        cls.resource_calendar_9_10_strange = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: 9/10 Hours/Week 1 hour less every day on second week + 1 wed pm off",
            'company_id': cls.env.company.id,
            'hours_per_day': 7.6,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': True,
            'hours_per_week': 34.2,
            'work_time_rate': 90,
            'full_time_required_hours': 38.0,
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {
                    'name': 'First week',
                    'dayofweek': '0',
                    'sequence': '0',
                    'hour_from': 0,
                    'day_period': 'morning',
                    'week_type': '0',
                    'hour_to': 0,
                    'display_type': 'line_section'
                }), (0, 0, {
                    'name': 'Second week',
                    'dayofweek': '0',
                    'sequence': '25',
                    'hour_from': 0,
                    'day_period': 'morning',
                    'week_type': '1',
                    'hour_to': 0,
                    'display_type': 'line_section'
                })] + [(0, 0, {
                    'name': "Attendance",
                    'dayofweek': dayofweek,
                    'hour_from': hour_from,
                    'hour_to': hour_to,
                    'day_period': day_period,
                    'sequence': sequence,
                    'week_type': week_type,
                    'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id
                }) for dayofweek, hour_from, hour_to, day_period, week_type, sequence in [
                    ("0", 9.0, 12.8, "morning", "0", "1"),
                    ("0", 12.8, 13.8, "lunch", "0", "2"),
                    ("0", 13.8, 17.6, "afternoon", "0", "3"),
                    ("1", 9.0, 12.8, "morning", "0", "4"),
                    ("1", 12.8, 13.8, "lunch", "0", "5"),
                    ("1", 13.8, 17.6, "afternoon", "0", "6"),
                    ("2", 9.0, 12.8, "morning", "0", "7"),
                    ("2", 12.8, 13.8, "lunch", "0", "8"),
                    ("2", 13.8, 17.6, "afternoon", "0", "9"),
                    ("3", 9.0, 12.8, "morning", "0", "10"),
                    ("3", 12.8, 13.8, "lunch", "0", "11"),
                    ("3", 13.8, 17.6, "afternoon", "0", "12"),
                    ("4", 9.0, 12.8, "morning", "0", "13"),
                    ("4", 12.8, 13.8, "lunch", "0", "14"),
                    ("4", 13.8, 17.6, "afternoon", "0", "15"),
                    ("0", 9.0, 12.8, "morning", "1", "26"),
                    ("0", 12.8, 13.8, "lunch", "1", "27"),
                    ("0", 13.8, 16.6, "afternoon", "1", "28"),
                    ("1", 9.0, 12.8, "morning", "1", "29"),
                    ("1", 12.8, 13.8, "lunch", "1", "30"),
                    ("1", 13.8, 16.6, "afternoon", "1", "31"),
                    ("2", 9.0, 12.8, "morning", "1", "32"),
                    ("3", 9.0, 12.8, "morning", "1", "33"),
                    ("3", 12.8, 13.8, "lunch", "1", "34"),
                    ("3", 13.8, 16.6, "afternoon", "1", "35"),
                    ("4", 9.0, 12.8, "morning", "1", "36"),
                    ("4", 12.8, 13.8, "lunch", "1", "37"),
                    ("4", 13.8, 16.6, "afternoon", "1", "38")]],
        }])

        cls.resource_calendar_4_5_monday_off_equal_morning_afternoon = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: 4/5 Monday/Friday Afternoon Off (equal morning/afternoon)",
            'company_id': cls.env.company.id,
            'hours_per_day': 6.08,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 30.4,
            'full_time_required_hours': 38.0,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
                'work_entry_type_id': cls.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 9.0, 12.8, "morning"),
                ("1", 9.0, 12.8, "morning"),
                ("1", 12.8, 13.8, "lunch"),
                ("1", 13.8, 17.6, "afternoon"),
                ("2", 9.0, 12.8, "morning"),
                ("2", 12.8, 13.8, "lunch"),
                ("2", 13.8, 17.6, "afternoon"),
                ("3", 9.0, 12.8, "morning"),
                ("3", 12.8, 13.8, "lunch"),
                ("3", 13.8, 17.6, "afternoon"),
                ("4", 9.0, 12.8, "morning"),
            ]],
        }])

        cls.employee = cls.env['hr.employee'].create([{
            'name': "Test Employee",
            'resource_calendar_id': cls.resource_calendar_38_hours_per_week.id,
            'company_id': cls.env.company.id,
            'km_home_work': 75,
        }])

        cls.brand = cls.env['fleet.vehicle.model.brand'].create([{
            'name': "Test Brand"
        }])

        cls.model = cls.env['fleet.vehicle.model'].create([{
            'name': "Test Model",
            'brand_id': cls.brand.id
        }])

        cls.car = cls.env['fleet.vehicle'].create([{
            'name': "Test Car",
            'license_plate': "TEST",
            'driver_id': cls.employee.work_contact_id.id,
            'company_id': cls.env.company.id,
            'model_id': cls.model.id,
            'first_contract_date': datetime.date(2020, 10, 8),
            'co2': 88.0,
            'car_value': 38000.0,
            'fuel_type': "diesel",
            'acquisition_date': datetime.date(2020, 1, 1)
        }])

        cls.vehicle_contract = cls.env['fleet.vehicle.log.contract'].create({
            'name': "Test Contract",
            'vehicle_id': cls.car.id,
            'company_id': cls.env.company.id,
            'start_date': datetime.date(2020, 10, 8),
            'expiration_date': datetime.date(2021, 10, 8),
            'state': "open",
            'cost_generated': 0.0,
            'cost_frequency': "monthly",
            'recurring_cost_amount_depreciated': 450.0
        })

        cls.contract = cls.env['hr.contract'].create([{
            'name': "Contract For Payslip Test",
            'employee_id': cls.employee.id,
            'resource_calendar_id': cls.resource_calendar_38_hours_per_week.id,
            'company_id': cls.env.company.id,
            'date_generated_from': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'car_id': cls.car.id,
            'structure_type_id': cls.env.ref('hr_contract.structure_type_employee_cp200').id,
            'date_start': datetime.date(2018, 12, 31),
            'wage': 2650.0,
            'wage_on_signature': 2650.0,
            'state': "open",
            'transport_mode_car': True,
            'fuel_card': 150.0,
            'internet': 38.0,
            'representation_fees': 150.0,
            'mobile': 30.0,
            'meal_voucher_amount': 7.45,
            'eco_checks': 250.0,
            'ip_wage_rate': 25.0,
            'ip': True,
        }])

        cls.sick_time_off_type = cls.env['hr.leave.type'].create({
            'name': 'Sick Time Off',
            'requires_allocation': 'no',
            'work_entry_type_id': cls.env.ref('hr_work_entry_contract.work_entry_type_sick_leave').id,
        })

        cls.long_term_sick_time_off_type = cls.env['hr.leave.type'].create({
            'name': 'Sick Time Off',
            'requires_allocation': 'no',
            'work_entry_type_id': cls.env.ref('l10n_be_hr_payroll.work_entry_type_long_sick').id,
        })

        cls.paid_time_off_type_2019 = cls.env['hr.leave.type'].create({
            'name': "Paid Time Off 2019",
            'requires_allocation': 'yes',
            'employee_requests': 'no',
            'allocation_validation_type': 'officer',
            'leave_validation_type': 'both',
            'company_id': cls.env.company.id,
            'work_entry_type_id': cls.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id,
        })

        cls.paid_time_off_type_2020 = cls.env['hr.leave.type'].create({
            'name': "Paid Time Off 2020",
            'requires_allocation': 'yes',
            'employee_requests': 'no',
            'allocation_validation_type': 'officer',
            'leave_validation_type': 'both',
            'company_id': cls.env.company.id,
            'work_entry_type_id': cls.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id,
        })

        cls.unpaid_time_off_type = cls.env['hr.leave.type'].create({
            'name': 'Unpaid',
            'requires_allocation': 'no',
            'leave_validation_type': 'both',
            'request_unit': 'hour',
            'unpaid': True,
            'company_id': cls.env.company.id,
            'work_entry_type_id': cls.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id,
        })

        cls.european_time_off_type = cls.env['hr.leave.type'].create({
            'name': 'European Time Off',
            'requires_allocation': 'no',
            'leave_validation_type': 'both',
            'request_unit': 'half_day',
            'company_id': cls.env.company.id,
            'work_entry_type_id': cls.env.ref('l10n_be_hr_payroll.work_entry_type_european').id,
        })

        cls.economic_unemployment_time_off_type = cls.env['hr.leave.type'].create({
            'name': 'Economic Unemployment',
            'requires_allocation': 'no',
            'leave_validation_type': 'both',
            'request_unit': 'half_day',
            'company_id': cls.env.company.id,
            'work_entry_type_id': cls.env.ref('l10n_be_hr_payroll.work_entry_type_economic_unemployment').id,
        })

        cls.leave_type_small_unemployment = cls.env['hr.leave.type'].create({
            'name': 'Small Unemployment',
            'request_unit': 'hour',
            'requires_allocation': 'no',
            'company_id': cls.env.company.id,
            'work_entry_type_id': cls.env.ref('l10n_be_hr_payroll.work_entry_type_small_unemployment').id,
        })

        cls.extra_legal_time_off_type = cls.env['hr.leave.type'].create({
            'name': 'Extra-Legal Time Off',
            'requires_allocation': 'no',
            'work_entry_type_id': cls.env.ref('l10n_be_hr_payroll.work_entry_type_extra_legal').id,
        })

    @classmethod
    def _generate_payslip(cls, date_from, date_to, struct_id=False, contract_id=False):
        work_entries = cls.contract.generate_work_entries(date_from, date_to)
        payslip = cls.env['hr.payslip'].create([{
            'name': "Test Payslip",
            'employee_id': cls.employee.id,
            'contract_id': contract_id or cls.contract.id,
            'company_id': cls.env.company.id,
            'vehicle_id': cls.car.id,
            'struct_id': struct_id or cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'date_from': date_from,
            'date_to': date_to,
        }])
        work_entries.action_validate()
        payslip.compute_sheet()
        return payslip

    @classmethod
    def _generate_departure_data(cls):
        cls.contract_2019 = cls.contract
        cls.contract_2019.write({
            'wage': 3000,
            'wage_on_signature': 3000,
            'commission_on_target': 1500,
            'state': 'close',
            'date_start': datetime.date(2019, 1, 1),
            'date_end': datetime.date(2019, 12, 31),
        })

        cls.contract_2020 = cls.env['hr.contract'].create({
            'name': "Contract For Payslip Test",
            'employee_id': cls.employee.id,
            'resource_calendar_id': cls.resource_calendar_38_hours_per_week.id,
            'company_id': cls.env.company.id,
            'date_generated_from': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'car_id': cls.car.id,
            'structure_type_id': cls.env.ref('hr_contract.structure_type_employee_cp200').id,
            'date_start': datetime.date(2020, 1, 1),
            'wage': 3200,
            'wage_on_signature': 3200,
            'commission_on_target': 1500,
            'state': "open",
            'transport_mode_car': True,
            'fuel_card': 150.0,
            'internet': 38.0,
            'representation_fees': 150.0,
            'mobile': 30.0,
            'meal_voucher_amount': 7.45,
            'eco_checks': 250.0,
            'ip_wage_rate': 25.0,
            'ip': True,
        })

        cls.allocation_2019 = cls.env['hr.leave.allocation'].create({
            'name': 'Paid Time Off - 2019',
            'holiday_status_id': cls.paid_time_off_type_2019.id,
            'number_of_days': 20,
            'employee_id': cls.employee.id,
            'date_from': datetime.date(2019, 1, 1),
            'date_to': datetime.date(2025, 12, 31),
        })

        cls.allocation_2020 = cls.env['hr.leave.allocation'].create({
            'name': 'Paid Time Off - 2020',
            'holiday_status_id': cls.paid_time_off_type_2020.id,
            'number_of_days': 20,
            'employee_id': cls.employee.id,
            'date_from': datetime.date(2020, 1, 1),
            'date_to': datetime.date(2025, 12, 31),
        })

        (cls.allocation_2019 + cls.allocation_2020).action_validate()

        cls.unpaid_leave_2019 = cls.env['hr.leave'].create({
            'name': 'Unpaid Time Off 2019',
            'holiday_status_id': cls.unpaid_time_off_type.id,
            'date_from': datetime.datetime(2019, 3, 4, 1, 0, 0),
            'date_to': datetime.datetime(2019, 3, 15, 23, 0, 0),
            'request_date_from': datetime.datetime(2019, 3, 4, 1, 0, 0),
            'request_date_to': datetime.datetime(2019, 3, 15, 23, 0, 0),
            'number_of_days': 10,
            'employee_id': cls.employee.id,
        })

        cls.legal_leave_2019 = cls.env['hr.leave'].create({
            'name': 'Legal Time Off 2019',
            'holiday_status_id': cls.paid_time_off_type_2019.id,
            'date_from': datetime.datetime(2019, 5, 6, 1, 0, 0),
            'date_to': datetime.datetime(2019, 5, 31, 23, 0, 0),
            'request_date_from': datetime.datetime(2019, 5, 6, 1, 0, 0),
            'request_date_to': datetime.datetime(2019, 5, 31, 23, 0, 0),
            'number_of_days': 20,
            'employee_id': cls.employee.id,
        })

        cls.legal_leave_2020 = cls.env['hr.leave'].create({
            'name': 'Legal Time Off 2020',
            'holiday_status_id': cls.paid_time_off_type_2020.id,
            'date_from': datetime.datetime(2020, 1, 13, 1, 0, 0),
            'date_to': datetime.datetime(2020, 1, 17, 23, 0, 0),
            'request_date_from': datetime.datetime(2020, 1, 13, 1, 0, 0),
            'request_date_to': datetime.datetime(2020, 1, 17, 23, 0, 0),
            'number_of_days': 5,
            'employee_id': cls.employee.id,
        })

        (cls.unpaid_leave_2019 + cls.legal_leave_2019 + cls.legal_leave_2020).action_validate()

        cls.contract_2019.generate_work_entries(datetime.date(2019, 1, 1), datetime.date(2019, 12, 31))
        cls.contract_2020.generate_work_entries(datetime.date(2020, 1, 1), datetime.date(2020, 3, 31))

        cls.batch = cls.env['hr.payslip.run'].create({
            'name': 'History Batch',
            'date_start': datetime.date(2019, 1, 1),
            'date_end': datetime.date(2020, 3, 31),
            'company_id': cls.env.company.id,
        })

        # Janvier 2019: Salary + Commissions
        # Février 2019: Salary
        # Mars 2019: Salary (10 unpaid days)
        # Avril 2019: Salary + Warrants (2 payslips)
        # Mai 2019: Salary (20 legal days)
        # Juin 2019: Salary + Double Holiday Pay (2 payslips)
        # Juillet 2019: Salary + Commissions
        # Aout 2019: Salary
        # Septembre 2019: Salary
        # Octobre 2019: Salary + Commissions
        # Novembre 2019: Salary
        # Décembre 2019: Salary + 13eme mois (2 payslips)
        # Janvier 2020: Salary + Commissions (5 legal days)
        # Février 2020: Salary
        # Mars 2020: Salary
        # Avril: Fired without notice period on the 15th of April (4 payslips):
        # - Termination Fees
        # - April Payslip
        # - Holiday Pay N
        # - Holiday Pay N-1
        cls.journal = cls.env['account.journal'].search([('type', '=', 'general')], limit=1)

        # Janvier 2019: Salary + Commissions
        cls.january_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Jan 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 1, 1),
            'date_to': datetime.datetime(2019, 1, 31),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': cls.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })]
        })

        # Février 2019: Salary
        cls.february_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Feb 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 2, 1),
            'date_to': datetime.datetime(2019, 2, 28),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        # Mars 2019: Salary (10 unpaid days)
        cls.march_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Mar 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 3, 1),
            'date_to': datetime.datetime(2019, 3, 31),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        # Avril 2019: Salary + Warrants (2 payslips)
        cls.april_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Apr 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 4, 1),
            'date_to': datetime.datetime(2019, 4, 30),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        cls.warrant_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Warrant 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 4, 1),
            'date_to': datetime.datetime(2019, 4, 30),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_structure_warrant').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        # Mai 2019: Salary (20 legal days)
        cls.may_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip May 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 5, 1),
            'date_to': datetime.datetime(2019, 5, 31),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        # Juin 2019: Salary + Double Holiday Pay (2 payslips)
        cls.june_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Jun 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 6, 1),
            'date_to': datetime.datetime(2019, 6, 30),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        cls.double_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Double 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 6, 1),
            'date_to': datetime.datetime(2019, 6, 30),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        # Juillet 2019: Salary + Commissions
        cls.july_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Jul 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 7, 1),
            'date_to': datetime.datetime(2019, 7, 31),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': cls.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })]
        })

        # Aout 2019: Salary
        cls.august_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Aug 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 8, 1),
            'date_to': datetime.datetime(2019, 8, 31),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        # Septembre 2019: Salary
        cls.september_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Sep 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 9, 1),
            'date_to': datetime.datetime(2019, 9, 30),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        # Octobre 2019: Salary + Commissions
        cls.october_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Oct 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 10, 1),
            'date_to': datetime.datetime(2019, 10, 31),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': cls.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })]
        })

        # Novembre 2019: Salary
        cls.november_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Nov 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 11, 1),
            'date_to': datetime.datetime(2019, 11, 30),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        # Décembre 2019: Salary + 13eme mois (2 payslips)
        cls.december_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Dec 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 12, 1),
            'date_to': datetime.datetime(2019, 12, 31),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        cls.thirteen_2019 = cls.env['hr.payslip'].create({
            'name': 'Payslip Thirteen Month 2019',
            'contract_id': cls.contract_2019.id,
            'date_from': datetime.datetime(2019, 12, 1),
            'date_to': datetime.datetime(2019, 12, 31),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_thirteen_month').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        # Janvier 2020: Salary + Commissions (5 legal days)
        cls.january_2020 = cls.env['hr.payslip'].create({
            'name': 'Payslip Jan 2020',
            'contract_id': cls.contract_2020.id,
            'date_from': datetime.datetime(2020, 1, 1),
            'date_to': datetime.datetime(2020, 1, 31),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': cls.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 2000,
            })]
        })

        # Février 2020: Salary
        cls.february_2020 = cls.env['hr.payslip'].create({
            'name': 'Payslip Feb 2020',
            'contract_id': cls.contract_2020.id,
            'date_from': datetime.datetime(2020, 2, 1),
            'date_to': datetime.datetime(2020, 2, 28),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        # Mars 2020: Salary
        cls.march_2020 = cls.env['hr.payslip'].create({
            'name': 'Payslip Mar 2020',
            'contract_id': cls.contract_2020.id,
            'date_from': datetime.datetime(2020, 3, 1),
            'date_to': datetime.datetime(2020, 3, 31),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        # Avril: Fired without notice period on the 15th of April (4 payslips):
        # - Termination Fees
        cls.departure_notice = cls.env['hr.payslip.employee.depature.notice'].create({
            'employee_id': cls.employee.id,
            'leaving_type_id': cls.env.ref('hr.departure_fired').id,
            'start_notice_period': datetime.date(2020, 4, 15),
            'end_notice_period': datetime.date(2020, 4, 15),
            'first_contract': datetime.date(2019, 1, 1),
            'notice_respect': 'without',
            'departure_description': 'foo',
        })

        # - April Payslip
        cls.april_2020 = cls.env['hr.payslip'].create({
            'name': 'Payslip Mar 2020',
            'contract_id': cls.contract_2020.id,
            'date_from': datetime.datetime(2020, 3, 1),
            'date_to': datetime.datetime(2020, 3, 31),
            'employee_id': cls.employee.id,
            'struct_id': cls.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': cls.env.company.id,
            'journal_id': cls.journal.id,
            'payslip_run_id': cls.batch.id,
        })

        all_payslips = cls.january_2019 + cls.february_2019 + cls.march_2019 + cls.april_2019 + \
                       cls.warrant_2019 + cls.may_2019 + cls.june_2019 + cls.double_2019 + \
                       cls.july_2019 + cls.august_2019 + cls.september_2019 + cls.october_2019 + \
                       cls.november_2019 + cls.december_2019 + cls.thirteen_2019 + \
                       cls.january_2020 + cls.february_2020 + cls.march_2020 + cls.april_2020
        all_payslips.action_refresh_from_work_entries()
        all_payslips.action_payslip_done()

        termination_payslip_id = cls.departure_notice.compute_termination_fee()['res_id']
        cls.termination_fees = cls.env['hr.payslip'].browse(termination_payslip_id)
        cls.termination_fees.compute_sheet()
        cls.termination_fees.action_payslip_done()
        cls.termination_fees.payslip_run_id = cls.batch

    def _validate_payslip(self, payslip, results):
        error = []
        line_values = payslip._get_line_values(set(results.keys()) | set(payslip.line_ids.mapped('code')))
        for code, value in results.items():
            payslip_line_value = line_values[code][payslip.id]['total']
            if float_compare(payslip_line_value, value, 2):
                error.append("Code: %s - Expected: %s - Reality: %s" % (code, value, payslip_line_value))
        for line in payslip.line_ids:
            if line.code not in results:
                error.append("Missing Line: '%s' - %s," % (line.code, line_values[line.code][payslip.id]['total']))
        if error:
            error.append("Payslip Actual Values: ")
            error.append("        {")
            for line in payslip.line_ids:
                error.append("            '%s': %s," % (line.code, line_values[line.code][payslip.id]['total']))
            error.append("        }")
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))

    def _validate_move_lines(self, lines, results):
        error = []
        for code, move_type, amount in results:
            if not any(l.account_id.code == code and not float_compare(l[move_type], amount, 2) for l in lines):
                error.append("Couldn't find %s move line on account %s with amount %s" % (move_type, code, amount))
        if error:
            for line in lines:
                for move_type in ['credit', 'debit']:
                    if line[move_type]:
                        error.append('%s - %s - %s' % (line.account_id.code, move_type, line[move_type]))
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))

    def test_low_salary(self):
        self.contract.wage_on_signature = 1800
        self.contract.ip = False

        payslip = self._generate_payslip(self.date_from, self.date_to)

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 28)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 1800.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 22.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 167.2, places=2)

        payslip_results = {
            'BASIC': 1800.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 1809.0,
            'ONSS': -236.44,
            'EmpBonus.1': 176.14,
            'ONSSTOTAL': 60.3,
            'ATN.CAR': 141.14,
            'GROSS': 1889.85,
            'P.P': -278.78,
            'P.P.DED': 58.37,
            'PPTOTAL': 220.41,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -23.98,
            'REP.FEES': 150.0,
            'NET': 1645.31,
            'REMUNERATION': 1800.0,
            'ONSSEMPLOYERBASIC': 452.61,
            'ONSSEMPLOYERFFE': 2.35,
            'ONSSEMPLOYERMFFE': 1.81,
            'ONSSEMPLOYERCPAE': 4.16,
            'ONSSEMPLOYERRESTREINT': 30.57,
            'ONSSEMPLOYERUNEMP': 1.81,
            'ONSSEMPLOYER': 493.31,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_end_of_contract(self):
        self.contract.date_end = datetime.date(2020, 9, 21)
        self.contract.ip = False

        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 14, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 14, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_phc').id
        }])

        payslip = self._generate_payslip(self.date_from, self.date_to)

        self.assertEqual(len(payslip.worked_days_line_ids), 3)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 27)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('PHC1'), 122.31, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 1671.54, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('OUT'), 0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('PHC1'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 14.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('OUT'), 7.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('PHC1'), 7.6, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 106.4, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('OUT'), 53.2, places=2)

        payslip_results = {
            'BASIC': 1793.85,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 1802.85,
            'ONSS': -235.63,
            'EmpBonus.1': 0,
            'ONSSTOTAL': 235.63,
            'ATN.CAR': 141.14,
            'GROSS': 1708.36,
            'P.P': -201.74,
            'PPTOTAL': 201.74,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0,
            'MEAL_V_EMP': -15.26,
            'REP.FEES': 101.54,
            'NET': 1442.76,
            'REMUNERATION': 1793.85,
            'ONSSEMPLOYERBASIC': 451.07,
            'ONSSEMPLOYERFFE': 2.34,
            'ONSSEMPLOYERMFFE': 1.8,
            'ONSSEMPLOYERCPAE': 4.15,
            'ONSSEMPLOYERRESTREINT': 30.47,
            'ONSSEMPLOYERUNEMP': 1.8,
            'ONSSEMPLOYER': 491.64,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_out_of_contract_credit_time(self):
        # The employee is on 4/5 credit time (wednesday off) from the 16 of September 2020
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
            'wage': 2120.0,
            'wage_on_signature': 2120.0,
            'date_start': datetime.date(2020, 9, 16),
            'date_end': datetime.date(2020, 12, 31),
        })
        payslip = self._generate_payslip(self.date_from, self.date_to)

        self.assertEqual(len(payslip.worked_days_line_ids), 3)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 32)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 1043.69, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('OUT'), 0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 3.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 8.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('OUT'), 11.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 22.8, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 60.8, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('OUT'), 83.6, places=2)

        payslip_results = {
            'BASIC': 1043.69,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 1052.69,
            'ONSS': -137.59,
            'EmpBonus.1': 10.32,
            'ONSSTOTAL': 127.27,
            'ATN.CAR': 141.14,
            'GROSSIP': 1066.56,
            'IP.PART': -260.92,
            'GROSS': 805.64,
            'P.P': 0,
            'P.P.DED': 0,
            'PPTOTAL': 0,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0,
            'MEAL_V_EMP': -8.72,
            'REP.FEES': 28.85,
            'IP': 260.92,
            'IP.DED': -19.57,
            'NET': 916.98,
            'REMUNERATION': 782.77,
            'ONSSEMPLOYERBASIC': 263.38,
            'ONSSEMPLOYERFFE': 1.37,
            'ONSSEMPLOYERMFFE': 1.05,
            'ONSSEMPLOYERCPAE': 2.42,
            'ONSSEMPLOYERRESTREINT': 17.79,
            'ONSSEMPLOYERUNEMP': 1.05,
            'ONSSEMPLOYER': 287.07,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    # If there is a public holiday less than 30 days after the end of the
    # contract, the employee should be paid for that day too
    def test_out_of_contract_public_holiday(self):
        self.contract.date_end = datetime.date(2020, 9, 15)

        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2020, 9, 22, 5, 0, 0),
            'date_to': datetime.datetime(2020, 9, 22, 16, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }])

        payslip = self._generate_payslip(self.date_from, self.date_to)

        # The input is already there
        payslip.input_line_ids.amount = 60.21
        payslip.compute_sheet()

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 1)
        self.assertEqual(len(payslip.line_ids), 32)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('OUT'), 0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 1304.62, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('OUT'), 11.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 11.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('OUT'), 83.6, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 83.6, places=2)

        payslip_results = {
            'BASIC': 1304.62,
            'AFTERPUB': 60.21,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 1373.83,
            'ONSS': -179.56,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 179.56,
            'ATN.CAR': 141.14,
            'GROSSIP': 1335.41,
            'IP.PART': -326.16,
            'GROSS': 1009.26,
            'P.P': -13.42,
            'PPTOTAL': 13.42,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -11.99,
            'REP.FEES': 73.85,
            'IP': 326.16,
            'IP.DED': -24.46,
            'NET': 1209.25,
            'REMUNERATION': 978.47,
            'ONSSEMPLOYERBASIC': 343.73,
            'ONSSEMPLOYERCPAE': 3.16,
            'ONSSEMPLOYERFFE': 1.79,
            'ONSSEMPLOYERMFFE': 1.37,
            'ONSSEMPLOYERRESTREINT': 23.22,
            'ONSSEMPLOYERUNEMP': 1.37,
            'ONSSEMPLOYER': 374.64,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_end_of_contract_no_public_leave_right(self):
        # Check that only 1 day is taken into account (not 3) + Check it becomes 0 if another
        # contract is following
        self.contract.date_end = datetime.date(2020, 10, 13)
        self.contract.ip = False

        self.env['resource.calendar.leaves'].create([{
            'name': 'Armistice',
            'date_from': datetime.datetime.strptime('2020-11-11 07:00:00', '%Y-%m-%d %H:%M:%S'),
            'date_to': datetime.datetime.strptime('2020-11-11 18:00:00', '%Y-%m-%d %H:%M:%S'),
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id,
            'time_type': 'leave',
        }, {
            'name': 'Noel',
            'date_from': datetime.datetime.strptime('2020-12-25 07:00:00', '%Y-%m-%d %H:%M:%S'),
            'date_to': datetime.datetime.strptime('2020-12-25 18:00:00', '%Y-%m-%d %H:%M:%S'),
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id,
            'time_type': 'leave',
        }, {
            'name': 'Nouvel An',
            'date_from': datetime.datetime.strptime('2021-01-01 07:00:00', '%Y-%m-%d %H:%M:%S'),
            'date_to': datetime.datetime.strptime('2021-01-01 18:00:00', '%Y-%m-%d %H:%M:%S'),
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id,
            'time_type': 'leave',
        }])

        payslip = self._generate_payslip(datetime.date(2020, 10, 1), datetime.date(2020, 10, 31))

        # After contract public holiday is proposed
        self.assertEqual(len(payslip.input_line_ids), 1)

        new_contract = self.env['hr.contract'].create([{
            'name': "New Contract For Payslip Test",
            'employee_id': self.employee.id,
            'resource_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_generated_from': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'date_generated_to': datetime.datetime(2020, 9, 1, 0, 0, 0),
            'car_id': self.car.id,
            'structure_type_id': self.env.ref('hr_contract.structure_type_employee_cp200').id,
            'date_start': datetime.date(2020, 10, 14),
            'date_end': False,
            'wage': 2650.0,
            'wage_on_signature': 2650.0,
            'state': "open",
            'transport_mode_car': True,
            'fuel_card': 150.0,
            'internet': 38.0,
            'representation_fees': 150.0,
            'mobile': 30.0,
            'meal_voucher_amount': 7.45,
            'eco_checks': 250.0,
            'ip_wage_rate': 25.0,
            'ip': True,
        }])

        new_contract.generate_work_entries(datetime.date(2020, 10, 1), datetime.date(2020, 10, 31))

        payslip.input_line_ids.unlink()
        payslip._compute_worked_days_line_ids()

        # After contract public holiday is not proposed anymore
        self.assertEqual(len(payslip.input_line_ids), 0)

    def test_one_day_contract(self):
        self.contract.write({
            'date_start': datetime.date(2020, 9, 1),
            'date_end': datetime.date(2020, 9, 1),
            'ip': False,
        })
        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 27)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 122.31, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('OUT'), 0.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('OUT'), 21.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 7.6, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('OUT'), 159.6, places=2)

        payslip_results = {
            'BASIC': 122.31,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 131.31,
            'ONSS': -17.16,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 17.16,
            'ATN.CAR': 141.14,
            'GROSS': 255.29,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -1.09,
            'REP.FEES': 4.62,
            'NET': 108.68,
            'REMUNERATION': 122.31,
            'ONSSEMPLOYERBASIC': 32.85,
            'ONSSEMPLOYERFFE': 0.17,
            'ONSSEMPLOYERMFFE': 0.13,
            'ONSSEMPLOYERCPAE': 0.3,
            'ONSSEMPLOYERRESTREINT': 2.22,
            'ONSSEMPLOYERUNEMP': 0.13,
            'ONSSEMPLOYER': 35.81,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_bank_holidays(self):
        self.contract.ip = False
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 14, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 14, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }])
        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 26)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE500'), 122.31, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2527.69, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE500'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 21.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE500'), 7.6, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 159.6, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'ATN.CAR': 141.14,
            'GROSS': 2452.61,
            'P.P': -542.93,
            'PPTOTAL': 542.93,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -22.89,
            'REP.FEES': 150.0,
            'NET': 1862.99,
            'REMUNERATION': 2650.0,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_public_holiday_compensation(self):
        self.contract.ip = False
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 14, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 14, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_phc').id
        }])
        public_compensation_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_phc')

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 26)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('PHC1'), 122.31, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2527.69, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('PHC1'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 21.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('PHC1'), 7.6, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 159.6, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'ATN.CAR': 141.14,
            'GROSS': 2452.61,
            'P.P': -542.93,
            'PPTOTAL': 542.93,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -22.89,
            'REP.FEES': 150.0,
            'NET': 1862.99,
            'REMUNERATION': 2650.0,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_bank_holiday_half_days(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 14, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 15, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }, {
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 16, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 16, 10, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 4)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 30)

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].amount, 57.94, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].amount, 64.37, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].amount, 244.62, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[3].amount, 2283.08, places=2)

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].number_of_days, 1.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].number_of_days, 1.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].number_of_days, 2.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[3].number_of_days, 19.0, places=2)

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].number_of_hours, 3.6, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].number_of_hours, 4.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].number_of_hours, 15.2, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[3].number_of_hours, 144.4, places=2)

        payslip_results = {
            'BASIC': 2650.01,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.01,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'ATN.CAR': 141.14,
            'GROSSIP': 2452.62,
            'IP.PART': -662.5,
            'GROSS': 1790.12,
            'P.P': -240.26,
            'PPTOTAL': 240.26,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2117.07,
            'REMUNERATION': 1987.51,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_classic_credit_time(self):
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2020, 8, 1),
            'date_end': datetime.date(2020, 11, 30),
            'wage': 2120.0,
            'wage_on_signature': 2120.0,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })
        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 32)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2120.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 5.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 17.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 38.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 129.2, places=2)

        payslip_results = {
            'BASIC': 2120.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2129.0,
            'ONSS': -278.26,
            'EmpBonus.1': 105.93,
            'ONSSTOTAL': 172.33,
            'ATN.CAR': 141.14,
            'GROSSIP': 2097.81,
            'IP.PART': -530.0,
            'GROSS': 1567.81,
            'P.P': -143.96,
            'P.P.DED': 35.11,
            'PPTOTAL': 108.85,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -13.27,
            'MEAL_V_EMP': -18.53,
            'REP.FEES': 150.0,
            'IP': 530.0,
            'IP.DED': -39.75,
            'NET': 1917.26,
            'REMUNERATION': 1590.0,
            'ONSSEMPLOYERBASIC': 532.68,
            'ONSSEMPLOYERFFE': 2.77,
            'ONSSEMPLOYERMFFE': 2.13,
            'ONSSEMPLOYERCPAE': 4.9,
            'ONSSEMPLOYERRESTREINT': 35.98,
            'ONSSEMPLOYERUNEMP': 2.13,
            'ONSSEMPLOYER': 580.58,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_credit_time_paid_time_off(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 14, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 15, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }, {
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 17, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 18, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2020, 8, 1),
            'date_end': datetime.date(2020, 11, 30),
            'wage': 2120.0,
            'wage_on_signature': 2120.0,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 3)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 32)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE120'), 489.23, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 1630.77, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 5.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE120'), 4.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 13.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 38.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 30.4, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 98.7999999999999, places=2)

        payslip_results = {
            'BASIC': 2120.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2129.0,
            'ONSS': -278.26,
            'EmpBonus.1': 105.93,
            'ONSSTOTAL': 172.33,
            'ATN.CAR': 141.14,
            'GROSSIP': 2097.81,
            'IP.PART': -530.0,
            'GROSS': 1567.81,
            'P.P': -143.96,
            'P.P.DED': 35.11,
            'PPTOTAL': 108.85,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -13.27,
            'MEAL_V_EMP': -14.17,
            'REP.FEES': 150.0,
            'IP': 530.0,
            'IP.DED': -39.75,
            'NET': 1921.62,
            'REMUNERATION': 1590.0,
            'ONSSEMPLOYERBASIC': 532.68,
            'ONSSEMPLOYERFFE': 2.77,
            'ONSSEMPLOYERMFFE': 2.13,
            'ONSSEMPLOYERCPAE': 4.9,
            'ONSSEMPLOYERRESTREINT': 35.98,
            'ONSSEMPLOYERUNEMP': 2.13,
            'ONSSEMPLOYER': 580.58,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_credit_time_unpaid(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 14, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 15, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id
        }])

        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2020, 8, 1),
            'date_end': datetime.date(2020, 11, 30),
            'wage': 2120.0,
            'wage_on_signature': 2120.0,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 3)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 32)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE90'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 1875.38, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 5.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE90'), 2.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 15.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 38.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE90'), 15.2, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 114.0, places=2)

        payslip_results = {
            'BASIC': 1875.38,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 1884.38,
            'ONSS': -246.29,
            'EmpBonus.1': 92.18,
            'ONSSTOTAL': 154.1,
            'ATN.CAR': 141.14,
            'GROSSIP': 1871.42,
            'IP.PART': -468.85,
            'GROSS': 1402.57,
            'P.P': -89.39,
            'P.P.DED': 30.55,
            'PPTOTAL': 58.84,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -16.35,
            'REP.FEES': 150.0,
            'IP': 468.85,
            'IP.DED': -35.16,
            'NET': 1760.92,
            'REMUNERATION': 1406.54,
            'ONSSEMPLOYERBASIC': 471.47,
            'ONSSEMPLOYERFFE': 2.45,
            'ONSSEMPLOYERMFFE': 1.88,
            'ONSSEMPLOYERCPAE': 4.33,
            'ONSSEMPLOYERRESTREINT': 31.85,
            'ONSSEMPLOYERUNEMP': 1.88,
            'ONSSEMPLOYER': 513.87,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_credit_time_sick(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 14, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 15, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_sick_leave').id
        }])

        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2020, 8, 1),
            'date_end': datetime.date(2020, 11, 30),
            'wage': 2120.0,
            'wage_on_signature': 2120.0,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 3)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 32)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE110'), 244.62, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 1875.38, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 5.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE110'), 2.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 15.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 38.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE110'), 15.2, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 114.0, places=2)

        payslip_results = {
            'BASIC': 2120.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2129.0,
            'ONSS': -278.26,
            'EmpBonus.1': 105.93,
            'ONSSTOTAL': 172.33,
            'ATN.CAR': 141.14,
            'GROSSIP': 2097.81,
            'IP.PART': -530.0,
            'GROSS': 1567.81,
            'P.P': -143.96,
            'P.P.DED': 35.11,
            'PPTOTAL': 108.85,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -13.27,
            'MEAL_V_EMP': -16.35,
            'REP.FEES': 150.0,
            'IP': 530.0,
            'IP.DED': -39.75,
            'NET': 1919.44,
            'REMUNERATION': 1590.0,
            'ONSSEMPLOYERBASIC': 532.68,
            'ONSSEMPLOYERFFE': 2.77,
            'ONSSEMPLOYERMFFE': 2.13,
            'ONSSEMPLOYERCPAE': 4.9,
            'ONSSEMPLOYERRESTREINT': 35.98,
            'ONSSEMPLOYERUNEMP': 2.13,
            'ONSSEMPLOYER': 580.58,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_credit_time_full_time(self):
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_0_hours_per_week.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2020, 8, 1),
            'date_end': datetime.date(2020, 11, 27),
            'wage': 0.0,
            'wage_on_signature': 0.0,
            'ip': False,
            'time_credit': True,
            'work_time_rate': 0,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 26)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 22.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 167.2, places=2)

        payslip_results = {
            'BASIC': 0.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 9.0,
            'ONSS': -1.18,
            'ONSSTOTAL': 1.18,
            'ATN.CAR': 141.14,
            'GROSS': 148.97,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': 0.0,
            'REP.FEES': 0.0,
            'NET': -1.18,
            'REMUNERATION': 0.0,
            'ONSSEMPLOYERBASIC': 2.25,
            'ONSSEMPLOYERFFE': 0.01,
            'ONSSEMPLOYERMFFE': 0.01,
            'ONSSEMPLOYERCPAE': 0.02,
            'ONSSEMPLOYERRESTREINT': 0.15,
            'ONSSEMPLOYERUNEMP': 0.01,
            'ONSSEMPLOYER': 2.45,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_half_time(self):
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_half_time.id,
            'wage': 1325.0,
            'wage_on_signature': 1325.0,
            'ip': False,
        })

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 28)

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].amount, 224.23, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].amount, 1100.77, places=2)

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].number_of_days, 5.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].number_of_days, 9.0, places=2)

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].number_of_hours, 19.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].number_of_hours, 68.4, places=2)

        payslip_results = {
            'BASIC': 1325.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 1334.0,
            'ONSS': -174.35,
            'EmpBonus.1': 174.35,
            'ONSSTOTAL': 0.0,
            'ATN.CAR': 141.14,
            'GROSS': 1475.14,
            'P.P': -109.45,
            'P.P.DED': 57.78,
            'PPTOTAL': 51.67,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -15.26,
            'REP.FEES': 150.0,
            'NET': 1408.07,
            'REMUNERATION': 1325.0,
            'ONSSEMPLOYERBASIC': 333.77,
            'ONSSEMPLOYERFFE': 1.73,
            'ONSSEMPLOYERMFFE': 1.33,
            'ONSSEMPLOYERCPAE': 3.07,
            'ONSSEMPLOYERRESTREINT': 22.54,
            'ONSSEMPLOYERUNEMP': 1.33,
            'ONSSEMPLOYER': 363.78,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_half_time_1_day_paid_time_off(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_half_time.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 14, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 14, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        self.contract.write({
            'resource_calendar_id': self.resource_calendar_half_time.id,
            'wage': 1325.0,
            'wage_on_signature': 1325.0,
            'ip': False,
        })

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 3)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 28)

        # 0 LEAVE120, 1-2 WORK100
        self.assertAlmostEqual(payslip.worked_days_line_ids[0].amount, 122.31, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].amount, 305.77, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].amount, 896.92, places=2)

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].number_of_days, 1.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].number_of_days, 5.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].number_of_days, 8.0, places=2)

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].number_of_hours, 7.6, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].number_of_hours, 19.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].number_of_hours, 60.8, places=2)

        payslip_results = {
            'BASIC': 1325.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 1334.0,
            'ONSS': -174.35,
            'EmpBonus.1': 174.35,
            'ONSSTOTAL': 0.0,
            'ATN.CAR': 141.14,
            'GROSS': 1475.14,
            'P.P': -109.45,
            'P.P.DED': 57.78,
            'PPTOTAL': 51.67,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -14.17,
            'REP.FEES': 150.0,
            'NET': 1409.16,
            'REMUNERATION': 1325.0,
            'ONSSEMPLOYERBASIC': 333.77,
            'ONSSEMPLOYERFFE': 1.73,
            'ONSSEMPLOYERMFFE': 1.33,
            'ONSSEMPLOYERCPAE': 3.07,
            'ONSSEMPLOYERRESTREINT': 22.54,
            'ONSSEMPLOYERUNEMP': 1.33,
            'ONSSEMPLOYER': 363.78,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_half_time_1_day_unpaid_time_off(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_half_time.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 16, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 16, 9, 48, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }, {
            'name': "Absence",
            'calendar_id': self.resource_calendar_half_time.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 21, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 21, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id
        }])

        self.contract.write({
            'resource_calendar_id': self.resource_calendar_half_time.id,
            'wage': 1325.0,
            'wage_on_signature': 1325.0,
            'ip': False,
        })

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 4)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 28)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE120'), 61.15, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE90'), 0.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].amount, 244.62, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[3].amount, 896.92, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE120'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE90'), 1.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].number_of_days, 4.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[3].number_of_days, 8.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 3.8, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE90'), 7.6, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].number_of_hours, 15.2, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[3].number_of_hours, 60.8, places=2)

        payslip_results = {
            'BASIC': 1202.69,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 1211.69,
            'ONSS': -158.37,
            'EmpBonus.1': 158.37,
            'ONSSTOTAL': 0.0,
            'ATN.CAR': 141.14,
            'GROSS': 1352.83,
            'P.P': -78.02,
            'P.P.DED': 52.48,
            'PPTOTAL': 25.54,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -13.08,
            'REP.FEES': 150.0,
            'NET': 1314.07,
            'REMUNERATION': 1202.69,
            'ONSSEMPLOYERBASIC': 303.16,
            'ONSSEMPLOYERFFE': 1.58,
            'ONSSEMPLOYERMFFE': 1.21,
            'ONSSEMPLOYERCPAE': 2.79,
            'ONSSEMPLOYERRESTREINT': 20.48,
            'ONSSEMPLOYERUNEMP': 1.21,
            'ONSSEMPLOYER': 330.43,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_maternity_time_off(self):
        self.public_time_off = self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2020, 10, 6, 5, 0, 0),
            'date_to': datetime.datetime(2020, 10, 6, 16, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }])

        maternity_time_off = self.env['hr.leave'].new({
            'name': 'Maternity Time Off : 15 weeks',
            'employee_id': self.employee.id,
            'holiday_status_id': self.env.ref('l10n_be_hr_payroll.holiday_type_maternity').id,
            'request_date_from': datetime.date(2020, 9, 10),
            'request_date_to': datetime.date(2020, 12, 24),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 76,
        })
        maternity_time_off._compute_date_from_to()
        maternity_time_off = self.env['hr.leave'].create(maternity_time_off._convert_to_write(maternity_time_off._cache))

        september_payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(september_payslip.worked_days_line_ids), 2)
        self.assertEqual(len(september_payslip.input_line_ids), 0)
        self.assertEqual(len(september_payslip.line_ids), 32)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('WORK100'), 815.38, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('LEAVE210'), 0.0, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('WORK100'), 7.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('LEAVE210'), 15.0, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('WORK100'), 53.2, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('LEAVE210'), 114.0, places=2)

        payslip_results = {
            'BASIC': 815.38,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 824.38,
            'ONSS': -107.75,
            'EmpBonus.1': 1.46,
            'ONSSTOTAL': 106.29,
            'ATN.CAR': 141.14,
            'GROSSIP': 859.24,
            'IP.PART': -203.85,
            'GROSS': 655.39,
            'P.P': 0.0,
            'P.P.DED': 0.0,
            'PPTOTAL': 0.0,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -7.63,
            'REP.FEES': 150.0,
            'IP': 203.85,
            'IP.DED': -15.29,
            'NET': 836.17,
            'REMUNERATION': 611.54,
            'ONSSEMPLOYERBASIC': 206.26,
            'ONSSEMPLOYERFFE': 1.07,
            'ONSSEMPLOYERMFFE': 0.82,
            'ONSSEMPLOYERCPAE': 1.9,
            'ONSSEMPLOYERRESTREINT': 13.93,
            'ONSSEMPLOYERUNEMP': 0.82,
            'ONSSEMPLOYER': 224.81,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(september_payslip, payslip_results)

        october_payslip = self._generate_payslip(datetime.date(2020, 10, 1), datetime.date(2020, 10, 31))

        self.assertEqual(len(october_payslip.worked_days_line_ids), 2)
        self.assertEqual(len(october_payslip.input_line_ids), 0)
        self.assertEqual(len(october_payslip.line_ids), 31)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('LEAVE210'), 0.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('LEAVE500'), 122.31, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('LEAVE210'), 21.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('LEAVE500'), 1.0, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('LEAVE210'), 159.60, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('LEAVE500'), 7.6, places=2)

        payslip_results = {
            'BASIC': 122.31,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 131.31,
            'ONSS': -17.16,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 17.16,
            'ATN.CAR': 141.14,
            'GROSSIP': 255.29,
            'IP.PART': -30.58,
            'GROSS': 224.71,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': 0.0,
            'REP.FEES': 150.0,
            'IP': 30.58,
            'IP.DED': -2.29,
            'NET': 252.85,
            'REMUNERATION': 91.73,
            'ONSSEMPLOYERBASIC': 32.85,
            'ONSSEMPLOYERFFE': 0.17,
            'ONSSEMPLOYERMFFE': 0.13,
            'ONSSEMPLOYERCPAE': 0.3,
            'ONSSEMPLOYERRESTREINT': 2.22,
            'ONSSEMPLOYERUNEMP': 0.13,
            'ONSSEMPLOYER': 35.81,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(october_payslip, payslip_results)

        november_payslip = self._generate_payslip(datetime.date(2020, 11, 1), datetime.date(2020, 11, 30))

        self.assertEqual(len(november_payslip.worked_days_line_ids), 1)
        self.assertEqual(len(november_payslip.input_line_ids), 0)
        self.assertEqual(len(november_payslip.line_ids), 30)

        self.assertAlmostEqual(november_payslip._get_worked_days_line_amount('LEAVE210'), 0.0, places=2)

        self.assertAlmostEqual(november_payslip._get_worked_days_line_number_of_days('LEAVE210'), 21.0, places=2)

        self.assertAlmostEqual(november_payslip._get_worked_days_line_number_of_hours('LEAVE210'), 159.6, places=2)
        payslip_results = {
            'BASIC': 0.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 9.0,
            'ONSS': -1.18,
            'ONSSTOTAL': 1.18,
            'ATN.CAR': 141.14,
            'GROSSIP': 148.97,
            'IP.PART': 0.0,
            'GROSS': 148.97,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': 0.0,
            'REP.FEES': 0.0,
            'IP': 0.0,
            'IP.DED': 0.0,
            'NET': -1.18,
            'REMUNERATION': 0.0,
            'ONSSEMPLOYERBASIC': 2.25,
            'ONSSEMPLOYERFFE': 0.01,
            'ONSSEMPLOYERMFFE': 0.01,
            'ONSSEMPLOYERCPAE': 0.02,
            'ONSSEMPLOYERRESTREINT': 0.15,
            'ONSSEMPLOYERUNEMP': 0.01,
            'ONSSEMPLOYER': 2.45,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(november_payslip, payslip_results)

    def test_paid_time_off_payslip(self):
        self.contract.ip = False
        self.leaves = self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 8, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 8, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 26)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE120'), 122.31, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2527.69, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE120'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 21.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 7.6, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 159.6, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'ATN.CAR': 141.14,
            'GROSS': 2452.61,
            'P.P': -542.93,
            'PPTOTAL': 542.93,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -22.89,
            'REP.FEES': 150.0,
            'NET': 1862.99,
            'REMUNERATION': 2650.0,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_sample_payslip_unpaid_time_off(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 8, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 9, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 31)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE90'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2405.38, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE90'), 2.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 20.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE90'), 15.2, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 152.0, places=2)

        payslip_results = {
            'BASIC': 2405.38,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2414.38,
            'ONSS': -315.56,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 315.56,
            'ATN.CAR': 141.14,
            'GROSSIP': 2239.96,
            'IP.PART': -601.35,
            'GROSS': 1638.62,
            'P.P': -176.06,
            'PPTOTAL': 176.06,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -20.97,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 150.0,
            'IP': 601.35,
            'IP.DED': -45.1,
            'NET': 1975.89,
            'REMUNERATION': 1804.04,
            'ONSSEMPLOYERBASIC': 604.08,
            'ONSSEMPLOYERFFE': 3.14,
            'ONSSEMPLOYERMFFE': 2.41,
            'ONSSEMPLOYERCPAE': 5.55,
            'ONSSEMPLOYERRESTREINT': 40.8,
            'ONSSEMPLOYERUNEMP': 2.41,
            'ONSSEMPLOYER': 658.4,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_unpaid_half_days(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 14, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 15, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id
        }, {
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 16, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 16, 10, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 4)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 31)

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].amount, 57.94, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].amount, 0.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].amount, 0.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[3].amount, 2283.08, places=2)

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].number_of_days, 1.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].number_of_days, 1.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].number_of_days, 2.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[3].number_of_days, 19.0, places=2)

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].number_of_hours, 3.6, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].number_of_hours, 4.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].number_of_hours, 15.2, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[3].number_of_hours, 144.4, places=2)

        payslip_results = {
            'BASIC': 2341.02,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2350.02,
            'ONSS': -307.15,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 307.15,
            'ATN.CAR': 141.14,
            'GROSSIP': 2184.02,
            'IP.PART': -585.26,
            'GROSS': 1598.76,
            'P.P': -156.8,
            'PPTOTAL': 156.8,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -20.26,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 150.0,
            'IP': 585.26,
            'IP.DED': -43.89,
            'NET': 1941.12,
            'REMUNERATION': 1755.77,
            'ONSSEMPLOYERBASIC': 587.98,
            'ONSSEMPLOYERFFE': 3.06,
            'ONSSEMPLOYERMFFE': 2.35,
            'ONSSEMPLOYERCPAE': 5.41,
            'ONSSEMPLOYERRESTREINT': 39.72,
            'ONSSEMPLOYERUNEMP': 2.35,
            'ONSSEMPLOYER': 640.85,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_unjustified_reason(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 14, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 14, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_unpredictable').id
        }])

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 31)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE250'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2527.69, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE250'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 21.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE250'), 7.6, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 159.6, places=2)

        payslip_results = {
            'BASIC': 2527.69,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2536.69,
            'ONSS': -331.55,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 331.55,
            'ATN.CAR': 141.14,
            'GROSSIP': 2346.29,
            'IP.PART': -631.92,
            'GROSS': 1714.36,
            'P.P': -208.16,
            'PPTOTAL': 208.16,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -22.31,
            'MEAL_V_EMP': -22.89,
            'REP.FEES': 150.0,
            'IP': 631.92,
            'IP.DED': -47.39,
            'NET': 2045.39,
            'REMUNERATION': 1895.77,
            'ONSSEMPLOYERBASIC': 634.68,
            'ONSSEMPLOYERFFE': 3.3,
            'ONSSEMPLOYERMFFE': 2.54,
            'ONSSEMPLOYERCPAE': 5.83,
            'ONSSEMPLOYERRESTREINT': 42.87,
            'ONSSEMPLOYERUNEMP': 2.54,
            'ONSSEMPLOYER': 691.76,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_private_car(self):
        self.employee.km_home_work = 41
        self.contract.write({
            'wage_with_holidays': 3707.12,
            'holidays': 12.0,
            'transport_mode_car': False,
            'transport_mode_private_car': True,
            'fuel_card': 0.0,
            'internet': 43.99,
            'representation_fees': 150.0,
            'ip_wage_rate': 20.0,
            'car_id': False,
        })
        self.contract.wage_on_signature = self.contract.wage_with_holidays

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 28)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 3707.12, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 22.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 167.2, places=2)

        payslip_results = {
            'BASIC': 3707.12,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 3716.12,
            'ONSS': -485.7,
            'ONSSTOTAL': 485.7,
            'GROSSIP': 3230.42,
            'IP.PART': -741.42,
            'GROSS': 2489.0,
            'P.P': -557.38,
            'PPTOTAL': 557.38,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -35.29,
            'MEAL_V_EMP': -23.98,
            'CAR.PRIV': 69.5,
            'REP.FEES': 150.0,
            'IP': 741.42,
            'IP.DED': -55.61,
            'NET': 2768.67,
            'REMUNERATION': 2965.7,
            'ONSSEMPLOYERBASIC': 929.77,
            'ONSSEMPLOYERFFE': 4.83,
            'ONSSEMPLOYERMFFE': 3.72,
            'ONSSEMPLOYERCPAE': 8.55,
            'ONSSEMPLOYERRESTREINT': 62.8,
            'ONSSEMPLOYERUNEMP': 3.72,
            'ONSSEMPLOYER': 1013.39,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_sample_payslip_lines_edition(self):
        """
        Test the edtion of payslip lines in this sample payslip
        We want to edit the amount of the payslip line containing ATN.INT as code.
        After the edition, we recompute the following payslip lines and we check if the payslip line containing the ATN.INT.2 as code
        has been edited. It should be the opposite amount of the ATN.INT.
        We also want to edit hte amount of the payslip line containing ATN.MOB as code.
        Same process than the previous edition.
        After these both editions, we need to check if all payslip lines are correct and we have the expected total for the NET SALARY.
        """
        self.contract.ip = False
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 2, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 3, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_sick_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 26)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'ATN.CAR': 141.14,
            'GROSS': 2452.61,
            'P.P': -542.93,
            'PPTOTAL': 542.93,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 150.0,
            'NET': 1864.08,
            'REMUNERATION': 2650.0,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

        # PAYSLIP EDITION
        action = payslip.action_edit_payslip_lines()
        wizard = self.env[action['res_model']].browse(action['res_id'])

        # Edit the amount of the payslip line with the ATN.INT code
        atn_int_line = wizard.line_ids.filtered(lambda line: line.code == 'ATN.INT')
        atn_int_line.amount = 6.0
        wizard.recompute_following_lines(atn_int_line.id)
        self.assertEqual(atn_int_line.amount, 6.0)
        self.assertAlmostEqual(atn_int_line.total, 6.0, places=2)

        # Check if the ATN.INT.2 has also been edited
        atn_int_2_line = wizard.line_ids.filtered(lambda line: line.code == 'ATN.INT.2')
        self.assertEqual(atn_int_2_line.amount, -atn_int_line.amount)
        self.assertAlmostEqual(atn_int_2_line.total, -6.0, places=2)

        # Edit the amount of the payslip line with the ATN.MOB code
        atn_mob_line = wizard.line_ids.filtered(lambda line: line.code == 'ATN.MOB')
        atn_mob_line.amount = 5.0
        wizard.recompute_following_lines(atn_mob_line.id)
        self.assertEqual(atn_mob_line.amount, 5.0)
        self.assertAlmostEqual(atn_mob_line.total, 5.0, places=2)

        # Check if the ATN.MOB.2
        atn_mob_2_line = wizard.line_ids.filtered(lambda line: line.code == 'ATN.MOB.2')
        self.assertEqual(atn_mob_2_line.amount, -5.0)
        self.assertAlmostEqual(atn_mob_2_line.total, -5.0, places=2)

        # Check if the payslip is correctly recomputed
        wizard.action_validate_edition()
        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 6.0,
            'ATN.MOB': 5.0,
            'SALARY': 2661.0,
            'ONSS': -347.79,
            'ONSSTOTAL': 347.79,
            'ATN.CAR': 141.14,
            'GROSS': 2454.35,
            'P.P': -542.93,
            'PPTOTAL': 542.93,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -6.0,
            'ATN.MOB.2': -5.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 150.0,
            'NET': 1863.82,
            'REMUNERATION': 2650.0,
            'ONSSEMPLOYERBASIC': 665.78,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERRESTREINT': 44.97,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.65,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_relapse_without_guaranteed_salary(self):
        # Sick 1 Week (1 - 7 september)
        # Back 1 week (8 - 14 september)
        # Sick 4 weeks (15 septembeer - 13 october)
        # Part time sick from the 31 calendar day since the first sick day

        sick_leave_1 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 1 Week',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2020, 9, 1),
            'request_date_to': datetime.date(2020, 9, 7),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 5,
        })
        sick_leave_1._compute_date_from_to()
        sick_leave_1 = self.env['hr.leave'].create(sick_leave_1._convert_to_write(sick_leave_1._cache))

        sick_leave_2 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 4 Weeks',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2020, 9, 15),
            'request_date_to': datetime.date(2020, 10, 13),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 24,
        })
        sick_leave_2._compute_date_from_to()
        sick_leave_2 = self.env['hr.leave'].create(sick_leave_2._convert_to_write(sick_leave_2._cache))

        (sick_leave_1 + sick_leave_2).action_validate()

        work_entries = self.employee.contract_id.generate_work_entries(datetime.date(2020, 9, 1), datetime.date(2020, 10, 31))

        attendance = self.env.ref('hr_work_entry.work_entry_type_attendance')
        sick_work_entry_type = self.env.ref('hr_work_entry_contract.work_entry_type_sick_leave')
        partial_sick_work_entry_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_part_sick')

        work_entries_expected_results = {
            (1, 9): sick_work_entry_type,
            (2, 9): sick_work_entry_type,
            (3, 9): sick_work_entry_type,
            (4, 9): sick_work_entry_type,
            (7, 9): sick_work_entry_type,
            (8, 9): attendance,
            (9, 9): attendance,
            (10, 9): attendance,
            (11, 9): attendance,
            (14, 9): attendance,
            (15, 9): sick_work_entry_type,
            (16, 9): sick_work_entry_type,
            (17, 9): sick_work_entry_type,
            (18, 9): sick_work_entry_type,
            (20, 9): sick_work_entry_type,
            (21, 9): sick_work_entry_type,
            (22, 9): sick_work_entry_type,
            (23, 9): sick_work_entry_type,
            (24, 9): sick_work_entry_type,
            (25, 9): sick_work_entry_type,
            (28, 9): sick_work_entry_type,
            (29, 9): sick_work_entry_type,
            (30, 9): sick_work_entry_type,
            (1, 10): sick_work_entry_type,
            (2, 10): sick_work_entry_type,
            (5, 10): sick_work_entry_type,
            (6, 10): sick_work_entry_type,
            (7, 10): sick_work_entry_type,
            (8, 10): partial_sick_work_entry_type,
            (9, 10): partial_sick_work_entry_type,
            (9, 10): partial_sick_work_entry_type,
            (12, 10): partial_sick_work_entry_type,
            (13, 10): partial_sick_work_entry_type,
            (14, 10): attendance,
            (15, 10): attendance,
            (16, 10): attendance,
            (19, 10): attendance,
            (20, 10): attendance,
            (21, 10): attendance,
            (22, 10): attendance,
            (23, 10): attendance,
            (26, 10): attendance,
            (27, 10): attendance,
            (28, 10): attendance,
            (29, 10): attendance,
            (30, 10): attendance,
            (31, 10): attendance,
        }

        for we in work_entries:
            self.assertEqual(
                we.work_entry_type_id,
                work_entries_expected_results[(we.date_start.day, we.date_start.month)],
                'On %s/%s, expected work entry type %s, got %s instead' % (we.date_start.day, we.date_start.month, work_entries_expected_results[(we.date_start.day, we.date_start.month)].name, we.work_entry_type_id.name))

        september_payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(september_payslip.worked_days_line_ids), 2)
        self.assertEqual(len(september_payslip.input_line_ids), 0)
        self.assertEqual(len(september_payslip.line_ids), 30)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('WORK100'), 611.54, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('LEAVE110'), 2038.46, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('WORK100'), 5.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('LEAVE110'), 17.0, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('WORK100'), 38.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('LEAVE110'), 129.2, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'ATN.CAR': 141.14,
            'GROSSIP': 2452.61,
            'IP.PART': -662.5,
            'GROSS': 1790.11,
            'P.P': -240.26,
            'PPTOTAL': 240.26,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -5.45,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2133.41,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(september_payslip, payslip_results)

        october_payslip = self._generate_payslip(datetime.date(2020, 10, 1), datetime.date(2020, 10, 31))

        self.assertEqual(len(october_payslip.worked_days_line_ids), 3)
        self.assertEqual(len(october_payslip.input_line_ids), 0)
        self.assertEqual(len(october_payslip.line_ids), 31)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('WORK100'), 1549.23, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('LEAVE110'), 611.54, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('LEAVE214'), 0.0, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('WORK100'), 13.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('LEAVE110'), 5.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('LEAVE214'), 4.0, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('WORK100'), 98.8, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('LEAVE110'), 38.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('LEAVE214'), 30.4, places=2)

        payslip_results = {
            'BASIC': 2160.77,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2169.77,
            'ONSS': -283.59,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 283.59,
            'ATN.CAR': 141.14,
            'GROSSIP': 2027.32,
            'IP.PART': -540.19,
            'GROSS': 1487.13,
            'P.P': -113.46,
            'PPTOTAL': 113.46,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -16.37,
            'MEAL_V_EMP': -14.17,
            'REP.FEES': 150.0,
            'IP': 540.19,
            'IP.DED': -40.51,
            'NET': 1842.67,
            'REMUNERATION': 1620.58,
            'ONSSEMPLOYERBASIC': 542.88,
            'ONSSEMPLOYERFFE': 2.82,
            'ONSSEMPLOYERMFFE': 2.17,
            'ONSSEMPLOYERCPAE': 4.99,
            'ONSSEMPLOYERRESTREINT': 36.67,
            'ONSSEMPLOYERUNEMP': 2.17,
            'ONSSEMPLOYER': 591.7,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(october_payslip, payslip_results)

    def test_relapse_with_guaranteed_salary(self):
        # Sick 1 Week (1 - 2 september)
        # Back 1 week (3 - 18 september)
        # Sick 2.5 weeks (21 septembeer - 7 october)
        # No part time sick as there is at least 15 days between the 2 sick time offs

        sick_leave_1 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 2 Days',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2020, 9, 1),
            'request_date_to': datetime.date(2020, 9, 2),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 2,
        })
        sick_leave_1._compute_date_from_to()
        sick_leave_1 = self.env['hr.leave'].create(sick_leave_1._convert_to_write(sick_leave_1._cache))

        sick_leave_2 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 2.5 Weeks',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2020, 9, 21),
            'request_date_to': datetime.date(2020, 10, 7),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 13,
        })
        sick_leave_2._compute_date_from_to()
        sick_leave_2 = self.env['hr.leave'].create(sick_leave_2._convert_to_write(sick_leave_2._cache))

        (sick_leave_1 + sick_leave_2).action_validate()

        work_entries = self.employee.contract_id.generate_work_entries(datetime.date(2020, 9, 1), datetime.date(2020, 10, 31))

        attendance = self.env.ref('hr_work_entry.work_entry_type_attendance')
        sick_work_entry_type = self.env.ref('hr_work_entry_contract.work_entry_type_sick_leave')

        work_entries_expected_results = {
            (1, 9): sick_work_entry_type,
            (2, 9): sick_work_entry_type,
            (3, 9): attendance,
            (4, 9): attendance,
            (7, 9): attendance,
            (8, 9): attendance,
            (9, 9): attendance,
            (10, 9): attendance,
            (11, 9): attendance,
            (14, 9): attendance,
            (15, 9): attendance,
            (16, 9): attendance,
            (17, 9): attendance,
            (18, 9): attendance,
            (20, 9): attendance,
            (21, 9): sick_work_entry_type,
            (22, 9): sick_work_entry_type,
            (23, 9): sick_work_entry_type,
            (24, 9): sick_work_entry_type,
            (25, 9): sick_work_entry_type,
            (28, 9): sick_work_entry_type,
            (29, 9): sick_work_entry_type,
            (30, 9): sick_work_entry_type,
            (1, 10): sick_work_entry_type,
            (2, 10): sick_work_entry_type,
            (5, 10): sick_work_entry_type,
            (6, 10): sick_work_entry_type,
            (7, 10): sick_work_entry_type,
            (8, 10): attendance,
            (9, 10): attendance,
            (9, 10): attendance,
            (12, 10): attendance,
            (13, 10): attendance,
            (14, 10): attendance,
            (15, 10): attendance,
            (16, 10): attendance,
            (19, 10): attendance,
            (20, 10): attendance,
            (21, 10): attendance,
            (22, 10): attendance,
            (23, 10): attendance,
            (26, 10): attendance,
            (27, 10): attendance,
            (28, 10): attendance,
            (29, 10): attendance,
            (30, 10): attendance,
            (31, 10): attendance,
        }

        for w in work_entries:
            self.assertEqual(w.work_entry_type_id, work_entries_expected_results.get((w.date_start.day, w.date_start.month)))

        september_payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(september_payslip.worked_days_line_ids), 2)
        self.assertEqual(len(september_payslip.input_line_ids), 0)
        self.assertEqual(len(september_payslip.line_ids), 30)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('LEAVE110'), 1223.08, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('WORK100'), 1426.92, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('LEAVE110'), 10.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('WORK100'), 12.0, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('LEAVE110'), 76.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('WORK100'), 91.2, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'ATN.CAR': 141.14,
            'GROSSIP': 2452.61,
            'IP.PART': -662.5,
            'GROSS': 1790.11,
            'P.P': -240.26,
            'PPTOTAL': 240.26,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -13.08,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2125.78,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(september_payslip, payslip_results)

        october_payslip = self._generate_payslip(datetime.date(2020, 10, 1), datetime.date(2020, 10, 31))

        self.assertEqual(len(october_payslip.worked_days_line_ids), 2)
        self.assertEqual(len(october_payslip.input_line_ids), 0)
        self.assertEqual(len(october_payslip.line_ids), 30)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('LEAVE110'), 611.54, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('WORK100'), 2038.46, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('LEAVE110'), 5.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('WORK100'), 17.0, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('LEAVE110'), 38.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('WORK100'), 129.2, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'ATN.CAR': 141.14,
            'GROSSIP': 2452.61,
            'IP.PART': -662.5,
            'GROSS': 1790.11,
            'P.P': -240.26,
            'PPTOTAL': 240.26,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -18.53,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2120.33,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(october_payslip, payslip_results)

    def test_sick_more_than_30_days(self):
        # Sick 1 september - 15 october
        # Part time sick from the 31th day
        sick_leave = self.env['hr.leave'].new({
            'name': 'Sick Time Off 33 Days',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2020, 9, 1),
            'request_date_to': datetime.date(2020, 10, 15),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 33,
        })
        sick_leave._compute_date_from_to()
        sick_leave = self.env['hr.leave'].create(sick_leave._convert_to_write(sick_leave._cache))
        sick_leave.action_validate()

        work_entries = self.employee.contract_id.generate_work_entries(datetime.date(2020, 9, 1), datetime.date(2020, 10, 31))

        attendance = self.env.ref('hr_work_entry.work_entry_type_attendance')
        sick_work_entry_type = self.env.ref('hr_work_entry_contract.work_entry_type_sick_leave')
        partial_sick_work_entry_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_part_sick')

        work_entries_expected_results = {
            (1, 9): sick_work_entry_type,
            (2, 9): sick_work_entry_type,
            (3, 9): sick_work_entry_type,
            (4, 9): sick_work_entry_type,
            (7, 9): sick_work_entry_type,
            (8, 9): sick_work_entry_type,
            (9, 9): sick_work_entry_type,
            (10, 9): sick_work_entry_type,
            (11, 9): sick_work_entry_type,
            (14, 9): sick_work_entry_type,
            (15, 9): sick_work_entry_type,
            (16, 9): sick_work_entry_type,
            (17, 9): sick_work_entry_type,
            (18, 9): sick_work_entry_type,
            (20, 9): sick_work_entry_type,
            (21, 9): sick_work_entry_type,
            (22, 9): sick_work_entry_type,
            (23, 9): sick_work_entry_type,
            (24, 9): sick_work_entry_type,
            (25, 9): sick_work_entry_type,
            (28, 9): sick_work_entry_type,
            (29, 9): sick_work_entry_type,
            (30, 9): sick_work_entry_type,
            (1, 10): partial_sick_work_entry_type,
            (2, 10): partial_sick_work_entry_type,
            (5, 10): partial_sick_work_entry_type,
            (6, 10): partial_sick_work_entry_type,
            (7, 10): partial_sick_work_entry_type,
            (8, 10): partial_sick_work_entry_type,
            (9, 10): partial_sick_work_entry_type,
            (9, 10): partial_sick_work_entry_type,
            (12, 10): partial_sick_work_entry_type,
            (13, 10): partial_sick_work_entry_type,
            (14, 10): partial_sick_work_entry_type,
            (15, 10): partial_sick_work_entry_type,
            (16, 10): attendance,
            (19, 10): attendance,
            (20, 10): attendance,
            (21, 10): attendance,
            (22, 10): attendance,
            (23, 10): attendance,
            (26, 10): attendance,
            (27, 10): attendance,
            (28, 10): attendance,
            (29, 10): attendance,
            (30, 10): attendance,
            (31, 10): attendance,
        }

        for w in work_entries:
            self.assertEqual(w.work_entry_type_id, work_entries_expected_results.get((w.date_start.day, w.date_start.month)))

        september_payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(september_payslip.worked_days_line_ids), 1)
        self.assertEqual(len(september_payslip.input_line_ids), 0)
        self.assertEqual(len(september_payslip.line_ids), 30)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('LEAVE110'), 2650.0, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('LEAVE110'), 22.0, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('LEAVE110'), 167.2, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'ATN.CAR': 141.14,
            'GROSSIP': 2452.61,
            'IP.PART': -662.5,
            'GROSS': 1790.11,
            'P.P': -240.26,
            'PPTOTAL': 240.26,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': 0.0,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2138.86,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(september_payslip, payslip_results)

        october_payslip = self._generate_payslip(datetime.date(2020, 10, 1), datetime.date(2020, 10, 31))

        self.assertEqual(len(october_payslip.worked_days_line_ids), 2)
        self.assertEqual(len(october_payslip.input_line_ids), 0)
        self.assertEqual(len(october_payslip.line_ids), 31)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('WORK100'), 1304.62, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('LEAVE214'), 0.0, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('WORK100'), 11.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('LEAVE214'), 11.0, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('WORK100'), 83.6, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('LEAVE214'), 83.6, places=2)

        payslip_results = {
            'BASIC': 1304.62,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 1313.62,
            'ONSS': -171.69,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 171.69,
            'ATN.CAR': 141.14,
            'GROSSIP': 1283.07,
            'IP.PART': -326.16,
            'GROSS': 956.92,
            'P.P': -2.18,
            'PPTOTAL': 2.18,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -11.99,
            'REP.FEES': 150.0,
            'IP': 326.16,
            'IP.DED': -24.46,
            'NET': 1244.3,
            'REMUNERATION': 978.47,
            'ONSSEMPLOYERBASIC': 328.67,
            'ONSSEMPLOYERFFE': 1.71,
            'ONSSEMPLOYERMFFE': 1.31,
            'ONSSEMPLOYERCPAE': 3.02,
            'ONSSEMPLOYERRESTREINT': 22.2,
            'ONSSEMPLOYERUNEMP': 1.31,
            'ONSSEMPLOYER': 358.22,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(october_payslip, payslip_results)

    def test_relapse_without_guaranteed_salary_credit_time(self):
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2020, 1, 1),
            'date_end': datetime.date(2021, 9, 30),
            'wage': 2120.0,
            'wage_on_signature': 2120.0,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })

        sick_leave_1 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 1 Week',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2020, 9, 1),
            'request_date_to': datetime.date(2020, 9, 7),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 5,
        })
        sick_leave_1._compute_date_from_to()
        sick_leave_1 = self.env['hr.leave'].create(sick_leave_1._convert_to_write(sick_leave_1._cache))

        sick_leave_2 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 4 Weeks',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2020, 9, 15),
            'request_date_to': datetime.date(2020, 10, 13),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 24,
        })
        sick_leave_2._compute_date_from_to()
        sick_leave_2 = self.env['hr.leave'].create(sick_leave_2._convert_to_write(sick_leave_2._cache))

        (sick_leave_1 + sick_leave_2).action_validate()

        work_entries = self.employee.contract_id.generate_work_entries(datetime.date(2020, 9, 1), datetime.date(2020, 10, 31))

        attendance = self.env.ref('hr_work_entry.work_entry_type_attendance')
        sick_work_entry_type = self.env.ref('hr_work_entry_contract.work_entry_type_sick_leave')
        partial_sick_work_entry_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_part_sick')
        credit_time_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time')

        work_entries_expected_results = {
            (1, 9): sick_work_entry_type,
            (2, 9): credit_time_type,
            (3, 9): sick_work_entry_type,
            (4, 9): sick_work_entry_type,
            (7, 9): sick_work_entry_type,
            (8, 9): attendance,
            (9, 9): credit_time_type,
            (10, 9): attendance,
            (11, 9): attendance,
            (14, 9): attendance,
            (15, 9): sick_work_entry_type,
            (16, 9): credit_time_type,
            (17, 9): sick_work_entry_type,
            (18, 9): sick_work_entry_type,
            (20, 9): sick_work_entry_type,
            (21, 9): sick_work_entry_type,
            (22, 9): sick_work_entry_type,
            (23, 9): credit_time_type,
            (24, 9): sick_work_entry_type,
            (25, 9): sick_work_entry_type,
            (28, 9): sick_work_entry_type,
            (29, 9): sick_work_entry_type,
            (30, 9): credit_time_type,
            (1, 10): sick_work_entry_type,
            (2, 10): sick_work_entry_type,
            (5, 10): sick_work_entry_type,
            (6, 10): sick_work_entry_type,
            (7, 10): credit_time_type,
            (8, 10): partial_sick_work_entry_type,
            (9, 10): partial_sick_work_entry_type,
            (9, 10): partial_sick_work_entry_type,
            (12, 10): partial_sick_work_entry_type,
            (13, 10): partial_sick_work_entry_type,
            (14, 10): credit_time_type,
            (15, 10): attendance,
            (16, 10): attendance,
            (19, 10): attendance,
            (20, 10): attendance,
            (21, 10): credit_time_type,
            (22, 10): attendance,
            (23, 10): attendance,
            (26, 10): attendance,
            (27, 10): attendance,
            (28, 10): credit_time_type,
            (29, 10): attendance,
            (30, 10): attendance,
            (31, 10): attendance,
        }

        for we in work_entries:
            self.assertEqual(
                we.work_entry_type_id,
                work_entries_expected_results[(we.date_start.day, we.date_start.month)],
                'On %s/%s, expected work entry type %s, got %s instead' % (we.date_start.day, we.date_start.month, work_entries_expected_results[(we.date_start.day, we.date_start.month)].name, we.work_entry_type_id.name))
        work_entries.action_validate()

        september_payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(september_payslip.worked_days_line_ids), 3)
        self.assertEqual(len(september_payslip.input_line_ids), 0)
        self.assertEqual(len(september_payslip.line_ids), 32)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('WORK100'), 489.23, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('LEAVE110'), 1630.77, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('WORK100'), 4.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('LEAVE110'), 13.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('LEAVE300'), 5.0, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('WORK100'), 30.4, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('LEAVE110'), 98.8, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('LEAVE300'), 38.0, places=2)

        payslip_results = {
            'BASIC': 2120.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2129.0,
            'ONSS': -278.26,
            'EmpBonus.1': 105.93,
            'ONSSTOTAL': 172.33,
            'ATN.CAR': 141.14,
            'GROSSIP': 2097.81,
            'IP.PART': -530.0,
            'GROSS': 1567.81,
            'P.P': -143.96,
            'P.P.DED': 35.11,
            'PPTOTAL': 108.85,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -13.27,
            'MEAL_V_EMP': -4.36,
            'REP.FEES': 150.0,
            'IP': 530.0,
            'IP.DED': -39.75,
            'NET': 1931.43,
            'REMUNERATION': 1590.0,
            'ONSSEMPLOYERBASIC': 532.68,
            'ONSSEMPLOYERFFE': 2.77,
            'ONSSEMPLOYERMFFE': 2.13,
            'ONSSEMPLOYERCPAE': 4.9,
            'ONSSEMPLOYERRESTREINT': 35.98,
            'ONSSEMPLOYERUNEMP': 2.13,
            'ONSSEMPLOYER': 580.58,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(september_payslip, payslip_results)

        october_payslip = self._generate_payslip(datetime.date(2020, 10, 1), datetime.date(2020, 10, 31))

        self.assertEqual(len(october_payslip.worked_days_line_ids), 4)
        self.assertEqual(len(october_payslip.input_line_ids), 0)
        self.assertEqual(len(october_payslip.line_ids), 32)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('LEAVE110'), 489.23, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('LEAVE214'), 0.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('WORK100'), 1141.54, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('LEAVE300'), 4.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('LEAVE110'), 4.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('LEAVE214'), 4.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('WORK100'), 10.0, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('LEAVE300'), 30.4, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('LEAVE110'), 30.4, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('LEAVE214'), 30.4, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('WORK100'), 76.0, places=2)

        payslip_results = {
            'BASIC': 1630.77,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 1639.77,
            'ONSS': -214.32,
            'EmpBonus.1': 85.93,
            'ONSSTOTAL': 128.39,
            'ATN.CAR': 141.14,
            'GROSSIP': 1652.52,
            'IP.PART': -407.69,
            'GROSS': 1244.83,
            'P.P': -55.55,
            'P.P.DED': 28.48,
            'PPTOTAL': 27.07,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -10.9,
            'REP.FEES': 150.0,
            'IP': 407.69,
            'IP.DED': -30.58,
            'NET': 1583.83,
            'REMUNERATION': 1223.08,
            'ONSSEMPLOYERBASIC': 410.27,
            'ONSSEMPLOYERFFE': 2.13,
            'ONSSEMPLOYERMFFE': 1.64,
            'ONSSEMPLOYERCPAE': 3.77,
            'ONSSEMPLOYERRESTREINT': 27.71,
            'ONSSEMPLOYERUNEMP': 1.64,
            'ONSSEMPLOYER': 447.17,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(october_payslip, payslip_results)

    def test_relapse_with_guaranteed_salary_credit_time(self):
        # Sick 2 days (1 - 2 september)
        # Back 1 week (3 - 18 september)
        # Sick 2.5 weeks (21 septembeer - 7 october)
        # No part time sick as there is at least 15 days between the 2 sick time offs
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2020, 1, 1),
            'date_end': datetime.date(2021, 9, 30),
            'wage': 2120.0,
            'wage_on_signature': 2120.0,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })

        sick_leave_1 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 2 Days',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2020, 9, 1),
            'request_date_to': datetime.date(2020, 9, 2),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 2,
        })
        sick_leave_1._compute_date_from_to()
        sick_leave_1 = self.env['hr.leave'].create(sick_leave_1._convert_to_write(sick_leave_1._cache))

        sick_leave_2 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 2.5 Weeks',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2020, 9, 21),
            'request_date_to': datetime.date(2020, 10, 7),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 13,
        })
        sick_leave_2._compute_date_from_to()
        sick_leave_2 = self.env['hr.leave'].create(sick_leave_2._convert_to_write(sick_leave_2._cache))

        (sick_leave_1 + sick_leave_2).action_validate()

        work_entries = self.employee.contract_id.generate_work_entries(datetime.date(2020, 9, 1), datetime.date(2020, 10, 31))

        attendance = self.env.ref('hr_work_entry.work_entry_type_attendance')
        sick_work_entry_type = self.env.ref('hr_work_entry_contract.work_entry_type_sick_leave')
        credit_time_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time')

        work_entries_expected_results = {
            (1, 9): sick_work_entry_type,
            (2, 9): credit_time_type,
            (3, 9): attendance,
            (4, 9): attendance,
            (7, 9): attendance,
            (8, 9): attendance,
            (9, 9): credit_time_type,
            (10, 9): attendance,
            (11, 9): attendance,
            (14, 9): attendance,
            (15, 9): attendance,
            (16, 9): credit_time_type,
            (17, 9): attendance,
            (18, 9): attendance,
            (20, 9): attendance,
            (21, 9): sick_work_entry_type,
            (22, 9): sick_work_entry_type,
            (23, 9): credit_time_type,
            (24, 9): sick_work_entry_type,
            (25, 9): sick_work_entry_type,
            (28, 9): sick_work_entry_type,
            (29, 9): sick_work_entry_type,
            (30, 9): credit_time_type,
            (1, 10): sick_work_entry_type,
            (2, 10): sick_work_entry_type,
            (5, 10): sick_work_entry_type,
            (6, 10): sick_work_entry_type,
            (7, 10): credit_time_type,
            (8, 10): attendance,
            (9, 10): attendance,
            (9, 10): attendance,
            (12, 10): attendance,
            (13, 10): attendance,
            (14, 10): credit_time_type,
            (15, 10): attendance,
            (16, 10): attendance,
            (19, 10): attendance,
            (20, 10): attendance,
            (21, 10): credit_time_type,
            (22, 10): attendance,
            (23, 10): attendance,
            (26, 10): attendance,
            (27, 10): attendance,
            (28, 10): credit_time_type,
            (29, 10): attendance,
            (30, 10): attendance,
            (31, 10): attendance,
        }

        for w in work_entries:
            self.assertEqual(w.work_entry_type_id, work_entries_expected_results.get((w.date_start.day, w.date_start.month)))
        work_entries.action_validate()

        september_payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(september_payslip.worked_days_line_ids), 3)
        self.assertEqual(len(september_payslip.input_line_ids), 0)
        self.assertEqual(len(september_payslip.line_ids), 32)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('WORK100'), 1263.85, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('LEAVE110'), 856.15, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('LEAVE300'), 5.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('WORK100'), 10.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('LEAVE110'), 7.0, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('LEAVE300'), 38.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('WORK100'), 76.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('LEAVE110'), 53.2, places=2)

        payslip_results = {
            'BASIC': 2120.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2129.0,
            'ONSS': -278.26,
            'EmpBonus.1': 105.93,
            'ONSSTOTAL': 172.33,
            'ATN.CAR': 141.14,
            'GROSSIP': 2097.81,
            'IP.PART': -530.0,
            'GROSS': 1567.81,
            'P.P': -143.96,
            'P.P.DED': 35.11,
            'PPTOTAL': 108.85,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -13.27,
            'MEAL_V_EMP': -10.9,
            'REP.FEES': 150.0,
            'IP': 530.0,
            'IP.DED': -39.75,
            'NET': 1924.89,
            'REMUNERATION': 1590.0,
            'ONSSEMPLOYERBASIC': 532.68,
            'ONSSEMPLOYERFFE': 2.77,
            'ONSSEMPLOYERMFFE': 2.13,
            'ONSSEMPLOYERCPAE': 4.9,
            'ONSSEMPLOYERRESTREINT': 35.98,
            'ONSSEMPLOYERUNEMP': 2.13,
            'ONSSEMPLOYER': 580.58,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(september_payslip, payslip_results)

        october_payslip = self._generate_payslip(datetime.date(2020, 10, 1), datetime.date(2020, 10, 31))

        self.assertEqual(len(october_payslip.worked_days_line_ids), 3)
        self.assertEqual(len(october_payslip.input_line_ids), 0)
        self.assertEqual(len(october_payslip.line_ids), 32)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('LEAVE110'), 489.23, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('WORK100'), 1630.77, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('LEAVE300'), 4.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('LEAVE110'), 4.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('WORK100'), 14.0, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('LEAVE300'), 30.4, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('LEAVE110'), 30.4, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('WORK100'), 106.4, places=2)

        payslip_results = {
            'BASIC': 2120.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2129.0,
            'ONSS': -278.26,
            'EmpBonus.1': 105.93,
            'ONSSTOTAL': 172.33,
            'ATN.CAR': 141.14,
            'GROSSIP': 2097.81,
            'IP.PART': -530.0,
            'GROSS': 1567.81,
            'P.P': -143.96,
            'P.P.DED': 35.11,
            'PPTOTAL': 108.85,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -13.27,
            'MEAL_V_EMP': -15.26,
            'REP.FEES': 150.0,
            'IP': 530.0,
            'IP.DED': -39.75,
            'NET': 1920.53,
            'REMUNERATION': 1590.0,
            'ONSSEMPLOYERBASIC': 532.68,
            'ONSSEMPLOYERFFE': 2.77,
            'ONSSEMPLOYERMFFE': 2.13,
            'ONSSEMPLOYERCPAE': 4.9,
            'ONSSEMPLOYERRESTREINT': 35.98,
            'ONSSEMPLOYERUNEMP': 2.13,
            'ONSSEMPLOYER': 580.58,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(october_payslip, payslip_results)

    def test_sick_more_than_30_days_credit_time(self):
        # Sick 1 september - 15 october
        # Part time sick from the 31th day
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2020, 1, 1),
            'date_end': datetime.date(2021, 9, 30),
            'wage': 2120.0,
            'wage_on_signature': 2120.0,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })

        sick_leave = self.env['hr.leave'].new({
            'name': 'Sick Time Off 33 Days',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2020, 9, 1),
            'request_date_to': datetime.date(2020, 10, 15),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 33,
        })
        sick_leave._compute_date_from_to()
        sick_leave = self.env['hr.leave'].create(sick_leave._convert_to_write(sick_leave._cache))
        sick_leave.action_validate()

        work_entries = self.employee.contract_id.generate_work_entries(datetime.date(2020, 9, 1), datetime.date(2020, 10, 31))

        attendance = self.env.ref('hr_work_entry.work_entry_type_attendance')
        sick_work_entry_type = self.env.ref('hr_work_entry_contract.work_entry_type_sick_leave')
        partial_sick_work_entry_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_part_sick')
        credit_time_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time')

        work_entries_expected_results = {
            (1, 9): sick_work_entry_type,
            (2, 9): credit_time_type,
            (3, 9): sick_work_entry_type,
            (4, 9): sick_work_entry_type,
            (7, 9): sick_work_entry_type,
            (8, 9): sick_work_entry_type,
            (9, 9): credit_time_type,
            (10, 9): sick_work_entry_type,
            (11, 9): sick_work_entry_type,
            (14, 9): sick_work_entry_type,
            (15, 9): sick_work_entry_type,
            (16, 9): credit_time_type,
            (17, 9): sick_work_entry_type,
            (18, 9): sick_work_entry_type,
            (20, 9): sick_work_entry_type,
            (21, 9): sick_work_entry_type,
            (22, 9): sick_work_entry_type,
            (23, 9): credit_time_type,
            (24, 9): sick_work_entry_type,
            (25, 9): sick_work_entry_type,
            (28, 9): sick_work_entry_type,
            (29, 9): sick_work_entry_type,
            (30, 9): credit_time_type,
            (1, 10): partial_sick_work_entry_type,
            (2, 10): partial_sick_work_entry_type,
            (5, 10): partial_sick_work_entry_type,
            (6, 10): partial_sick_work_entry_type,
            (7, 10): credit_time_type,
            (8, 10): partial_sick_work_entry_type,
            (9, 10): partial_sick_work_entry_type,
            (9, 10): partial_sick_work_entry_type,
            (12, 10): partial_sick_work_entry_type,
            (13, 10): partial_sick_work_entry_type,
            (14, 10): credit_time_type,
            (15, 10): partial_sick_work_entry_type,
            (16, 10): attendance,
            (19, 10): attendance,
            (20, 10): attendance,
            (21, 10): credit_time_type,
            (22, 10): attendance,
            (23, 10): attendance,
            (26, 10): attendance,
            (27, 10): attendance,
            (28, 10): credit_time_type,
            (29, 10): attendance,
            (30, 10): attendance,
            (31, 10): attendance,
        }

        for we in work_entries:
            self.assertEqual(
                we.work_entry_type_id,
                work_entries_expected_results[(we.date_start.day, we.date_start.month)],
                'On %s/%s, expected work entry type %s, got %s instead' % (we.date_start.day, we.date_start.month, work_entries_expected_results[(we.date_start.day, we.date_start.month)].name, we.work_entry_type_id.name))

        september_payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(september_payslip.worked_days_line_ids), 2)
        self.assertEqual(len(september_payslip.input_line_ids), 0)
        self.assertEqual(len(september_payslip.line_ids), 32)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_amount('LEAVE110'), 2120.0, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('LEAVE300'), 5.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_days('LEAVE110'), 17.0, places=2)

        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('LEAVE300'), 38.0, places=2)
        self.assertAlmostEqual(september_payslip._get_worked_days_line_number_of_hours('LEAVE110'), 129.2, places=2)

        payslip_results = {
            'BASIC': 2120.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2129.0,
            'ONSS': -278.26,
            'EmpBonus.1': 105.93,
            'ONSSTOTAL': 172.33,
            'ATN.CAR': 141.14,
            'GROSSIP': 2097.81,
            'IP.PART': -530.0,
            'GROSS': 1567.81,
            'P.P': -143.96,
            'P.P.DED': 35.11,
            'PPTOTAL': 108.85,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -13.27,
            'MEAL_V_EMP': 0.0,
            'REP.FEES': 150.0,
            'IP': 530.0,
            'IP.DED': -39.75,
            'NET': 1935.79,
            'REMUNERATION': 1590.0,
            'ONSSEMPLOYERBASIC': 532.68,
            'ONSSEMPLOYERFFE': 2.77,
            'ONSSEMPLOYERMFFE': 2.13,
            'ONSSEMPLOYERCPAE': 4.9,
            'ONSSEMPLOYERRESTREINT': 35.98,
            'ONSSEMPLOYERUNEMP': 2.13,
            'ONSSEMPLOYER': 580.58,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(september_payslip, payslip_results)

        october_payslip = self._generate_payslip(datetime.date(2020, 10, 1), datetime.date(2020, 10, 31))

        self.assertEqual(len(october_payslip.worked_days_line_ids), 3)
        self.assertEqual(len(october_payslip.input_line_ids), 0)
        self.assertEqual(len(october_payslip.line_ids), 32)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('LEAVE214'), 0.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_amount('WORK100'), 1019.23, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('LEAVE300'), 4.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('LEAVE214'), 9.0, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_days('WORK100'), 9.0, places=2)

        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('LEAVE300'), 30.4, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('LEAVE214'), 68.4, places=2)
        self.assertAlmostEqual(october_payslip._get_worked_days_line_number_of_hours('WORK100'), 68.4, places=2)

        payslip_results = {
            'BASIC': 1019.23,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 1028.23,
            'ONSS': -134.39,
            'EmpBonus.1': 60.92,
            'ONSSTOTAL': 73.47,
            'ATN.CAR': 141.14,
            'GROSSIP': 1095.91,
            'IP.PART': -254.81,
            'GROSS': 841.1,
            'P.P': 0.0,
            'P.P.DED': 0.0,
            'PPTOTAL': 0.0,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -9.81,
            'REP.FEES': 150.0,
            'IP': 254.81,
            'IP.DED': -19.11,
            'NET': 1066.84,
            'REMUNERATION': 764.42,
            'ONSSEMPLOYERBASIC': 257.26,
            'ONSSEMPLOYERFFE': 1.34,
            'ONSSEMPLOYERMFFE': 1.03,
            'ONSSEMPLOYERCPAE': 2.36,
            'ONSSEMPLOYERRESTREINT': 17.38,
            'ONSSEMPLOYERUNEMP': 1.03,
            'ONSSEMPLOYER': 280.4,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(october_payslip, payslip_results)

    def test_small_unemployment(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 14, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 14, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_small_unemployment').id
        }])

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 30)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE205'), 122.31, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2527.69, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE205'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 21.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE205'), 7.6, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 159.6, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'ATN.CAR': 141.14,
            'GROSSIP': 2452.61,
            'IP.PART': -662.5,
            'GROSS': 1790.11,
            'P.P': -240.26,
            'PPTOTAL': 240.26,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -22.89,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2115.97,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_small_unemployment_1_week(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 14, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 18, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_small_unemployment').id
        }, {
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 9, 21, 6, 0, 0),
            'date_to': datetime.datetime(2020, 9, 22, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_small_unemployment').id
        }])

        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 30)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE205'), 856.15, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 1793.85, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE205'), 7.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 15.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE205'), 53.2, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 114.0, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'ATN.CAR': 141.14,
            'GROSSIP': 2452.61,
            'IP.PART': -662.5,
            'GROSS': 1790.11,
            'P.P': -240.26,
            'PPTOTAL': 240.26,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -16.35,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2122.51,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_full_time_credit_time_atn_negative_net(self):
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_0_hours_per_week.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2020, 8, 1),
            'date_end': datetime.date(2020, 11, 30),
            'wage': 0.0,
            'wage_on_signature': 0.0,
            'time_credit': True,
            'work_time_rate': 0,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })
        payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 30)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 22.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 167.2, places=2)

        payslip_results = {
            'BASIC': 0.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 9.0,
            'ONSS': -1.18,
            'ONSSTOTAL': 1.18,
            'ATN.CAR': 141.14,
            'GROSSIP': 148.97,
            'IP.PART': 0.0,
            'GROSS': 148.97,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': 0.0,
            'REP.FEES': 0.0,
            'IP': 0.0,
            'IP.DED': 0.0,
            'NET': -1.18,
            'REMUNERATION': 0.0,
            'ONSSEMPLOYERBASIC': 2.25,
            'ONSSEMPLOYERFFE': 0.01,
            'ONSSEMPLOYERMFFE': 0.01,
            'ONSSEMPLOYERCPAE': 0.02,
            'ONSSEMPLOYERRESTREINT': 0.15,
            'ONSSEMPLOYERUNEMP': 0.01,
            'ONSSEMPLOYER': 2.45,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_training_time_off_above_threshold(self):
        self.leaves = self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_thurday_off.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2020, 5, 4, 5, 0, 0),
            'date_to': datetime.datetime(2020, 5, 4, 16, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }, {
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_thurday_off.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2020, 5, 5, 5, 0, 0),
            'date_to': datetime.datetime(2020, 5, 5, 16, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }, {
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_thurday_off.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 5, 6, 6, 0, 0),
            'date_to': datetime.datetime(2020, 5, 6, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_training_time_off').id
        }])

        self.car.write({
            'first_contract_date': datetime.date(2014, 6, 10),
            'co2': 98.0,
            'car_value': 25686.82,
            'acquisition_date': datetime.date(2014, 6, 10)
        })

        self.vehicle_contract.write({
            'name': "Test Contract",
            'vehicle_id': self.car.id,
            'company_id': self.env.company.id,
            'start_date': datetime.date(2020, 11, 30),
            'expiration_date': datetime.date(2021, 11, 30),
            'state': "open",
            'cost_generated': 0.0,
            'cost_frequency': "monthly",
            'recurring_cost_amount_depreciated': 405.315
        })

        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_thurday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2020, 4, 1),
            'date_end': datetime.date(2020, 11, 30),
            'wage': 3608.66,
            'wage_on_signature': 3608.66,
            'fuel_card': 200.0,
            'mobile': 0.0,
            'ip': True,
            'ip_wage_rate': 25.0,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })

        payslip = self._generate_payslip(datetime.date(2020, 5, 1), datetime.date(2020, 5, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 4)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 28)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE500'), 416.38, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2984.08, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE260'), 135.14, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE500'), 2.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 14.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 4.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE260'), 1.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE500'), 15.2, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 106.4, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 30.4, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE260'), 7.6, places=2)

        payslip_results = {
            'BASIC': 3535.6,
            'ATN.INT': 5.0,
            'SALARY': 3540.6,
            'ONSS': -462.76,
            'ONSSTOTAL': 462.76,
            'ATN.CAR': 111.67,
            'GROSSIP': 3189.51,
            'IP.PART': -883.9,
            'GROSS': 2305.61,
            'P.P': -470.71,
            'PPTOTAL': 470.71,
            'ATN.CAR.2': -111.67,
            'ATN.INT.2': -5.0,
            'M.ONSS': -33.4,
            'MEAL_V_EMP': -15.26,
            'REP.FEES': 150.0,
            'IP': 883.9,
            'IP.DED': -66.29,
            'NET': 2637.18,
            'REMUNERATION': 2651.7,
            'ONSSEMPLOYERBASIC': 885.86,
            'ONSSEMPLOYERFFE': 4.6,
            'ONSSEMPLOYERMFFE': 3.54,
            'ONSSEMPLOYERCPAE': 8.14,
            'ONSSEMPLOYERRESTREINT': 59.84,
            'ONSSEMPLOYERUNEMP': 3.54,
            'ONSSEMPLOYER': 965.52,
            'CO2FEE': 30.73,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_training_time_off_below_threshold(self):
        self.leaves = self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_thurday_off.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2020, 5, 4, 5, 0, 0),
            'date_to': datetime.datetime(2020, 5, 4, 16, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }, {
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_thurday_off.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2020, 5, 5, 5, 0, 0),
            'date_to': datetime.datetime(2020, 5, 5, 16, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }, {
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_thurday_off.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2020, 5, 6, 6, 0, 0),
            'date_to': datetime.datetime(2020, 5, 6, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_training_time_off').id
        }])

        self.car.write({
            'first_contract_date': datetime.date(2014, 6, 10),
            'co2': 98.0,
            'car_value': 25686.82,
            'acquisition_date': datetime.date(2014, 6, 10)
        })

        self.vehicle_contract.write({
            'name': "Test Contract",
            'vehicle_id': self.car.id,
            'company_id': self.env.company.id,
            'start_date': datetime.date(2020, 11, 30),
            'expiration_date': datetime.date(2021, 11, 30),
            'state': "open",
            'cost_generated': 0.0,
            'cost_frequency': "monthly",
            'recurring_cost_amount_depreciated': 405.315
        })

        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_thurday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2020, 4, 1),
            'date_end': datetime.date(2020, 11, 30),
            'wage': 2650,
            'wage_on_signature': 2650,
            'fuel_card': 200.0,
            'mobile': 0.0,
            'ip': True,
            'ip_wage_rate': 25.0,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })

        payslip = self._generate_payslip(datetime.date(2020, 5, 1), datetime.date(2020, 5, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 4)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 28)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE260'), 152.88, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE500'), 305.77, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2191.35, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE260'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE500'), 2.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 14.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 4.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE260'), 7.6, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE500'), 15.2, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 106.4, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 30.4, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'SALARY': 2655.0,
            'ONSS': -347.01,
            'ONSSTOTAL': 347.01,
            'ATN.CAR': 111.67,
            'GROSSIP': 2419.66,
            'IP.PART': -662.5,
            'GROSS': 1757.16,
            'P.P': -227.42,
            'PPTOTAL': 227.42,
            'ATN.CAR.2': -111.67,
            'ATN.INT.2': -5.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -15.26,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2136.97,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 664.28,
            'ONSSEMPLOYERFFE': 3.45,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.11,
            'ONSSEMPLOYERRESTREINT': 44.87,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 724.02,
            'CO2FEE': 30.73,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_variable_revenues(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2020, 9, 23, 5, 0, 0),
            'date_to': datetime.datetime(2020, 9, 23, 16, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }])

        self.contract.commission_on_target = 1000
        self.contract.date_start = datetime.date(2020, 1, 15)

        self.employee.first_contract_date = datetime.date(2020, 1, 15)

        commission_payslip = self._generate_payslip(datetime.date(2020, 3, 1), datetime.date(2020, 3, 31))

        self.env['hr.payslip.input'].create([{
            'name': "Test Input",
            'payslip_id': commission_payslip.id,
            'sequence': 10,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
            'amount': 8484.0
        }])

        work_entries = self.contract.generate_work_entries(datetime.date(2020, 3, 1), datetime.date(2020, 3, 31))
        work_entries.action_validate()
        commission_payslip.input_line_ids.amount = 8484.0
        commission_payslip.compute_sheet()
        commission_payslip.action_payslip_done()

        self.assertEqual(len(commission_payslip.worked_days_line_ids), 1)
        self.assertEqual(len(commission_payslip.input_line_ids), 1)
        self.assertEqual(len(commission_payslip.line_ids), 31)

        payslip_results = {
            'BASIC': 2650.0,
            'COMMISSION': 8484.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 11143.0,
            'ONSS': -1456.39,
            'ONSSTOTAL': 1456.39,
            'ATN.CAR': 141.14,
            'GROSSIP': 9827.75,
            'IP.PART': -662.5,
            'GROSS': 9165.25,
            'P.P': -4064.03,
            'PPTOTAL': 4064.03,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -23.98,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 5666.25,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 2787.98,
            'ONSSEMPLOYERCPAE': 25.63,
            'ONSSEMPLOYERFFE': 14.49,
            'ONSSEMPLOYERMFFE': 11.14,
            'ONSSEMPLOYERRESTREINT': 188.32,
            'ONSSEMPLOYERUNEMP': 11.14,
            'ONSSEMPLOYER': 3038.7,
            'CO2FEE': 20.92,
        }

        self._validate_payslip(commission_payslip, payslip_results)

        classic_payslip = self._generate_payslip(datetime.date(2020, 9, 1), datetime.date(2020, 9, 30))

        self.assertEqual(len(classic_payslip.worked_days_line_ids), 3)
        self.assertEqual(len(classic_payslip.input_line_ids), 0)
        self.assertEqual(len(classic_payslip.line_ids), 30)

        self.assertAlmostEqual(classic_payslip._get_worked_days_line_amount('LEAVE500'), 122.31, places=2)
        self.assertAlmostEqual(classic_payslip._get_worked_days_line_amount('WORK100'), 2527.69, places=2)
        self.assertAlmostEqual(classic_payslip._get_worked_days_line_amount('LEAVE1731'), 50.9, places=2)

        self.assertAlmostEqual(classic_payslip._get_worked_days_line_number_of_days('LEAVE500'), 1.0, places=2)
        self.assertAlmostEqual(classic_payslip._get_worked_days_line_number_of_days('WORK100'), 21.0, places=2)
        self.assertAlmostEqual(classic_payslip._get_worked_days_line_number_of_days('LEAVE1731'), 0.0, places=2)

        self.assertAlmostEqual(classic_payslip._get_worked_days_line_number_of_hours('LEAVE500'), 7.6, places=2)
        self.assertAlmostEqual(classic_payslip._get_worked_days_line_number_of_hours('WORK100'), 159.6, places=2)
        self.assertAlmostEqual(classic_payslip._get_worked_days_line_number_of_hours('LEAVE1731'), 0.0, places=2)

        payslip_result = {
            'BASIC': 2700.9,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2709.9,
            'ONSS': -354.18,
            'ATN.CAR': 141.14,
            'GROSSIP': 2496.86,
            'IP.PART': -675.23,
            'GROSS': 1821.63,
            'P.P': -253.1,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -24.22,
            'MEAL_V_EMP': -22.89,
            'REP.FEES': 150.0,
            'IP': 675.23,
            'IP.DED': -50.64,
            'NET': 2145.87,
        }
        error = []
        line_values = classic_payslip._get_line_values(payslip_result.keys())
        for code, value in payslip_result.items():
            payslip_line_value = line_values[code][classic_payslip.id]['total']
            if float_compare(payslip_line_value, value, 2):
                error.append("Computed line %s should have an amount = %s instead of %s" % (code, value, payslip_line_value))
        self.assertEqual(len(error), 0, '\n' + '\n'.join(error))

    def test_credit_time_keep_old_time_off(self):
        # Test Case: When setting a credit time, we change the calendar
        # and thus it could be possible to loose the time off that were planned
        # and validated before the contract change.
        # Ensure that the time off are not lost.

        sick_time_off = self.env['hr.leave'].new({
            'name': 'Maternity Time Off : 15 weeks',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2020, 11, 9),
            'request_date_to': datetime.date(2020, 11, 10),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 2,
        })
        sick_time_off._compute_date_from_to()
        sick_time_off = self.env['hr.leave'].create(sick_time_off._convert_to_write(sick_time_off._cache))
        sick_time_off.action_validate()

        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week,
            'time_credit': True,
            'work_time_rate': "0.8",
            'wage': 2120.0,
            'wage_on_signature': 2120.0,
            'date_start': datetime.date(2020, 9, 16),
            'date_end': datetime.date(2020, 12, 31),
        })

        work_entries = self.contract.generate_work_entries(datetime.date(2020, 11, 1), datetime.date(2020, 11, 30))
        sick_work_entries = work_entries.filtered(lambda we: we.work_entry_type_id == self.sick_time_off_type.work_entry_type_id)
        self.assertEqual(len(sick_work_entries), 4)

    def test_accounting_entries(self):
        # Test case: Create 2 payslips (1 classic / 1 low salary)
        # Generate and validate the accounting entries

        # 1rst contract
        self.contract.write({
            'transport_mode_private_car': True,
            'date_generated_from': datetime.datetime(2020, 12, 1, 0, 0, 0),
            'date_generated_to': datetime.datetime(2020, 12, 1, 0, 0, 0),
        })

        # Second contract
        second_employee = self.env['hr.employee'].create([{
            'name': "Test Employee",
            'resource_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'marital': "single",
            'km_home_work': 75,
        }])

        second_contract = self.env['hr.contract'].create([{
            'name': "Contract For Payslip Test",
            'employee_id': second_employee.id,
            'resource_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_generated_from': datetime.datetime(2020, 12, 1, 0, 0, 0),
            'date_generated_to': datetime.datetime(2020, 12, 1, 0, 0, 0),
            'car_id': False,
            'structure_type_id': self.env.ref('hr_contract.structure_type_employee_cp200').id,
            'date_start': datetime.date(2018, 12, 31),
            'wage': 2000.0,
            'wage_on_signature': 2000.0,
            'state': "open",
            'transport_mode_car': False,
            'transport_mode_private_car': True,
            'fuel_card': 150.0,
            'internet': 38.0,
            'representation_fees': 150.0,
            'mobile': 30.0,
            'meal_voucher_amount': 7.45,
            'eco_checks': 250.0,
            'ip_wage_rate': 25.0,
            'ip': True,
        }])

        # Generate Batch / payslips
        self.contract.generate_work_entries(datetime.date(2020, 12, 1), datetime.date(2020, 12, 31))
        payslip_run_id = self.env['hr.payslip.employees'].with_context(
            default_date_start='2020-12-01',
            default_date_end='2020-12-31',
            allowed_company_ids=self.env.company.ids,
        ).create({}).compute_sheet()['res_id']
        payslip_run = self.env['hr.payslip.run'].browse(payslip_run_id)

        payslips = payslip_run.slip_ids
        self.assertEqual(len(payslips), 2)

        payslip_1 = payslips.filtered(lambda p: p.employee_id == self.employee)
        self.assertEqual(len(payslip_1.worked_days_line_ids), 1)
        self.assertEqual(len(payslip_1.input_line_ids), 0)
        self.assertEqual(len(payslip_1.line_ids), 28)
        self.assertAlmostEqual(payslip_1._get_worked_days_line_amount('WORK100'), 2650.0, places=2)
        self.assertAlmostEqual(payslip_1._get_worked_days_line_number_of_days('WORK100'), 23.0, places=2)
        self.assertAlmostEqual(payslip_1._get_worked_days_line_number_of_hours('WORK100'), 174.8, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'GROSSIP': 2311.47,
            'IP.PART': -662.5,
            'GROSS': 1648.97,
            'P.P': -176.06,
            'PPTOTAL': 176.06,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -25.07,
            'CAR.PRIV': 98.5,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2276.49,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
        }
        self._validate_payslip(payslip_1, payslip_results)
        # ================================================ #
        #         Accounting entries for slip 1            #
        # ================================================ #
        # Basic salary 2650

        # Account   Formula                                                     Debit       Credit
        # 620200    Remuneration: Basic_Salary - IP                            1987.5
        # 453000    Withholding Taxes  Precompte - low salary bonus                         208.16

        # 643000    IP                                                          662.5
        # 453000    IP Deduction                                                             43.17

        # 454000    ONSS worker - Employment Bonus                                          347.53
        # 454000    ONSS Misceleneous                                                        23.66

        # 620200    Private Car                                                  98.5
        # 620200    Frais de rep                                                  150

        # 743000    Meal vouchers retenue                                                    25.07
        # 455000    Remunration dues = NET                                                 2193.13

        # 454000    ONSS Employer                                                           725.11
        # 621000    ONSS Employer                                              725.11
        # ----------------------------------------------------------------------------------------
        # BALANCE                                                             3620.15      3620.15

        payslip_2 = payslips.filtered(lambda p: p.employee_id == second_employee)

        self.assertEqual(len(payslip_2.worked_days_line_ids), 1)
        self.assertEqual(len(payslip_2.input_line_ids), 0)
        self.assertEqual(len(payslip_2.line_ids), 30)

        self.assertAlmostEqual(payslip_2._get_worked_days_line_amount('WORK100'), 2000.0, places=2)
        self.assertAlmostEqual(payslip_2._get_worked_days_line_number_of_days('WORK100'), 23.0, places=2)
        self.assertAlmostEqual(payslip_2._get_worked_days_line_number_of_hours('WORK100'), 174.8, places=2)

        payslip_results = {
            'BASIC': 2000.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2009.0,
            'ONSS': -262.58,
            'EmpBonus.1': 132.26,
            'ONSSTOTAL': 130.32,
            'GROSSIP': 1878.68,
            'IP.PART': -500.0,
            'GROSS': 1378.68,
            'P.P': -81.36,
            'P.P.DED': 43.83,
            'PPTOTAL': 37.53,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -4.15,
            'MEAL_V_EMP': -25.07,
            'CAR.PRIV': 98.5,
            'REP.FEES': 150.0,
            'IP': 500.0,
            'IP.DED': -37.5,
            'NET': 2013.93,
            'REMUNERATION': 1500.0,
            'ONSSEMPLOYERBASIC': 502.65,
            'ONSSEMPLOYERFFE': 2.61,
            'ONSSEMPLOYERMFFE': 2.01,
            'ONSSEMPLOYERCPAE': 4.62,
            'ONSSEMPLOYERRESTREINT': 33.95,
            'ONSSEMPLOYERUNEMP': 2.01,
            'ONSSEMPLOYER': 547.85,
        }
        self._validate_payslip(payslip_2, payslip_results)
        # ================================================ #
        #         Accounting entries for slip 2            #
        # ================================================ #
        # Basic salary 2000

        # Account   Formula                                                     Debit       Credit
        # 620200    Remuneration: Basic_Salary - IP                              1500
        # 453000    Withholding Taxes  Precompte - low salary bonus                         57.59

        # 643000    IP                                                            500
        # 453000    IP Deduction                                                             32.58

        # 454000    ONSS worker - Employment Bonus                                          130.32
        # 454000    ONSS Misceleneous                                                         4.15

        # 620200    Private Car                                                  98.5
        # 620200    Frais de rep                                                  150

        # 743000    Meal vouchers retenue                                                    25.07
        # 455000    Remunration dues = NET                                                 1949.83

        # 454000    ONSS Employer                                                           547.85
        # 621000    ONSS Employer                                              547.85
        # ----------------------------------------------------------------------------------------
        # BALANCE                                                             2793.74      2793.74

        # Generate accounting entries
        payslip_run.action_validate()
        account_move = payslip_1.move_id
        move_lines = account_move.line_ids

        balance = 6419.96
        move_line_results = [
            ('620200', 'debit', 3487.5),        # remuneration
            ('453000', 'credit', 213.59),       # PP
            ('643000', 'debit', 1162.5),        # IP
            ('453000', 'credit', 87.19),        # IP DED
            ('454000', 'credit', 477.85),       # ONSS - Emp Bonus
            ('454000', 'credit', 27.81),        # Misc ONSS
            ('620200', 'debit', 197),           # Private Car
            ('620200', 'debit', 300),           # Representation Fees
            ('743000', 'credit', 50.14),        # Meal vouchers
            ('455000', 'credit', 4290.42),      # NET
            ('454000', 'credit', 1272.96),      # ONSS Employer
            ('621000', 'debit', 1272.96),       # ONSS Employer
        ]

        # ================================================ #
        #         Accounting entries for Batch             #
        # ================================================ #
        # Account   Formula                                                     Debit       Credit
        # 620200    Remuneration: Basic_Salary - IP                            3487.5
        # 453000    Withholding Taxes  Precompte - low salary bonus                         372.49

        # 643000    IP                                                         1162.5
        # 453000    IP Deduction                                                             87.19

        # 454000    ONSS worker - Employment Bonus                                          477.85
        # 454000    ONSS Misceleneous                                                        27.81

        # 620200    Private Car                                                   197
        # 620200    Frais de rep                                                  300

        # 743000    Meal vouchers retenue                                                    50.14
        # 455000    Remunration dues = NET                                                 4131.52

        # 454000    ONSS Employer                                                          1272.96
        # 621000    ONSS Employer                                             1272.96
        # ----------------------------------------------------------------------------------------
        # BALANCE                                                             6419.96      6419.96

        self.assertEqual(len(move_lines), 12)
        self.assertAlmostEqual(sum(l.debit for l in move_lines), balance, places=2)
        self.assertAlmostEqual(sum(l.credit for l in move_lines), balance, places=2)
        self._validate_move_lines(move_lines, move_line_results)

    def test_long_term_sick_leave(self):
        public_holiday = self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2020, 3, 17, 6, 0, 0),
            'date_to': datetime.datetime(2020, 3, 17, 18, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }])

        long_term_sick = self.env['hr.leave'].new({
            'name': 'Long Term Sick',
            'employee_id': self.employee.id,
            'holiday_status_id': self.long_term_sick_time_off_type.id,
            'request_date_from': datetime.date(2020, 3, 1),
            'request_date_to': datetime.date(2020, 3, 31),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 22,
        })
        long_term_sick._compute_date_from_to()
        long_term_sick = self.env['hr.leave'].create(long_term_sick._convert_to_write(long_term_sick._cache))
        long_term_sick.action_validate()

        payslip = self._generate_payslip(datetime.date(2020, 3, 1), datetime.date(2020, 3, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 30)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE280'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE280'), 22.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE280'), 167.2, places=2)

        payslip_results = {
            'BASIC': 0.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 9.0,
            'ONSS': -1.18,
            'ONSSTOTAL': 1.18,
            'ATN.CAR': 141.14,
            'GROSSIP': 148.97,
            'IP.PART': 0.0,
            'GROSS': 148.97,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'ATN.CAR.2': -141.14,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': 0.0,
            'REP.FEES': 0.0,
            'IP': 0.0,
            'IP.DED': 0.0,
            'NET': -1.18,
            'REMUNERATION': 0.0,
            'ONSSEMPLOYERBASIC': 2.25,
            'ONSSEMPLOYERFFE': 0.01,
            'ONSSEMPLOYERMFFE': 0.01,
            'ONSSEMPLOYERCPAE': 0.02,
            'ONSSEMPLOYERRESTREINT': 0.15,
            'ONSSEMPLOYERUNEMP': 0.01,
            'ONSSEMPLOYER': 2.45,
            'CO2FEE': 20.92,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_commissions_with_low_salary_no_employment_bonus(self):
        self.contract.write({
            'wage_on_signature': 2300,
            'ip': False,
        })

        payslip = self._generate_payslip(datetime.date(2021, 1, 1), datetime.date(2021, 1, 31))

        self.env['hr.payslip.input'].create([{
            'name': "Commissions",
            'payslip_id': payslip.id,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
            'amount': 3000.0
        }])
        payslip.compute_sheet()

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 1)
        self.assertEqual(len(payslip.line_ids), 27)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2300.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 21.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 159.6, places=2)

        payslip_results = {
            'BASIC': 2300.0,
            'COMMISSION': 3000.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 5309.0,
            'ONSS': -693.89,
            'ONSSTOTAL': 693.89,
            'ATN.CAR': 150.53,
            'GROSS': 4765.65,
            'P.P': -1698.62,
            'PPTOTAL': 1698.62,
            'ATN.CAR.2': -150.53,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -19.81,
            'MEAL_V_EMP': -22.89,
            'REP.FEES': 150.0,
            'NET': 3014.8,
            'REMUNERATION': 2300.0,
            'ONSSEMPLOYERBASIC': 1328.31,
            'ONSSEMPLOYERCPAE': 12.21,
            'ONSSEMPLOYERFFE': 6.9,
            'ONSSEMPLOYERMFFE': 5.31,
            'ONSSEMPLOYERRESTREINT': 89.72,
            'ONSSEMPLOYERUNEMP': 5.31,
            'ONSSEMPLOYER': 1447.76,
            'CO2FEE': 21.16,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_private_car_capping_part_time(self):
        # Private car reimbursement should be 10 intead of 50 for employees working 1 day per week
        self.employee.km_home_work = 25

        self.contract.write({
            'transport_mode_car': False,
            'transport_mode_private_car': True,
            'resource_calendar_id': self.resource_calendar_1_5_monday_on.id,
            'ip': False,
        })

        payslip = self._generate_payslip(datetime.date(2021, 1, 1), datetime.date(2021, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 24)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2650.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 4.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 30.4, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'GROSS': 2311.47,
            'P.P': -473.38,
            'PPTOTAL': 473.38,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -4.36,
            'CAR.PRIV': 10.0,
            'REP.FEES': 150.0,
            'NET': 1961.07,
            'REMUNERATION': 2650.0,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_private_car_capping_part_time_1_time_off(self):
        # Private car reimbursement should be 10 intead of 50 for employees working 1 day per week
        self.employee.km_home_work = 25

        self.contract.write({
            'transport_mode_car': False,
            'transport_mode_private_car': True,
            'resource_calendar_id': self.resource_calendar_1_5_monday_on.id,
            'ip': False,
        })

        self.leaves = self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_1_5_monday_on.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2021, 1, 11, 7, 0, 0),
            'date_to': datetime.datetime(2021, 1, 11, 15, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_sick_leave').id
        }])
        payslip = self._generate_payslip(datetime.date(2021, 1, 1), datetime.date(2021, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 24)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE110'), 611.54, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2038.46, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE110'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 3.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE110'), 7.6, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 22.8, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'GROSS': 2311.47,
            'P.P': -473.38,
            'PPTOTAL': 473.38,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -3.27,
            'CAR.PRIV': 7.69,
            'REP.FEES': 150.0,
            'NET': 1959.85,
            'REMUNERATION': 2650.0,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_maternity_time_off_bank_holidays(self):
        # Maternity time off > bank holiday after 30 days
        # Means that the time off isn't paid by the employer after 30 days
        # but is paid in this case

        maternity_time_off = self.env['hr.leave'].new({
            'name': 'Maternity Time Off : 2 days',
            'employee_id': self.employee.id,
            'holiday_status_id': self.env.ref('l10n_be_hr_payroll.holiday_type_maternity').id,
            'request_date_from': datetime.date(2020, 12, 31),
            'request_date_to': datetime.date(2021, 1, 1),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 2,
        })
        maternity_time_off._compute_date_from_to()
        maternity_time_off = self.env['hr.leave'].create(maternity_time_off._convert_to_write(maternity_time_off._cache))

        self.env['resource.calendar.leaves'].create({
            'name': "Bank Holiday",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2021, 1, 1, 5, 0, 0),
            'date_to': datetime.datetime(2021, 1, 1, 18, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        })

        payslip = self._generate_payslip(datetime.date(2021, 1, 1), datetime.date(2021, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 30)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE500'), 122.31, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2527.69, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE500'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 20.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE500'), 7.6, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 152.0, places=2)

    def test_extra_legal_representation_fees(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2021, 1, 4, 7, 0, 0),
            'date_to': datetime.datetime(2021, 1, 4, 15, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_extra_legal').id
        }])

        payslip = self._generate_payslip(datetime.date(2021, 1, 1), datetime.date(2021, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 30)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE213'), 122.31, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2527.69, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE213'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 20.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE213'), 7.6, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 152.0, places=2)

        self.assertAlmostEqual(payslip._get_line_values(['REP.FEES'])['REP.FEES'][payslip.id]['total'], 150.0, places=2)

    def test_payslip_on_contract_cancelation(self):
        payslip = self._generate_payslip(datetime.date(2021, 1, 1), datetime.date(2021, 1, 31))
        self.contract.state = 'cancel'
        self.assertEqual(payslip.state, 'cancel')

    def test_credit_time_representation_fees(self):
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2020, 12, 1),
            'date_end': datetime.date(2021, 2, 28),
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })

        payslip = self._generate_payslip(datetime.date(2021, 1, 1), datetime.date(2021, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 30)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2650, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 17, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 4, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 129.2, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 30.4, places=2)

        self.assertAlmostEqual(payslip._get_line_values(['REP.FEES'])['REP.FEES'][payslip.id]['total'], 150, places=2)

    def test_credit_time_representation_fees_prorated(self):
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2020, 12, 1),
            'date_end': datetime.date(2021, 2, 28),
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
            'representation_fees': 400,
        })

        payslip = self._generate_payslip(datetime.date(2021, 1, 1), datetime.date(2021, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 31)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2650, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 17, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 4, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 129.2, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 30.4, places=2)

        self.assertAlmostEqual(payslip._get_line_values(['REP.FEES'])['REP.FEES'][payslip.id]['total'], 279.31, places=2)
        self.assertAlmostEqual(payslip._get_line_values(['REP.FEES.VOLATILE'])['REP.FEES.VOLATILE'][payslip.id]['total'], 372.15 - 279.31, places=2)

    def test_contractual_part_time_representation_fees(self):
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
        })

        payslip = self._generate_payslip(datetime.date(2021, 1, 1), datetime.date(2021, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 30)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2650.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 17.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 129.2, places=2)

        self.assertAlmostEqual(payslip._get_line_values(['REP.FEES'])['REP.FEES'][payslip.id]['total'], 150.0, places=2)

    def test_contractual_part_time_representation_fees_prorated(self):
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'representation_fees': 400,
        })

        payslip = self._generate_payslip(datetime.date(2021, 1, 1), datetime.date(2021, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 31)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 2650.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 17.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 129.2, places=2)

        self.assertAlmostEqual(payslip._get_line_values(['REP.FEES'])['REP.FEES'][payslip.id]['total'], 279.31, places=2)
        self.assertAlmostEqual(payslip._get_line_values(['REP.FEES.VOLATILE'])['REP.FEES.VOLATILE'][payslip.id]['total'], 375.86 - 279.31, places=2)

    def test_employment_bonus_half_days(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2021, 3, 1, 7, 0, 0),
            'date_to': datetime.datetime(2021, 3, 1, 11, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_sick_leave').id
        }])

        self.contract.write({
            'wage': 2500.0,
            'wage_on_signature': 2500.0,
        })

        payslip = self._generate_payslip(datetime.date(2021, 3, 1), datetime.date(2021, 3, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 3)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 32)

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].amount, 54.66, places=2)  # WORK100
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].amount, 60.73, places=2) # LEAVE110
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].amount, 2384.62, places=2) # WORK100

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].number_of_days, 1.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].number_of_days, 1.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].number_of_days, 22.0, places=2)

        self.assertAlmostEqual(payslip.worked_days_line_ids[0].number_of_hours, 3.6, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[1].number_of_hours, 4.0, places=2)
        self.assertAlmostEqual(payslip.worked_days_line_ids[2].number_of_hours, 167.2, places=2)

        payslip_results = {
            'BASIC': 2500.01,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2509.01,
            'ONSS': -327.93,
            'EmpBonus.1': 22.56,
            'ONSSTOTAL': 305.37,
            'ATN.CAR': 150.53,
            'GROSSIP': 2354.17,
            'IP.PART': -625.0,
            'GROSS': 1729.17,
            'P.P': -210.83,
            'P.P.DED': 7.48,
            'PPTOTAL': 203.35,
            'ATN.CAR.2': -150.53,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -22.01,
            'MEAL_V_EMP': -25.07,
            'REP.FEES': 150.0,
            'IP': 625.0,
            'IP.DED': -46.88,
            'NET': 2047.33,
            'REMUNERATION': 1875.01,
            'ONSSEMPLOYERBASIC': 627.75,
            'ONSSEMPLOYERFFE': 3.26,
            'ONSSEMPLOYERMFFE': 2.51,
            'ONSSEMPLOYERCPAE': 5.77,
            'ONSSEMPLOYERRESTREINT': 42.4,
            'ONSSEMPLOYERUNEMP': 2.51,
            'ONSSEMPLOYER': 684.21,
            'CO2FEE': 21.16,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_employee_departure(self):
        self._generate_departure_data()
        # - Holiday Pay N
        # - Holiday Pay N-1
        self.holiday_attest = self.env['hr.payslip.employee.depature.holiday.attests'].with_context(
            active_id=self.employee.id).create({})
        self.holiday_attest.write(
            self.holiday_attest.with_context(active_id=self.employee.id).default_get(self.holiday_attest._fields))
        holiday_pay_ids = self.holiday_attest.compute_termination_holidays()['domain'][0][2]
        holiday_pays = self.env['hr.payslip'].browse(holiday_pay_ids)

        struct_n1_id = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n1_holidays')
        struct_n_id = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n_holidays')

        self.holiday_pay_2019 = holiday_pays.filtered(lambda p: p.struct_id == struct_n1_id)
        self.holiday_pay_2020 = holiday_pays.filtered(lambda p: p.struct_id == struct_n_id)

        self.assertEqual(len(self.termination_fees.worked_days_line_ids), 0)
        self.assertEqual(len(self.termination_fees.input_line_ids), 16)
        self.assertEqual(len(self.termination_fees.line_ids), 41)
        payslip_results = {
            'BASIC2': 41344.0,
            'YEAREND_BONUS': 3200.0,
            'RESIDENCE': 0.0,
            'EXPATRIATE': 0.0,
            'MEAL_VOUCHER': 1399.21,
            'ECO_VOUCHER': 250.0,
            'VARIABLE_SALARY': 6000.0,
            'PAY_VARIABLE_SALARY': 920.4,
            'BENEFIT_IN_KIND': 0.0,
            'ADVANTAGE_ANY_KIND': 116.28,
            'ATN.CAR': 1693.71,
            'AMBULATORY_INSURANCE': 0.0,
            'HOSPITAL_INSURANCE': 0.0,
            'GROUP_INSURANCE': 0.0,
            'STOCK_OPTION': 1500.0,
            'SPECIFIC RULES': 0.0,
            'OTHER': 0.0,
            'ANNUAL_SALARY_REVALUED': 56423.61,
            'ND_MONTH': 0.0,
            'ND_WEEK': 9765.62,
            'ND_DAY': 0.0,
            'TOTALFEES': 9765.62,
            'ONSSEMPLOYERBASIC': 2443.36,
            'ONSSEMPLOYERCPAE': 22.46,
            'ONSSEMPLOYERFFE': 12.7,
            'ONSSEMPLOYERMFFE': 9.77,
            'ONSSEMPLOYERRESTREINT': 165.04,
            'ONSSEMPLOYERUNEMP': 9.77,
            'OUTPLACEMENT': 0.0,
            'ONSSEMPLOYER': 2663.09,
            'UNREASONABLE_DISMISSAL': 0.0,
            'NON_RESPECT_MOTIVATION': 0.0,
            'EMPLOYERCOST': 12428.71,
            'BASIC': 9765.62,
            'ONSS': -1276.37,
            'ONSSTOTAL': 1276.37,
            'GROSS': 8489.26,
            'P.P': -3694.88,
            'PPTOTAL': 3694.88,
            'REMUNERATION': 9765.62,
            'NET': 4794.38,
        }
        self._validate_payslip(self.termination_fees, payslip_results)

        self.holiday_pay_2020.write({
            'input_line_ids': [
                (0, 0, {
                    'input_type_id': self.env.ref('hr_payroll.input_reimbursement').id,
                    'amount': 50}),
                (0, 0, {
                    'input_type_id': self.env.ref('hr_payroll.input_deduction').id,
                    'amount': 20}),
                (0, 0, {
                    'input_type_id': self.env.ref('hr_payroll.input_attachment_salary').id,
                    'amount': 10}),
                (0, 0, {
                    'input_type_id': self.env.ref('hr_payroll.input_assignment_salary').id,
                    'amount': 10}),
                (0, 0, {
                    'input_type_id': self.env.ref('hr_payroll.input_child_support').id,
                    'amount': 10})
            ]
        })
        self.holiday_pay_2020.compute_sheet()
        self.assertEqual(len(self.holiday_pay_2020.worked_days_line_ids), 0)
        self.assertEqual(len(self.holiday_pay_2020.input_line_ids), 11)
        self.assertEqual(len(self.holiday_pay_2020.line_ids), 24)
        payslip_results = {
            'PAY_SIMPLE': 1137.92,
            'DOUBLE_BASIC': 1008.85,
            'PAY DOUBLE': 1008.85,
            'PAY DOUBLE COMPLEMENTARY': 129.07,
            'BASIC': 2275.84,
            'ONSS1': -148.73,
            'ONSS2': -131.86,
            'ONSSTOTAL': 280.58,
            'GROSS': 1995.26,
            'PROF_TAX': -725.08,
            'PPTOTAL': 725.08,
            'ASSIG_SALARY': -10.0,
            'ATTACH_SALARY': -10.0,
            'CHILD_SUPPORT': -10.0,
            'DEDUCTION': -20.0,
            'REIMBURSEMENT': 50.0,
            'NET': 1270.18,
            'ONSSEMPLOYERBASIC': 284.71,
            'ONSSEMPLOYERCPAE': 2.62,
            'ONSSEMPLOYERFFE': 1.48,
            'ONSSEMPLOYERMFFE': 1.14,
            'ONSSEMPLOYERRESTREINT': 19.23,
            'ONSSEMPLOYERUNEMP': 1.14,
            'ONSSEMPLOYER': 310.31,
        }
        self._validate_payslip(self.holiday_pay_2020, payslip_results)

        self.holiday_pay_2019.write({
            'input_line_ids': [
                (0, 0, {
                    'input_type_id': self.env.ref('hr_payroll.input_reimbursement').id,
                    'amount': 50}),
                (0, 0, {
                    'input_type_id': self.env.ref('hr_payroll.input_deduction').id,
                    'amount': 20}),
                (0, 0, {
                    'input_type_id': self.env.ref('hr_payroll.input_attachment_salary').id,
                    'amount': 10}),
                (0, 0, {
                    'input_type_id': self.env.ref('hr_payroll.input_assignment_salary').id,
                    'amount': 10}),
                (0, 0, {
                    'input_type_id': self.env.ref('hr_payroll.input_child_support').id,
                    'amount': 10})
            ]
        })
        self.holiday_pay_2019.compute_sheet()

        self.assertEqual(len(self.holiday_pay_2019.worked_days_line_ids), 0)
        self.assertEqual(len(self.holiday_pay_2019.input_line_ids), 11)
        self.assertEqual(len(self.holiday_pay_2019.line_ids), 32)
        payslip_results = {
            'BASIC_PAY_SIMPLE': 2508.58,
            'SIMPLE_PAY_DECEMBER': 0.0,
            'PAY_SIMPLE': 2508.58,
            'DOUBLE_BASIC': 2965.37,
            'EUROPEAN': 0.0,
            'DHALREADYPAID': 0.0,
            'DOUBLE_PAY_DECEMBER': 0.0,
            'PAY DOUBLE': 2965.37,
            'CDHBASIC': 379.39,
            'CDHALREADYPAID': 0.0,
            'COMP_DOUBLE_PAY_DECEMBER': 0.0,
            'PAY DOUBLE COMPLEMENTARY': 379.39,
            'BASIC': 5853.34,
            'ONSS1': -327.87,
            'ONSS2': -387.57,
            'ONSSTOTAL': 715.45,
            'GROSS': 5137.9,
            'PROF_TAX': -1867.11,
            'PPTOTAL': 1867.11,
            'ASSIG_SALARY': -10.0,
            'ATTACH_SALARY': -10.0,
            'CHILD_SUPPORT': -10.0,
            'DEDUCTION': -20.0,
            'REIMBURSEMENT': 50.0,
            'NET': 3270.79,
            'ONSSEMPLOYERBASIC': 627.65,
            'ONSSEMPLOYERCPAE': 5.77,
            'ONSSEMPLOYERFFE': 3.26,
            'ONSSEMPLOYERMFFE': 2.51,
            'ONSSEMPLOYERRESTREINT': 42.39,
            'ONSSEMPLOYERUNEMP': 2.51,
            'ONSSEMPLOYER': 684.09,
        }
        self._validate_payslip(self.holiday_pay_2019, payslip_results)

    def test_employee_departure_european_time_off(self):
        self._generate_departure_data()
        self.march_2019.state = 'verify'
        worked_days = self.march_2019.worked_days_line_ids.filtered(lambda wd: wd.code == 'LEAVE90')
        worked_days.work_entry_type_id = self.env.ref("l10n_be_hr_payroll.work_entry_type_european")
        worked_days._compute_amount()
        self.march_2019.state = 'done'
        # - Holiday Pay N
        # - Holiday Pay N-1
        self.holiday_attest = self.env['hr.payslip.employee.depature.holiday.attests'].with_context(
            active_id=self.employee.id).create({})
        self.holiday_attest.write(
            self.holiday_attest.with_context(active_id=self.employee.id).default_get(self.holiday_attest._fields))
        holiday_pay_ids = self.holiday_attest.compute_termination_holidays()['domain'][0][2]
        holiday_pays = self.env['hr.payslip'].browse(holiday_pay_ids)

        struct_n1_id = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n1_holidays')
        struct_n_id = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n_holidays')

        self.holiday_pay_2019 = holiday_pays.filtered(lambda p: p.struct_id == struct_n1_id)
        self.holiday_pay_2020 = holiday_pays.filtered(lambda p: p.struct_id == struct_n_id)

        self.assertEqual(len(self.termination_fees.worked_days_line_ids), 0)
        self.assertEqual(len(self.termination_fees.input_line_ids), 16)
        self.assertEqual(len(self.termination_fees.line_ids), 41)
        payslip_results = {
            'BASIC2': 41344.0,
            'YEAREND_BONUS': 3200.0,
            'RESIDENCE': 0.0,
            'EXPATRIATE': 0.0,
            'MEAL_VOUCHER': 1399.21,
            'ECO_VOUCHER': 250.0,
            'VARIABLE_SALARY': 6000.0,
            'PAY_VARIABLE_SALARY': 920.4,
            'BENEFIT_IN_KIND': 0.0,
            'ADVANTAGE_ANY_KIND': 116.28,
            'ATN.CAR': 1693.71,
            'AMBULATORY_INSURANCE': 0.0,
            'HOSPITAL_INSURANCE': 0.0,
            'GROUP_INSURANCE': 0.0,
            'STOCK_OPTION': 1500.0,
            'SPECIFIC RULES': 0.0,
            'OTHER': 0.0,
            'ANNUAL_SALARY_REVALUED': 56423.61,
            'ND_MONTH': 0.0,
            'ND_WEEK': 9765.62,
            'ND_DAY': 0.0,
            'TOTALFEES': 9765.62,
            'ONSSEMPLOYERBASIC': 2443.36,
            'ONSSEMPLOYERCPAE': 22.46,
            'ONSSEMPLOYERFFE': 12.7,
            'ONSSEMPLOYERMFFE': 9.77,
            'ONSSEMPLOYERRESTREINT': 165.04,
            'ONSSEMPLOYERUNEMP': 9.77,
            'OUTPLACEMENT': 0.0,
            'ONSSEMPLOYER': 2663.09,
            'UNREASONABLE_DISMISSAL': 0.0,
            'NON_RESPECT_MOTIVATION': 0.0,
            'EMPLOYERCOST': 12428.71,
            'BASIC': 9765.62,
            'ONSS': -1276.37,
            'ONSSTOTAL': 1276.37,
            'GROSS': 8489.26,
            'P.P': -3694.88,
            'PPTOTAL': 3694.88,
            'REMUNERATION': 9765.62,
            'NET': 4794.38,
        }
        self._validate_payslip(self.termination_fees, payslip_results)

        self.assertEqual(len(self.holiday_pay_2020.worked_days_line_ids), 0)
        self.assertEqual(len(self.holiday_pay_2020.input_line_ids), 6)
        self.assertEqual(len(self.holiday_pay_2020.line_ids), 19)
        payslip_results = {
            'PAY_SIMPLE': 1137.92,
            'DOUBLE_BASIC': 1008.85,
            'PAY DOUBLE': 1008.85,
            'PAY DOUBLE COMPLEMENTARY': 129.07,
            'BASIC': 2275.84,
            'ONSS1': -148.73,
            'ONSS2': -131.86,
            'ONSSTOTAL': 280.58,
            'GROSS': 1995.26,
            'PROF_TAX': -725.08,
            'PPTOTAL': 725.08,
            'NET': 1270.18,
            'ONSSEMPLOYERBASIC': 284.71,
            'ONSSEMPLOYERCPAE': 2.62,
            'ONSSEMPLOYERFFE': 1.48,
            'ONSSEMPLOYERMFFE': 1.14,
            'ONSSEMPLOYERRESTREINT': 19.23,
            'ONSSEMPLOYERUNEMP': 1.14,
            'ONSSEMPLOYER': 310.31,
        }
        self._validate_payslip(self.holiday_pay_2020, payslip_results)

        self.assertEqual(len(self.holiday_pay_2019.worked_days_line_ids), 0)
        self.assertEqual(len(self.holiday_pay_2019.input_line_ids), 6)
        self.assertEqual(len(self.holiday_pay_2019.line_ids), 27)
        payslip_results = {
            'BASIC_PAY_SIMPLE': 2508.58,
            'SIMPLE_PAY_DECEMBER': 0.0,
            'PAY_SIMPLE': 2508.58,
            'DOUBLE_BASIC': 2965.37,
            'EUROPEAN': -1384.62,
            'DHALREADYPAID': 0.0,
            'DOUBLE_PAY_DECEMBER': 0.0,
            'PAY DOUBLE': 1580.75,
            'CDHBASIC': 202.24,
            'CDHALREADYPAID': 0.0,
            'COMP_DOUBLE_PAY_DECEMBER': 0.0,
            'PAY DOUBLE COMPLEMENTARY': 202.24,
            'BASIC': 4291.57,
            'ONSS1': -327.87,
            'ONSS2': -206.6,
            'ONSSTOTAL': 534.48,
            'GROSS': 3757.1,
            'PROF_TAX': -1365.33,
            'PPTOTAL': 1365.33,
            'NET': 2391.77,
            'ONSSEMPLOYERBASIC': 627.65,
            'ONSSEMPLOYERFFE': 3.26,
            'ONSSEMPLOYERMFFE': 2.51,
            'ONSSEMPLOYERCPAE': 5.77,
            'ONSSEMPLOYERRESTREINT': 42.39,
            'ONSSEMPLOYERUNEMP': 2.51,
            'ONSSEMPLOYER': 684.09,
        }
        self._validate_payslip(self.holiday_pay_2019, payslip_results)

    def test_work_incapacity_due_to_illness(self):
        self.contract.write({
            'wage_on_signature': 3548.6,
            'wage': 3548.6,
            'resource_calendar_id': self.resource_calendar_19_part_time_sick.id,
            'date_start': datetime.date(2021, 3, 27),
            'date_end': datetime.date(2021, 4, 30),
        })

        payslip = self._generate_payslip(datetime.date(2021, 3, 1), datetime.date(2021, 3, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 3)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 31)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 245.67, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE281'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('OUT'), 0.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 3.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE281'), 3.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('OUT'), 20.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 11.4, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE281'), 11.4, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('OUT'), 152, places=2)

        payslip_results = {
            'BASIC': 245.67,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 254.67,
            'ONSS': -33.29,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 33.29,
            'ATN.CAR': 150.53,
            'GROSSIP': 371.92,
            'IP.PART': -61.42,
            'GROSS': 310.5,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'ATN.CAR.2': -150.53,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -3.27,
            'REP.FEES': 5.77,
            'IP': 61.42,
            'IP.DED': -4.61,
            'NET': 210.28,
            'REMUNERATION': 184.25,
            'ONSSEMPLOYERBASIC': 63.72,
            'ONSSEMPLOYERFFE': 0.33,
            'ONSSEMPLOYERMFFE': 0.25,
            'ONSSEMPLOYERCPAE': 0.59,
            'ONSSEMPLOYERRESTREINT': 4.3,
            'ONSSEMPLOYERUNEMP': 0.25,
            'ONSSEMPLOYER': 69.45,
            'CO2FEE': 21.16,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_work_incapacity_due_to_illness_full_month(self):
        self.employee.write({
            'km_home_work': 53,
        })

        self.contract.write({
            'resource_calendar_id': self.resource_calendar_19_part_time_sick.id,
            'wage': 1774.30,
            'wage_on_signature': 1774.30,
            'date_generated_from': datetime.datetime(2021, 4, 1, 0, 0, 0),
            'date_generated_to': datetime.datetime(2021, 4, 1, 0, 0, 0),
            'holidays': 5.0,
            'transport_mode_private_car': True,
            'fuel_card': 0.0,
            'internet': 0.0,
            'representation_fees': 399.0,
            'mobile': 0.0,
            'ip': True,
            'ip_wage_rate': 20.0,
        })

        # Public Holiday
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_19_part_time_sick.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2021, 4, 5, 4, 0, 0),
            'date_to': datetime.datetime(2021, 4, 5, 17, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }])

        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_19_part_time_sick.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2021, 4, 12, 7, 0, 0),
            'date_to': datetime.datetime(2021, 4, 12, 10, 48, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_extra_legal').id
        }])

        payslip = self._generate_payslip(datetime.date(2021, 4, 1), datetime.date(2021, 4, 30))

        self.assertEqual(len(payslip.worked_days_line_ids), 4)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 30)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE281'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('WORK100'), 791.61, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE500'), 40.95, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE213'), 40.95, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE281'), 22.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('WORK100'), 20.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE500'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE213'), 1.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE281'), 83.60, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('WORK100'), 76.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE500'), 3.8, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE213'), 3.8, places=2)

        payslip_results = {
            'BASIC': 873.51,
            'SALARY': 873.51,
            'ONSS': -114.17,
            'EmpBonus.1': 94.87,
            'ONSSTOTAL': 19.3,
            'ATN.CAR': 150.53,
            'GROSSIP': 1004.74,
            'IP.PART': -174.7,
            'GROSS': 830.04,
            'P.P': 0.0,
            'P.P.DED': 0.0,
            'PPTOTAL': 0.0,
            'ATN.CAR.2': -150.53,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -21.8,
            'CAR.PRIV': 76.25,
            'REP.FEES': 279.31,
            'REP.FEES.VOLATILE': 59.85,
            'IP': 174.7,
            'IP.DED': -13.1,
            'NET': 1234.71,
            'REMUNERATION': 698.81,
            'ONSSEMPLOYERBASIC': 218.55,
            'ONSSEMPLOYERFFE': 1.14,
            'ONSSEMPLOYERMFFE': 0.87,
            'ONSSEMPLOYERCPAE': 2.01,
            'ONSSEMPLOYERRESTREINT': 14.76,
            'ONSSEMPLOYERUNEMP': 0.87,
            'ONSSEMPLOYER': 238.21,
            'CO2FEE': 21.16,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays(self):
        self.contract.write({
            'transport_mode_car': False,
        })
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip.compute_sheet()

        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 7)

        payslip_results = {
            'BASIC': 2438.0,
            'SALARY': 2252.5,
            'ONSS': -294.4,
            'GROSS': 2143.6,
            'P.P': -843.93,
            'PPTOTAL': 843.93,
            'NET': 1299.66,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holiday_no_right(self):
        self.contract.date_start = datetime.date(2021, 1, 1)
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip.compute_sheet()

        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 7)

        payslip_results = {
            'BASIC': 0.0,
            'SALARY': 0.0,
            'ONSS': 0.0,
            'GROSS': 0.0,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'NET': 0.0,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays_incomplete_year_full_time(self):
        self.contract.write({
            'date_start': datetime.date(2020, 3, 15),
            'transport_mode_car': False,
        })
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 1828.5,
            'SALARY': 1689.38,
            'ONSS': -220.8,
            'GROSS': 1607.7,
            'P.P': -632.95,
            'PPTOTAL': 632.95,
            'NET': 974.75,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays_complete_year_credit_time(self):
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
            'wage': 2120.0,
            'wage_on_signature': 2120.0,
            'transport_mode_car': False,
        })
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 1950.4,
            'SALARY': 1802.0,
            'ONSS': -235.52,
            'GROSS': 1714.88,
            'P.P': -623.19,
            'PPTOTAL': 623.19,
            'NET': 1091.69,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays_incomplete_year_credit_time(self):
        self.contract.write({
            'date_start': datetime.date(2020, 3, 15),
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
            'wage': 2120.0,
            'wage_on_signature': 2120.0,
            'transport_mode_car': False,
        })
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 1462.8,
            'SALARY': 1351.5,
            'ONSS': -176.64,
            'GROSS': 1286.16,
            'P.P': -467.39,
            'PPTOTAL': 467.39,
            'NET': 818.77,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays_complete_year_part_time(self):
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_38_hours_per_week,
            'wage': 2120.0,
            'wage_on_signature': 2120.0,
            'transport_mode_car': False,
        })
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 1950.4,
            'SALARY': 1802.0,
            'ONSS': -235.52,
            'GROSS': 1714.88,
            'P.P': -623.19,
            'PPTOTAL': 623.19,
            'NET': 1091.69,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays_incomplete_year_part_time(self):
        self.contract.write({
            'date_start': datetime.date(2020, 3, 15),
            'resource_calendar_id': self.resource_calendar_38_hours_per_week,
            'wage': 2120.0,
            'wage_on_signature': 2120.0,
            'transport_mode_car': False,
        })
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 1462.8,
            'SALARY': 1351.5,
            'ONSS': -176.64,
            'GROSS': 1286.16,
            'P.P': -467.39,
            'PPTOTAL': 467.39,
            'NET': 818.77,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays_children_no_reduction(self):
        self.contract.write({
            'date_start': datetime.date(2020, 3, 15),
            'transport_mode_car': False,
        })
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        self.employee.write({
            'children': 2,
        })

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 1828.5,
            'SALARY': 1689.38,
            'ONSS': -220.8,
            'GROSS': 1607.7,
            'P.P': -632.95,
            'PPTOTAL': 632.95,
            'NET': 974.75,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays_children_with_reductions(self):
        self.contract.write({
            'date_start': datetime.date(2020, 3, 15),
            'transport_mode_car': False,
        })
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        self.employee.write({
            'children': 6,
        })

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 1828.5,
            'SALARY': 1689.38,
            'ONSS': -220.8,
            'GROSS': 1607.7,
            'P.P': -105.51,
            'PPTOTAL': 105.51,
            'NET': 1502.19,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays_variable_revenues_complete_year(self):
        commission_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'contract_id': self.contract.id,
            'date_from': datetime.datetime(2020, 5, 1),
            'date_to': datetime.datetime(2020, 5, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.env.company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 3000,
            })]
        })
        commission_payslip.action_refresh_from_work_entries()
        commission_payslip.action_payslip_done()

        self.contract.write({
            'commission_on_target': 1000,
            'transport_mode_car': False,
        })
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 2438.0,
            'SALARY': 2252.5,
            'ONSS': -294.4,
            'GROSS': 2143.6,
            'P.P': -843.93,
            'PPTOTAL': 843.93,
            'NET': 1299.66,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays_variable_revenues_incomplete_year(self):
        commission_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'contract_id': self.contract.id,
            'date_from': datetime.datetime(2020, 5, 1),
            'date_to': datetime.datetime(2020, 5, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.env.company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': 3000,
            })]
        })
        commission_payslip.action_refresh_from_work_entries()
        commission_payslip.action_payslip_done()

        self.contract.write({
            'commission_on_target': 1000,
            'date_start': datetime.date(2020, 3, 15),
            'transport_mode_car': False,
        })
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 1828.5,
            'SALARY': 1689.38,
            'ONSS': -220.8,
            'GROSS': 1607.7,
            'P.P': -632.95,
            'PPTOTAL': 632.95,
            'NET': 974.75,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays_european_time_off(self):
        self.contract.write({
            'date_start': datetime.date(2020, 3, 15),
            'transport_mode_car': False,
        })
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        self.employee.write({
            'children': 2,
        })

        european_time_off = self.env['hr.leave'].create({
            'name': 'European Time Off',
            'holiday_status_id': self.european_time_off_type.id,
            'request_date_from': datetime.date(2020, 5, 4),
            'request_date_to': datetime.date(2020, 5, 4),
            'employee_id': self.employee.id,
        })
        european_time_off.action_validate()

        european_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'contract_id': self.contract.id,
            'date_from': datetime.datetime(2020, 5, 1),
            'date_to': datetime.datetime(2020, 5, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.env.company.id,
        })
        european_payslip.action_refresh_from_work_entries()
        european_payslip.action_payslip_done()
        self.assertEqual(european_payslip.worked_days_line_ids.filtered(lambda wd: wd.code == 'LEAVE216').amount, 122.31)

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip.compute_sheet()

        self.assertEqual(len(payslip.input_line_ids), 1)
        payslip_results = {
            'BASIC': 1828.5,
            'EU.LEAVE.DEDUC': -122.31,
            'SALARY': 1576.37,
            'ONSS': -206.03,
            'GROSS': 1500.16,
            'P.P': -590.61,
            'PPTOTAL': 590.61,
            'NET': 909.55,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays_european_time_off_over_2_years(self):
        self.contract.write({
            'date_start': datetime.date(2019, 1, 1),
            'transport_mode_car': False,
        })
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        self.employee.write({
            'children': 2,
        })

        # Takes all the 4 weeks of european time off in Feb 2019
        # Should recover 2650 € in 2020
        european_time_off = self.env['hr.leave'].create({
            'name': 'European Time Off',
            'holiday_status_id': self.european_time_off_type.id,
            'request_date_from': datetime.date(2019, 2, 1),
            'request_date_to': datetime.date(2019, 2, 28),
            'employee_id': self.employee.id,
        })
        european_time_off.action_validate()

        european_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'contract_id': self.contract.id,
            'date_from': datetime.datetime(2019, 2, 1),
            'date_to': datetime.datetime(2019, 2, 28),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.env.company.id,
        })
        european_payslip.action_refresh_from_work_entries()
        european_payslip.action_payslip_done()
        self.assertEqual(european_payslip.worked_days_line_ids.filtered(lambda wd: wd.code == 'LEAVE216').amount, 2650)

        payslip_2020 = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2020, 6, 1),
            'date_to': datetime.date(2020, 6, 30)
        })
        payslip_2020.compute_sheet()
        payslip_2020.action_payslip_done()

        # We recover the maximum amount in 2020, and we should recover the remaining in 2021
        # 2650 - 2438 = 212 €
        self.assertEqual(len(payslip_2020.input_line_ids), 1)
        payslip_results = {
            'BASIC': 2438.0,
            'EU.LEAVE.DEDUC': -2438.0,
            'SALARY': 0.0,
            'ONSS': 0.0,
            'GROSS': 0.0,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'NET': 0.0,
        }
        self._validate_payslip(payslip_2020, payslip_results)

        payslip_2021 = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip_2021.compute_sheet()
        self.assertEqual(len(payslip_2021.input_line_ids), 1)

        payslip_results = {
            'BASIC': 2438.0,
            'EU.LEAVE.DEDUC': -212.0,
            'SALARY': 2056.63,
            'ONSS': -268.8,
            'GROSS': 1957.2,
            'P.P': -770.55,
            'PPTOTAL': 770.55,
            'NET': 1186.65,
        }
        self._validate_payslip(payslip_2021, payslip_results)

    def test_double_holidays_company_car(self):
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))
        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30)
        })
        payslip.compute_sheet()

        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 7)

        payslip_results = {
            'BASIC': 2438.0,
            'SALARY': 2252.5,
            'ONSS': -294.4,
            'GROSS': 2143.6,
            'P.P': -908.67,
            'PPTOTAL': 908.67,
            'NET': 1234.93,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays_pay_recovery(self):
        self.contract.write({
            'transport_mode_car': False,
        })
        self.contract.generate_work_entries(self.contract.date_start, datetime.date(2021, 6, 30))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2021, 6, 1),
            'date_to': datetime.date(2021, 6, 30),
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_double_holiday_recovery').id,
                'amount': 438.0,
            })]
        })
        payslip.compute_sheet()

        self.assertEqual(len(payslip.worked_days_line_ids), 0)
        self.assertEqual(len(payslip.input_line_ids), 1)
        self.assertEqual(len(payslip.line_ids), 8)

        payslip_results = {
            'BASIC': 2438.0,
            'DOUBLERECOVERY': -438.0,
            'SALARY': 1847.83,
            'ONSS': -241.51,
            'GROSS': 1758.49,
            'P.P': -692.32,
            'PPTOTAL': 692.32,
            'NET': 1066.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_termination_holidays_pp_exoneration_reduction(self):
        self.employee.children = 2

        termination_payslips = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'contract_id': self.contract.id,
            'date_from': datetime.datetime(2021, 5, 1),
            'date_to': datetime.datetime(2021, 5, 31),
            'vehicle_id': self.car.id,
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n1_holidays').id,
            'company_id': self.env.company.id,
            'input_line_ids': [(0, 0, {
                'name': "Test Input",
                'sequence': 1,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_gross_ref').id,
                'amount': 43608.44
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 3,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_allocation').id,
                'amount': 20.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 4,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_time_off_taken').id,
                'amount': 5.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 5,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_annual_taxable_amount').id,
                'amount': 15000.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 6,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_european_leave').id,
                'amount': 0.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 7,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_european_leave_days').id,
                'amount': 0.0
            })],
        })
        termination_payslips.compute_sheet()

        self.assertEqual(len(termination_payslips.worked_days_line_ids), 0)
        self.assertEqual(len(termination_payslips.input_line_ids), 6)
        self.assertEqual(len(termination_payslips.line_ids), 27)

        payslip_results = {
            'BASIC_PAY_SIMPLE': 2508.58,
            'SIMPLE_PAY_DECEMBER': 0.0,
            'PAY_SIMPLE': 2508.58,
            'DOUBLE_BASIC': 2965.37,
            'EUROPEAN': 0.0,
            'DHALREADYPAID': 0.0,
            'DOUBLE_PAY_DECEMBER': 0.0,
            'PAY DOUBLE': 2965.37,
            'CDHBASIC': 379.39,
            'CDHALREADYPAID': 0.0,
            'COMP_DOUBLE_PAY_DECEMBER': 0.0,
            'PAY DOUBLE COMPLEMENTARY': 379.39,
            'BASIC': 5853.34,
            'ONSS1': -327.87,
            'ONSS2': -387.57,
            'ONSSTOTAL': 715.45,
            'GROSS': 5137.9,
            'PROF_TAX': -646.36,
            'PPTOTAL': 646.36,
            'NET': 4491.54,
            'ONSSEMPLOYERBASIC': 627.65,
            'ONSSEMPLOYERFFE': 3.26,
            'ONSSEMPLOYERMFFE': 2.51,
            'ONSSEMPLOYERCPAE': 5.77,
            'ONSSEMPLOYERRESTREINT': 42.39,
            'ONSSEMPLOYERUNEMP': 2.51,
            'ONSSEMPLOYER': 684.09,
        }
        self.assertAlmostEqual(termination_payslips.line_ids.filtered(lambda l: l.code == 'PROF_TAX').rate, -21.00, places=2)
        self._validate_payslip(termination_payslips, payslip_results)

    def test_termination_holidays_pp_no_exoneration_reduction(self):
        self.employee.children = 2

        termination_payslips = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'contract_id': self.contract.id,
            'date_from': datetime.datetime(2021, 5, 1),
            'date_to': datetime.datetime(2021, 5, 31),
            'vehicle_id': self.car.id,
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n1_holidays').id,
            'company_id': self.env.company.id,
            'input_line_ids': [(0, 0, {
                'name': "Test Input",
                'sequence': 1,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_gross_ref').id,
                'amount': 43608.44
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 3,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_allocation').id,
                'amount': 20.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 4,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_time_off_taken').id,
                'amount': 5.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 5,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_annual_taxable_amount').id,
                'amount': 18000.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 6,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_european_leave').id,
                'amount': 0.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 7,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_european_leave_days').id,
                'amount': 0.0
            })],
        })
        termination_payslips.compute_sheet()

        self.assertEqual(len(termination_payslips.worked_days_line_ids), 0)
        self.assertEqual(len(termination_payslips.input_line_ids), 6)
        self.assertEqual(len(termination_payslips.line_ids), 27)

        payslip_results = {
            'BASIC_PAY_SIMPLE': 2508.58,
            'SIMPLE_PAY_DECEMBER': 0.0,
            'PAY_SIMPLE': 2508.58,
            'DOUBLE_BASIC': 2965.37,
            'EUROPEAN': 0.0,
            'DHALREADYPAID': 0.0,
            'DOUBLE_PAY_DECEMBER': 0.0,
            'PAY DOUBLE': 2965.37,
            'CDHBASIC': 379.39,
            'CDHALREADYPAID': 0.0,
            'COMP_DOUBLE_PAY_DECEMBER': 0.0,
            'PAY DOUBLE COMPLEMENTARY': 379.39,
            'BASIC': 5853.34,
            'ONSS1': -327.87,
            'ONSS2': -387.57,
            'ONSSTOTAL': 715.45,
            'GROSS': 5137.9,
            'PROF_TAX': -1286.53,
            'PPTOTAL': 1286.53,
            'NET': 3851.37,
            'ONSSEMPLOYERBASIC': 627.65,
            'ONSSEMPLOYERFFE': 3.26,
            'ONSSEMPLOYERMFFE': 2.51,
            'ONSSEMPLOYERCPAE': 5.77,
            'ONSSEMPLOYERRESTREINT': 42.39,
            'ONSSEMPLOYERUNEMP': 2.51,
            'ONSSEMPLOYER': 684.09,
        }
        self.assertAlmostEqual(termination_payslips.line_ids.filtered(lambda l: l.code == 'PROF_TAX').rate, -25.04, places=2)
        self._validate_payslip(termination_payslips, payslip_results)

    def test_termination_holidays_december_payslip(self):
        termination_payslips = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'contract_id': self.contract.id,
            'date_from': datetime.datetime(2021, 5, 1),
            'date_to': datetime.datetime(2021, 5, 31),
            'vehicle_id': self.car.id,
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n1_holidays').id,
            'company_id': self.env.company.id,
            'input_line_ids': [(0, 0, {
                'name': "Test Input",
                'sequence': 1,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_gross_ref').id,
                'amount': 43608.44
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 3,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_allocation').id,
                'amount': 20.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 4,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_time_off_taken').id,
                'amount': 5.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 5,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_annual_taxable_amount').id,
                'amount': 18000.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 6,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_european_leave').id,
                'amount': 0.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 7,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_european_leave_days').id,
                'amount': 0.0
            }), (0, 0, {
                'name': "Double Already Paid",
                'sequence': 6,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_double_pay_already_paid').id,
                'amount': 10
            }), (0, 0, {
                'name': "Complementary Double Already Paid",
                'sequence': 6,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_complementary_double_pay_already_paid').id,
                'amount': 10
            }), (0, 0, {
                'name': "Simple December",
                'sequence': 6,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_simple_pay_december').id,
                'amount': 20
            }), (0, 0, {
                'name': "Double December",
                'sequence': 6,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_double_pay_december').id,
                'amount': 20
            }), (0, 0, {
                'name': "Complementary Double December",
                'sequence': 6,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_complementary_double_pay_december').id,
                'amount': 20
            })],
        })
        termination_payslips.compute_sheet()

        self.assertEqual(len(termination_payslips.worked_days_line_ids), 0)
        self.assertEqual(len(termination_payslips.input_line_ids), 11)
        self.assertEqual(len(termination_payslips.line_ids), 27)

        payslip_results = {
            'BASIC_PAY_SIMPLE': 2508.58,
            'SIMPLE_PAY_DECEMBER': 20.0,
            'PAY_SIMPLE': 2528.58,
            'DOUBLE_BASIC': 2965.37,
            'EUROPEAN': 0.0,
            'DHALREADYPAID': -10.0,
            'DOUBLE_PAY_DECEMBER': 20.0,
            'PAY DOUBLE': 2975.37,
            'CDHBASIC': 380.67,
            'CDHALREADYPAID': -10.0,
            'COMP_DOUBLE_PAY_DECEMBER': 20.0,
            'PAY DOUBLE COMPLEMENTARY': 390.67,
            'BASIC': 5894.62,
            'ONSS1': -330.48,
            'ONSS2': -388.88,
            'ONSSTOTAL': 719.37,
            'GROSS': 5175.26,
            'PROF_TAX': -1619.86,
            'PPTOTAL': 1619.86,
            'NET': 3555.4,
            'ONSSEMPLOYERBASIC': 632.65,
            'ONSSEMPLOYERFFE': 3.29,
            'ONSSEMPLOYERMFFE': 2.53,
            'ONSSEMPLOYERCPAE': 5.82,
            'ONSSEMPLOYERRESTREINT': 42.73,
            'ONSSEMPLOYERUNEMP': 2.53,
            'ONSSEMPLOYER': 689.54,
        }
        self._validate_payslip(termination_payslips, payslip_results)

    def test_termination_holidays_pp_no_exoneration_no_reduction(self):
        self.employee.children = 2

        termination_payslips = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'contract_id': self.contract.id,
            'date_from': datetime.datetime(2021, 5, 1),
            'date_to': datetime.datetime(2021, 5, 31),
            'vehicle_id': self.car.id,
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n1_holidays').id,
            'company_id': self.env.company.id,
            'input_line_ids': [(0, 0, {
                'name': "Test Input",
                'sequence': 1,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_gross_ref').id,
                'amount': 43608.44
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 3,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_allocation').id,
                'amount': 20.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 4,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_time_off_taken').id,
                'amount': 5.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 5,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_annual_taxable_amount').id,
                'amount': 25000.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 6,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_european_leave').id,
                'amount': 0.0
            }), (0, 0, {
                'name': "Test Input",
                'sequence': 7,
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_european_leave_days').id,
                'amount': 0.0
            })],
        })
        termination_payslips.compute_sheet()

        self.assertEqual(len(termination_payslips.worked_days_line_ids), 0)
        self.assertEqual(len(termination_payslips.input_line_ids), 6)
        self.assertEqual(len(termination_payslips.line_ids), 27)

        payslip_results = {
            'BASIC_PAY_SIMPLE': 2508.58,
            'SIMPLE_PAY_DECEMBER': 0.0,
            'PAY_SIMPLE': 2508.58,
            'DOUBLE_BASIC': 2965.37,
            'EUROPEAN': 0.0,
            'DHALREADYPAID': 0.0,
            'DOUBLE_PAY_DECEMBER': 0.0,
            'PAY DOUBLE': 2965.37,
            'CDHBASIC': 379.39,
            'CDHALREADYPAID': 0.0,
            'COMP_DOUBLE_PAY_DECEMBER': 0.0,
            'PAY DOUBLE COMPLEMENTARY': 379.39,
            'BASIC': 5853.34,
            'ONSS1': -327.87,
            'ONSS2': -387.57,
            'ONSSTOTAL': 715.45,
            'GROSS': 5137.9,
            'PROF_TAX': -1867.11,
            'PPTOTAL': 1867.11,
            'NET': 3270.79,
            'ONSSEMPLOYERBASIC': 627.65,
            'ONSSEMPLOYERFFE': 3.26,
            'ONSSEMPLOYERMFFE': 2.51,
            'ONSSEMPLOYERCPAE': 5.77,
            'ONSSEMPLOYERRESTREINT': 42.39,
            'ONSSEMPLOYERUNEMP': 2.51,
            'ONSSEMPLOYER': 684.09,
        }
        self.assertAlmostEqual(termination_payslips.line_ids.filtered(lambda l: l.code == 'PROF_TAX').rate, -36.34, places=2)
        self._validate_payslip(termination_payslips, payslip_results)

    def test_public_holiday_right_unemployment(self):
        # Note: The public holidays are paid the first 14 days of unemployment

        self.contract.ip = False

        # Public time offs
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2021, 5, 12, 4, 0, 0),
            'date_to': datetime.datetime(2021, 5, 12, 21, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }, {
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2021, 5, 26, 4, 0, 0),
            'date_to': datetime.datetime(2021, 5, 26, 21, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }])

        economic_unemployment = self.env['hr.leave'].create({
            'name': 'Legal Time Off 2020',
            'holiday_status_id': self.economic_unemployment_time_off_type.id,
            'request_date_from': datetime.date(2021, 5, 1),
            'request_date_to': datetime.date(2021, 5, 31),
            'employee_id': self.employee.id,
        })
        economic_unemployment.action_validate()

        self.contract.generate_work_entries(datetime.date(2021, 5, 1), datetime.date(2021, 5, 31))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'date_from': datetime.date(2021, 5, 1),
            'date_to': datetime.date(2021, 5, 31)
        })
        payslip.compute_sheet()

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 26)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE6665'), 2446.15, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE500'), 203.85, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE6665'), 20.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE500'), 1.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE6665'), 152.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE500'), 7.6, places=2)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'ATN.CAR': 150.53,
            'GROSS': 2462.0,
            'P.P': -545.61,
            'PPTOTAL': 545.61,
            'ATN.CAR.2': -150.53,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': 0.0,
            'REP.FEES': 150.0,
            'NET': 1883.2,
            'REMUNERATION': 2650.0,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
            'CO2FEE': 21.16,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_public_holiday_right_maternity(self):
        # Note: The public holidays are paid the first 30 days of maternity/partial incapacity, ...

        self.contract.ip = False

        # Public time offs
        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2021, 5, 12, 4, 0, 0),
            'date_to': datetime.datetime(2021, 5, 12, 21, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }, {
            'name': "Absence",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2021, 5, 17, 4, 0, 0),
            'date_to': datetime.datetime(2021, 5, 17, 21, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }])

        maternity = self.env['hr.leave'].create({
            'name': 'Legal Time Off 2020',
            'holiday_status_id': self.env.ref('l10n_be_hr_payroll.holiday_type_maternity').id,
            'request_date_from': datetime.date(2021, 4, 17),
            'request_date_to': datetime.date(2021, 5, 31),
            'employee_id': self.employee.id,
        })
        maternity.action_validate()

        self.contract.generate_work_entries(datetime.date(2021, 4, 1), datetime.date(2021, 5, 31))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'date_from': datetime.date(2021, 5, 1),
            'date_to': datetime.date(2021, 5, 31)
        })
        payslip.compute_sheet()

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 27)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE210'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE500'), 122.31, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE210'), 20.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE500'), 1.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE210'), 152.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE500'), 7.6, places=2)

        payslip_results = {
            'BASIC': 122.31,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 131.31,
            'ONSS': -17.16,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 17.16,
            'ATN.CAR': 150.53,
            'GROSS': 264.68,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'ATN.CAR.2': -150.53,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': 0.0,
            'REP.FEES': 150.0,
            'NET': 255.15,
            'REMUNERATION': 122.31,
            'ONSSEMPLOYERBASIC': 32.85,
            'ONSSEMPLOYERFFE': 0.17,
            'ONSSEMPLOYERMFFE': 0.13,
            'ONSSEMPLOYERCPAE': 0.3,
            'ONSSEMPLOYERRESTREINT': 2.22,
            'ONSSEMPLOYERUNEMP': 0.13,
            'ONSSEMPLOYER': 35.81,
            'CO2FEE': 21.16,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_public_holiday_right_maternity_full_time_credit_time(self):
        # Note: Always unpaid
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_0_hours_per_week.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2021, 5, 1),
            'wage': 0.0,
            'wage_on_signature': 0.0,
            'ip': False,
            'time_credit': True,
            'work_time_rate': 0,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })

        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_0_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2021, 5, 4, 4, 0, 0),
            'date_to': datetime.datetime(2021, 5, 4, 21, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }])

        maternity = self.env['hr.leave'].create({
            'name': 'Legal Time Off 2020',
            'holiday_status_id': self.env.ref('l10n_be_hr_payroll.holiday_type_maternity').id,
            'request_date_from': '2021-5-1',
            'request_date_to': '2021-5-31',
            'employee_id': self.employee.id,
        })
        maternity.action_validate()

        self.contract.generate_work_entries(datetime.date(2021, 5, 1), datetime.date(2021, 5, 31))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'date_from': datetime.date(2021, 5, 1),
            'date_to': datetime.date(2021, 5, 31)
        })
        payslip.compute_sheet()

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 26)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 21.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 159.6, places=2)

    def test_public_holiday_right_maternity_credit_time_less_1_month(self):
        # Note: Unpaid
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2021, 5, 1),
            'wage': 2120,
            'wage_on_signature': 2120,
            'ip': False,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })

        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2021, 5, 4, 4, 0, 0),
            'date_to': datetime.datetime(2021, 5, 4, 21, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }])

        maternity = self.env['hr.leave'].create({
            'name': 'Legal Time Off 2020',
            'holiday_status_id': self.env.ref('l10n_be_hr_payroll.holiday_type_maternity').id,
            'request_date_from': datetime.date(2021, 5, 1),
            'request_date_to': datetime.date(2021, 5, 31),
            'employee_id': self.employee.id,
        })
        maternity.action_validate()

        self.contract.generate_work_entries(datetime.date(2021, 5, 1), datetime.date(2021, 5, 31))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'date_from': datetime.date(2021, 5, 1),
            'date_to': datetime.date(2021, 5, 31)
        })
        payslip.compute_sheet()

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 26)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE210'), 0.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 4.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE210'), 17.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 30.4, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE210'), 129.2, places=2)

    def test_public_holiday_right_maternity_credit_time_less_3_month(self):
        # Note: Paid the first 14 days
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'date_start': datetime.date(2021, 4, 1),
            'wage': 2120,
            'wage_on_signature': 2120,
            'ip': False,
            'time_credit': True,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_credit_time').id,
        })

        self.env['resource.calendar.leaves'].create([{
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2021, 5, 4, 4, 0, 0),
            'date_to': datetime.datetime(2021, 5, 4, 21, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }, {
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2021, 5, 13, 4, 0, 0),
            'date_to': datetime.datetime(2021, 5, 13, 21, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }, {
            'name': "Absence",
            'calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2021, 5, 17, 4, 0, 0),
            'date_to': datetime.datetime(2021, 5, 17, 21, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }])

        maternity = self.env['hr.leave'].create({
            'name': 'Legal Time Off 2020',
            'holiday_status_id': self.env.ref('l10n_be_hr_payroll.holiday_type_maternity').id,
            'request_date_from': datetime.date(2021, 5, 1),
            'request_date_to': datetime.date(2021, 5, 31),
            'employee_id': self.employee.id,
        })
        maternity.action_validate()

        self.contract.generate_work_entries(datetime.date(2021, 5, 1), datetime.date(2021, 5, 31))

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'date_from': datetime.date(2021, 5, 1),
            'date_to': datetime.date(2021, 5, 31)
        })
        payslip.compute_sheet()

        self.assertEqual(len(payslip.worked_days_line_ids), 3)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 28)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE300'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE210'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE500'), 244.62, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE300'), 4.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE210'), 15.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE500'), 2.0, places=2)

        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE300'), 30.4, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE210'), 114.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE500'), 15.2, places=2)

    def test_double_holiday_recovery(self):
        self.contract.write({
            'date_start': datetime.date(2020, 8, 3),
            'wage_on_signature': 1956.69,
        })

        double_pay_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'contract_id': self.contract.id,
            'date_from': datetime.datetime(2021, 6, 1),
            'date_to': datetime.datetime(2021, 6, 30),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'company_id': self.env.company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_double_holiday_nbr_months').id,
                'amount': 11,
            })],
        })

        wizard = self.env['l10n.be.double.pay.recovery.wizard'].with_context(
            active_id=double_pay_payslip.id,
            active_model="hr.payslip"
        ).create({
            'line_ids': [(0, 0, {
                'months_count': 6,
                'amount': 2781.82,
                'occupation_rate': 100,
            })],
        })
        wizard.action_validate()
        double_pay_payslip.compute_sheet()

        self.assertAlmostEqual(wizard.months_count, 5, places=2)
        self.assertAlmostEqual(wizard.double_pay_to_recover, 900.47, places=2)
        self.assertAlmostEqual(double_pay_payslip.input_line_ids.filtered(lambda l: l.code == 'DOUBLERECOVERY').amount, 900.47)

        self.assertEqual(len(double_pay_payslip.worked_days_line_ids), 0)
        self.assertEqual(len(double_pay_payslip.input_line_ids), 2)
        self.assertEqual(len(double_pay_payslip.line_ids), 8)

        payslip_results = {
            'BASIC': 1650.14,
            'DOUBLERECOVERY': -900.47,
            'SALARY': 692.63,
            'ONSS': -90.53,
            'GROSS': 659.14,
            'P.P': -239.53,
            'PPTOTAL': 239.53,
            'NET': 419.61,
        }
        self._validate_payslip(double_pay_payslip, payslip_results)

    def test_double_holiday_recovery_half_time_multi_attest(self):
        # Note: The employee was occupied with 2 half times over the same period
        self.contract.write({
            'date_start': datetime.date(2020, 8, 3),
            'wage_on_signature': 2322.22,
        })

        double_pay_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'contract_id': self.contract.id,
            'date_from': datetime.datetime(2021, 6, 1),
            'date_to': datetime.datetime(2021, 6, 30),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'company_id': self.env.company.id,
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.input_double_holiday_nbr_months').id,
                'amount': 7,
            })],
        })

        wizard = self.env['l10n.be.double.pay.recovery.wizard'].with_context(
            active_id=double_pay_payslip.id,
            active_model="hr.payslip"
        ).create({
            'line_ids': [(0, 0, {
                'months_count': 2,
                'amount': 520.89,
                'occupation_rate': 50,
            }), (0, 0, {
                'months_count': 2,
                'amount': 491.62,
                'occupation_rate': 50,
            })],
        })
        wizard.action_validate()
        double_pay_payslip.compute_sheet()

        self.assertAlmostEqual(wizard.months_count, 5, places=2)
        self.assertAlmostEqual(wizard.double_pay_to_recover, 356.23, places=2)
        self.assertAlmostEqual(double_pay_payslip.input_line_ids.filtered(lambda l: l.code == 'DOUBLERECOVERY').amount, 356.23)

        self.assertEqual(len(double_pay_payslip.worked_days_line_ids), 0)
        self.assertEqual(len(double_pay_payslip.input_line_ids), 2)
        self.assertEqual(len(double_pay_payslip.line_ids), 8)

        payslip_results = {
            'BASIC': 1246.26,
            'DOUBLERECOVERY': -356.23,
            'SALARY': 822.31,
            'ONSS': -107.48,
            'GROSS': 782.55,
            'P.P': -308.09,
            'PPTOTAL': 308.09,
            'NET': 474.46,
        }
        self._validate_payslip(double_pay_payslip, payslip_results)

    def test_double_remuneration_line_2_contracts(self):
        self.employee.km_home_work = 41

        contract_1 = self.contract
        contract_1.write({
            'date_start': datetime.date(2022, 2, 1),
            'date_end': datetime.date(2022, 2, 15),
            'transport_mode_private_car': True,
            'transport_mode_train': True,
            'train_transport_employee_amount': 50,
            'l10n_be_canteen_cost': 42,
        })

        contract_2 = contract_1.copy({
            'date_start': datetime.date(2022, 2, 16),
            'date_end': False,
            'state': 'open',
        })

        (contract_1 + contract_2).generate_work_entries(datetime.date(2022, 2, 1), datetime.date(2022, 2, 28))

        payslip_1 = self.env['hr.payslip'].create([{
            'name': "Test Payslip 1",
            'employee_id': self.employee.id,
            'contract_id': contract_1.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'date_from': datetime.date(2022, 2, 1),
            'date_to': datetime.date(2022, 2, 28),
        }])
        payslip_2 = self.env['hr.payslip'].create([{
            'name': "Test Payslip 2",
            'employee_id': self.employee.id,
            'contract_id': contract_2.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'date_from': datetime.date(2022, 2, 1),
            'date_to': datetime.date(2022, 2, 28),
        }])
        (payslip_1 + payslip_2).compute_sheet()

        payslip_1_results = {
            'BASIC': 1549.23,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 1558.23,
            'ONSS': -203.66,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 203.66,
            'ATN.CAR': 162.42,
            'GROSSIP': 1516.99,
            'IP.PART': -387.31,
            'GROSS': 1129.68,
            'P.P': -25.41,
            'PPTOTAL': 25.41,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -11.99,
            'PUB.TRANS': 40.0,
            'CAR.PRIV': 42.38,
            'REP.FEES': 87.69,
            'IP': 387.31,
            'IP.DED': -29.05,
            'CANTEEN': -42.00,
            'NET': 1407.2,
            'REMUNERATION': 1161.92,
            'ONSSEMPLOYERBASIC': 390.02,
            'ONSSEMPLOYERFFE': 1.09,
            'ONSSEMPLOYERMFFE': 1.56,
            'ONSSEMPLOYERCPAE': 3.58,
            'ONSSEMPLOYERRESTREINT': 26.33,
            'ONSSEMPLOYERUNEMP': 1.56,
            'ONSSEMPLOYER': 424.15,
            'CO2FEE': 28.17,
        }
        payslip_2_results = {
            'BASIC': 1304.62,
            'ATN.INT': 0.0,
            'ATN.MOB': 0.0,
            'SALARY': 1304.62,
            'ONSS': -170.51,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 170.51,
            'ATN.CAR': 0.0,
            'GROSSIP': 1134.11,
            'IP.PART': -326.16,
            'GROSS': 807.95,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'ATN.CAR.2': 0.0,
            'ATN.INT.2': 0.0,
            'ATN.MOB.2': 0.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -9.81,
            'PUB.TRANS': 0.0,
            'CAR.PRIV': 35.69,
            'REP.FEES': 73.85,
            'IP': 326.16,
            'IP.DED': -24.46,
            'CANTEEN': 0.00,
            'NET': 1209.38,
            'REMUNERATION': 978.47,
            'ONSSEMPLOYERBASIC': 326.55,
            'ONSSEMPLOYERFFE': 0.91,
            'ONSSEMPLOYERMFFE': 1.3,
            'ONSSEMPLOYERCPAE': 3.0,
            'ONSSEMPLOYERRESTREINT': 22.05,
            'ONSSEMPLOYERUNEMP': 1.3,
            'ONSSEMPLOYER': 355.12,
            'CO2FEE': 0.0,
        }
        self._validate_payslip(payslip_1, payslip_1_results)
        self._validate_payslip(payslip_2, payslip_2_results)

    def test_double_remuneration_line_1_contract(self):
        # In case only one of both contracts has an advantage
        # Ensure we don't set it to 0
        self.employee.km_home_work = 41

        contract_1 = self.contract
        contract_1.write({
            'date_start': datetime.date(2022, 2, 1),
            'date_end': datetime.date(2022, 2, 15),
            'transport_mode_car': False,
            'mobile': False,
            'internet': False,
            'transport_mode_private_car': False,
            'transport_mode_train': False,
            'train_transport_employee_amount': 0,
        })

        contract_2 = contract_1.copy({
            'date_start': datetime.date(2022, 2, 16),
            'date_end': False,
            'state': 'open',
            'transport_mode_car': True,
            'mobile': 30,
            'internet': 38.0,
            'transport_mode_private_car': True,
            'transport_mode_train': True,
            'train_transport_employee_amount': 50,
        })

        (contract_1 + contract_2).generate_work_entries(datetime.date(2022, 2, 1), datetime.date(2022, 2, 28))

        payslip_1 = self.env['hr.payslip'].create([{
            'name': "Test Payslip 1",
            'employee_id': self.employee.id,
            'contract_id': contract_1.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'date_from': datetime.date(2022, 2, 1),
            'date_to': datetime.date(2022, 2, 28),
        }])
        payslip_2 = self.env['hr.payslip'].create([{
            'name': "Test Payslip 2",
            'employee_id': self.employee.id,
            'contract_id': contract_2.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'date_from': datetime.date(2022, 2, 1),
            'date_to': datetime.date(2022, 2, 28),
        }])
        (payslip_1 + payslip_2).compute_sheet()

        payslip_1_results = {
            'BASIC': 1549.23,
            'SALARY': 1549.23,
            'ONSS': -202.48,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 202.48,
            'GROSSIP': 1346.75,
            'IP.PART': -387.31,
            'GROSS': 959.44,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -11.99,
            'REP.FEES': 87.69,
            'IP': 387.31,
            'IP.DED': -29.05,
            'NET': 1393.4,
            'REMUNERATION': 1161.92,
            'ONSSEMPLOYERBASIC': 387.77,
            'ONSSEMPLOYERFFE': 1.08,
            'ONSSEMPLOYERMFFE': 1.55,
            'ONSSEMPLOYERCPAE': 3.56,
            'ONSSEMPLOYERRESTREINT': 26.18,
            'ONSSEMPLOYERUNEMP': 1.55,
            'ONSSEMPLOYER': 421.7,
        }
        payslip_2_results = {
            'BASIC': 1304.62,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 1313.62,
            'ONSS': -171.69,
            'EmpBonus.1': 0.0,
            'ONSSTOTAL': 171.69,
            'ATN.CAR': 162.42,
            'GROSSIP': 1304.35,
            'IP.PART': -326.16,
            'GROSS': 978.2,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': -9.81,
            'PUB.TRANS': 0.0,
            'CAR.PRIV': 35.69,
            'REP.FEES': 73.85,
            'IP': 326.16,
            'IP.DED': -24.46,
            'NET': 1208.2,
            'REMUNERATION': 978.47,
            'ONSSEMPLOYERBASIC': 328.8,
            'ONSSEMPLOYERFFE': 0.92,
            'ONSSEMPLOYERMFFE': 1.31,
            'ONSSEMPLOYERCPAE': 3.02,
            'ONSSEMPLOYERRESTREINT': 22.2,
            'ONSSEMPLOYERUNEMP': 1.31,
            'ONSSEMPLOYER': 357.57,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip_1, payslip_1_results)
        self._validate_payslip(payslip_2, payslip_2_results)

    def test_holiday_attest_n_before_june(self):
        self._generate_departure_data()

        holiday_attest = self.env['hr.payslip.employee.depature.holiday.attests'].with_context(
            active_id=self.employee.id).create({})
        holiday_attest.write(
            holiday_attest.with_context(active_id=self.employee.id).default_get(holiday_attest._fields))
        holiday_pay_ids = holiday_attest.compute_termination_holidays()['domain'][0][2]
        holiday_pays = self.env['hr.payslip'].browse(holiday_pay_ids)
        struct_n_id = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n_holidays')

        holiday_pay_2020 = holiday_pays.filtered(lambda p: p.struct_id == struct_n_id)
        holiday_pay_2020.write({
            'date_from': datetime.date(2020, 4, 1),
            'date_to': datetime.date(2020, 4, 30),
        })
        holiday_pay_2020.compute_sheet()

        payslip_results = {
            'PAY_SIMPLE': 1137.92,
            'DOUBLE_BASIC': 1008.85,
            'PAY DOUBLE': 1008.85,
            'PAY DOUBLE COMPLEMENTARY': 129.07,
            'BASIC': 2275.84,
            'ONSS1': -148.73,
            'ONSS2': -131.86,
            'ONSSTOTAL': 280.58,
            'GROSS': 1995.26,
            'PROF_TAX': -725.08,
            'PPTOTAL': 725.08,
            'NET': 1270.18,
            'ONSSEMPLOYERBASIC': 284.71,
            'ONSSEMPLOYERCPAE': 2.62,
            'ONSSEMPLOYERFFE': 1.48,
            'ONSSEMPLOYERMFFE': 1.14,
            'ONSSEMPLOYERRESTREINT': 19.23,
            'ONSSEMPLOYERUNEMP': 1.14,
            'ONSSEMPLOYER': 310.31,
        }
        self._validate_payslip(holiday_pay_2020, payslip_results)

    def test_holiday_attest_n_after_june(self):
        self._generate_departure_data()

        double_pay_payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract_2020.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2020, 3, 1),
            'date_to': datetime.date(2020, 3, 31),
            'journal_id': self.journal.id,
            'payslip_run_id': self.batch.id,
        })
        double_pay_payslip.compute_sheet()
        double_pay_payslip.action_payslip_done()

        payslip_results = {
            'BASIC': 3404.0,
            'SALARY': 3145.0,
            'ONSS': -411.05,
            'GROSS': 2992.95,
            'P.P': -1268.71,
            'PPTOTAL': 1268.71,
            'NET': 1724.24,
        }
        self._validate_payslip(double_pay_payslip, payslip_results)

        holiday_attest = self.env['hr.payslip.employee.depature.holiday.attests'].with_context(
            active_id=self.employee.id).create({})
        holiday_attest.write(
            holiday_attest.with_context(active_id=self.employee.id).default_get(holiday_attest._fields))
        holiday_pay_ids = holiday_attest.compute_termination_holidays()['domain'][0][2]
        holiday_pays = self.env['hr.payslip'].browse(holiday_pay_ids)
        struct_n_id = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n_holidays')

        holiday_pay_2020 = holiday_pays.filtered(lambda p: p.struct_id == struct_n_id)
        holiday_pay_2020.write({
            'date_from': datetime.date(2020, 4, 1),
            'date_to': datetime.date(2020, 4, 30),
        })
        holiday_pay_2020.compute_sheet()

        payslip_results = {
            'PAY_SIMPLE': 1137.92,
            'DOUBLE_BASIC': 1008.85,
            'PAY DOUBLE': 1008.85,
            'PAY DOUBLE COMPLEMENTARY': 129.07,
            'BASIC': 2275.84,
            'ONSS1': -148.73,
            'ONSS2': -131.86,
            'ONSSTOTAL': 280.58,
            'GROSS': 1995.26,
            'PROF_TAX': -725.08,
            'PPTOTAL': 725.08,
            'NET': 1270.18,
            'ONSSEMPLOYERBASIC': 284.71,
            'ONSSEMPLOYERCPAE': 2.62,
            'ONSSEMPLOYERFFE': 1.48,
            'ONSSEMPLOYERMFFE': 1.14,
            'ONSSEMPLOYERRESTREINT': 19.23,
            'ONSSEMPLOYERUNEMP': 1.14,
            'ONSSEMPLOYER': 310.31,
        }
        self._validate_payslip(holiday_pay_2020, payslip_results)

        struct_n1_id = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n1_holidays')

        holiday_pay_2019 = holiday_pays.filtered(lambda p: p.struct_id == struct_n1_id)
        holiday_pay_2019.write({
            'date_from': datetime.date(2020, 4, 1),
            'date_to': datetime.date(2020, 4, 30),
        })
        holiday_pay_2019.compute_sheet()

        payslip_results = {
            'BASIC_PAY_SIMPLE': 2508.58,
            'SIMPLE_PAY_DECEMBER': 0.0,
            'PAY_SIMPLE': 2508.58,
            'DOUBLE_BASIC': 0.0,
            'EUROPEAN': 0.0,
            'DHALREADYPAID': 0.0,
            'DOUBLE_PAY_DECEMBER': 0.0,
            'PAY DOUBLE': 0.0,
            'CDHBASIC': 0.0,
            'CDHALREADYPAID': 0.0,
            'COMP_DOUBLE_PAY_DECEMBER': 0.0,
            'PAY DOUBLE COMPLEMENTARY': 0.0,
            'BASIC': 2508.58,
            'ONSS1': -327.87,
            'ONSS2': 0.0,
            'ONSSTOTAL': 327.87,
            'GROSS': 2180.7,
            'PROF_TAX': -792.47,
            'PPTOTAL': 792.47,
            'NET': 1388.24,
            'ONSSEMPLOYERBASIC': 627.65,
            'ONSSEMPLOYERCPAE': 5.77,
            'ONSSEMPLOYERFFE': 3.26,
            'ONSSEMPLOYERMFFE': 2.51,
            'ONSSEMPLOYERRESTREINT': 42.39,
            'ONSSEMPLOYERUNEMP': 2.51,
            'ONSSEMPLOYER': 684.09,
        }
        self._validate_payslip(holiday_pay_2019, payslip_results)

    def test_double_remuneration_refunds_partial_contracts(self):
        # 1 full time parental time off at the start of the month
        # 1 4/5 over the rest of the month
        # 1 refund + 1 correction
        self.employee.write({
            'km_home_work': 40.0,
            'marital': 'cohabitant',
            'spouse_fiscal_status': 'high_income',
            'children': 0,
        })

        self.contract.write({
            'name': "Full Time Parental Time Off",
            'time_credit': True,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'work_time_rate': 0,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_parental_time_off').id,
            'wage_on_signature': 2821.00,
            'wage': 2821.00,
            'resource_calendar_id': self.resource_calendar_0_hours_per_week.id,
            'date_start': datetime.date(2022, 1, 3),
            'date_end': datetime.date(2022, 4, 2),
            'car_id': False,
            'transport_mode_car': False,
            'fuel_card': 0,
            'internet': 0,
            'representation_fees': 399.0,
            'mobile': 0,
            'meal_voucher_amount': 8.0,
            'ip_wage_rate': 12.0,
            'ip': True,
            'commission_on_target': 1533.0,
            'transport_mode_public': True,
            'public_transport_employee_amount': 49.0,
            'transport_mode_private_car': True,
        })

        partial_contract = self.env['hr.contract'].create([{
            'name': "Partial Contract For Payslip Test",
            'employee_id': self.employee.id,
            'resource_calendar_id': self.resource_calendar_4_5_friday_off.id,
            'time_credit': True,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_parental_time_off').id,
            'company_id': self.env.company.id,
            'date_generated_from': datetime.datetime(2022, 9, 1, 0, 0, 0),
            'date_generated_to': datetime.datetime(2022, 9, 1, 0, 0, 0),
            'car_id': False,
            'structure_type_id': self.env.ref('hr_contract.structure_type_employee_cp200').id,
            'date_start': datetime.date(2022, 4, 3),
            'date_end': datetime.date(2022, 9, 2),
            'wage': 2851.71,
            'wage_on_signature': 2851.71,
            'state': "open",
            'transport_mode_car': False,
            'fuel_card': 0,
            'internet': 0,
            'representation_fees': 399.0,
            'mobile': 0,
            'meal_voucher_amount': 8.0,
            'eco_checks': 250.0,
            'ip_wage_rate': 12.0,
            'ip': True,
            'commission_on_target': 1433.33,
            'transport_mode_public': True,
            'public_transport_employee_amount': 49.0,
            'transport_mode_private_car': True,
        }])

        (self.contract + partial_contract).generate_work_entries(datetime.date(2022, 4, 1), datetime.date(2022, 4, 30))
        payslip_1 = self.env['hr.payslip'].create([{
            'name': "Test Payslip 1",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'date_from': datetime.date(2022, 4, 1),
            'date_to': datetime.date(2022, 4, 30),
        }])
        payslip_2 = self.env['hr.payslip'].create([{
            'name': "Test Payslip 2",
            'employee_id': self.employee.id,
            'contract_id': partial_contract.id,
            'company_id': self.env.company.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'date_from': datetime.date(2022, 4, 1),
            'date_to': datetime.date(2022, 4, 30),
        }])
        (payslip_1 + payslip_2).compute_sheet()

        payslip_1_results = {
            'BASIC': 0.0,
            'SALARY': 0.0,
            'ONSS': 0.0,
            'ONSSTOTAL': 0.0,
            'GROSSIP': 0.0,
            'IP.PART': 0.0,
            'GROSS': 0.0,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'M.ONSS': 0.0,
            'MEAL_V_EMP': 0.0,
            'PUB.TRANS': 0.0,
            'CAR.PRIV': 0.0,
            'REP.FEES': 0.0,
            'IP': 0.0,
            'IP.DED': 0.0,
            'NET': 0.0,
            'REMUNERATION': 0.0,
            'ONSSEMPLOYERBASIC': 0.0,
            'ONSSEMPLOYERFFE': 0.0,
            'ONSSEMPLOYERMFFE': 0.0,
            'ONSSEMPLOYERCPAE': 0.0,
            'ONSSEMPLOYERRESTREINT': 0.0,
            'ONSSEMPLOYERUNEMP': 0.0,
            'ONSSEMPLOYER': 0.0,
        }
        payslip_2_results = {
            'BASIC': 2720.09,
            'SALARY': 2720.09,
            'ONSS': -355.52,
            'EmpBonus.1': 0,
            'ONSSTOTAL': 355.52,
            'GROSSIP': 2364.57,
            'IP.PART': -326.41,
            'GROSS': 2038.16,
            'P.P': -316.67,
            'PPTOTAL': 316.67,
            'M.ONSS': -20.27,
            'MEAL_V_EMP': -17.44,
            'PUB.TRANS': 34.0,
            'CAR.PRIV': 41.27,
            'REP.FEES': 279.31,
            'REP.FEES.VOLATILE': 4.59,
            'IP': 326.41,
            'IP.DED': -24.48,
            'NET': 2344.88,
            'REMUNERATION': 2393.68,
            'ONSSEMPLOYERBASIC': 680.84,
            'ONSSEMPLOYERFFE': 1.9,
            'ONSSEMPLOYERMFFE': 2.72,
            'ONSSEMPLOYERCPAE': 6.26,
            'ONSSEMPLOYERRESTREINT': 45.97,
            'ONSSEMPLOYERUNEMP': 2.72,
            'ONSSEMPLOYER': 740.41,
        }
        self._validate_payslip(payslip_1, payslip_1_results)
        self._validate_payslip(payslip_2, payslip_2_results)

        action_refund_payslip_2 = payslip_2.refund_sheet()
        refund_payslip = self.env['hr.payslip'].browse(action_refund_payslip_2['domain'][0][2])

        refund_payslip_results = {
            'BASIC': -2720.09,
            'SALARY': -2720.09,
            'ONSS': 355.52,
            'EmpBonus.1': 0,
            'ONSSTOTAL': -355.52,
            'GROSSIP': -2364.57,
            'IP.PART': 326.41,
            'GROSS': -2038.16,
            'P.P': 316.67,
            'PPTOTAL': -316.67,
            'M.ONSS': 20.27,
            'MEAL_V_EMP': 17.44,
            'PUB.TRANS': -34.0,
            'CAR.PRIV': -41.27,
            'REP.FEES': -279.31,
            'REP.FEES.VOLATILE': -4.59,
            'IP': -326.41,
            'IP.DED': 24.48,
            'NET': -2344.88,
            'REMUNERATION': -2393.68,
            'ONSSEMPLOYERBASIC': -680.84,
            'ONSSEMPLOYERFFE': -1.9,
            'ONSSEMPLOYERMFFE': -2.72,
            'ONSSEMPLOYERCPAE': -6.26,
            'ONSSEMPLOYERRESTREINT': -45.97,
            'ONSSEMPLOYERUNEMP': -2.72,
            'ONSSEMPLOYER': -740.41,
        }
        self._validate_payslip(refund_payslip, refund_payslip_results)

        new_payslip_2 = self.env['hr.payslip'].create([{
            'name': "New Test Payslip 2",
            'employee_id': self.employee.id,
            'contract_id': partial_contract.id,
            'company_id': self.env.company.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'date_from': datetime.date(2022, 4, 1),
            'date_to': datetime.date(2022, 4, 30),
        }])
        new_payslip_2.compute_sheet()

        new_payslip_2_results = {
            'BASIC': 2720.09,
            'SALARY': 2720.09,
            'ONSS': -355.52,
            'EmpBonus.1': 0,
            'ONSSTOTAL': 355.52,
            'GROSSIP': 2364.57,
            'IP.PART': -326.41,
            'GROSS': 2038.16,
            'P.P': -316.67,
            'PPTOTAL': 316.67,
            'M.ONSS': -20.27,
            'MEAL_V_EMP': -17.44,
            'PUB.TRANS': 34.0,
            'CAR.PRIV': 41.27,
            'REP.FEES': 279.31,
            'REP.FEES.VOLATILE': 4.59,
            'IP': 326.41,
            'IP.DED': -24.48,
            'NET': 2344.88,
            'REMUNERATION': 2393.68,
            'ONSSEMPLOYERBASIC': 680.84,
            'ONSSEMPLOYERFFE': 1.9,
            'ONSSEMPLOYERMFFE': 2.72,
            'ONSSEMPLOYERCPAE': 6.26,
            'ONSSEMPLOYERRESTREINT': 45.97,
            'ONSSEMPLOYERUNEMP': 2.72,
            'ONSSEMPLOYER': 740.41,
        }
        self._validate_payslip(new_payslip_2, new_payslip_2_results)

    def test_company_car_pp_exemption_2021(self):
        payslip = self._generate_payslip(datetime.date(2022, 5, 1), datetime.date(2022, 5, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 32)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'EmpBonus.1': 43.75,
            'ONSSTOTAL': 303.78,
            'ATN.CAR': 162.42,
            'GROSSIP': 2517.64,
            'IP.PART': -662.5,
            'GROSS': 1855.14,
            'P.P': -239.63,
            'P.P.DED': 14.5,
            'PPTOTAL': 225.13,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -23.98,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2182.03,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.55,
            'ONSSEMPLOYERFFE': 1.86,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 723.78,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_company_car_cycle_capped(self):
        payslip = self._generate_payslip(datetime.date(2022, 5, 1), datetime.date(2022, 5, 31))
        payslip.write({
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_input_cycle_transportation').id,
                'amount': 2,
            })]
        })
        payslip.compute_sheet()
        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 1)
        self.assertEqual(len(payslip.line_ids), 33)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'EmpBonus.1': 43.75,
            'ONSSTOTAL': 303.78,
            'ATN.CAR': 162.42,
            'GROSSIP': 2517.64,
            'IP.PART': -662.5,
            'GROSS': 1855.14,
            'P.P': -239.63,
            'P.P.DED': 14.5,
            'PPTOTAL': 225.13,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -23.98,
            'CYCLE': 8.0,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2190.03,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.55,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERFFE': 1.86,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 723.78,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_company_car_cycle_uncapped(self):
        self.employee.km_home_work = 5
        payslip = self._generate_payslip(datetime.date(2022, 5, 1), datetime.date(2022, 5, 31))
        payslip.write({
            'input_line_ids': [(0, 0, {
                'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_input_cycle_transportation').id,
                'amount': 2,
            })]
        })
        payslip.compute_sheet()
        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 1)
        self.assertEqual(len(payslip.line_ids), 33)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'EmpBonus.1': 43.75,
            'ONSSTOTAL': 303.78,
            'ATN.CAR': 162.42,
            'GROSSIP': 2517.64,
            'IP.PART': -662.5,
            'GROSS': 1855.14,
            'P.P': -239.63,
            'P.P.DED': 14.5,
            'PPTOTAL': 225.13,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -23.98,
            'CYCLE': 5.0,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2187.03,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.55,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERFFE': 1.86,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 723.78,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_representation_fees_two_weeks_calendar(self):
        self.contract.resource_calendar_id = self.resource_calendar_9_10_monday_off
        self.contract.representation_fees = 399
        payslip = self._generate_payslip(datetime.date(2022, 5, 1), datetime.date(2022, 5, 31))
        payslip.compute_sheet()
        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(payslip.worked_days_line_ids.number_of_days, 20) # Instead of 22
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 33)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'EmpBonus.1': 43.75,
            'ONSSTOTAL': 303.78,
            'ATN.CAR': 162.42,
            'GROSSIP': 2517.64,
            'IP.PART': -662.5,
            'GROSS': 1855.14,
            'P.P': -239.63,
            'P.P.DED': 14.5,
            'PPTOTAL': 225.13,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 279.31,
            'REP.FEES.VOLATILE': 107.72,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2421.24,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.55,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERFFE': 1.86,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 723.78,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_representation_fees_two_weeks_calendar_credit_time(self):
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_9_10_monday_off.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week,
            'time_credit': True,
            'work_time_rate': 90,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_parental_time_off').id,
            'representation_fees': 399,
        })
        payslip = self._generate_payslip(datetime.date(2022, 5, 1), datetime.date(2022, 5, 31))
        payslip.compute_sheet()
        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 33)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'EmpBonus.1': 43.75,
            'ONSSTOTAL': 303.78,
            'ATN.CAR': 162.42,
            'GROSSIP': 2517.64,
            'IP.PART': -662.5,
            'GROSS': 1855.14,
            'P.P': -239.63,
            'P.P.DED': 14.5,
            'PPTOTAL': 225.13,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 279.31,
            'REP.FEES.VOLATILE': 107.41,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2420.93,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.55,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERFFE': 1.86,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 723.78,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_representation_fees_strange_two_weeks_calendar_credit_time(self):
        self.contract.write({
            'resource_calendar_id': self.resource_calendar_9_10_strange.id,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week,
            'time_credit': True,
            'work_time_rate': 90,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_parental_time_off').id,
            'representation_fees': 399,
        })
        payslip = self._generate_payslip(datetime.date(2022, 5, 1), datetime.date(2022, 5, 31))
        payslip.compute_sheet()
        self.assertEqual(len(payslip.worked_days_line_ids), 3) # Work entries are overlapping
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 33)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'EmpBonus.1': 43.75,
            'ONSSTOTAL': 303.78,
            'ATN.CAR': 162.42,
            'GROSSIP': 2517.64,
            'IP.PART': -662.5,
            'GROSS': 1855.14,
            'P.P': -239.63,
            'P.P.DED': 14.5,
            'PPTOTAL': 225.13,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -23.98,
            'REP.FEES': 279.31,
            'REP.FEES.VOLATILE': 107.41,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2418.75,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.55,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERFFE': 1.86,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 723.78,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_relapse_without_guaranteed_salary_split_time_off(self):
        # Check when the employee is always sick, but with split time off
        # Sick 3 days (27 - 29 April 2022)
        # Sick 1 week (2 - 6 May)
        # Sick 2 weeks (7 - 20 May)
        # Sick 4 week (21 May - 17 June)

        bank_holiday = self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday')
        attendance = self.env.ref('hr_work_entry.work_entry_type_attendance')
        sick_work_entry_type = self.env.ref('hr_work_entry_contract.work_entry_type_sick_leave')
        partial_sick_work_entry_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_part_sick')

        self.env['resource.calendar.leaves'].create([{
            'name': "Easter Monday",
            'calendar_id': False,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2022, 4, 18, 5, 0, 0),
            'date_to': datetime.datetime(2022, 4, 18, 18, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': bank_holiday.id
        }, {
            'name': "Ascension Day",
            'calendar_id': False,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2022, 5, 26, 5, 0, 0),
            'date_to': datetime.datetime(2022, 5, 26, 18, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': bank_holiday.id
        }])

        sick_leave_1 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 3 days',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2022, 4, 27),
            'request_date_to': datetime.date(2022, 4, 29),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 3,
        })

        sick_leave_1._compute_date_from_to()
        sick_leave_1 = self.env['hr.leave'].create(sick_leave_1._convert_to_write(sick_leave_1._cache))

        sick_leave_2 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 1 Week',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2022, 5, 2),
            'request_date_to': datetime.date(2022, 5, 6),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 5,
        })
        sick_leave_2._compute_date_from_to()
        sick_leave_2 = self.env['hr.leave'].create(sick_leave_2._convert_to_write(sick_leave_2._cache))

        sick_leave_3 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 2 Week',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2022, 5, 7),
            'request_date_to': datetime.date(2022, 5, 20),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 10,
        })
        sick_leave_3._compute_date_from_to()
        sick_leave_3 = self.env['hr.leave'].create(sick_leave_3._convert_to_write(sick_leave_3._cache))

        sick_leave_4 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 4 Week',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2022, 5, 21),
            'request_date_to': datetime.date(2022, 6, 17),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 20,
        })
        sick_leave_4._compute_date_from_to()
        sick_leave_4 = self.env['hr.leave'].create(sick_leave_4._convert_to_write(sick_leave_4._cache))

        (sick_leave_1 + sick_leave_2 + sick_leave_3 + sick_leave_4).action_validate()

        work_entries = self.employee.contract_id.generate_work_entries(datetime.date(2022, 4, 1), datetime.date(2022, 6, 30))

        work_entries_expected_results = {
            # Attendances
            (1, 4): attendance,

            (4, 4): attendance,
            (5, 4): attendance,
            (6, 4): attendance,
            (7, 4): attendance,
            (8, 4): attendance,

            (11, 4): attendance,
            (12, 4): attendance,
            (13, 4): attendance,
            (14, 4): attendance,
            (15, 4): attendance,

            (18, 4): bank_holiday,
            (19, 4): attendance,
            (20, 4): attendance,
            (21, 4): attendance,
            (22, 4): attendance,

            # 1rs time off
            (25, 4): attendance,
            (26, 4): attendance,
            (27, 4): sick_work_entry_type,
            (28, 4): sick_work_entry_type,
            (29, 4): sick_work_entry_type,
            # 2nd time off
            (2, 5): sick_work_entry_type,
            (3, 5): sick_work_entry_type,
            (4, 5): sick_work_entry_type,
            (5, 5): sick_work_entry_type,
            (6, 5): sick_work_entry_type,
            # 3rd time off
            (9, 5): sick_work_entry_type,
            (10, 5): sick_work_entry_type,
            (11, 5): sick_work_entry_type,
            (12, 5): sick_work_entry_type,
            (13, 5): sick_work_entry_type,

            (16, 5): sick_work_entry_type,
            (17, 5): sick_work_entry_type,
            (18, 5): sick_work_entry_type,
            (19, 5): sick_work_entry_type,
            (20, 5): sick_work_entry_type,
            # 4th time off
            (23, 5): sick_work_entry_type,
            (24, 5): sick_work_entry_type,
            (25, 5): sick_work_entry_type,
            (26, 5): bank_holiday,
            (27, 5): partial_sick_work_entry_type,

            (30, 5): partial_sick_work_entry_type,
            (31, 5): partial_sick_work_entry_type,
            (1, 6): partial_sick_work_entry_type,
            (2, 6): partial_sick_work_entry_type,
            (3, 6): partial_sick_work_entry_type,

            (6, 6): partial_sick_work_entry_type,
            (7, 6): partial_sick_work_entry_type,
            (8, 6): partial_sick_work_entry_type,
            (9, 6): partial_sick_work_entry_type,
            (10, 6): partial_sick_work_entry_type,

            (13, 6): partial_sick_work_entry_type,
            (14, 6): partial_sick_work_entry_type,
            (15, 6): partial_sick_work_entry_type,
            (16, 6): partial_sick_work_entry_type,
            (17, 6): partial_sick_work_entry_type,

            # Come back
            (20, 6): attendance,
            (21, 6): attendance,
            (22, 6): attendance,
            (23, 6): attendance,
            (24, 6): attendance,

            (27, 6): attendance,
            (28, 6): attendance,
            (29, 6): attendance,
            (30, 6): attendance,
        }

        for we in work_entries:
            self.assertEqual(
                we.work_entry_type_id,
                work_entries_expected_results[(we.date_start.day, we.date_start.month)],
                'On %s/%s, expected work entry type %s, got %s instead' % (we.date_start.day, we.date_start.month, work_entries_expected_results[(we.date_start.day, we.date_start.month)].name, we.work_entry_type_id.name))

        april_payslip = self._generate_payslip(datetime.date(2022, 4, 1), datetime.date(2022, 4, 30))

        self.assertEqual(len(april_payslip.worked_days_line_ids), 3)
        self.assertEqual(len(april_payslip.input_line_ids), 0)
        self.assertEqual(len(april_payslip.line_ids), 32)

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'EmpBonus.1': 43.75,
            'ONSSTOTAL': 303.78,
            'ATN.CAR': 162.42,
            'GROSSIP': 2517.64,
            'IP.PART': -662.5,
            'GROSS': 1855.14,
            'P.P': -239.63,
            'P.P.DED': 14.5,
            'PPTOTAL': 225.13,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -18.53,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2187.48,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.55,
            'ONSSEMPLOYERFFE': 1.86,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 723.78,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(april_payslip, payslip_results)

        may_payslip = self._generate_payslip(datetime.date(2022, 5, 1), datetime.date(2022, 5, 31))

        self.assertEqual(len(may_payslip.worked_days_line_ids), 3)
        self.assertEqual(len(may_payslip.input_line_ids), 0)
        self.assertEqual(len(may_payslip.line_ids), 32)

        payslip_results = {
            'BASIC': 2283.08,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2292.08,
            'ONSS': -299.57,
            'EmpBonus.1': 38.79,
            'ONSSTOTAL': 260.79,
            'ATN.CAR': 162.42,
            'GROSSIP': 2193.71,
            'IP.PART': -570.77,
            'GROSS': 1622.94,
            'P.P': -143.33,
            'P.P.DED': 12.85,
            'PPTOTAL': 130.48,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -11.35,
            'MEAL_V_EMP': 0.0,
            'REP.FEES': 150.0,
            'IP': 570.77,
            'IP.DED': -42.81,
            'NET': 1987.65,
            'REMUNERATION': 1712.31,
            'ONSSEMPLOYERBASIC': 573.71,
            'ONSSEMPLOYERFFE': 1.6,
            'ONSSEMPLOYERMFFE': 2.29,
            'ONSSEMPLOYERCPAE': 5.27,
            'ONSSEMPLOYERRESTREINT': 38.74,
            'ONSSEMPLOYERUNEMP': 2.29,
            'ONSSEMPLOYER': 623.9,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(may_payslip, payslip_results)

        june_payslip = self._generate_payslip(datetime.date(2022, 5, 1), datetime.date(2022, 5, 31))

        self.assertEqual(len(june_payslip.worked_days_line_ids), 3)
        self.assertEqual(len(june_payslip.input_line_ids), 0)
        self.assertEqual(len(june_payslip.line_ids), 32)

        payslip_results = {
            'BASIC': 2283.08,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2292.08,
            'ONSS': -299.57,
            'EmpBonus.1': 38.79,
            'ONSSTOTAL': 260.79,
            'ATN.CAR': 162.42,
            'GROSSIP': 2193.71,
            'IP.PART': -570.77,
            'GROSS': 1622.94,
            'P.P': -143.33,
            'P.P.DED': 12.85,
            'PPTOTAL': 130.48,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -11.35,
            'MEAL_V_EMP': 0.0,
            'REP.FEES': 150.0,
            'IP': 570.77,
            'IP.DED': -42.81,
            'NET': 1987.65,
            'REMUNERATION': 1712.31,
            'ONSSEMPLOYERBASIC': 573.71,
            'ONSSEMPLOYERFFE': 1.6,
            'ONSSEMPLOYERMFFE': 2.29,
            'ONSSEMPLOYERCPAE': 5.27,
            'ONSSEMPLOYERRESTREINT': 38.74,
            'ONSSEMPLOYERUNEMP': 2.29,
            'ONSSEMPLOYER': 623.9,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(june_payslip, payslip_results)

    def test_strike_days(self):
        strike_leave = self.env['hr.leave'].new({
            'name': 'Strike Day',
            'employee_id': self.employee.id,
            'holiday_status_id': self.env.ref('l10n_be_hr_payroll.holiday_type_strike').id,
            'request_date_from': datetime.date(2022, 5, 17),
            'request_date_to': datetime.date(2022, 5, 17),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 1,
        })
        strike_leave._compute_date_from_to()
        strike_leave = self.env['hr.leave'].create(strike_leave._convert_to_write(strike_leave._cache))
        strike_leave.action_validate()

        payslip = self._generate_payslip(datetime.date(2022, 5, 1), datetime.date(2022, 5, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        self.assertEqual(len(payslip.input_line_ids), 0)
        self.assertEqual(len(payslip.line_ids), 32)

        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE251'), 0.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_days('LEAVE251'), 1.0, places=2)
        self.assertAlmostEqual(payslip._get_worked_days_line_number_of_hours('LEAVE251'), 7.6, places=2)

        payslip_results = {
            'BASIC': 2527.69,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2536.69,
            'ONSS': -331.55,
            'EmpBonus.1': 42.1,
            'ONSSTOTAL': 289.45,
            'ATN.CAR': 162.42,
            'GROSSIP': 2409.66,
            'IP.PART': -631.92,
            'GROSS': 1777.74,
            'P.P': -207.53,
            'P.P.DED': 13.95,
            'PPTOTAL': 193.58,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -14.04,
            'MEAL_V_EMP': -22.89,
            'REP.FEES': 150.0,
            'IP': 631.92,
            'IP.DED': -47.39,
            'NET': 2110.33,
            'REMUNERATION': 1895.77,
            'ONSSEMPLOYERBASIC': 634.93,
            'ONSSEMPLOYERFFE': 1.78,
            'ONSSEMPLOYERMFFE': 2.54,
            'ONSSEMPLOYERCPAE': 5.83,
            'ONSSEMPLOYERRESTREINT': 42.87,
            'ONSSEMPLOYERUNEMP': 2.54,
            'ONSSEMPLOYER': 690.49,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_double_holidays_commission_first_incomplete_month(self):
        # If a payslip (first one or mid-month signing is incomplete and has commissions
        # take them into account
        self.contract.write({
            'date_start': datetime.date(2021, 12, 7),
            'commission_on_target': 1500,
        })

        payslip = self._generate_payslip(datetime.date(2021, 12, 1), datetime.date(2021, 12, 31))
        payslip.input_line_ids = [(0, 0, {
            'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
            'amount': 300,
        })]
        payslip.compute_sheet()
        payslip.action_payslip_done()

        double_payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2022, 6, 1),
            'date_to': datetime.date(2022, 6, 30)
        })
        double_payslip.compute_sheet()

        payslip_results = {
            'BASIC': 0.0,
            'SALARY': 0.0,
            'ONSS': 0.0,
            'GROSS': 0.0,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'NET': 0.0,
        }
        self._validate_payslip(double_payslip, payslip_results)

    def test_double_holidays_full_time_credit_time(self):
        # Check that a full time credit time is not taken into account
        # on the number of occupation months
        self.contract.write({
            'name': "Full Time Parental Time Off",
            'time_credit': True,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'work_time_rate': 0,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_parental_time_off').id,
            'resource_calendar_id': self.resource_calendar_0_hours_per_week.id,
            'date_start': datetime.date(2021, 1, 1),
        })

        double_payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2022, 6, 1),
            'date_to': datetime.date(2022, 6, 30)
        })
        double_payslip.compute_sheet()

        payslip_results = {
            'BASIC': 0.0,
            'SALARY': 0.0,
            'ONSS': 0.0,
            'GROSS': 0.0,
            'P.P': 0.0,
            'PPTOTAL': 0.0,
            'NET': 0.0,
        }
        self._validate_payslip(double_payslip, payslip_results)

    def test_double_holidays_european_time_off_current_year(self):
        # Check that european time off taken on the current year
        # are not recovered on the double holiday pay (and left for next year)
        self.contract.generate_work_entries(datetime.date(2020, 5, 1), datetime.date(2022, 6, 30))

        european_time_off = self.env['hr.leave'].create({
            'name': 'European Time Off',
            'holiday_status_id': self.european_time_off_type.id,
            'request_date_from': '2022-5-9',
            'request_date_to': '2022-5-12',
            'employee_id': self.employee.id,
        })
        european_time_off.action_validate()

        european_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip',
            'contract_id': self.contract.id,
            'date_from': datetime.datetime(2022, 5, 1),
            'date_to': datetime.datetime(2022, 5, 31),
            'employee_id': self.employee.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id,
            'company_id': self.env.company.id,
        })
        european_payslip.action_refresh_from_work_entries()
        european_payslip.action_payslip_done()
        self.assertEqual(european_payslip.worked_days_line_ids.filtered(lambda wd: wd.code == 'LEAVE216').amount, 489.23)

        payslip = self.env['hr.payslip'].create({
            'name': "Test Payslip",
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'company_id': self.env.company.id,
            'vehicle_id': self.car.id,
            'struct_id': self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id,
            'date_from': datetime.date(2022, 6, 1),
            'date_to': datetime.date(2022, 6, 30)
        })
        payslip.compute_sheet()

        self.assertEqual(len(payslip.input_line_ids), 0)
        payslip_results = {
            'BASIC': 2438.0,
            'SALARY': 2252.5,
            'ONSS': -294.4,
            'GROSS': 2143.6,
            'P.P': -908.67,
            'PPTOTAL': 908.67,
            'NET': 1234.93,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_cycle_private_car(self):
        # Test that cycle days are removed from private car reimbursement
        self.contract.write({
            'transport_mode_car': False,
            'transport_mode_private_car': True,
        })
        payslip = self._generate_payslip(datetime.date(2022, 7, 1), datetime.date(2022, 7, 31))
        payslip.input_line_ids = [(0, 0, {
            'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_input_cycle_transportation').id,
            'amount': 2,
        })]
        payslip.compute_sheet()

        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'EmpBonus.1': 43.75,
            'ONSSTOTAL': 303.78,
            'GROSSIP': 2355.22,
            'IP.PART': -662.5,
            'GROSS': 1692.72,
            'P.P': -169.01,
            'P.P.DED': 14.5,
            'PPTOTAL': 154.51,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -22.89,
            'CAR.PRIV': 93.04,
            'CYCLE': 16.0,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2362.78,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.55,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERFFE': 1.86,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 723.78,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_simple_n1_holiday_pay_recovery_half_days(self):
        # Check that half days AND full days are taken into account
        self.contract.date_start = datetime.date(2022, 1, 1)
        self.employee.l10n_be_holiday_pay_to_recover_n1 = 1000
        self.employee.l10n_be_holiday_pay_number_of_days_n1 = 5

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal Leave Half Day",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 7, 22, 6, 0, 0), # utc + 2
            'date_to': datetime.datetime(2022, 7, 22, 10, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }, {
            'name': "Legal Leave Whole Day",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 7, 20, 6, 0, 0),
            'date_to': datetime.datetime(2022, 7, 20, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2022, 7, 1), datetime.date(2022, 7, 31))
        self.assertEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 7.6 + 4)
        self.assertEqual(payslip._get_worked_days_line_amount('LEAVE120'), 122.31 + 64.37)

        payslip_results = {
            'BASIC': 2650.0,
            'HolPayRecN1': -186.68,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2472.32,
            'ONSS': -323.13,
            'EmpBonus.1': 86.93,
            'ONSSTOTAL': 236.2,
            'ATN.CAR': 162.42,
            'GROSSIP': 2398.54,
            'IP.PART': -662.5,
            'GROSS': 1736.04,
            'P.P': -188.27,
            'P.P.DED': 28.81,
            'PPTOTAL': 159.46,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2130.78,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 618.82,
            'ONSSEMPLOYERFFE': 1.73,
            'ONSSEMPLOYERMFFE': 2.47,
            'ONSSEMPLOYERCPAE': 5.69,
            'ONSSEMPLOYERRESTREINT': 41.78,
            'ONSSEMPLOYERUNEMP': 2.47,
            'ONSSEMPLOYER': 672.97,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_simple_n1_holiday_pay_recovery_higher_salary(self):
        # Check that half days AND full days are taken into account
        self.contract.date_start = datetime.date(2022, 1, 1)
        # Employee received 10€ for 5 days of holidays from previous employer
        # The salary being higher in his current company, the HolidayPayRecN1 shouldn't exceed 10€
        self.employee.l10n_be_holiday_pay_to_recover_n1 = 10
        self.employee.l10n_be_holiday_pay_number_of_days_n1 = 5

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal Leave Half Day",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 7, 22, 6, 0, 0), # utc + 2
            'date_to': datetime.datetime(2022, 7, 22, 10, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }, {
            'name': "Legal Leave Whole Day",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 7, 20, 6, 0, 0),
            'date_to': datetime.datetime(2022, 7, 20, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2022, 7, 1), datetime.date(2022, 7, 31))
        self.assertEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 7.6 + 4)
        self.assertEqual(payslip._get_worked_days_line_amount('LEAVE120'), 122.31 + 64.37)

        payslip_results = {
            'BASIC': 2650.0,
            'HolPayRecN1': -10.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2649.0,
            'ONSS': -346.22,
            'EmpBonus.1': 46.06,
            'ONSSTOTAL': 300.16,
            'ATN.CAR': 162.42,
            'GROSSIP': 2511.26,
            'IP.PART': -662.5,
            'GROSS': 1848.76,
            'P.P': -239.63,
            'P.P.DED': 15.27,
            'PPTOTAL': 224.36,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2178.6,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 663.04,
            'ONSSEMPLOYERFFE': 1.85,
            'ONSSEMPLOYERMFFE': 2.65,
            'ONSSEMPLOYERCPAE': 6.09,
            'ONSSEMPLOYERRESTREINT': 44.77,
            'ONSSEMPLOYERUNEMP': 2.65,
            'ONSSEMPLOYER': 721.06,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_simple_n1_holiday_pay_recovery_lower_salary(self):
        self.contract.date_start = datetime.date(2022, 1, 1)
        # Employee received 10 000€ for 2 days of holidays from the previous employer
        # The salary being lower in his current company, the HolidayPayRecN1 shouldn't exceed the employee cost for the 5 days
        self.employee.l10n_be_holiday_pay_to_recover_n1 = 10000
        self.employee.l10n_be_holiday_pay_number_of_days_n1 = 2

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal Leave Full Week",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 7, 18, 6, 0, 0),
            'date_to': datetime.datetime(2022, 7, 22, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2022, 7, 1), datetime.date(2022, 7, 31))
        self.assertEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 7.6 * 5)
        self.assertEqual(payslip._get_worked_days_line_amount('LEAVE120'), 611.54)

        payslip_results = {
            'BASIC': 2650.0,
            'HolPayRecN1': -252.38,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2406.62,
            'ONSS': -314.55,
            'EmpBonus.1': 102.13,
            'ONSSTOTAL': 212.42,
            'ATN.CAR': 162.42,
            'GROSSIP': 2356.62,
            'IP.PART': -662.5,
            'GROSS': 1694.12,
            'P.P': -169.01,
            'P.P.DED': 33.84,
            'PPTOTAL': 135.17,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -17.44,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2117.52,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 602.38,
            'ONSSEMPLOYERFFE': 1.68,
            'ONSSEMPLOYERMFFE': 2.41,
            'ONSSEMPLOYERCPAE': 5.54,
            'ONSSEMPLOYERRESTREINT': 40.67,
            'ONSSEMPLOYERUNEMP': 2.41,
            'ONSSEMPLOYER': 655.08,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_simple_n1_holiday_pay_recovery_lower_salary_2_payslips(self):
        self.contract.date_start = datetime.date(2022, 1, 1)
        # Employee received 10 000€ for 3 days of holidays from the previous employer
        # Employee took 2 days on september (so the HolidayPayRecN1 should be equal to the right amount for 2 days)
        # Employee took 2 days on october (so the HolidayPayRecN1 shouldn't exceed the employee cost for the 2 days)
        # Employee took 4 days on november (so the HolidayPayRecN1 should be equal to 0)
        self.employee.l10n_be_holiday_pay_to_recover_n1 = 10000
        self.employee.l10n_be_holiday_pay_number_of_days_n1 = 3

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal leave 2 days september",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 9, 19, 6, 0, 0),
            'date_to': datetime.datetime(2022, 9, 20, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal leave 2 days october",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 10, 12, 6, 0, 0),
            'date_to': datetime.datetime(2022, 10, 13, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal leave 4 days november",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 11, 8, 6, 0, 0),
            'date_to': datetime.datetime(2022, 11, 11, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2022, 9, 1), datetime.date(2022, 9, 30))
        payslip.action_payslip_done()
        self.assertEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 7.6 * 2)
        self.assertEqual(payslip._get_worked_days_line_amount('LEAVE120'), 244.62)

        payslip_results = {
            'BASIC': 2650.0,
            'HolPayRecN1': -240.91,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2418.09,
            'ONSS': -316.04,
            'EmpBonus.1': 126.09,
            'ONSSTOTAL': 189.96,
            'ATN.CAR': 162.42,
            'GROSSIP': 2390.56,
            'IP.PART': -662.5,
            'GROSS': 1728.06,
            'P.P': -188.27,
            'P.P.DED': 41.79,
            'PPTOTAL': 146.48,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2135.77,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 605.25,
            'ONSSEMPLOYERFFE': 1.69,
            'ONSSEMPLOYERMFFE': 2.42,
            'ONSSEMPLOYERCPAE': 5.56,
            'ONSSEMPLOYERRESTREINT': 40.87,
            'ONSSEMPLOYERUNEMP': 2.42,
            'ONSSEMPLOYER': 658.2,
            'CO2FEE': 28.17,
        }

        self._validate_payslip(payslip, payslip_results)

        payslip2 = self._generate_payslip(datetime.date(2022, 10, 1), datetime.date(2022, 10, 31))
        payslip2.action_payslip_done()
        self.assertEqual(payslip2._get_worked_days_line_number_of_hours('LEAVE120'), 7.6 * 2)
        self.assertEqual(payslip2._get_worked_days_line_amount('LEAVE120'), 244.62)

        payslip2_results = {
            'BASIC': 2650.0,
            'HolPayRecN1': -126.19,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2532.81,
            'ONSS': -331.04,
            'EmpBonus.1': 99.55,
            'ONSSTOTAL': 231.49,
            'ATN.CAR': 162.42,
            'GROSSIP': 2463.75,
            'IP.PART': -662.5,
            'GROSS': 1801.25,
            'P.P': -220.37,
            'P.P.DED': 32.99,
            'PPTOTAL': 187.38,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -20.71,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2169.16,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 633.96,
            'ONSSEMPLOYERFFE': 1.77,
            'ONSSEMPLOYERMFFE': 2.53,
            'ONSSEMPLOYERCPAE': 5.83,
            'ONSSEMPLOYERRESTREINT': 42.8,
            'ONSSEMPLOYERUNEMP': 2.53,
            'ONSSEMPLOYER': 689.43,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip2, payslip2_results)

        payslip3 = self._generate_payslip(datetime.date(2022, 11, 1), datetime.date(2022, 11, 30))
        self.assertEqual(payslip3._get_worked_days_line_number_of_hours('LEAVE120'), 7.6 * 4)
        self.assertEqual(payslip3._get_worked_days_line_amount('LEAVE120'), 489.23)

        payslip3_results = {
            'BASIC': 2650.0,
            'HolPayRecN1': 0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'EmpBonus.1': 84.07,
            'ONSSTOTAL': 263.47,
            'ATN.CAR': 162.42,
            'GROSSIP': 2557.96,
            'IP.PART': -662.5,
            'GROSS': 1895.46,
            'P.P': -258.89,
            'P.P.DED': 27.86,
            'PPTOTAL': 231.03,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -19.62,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2220.81,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.55,
            'ONSSEMPLOYERFFE': 1.86,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 723.78,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip3, payslip3_results)

    def test_simple_n_holiday_pay_recovery_half_days(self):
        # Check that half days AND full days are taken into account
        self.contract.date_start = datetime.date(2021, 1, 1)
        self.employee.l10n_be_holiday_pay_to_recover_n = 1000
        self.employee.l10n_be_holiday_pay_number_of_days_n = 5

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal Leave Half Day",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 7, 22, 6, 0, 0), # utc + 2
            'date_to': datetime.datetime(2022, 7, 22, 10, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }, {
            'name': "Legal Leave Whole Day",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 7, 20, 6, 0, 0),
            'date_to': datetime.datetime(2022, 7, 20, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2022, 7, 1), datetime.date(2022, 7, 31))
        self.assertEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 7.6 + 4)
        self.assertEqual(payslip._get_worked_days_line_amount('LEAVE120'), 122.31 + 64.37)

        payslip_results = {
            'BASIC': 2650.0,
            'HolPayRecN': -186.68,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2472.32,
            'ONSS': -323.13,
            'EmpBonus.1': 86.93,
            'ONSSTOTAL': 236.2,
            'ATN.CAR': 162.42,
            'GROSSIP': 2398.54,
            'IP.PART': -662.5,
            'GROSS': 1736.04,
            'P.P': -188.27,
            'P.P.DED': 28.81,
            'PPTOTAL': 159.46,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2130.78,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 618.82,
            'ONSSEMPLOYERFFE': 1.73,
            'ONSSEMPLOYERMFFE': 2.47,
            'ONSSEMPLOYERCPAE': 5.69,
            'ONSSEMPLOYERRESTREINT': 41.78,
            'ONSSEMPLOYERUNEMP': 2.47,
            'ONSSEMPLOYER': 672.97,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_simple_n_holiday_pay_recovery_higher_salary(self):
        # Check that half days AND full days are taken into account
        self.contract.date_start = datetime.date(2021, 1, 1)
        # Employee received 10€ for 5 days of holidays from previous employer
        # The salary being higher in his current company, the HolidayPayRecN1 shouldn't exceed 10€
        self.employee.l10n_be_holiday_pay_to_recover_n = 10
        self.employee.l10n_be_holiday_pay_number_of_days_n = 5

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal Leave Half Day",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 7, 22, 6, 0, 0), # utc + 2
            'date_to': datetime.datetime(2022, 7, 22, 10, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }, {
            'name': "Legal Leave Whole Day",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 7, 20, 6, 0, 0),
            'date_to': datetime.datetime(2022, 7, 20, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2022, 7, 1), datetime.date(2022, 7, 31))
        self.assertEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 7.6 + 4)
        self.assertEqual(payslip._get_worked_days_line_amount('LEAVE120'), 122.31 + 64.37)

        payslip_results = {
            'BASIC': 2650.0,
            'HolPayRecN': -10.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2649.0,
            'ONSS': -346.22,
            'EmpBonus.1': 46.06,
            'ONSSTOTAL': 300.16,
            'ATN.CAR': 162.42,
            'GROSSIP': 2511.26,
            'IP.PART': -662.5,
            'GROSS': 1848.76,
            'P.P': -239.63,
            'P.P.DED': 15.27,
            'PPTOTAL': 224.36,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2178.6,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 663.04,
            'ONSSEMPLOYERFFE': 1.85,
            'ONSSEMPLOYERMFFE': 2.65,
            'ONSSEMPLOYERCPAE': 6.09,
            'ONSSEMPLOYERRESTREINT': 44.77,
            'ONSSEMPLOYERUNEMP': 2.65,
            'ONSSEMPLOYER': 721.06,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_simple_n_holiday_pay_recovery_lower_salary(self):
        self.contract.date_start = datetime.date(2021, 1, 1)
        # Employee received 10 000€ for 2 days of holidays from the previous employer
        # The salary being lower in his current company, the HolidayPayRecN1 shouldn't exceed the employee cost for the 5 days
        self.employee.l10n_be_holiday_pay_to_recover_n = 10000
        self.employee.l10n_be_holiday_pay_number_of_days_n = 2

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal Leave Full Week",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 7, 18, 6, 0, 0),
            'date_to': datetime.datetime(2022, 7, 22, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2022, 7, 1), datetime.date(2022, 7, 31))
        self.assertEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 7.6 * 5)
        self.assertEqual(payslip._get_worked_days_line_amount('LEAVE120'), 611.54)

        payslip_results = {
            'BASIC': 2650.0,
            'HolPayRecN': -252.38,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2406.62,
            'ONSS': -314.55,
            'EmpBonus.1': 102.13,
            'ONSSTOTAL': 212.42,
            'ATN.CAR': 162.42,
            'GROSSIP': 2356.62,
            'IP.PART': -662.5,
            'GROSS': 1694.12,
            'P.P': -169.01,
            'P.P.DED': 33.84,
            'PPTOTAL': 135.17,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -17.44,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2117.52,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 602.38,
            'ONSSEMPLOYERFFE': 1.68,
            'ONSSEMPLOYERMFFE': 2.41,
            'ONSSEMPLOYERCPAE': 5.54,
            'ONSSEMPLOYERRESTREINT': 40.67,
            'ONSSEMPLOYERUNEMP': 2.41,
            'ONSSEMPLOYER': 655.08,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_simple_n_holiday_pay_recovery_lower_salary_2_payslips(self):
        self.contract.date_start = datetime.date(2021, 1, 1)
        # Employee received 10 000€ for 3 days of holidays from the previous employer
        # Employee took 2 days on september (so the HolidayPayRecN1 should be equal to the right amount for 2 days)
        # Employee took 2 days on october (so the HolidayPayRecN1 shouldn't exceed the employee cost for the 2 days)
        # Employee took 4 days on november (so the HolidayPayRecN1 should be equal to 0)
        self.employee.l10n_be_holiday_pay_to_recover_n = 10000
        self.employee.l10n_be_holiday_pay_number_of_days_n = 3

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal leave 2 days september",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 9, 19, 6, 0, 0),
            'date_to': datetime.datetime(2022, 9, 20, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal leave 2 days october",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 10, 12, 6, 0, 0),
            'date_to': datetime.datetime(2022, 10, 13, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal leave 4 days november",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2022, 11, 8, 6, 0, 0),
            'date_to': datetime.datetime(2022, 11, 11, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2022, 9, 1), datetime.date(2022, 9, 30))
        payslip.action_payslip_done()
        self.assertEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 7.6 * 2)
        self.assertEqual(payslip._get_worked_days_line_amount('LEAVE120'), 244.62)

        payslip_results = {
            'BASIC': 2650.0,
            'HolPayRecN': -240.91,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2418.09,
            'ONSS': -316.04,
            'EmpBonus.1': 126.09,
            'ONSSTOTAL': 189.96,
            'ATN.CAR': 162.42,
            'GROSSIP': 2390.56,
            'IP.PART': -662.5,
            'GROSS': 1728.06,
            'P.P': -188.27,
            'P.P.DED': 41.79,
            'PPTOTAL': 146.48,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2135.77,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 605.25,
            'ONSSEMPLOYERFFE': 1.69,
            'ONSSEMPLOYERMFFE': 2.42,
            'ONSSEMPLOYERCPAE': 5.56,
            'ONSSEMPLOYERRESTREINT': 40.87,
            'ONSSEMPLOYERUNEMP': 2.42,
            'ONSSEMPLOYER': 658.2,
            'CO2FEE': 28.17,
        }

        self._validate_payslip(payslip, payslip_results)

        payslip2 = self._generate_payslip(datetime.date(2022, 10, 1), datetime.date(2022, 10, 31))
        payslip2.action_payslip_done()
        self.assertEqual(payslip2._get_worked_days_line_number_of_hours('LEAVE120'), 7.6 * 2)
        self.assertEqual(payslip2._get_worked_days_line_amount('LEAVE120'), 244.62)

        payslip2_results = {
            'BASIC': 2650.0,
            'HolPayRecN': -126.19,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2532.81,
            'ONSS': -331.04,
            'EmpBonus.1': 99.55,
            'ONSSTOTAL': 231.49,
            'ATN.CAR': 162.42,
            'GROSSIP': 2463.75,
            'IP.PART': -662.5,
            'GROSS': 1801.25,
            'P.P': -220.37,
            'P.P.DED': 32.99,
            'PPTOTAL': 187.38,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -20.71,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2169.16,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 633.96,
            'ONSSEMPLOYERFFE': 1.77,
            'ONSSEMPLOYERMFFE': 2.53,
            'ONSSEMPLOYERCPAE': 5.83,
            'ONSSEMPLOYERRESTREINT': 42.8,
            'ONSSEMPLOYERUNEMP': 2.53,
            'ONSSEMPLOYER': 689.43,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip2, payslip2_results)

        payslip3 = self._generate_payslip(datetime.date(2022, 11, 1), datetime.date(2022, 11, 30))
        self.assertEqual(payslip3._get_worked_days_line_number_of_hours('LEAVE120'), 7.6 * 4)
        self.assertEqual(payslip3._get_worked_days_line_amount('LEAVE120'), 489.23)

        payslip3_results = {
            'BASIC': 2650.0,
            'HolPayRecN': 0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'EmpBonus.1': 84.07,
            'ONSSTOTAL': 263.47,
            'ATN.CAR': 162.42,
            'GROSSIP': 2557.96,
            'IP.PART': -662.5,
            'GROSS': 1895.46,
            'P.P': -258.89,
            'P.P.DED': 27.86,
            'PPTOTAL': 231.03,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -19.62,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2220.81,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.55,
            'ONSSEMPLOYERFFE': 1.86,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 723.78,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip3, payslip3_results)

    def test_refund_accounting_entries(self):
        payslip = self._generate_payslip(datetime.date(2022, 8, 1), datetime.date(2022, 8, 31))
        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'EmpBonus.1': 70.36,
            'ONSSTOTAL': 277.17,
            'ATN.CAR': 162.42,
            'GROSSIP': 2544.26,
            'IP.PART': -662.5,
            'GROSS': 1881.76,
            'P.P': -252.47,
            'P.P.DED': 23.32,
            'PPTOTAL': 229.15,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -25.07,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2203.54,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.55,
            'ONSSEMPLOYERFFE': 1.86,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 723.78,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

        payslip.action_payslip_done()

        net_account_move_line = payslip.move_id.line_ids.filtered(lambda l: l.name == 'Net Salary')
        self.assertAlmostEqual(net_account_move_line.debit, 0.0, places=2)
        self.assertAlmostEqual(net_account_move_line.credit, 2203.54, places=2)

        refund_action = payslip.refund_sheet()
        refund = self.env['hr.payslip'].browse(refund_action['domain'][0][2])
        payslip_results = {
            'BASIC': -2650.0,
            'ATN.INT': -5.0,
            'ATN.MOB': -4.0,
            'SALARY': -2659.0,
            'ONSS': 347.53,
            'EmpBonus.1': -70.36,
            'ONSSTOTAL': -277.17,
            'ATN.CAR': -162.42,
            'GROSSIP': -2544.26,
            'IP.PART': 662.5,
            'GROSS': -1881.76,
            'P.P': 252.47,
            'P.P.DED': -23.32,
            'PPTOTAL': -229.15,
            'ATN.CAR.2': 162.42,
            'ATN.INT.2': 5.0,
            'ATN.MOB.2': 4.0,
            'M.ONSS': 15.39,
            'MEAL_V_EMP': 25.07,
            'REP.FEES': -150.0,
            'IP': -662.5,
            'IP.DED': 49.69,
            'NET': -2203.54,
            'REMUNERATION': -1987.5,
            'ONSSEMPLOYERBASIC': -665.55,
            'ONSSEMPLOYERFFE': -1.86,
            'ONSSEMPLOYERMFFE': -2.66,
            'ONSSEMPLOYERCPAE': -6.12,
            'ONSSEMPLOYERRESTREINT': -44.94,
            'ONSSEMPLOYERUNEMP': -2.66,
            'ONSSEMPLOYER': -723.78,
            'CO2FEE': -28.17,
        }
        self._validate_payslip(refund, payslip_results)

        refund.action_payslip_done()

        net_account_move_line = refund.move_id.line_ids.filtered(lambda l: l.name == 'Net Salary')
        self.assertAlmostEqual(net_account_move_line.debit, 2203.54, places=2)
        self.assertAlmostEqual(net_account_move_line.credit, 0.0, places=2)

    def test_sick_time_off_without_guaranteed_salary_half_days_no_attendances(self):
        # Check the sick time off is not counted twice on half/full days
        # if only sick time off without attendances (and without guaranteed salary)

        self.contract.write({
            'wage_on_signature': 3846.00,
            'resource_calendar_id': self.resource_calendar_4_5_monday_off_equal_morning_afternoon.id,
        })

        sick_leave_1 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 16 days',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2022, 9, 26),
            'request_date_to': datetime.date(2022, 10, 17),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 16,
        })
        sick_leave_1._compute_date_from_to()
        sick_leave_1 = self.env['hr.leave'].create(sick_leave_1._convert_to_write(sick_leave_1._cache))

        sick_leave_2 = self.env['hr.leave'].new({
            'name': 'Sick Time Off 20 days',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2022, 10, 18),
            'request_date_to': datetime.date(2022, 11, 14),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 20,
        })
        sick_leave_2._compute_date_from_to()
        sick_leave_2 = self.env['hr.leave'].create(sick_leave_2._convert_to_write(sick_leave_2._cache))

        (sick_leave_1 + sick_leave_2).action_validate()

        self.contract.generate_work_entries(datetime.date(2022, 10, 1), datetime.date(2022, 10, 31))
        payslip = self._generate_payslip(datetime.date(2022, 10, 1), datetime.date(2022, 10, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 4)
        self.assertEqual(len(payslip.input_line_ids), 0)

        # Without guaranteed salary
        wds = payslip.worked_days_line_ids
        sick = wds.filtered(lambda wd: wd.code == "LEAVE214" and wd.number_of_hours == 7.6)
        self.assertAlmostEqual(sick.amount, 0, places=2)
        sick = wds.filtered(lambda wd: wd.code == "LEAVE214" and wd.number_of_hours == 15.2)
        self.assertAlmostEqual(sick.amount, 0, places=2)
        # Sick time off
        sick = wds.filtered(lambda wd: wd.code == "LEAVE110" and wd.number_of_hours == 26.6)
        self.assertAlmostEqual(sick.amount, 776.6, places=2)
        sick = wds.filtered(lambda wd: wd.code == "LEAVE110" and wd.number_of_hours == 76.0)
        self.assertAlmostEqual(sick.amount, 2403.75, places=2)

        payslip_results = {
            'BASIC': 3180.35,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 3189.35,
            'ONSS': -416.85,
            'ONSSTOTAL': 416.85,
            'ATN.CAR': 162.42,
            'GROSSIP': 2934.92,
            'IP.PART': -795.09,
            'GROSS': 2139.84,
            'P.P': -361.61,
            'PPTOTAL': 361.61,
            'ATN.CAR.2': -162.42,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -21.22,
            'MEAL_V_EMP': 0,
            'REP.FEES': 150.0,
            'IP': 795.09,
            'IP.DED': -59.63,
            'NET': 2471.04,
            'REMUNERATION': 2385.26,
            'ONSSEMPLOYERBASIC': 798.29,
            'ONSSEMPLOYERFFE': 2.23,
            'ONSSEMPLOYERMFFE': 3.19,
            'ONSSEMPLOYERCPAE': 7.34,
            'ONSSEMPLOYERRESTREINT': 53.9,
            'ONSSEMPLOYERUNEMP': 3.19,
            'ONSSEMPLOYER': 868.14,
            'CO2FEE': 28.17,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_example(self):
        self.contract.write({
            'wage': 2500,
            'wage_on_signature': 2500,
            'internet': 0,
            'mobile': 0,
            'transport_mode_car': False,
            'ip': False,
            'date_start': datetime.date(2019, 1, 1),
        })
        self.contract.generate_work_entries(datetime.date(2019, 10, 1), datetime.date(2019, 10, 31))
        payslip = self._generate_payslip(datetime.date(2019, 10, 1), datetime.date(2019, 10, 31))

        payslip_results = {
            'BASIC': 2500.0,
            'SALARY': 2500.0,
            'ONSS': -326.75,
            'EmpBonus.1': 13.29,
            'ONSSTOTAL': 313.46,
            'GROSS': 2186.54,
            'P.P': -422.65,
            'P.P.DED': 4.4,
            'PPTOTAL': 418.25,
            'M.ONSS': -22.01,
            'MEAL_V_EMP': -25.07,
            'REP.FEES': 150.0,
            'NET': 1871.22,
            'REMUNERATION': 2500.0,
            'ONSSEMPLOYERBASIC': 625.5,
            'ONSSEMPLOYERFFE': 3.25,
            'ONSSEMPLOYERMFFE': 2.5,
            'ONSSEMPLOYERCPAE': 5.75,
            'ONSSEMPLOYERRESTREINT': 42.25,
            'ONSSEMPLOYERUNEMP': 2.5,
            'ONSSEMPLOYER': 681.75,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_cdi_laurie_poiret(self):
        self.contract.ip = False
        self.contract.generate_work_entries(datetime.date(2019, 2, 1), datetime.date(2019, 2, 28))
        payslip = self._generate_payslip(datetime.date(2019, 2, 1), datetime.date(2019, 2, 28))
        payslip_results = {
            'BASIC': 2650.0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'ONSSTOTAL': 347.53,
            'ATN.CAR': 149.29,
            'GROSS': 2460.75,
            'P.P': -559.87,
            'PPTOTAL': 559.87,
            'ATN.CAR.2': -149.29,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -23.66,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 150.0,
            'NET': 1847.14,
            'REMUNERATION': 2650.0,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 3.46,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 725.11,
            'CO2FEE': 20.83,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_without_car_without_atn(self):
        # 4 hours unpaid, 2 days leave, no atn and no car
        # Note: The IP is not the same as in the reference payslip, as it
        # was incorrectly computed by SDWorx during 2018
        self.contract.write({
            'date_start': datetime.date(2018, 1, 1),
            'wage': 3746.33,
            'wage_on_signature': 3746.33,
            'internet': 0,
            'mobile': 0,
            'transport_mode_car': False,
        })

        unpaid_time_off = self.env['hr.leave'].create({
            'name': 'Unpaid Leave 4 hours',
            'holiday_status_id': self.unpaid_time_off_type.id,
            'request_date_from': '2018-11-06',
            'request_date_to': '2018-11-06',
            'request_unit_half': True,
            'request_date_from_period': 'am',
            'employee_id': self.employee.id,
        })
        unpaid_time_off.action_validate()

        self.env['resource.calendar.leaves'].create({
            'name': "Bank Holiday",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2018, 11, 9, 7),
            'date_to': datetime.datetime(2018, 11, 9, 18),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        })

        self.contract.generate_work_entries(datetime.date(2018, 11, 1), datetime.date(2018, 11, 30))
        payslip = self._generate_payslip(datetime.date(2018, 11, 1), datetime.date(2018, 11, 30))
        payslip_results = {
            'BASIC': 3655.32,
            'SALARY': 3655.32,
            'ONSS': -477.75,
            'ONSSTOTAL': 477.75,
            'GROSSIP': 3177.57,
            'IP.PART': -913.83,
            'GROSS': 2263.74,
            'P.P': -501.6,
            'PPTOTAL': 501.6,
            'M.ONSS': -34.72,
            'MEAL_V_EMP': -22.89,
            'REP.FEES': 150.0,
            'IP': 913.83,
            'IP.DED': -68.54,
            'NET': 2699.83,
            'REMUNERATION': 2741.49,
            'ONSSEMPLOYERBASIC': 914.56,
            'ONSSEMPLOYERFFE': 4.75,
            'ONSSEMPLOYERMFFE': 3.66,
            'ONSSEMPLOYERCPAE': 8.41,
            'ONSSEMPLOYERRESTREINT': 61.77,
            'ONSSEMPLOYERUNEMP': 3.66,
            'ONSSEMPLOYER': 996.81,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_with_car_with_atn_with_child(self):
        # 2 unpaid days + 2 bank holidays + IP + Mobile + 1 child + extra leaves
        # IP should be correct as we are in 2019,
        self.contract.employee_id.write({
            'marital': 'cohabitant',
            'spouse_fiscal_status': 'high_income',
            'children': 1,
        })
        self.contract.car_id.write({
            'acquisition_date': datetime.date(2018, 1, 15),
            'first_contract_date': datetime.date(2018, 1, 15),
            'car_value': 29235.15,
            'fuel_type': 'diesel',
            'co2': 89,
        })
        vehicle = self.contract.car_id
        self.env['fleet.vehicle.log.contract'].create({
            'vehicle_id': vehicle.id,
            'recurring_cost_amount_depreciated': vehicle.model_id.default_recurring_cost_amount_depreciated,
            'purchaser_id': vehicle.driver_id.id,
            'company_id': vehicle.company_id.id,
            'user_id': vehicle.manager_id.id if vehicle.manager_id else self.env.user.id
        })
        self.contract.car_id.log_contracts.recurring_cost_amount_depreciated = 562.52
        self.contract.write({
            'wage': 3542.63,
            'holidays': 1,
            'mobile': 0,
        })
        self.contract.wage_on_signature = self.contract.wage_with_holidays

        unpaid_times_off = self.env['hr.leave'].create([{
            'name': 'Unpaid Leave Day 1',
            'holiday_status_id': self.unpaid_time_off_type.id,
            'date_from': datetime.datetime(2019, 5, 1, 5),
            'date_to': datetime.datetime(2019, 5, 1, 20),
            'request_date_from': datetime.datetime(2019, 5, 1, 5),
            'request_date_to': datetime.datetime(2019, 5, 1, 20),
            'number_of_days': 1,
            'employee_id': self.employee.id,
        }, {
            'name': 'Unpaid Leave Day 2',
            'holiday_status_id': self.unpaid_time_off_type.id,
            'date_from': datetime.datetime(2019, 5, 2, 5),
            'date_to': datetime.datetime(2019, 5, 2, 20),
            'request_date_from': datetime.datetime(2019, 5, 2, 5),
            'request_date_to': datetime.datetime(2019, 5, 2, 20),
            'number_of_days': 1,
            'employee_id': self.employee.id,
        }])
        unpaid_times_off.action_validate()

        self.env['resource.calendar.leaves'].create([{
            'name': "Bank Holiday Day 1",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2019, 5, 7, 5),
            'date_to': datetime.datetime(2019, 5, 7, 20),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }, {
            'name': "Bank Holiday Day 2",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2019, 5, 6, 5),
            'date_to': datetime.datetime(2019, 5, 6, 20),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }])

        self.contract.generate_work_entries(datetime.date(2019, 5, 1), datetime.date(2019, 5, 31))
        payslip = self._generate_payslip(datetime.date(2019, 5, 1), datetime.date(2019, 5, 31))
        payslip_results = {
            'BASIC': 3197.34,
            'ATN.INT': 5.0,
            'SALARY': 3202.34,
            'ONSS': -418.55,
            'ONSSTOTAL': 418.55,
            'ATN.CAR': 109.92,
            'GROSSIP': 2893.72,
            'IP.PART': -799.34,
            'GROSS': 2094.38,
            'P.P': -343.31,
            'PPTOTAL': 343.31,
            'ATN.CAR.2': -109.92,
            'ATN.INT.2': -5.0,
            'M.ONSS': -29.68,
            'MEAL_V_EMP': -20.71,
            'REP.FEES': 150.0,
            'IP': 799.34,
            'IP.DED': -59.95,
            'NET': 2475.15,
            'REMUNERATION': 2398.01,
            'ONSSEMPLOYERBASIC': 801.23,
            'ONSSEMPLOYERFFE': 4.16,
            'ONSSEMPLOYERMFFE': 3.2,
            'ONSSEMPLOYERCPAE': 7.37,
            'ONSSEMPLOYERRESTREINT': 54.12,
            'ONSSEMPLOYERUNEMP': 3.2,
            'ONSSEMPLOYER': 873.28,
            'CO2FEE': 21.69,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_with_car_with_atn_with_car(self):
        # ATN + No leave + IP (2019) + car
        self.contract.employee_id.write({
            'marital': 'cohabitant',
            'spouse_fiscal_status': 'high_income',
        })
        self.contract.car_id.write({
            'acquisition_date': datetime.date(2014, 12, 10),
            'first_contract_date': datetime.date(2014, 12, 10),
            'car_value': 28138.86,
            'fuel_type': 'diesel',
            'co2': 88.00,
        })
        vehicle = self.contract.car_id
        self.env['fleet.vehicle.log.contract'].create({
            'vehicle_id': vehicle.id,
            'recurring_cost_amount_depreciated': vehicle.model_id.default_recurring_cost_amount_depreciated,
            'purchaser_id': vehicle.driver_id.id,
            'company_id': vehicle.company_id.id,
            'user_id': vehicle.manager_id.id if vehicle.manager_id else self.env.user.id
        })
        self.contract.car_id.log_contracts.recurring_cost_amount_depreciated = 503.12
        self.contract.write({
            'wage': 3470.36,
            'holidays': 1,
            'mobile': 0,
            'ip_wage_rate': 25,
            'ip': True,
        })
        self.contract.wage_on_signature = self.contract.wage_with_holidays

        self.contract.generate_work_entries(datetime.date(2019, 3, 1), datetime.date(2019, 3, 31))
        payslip = self._generate_payslip(datetime.date(2019, 3, 1), datetime.date(2019, 3, 31))
        payslip_results = {
            'BASIC': 3450.89,
            'ATN.INT': 5.0,
            'SALARY': 3455.89,
            'ONSS': -451.68,
            'ONSSTOTAL': 451.68,
            'ATN.CAR': 109.17,
            'GROSSIP': 3113.37,
            'IP.PART': -862.72,
            'GROSS': 2250.65,
            'P.P': -458.76,
            'PPTOTAL': 458.76,
            'ATN.CAR.2': -109.17,
            'ATN.INT.2': -5.0,
            'M.ONSS': -32.47,
            'MEAL_V_EMP': -22.89,
            'REP.FEES': 150.0,
            'IP': 862.72,
            'IP.DED': -64.7,
            'NET': 2570.38,
            'REMUNERATION': 2588.17,
            'ONSSEMPLOYERBASIC': 864.66,
            'ONSSEMPLOYERFFE': 4.49,
            'ONSSEMPLOYERMFFE': 3.46,
            'ONSSEMPLOYERCPAE': 7.95,
            'ONSSEMPLOYERRESTREINT': 58.4,
            'ONSSEMPLOYERUNEMP': 3.46,
            'ONSSEMPLOYER': 942.42,
            'CO2FEE': 20.83,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_with_car_with_atn_with_car_based_on_yearly_cost(self):
        # ATN + No leave + IP (2019) + car
        self.contract.employee_id.write({
            'marital': 'cohabitant',
            'spouse_fiscal_status': 'high_income',
        })
        self.contract.car_id.write({
            'acquisition_date': datetime.date(2014, 12, 10),
            'first_contract_date': datetime.date(2014, 12, 10),
            'car_value': 28138.86,
            'fuel_type': 'diesel',
            'co2': 88.00,
        })
        vehicle = self.contract.car_id
        self.env['fleet.vehicle.log.contract'].create({
            'vehicle_id': vehicle.id,
            'recurring_cost_amount_depreciated': vehicle.model_id.default_recurring_cost_amount_depreciated,
            'purchaser_id': vehicle.driver_id.id,
            'company_id': vehicle.company_id.id,
            'user_id': vehicle.manager_id.id if vehicle.manager_id else self.env.user.id
        })
        self.contract.car_id.log_contracts.recurring_cost_amount_depreciated = 503.12
        self.contract.write({
            'wage_with_holidays': 3450.89,
            'holidays': 1,
            'mobile': 0,
            'ip_wage_rate': 25,
            'ip': True,
        })

        cost_before = self.contract.final_yearly_costs
        the_car = self.contract.car_id
        self.contract.car_id = False
        self.contract.car_id = the_car
        self.assertEqual(self.contract.final_yearly_costs, cost_before)

    def test_no_ip_emp_bonus(self):
        # No IP, with employment bonus
        self.contract.write({
            'wage': 2075.44,
            'wage_on_signature': 2075.44,
            'representation_fees': 0,
            'internet': False,
            'mobile': False,
            'transport_mode_car': False,
            'ip': False,
        })
        self.contract.generate_work_entries(datetime.date(2019, 2, 1), datetime.date(2019, 2, 28))
        payslip = self._generate_payslip(datetime.date(2019, 2, 1), datetime.date(2019, 2, 28))
        payslip_results = {
            'BASIC': 2075.44,
            'SALARY': 2075.44,
            'ONSS': -271.26,
            'EmpBonus.1': 106.44,
            'ONSSTOTAL': 164.82,
            'GROSS': 1910.62,
            'P.P': -299.68,
            'P.P.DED': 35.27,
            'PPTOTAL': 264.41,
            'M.ONSS': -9.88,
            'MEAL_V_EMP': -21.8,
            'NET': 1614.53,
            'REMUNERATION': 2075.44,
            'ONSSEMPLOYERBASIC': 519.28,
            'ONSSEMPLOYERFFE': 2.7,
            'ONSSEMPLOYERMFFE': 2.08,
            'ONSSEMPLOYERCPAE': 4.77,
            'ONSSEMPLOYERRESTREINT': 35.07,
            'ONSSEMPLOYERUNEMP': 2.08,
            'ONSSEMPLOYER': 565.97,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_small_unemployment_leave(self):
        # Small unemployment leave, spouse without income
        self.contract.employee_id.write({
            'marital': 'married',
            'children': 1,
            'spouse_fiscal_status': 'without_income',
        })
        self.contract.write({
            'wage': 2706.14,
            'wage_on_signature': 2706.14,
        })

        brief_holidays = self.env['hr.leave'].create([{
            'name': 'Small Unemployment - Day 1',
            'holiday_status_id': self.leave_type_small_unemployment.id,
            'date_from': datetime.datetime(2019, 2, 27, 5),
            'date_to': datetime.datetime(2019, 2, 27, 20),
            'request_date_from': datetime.datetime(2019, 2, 27, 5),
            'request_date_to': datetime.datetime(2019, 2, 27, 20),
            'number_of_days': 1,
            'employee_id': self.employee.id,
        }, {
            'name': 'Small Unemployment - Day 2',
            'holiday_status_id': self.leave_type_small_unemployment.id,
            'date_from': datetime.datetime(2019, 2, 28, 5),
            'date_to': datetime.datetime(2019, 2, 28, 20),
            'request_date_from': datetime.datetime(2019, 2, 28, 5),
            'request_date_to': datetime.datetime(2019, 2, 28, 20),
            'number_of_days': 1,
            'employee_id': self.employee.id,
        }])
        brief_holidays.action_validate()

        self.contract.generate_work_entries(datetime.date(2019, 2, 1), datetime.date(2019, 2, 28))
        payslip = self._generate_payslip(datetime.date(2019, 2, 1), datetime.date(2019, 2, 28))
        payslip_results = {
            'BASIC': 2706.14,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2715.14,
            'ONSS': -354.87,
            'ONSSTOTAL': 354.87,
            'ATN.CAR': 149.29,
            'GROSSIP': 2509.56,
            'IP.PART': -676.54,
            'GROSS': 1833.02,
            'P.P': -2.11,
            'PPTOTAL': 2.11,
            'ATN.CAR.2': -149.29,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -24.28,
            'MEAL_V_EMP': -19.62,
            'REP.FEES': 150.0,
            'IP': 676.54,
            'IP.DED': -50.74,
            'NET': 2404.53,
            'REMUNERATION': 2029.61,
            'ONSSEMPLOYERBASIC': 679.33,
            'ONSSEMPLOYERFFE': 3.53,
            'ONSSEMPLOYERMFFE': 2.72,
            'ONSSEMPLOYERCPAE': 6.24,
            'ONSSEMPLOYERRESTREINT': 45.89,
            'ONSSEMPLOYERUNEMP': 2.72,
            'ONSSEMPLOYER': 740.42,
            'CO2FEE': 20.83,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_pfi_company_car_pay(self):
        # PFI with company car
        self.contract.write({
            'wage': 1653.11,
            'wage_on_signature': 1653.11,
            'meal_voucher_amount': 7.45,
            'internet': False,
            'mobile': False,
        })

        self.env['resource.calendar.leaves'].create({
            'name': "Bank Holiday",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2019, 1, 1, 5),
            'date_to': datetime.datetime(2019, 1, 1, 20),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        })

        self.contract.generate_work_entries(datetime.date(2019, 1, 1), datetime.date(2019, 1, 31))
        payslip = self._generate_payslip(datetime.date(2019, 1, 1), datetime.date(2019, 1, 31), struct_id=self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_pfi').id)
        payslip_results = {
            'BASIC': 1653.11,
            'ATN.CAR': 149.29,
            'SALARY': 1653.11,
            'GROSS': 1802.4,
            'P.P': -360.48,  # 20% of BASIC + ATN.CAR
            'ATN.CAR.2': -149.29,
            'MEAL_V_EMP': -23.98,
            'NET': 1268.65,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_pfi_with_benefits_pay(self):
        # PFI with company car, mobile and internet
        self.contract.write({
            'wage': 1572.8,
            'wage_on_signature': 1572.8,
        })
        self.contract.generate_work_entries(datetime.date(2019, 2, 1), datetime.date(2019, 2, 28))
        payslip = self._generate_payslip(datetime.date(2019, 2, 1), datetime.date(2019, 2, 28), struct_id=self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_pfi').id)
        payslip_results = {
            'BASIC': 1572.8,
            'ATN.INT': 5,
            'ATN.MOB': 4,
            'SALARY': 1581.8,
            'GROSS': 1731.09,
            'P.P': -344.42,  # 20% of BASIC + ATN.CAR
            'ATN.CAR': 149.29,
            'MEAL_V_EMP': -21.8,
            'ATN.INT.2': -5,
            'ATN.MOB.2': -4,
            'ATN.CAR.2': -149.29,
            'NET': 1206.58,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_repartition_few_half_days(self):
        calendar = self.env['resource.calendar'].create([{
            'name': "Test Calendar : 26 Hours/Week",
            'company_id': self.env.company.id,
            'hours_per_day': 6.67,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 26.67,
            'full_time_required_hours': 38.0,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
                'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id

            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 9.0, 12.0, "morning"),
                ("0", 12.75, 17, "afternoon"),
                ("1", 9.0, 12.0, "morning"),
                ("1", 12.75, 17.0, "afternoon"),
                ("2", 9.0, 14.75, "morning"),
                ("3", 9.0, 12.0, "morning"),
                ("3", 12.75, 17, "afternoon"),
            ]],
        }])
        self.employee.resource_calendar_id = calendar
        self.contract.write({
            'wage_on_signature': 908.33,
            'wage': 908.33,
            'resource_calendar_id': calendar.id,
            'date_start': datetime.date(2023, 3, 27),
            'internet': 0,
            'mobile': 0,
            'ip': False,
        })

        sick_leave = self.env['hr.leave'].new({
            'name': 'Sick Time Off 3 Days',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2023, 3, 27),
            'request_date_to': datetime.date(2023, 3, 29),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 3,
        })
        sick_leave._compute_date_from_to()
        sick_leave = self.env['hr.leave'].create(sick_leave._convert_to_write(sick_leave._cache))
        sick_leave.action_validate()
        self.contract.generate_work_entries(datetime.date(2023, 3, 1), datetime.date(2023, 3, 31))
        payslip = self._generate_payslip(datetime.date(2023, 3, 1), datetime.date(2023, 3, 31))

        wds = payslip.worked_days_line_ids.sorted("number_of_hours")
        self.assertAlmostEqual(wds[0].number_of_days, 1, places=2)
        self.assertAlmostEqual(wds[0].number_of_hours, 5.75, places=2)
        self.assertAlmostEqual(wds[0].amount, 43.83, places=2)
        self.assertEqual(wds[0].work_entry_type_id.code, "LEAVE110")

        self.assertAlmostEqual(wds[1].number_of_days, 1, places=2)
        self.assertAlmostEqual(wds[1].number_of_hours, 7.25, places=2)
        self.assertAlmostEqual(wds[1].amount, 55.26, places=2)
        self.assertEqual(wds[1].work_entry_type_id.code, "WORK100")

        self.assertAlmostEqual(wds[2].number_of_days, 2, places=2)
        self.assertAlmostEqual(wds[2].number_of_hours, 14.5, places=2)
        self.assertAlmostEqual(wds[2].amount, 81.31, places=2)
        self.assertEqual(wds[2].work_entry_type_id.code, "LEAVE110")

        self.assertAlmostEqual(wds[3].number_of_days, 14, places=2)
        self.assertAlmostEqual(wds[3].number_of_hours, 95.5, places=2)
        self.assertAlmostEqual(wds[3].amount, 0, places=2)
        self.assertEqual(wds[3].work_entry_type_id.code, "OUT")

        payslip_results = {
            'BASIC': 180.4,
            'SALARY': 180.4,
            'ONSS': -23.58,
            'EmpBonus.1': 23.58,
            'ONSSTOTAL': 0,
            'ATN.CAR': 169.15,
            'GROSS': 349.55,
            'P.P': 0,
            'P.P.DED': 0,
            'PPTOTAL': 0,
            'ATN.CAR.2': -169.15,
            'M.ONSS': 0,
            'MEAL_V_EMP': -1.09,
            'REP.FEES': 20.88,
            'NET': 200.19,
            'REMUNERATION': 180.4,
            'ONSSEMPLOYERBASIC': 45.15,
            'ONSSEMPLOYERFFE': 0.13,
            'ONSSEMPLOYERMFFE': 0.18,
            'ONSSEMPLOYERCPAE': 0.41,
            'ONSSEMPLOYERRESTREINT': 3.05,
            'ONSSEMPLOYERUNEMP': 0.18,
            'ONSSEMPLOYER': 49.1,
            'CO2FEE': 31.34,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_thirteen_month(self):
        payslip = self._generate_payslip(datetime.date(2023, 6, 1), datetime.date(2023, 6, 30), struct_id=self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_thirteen_month').id)
        payslip_results = {
            'BASIC': 1325.0,
            'SALARY': 1325.0,
            'ONSS': -173.18,
            'GROSS': 1151.82,
            'P.P': -534.91,
            'PPTOTAL': 534.91,
            'NET': 616.92,
            'ONSSEMPLOYERBASIC': 331.65,
            'ONSSEMPLOYERFFE': 0.93,
            'ONSSEMPLOYERMFFE': 1.33,
            'ONSSEMPLOYERCPAE': 3.05,
            'ONSSEMPLOYERRESTREINT': 22.39,
            'ONSSEMPLOYERUNEMP': 1.33,
            'ONSSEMPLOYER': 360.67,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_simple_n_holiday_pay_recovery_2024(self):
        # Check that the same amount if recovered on 2 diffent months (July / February)
        self.contract.date_start = datetime.date(2023, 1, 1)
        # Employee received 1000€ for 5 days of holidays from previous employer
        self.employee.l10n_be_holiday_pay_to_recover_n = 100000
        self.employee.l10n_be_holiday_pay_number_of_days_n = 2

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal Leave Whole Day",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2024, 2, 11, 6, 0, 0),
            'date_to': datetime.datetime(2024, 2, 15, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2024, 2, 1), datetime.date(2024, 2, 29))
        self.assertEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 30.4)
        self.assertEqual(payslip._get_worked_days_line_amount('LEAVE120'), 489.23)
        # Should be 122.31 * 2 = 244.62 instead of 252.38
        payslip_results = {
            'BASIC': 2650.0,
            'HolPayRecN': -244.62,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2414.38,
            'ONSS': -315.56,
            'EmpBonus.1': 158.81,
            'ONSSTOTAL': 156.75,
            'ATN.CAR': 156.78,
            'GROSSIP': 2414.41,
            'IP.PART': -662.5,
            'GROSS': 1751.91,
            'P.P': -104.61,
            'P.P.DED': 52.63,
            'PPTOTAL': 51.98,
            'ATN.CAR.2': -156.78,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -18.53,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2263.05,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 604.08,
            'ONSSEMPLOYERFFE': 1.69,
            'ONSSEMPLOYERMFFE': 2.41,
            'ONSSEMPLOYERCPAE': 5.55,
            'ONSSEMPLOYERRESTREINT': 40.8,
            'ONSSEMPLOYERUNEMP': 2.41,
            'ONSSEMPLOYER': 656.95,
            'CO2FEE': 31.34,
        }
        self._validate_payslip(payslip, payslip_results)

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal Leave Whole Day",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2024, 7, 14, 6, 0, 0),
            'date_to': datetime.datetime(2024, 7, 18, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2024, 7, 1), datetime.date(2024, 7, 31))
        self.assertEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 30.4)
        self.assertEqual(payslip._get_worked_days_line_amount('LEAVE120'), 489.23)

        # Should be 122.31 * 2 = 244.62 instead of 230.43
        payslip_results = {
            'BASIC': 2650.0,
            'HolPayRecN': -244.62,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2414.38,
            'ONSS': -315.56,
            'EmpBonus.1': 201.59,
            'ONSSTOTAL': 113.97,
            'ATN.CAR': 156.78,
            'GROSSIP': 2457.2,
            'IP.PART': -662.5,
            'GROSS': 1794.7,
            'P.P': -116.05,
            'P.P.DED': 82.98,
            'PPTOTAL': 33.07,
            'ATN.CAR.2': -156.78,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -20.71,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2322.57,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 604.08,
            'ONSSEMPLOYERFFE': 1.69,
            'ONSSEMPLOYERMFFE': 2.41,
            'ONSSEMPLOYERCPAE': 5.55,
            'ONSSEMPLOYERRESTREINT': 40.8,
            'ONSSEMPLOYERUNEMP': 2.41,
            'ONSSEMPLOYER': 656.95,
            'CO2FEE': 31.34,
        }
        self._validate_payslip(payslip, payslip_results)

    # same function for simple_n1 or simple_n so only one test.
    def test_simple_n_holiday_pay_recovery_lower_salary_2_payslips_2024(self):
        # Check that the same amount if recovered on 2 diffent months (July / February)
        self.contract.date_start = datetime.date(2023, 1, 1)
        # Employee received 1000€ for 5 days of holidays from previous employer
        # Employee took 2 days on january (so the HolidayPayRecN1 should be equal to the right amount for 2 days)
        # Employee took 2 days on febrary (so the HolidayPayRecN1 shouldn't exceed the employee cost for the 2 days)
        # Employee took 4 days on march (so the HolidayPayRecN1 should be equal to 0)
        self.employee.l10n_be_holiday_pay_to_recover_n = 100000
        self.employee.l10n_be_holiday_pay_number_of_days_n = 3

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal Leave",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2024, 1, 11, 6, 0, 0),
            'date_to': datetime.datetime(2024, 1, 12, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2024, 1, 1), datetime.date(2024, 1, 31))
        payslip.action_payslip_done()
        self.assertEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 15.2)
        self.assertEqual(payslip._get_worked_days_line_amount('LEAVE120'), 244.62)
        # Should be 122.31 * 2 = 244.62 instead of 252.38
        payslip_results = {
            'BASIC': 2650.0,
            'HolPayRecN': -244.62,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2414.38,
            'ONSS': -315.56,
            'EmpBonus.1': 158.81,
            'ONSSTOTAL': 156.75,
            'ATN.CAR': 156.78,
            'GROSSIP': 2414.41,
            'IP.PART': -662.5,
            'GROSS': 1751.91,
            'P.P': -104.61,
            'P.P.DED': 52.63,
            'PPTOTAL': 51.98,
            'ATN.CAR.2': -156.78,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -22.89,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2258.69,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 604.08,
            'ONSSEMPLOYERFFE': 1.69,
            'ONSSEMPLOYERMFFE': 2.41,
            'ONSSEMPLOYERCPAE': 5.55,
            'ONSSEMPLOYERRESTREINT': 40.8,
            'ONSSEMPLOYERUNEMP': 2.41,
            'ONSSEMPLOYER': 656.95,
            'CO2FEE': 31.34,
        }
        self._validate_payslip(payslip, payslip_results)

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal Leave",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2024, 2, 6, 6, 0, 0),
            'date_to': datetime.datetime(2024, 2, 7, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2024, 2, 1), datetime.date(2024, 2, 29))
        payslip.action_payslip_done()
        self.assertEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 15.2)
        self.assertEqual(payslip._get_worked_days_line_amount('LEAVE120'), 244.62)
        # HolPayRecN should be equal to - 224.62 / 2 = -122.31
        payslip_results = {
            'BASIC': 2650.0,
            'HolPayRecN': -122.31,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2536.69,
            'ONSS': -331.55,
            'EmpBonus.1': 127.26,
            'ONSSTOTAL': 204.28,
            'ATN.CAR': 156.78,
            'GROSSIP': 2489.19,
            'IP.PART': -662.5,
            'GROSS': 1826.69,
            'P.P': -129.16,
            'P.P.DED': 42.18,
            'PPTOTAL': 86.98,
            'ATN.CAR.2': -156.78,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -20.71,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2300.64,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 634.68,
            'ONSSEMPLOYERFFE': 1.78,
            'ONSSEMPLOYERMFFE': 2.54,
            'ONSSEMPLOYERCPAE': 5.83,
            'ONSSEMPLOYERRESTREINT': 42.87,
            'ONSSEMPLOYERUNEMP': 2.54,
            'ONSSEMPLOYER': 690.23,
            'CO2FEE': 31.34,
        }
        self._validate_payslip(payslip, payslip_results)

        self.env['resource.calendar.leaves'].create([{
            'name': "Legal Leave",
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2024, 3, 18, 6, 0, 0),
            'date_to': datetime.datetime(2024, 3, 21, 19, 0, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2024, 3, 1), datetime.date(2024, 3, 31))
        payslip.action_payslip_done()
        self.assertEqual(payslip._get_worked_days_line_number_of_hours('LEAVE120'), 30.4)
        self.assertEqual(payslip._get_worked_days_line_amount('LEAVE120'), 489.23)
        # HolPayRecN should be equal to 0
        payslip_results = {
            'BASIC': 2650.0,
            'HolPayRecN': 0,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2659.0,
            'ONSS': -347.53,
            'EmpBonus.1': 112.89,
            'ONSSTOTAL': 234.64,
            'ATN.CAR': 156.78,
            'GROSSIP': 2581.13,
            'IP.PART': -662.5,
            'GROSS': 1918.63,
            'P.P': -168.52,
            'P.P.DED': 37.41,
            'PPTOTAL': 131.11,
            'ATN.CAR.2': -156.78,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -15.39,
            'MEAL_V_EMP': -18.53,
            'REP.FEES': 150.0,
            'IP': 662.5,
            'IP.DED': -49.69,
            'NET': 2350.64,
            'REMUNERATION': 1987.5,
            'ONSSEMPLOYERBASIC': 665.28,
            'ONSSEMPLOYERFFE': 1.86,
            'ONSSEMPLOYERMFFE': 2.66,
            'ONSSEMPLOYERCPAE': 6.12,
            'ONSSEMPLOYERRESTREINT': 44.94,
            'ONSSEMPLOYERUNEMP': 2.66,
            'ONSSEMPLOYER': 723.51,
            'CO2FEE': 31.34,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_thirteen_month_sick_leave(self):
        # 30 days of unpaid sick leaves are taken into account as attendances on
        # the gross computation
        sick_leave = self.env['hr.leave'].new({
            'name': 'Sick Time Off 2 Months',
            'employee_id': self.employee.id,
            'holiday_status_id': self.sick_time_off_type.id,
            'request_date_from': datetime.date(2023, 1, 1),
            'request_date_to': datetime.date(2023, 3, 31),
            'request_hour_from': '7',
            'request_hour_to': '18',
            'number_of_days': 65,
        })
        sick_leave._compute_date_from_to()
        sick_leave = self.env['hr.leave'].create(sick_leave._convert_to_write(sick_leave._cache))
        sick_leave.action_validate()

        self.employee.contract_ids.generate_work_entries(datetime.date(2023, 1, 1), datetime.date(2023, 6, 30))

        payslip = self._generate_payslip(datetime.date(2023, 6, 1), datetime.date(2023, 6, 30), struct_id=self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_thirteen_month').id)
        payslip_results = {
            'BASIC': 1182.31,
            'SALARY': 1182.31,
            'ONSS': -154.53,
            'GROSS': 1027.78,
            'P.P': -477.3,
            'PPTOTAL': 477.3,
            'NET': 550.48,
            'ONSSEMPLOYERBASIC': 295.93,
            'ONSSEMPLOYERFFE': 0.83,
            'ONSSEMPLOYERMFFE': 1.18,
            'ONSSEMPLOYERCPAE': 2.72,
            'ONSSEMPLOYERRESTREINT': 19.98,
            'ONSSEMPLOYERUNEMP': 1.18,
            'ONSSEMPLOYER': 321.82,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_multiple_public_holidays_variable_salary(self):
        self.contract.commission_on_target = 1000
        self.env['resource.calendar.leaves'].create([{
            'name': 'Public Time Off 1',
            'date_from': datetime.datetime(2023, 8, 7, 2),
            'date_to': datetime.datetime(2023, 8, 7, 22),
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id,
            'time_type': 'leave',
        }, {
            'name': 'Public Time Off 2',
            'date_from': datetime.datetime(2023, 8, 8, 2),
            'date_to': datetime.datetime(2023, 8, 8, 22),
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id,
            'time_type': 'leave',
        }, {
            'name': 'Public Time Off 3',
            'date_from': datetime.datetime(2023, 8, 9, 2),
            'date_to': datetime.datetime(2023, 8, 9, 22),
            'calendar_id': self.resource_calendar_38_hours_per_week.id,
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id,
            'time_type': 'leave',
        }])

        commission_payslip = self._generate_payslip(datetime.date(2023, 7, 1), datetime.date(2023, 7, 31))
        self.env['hr.payslip.input'].create([{
            'name': "Commission Input",
            'payslip_id': commission_payslip.id,
            'sequence': 10,
            'input_type_id': self.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
            'amount': 10000,
        }])
        commission_payslip.compute_sheet()
        commission_payslip.action_payslip_done()

        payslip = self._generate_payslip(datetime.date(2023, 8, 1), datetime.date(2023, 8, 31))
        payslip_results = {
            'BASIC': 2770.0,  # 2650 + 40 * 3
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 2779.0,
            'ONSS': -363.22,
            'EmpBonus.1': 85.13,
            'ONSSTOTAL': 278.08,
            'ATN.CAR': 169.15,
            'GROSSIP': 2670.07,
            'IP.PART': -692.5,
            'GROSS': 1977.57,
            'P.P': -232.53,
            'P.P.DED': 28.21,
            'PPTOTAL': 204.32,
            'ATN.CAR.2': -169.15,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': -16.71,
            'MEAL_V_EMP': -21.8,
            'REP.FEES': 150.0,
            'IP': 692.5,
            'IP.DED': -51.94,
            'NET': 2347.15,
            'REMUNERATION': 2077.5,
            'ONSSEMPLOYERBASIC': 695.58,
            'ONSSEMPLOYERFFE': 1.95,
            'ONSSEMPLOYERMFFE': 2.78,
            'ONSSEMPLOYERCPAE': 6.39,
            'ONSSEMPLOYERRESTREINT': 46.97,
            'ONSSEMPLOYERUNEMP': 2.78,
            'ONSSEMPLOYER': 756.44,
            'CO2FEE': 31.34,
        }
        self.assertAlmostEqual(payslip._get_worked_days_line_amount('LEAVE1731'), 120, places=2)
        self._validate_payslip(payslip, payslip_results)

    def test_parental_time_off_out_of_contract(self):
        self.contract.write({
            'name': "4/5 Parental Time Off",
            'time_credit': True,
            'standard_calendar_id': self.resource_calendar_38_hours_per_week.id,
            'work_time_rate': 80,
            'time_credit_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_parental_time_off').id,
            'resource_calendar_id': self.resource_calendar_4_5_friday_off.id,
            'date_start': datetime.date(2023, 4, 1),
            'date_end': datetime.date(2023, 8, 13),
            'wage': 2562.78,
            'wage_on_signature': 2562.78,
        })

        extra_legal_time_off = self.env['hr.leave'].create({
            'name': 'Extra Legal Time Off',
            'holiday_status_id': self.extra_legal_time_off_type.id,
            'date_from': datetime.datetime(2023, 8, 1, 6, 0, 0),
            'date_to': datetime.datetime(2023, 8, 10, 20, 0, 0),
            'request_date_from': datetime.datetime(2023, 8, 1, 6, 0, 0),
            'request_date_to': datetime.datetime(2023, 8, 10, 20, 0, 0),
            'number_of_days': 7,
            'employee_id': self.employee.id,
        })
        extra_legal_time_off.action_validate()

        payslip = self._generate_payslip(datetime.date(2023, 8, 1), datetime.date(2023, 8, 31))

        worked_days_values = {
            'OUT': {
                'number_of_days': 14,
                'number_of_hours': 106.40,
                'amount': 0,
            },
            'LEAVE213': {
                'number_of_days': 7,
                'number_of_hours': 53.2,
                'amount': 906.83,
            },
            'LEAVE301': {
                'number_of_days': 2,
                'number_of_hours': 15.2,
                'amount': 0,
            }
        }
        for work_day in payslip.worked_days_line_ids:
            self.assertAlmostEqual(work_day.number_of_days, worked_days_values[work_day.code]['number_of_days'], places=2)
            self.assertAlmostEqual(work_day.number_of_hours, worked_days_values[work_day.code]['number_of_hours'], places=2)
            self.assertAlmostEqual(work_day.amount, worked_days_values[work_day.code]['amount'], places=2)

        payslip_results = {
            'BASIC': 906.83,
            'ATN.INT': 5.0,
            'ATN.MOB': 4.0,
            'SALARY': 915.83,
            'ONSS': -119.7,
            'EmpBonus.1': 30.81,
            'ONSSTOTAL': 88.89,
            'ATN.CAR': 169.15,
            'GROSSIP': 996.09,
            'IP.PART': -226.71,
            'GROSS': 769.38,
            'P.P': 0,
            'P.P.DED': 0,
            'PPTOTAL': 0,
            'ATN.CAR.2': -169.15,
            'ATN.INT.2': -5.0,
            'ATN.MOB.2': -4.0,
            'M.ONSS': 0,
            'MEAL_V_EMP': 0,
            'REP.FEES': 11.54,
            'IP': 226.71,
            'IP.DED': -17.0,
            'NET': 812.47,
            'REMUNERATION': 680.12,
            'ONSSEMPLOYERBASIC': 229.23,
            'ONSSEMPLOYERFFE': 0.64,
            'ONSSEMPLOYERMFFE': 0.92,
            'ONSSEMPLOYERCPAE': 2.11,
            'ONSSEMPLOYERRESTREINT': 15.48,
            'ONSSEMPLOYERUNEMP': 0.92,
            'ONSSEMPLOYER': 249.29,
            'CO2FEE': 31.34,
        }
        self._validate_payslip(payslip, payslip_results)

        contract_2 = self.contract.copy({
            'date_start': datetime.date(2023, 8, 14),
            'date_end': datetime.date(2023, 12, 21),
            'resource_calendar_id': self.resource_calendar_4_5_wednesday_off.id,
        })

        # Public Holiday
        self.env['resource.calendar.leaves'].create([{
            'name': "15 Aout",
            'calendar_id': False,
            'company_id': self.env.company.id,
            'date_from': datetime.datetime(2023, 8, 15, 5, 0, 0),
            'date_to': datetime.datetime(2023, 8, 15, 20, 0, 0),
            'resource_id': False,
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('l10n_be_hr_payroll.work_entry_type_bank_holiday').id
        }])

        # Paid Time Off
        self.env['resource.calendar.leaves'].create([{
            'name': "Paid Time Off",
            'calendar_id': self.resource_calendar_4_5_wednesday_off.id,
            'company_id': self.env.company.id,
            'resource_id': self.employee.resource_id.id,
            'date_from': datetime.datetime(2023, 8, 14, 6, 0, 0),
            'date_to': datetime.datetime(2023, 8, 14, 14, 36, 0),
            'time_type': "leave",
            'work_entry_type_id': self.env.ref('hr_work_entry_contract.work_entry_type_legal_leave').id
        }])

        payslip = self._generate_payslip(datetime.date(2023, 8, 1), datetime.date(2023, 8, 31), contract_id=contract_2.id)
        worked_days_values = {
            'LEAVE120': {
                'number_of_days': 1.0,
                'number_of_hours': 7.6,
                'amount': 147.85
            },
            'LEAVE500': {
                'number_of_days': 1.0,
                'number_of_hours': 7.6,
                'amount': 147.85
            },
            'WORK100': {
                'number_of_days': 9.0,
                'number_of_hours': 68.4,
                'amount': 1202.54
            },
            'OUT': {
                'number_of_days': 9.0,
                'number_of_hours': 68.4,
                'amount': 0.0
            },
            'LEAVE301': {
                'number_of_days': 3.0,
                'number_of_hours': 22.80,
                'amount': 0.0
            }
        }
        for work_day in payslip.worked_days_line_ids:
            self.assertAlmostEqual(work_day.number_of_days, worked_days_values[work_day.code]['number_of_days'], places=2)
            self.assertAlmostEqual(work_day.number_of_hours, worked_days_values[work_day.code]['number_of_hours'], places=2)
            self.assertAlmostEqual(work_day.amount, worked_days_values[work_day.code]['amount'], places=2)
        payslip_results = {
            'BASIC': 1498.24,
            'ATN.INT': 0,
            'ATN.MOB': 0,
            'SALARY': 1498.24,
            'ONSS': -195.82,
            'EmpBonus.1': 53.81,
            'ONSSTOTAL': 142.01,
            'ATN.CAR': 0,
            'GROSSIP': 1356.23,
            'IP.PART': -374.56,
            'GROSS': 981.67,
            'P.P': 0,
            'P.P.DED': 0,
            'PPTOTAL': 0,
            'ATN.CAR.2': 0,
            'ATN.INT.2': 0,
            'ATN.MOB.2': 0,
            'M.ONSS': 0,
            'MEAL_V_EMP': -9.81,
            'REP.FEES': 46.15,
            'IP': 374.56,
            'IP.DED': -28.09,
            'NET': 1364.48,
            'REMUNERATION': 1123.68,
            'ONSSEMPLOYERBASIC': 375.01,
            'ONSSEMPLOYERFFE': 1.05,
            'ONSSEMPLOYERMFFE': 1.5,
            'ONSSEMPLOYERCPAE': 3.45,
            'ONSSEMPLOYERRESTREINT': 25.32,
            'ONSSEMPLOYERUNEMP': 1.5,
            'ONSSEMPLOYER': 407.82,
            'CO2FEE': 0,
        }
        self._validate_payslip(payslip, payslip_results)
