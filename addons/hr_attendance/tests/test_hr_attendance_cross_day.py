# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from datetime import datetime
import pytz
from pytz import timezone
from odoo.tests import tagged


@tagged('at_install', '-post_install')
class TestAttendanceCrossDay(TransactionCase):


    @classmethod
    def setUpClass(cls):
        super(TestAttendanceCrossDay, cls).setUpClass()
        cls.attendance = cls.env['hr.attendance']
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'tz': 'Europe/Brussels',
        })

    def test_01_single_normal_day_attendance(self):
        """ 
        check-in :O9:00 Mon
        check-out:17:00 Mon
        no split
        """
        check_in = datetime(2025, 11, 3, 9, 0)
        check_out = datetime(2025, 11, 3, 17, 0)
        normal_attendance = self.attendance.create([{
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        }])
        self.assertEqual(len(normal_attendance), 1)
        self.assertEqual(normal_attendance.check_in, check_in)
        self.assertEqual(normal_attendance.check_out, check_out)

    def test_02_standard_overnight_checkout(self):
        """ 
        check-in :20:00 Tue
        check-out:04:00 Wed
        split using the write() method
        """
        check_in = datetime(2025, 11, 4, 20, 0, 0)
        open_attendance = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': check_in,
        })
        check_out = datetime(2025, 11, 5, 4, 0, 0)
        open_attendance.write({'check_out': check_out})

        self.assertEqual(open_attendance.worked_hours, 4.0, "Day 1 should have 4 hours (20:00-00:00 local)")        
        day2_attendance = self.attendance.search([
            ('employee_id', '=', self.employee.id),
            ('id', '!=', open_attendance.id)
        ])
        self.assertTrue(day2_attendance, "A new record will be created for Day 2")
        self.assertEqual(day2_attendance.worked_hours, 4.0, "Day 2 should have 4 hours (00:00-04:00 local)")

    def test_03_multi_day_manual_entry(self):
        """ 
        check-in :20:00 Wed
        check-out:10:00 Fri
        split using the create() method
        """
        check_in = datetime(2025, 11, 5, 20, 0, 0)
        check_out = datetime(2025, 11, 7, 10, 0, 0)
        new_records = self.attendance.create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })

        map = {rec.date: rec.worked_hours for rec in new_records}
        self.assertEqual(len(new_records), 3, "The 3-day shift should result in exactly 3 separate attendance records.")
        self.assertEqual(map.get(datetime(2025, 11, 5).date()), 4.0, "Slice 1 (Wednesday) should have 4.0 hours.")
        self.assertEqual(map.get(datetime(2025, 11, 6).date()), 23.0, "Slice 2 (Thursday) should have 23.0 hours.")
        self.assertEqual(map.get(datetime(2025, 11, 7).date()), 10.0, "Slice 3 (Friday) should have 10.0 hours.")
