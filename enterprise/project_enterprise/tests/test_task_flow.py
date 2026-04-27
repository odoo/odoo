# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from markupsafe import Markup

from odoo import Command
from odoo.tests import Form, TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestTaskFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.resource_calendar_id.tz = "Europe/Brussels"
        cls.project_user = mail_new_test_user(
            cls.env, login='Armande',
            name='Armande Project_user', email='armande.project_user@example.com',
            notification_type='inbox',
            groups='project.group_project_user',
        )

        cls.project_test_user = mail_new_test_user(
            cls.env, login='Armando',
            name='Armando Project_user', email='armando.project_user@example.com',
            notification_type='inbox',
            groups='project.group_project_user',
        )

        cls.project_test = cls.env['project.project'].create({
            'name': 'Project Test',
        })

        cls.portal_user = mail_new_test_user(
            cls.env, login='portal_project',
            name='Portal_user', email='portal_project_user@example.com',
            notification_type='email',
            groups='base.group_portal',
        )

    def create_tasks(self, nb=40):
        now = datetime.combine(datetime.now(), datetime.min.time())
        hour_start = [6, 11]
        hour_end = [10, 15]
        users = [self.project_test_user, self.project_user, self.project_user | self.project_test_user]

        self.env['project.task'].with_context(tracking_disable=True).create([{
            'name': 'Fsm task ' + str(i),
            'user_ids': users[i % 3],
            'project_id': self.project_test.id,
            'planned_date_begin': now + relativedelta(days=i / 2, hour=hour_start[i % 2]),
            'date_deadline': now + relativedelta(days=i / 2, hour=hour_end[i % 2])
        } for i in range(0, nb)])

    @freeze_time('2023-01-02')
    def test_default_allocated_hours_when_creating_tasks(self):
        # Add allocated_hours to the task form view so that we can read its value
        form_view = self.env["ir.ui.view"].create({
            "name": "Test Form",
            "model": "project.task",
            "type": "form",
            "inherit_id": self.env.ref("project.view_task_form2").id,
            "arch": """
                <form position="inside">
                    <field name="allocated_hours"/>
                </form>
            """,
        })

        data = [{
                "scales": ["day", "week"],
                "dates": (datetime(2023, 1, 2), datetime(2023, 1, 2, 23, 59, 59)),
                "expected_dates": (datetime(2023, 1, 2), datetime(2023, 1, 2, 23, 59, 59)),
                "expected_allocated_hours": 8.0,
                "dates_message": """
                    For day and week scale, planned_date_begin and date_deadline should be the same as the ones selected by the user,
                    they should not be modified according to the user calendar.
                """,
                "allocated_hours_message": "allocated_hours should not be computed according to the dates selected by the user but to the intersection between dates and user calendar.",
                "second_date_deadline": datetime(2023, 1, 2, 13, 0, 0),
                "second_expected_allocated_hours": 5.0,
            }, {
                "scales": ["month", "year"],
                "dates": (datetime(2023, 1, 2), datetime(2023, 1, 6, 23, 59, 59)),
                "expected_dates": (datetime(2023, 1, 2, 7, 0), datetime(2023, 1, 6, 16, 0, 0)),
                "expected_allocated_hours": 40.0,
                "dates_message": "For month and year scale, planned_date_begin and date_deadline should be modified according to the user calendar.",
                "allocated_hours_message": "allocated_hours should be computed according to the modified dates.",
                "second_date_deadline": datetime(2023, 1, 5, 22, 0, 0),
                "second_expected_allocated_hours": 32.0,
            },
        ]

        for datum in data:
            for scale in datum["scales"]:
                with Form(self.env["project.task"].with_context({
                    'default_planned_date_begin': datum["dates"][0],
                    'default_date_deadline': datum["dates"][1],
                    'scale': scale,
                }), form_view) as task:
                    task.name = "Test"
                    task.user_ids = self.project_user
                    task.project_id = self.project_test
                    self.assertEqual(task.allocated_hours, datum["expected_allocated_hours"], datum["allocated_hours_message"])
                    self.assertEqual((task.planned_date_begin, task.date_deadline), datum["expected_dates"], datum["dates_message"])
                    task.date_deadline = datum["second_date_deadline"]
                    self.assertEqual(task.allocated_hours, datum["second_expected_allocated_hours"], "Allocated hours should be computed when the planned dates are modified")
                    task.planned_date_begin = False
                    self.assertEqual(task.allocated_hours, 0.0, "Allocated hours should be 0 as there is no planned_date_begin")

    def test_planning_overlap(self):
        task_A = self.env['project.task'].create({
            'name': 'Fsm task 1',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': datetime.now(),
            'date_deadline': datetime.now() + relativedelta(hours=4),
            'allocated_hours': 4,
        })
        task_B = self.env['project.task'].create({
            'name': 'Fsm task 2',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': datetime.now() + relativedelta(hours=2),
            'date_deadline': datetime.now() + relativedelta(hours=6),
            'allocated_hours': 4,
        })
        task_C = self.env['project.task'].create({
            'name': 'Fsm task 2',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': datetime.now() + relativedelta(hours=5),
            'date_deadline': datetime.now() + relativedelta(hours=7),
            'allocated_hours': 2,
        })
        task_D = self.env['project.task'].create({
            'name': 'Fsm task 2',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': datetime.now() + relativedelta(hours=8),
            'date_deadline': datetime.now() + relativedelta(hours=9),
            'allocated_hours': 1,
        })
        self.assertEqual(task_A.planning_overlap, Markup('<p>Armande Project_user has 1 tasks at the same time.</p>'))
        self.assertEqual(task_B.planning_overlap, Markup('<p>Armande Project_user has 2 tasks at the same time.</p>'))
        self.assertFalse(task_D.planning_overlap, "No task should be overlapping with task_D")

    def test_gantt_progress_bar(self):
        self.env['project.task'].create([{
            'name': 'Task 1',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': '2021-09-24 06:00:00',
            'date_deadline': '2021-09-24 15:00:00',
            'allocated_hours': 8,
        }, {
            'name': 'Task 2',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': '2021-09-27 06:00:00',
            'date_deadline': '2021-09-28 15:00:00',
            'allocated_hours': 16,
        }, {
            'name': 'Task 3',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': '2021-09-29 05:00:00',
            'date_deadline': '2021-09-29 08:00:00',
            'allocated_hours': 3,
        }, {
            'name': 'Task 4',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': '2021-09-30 12:00:00',
            'date_deadline': '2021-09-30 15:00:00',
            'allocated_hours': 3,
        }])

        start, stop = datetime(2021, 9, 26), datetime(2021, 10, 2, 23, 59, 59)
        progress_bar = self.env['project.task']._gantt_progress_bar(
            'user_ids', self.project_user.ids, start, stop
        )
        self.assertEqual(22, progress_bar[self.project_user.id]['value'], "User should have 22 hours planned on this period")
        self.assertEqual(40, progress_bar[self.project_user.id]['max_value'], "User is expected to work 40 hours on this period")

        self.env['project.task'].create([{
            'name': 'Task 5',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': '2021-10-02 06:00:00',
            'date_deadline': '2021-10-02 15:00:00',
            'allocated_hours': 8,
        }])

        progress_bar = self.env['project.task']._gantt_progress_bar(
            'user_ids', self.project_user.ids, start, stop
        )
        self.assertEqual(30, progress_bar[self.project_user.id]['value'], "User should have 30 hours planned on this period")
        self.assertEqual(40, progress_bar[self.project_user.id]['max_value'], "User is expected to work 40 hours on this period")

        self.env['project.task'].create([{
            'name': 'Task 6',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': '2021-09-24 06:00:00',
            'date_deadline': '2021-09-27 15:00:00',
            'allocated_hours': 16,
        }])

        progress_bar = self.env['project.task']._gantt_progress_bar(
            'user_ids', self.project_user.ids, start, stop
        )
        self.assertEqual(38, progress_bar[self.project_user.id]['value'], "User should have 38 hours planned on this period")
        self.assertEqual(40, progress_bar[self.project_user.id]['max_value'], "User is expected to work 40 hours on this period")

    def test_project_user_can_see_progress_bar(self):
        self.env['project.task'].create([{
            'name': 'Task 1',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': '2021-09-27 06:00:00',
            'date_deadline': '2021-09-28 15:00:00',
            'allocated_hours': 16,
        }])

        progress_bar = self.env['project.task'].with_user(self.project_test_user)._gantt_progress_bar(
            'user_ids', self.project_user.ids, datetime(2021, 9, 26), datetime(2021, 10, 2, 23, 59, 59)
        )
        self.assertEqual(16, progress_bar[self.project_user.id]['value'], "User should have 16 hours planned on this period")
        self.assertEqual(40, progress_bar[self.project_user.id]['max_value'], "User is expected to work 40 hours on this period")

    def test_portal_user_cannot_see_progress_bar(self):
        self.env['project.task'].create([{
            'name': 'Task 1',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': '2021-09-27 06:00:00',
            'date_deadline': '2021-09-28 15:00:00',
            'allocated_hours': 16,
        }])

        progress_bar = self.env['project.task'].with_user(self.portal_user)._gantt_progress_bar(
            'user_ids', self.project_user.ids, datetime(2021, 9, 26), datetime(2021, 10, 2, 23, 59, 59)
        )
        self.assertFalse(progress_bar, "Progress bar should be empty for non-project users")

    def test_planned_date_consistency_for_tasks(self):
        """ This test ensures that a task can not have date start set, if its date end is False"""
        task_1 = self.env['project.task'].create([{
            'name': 'Task 1',
            'user_ids': self.project_user,
            'project_id': self.project_test.id,
            'planned_date_begin': '2021-09-27 06:00:00',
            'date_deadline': '2021-09-28 15:00:00',
        }])

        task_1.planned_date_begin = False
        self.assertFalse(task_1.planned_date_begin, 'the planned date begin should be set to False')
        self.assertEqual('2021-09-28', task_1.date_deadline.strftime('%Y-%m-%d'))

        task_1.write({'planned_date_begin': '2021-09-27 06:00:00'})
        self.assertEqual('2021-09-27', task_1.planned_date_begin.strftime('%Y-%m-%d'), 'the planned date begin should be set to the new date')
        self.assertEqual('2021-09-28', task_1.date_deadline.strftime('%Y-%m-%d'), 'the planned date end should be set')

        task_1.date_deadline = False
        self.assertFalse(task_1.planned_date_begin, 'the planned date begin should be set to False')
        self.assertFalse(task_1.date_deadline, 'the planned date end should be set to False')

        task_1.write({'date_deadline': '2021-09-27 06:00:00'})
        self.assertFalse(task_1.planned_date_begin, 'the planned date begin should not be updated')
        self.assertEqual('2021-09-27', task_1.date_deadline.strftime('%Y-%m-%d'))

    def test_performance(self):
        nb = 40
        self.create_tasks(nb=nb)
        start = datetime.combine(datetime.now(), datetime.min.time()) + relativedelta(days=-1)
        end = start + relativedelta(days=nb / 2 + 1)
        users = self.project_user | self.project_test_user

        with self.assertQueryCount(__system__=9):
            # Query count should be stable even if the number of tasks or users increase (progress bar query count is O(1))
            progress_bar = self.env['project.task']._gantt_progress_bar(
                'user_ids', users.ids, start, end
            )

        self.assertEqual(len(progress_bar), 3)  # 2 users + 1 warning

    def test_editing_task_planned_date(self):
        """Check writing dates to a task:
            - when writing to a single task, write dates as given
            - when writing to multiple tasks, write dates as given if any task already had dates
            - otherwise, modify dates according to assignee's or company's schedule
        """
        def get_hours(task):
            return task.planned_date_begin.hour, task.date_deadline.hour

        self.env.company.resource_calendar_id.tz = 'UTC'
        self.project_user.resource_calendar_id = self.env.company.resource_calendar_id
        self.project_test_user.resource_calendar_id = self.env['resource.calendar'].create({
            'tz': 'UTC',
            'attendance_ids': [Command.create({
                'name': day,
                'dayofweek': day,
                'day_period': 'afternoon',
                'hour_from': 12,
                'hour_to': 19,
            }) for day in '12345'],
        })

        tasks = task_A, task_B, task_C = self.env['project.task'].create([{
            'name': "Task A - Armande",
            'user_ids': self.project_user.ids,
            'project_id': self.project_test.id,
        }, {
            'name': "Task B - Armando",
            'user_ids': self.project_test_user.ids,
            'project_id': self.project_test.id,
        }, {
            'name': "Task C - Planned",
            'user_ids': (self.project_user + self.project_test_user).ids,
            'project_id': self.project_test.id,
            # Wednesday 05:00:00 -> 10:00:00
            'planned_date_begin': '2024-08-27 05:00:00',
            'date_deadline': '2024-08-27 10:00:00',
        }])

        self.assertEqual(
            get_hours(task_C),
            (5, 10),
            "Create shouldn't overwrite hours",
        )

        (task_A + task_C).write({
            # Monday 00:00:00 -> 23:59:59 CET
            'planned_date_begin': '2024-08-26 00:00:00',
            'date_deadline': '2024-08-26 23:59:59',
        })
        self.assertListEqual(
            [get_hours(task_A), get_hours(task_C)],
            [(0, 23), (0, 23)],
            "Write shouldn't modify hours when batch processes includes task with dates",
        )

        task_B.write({
            # Tuesday 16:00:00 -> 21:00:00 CET
            'planned_date_begin': '2024-08-27 16:00:00',
            'date_deadline': '2024-08-27 21:00:00',
        })
        self.assertEqual(get_hours(task_B), (16, 21), "Hand-picked hours shouldn't change")

        tasks.date_deadline = False
        self.assertFalse(
            any(task.planned_date_begin for task in tasks),
            "Removing deadline should also remove planned_date_begin",
        )

        tasks.write({
            # Tuesday 16:00:00 -> 22:00:00 CET
            'planned_date_begin': '2024-08-27 16:00:00',
            'date_deadline': '2024-08-27 22:00:00',
        })
        self.assertListEqual(
            [get_hours(task) for task in tasks],
            [(16, 19), (16, 19), (16, 19)],
            "Batched tasks should be planned using schedule",
        )

        tasks.write({
            'date_deadline': False,
            'user_ids': self.project_user.ids,
        })
        (task_B + task_C).write({
            'planned_date_begin': '2024-03-24 06:00:00',
            'date_deadline': '2024-03-30 15:00:00',
        })
        self.assertEqual('2024-03-25', task_B.planned_date_begin.strftime('%Y-%m-%d'),
            'the planned date begin should be the first working day found according to the resource calendar of the user assigned and the start datetime selected by the user')
        self.assertEqual('2024-03-29', task_B.date_deadline.strftime('%Y-%m-%d'),
            'the planned date end should be the last working day found according to the resource calendar of the user assigned and the end datetime selected by the user')
        self.assertEqual('2024-03-25', task_C.planned_date_begin.strftime('%Y-%m-%d'),
            'the planned date begin should be the first working day found according to the resource calendar of the user assigned and the start datetime selected by the user')
        self.assertEqual('2024-03-29', task_C.date_deadline.strftime('%Y-%m-%d'),
            'the planned date end should be the last working day found according to the resource calendar of the user assigned and the end datetime selected by the user')

        tasks.write({
            'planned_date_begin': '2024-03-24 06:00:00',
            'date_deadline': '2024-03-30 15:00:00',
        })
        self.assertEqual('2024-03-24', task_A.planned_date_begin.strftime('%Y-%m-%d'),
            'the planned date begin should be the one selected by the user')
        self.assertEqual('2024-03-30', task_A.date_deadline.strftime('%Y-%m-%d'),
            'the planned date end should be the one selected by the user')
        self.assertEqual('2024-03-24', task_B.planned_date_begin.strftime('%Y-%m-%d'),
            'the planned date begin should be the one selected by the user')
        self.assertEqual('2024-03-30', task_B.date_deadline.strftime('%Y-%m-%d'),
            'the planned date end should be the one selected by the user')
        self.assertEqual('2024-03-24', task_C.planned_date_begin.strftime('%Y-%m-%d'),
            'the planned date begin should be the one selected by the user')
        self.assertEqual('2024-03-30', task_C.date_deadline.strftime('%Y-%m-%d'),
            'the planned date end should be the one selected by the user')

    @freeze_time('2023-01-02')
    def test_cancelling_future_task_reset_planned_date(self):
        task = self.env['project.task'].create({
            'name': 'Task',
            'project_id': self.project_test.id,
        })
        # 1) Cancel a task which has no begin date or deadline
        task.state = '1_canceled'
        self.assertFalse(task.planned_date_begin, 'The begin date should remain unset')
        self.assertFalse(task.date_deadline, 'The deadline should remain unset')

        # 2) Cancel a task which has only a deadline
        task.date_deadline = datetime.now() + relativedelta(hours=4)
        task.state = '1_canceled'
        self.assertFalse(task.planned_date_begin, 'The begin date should remain unset')
        self.assertEqual(task.date_deadline, datetime.now() + relativedelta(hours=4), 'The deadline should not have changed')

        # 3) Cancel a task which has both a begin date and a deadline, the begin date being prior than today's date (this is not a future task)
        task.planned_date_begin = datetime.now() - relativedelta(hours=1)
        task.state = '1_canceled'
        self.assertEqual(task.planned_date_begin, datetime.now() - relativedelta(hours=1), 'The begin date should not have changed as this is not a future task')
        self.assertEqual(task.date_deadline, datetime.now() + relativedelta(hours=4), 'The deadline should not have changed as this is not a future task')

        # 4) Cancel a task which has both a begin date and a deadline, the begin date being later than today's date (this is future task)
        task.planned_date_begin = datetime.now() + relativedelta(hours=1)
        task.state = '1_canceled'
        self.assertFalse(task.planned_date_begin, 'The begin date should be reset as this is a future task')
        self.assertFalse(task.date_deadline, 'The deadline should be reset as this is a future task')
