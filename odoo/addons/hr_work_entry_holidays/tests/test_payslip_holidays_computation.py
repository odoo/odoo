# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date

from odoo.addons.hr_work_entry_holidays.tests.common import TestWorkEntryHolidaysBase


class TestPayslipHolidaysComputation(TestWorkEntryHolidaysBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'requires_allocation': 'no',
            'work_entry_type_id': cls.work_entry_type_leave.id
        })

    def test_work_data(self):
        start = datetime(2015, 11, 8, 8, 0)
        end = datetime(2015, 11, 10, 22, 0)
        leave = self.env['hr.leave'].create({
            'name': 'Doctor Appointment',
            'employee_id': self.jules_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': start,
            'request_date_to': end,
        })
        leave.action_approve()

        work_entries = self.jules_emp.contract_ids.generate_work_entries(date(2015, 11, 10), date(2015, 11, 21))
        work_entries.action_validate()
        work_entries = work_entries.filtered(lambda we: we.work_entry_type_id in self.env.ref('hr_work_entry.work_entry_type_attendance'))
        sum_hours = sum(work_entries.mapped('duration'))
        self.assertEqual(sum_hours, 59, 'It should count 59 attendance hours')  # 24h first contract + 35h second contract
