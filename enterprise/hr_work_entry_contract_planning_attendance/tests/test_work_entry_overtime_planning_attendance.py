# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date

from odoo.tests import tagged, TransactionCase, HttpCase


@tagged('-at_install', 'post_install')
class HrWorkEntryContractTest(HttpCase, TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')
        cls.env.company.resource_calendar_id.tz = "Europe/Brussels"
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Homelander',
            'tz': 'UTC',
        })
        cls.contract = cls.env['hr.contract'].create({
            'name': 'Homelander\'s contract',
            'employee_id': cls.employee.id,
            'wage': 35000,
            'work_entry_source': 'planning',
            'date_start': date(2024, 1, 1),
            'state': 'open',
        })
        cls.slots = cls.env['planning.slot'].create({
            'resource_id': cls.contract.employee_id.resource_id.id,
            'start_datetime': datetime(2024, 7, 16, 8, 0, 0),
            'end_datetime': datetime(2024, 7, 16, 16, 0, 0),
            'state': 'published',
        })
        cls.attendance_type = cls.env.ref('hr_work_entry.work_entry_type_attendance')
        cls.overtime_type = cls.env.ref('hr_work_entry.overtime_work_entry_type')

    def test_overtime_work_entry_by_planning(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2024, 7, 16, 8, 0, 0),
            'check_out': datetime(2024, 7, 16, 18, 0, 0),
        })

        work_entries = self.contract.generate_work_entries(date(2024, 7, 1), date(2024, 7, 31)).sorted('date_start')
        another_work_entry = self.contract.generate_work_entries(date(2024, 7, 1), date(2024, 7, 31)).sorted('date_start')
        self.assertEqual(len(work_entries), 2)
        self.assertEqual(work_entries[0].date_start, datetime(2024, 7, 16, 8, 0))
        self.assertEqual(work_entries[0].date_stop, datetime(2024, 7, 16, 16, 0))
        self.assertEqual(work_entries[0].work_entry_type_id, self.attendance_type)
        self.assertEqual(work_entries[1].date_start, datetime(2024, 7, 16, 16, 0))
        self.assertEqual(work_entries[1].date_stop, datetime(2024, 7, 16, 18, 0))
        self.assertEqual(work_entries[1].work_entry_type_id, self.overtime_type)

        # should not generate the work entry becuase the work entry for that woking day is already generated
        self.assertFalse(another_work_entry)
