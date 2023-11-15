# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo.tests import new_test_user
from odoo.tests.common import tagged, TransactionCase

@tagged('post_install', '-at_install', 'hr_attendance_contract')
class TestHrAttendanceContract(TransactionCase):
    """ Tests for contract based  """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'SweatChipChop Inc.',
            'hr_attendance_overtime': True,
            'overtime_start_date': datetime(2021, 1, 1),
            'overtime_company_threshold': 10,
            'overtime_employee_threshold': 10,
        })
        cls.user = new_test_user(cls.env, login='fru', groups='base.group_user', company_id=cls.company.id).with_company(cls.company)
        cls.employee = cls.env['hr.employee'].create({
            'name': "Louis-Philippe de Bourbon-Leclerc",
            'user_id': cls.user.id,
            'company_id': cls.company.id,
            'tz': 'UTC',
        })

        cls.jpn_employee = cls.env['hr.employee'].create({
            'name': 'Haruto Yamamoto',
            'company_id': cls.company.id,
            'tz': 'Asia/Tokyo',
        })

        cls.no_lunch_time_50h_calendar = [
            (0, 0, {'name': 'Monday', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 19, 'day_period': 'morning'}),
            (0, 0, {'name': 'Tuesday', 'dayofweek': '1', 'hour_from': 9, 'hour_to': 19, 'day_period': 'morning'}),
            (0, 0, {'name': 'Wednesday', 'dayofweek': '2', 'hour_from': 9, 'hour_to': 19, 'day_period': 'morning'}),
            (0, 0, {'name': 'Thursday', 'dayofweek': '3', 'hour_from': 9, 'hour_to': 19, 'day_period': 'morning'}),
            (0, 0, {'name': 'Friday', 'dayofweek': '4', 'hour_from': 9, 'hour_to': 19, 'day_period': 'morning'}),
        ]

        cls.part_time_30h_attendance_ids = [
            (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
            (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
            (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
            (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'})
        ]

        cls.part_time_19h_friday_off_attendance_ids = [
            (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 15, 'day_period': 'afternoon'}),
            (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 15, 'day_period': 'afternoon'}),
            (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 15, 'day_period': 'afternoon'}),
        ]

        cls.full_time_50h_no_lunch, cls.part_time_30h_calendar, cls.part_time_19h_calendar = cls.env['resource.calendar'].create([
            {
                'name': '50h Calendar Full Time ',
                'company_id': cls.company.id,
                'hours_per_day': 10,
                'attendance_ids': cls.no_lunch_time_50h_calendar,
            },
            {
                'name': '30h Calendar',
                'company_id': cls.company.id,
                'hours_per_day': 6,
                'attendance_ids': cls.part_time_30h_attendance_ids,
            }, {
                'name': '19h Calendar Friday off ',
                'company_id': cls.company.id,
                'hours_per_day': 5,
                'attendance_ids': cls.part_time_19h_friday_off_attendance_ids,
            }
        ])

        cls.jpn_full_time_50h_no_lunch, cls.jpn_part_time_30h_calendar, cls.jpn_part_time_19h_calendar = cls.env['resource.calendar'].create([
            {
                'name': '50h Calendar Full Time ',
                'company_id': cls.company.id,
                'hours_per_day': 10,
                'attendance_ids': cls.no_lunch_time_50h_calendar,
                'tz': 'Asia/Tokyo'
            },
            {
                'name': '30h Calendar',
                'company_id': cls.company.id,
                'hours_per_day': 6,
                'attendance_ids': cls.part_time_30h_attendance_ids,
                'tz': 'Asia/Tokyo',
            }, {
                'name': '19h Calendar Friday off ',
                'company_id': cls.company.id,
                'hours_per_day': 5,
                'attendance_ids': cls.part_time_19h_friday_off_attendance_ids,
                'tz': 'Asia/Tokyo'
            }
        ])

        contracts = [
            {
                'name': "Contract 1 for Louis 50h",
                'employee_id': cls.employee.id,
                'date_start': datetime(2021, 1, 1),
                'date_end': datetime(2021, 4, 30),
                'resource_calendar_id': cls.full_time_50h_no_lunch.id,
                'state': 'close',
                'wage': 50000
            },
            {
                'name': "Contract 2 for Louis 30h",
                'employee_id': cls.employee.id,
                'date_start': datetime(2021, 5, 3),
                'date_end': datetime(2021, 12, 31),
                'resource_calendar_id': cls.part_time_30h_calendar.id,
                'state': 'close',
                'wage': 50000
            },
            {
                'name': "Contract 3 for Louis 19h",
                'employee_id': cls.employee.id,
                'date_start': datetime(2022, 1, 3),
                'date_end': False,
                'resource_calendar_id': cls.part_time_19h_calendar.id,
                'state': 'open',
                'wage': 50000
            },
            {
                'name': "Contract 1 for Haruto 50h",
                'employee_id': cls.jpn_employee.id,
                'date_start': datetime(2021, 1, 1),
                'date_end': datetime(2021, 4, 30),
                'resource_calendar_id': cls.jpn_full_time_50h_no_lunch.id,
                'state': 'close',
                'wage': 50000
            },
            {
                'name': "Contract 2 for Haruto 30h",
                'employee_id': cls.jpn_employee.id,
                'date_start': datetime(2021, 5, 3),
                'date_end': datetime(2021, 12, 31),
                'resource_calendar_id': cls.jpn_part_time_30h_calendar.id,
                'state': 'close',
                'wage': 50000
            },
            {
                'name': "Contract 3 for Haruto 19h",
                'employee_id': cls.jpn_employee.id,
                'date_start': datetime(2022, 1, 3),
                'date_end': False,
                'resource_calendar_id': cls.jpn_part_time_19h_calendar.id,
                'state': 'open',
                'wage': 50000
            },
        ]

        cls.env['hr.contract'].create(contracts)

    def create_attendance(self, employee, check_in, check_out):
        return self.env['hr.attendance'].sudo().create({
            'employee_id': employee.id,
            'check_in': check_in,
            'check_out': check_out
        })

    def test_attendance_flow_utc(self):
        # Case 1 : First Employee Louis
        # Running 3 different contracts over time

        # Classic day during first contract
        attendance_1 = self.create_attendance(self.employee,
                                              datetime(2021, 1, 4, 9, 0),
                                              datetime(2021, 1, 4, 19, 0))

        self.assertEqual(attendance_1.worked_hours, 10)
        self.assertEqual(self.employee.total_overtime, 0)

        # Last day of first contract
        attendance_2 = self.create_attendance(self.employee,
                                              datetime(2021, 4, 30, 9, 0),
                                              datetime(2021, 4, 30, 19, 0))

        self.assertEqual(attendance_2.worked_hours, 10)
        self.assertEqual(self.employee.total_overtime, 0)

        # First Day of second contract
        attendance_3 = self.create_attendance(self.employee,
                                              datetime(2021, 5, 3, 9, 0),
                                              datetime(2021, 5, 3, 16, 0))

        self.assertEqual(attendance_3.worked_hours, 6)
        self.assertEqual(self.employee.total_overtime, 0)

        # A wednesday in second contract, which should be a day off
        attendance_4 = self.create_attendance(self.employee,
                                              datetime(2021, 5, 5, 9, 0),
                                              datetime(2021, 5, 5, 16, 0))
        self.assertEqual(attendance_4.worked_hours, 7)
        self.assertEqual(attendance_4.overtime_hours, 7)
        overtime_1 = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id),
                                                                ('date', '=', datetime(2021, 5, 5))])
        self.assertEqual(overtime_1.duration, 7)


        # Last Day of second contract with over time that day
        attendance_5 = self.create_attendance(self.employee,
                                              datetime(2021, 12, 31, 9, 0),
                                              datetime(2021, 12, 31, 19, 0))
        self.assertEqual(attendance_5.worked_hours, 9)
        self.assertAlmostEqual(attendance_5.overtime_hours, 3, 2)
        overtime_2 = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id),
                                                                ('date', '=', datetime(2021, 12, 31))])
        self.assertEqual(overtime_2.duration, 3)


        # First day of third contract with over time that day
        attendance_6 = self.create_attendance(self.employee,
                                              datetime(2022, 1, 3, 9, 0),
                                              datetime(2022, 1, 3, 19, 0))
        self.assertEqual(attendance_6.worked_hours, 9)
        self.assertAlmostEqual(attendance_6.overtime_hours, 4, 2)
        overtime_3 = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id),
                                                                ('date', '=', datetime(2022, 1, 3))])
        self.assertEqual(overtime_3.duration, 4)


        # Firday in the last contract (should be off that day)
        attendance_7 = self.create_attendance(self.employee,
                                              datetime(2022, 1, 7, 9, 0),
                                              datetime(2022, 1, 7, 19, 0))
        self.assertEqual(attendance_7.worked_hours, 10)
        self.assertAlmostEqual(attendance_7.overtime_hours, 10, 2)
        overtime_4 = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id),
                                                                ('date', '=', datetime(2022, 1, 7))])
        self.assertEqual(overtime_4.duration, 10)

    def test_attendance_flow_other_timezone(self):
        # Case 2 : Second Employee Haruto with japanese timezone
        # Running 3 different contracts over time

        # Classic day during first contract
        attendance_1 = self.create_attendance(self.jpn_employee,
                                              datetime(2021, 1, 4, 0, 0),  # Converted to JST
                                              datetime(2021, 1, 4, 10, 0))  # Converted to JST

        self.assertEqual(attendance_1.worked_hours, 10)
        self.assertEqual(self.employee.total_overtime, 0)

        # Last day of first contract
        attendance_2 = self.create_attendance(self.jpn_employee,
                                              datetime(2021, 4, 30, 0, 0),  # Converted to JST
                                              datetime(2021, 4, 30, 10, 0))  # Converted to JST

        self.assertEqual(attendance_2.worked_hours, 10)
        self.assertEqual(self.jpn_employee.total_overtime, 0)

        # First Day of second contract
        attendance_3 = self.create_attendance(self.jpn_employee,
                                              datetime(2021, 5, 3, 0, 0),  # Converted to JST
                                              datetime(2021, 5, 3, 7, 0))  # Converted to JST

        self.assertEqual(attendance_3.worked_hours, 6)
        self.assertEqual(self.jpn_employee.total_overtime, 0)

        # A Wednesday in second contract, which should be a day off
        attendance_4 = self.create_attendance(self.jpn_employee,
                                              datetime(2021, 5, 5, 0, 0),  # Converted to JST
                                              datetime(2021, 5, 5, 7, 0))  # Converted to JST
        self.assertEqual(attendance_4.worked_hours, 7)
        self.assertEqual(attendance_4.overtime_hours, 7)
        overtime_1 = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.jpn_employee.id),
                                                                ('date', '=',
                                                                 datetime(2021, 5, 5))])
        self.assertEqual(overtime_1.duration, 7)

        # Last Day of second contract with over time that day
        attendance_5 = self.create_attendance(self.jpn_employee,
                                              datetime(2021, 12, 31, 0, 0),  # Converted to JST
                                              datetime(2021, 12, 31, 10, 0))  # Converted to JST
        self.assertEqual(attendance_5.worked_hours, 9)
        self.assertAlmostEqual(attendance_5.overtime_hours, 3, 2)
        overtime_2 = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.jpn_employee.id),
                                                                ('date', '=',
                                                                 datetime(2021, 12, 31))])
        self.assertEqual(overtime_2.duration, 3)

        # First day of third contract with over time that day
        attendance_6 = self.create_attendance(self.jpn_employee,
                                              datetime(2022, 1, 3, 0, 0),  # Converted to JST
                                              datetime(2022, 1, 3, 10, 0))  # Converted to JST
        self.assertEqual(attendance_6.worked_hours, 9)
        self.assertAlmostEqual(attendance_6.overtime_hours, 4, 2)
        overtime_3 = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.jpn_employee.id),
                                                                ('date', '=',
                                                                 datetime(2022, 1, 3))])
        self.assertEqual(overtime_3.duration, 4)

        # Friday in the last contract (should be off that day)
        attendance_7 = self.create_attendance(self.jpn_employee,
                                              datetime(2022, 1, 7, 0, 0),  # Converted to JST
                                              datetime(2022, 1, 7, 10, 0))  # Converted to JST
        self.assertEqual(attendance_7.worked_hours, 10)
        self.assertAlmostEqual(attendance_7.overtime_hours, 10, 2)
        overtime_4 = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.jpn_employee.id),
                                                                ('date', '=',
                                                                 datetime(2022, 1, 7))])
        self.assertEqual(overtime_4.duration, 10)

        # Classic day but spanning 2 days in utc
        attendance_8 = self.create_attendance(self.jpn_employee,
                                              datetime(2022, 1, 9, 22, 0),  # Converted to JST
                                              datetime(2022, 1, 10, 6, 0))  # Converted to JST
        self.assertEqual(attendance_8.worked_hours, 7)
        overtime_5 = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.jpn_employee.id),
                                                                ('date', '=',
                                                                 datetime(2022, 1, 10))])
        self.assertEqual(overtime_5.duration, 2)
