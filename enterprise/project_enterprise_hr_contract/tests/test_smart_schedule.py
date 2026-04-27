# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.addons.project_enterprise_hr.tests.auto_shift_dates_hr_common import AutoShiftDatesHRCommon


class ProjectEnterpriseHrTestSmartSchedule(AutoShiftDatesHRCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.contract = cls.env['hr.contract'].create({
            'date_start': datetime(2023, 1, 1),
            'date_end': datetime(2023, 8, 10),
            'name': 'CDD Contract for Armande ProjectUser',
            'resource_calendar_id': cls.calendar_morning.id,
            'wage': 5000.0,
            'employee_id': cls.armande_employee.id,
            'state': 'close',
        })

    def test_auto_plan_with_expired_contract(self):
        self.task_1.write({
            "planned_date_begin": False,
            "date_deadline": False,
        })

        res = self.task_1.with_context({
            'last_date_view': '2023-10-31 22:00:00',
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': '2023-08-15 22:00:00',
            'date_deadline': '2023-10-16 21:59:59',
            'user_ids': self.armande_employee.user_id.ids,
        })

        self.assertEqual(next(iter(res[0].keys())), 'no_intervals')
        self.assertEqual(res[1], {}, "no pills planned")
        self.assertFalse(self.task_1.planned_date_begin)
        self.assertFalse(self.task_1.date_deadline)
