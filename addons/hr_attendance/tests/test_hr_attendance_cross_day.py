# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime

from odoo import Command
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('at_install', '-post_install')
class TestAttendanceCrossDay(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ruleset = cls.env['hr.attendance.overtime.ruleset'].create({
        'name': 'Ruleset for overtime testing',
        'rule_ids': [Command.create({
                'name': 'Ruleset for overtime testing - Rule 1',
                'base_off': 'quantity',
                'expected_hours_from_contract': True,
                'quantity_period': 'day',
            })],
        })
        cls.company = cls.env['res.company'].create({
            'name': 'BE Inc.',
        })
        cls.attendance = cls.env['hr.attendance']
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Youssef Ahmed',
            'company_id': cls.company.id,
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
            'ruleset_id': cls.ruleset.id,
            'resource_calendar_id': cls.company.resource_calendar_id.id,
            'tz': 'Europe/Brussels',
        })

    def test_01_single_normal_day_attendance(self):
        """
        check-in -> (3rd) O9:00
        check-out-> (3rd) 17:00
        No split
        """
        normal_attendance = self.attendance.create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 11, 3, 9, 0),
            'check_out': datetime(2025, 11, 3, 17, 0),
        }])
        self.assertEqual(len(normal_attendance), 1)
        self.assertEqual(normal_attendance.check_in, datetime(2025, 11, 3, 9, 0))
        self.assertEqual(normal_attendance.check_out, datetime(2025, 11, 3, 17, 0))

    def test_02_standard_overnight_checkout(self):
        """
        check-in -> (4th) 08:00 (UTC)
        check-out-> (5th) 11:00 (UTC)
        Attendnace splitted acording to employee local midnight (Brussels) into 2 records:
        1st record : (4th) 08:00 -> (4th) 23:00 (15hrs worked & 7hrs overtime)
        2nd record : (4th) 23:00 -> (5th) 11:00 (12hrs worked & 4hrs overtime)
        """
        cross_day_attendance = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 11, 4, 8, 0, 0),
            'check_out': datetime(2025, 11, 5, 11, 0, 0)
        })

        self.assertEqual(len(cross_day_attendance), 2, "The overnight shift should result in exactly 2 separate attendance records.")

        self.assertEqual(cross_day_attendance[0].check_in, datetime(2025, 11, 4, 8, 0, 0))
        self.assertEqual(cross_day_attendance[0].check_out, datetime(2025, 11, 4, 23, 0))
        self.assertEqual(cross_day_attendance[0].worked_hours, 15.0)
        self.assertEqual(cross_day_attendance[0].overtime_hours, 7.0)

        self.assertEqual(cross_day_attendance[1].check_in, datetime(2025, 11, 4, 23, 0, 0))
        self.assertEqual(cross_day_attendance[1].check_out, datetime(2025, 11, 5, 11, 0))
        self.assertEqual(cross_day_attendance[1].worked_hours, 12.0)
        self.assertEqual(cross_day_attendance[1].overtime_hours, 4.0)

    def test_03_multi_day_manual_entry(self):
        """
        check-in -> (5th) 20:00 (UTC)
        check-out-> (7th) 10:00 (UTC)
        Attendnace splitted acording to employee local midnight (Brussels) into 3 records:
        1st record : (5th) 20:00 -> (5th) 23:00 (3hrs worked  & 0hrs overtime)
        2nd record : (5th) 23:00 -> (6th) 23:00 (24hrs worked & 16hrs overtime)
        3rd record : (6th) 23:00 -> (7th) 10:00 (13hrs worked & 5hrs overtime)
        """
        cross_day_attendance = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 11, 5, 20, 0, 0),
            'check_out': datetime(2025, 11, 7, 12, 0, 0),
        })

        self.assertEqual(len(cross_day_attendance), 3, "The overnight shift should result in exactly 3 separate attendance records.")

        self.assertEqual(cross_day_attendance[0].check_in, datetime(2025, 11, 5, 20, 0, 0))
        self.assertEqual(cross_day_attendance[0].check_out, datetime(2025, 11, 5, 23, 0))
        self.assertEqual(cross_day_attendance[0].worked_hours, 3.0)
        self.assertEqual(cross_day_attendance[0].overtime_hours, 0.0)

        self.assertEqual(cross_day_attendance[1].check_in, datetime(2025, 11, 5, 23, 0, 0))
        self.assertEqual(cross_day_attendance[1].check_out, datetime(2025, 11, 6, 23, 0))
        self.assertEqual(cross_day_attendance[1].worked_hours, 24.0)
        self.assertEqual(cross_day_attendance[1].overtime_hours, 16.0)

        self.assertEqual(cross_day_attendance[2].check_in, datetime(2025, 11, 6, 23, 0, 0))
        self.assertEqual(cross_day_attendance[2].check_out, datetime(2025, 11, 7, 12, 0))
        self.assertEqual(cross_day_attendance[2].worked_hours, 13.0)
        self.assertEqual(cross_day_attendance[2].overtime_hours, 5.0)

    def test_04_multiple_multi_day_creates(self):
        """
        check-in -> (10th)  07:00 (UTC)
        check-out-> (11st)  23:00 (UTC)
        Attendnace splitted acording to employee local midnight (Brussels) into 2 records:
        1st record : (10th) 07:00 -> (10th) 23:00 (16hrs worked  & 8hrs overtime)
        2nd record : (10th) 23:00 -> (11th) 23:00 (24hrs worked & 16hrs overtime)

        check-in -> (11st) 23:30 (UTC)
        check-out-> (14th) 09:00 (UTC)
        Attendnace splitted acording to employee local midnight (Brussels) into 3 records:
        1st record : (11st) 23:30 -> (12nd) 23:00 (23.5hrs worked & 15.5hrs overtime)
        2nd record : (12nd) 23:00 -> (13rd) 23:00 (24hrs   worked & 16hrs overtime)
        3rd record : (13rd) 23:00 -> (14th) 09:00 (10hrs   worked & 2hrs overtime)
        """
        attendance = self.attendance.create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2025, 11, 10, 7, 0, 0),
                'check_out': datetime(2025, 11, 11, 23, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2025, 11, 11, 23, 30, 0),
                'check_out': datetime(2025, 11, 14, 9, 0, 0),
            }
        ])

        self.assertEqual(len(attendance), 5, "The batch create should result in 5 total split records.")

        # SHIFT 1: Record 1 (Monday)
        self.assertEqual(attendance[0].check_in, datetime(2025, 11, 10, 7, 0, 0))
        self.assertEqual(attendance[0].check_out, datetime(2025, 11, 10, 23, 0, 0))
        self.assertEqual(attendance[0].worked_hours, 16.0)
        self.assertEqual(attendance[0].overtime_hours, 8.0)

        # SHIFT 1: Record 2 (Tuesday)
        self.assertEqual(attendance[1].check_in, datetime(2025, 11, 10, 23, 0, 0))
        self.assertEqual(attendance[1].check_out, datetime(2025, 11, 11, 23, 0, 0))
        self.assertEqual(attendance[1].worked_hours, 24.0)
        self.assertEqual(attendance[1].overtime_hours, 16.0)

        # SHIFT 2: Record 3 (Wednesday)
        self.assertEqual(attendance[2].check_in, datetime(2025, 11, 11, 23, 30, 0))
        self.assertEqual(attendance[2].check_out, datetime(2025, 11, 12, 23, 0, 0))
        self.assertEqual(attendance[2].worked_hours, 23.5)
        self.assertEqual(attendance[2].overtime_hours, 15.5)

        # SHIFT 2: Record 4 (Thursday)
        self.assertEqual(attendance[3].check_in, datetime(2025, 11, 12, 23, 0, 0))
        self.assertEqual(attendance[3].check_out, datetime(2025, 11, 13, 23, 0, 0))
        self.assertEqual(attendance[3].worked_hours, 24.0)
        self.assertEqual(attendance[3].overtime_hours, 16.0)

        # SHIFT 2: Record 5 (Friday)
        self.assertEqual(attendance[4].check_in, datetime(2025, 11, 13, 23, 0, 0))
        self.assertEqual(attendance[4].check_out, datetime(2025, 11, 14, 9, 0, 0))
        self.assertEqual(attendance[4].worked_hours, 10.0)
        self.assertEqual(attendance[4].overtime_hours, 2.0)

    def test_05_cron_auto_check_out_without_split_shift(self):
        """
        check-in -> (10th)  09:00 (UTC)
        check-out-> .....
        """
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 2.0
        })

        check_in = datetime(2025, 11, 10, 9, 0, 0)
        open_attendnace = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': check_in,
        })

        open_attendnace._cron_auto_check_out()

        closed_attendance = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('check_in', '=', check_in),
        ])

        self.assertEqual(closed_attendance.check_out, datetime(2025, 11, 10, 19, 0, 0),
                        "Monday checkout should be adjusted back to 19:00 (9:00 + 8h work + 2h tol)")
        self.assertEqual(closed_attendance.out_mode, 'auto_check_out')
        self.assertAlmostEqual(closed_attendance.worked_hours, 10.0)

    def test_06_cron_auto_check_out_with_split_shift(self):
        """
        check-in -> (10th)  20:00 (UTC)
        check-out-> .....
        """
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_tolerance': 2.0
        })

        check_in = datetime(2025, 11, 10, 20, 0, 0)
        open_attendnace = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': check_in,
        })

        # Attendnace splitted acording to employee local midnight (Brussels) into 2 records
        open_attendnace._cron_auto_check_out()

        closed_attendances = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('check_in', '>=', check_in)
        ], order='check_in asc')

        self.assertEqual(closed_attendances[0].check_out, datetime(2025, 11, 10, 23, 0, 0))
        self.assertEqual(closed_attendances[0].out_mode, 'auto_check_out')
        self.assertAlmostEqual(closed_attendances[0].worked_hours, 3.0)

        self.assertEqual(closed_attendances[1].check_out, datetime(2025, 11, 11, 6, 0, 0))
        self.assertEqual(closed_attendances[1].out_mode, 'auto_check_out')
        self.assertAlmostEqual(closed_attendances[1].worked_hours, 7.0)

        self.assertEqual(sum(closed_attendances.mapped('worked_hours')), 10, "total worked hours (20:00 + 8h work + 2h tol)")
