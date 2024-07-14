#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_work_entry_contract_attendance.tests.common import HrWorkEntryAttendanceCommon

from datetime import datetime, date

from odoo.tests import tagged

@tagged('-at_install', 'post_install', 'work_entry_overtime')
class TestPayslipOvertime(HrWorkEntryAttendanceCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contract.write({
            'work_entry_source': "calendar",
        })
        cls.contract.company_id.write({
            'hr_attendance_overtime': True,
            'overtime_start_date': date(2022, 12, 1),
        })
        cls.attendance_type = cls.env.ref('hr_work_entry.work_entry_type_attendance')
        cls.overtime_type = cls.env.ref('hr_work_entry.overtime_work_entry_type')
        cls.work_entry_type_public_type_off = cls.env['hr.work.entry.type'].create({
            'name': 'Public Time Off',
            'code': 'PUBLIC',
            'is_leave': True,
        })

    def test_01_no_overtime(self):
        work_entries = self.contract.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12)).sorted('date_start')
        self.assertEqual(len(work_entries), 2)
        self.assertEqual(work_entries[0].date_start, datetime(2022, 12, 12, 7, 0))
        self.assertEqual(work_entries[0].date_stop, datetime(2022, 12, 12, 11, 0))
        self.assertEqual(work_entries[0].work_entry_type_id, self.attendance_type)
        self.assertEqual(work_entries[1].date_start, datetime(2022, 12, 12, 12, 0))
        self.assertEqual(work_entries[1].date_stop, datetime(2022, 12, 12, 16, 0))
        self.assertEqual(work_entries[1].work_entry_type_id, self.attendance_type)

    def test_02_overtime_classic_day_before_after(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 20),
        })
        work_entries = self.contract.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12)).sorted('date_start')
        self.assertEqual(len(work_entries), 4)
        self.assertEqual(work_entries[0].date_start, datetime(2022, 12, 12, 6, 0))
        self.assertEqual(work_entries[0].date_stop, datetime(2022, 12, 12, 7, 0))
        self.assertEqual(work_entries[0].work_entry_type_id, self.overtime_type)
        self.assertEqual(work_entries[1].date_start, datetime(2022, 12, 12, 7, 0))
        self.assertEqual(work_entries[1].date_stop, datetime(2022, 12, 12, 11, 0))
        self.assertEqual(work_entries[1].work_entry_type_id, self.attendance_type)
        self.assertEqual(work_entries[2].date_start, datetime(2022, 12, 12, 12, 0))
        self.assertEqual(work_entries[2].date_stop, datetime(2022, 12, 12, 16, 0))
        self.assertEqual(work_entries[2].work_entry_type_id, self.attendance_type)
        self.assertEqual(work_entries[3].date_start, datetime(2022, 12, 12, 16, 0))
        self.assertEqual(work_entries[3].date_stop, datetime(2022, 12, 12, 20, 0))
        self.assertEqual(work_entries[3].work_entry_type_id, self.overtime_type)

    def test_03_overtime_classic_day_before(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 12, 6),
            'check_out': datetime(2022, 12, 12, 15),
        })
        work_entries = self.contract.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12)).sorted('date_start')
        self.assertEqual(len(work_entries), 3)
        self.assertEqual(work_entries[0].date_start, datetime(2022, 12, 12, 6, 0))
        self.assertEqual(work_entries[0].date_stop, datetime(2022, 12, 12, 7, 0))
        self.assertEqual(work_entries[0].work_entry_type_id, self.overtime_type)
        self.assertEqual(work_entries[1].date_start, datetime(2022, 12, 12, 7, 0))
        self.assertEqual(work_entries[1].date_stop, datetime(2022, 12, 12, 11, 0))
        self.assertEqual(work_entries[1].work_entry_type_id, self.attendance_type)
        self.assertEqual(work_entries[2].date_start, datetime(2022, 12, 12, 12, 0))
        self.assertEqual(work_entries[2].date_stop, datetime(2022, 12, 12, 16, 0))
        self.assertEqual(work_entries[2].work_entry_type_id, self.attendance_type)

    def test_04_overtime_classic_day_after(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 12, 11),
            'check_out': datetime(2022, 12, 12, 17),
        })
        work_entries = self.contract.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12)).sorted('date_start')
        self.assertEqual(len(work_entries), 3)
        self.assertEqual(work_entries[0].date_start, datetime(2022, 12, 12, 7, 0))
        self.assertEqual(work_entries[0].date_stop, datetime(2022, 12, 12, 11, 0))
        self.assertEqual(work_entries[0].work_entry_type_id, self.attendance_type)
        self.assertEqual(work_entries[1].date_start, datetime(2022, 12, 12, 12, 0))
        self.assertEqual(work_entries[1].date_stop, datetime(2022, 12, 12, 16, 0))
        self.assertEqual(work_entries[1].work_entry_type_id, self.attendance_type)
        self.assertEqual(work_entries[2].date_start, datetime(2022, 12, 12, 16, 0))
        self.assertEqual(work_entries[2].date_stop, datetime(2022, 12, 12, 17, 0))
        self.assertEqual(work_entries[2].work_entry_type_id, self.overtime_type)

    def test_05_overtime_week_end(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 10, 11),
            'check_out': datetime(2022, 12, 10, 17),
        })
        work_entries = self.contract.generate_work_entries(date(2022, 12, 10), date(2022, 12, 10)).sorted('date_start')
        self.assertEqual(len(work_entries), 1)
        self.assertEqual(work_entries.date_start, datetime(2022, 12, 10, 11, 0))
        self.assertEqual(work_entries.date_stop, datetime(2022, 12, 10, 17, 0))
        self.assertEqual(work_entries.work_entry_type_id, self.overtime_type)

    def test_06_no_overtime_public_time_off_whole_day(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Public Time Off",
            'calendar_id': False,
            'company_id': self.env.company.id,
            'resource_id': False,
            'date_from': datetime(2022, 12, 26, 0, 0, 0),
            'date_to': datetime(2022, 12, 26, 23, 59, 59),
            'time_type': "leave",
            'work_entry_type_id': self.work_entry_type_public_type_off.id,
        }])
        work_entries = self.contract.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26)).sorted('date_start')
        self.assertEqual(len(work_entries), 2)
        self.assertEqual(work_entries[0].date_start, datetime(2022, 12, 26, 7, 0))
        self.assertEqual(work_entries[0].date_stop, datetime(2022, 12, 26, 11, 0))
        self.assertEqual(work_entries[0].work_entry_type_id, self.work_entry_type_public_type_off)
        self.assertEqual(work_entries[1].date_start, datetime(2022, 12, 26, 12, 0))
        self.assertEqual(work_entries[1].date_stop, datetime(2022, 12, 26, 16, 0))
        self.assertEqual(work_entries[1].work_entry_type_id, self.work_entry_type_public_type_off)

    def test_07_overtime_public_time_off_whole_day(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Public Time Off",
            'calendar_id': False,
            'company_id': self.env.company.id,
            'resource_id': False,
            'date_from': datetime(2022, 12, 26, 0, 0, 0),
            'date_to': datetime(2022, 12, 26, 23, 59, 59),
            'time_type': "leave",
            'work_entry_type_id': self.work_entry_type_public_type_off.id,
        }])
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 26, 6),
            'check_out': datetime(2022, 12, 26, 20),
        })
        work_entries = self.contract.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26)).sorted('date_start')
        self.assertEqual(len(work_entries), 2)
        self.assertEqual(work_entries[0].date_start, datetime(2022, 12, 26, 6, 0))
        self.assertEqual(work_entries[0].date_stop, datetime(2022, 12, 26, 11, 0))
        self.assertEqual(work_entries[0].work_entry_type_id, self.overtime_type)
        self.assertEqual(work_entries[1].date_start, datetime(2022, 12, 26, 12, 0))
        self.assertEqual(work_entries[1].date_stop, datetime(2022, 12, 26, 20, 0))
        self.assertEqual(work_entries[1].work_entry_type_id, self.overtime_type)

    def test_08_overtime_public_time_off_half_day(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Public Time Off",
            'calendar_id': False,
            'company_id': self.env.company.id,
            'resource_id': False,
            'date_from': datetime(2022, 12, 26, 0, 0, 0),
            'date_to': datetime(2022, 12, 26, 23, 59, 59),
            'time_type': "leave",
            'work_entry_type_id': self.work_entry_type_public_type_off.id,
        }])
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 26, 6),
            'check_out': datetime(2022, 12, 26, 11),
        })
        work_entries = self.contract.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26)).sorted('date_start')
        self.assertEqual(len(work_entries), 2)
        self.assertEqual(work_entries[0].date_start, datetime(2022, 12, 26, 6, 0))
        self.assertEqual(work_entries[0].date_stop, datetime(2022, 12, 26, 11, 0))
        self.assertEqual(work_entries[0].work_entry_type_id, self.overtime_type)
        self.assertEqual(work_entries[1].date_start, datetime(2022, 12, 26, 12, 0))
        self.assertEqual(work_entries[1].date_stop, datetime(2022, 12, 26, 16, 0))
        self.assertEqual(work_entries[1].work_entry_type_id, self.work_entry_type_public_type_off)

    def test_09_overtime_public_time_off_1_hour(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Public Time Off",
            'calendar_id': False,
            'company_id': self.env.company.id,
            'resource_id': False,
            'date_from': datetime(2022, 12, 26, 0, 0, 0),
            'date_to': datetime(2022, 12, 26, 23, 59, 59),
            'time_type': "leave",
            'work_entry_type_id': self.work_entry_type_public_type_off.id,
        }])
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 26, 10),
            'check_out': datetime(2022, 12, 26, 11),
        })
        work_entries = self.contract.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26)).sorted('date_start')
        self.assertEqual(len(work_entries), 3)
        self.assertEqual(work_entries[0].date_start, datetime(2022, 12, 26, 7, 0))
        self.assertEqual(work_entries[0].date_stop, datetime(2022, 12, 26, 10, 0))
        self.assertEqual(work_entries[0].work_entry_type_id, self.work_entry_type_public_type_off)
        self.assertEqual(work_entries[1].date_start, datetime(2022, 12, 26, 10, 0))
        self.assertEqual(work_entries[1].date_stop, datetime(2022, 12, 26, 11, 0))
        self.assertEqual(work_entries[1].work_entry_type_id, self.overtime_type)
        self.assertEqual(work_entries[2].date_start, datetime(2022, 12, 26, 12, 0))
        self.assertEqual(work_entries[2].date_stop, datetime(2022, 12, 26, 16, 0))
        self.assertEqual(work_entries[2].work_entry_type_id, self.work_entry_type_public_type_off)

    def test_10_overtime_public_time_off_1_hour_inside(self):
        self.env['resource.calendar.leaves'].create([{
            'name': "Public Time Off",
            'calendar_id': False,
            'company_id': self.env.company.id,
            'resource_id': False,
            'date_from': datetime(2022, 12, 26, 0, 0, 0),
            'date_to': datetime(2022, 12, 26, 23, 59, 59),
            'time_type': "leave",
            'work_entry_type_id': self.work_entry_type_public_type_off.id,
        }])
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 26, 9),
            'check_out': datetime(2022, 12, 26, 10),
        })
        work_entries = self.contract.generate_work_entries(date(2022, 12, 26), date(2022, 12, 26)).sorted('date_start')
        self.assertEqual(len(work_entries), 4)
        self.assertEqual(work_entries[0].date_start, datetime(2022, 12, 26, 7, 0))
        self.assertEqual(work_entries[0].date_stop, datetime(2022, 12, 26, 9, 0))
        self.assertEqual(work_entries[0].work_entry_type_id, self.work_entry_type_public_type_off)
        self.assertEqual(work_entries[1].date_start, datetime(2022, 12, 26, 9, 0))
        self.assertEqual(work_entries[1].date_stop, datetime(2022, 12, 26, 10, 0))
        self.assertEqual(work_entries[1].work_entry_type_id, self.overtime_type)
        self.assertEqual(work_entries[2].date_start, datetime(2022, 12, 26, 10, 0))
        self.assertEqual(work_entries[2].date_stop, datetime(2022, 12, 26, 11, 0))
        self.assertEqual(work_entries[2].work_entry_type_id, self.work_entry_type_public_type_off)
        self.assertEqual(work_entries[3].date_start, datetime(2022, 12, 26, 12, 0))
        self.assertEqual(work_entries[3].date_stop, datetime(2022, 12, 26, 16, 0))
        self.assertEqual(work_entries[3].work_entry_type_id, self.work_entry_type_public_type_off)

    def test_11_overtime_classic_day_under_threshold(self):
        self.contract.company_id.overtime_company_threshold = 15
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 12, 15),
            'check_out': datetime(2022, 12, 12, 16, 13),
        })
        work_entries = self.contract.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12)).sorted('date_start')
        self.assertEqual(len(work_entries), 2)
        self.assertEqual(work_entries[0].date_start, datetime(2022, 12, 12, 7, 0))
        self.assertEqual(work_entries[0].date_stop, datetime(2022, 12, 12, 11, 0))
        self.assertEqual(work_entries[0].work_entry_type_id, self.attendance_type)
        self.assertEqual(work_entries[1].date_start, datetime(2022, 12, 12, 12, 0))
        self.assertEqual(work_entries[1].date_stop, datetime(2022, 12, 12, 16, 0))
        self.assertEqual(work_entries[1].work_entry_type_id, self.attendance_type)

    def test_12_overtime_classic_day_below_threshold(self):
        self.contract.company_id.overtime_company_threshold = 15
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2022, 12, 12, 15),
            'check_out': datetime(2022, 12, 12, 16, 18),
        })
        work_entries = self.contract.generate_work_entries(date(2022, 12, 12), date(2022, 12, 12)).sorted('date_start')
        self.assertEqual(len(work_entries), 3)
        self.assertEqual(work_entries[0].date_start, datetime(2022, 12, 12, 7, 0))
        self.assertEqual(work_entries[0].date_stop, datetime(2022, 12, 12, 11, 0))
        self.assertEqual(work_entries[0].work_entry_type_id, self.attendance_type)
        self.assertEqual(work_entries[1].date_start, datetime(2022, 12, 12, 12, 0))
        self.assertEqual(work_entries[1].date_stop, datetime(2022, 12, 12, 16, 0))
        self.assertEqual(work_entries[1].work_entry_type_id, self.attendance_type)
        self.assertEqual(work_entries[2].date_start, datetime(2022, 12, 12, 16, 0))
        self.assertEqual(work_entries[2].date_stop, datetime(2022, 12, 12, 16, 18))
        self.assertEqual(work_entries[2].work_entry_type_id, self.overtime_type)
