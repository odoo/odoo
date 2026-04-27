# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tests import tagged, freeze_time
from odoo.addons.project_enterprise.tests.test_smart_schedule_common import TestSmartScheduleCommon


@tagged('-at_install', 'post_install')
@freeze_time('2023-01-01')
class TestSmartSchedule(TestSmartScheduleCommon):
    def test_multi_users_tasks(self):
        """
            user_projectuser     [task_project_pigs_with_allocated_hours_user] [task_project_goats_with_allocated_hours_user]                                               [task_project_pigs_no_allocated_hours_user]
                                                                            |                                                                                                ^
                                                                            |                                                                                                |
                                                                            |                                                                                                |
            user_projectmanager                                             ------------------------------------------------>[task_project_pigs_with_allocated_hours_manager]-
            and user_projectuser
        """
        self.task_project_pigs_with_allocated_hours_manager.write({
            "user_ids": [self.user_projectmanager.id, self.user_projectuser.id],
            "depend_on_ids": [self.task_project_pigs_with_allocated_hours_user.id],
            "dependent_ids": [self.task_project_pigs_no_allocated_hours_user.id],
            "date_deadline": datetime(2023, 2, 2),
        })

        self.task_project_pigs_no_allocated_hours_user.write({
            "user_ids": [self.user_projectuser.id],
        })

        self.env["hr.employee"].create([{
            "name": self.user_projectuser.name,
            "user_id": self.user_projectuser.id
        }, {
            "name": self.user_projectmanager.name,
            "user_id": self.user_projectmanager.id
        }])

        self.env['resource.calendar.leaves'].create([{
            'name': 'scheduled leave',
            'date_from': datetime(2023, 1, 3, 0),
            'date_to': datetime(2023, 1, 6, 23),
            'resource_id': self.user_projectuser.employee_id.resource_id.id,
            'time_type': 'leave',
        }, {
            'name': 'scheduled leave',
            'date_from': datetime(2023, 1, 5, 0),
            'date_to': datetime(2023, 1, 10, 23),
            'resource_id': self.user_projectmanager.employee_id.resource_id.id,
            'time_type': 'leave',
        }])

        result = (
            self.task_project_pigs_with_allocated_hours_user + self.task_project_pigs_with_allocated_hours_manager + self.task_project_pigs_no_allocated_hours_user + self.task_project_goats_with_allocated_hours_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "week",
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectuser.ids,
        })
        # Test no warning is displayed
        self.assertDictEqual(result[0], {}, 'No warnings should be displayed')

        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.planned_date_begin, datetime(2023, 1, 2, 7))
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.date_deadline, datetime(2023, 1, 2, 16))

        # user_projectuser is off till 6
        # user_projectmanager is off till 10
        # the first possible time for both of them is starting from 11
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.planned_date_begin, datetime(2023, 1, 11, 7))
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.date_deadline, datetime(2023, 1, 12, 9 if self.is_module_timesheet_grid_installed else 11))

        # even that task_project_pigs_with_allocated_hours_manager was planned first as it has a deadline
        # smart scheduling is optimizing resources so
        # the gap in days 09 and 10 was filled to plan task_project_goats_with_allocated_hours_user
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.planned_date_begin, datetime(2023, 1, 9, 7))
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.date_deadline, datetime(2023, 1, 10, 9))

        # should not be planned after the old deadline of its parent, as its parent will be planned again
        # if the new deadline is before the old one, no need to block the task and plan it ASAP
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.planned_date_begin, datetime(2023, 1, 12, 9 if self.is_module_timesheet_grid_installed else 12))
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.date_deadline, datetime(2023, 1, 13, 14 if self.is_module_timesheet_grid_installed else 16))
