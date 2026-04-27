# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tests import tagged, freeze_time

from .test_smart_schedule_common import TestSmartScheduleCommon


@tagged('-at_install', 'post_install')
@freeze_time('2023-01-01')
class TestSmartSchedule(TestSmartScheduleCommon):
    def test_tasks_allocated_hours_multiple_users(self):
        result = (
            self.task_project_pigs_with_allocated_hours_user + self.task_project_pigs_with_allocated_hours_manager
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "week",
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectmanager.ids,
        })
        # Test no warning is displayed
        self.assertDictEqual(result[0], {}, 'No warnings should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 16:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 09:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.user_ids, self.user_projectmanager, "Wrong user id")
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.user_ids, self.user_projectmanager, "Wrong user id")

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

        self.user_projectmanager.resource_calendar_id = self.user_projectmanager.resource_calendar_id.copy()

        self.env['resource.calendar.leaves'].create([{
            'name': 'scheduled leave',
            'date_from': datetime(2023, 1, 3, 0),
            'date_to': datetime(2023, 1, 6, 23),
            'calendar_id': self.user_projectuser.resource_calendar_id.id,
            'time_type': 'leave',
        }, {
            'name': 'scheduled leave',
            'date_from': datetime(2023, 1, 5, 0),
            'date_to': datetime(2023, 1, 10, 23),
            'calendar_id': self.user_projectmanager.resource_calendar_id.id,
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

    def test_tasks_allocated_hours_no_user(self):
        result = (
            self.task_project_pigs_with_allocated_hours_user + self.task_project_pigs_with_allocated_hours_no_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "week",
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': None,
        })
        # That no warning is displayed
        self.assertDictEqual(result[0], {}, 'No warnings should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 16:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_no_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_no_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertFalse(self.task_project_pigs_with_allocated_hours_no_user.user_ids, "Wrong user id")

    def test_tasks_allocated_hours_multiple_projects(self):
        result = (
            self.task_project_pigs_with_allocated_hours_manager + self.task_project_goats_with_allocated_hours_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "week",
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectmanager.ids,
        })
        # Test no warning is displayed
        self.assertDictEqual(result[0], {}, 'No warnings should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 11:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.user_ids, self.user_projectmanager, "Wrong user id")
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.user_ids, self.user_projectmanager, "Wrong user id")

    def test_tasks_allocated_hours_with_leaves(self):
        # Creation of a leave from tuesday to thursday
        begin_leave = self.start_date_view + relativedelta(days=2)
        end_leave = begin_leave + relativedelta(days=2)
        self.env['resource.calendar.leaves'].create([
            {
                'name': 'scheduled leave',
                'date_from': begin_leave.strftime('%Y-%m-%d %H:%M:%S'),
                'date_to': end_leave.strftime('%Y-%m-%d %H:%M:%S'),
                'calendar_id': self.user_projectuser.resource_calendar_id.id,
                'time_type': 'leave',
            },
        ])

        result = (
            self.task_project_pigs_with_allocated_hours_user + self.task_project_goats_with_allocated_hours_user
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
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 16:00:00',
                         )
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-05 07:00:00',
                         )
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-06 09:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_goats_with_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")

    def test_tasks_allocated_hours_dependency(self):
        task_already_planned = self.env['project.task'].create(
            {
                'name': 'task_already_planned',
                'planned_date_begin': self.start_date_view + relativedelta(days=3),
                'date_deadline': self.start_date_view + relativedelta(days=4),
                'project_id': self.project_pigs.id,
                'user_ids': [self.user_projectuser.id],
            },
        )
        self.task_project_pigs_with_allocated_hours_user.depend_on_ids |= task_already_planned

        result = (
            self.task_project_pigs_with_allocated_hours_user
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
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-05 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-05 16:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")

    def test_tasks_no_allocated_hours_for_day_scale(self):
        result = (
            self.task_project_pigs_with_allocated_hours_manager + self.task_project_pigs_no_allocated_hours_user + self.task_project_pigs_no_allocated_hours_no_user + self.task_project_goats_no_allocated_hours_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "day",
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectuser.ids,
        })
        # Test no warning is displayed
        self.assertDictEqual(result[0], {}, 'No warnings should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 14:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 14:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-06 09:00:00',
                         )
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-06 09:00:00',
                         )
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-09 14:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")

    def test_tasks_no_allocated_hours_for_week_scale(self):
        result = (
            self.task_project_pigs_with_allocated_hours_manager + self.task_project_pigs_no_allocated_hours_user + self.task_project_pigs_no_allocated_hours_no_user + self.task_project_goats_no_allocated_hours_user
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
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 14:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-04 14:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-06 09:00:00',
                         )
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-06 09:00:00',
                         )
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-09 14:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")

    def test_tasks_no_allocated_hours_for_month_scale_with_precision_one_day(self):
        result = (
            self.task_project_pigs_with_allocated_hours_manager + self.task_project_pigs_no_allocated_hours_user + self.task_project_pigs_no_allocated_hours_no_user + self.task_project_goats_no_allocated_hours_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "month",
            'cell_part': 1.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectuser.ids,
        })
        # Test no warning is displayed
        self.assertDictEqual(result[0], {}, 'No warnings should be displayed')
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-06 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-06 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-11 09:00:00',
                         )
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-11 09:00:00',
                         )
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-16 09:00:00',
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.user_ids, self.user_projectuser, "Wrong user id")
        self.assertEqual(self.task_project_goats_no_allocated_hours_user.user_ids, self.user_projectuser, "Wrong user id")

    def test_tasks_no_allocated_hours_for_year_scale(self):
        (
            self.task_project_pigs_with_allocated_hours_manager + self.task_project_pigs_no_allocated_hours_user + self.task_project_pigs_no_allocated_hours_manager + self.task_project_pigs_no_allocated_hours_no_user
        ).with_context({
            'last_date_view': self.end_date_view_str,
            'gantt_scale': "year",
            'cell_part': 1.0,
        }).schedule_tasks({
            'planned_date_begin': self.start_date_view_str,
            'date_deadline': (self.start_date_view + relativedelta(day=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_ids': self.user_projectmanager.ids,
        })
        # Checking of the planned dates
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-02 07:00:00',
                         )
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-03 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-31 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_manager.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-01-31 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_manager.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-02-28 09:00:00',
                         'when no allocated hours, delta hours = 160, from 9H day 31/01 to 9H day 28/02, duration = 20 * 8 = 160'
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.planned_date_start.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-02-28 09:00:00',
                         )
        self.assertEqual(self.task_project_pigs_no_allocated_hours_no_user.date_deadline.strftime('%Y-%m-%d %H:%M:%S'),
                         '2023-03-28 08:00:00',
                         """
                            when no allocated hours, delta hours = 160, from 9H day 28/02 to 9H day 28/03, duration = 20 * 8 = 160
                            It's 8H on day 28 instead of 9H in the assert because Daylight Saving Time (DST) in Europe in 2023 began
                            on Sunday, March 26, 2023
                         """
                         )
        # Check if the user is the target one
        self.assertEqual(self.task_project_pigs_with_allocated_hours_manager.user_ids, self.user_projectmanager, "Wrong user id")
        self.assertEqual(self.task_project_pigs_no_allocated_hours_user.user_ids, self.user_projectmanager, "Wrong user id")

    def test_smart_schedule_with_allocated_hours_and_deadlines(self):
        """ test if the recordset is correctly sorted when multiple dependencies are involved """
        self.user_projectmanager.write({
            "tz": "Europe/Brussels",
            "resource_calendar_id": self.env['ir.model.data']._xmlid_to_res_id("resource.resource_calendar_std"),
        })

        vals_list = [{
            'name': f"Task (deadline: {day_of_week}, allocated: {allocated_hours}h, priority: {priority})",
            'date_deadline': date_deadline,
            'allocated_hours': allocated_hours,
            'priority': priority,
        } for date_deadline, day_of_week in [(False, "None"), (datetime(2023, 10, 17, 10, 0), "Tuesday"), (datetime(2023, 10, 18, 10, 0), "Wednesday")]
            for allocated_hours in [0, 8]
                for priority in ["0", "1"]
        ]

        tasks = self.env['project.task'].with_context({
            'mail_create_nolog': True,
            'default_project_id': self.project_pigs.id,
        }).create(vals_list)

        # Click on the magnifying glass, on Monday's cell, to schedule the tasks
        tasks.with_context({
            'last_date_view': '2023-10-31 22:00:00',
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': '2023-10-15 22:00:00',
            'date_deadline': '2023-10-16 21:59:59',
            'user_ids': self.user_projectmanager.ids,
        })
        # the project will automatically be timesheetable since the default value is true and so the allocated_hours will
        # not be recomputed when the project is timesheetable since we assume the user will manually set the allocated
        # hours on his tasks to correctly timesheets.
        allocated_hours = 0 if self.is_module_timesheet_grid_installed else 12
        self.assertEqual(
            tasks.sorted('planned_date_begin').mapped(lambda t: (t.name, t.allocated_hours, t.planned_date_begin, t.date_deadline)),
            [
                ('Task (deadline: Tuesday, allocated: 8h, priority: 1)', 8.0, datetime(2023, 10, 16, 6, 0), datetime(2023, 10, 16, 15, 0)),
                ('Task (deadline: Tuesday, allocated: 8h, priority: 0)', 8.0, datetime(2023, 10, 17, 6, 0), datetime(2023, 10, 17, 15, 0)),
                ('Task (deadline: Tuesday, allocated: 0h, priority: 1)', allocated_hours, datetime(2023, 10, 18, 6, 0), datetime(2023, 10, 19, 10, 0)),
                ('Task (deadline: Tuesday, allocated: 0h, priority: 0)', allocated_hours, datetime(2023, 10, 19, 11, 0), datetime(2023, 10, 20, 15, 0)),
                ('Task (deadline: Wednesday, allocated: 8h, priority: 1)', 8.0, datetime(2023, 10, 23, 6, 0), datetime(2023, 10, 23, 15, 0)),
                ('Task (deadline: Wednesday, allocated: 8h, priority: 0)', 8.0, datetime(2023, 10, 24, 6, 0), datetime(2023, 10, 24, 15, 0)),
                ('Task (deadline: Wednesday, allocated: 0h, priority: 1)', allocated_hours, datetime(2023, 10, 25, 6, 0), datetime(2023, 10, 26, 10, 0)),
                ('Task (deadline: Wednesday, allocated: 0h, priority: 0)', allocated_hours, datetime(2023, 10, 26, 11, 0), datetime(2023, 10, 27, 15, 0)),
                ('Task (deadline: None, allocated: 8h, priority: 1)', 8.0, datetime(2023, 10, 30, 7, 0), datetime(2023, 10, 30, 16, 0)),
                ('Task (deadline: None, allocated: 8h, priority: 0)', 8.0, datetime(2023, 10, 31, 7, 0), datetime(2023, 10, 31, 16, 0)),
                ('Task (deadline: None, allocated: 0h, priority: 1)', 12.0, datetime(2023, 11, 1, 7, 0), datetime(2023, 11, 2, 11, 0)),
                ('Task (deadline: None, allocated: 0h, priority: 0)', 12.0, datetime(2023, 11, 2, 12, 0), datetime(2023, 11, 3, 16, 0)),
            ],
            """
            We expect the tasks to be sorted as follows:
                - 3 groups of 4 tasks, having respectively and in that order Tuesday, Wednesday, None as deadline.
                - In each group, 2 subgroups of 2 tasks, having respectively and in that order 8h and 0h allocated.
                - In each subgroup, 2 tasks, having respectively and in that order priority 1 and 0.
            Moreover, the tasks with 8h allocated should take the whole day, while the tasks with 0h allocated should take half a day.
            """
        )

    def test_smart_schedule_impossible_deadline(self):
        """ test if the recordset is correctly sorted when multiple dependencies are involved """
        self.user_projectmanager.tz = "Europe/Brussels"
        tasks = task_concu, *dummy = self.env['project.task'].with_context({
            'mail_create_nolog': True,
            'default_project_id': self.project_pigs.id,
        }).create([{
            # This task is planned for "tomorrow".
            'name': "Task concu",
            'user_ids': self.user_projectmanager.ids,
            'planned_date_begin': datetime(2023, 10, 17, 6, 0),
            'date_deadline': datetime(2023, 10, 17, 15, 0),
        }, {
            # This task has the closest deadline => planned first
            'name': "Task (allocated: 1, deadline: Tuesday)",
            'date_deadline': datetime(2023, 10, 17, 10, 0),
            'allocated_hours': 16,
        }, {
            'name': "Task (allocated: 1 days, deadline: Friday)",
            'date_deadline': datetime(2023, 10, 20, 10, 0),
            'allocated_hours': 8,
        }])
        tasks -= task_concu

        tasks.with_context({
            'last_date_view': '2023-10-31 22:00:00',
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': '2023-10-15 22:00:00',
            'date_deadline': '2023-10-16 21:59:59',
            'user_ids': self.user_projectmanager.ids,
        })

        self.assertEqual(
            tasks.sorted('planned_date_begin').mapped(lambda t: (t.allocated_hours, t.planned_date_begin, t.date_deadline)),
            [
                (16.0 if self.is_module_timesheet_grid_installed else 24.0, datetime(2023, 10, 16, 6, 0), datetime(2023, 10, 18, 15, 0)),
                (8.0, datetime(2023, 10, 19, 6, 0), datetime(2023, 10, 19, 15, 0)),
            ],
        )

    def test_undo_scheduling(self):
        old_vals = {
            self.task_project_pigs_with_allocated_hours_user.id: {
                "planned_date_begin": False,
                "date_deadline": datetime(2023, 10, 19, 15, 0),
                # user_id will not be changed as it's already assigned to user_projectuser in the first iteration
            },
            self.task_project_pigs_with_allocated_hours_manager.id: {
                "planned_date_begin": False,
                "date_deadline": datetime(2024, 9, 18, 15, 0),
                "user_ids": [self.user_projectmanager.id],
            },
            self.task_project_pigs_with_allocated_hours_no_user.id: {
                "planned_date_begin": False,
                "date_deadline": False,
                "user_ids": False,
            },
            self.task_project_pigs_no_allocated_hours_user.id: {
                "planned_date_begin": False,
                "date_deadline": False,
                # user_id will not be changed as user_projectuser is part of the assignees in the first iteration
            },
        }

        self.task_project_pigs_with_allocated_hours_user.write({"date_deadline": datetime(2023, 10, 19, 15, 0)})
        self.task_project_pigs_with_allocated_hours_manager.write({"date_deadline": datetime(2024, 9, 18, 15, 0)})
        self.task_project_pigs_no_allocated_hours_user.write({"user_ids": [self.user_projectuser.id, self.user_projectmanager.id]})

        tasks_to_schedule = self.task_project_pigs_with_allocated_hours_user + self.task_project_pigs_with_allocated_hours_manager + self.task_project_pigs_with_allocated_hours_no_user + self.task_project_pigs_no_allocated_hours_user

        for new_user in [self.user_projectuser.ids, False]:
            if not new_user:
                # when planning from not assigned line, user_ids will not change
                del old_vals[self.task_project_pigs_with_allocated_hours_no_user.id]["user_ids"]
                del old_vals[self.task_project_pigs_with_allocated_hours_manager.id]["user_ids"]

            result = tasks_to_schedule.with_context({
                'last_date_view': '2023-10-31 22:00:00',
                'cell_part': 2.0,
            }).schedule_tasks({
                'planned_date_begin': '2023-10-15 22:00:00',
                'date_deadline': '2023-10-16 21:59:59',
                'user_ids': new_user,
            })

            self.assertDictEqual(result[1], old_vals)
            tasks_to_schedule.action_rollback_auto_scheduling({str(task_id): vals for task_id, vals in result[1].items()})

            for task in tasks_to_schedule:
                for field in ["planned_date_begin", "date_deadline", "user_ids"]:
                    if field in old_vals[task.id]:
                        self.assertEqual(task[field].ids or False if field == "user_ids" else task[field], old_vals[task.id][field])

    def test_load_more_intervals(self):
        """
            first, valid intervals will be between planned_date_begin and last_date_view
            only 16 hours can be planned during these 2 days (30, 31)

            then, loading more intervals will run and get other ranges starting from 01 Dec 2023
            day 01, 02 and 03 will be enough to plan the 24 remaining hours
        """
        self.task_project_pigs_with_allocated_hours_user.allocated_hours = 40
        self.task_project_pigs_with_allocated_hours_user.with_context({
            'last_date_view': '2023-10-31 22:00:00',
            'cell_part': 2.0,
        }).schedule_tasks({
            'planned_date_begin': '2023-10-30 00:00:00',
            'date_deadline': '2023-10-31 22:00:00',
            'user_ids': self.user_projectmanager.ids,
        })

        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.planned_date_begin, datetime(2023, 10, 30, 7))
        self.assertEqual(self.task_project_pigs_with_allocated_hours_user.date_deadline, datetime(2023, 11, 3, 16))
