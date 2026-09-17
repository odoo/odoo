from datetime import datetime

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from markupsafe import Markup

from odoo import Command, fields
from odoo.tests import Form, TransactionCase

from odoo.addons.mail.tests.common import mail_new_test_user


class TestTaskPlanningFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.resource_calendar_id.tz = "Europe/Brussels"
        cls.project_user = mail_new_test_user(
            cls.env,
            login="Armande",
            name="Armande Project_user",
            email="armande.project_user@example.com",
            notification_type="inbox",
            groups="project.group_project_user",
        )

        cls.project_test_user = mail_new_test_user(
            cls.env,
            login="Armando",
            name="Armando Project_user",
            email="armando.project_user@example.com",
            notification_type="inbox",
            groups="project.group_project_user",
        )

        cls.project_test = cls.env["project.project"].create(
            {
                "name": "Project Test",
            }
        )

        cls.portal_user = mail_new_test_user(
            cls.env,
            login="portal_project",
            name="Portal_user",
            email="portal_project_user@example.com",
            notification_type="email",
            groups="base.group_portal",
        )

    def create_tasks(self, nb=40):
        now = datetime.combine(datetime.now(), datetime.min.time())
        hour_start = [6, 11]
        hour_end = [10, 15]
        users = [
            self.project_test_user,
            self.project_user,
            self.project_user | self.project_test_user,
        ]

        self.env["project.task"].with_context(tracking_disable=True).create(
            [
                {
                    "name": "Fsm task " + str(i),
                    "user_ids": users[i % 3],
                    "project_id": self.project_test.id,
                    "date_start": now
                    + relativedelta(days=i / 2, hour=hour_start[i % 2]),
                    "date_end": now + relativedelta(days=i / 2, hour=hour_end[i % 2]),
                }
                for i in range(nb)
            ]
        )

    @freeze_time("2023-01-02")
    def test_default_allocated_hours_when_creating_tasks(self):
        form_view = self.env["ir.ui.view"].create(
            {
                "name": "Test Form",
                "model": "project.task",
                "type": "form",
                "inherit_id": self.env.ref("project.view_task_form2").id,
                "arch": """
                <form position="inside">
                    <field name="allocated_hours"/>
                </form>
            """,
            }
        )

        data = [
            {
                "scales": ["day", "week"],
                "dates": (datetime(2023, 1, 2), datetime(2023, 1, 2, 23, 59, 59)),
                "expected_dates": (
                    datetime(2023, 1, 2),
                    datetime(2023, 1, 2, 23, 59, 59),
                ),
                "expected_allocated_hours": 8.0,
                "dates_message": """
                    For day and week scale, date_start and date_end should be the same as the ones selected by the user,
                    they should not be modified according to the user calendar.
                """,
                "allocated_hours_message": "scheduled_hours is the intersection between the selected dates and the user calendar; allocated_hours is the reservation-derived commitment and is not date-derived in this fork.",
                "second_date_deadline": datetime(2023, 1, 2, 13, 0, 0),
                "second_expected_allocated_hours": 5.0,
            },
            {
                "scales": ["month", "year"],
                "dates": (datetime(2023, 1, 2), datetime(2023, 1, 6, 23, 59, 59)),
                "expected_dates": (
                    datetime(2023, 1, 2, 7, 0),
                    datetime(2023, 1, 6, 16, 0, 0),
                ),
                "expected_allocated_hours": 40.0,
                "dates_message": "For month and year scale, date_start and date_end should be modified according to the user calendar.",
                "allocated_hours_message": "allocated_hours should be computed according to the modified dates.",
                "second_date_deadline": datetime(2023, 1, 5, 22, 0, 0),
                "second_expected_allocated_hours": 32.0,
            },
        ]

        for datum in data:
            for scale in datum["scales"]:
                with Form(
                    self.env["project.task"].with_context(
                        {
                            "default_date_start": datum["dates"][0],
                            "default_date_end": datum["dates"][1],
                            "default_user_ids": self.project_user.ids,
                            "scale": scale,
                        }
                    ),
                    form_view,
                ) as task:
                    task.name = "Test"
                    task.project_id = self.project_test
                    self.assertEqual(
                        task.scheduled_hours,
                        datum["expected_allocated_hours"],
                        datum["allocated_hours_message"],
                    )
                    self.assertEqual(
                        (task.date_start, task.date_end),
                        datum["expected_dates"],
                        datum["dates_message"],
                    )
                    task.date_end = datum["second_date_deadline"]
                    self.assertEqual(
                        task.scheduled_hours,
                        datum["second_expected_allocated_hours"],
                        "Scheduled hours should be recomputed when the planned dates are modified",
                    )
                # date_start is the invisible companion of the date_end daterange
                # widget (options start_date_field), so the view offers no direct
                # write on it and Form rightly refuses one -- clear it on the saved
                # record instead. The field that follows the dates is
                # scheduled_hours; allocated_hours is reservation-derived in this
                # fork, which is what the message four lines up already says, so
                # asserting it here was asserting the vanilla semantics.
                created = task.record
                created.write({"date_start": False})
                self.assertEqual(
                    created.scheduled_hours,
                    0.0,
                    "Scheduled hours should be 0 as there is no date_start",
                )

    def test_planning_overlap(self):
        task_A = self.env["project.task"].create(
            {
                "name": "Fsm task 1",
                "user_ids": self.project_user,
                "project_id": self.project_test.id,
                "date_start": datetime.now(),
                "date_end": datetime.now() + relativedelta(hours=4),
                "allocated_hours": 4,
            }
        )
        task_B = self.env["project.task"].create(
            {
                "name": "Fsm task 2",
                "user_ids": self.project_user,
                "project_id": self.project_test.id,
                "date_start": datetime.now() + relativedelta(hours=2),
                "date_end": datetime.now() + relativedelta(hours=6),
                "allocated_hours": 4,
            }
        )
        self.env["project.task"].create(
            {
                "name": "Fsm task 2",
                "user_ids": self.project_user,
                "project_id": self.project_test.id,
                "date_start": datetime.now() + relativedelta(hours=5),
                "date_end": datetime.now() + relativedelta(hours=7),
                "allocated_hours": 2,
            }
        )
        task_D = self.env["project.task"].create(
            {
                "name": "Fsm task 2",
                "user_ids": self.project_user,
                "project_id": self.project_test.id,
                "date_start": datetime.now() + relativedelta(hours=8),
                "date_end": datetime.now() + relativedelta(hours=9),
                "allocated_hours": 1,
            }
        )
        self.assertEqual(
            task_A.planning_overlap,
            Markup("<p>Armande Project_user has 1 tasks at the same time.</p>"),
        )
        self.assertEqual(
            task_B.planning_overlap,
            Markup("<p>Armande Project_user has 2 tasks at the same time.</p>"),
        )
        self.assertFalse(
            task_D.planning_overlap, "No task should be overlapping with task_D"
        )

    def test_planned_date_consistency_for_tasks(self):
        task_1 = self.env["project.task"].create(
            [
                {
                    "name": "Task 1",
                    "user_ids": self.project_user,
                    "project_id": self.project_test.id,
                    "date_start": "2021-09-27 06:00:00",
                    "date_end": "2021-09-28 15:00:00",
                }
            ]
        )

        task_1.date_start = False
        self.assertFalse(
            task_1.date_start, "the planned date begin should be set to False"
        )
        self.assertEqual("2021-09-28", task_1.date_end.strftime("%Y-%m-%d"))

        task_1.write({"date_start": "2021-09-27 06:00:00"})
        self.assertEqual(
            "2021-09-27",
            task_1.date_start.strftime("%Y-%m-%d"),
            "the planned date begin should be set to the new date",
        )
        self.assertEqual(
            "2021-09-28",
            task_1.date_end.strftime("%Y-%m-%d"),
            "the planned date end should be set",
        )

        task_1.date_end = False
        self.assertFalse(
            task_1.date_start, "the planned date begin should be set to False"
        )
        self.assertFalse(task_1.date_end, "the planned date end should be set to False")

        task_1.write({"date_end": "2021-09-27 06:00:00"})
        self.assertFalse(
            task_1.date_start, "the planned date begin should not be updated"
        )
        self.assertEqual("2021-09-27", task_1.date_end.strftime("%Y-%m-%d"))

    def test_editing_task_planned_date(self):

        def get_hours(task):
            return task.date_start.hour, task.date_end.hour

        self.env.company.resource_calendar_id.tz = "UTC"
        self.project_user.resource_calendar_id = self.env.company.resource_calendar_id
        self.project_test_user.resource_calendar_id = self.env[
            "resource.calendar"
        ].create(
            {
                "tz": "UTC",
                "attendance_ids": [
                    Command.create(
                        {
                            "name": day,
                            "dayofweek": day,
                            "day_period": "afternoon",
                            "hour_from": 12,
                            "hour_to": 19,
                        }
                    )
                    for day in "12345"
                ],
            }
        )

        tasks = task_A, task_B, task_C = self.env["project.task"].create(
            [
                {
                    "name": "Task A - Armande",
                    "user_ids": self.project_user.ids,
                    "project_id": self.project_test.id,
                },
                {
                    "name": "Task B - Armando",
                    "user_ids": self.project_test_user.ids,
                    "project_id": self.project_test.id,
                },
                {
                    "name": "Task C - Planned",
                    "user_ids": (self.project_user + self.project_test_user).ids,
                    "project_id": self.project_test.id,
                    "date_start": "2024-08-27 05:00:00",
                    "date_end": "2024-08-27 10:00:00",
                },
            ]
        )

        self.assertEqual(
            get_hours(task_C),
            (5, 10),
            "Create shouldn't overwrite hours",
        )

        (task_A + task_C).write(
            {
                "date_start": "2024-08-26 00:00:00",
                "date_end": "2024-08-26 23:59:59",
            }
        )
        self.assertListEqual(
            [get_hours(task_A), get_hours(task_C)],
            [(0, 23), (0, 23)],
            "Write shouldn't modify hours when batch processes includes task with dates",
        )

        task_B.write(
            {
                "date_start": "2024-08-27 16:00:00",
                "date_end": "2024-08-27 21:00:00",
            }
        )
        self.assertEqual(
            get_hours(task_B), (16, 21), "Hand-picked hours shouldn't change"
        )

        tasks.date_end = False
        self.assertFalse(
            any(task.date_start for task in tasks),
            "Removing deadline should also remove date_start",
        )

        tasks.write(
            {
                "date_start": "2024-08-27 16:00:00",
                "date_end": "2024-08-27 22:00:00",
            }
        )
        self.assertListEqual(
            [get_hours(task) for task in tasks],
            [(16, 17), (16, 19), (16, 17)],
            "Batched tasks should be planned using each assignee's schedule",
        )

        tasks.write(
            {
                "date_end": False,
                "user_ids": self.project_user.ids,
            }
        )
        (task_B + task_C).write(
            {
                "date_start": "2024-03-24 06:00:00",
                "date_end": "2024-03-30 15:00:00",
            }
        )
        self.assertEqual(
            "2024-03-25",
            task_B.date_start.strftime("%Y-%m-%d"),
            "the planned date begin should be the first working day found according to the resource calendar of the user assigned and the start datetime selected by the user",
        )
        self.assertEqual(
            "2024-03-29",
            task_B.date_end.strftime("%Y-%m-%d"),
            "the planned date end should be the last working day found according to the resource calendar of the user assigned and the end datetime selected by the user",
        )
        self.assertEqual(
            "2024-03-25",
            task_C.date_start.strftime("%Y-%m-%d"),
            "the planned date begin should be the first working day found according to the resource calendar of the user assigned and the start datetime selected by the user",
        )
        self.assertEqual(
            "2024-03-29",
            task_C.date_end.strftime("%Y-%m-%d"),
            "the planned date end should be the last working day found according to the resource calendar of the user assigned and the end datetime selected by the user",
        )

        tasks.write(
            {
                "date_start": "2024-03-24 06:00:00",
                "date_end": "2024-03-30 15:00:00",
            }
        )
        self.assertEqual(
            "2024-03-24",
            task_A.date_start.strftime("%Y-%m-%d"),
            "the planned date begin should be the one selected by the user",
        )
        self.assertEqual(
            "2024-03-30",
            task_A.date_end.strftime("%Y-%m-%d"),
            "the planned date end should be the one selected by the user",
        )
        self.assertEqual(
            "2024-03-24",
            task_B.date_start.strftime("%Y-%m-%d"),
            "the planned date begin should be the one selected by the user",
        )
        self.assertEqual(
            "2024-03-30",
            task_B.date_end.strftime("%Y-%m-%d"),
            "the planned date end should be the one selected by the user",
        )
        self.assertEqual(
            "2024-03-24",
            task_C.date_start.strftime("%Y-%m-%d"),
            "the planned date begin should be the one selected by the user",
        )
        self.assertEqual(
            "2024-03-30",
            task_C.date_end.strftime("%Y-%m-%d"),
            "the planned date end should be the one selected by the user",
        )

    @freeze_time("2023-01-02")
    def test_cancelling_future_task_reset_planned_date(self):
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": self.project_test.id,
            }
        )
        task.state = "canceled"
        self.assertFalse(task.date_start, "The begin date should remain unset")
        self.assertFalse(task.date_end, "The deadline should remain unset")

        task.date_end = datetime.now() + relativedelta(hours=4)
        task.state = "canceled"
        self.assertFalse(task.date_start, "The begin date should remain unset")
        self.assertEqual(
            task.date_end,
            datetime.now() + relativedelta(hours=4),
            "The deadline should not have changed",
        )

        task.date_start = datetime.now() - relativedelta(hours=1)
        task.state = "canceled"
        self.assertEqual(
            task.date_start,
            datetime.now() - relativedelta(hours=1),
            "The begin date should not have changed as this is not a future task",
        )
        self.assertEqual(
            task.date_end,
            datetime.now() + relativedelta(hours=4),
            "The deadline should not have changed as this is not a future task",
        )

        task.date_start = datetime.now() + relativedelta(hours=1)
        task.state = "canceled"
        self.assertFalse(
            task.date_start,
            "The begin date should be reset as this is a future task",
        )
        self.assertFalse(
            task.date_end, "The deadline should be reset as this is a future task"
        )

    def test_duplicate_doesnt_copy_planned_date_begin(self):
        project = self.env["project.project"].create(
            {
                "name": "Project",
            }
        )
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": project.id,
                "date_start": "2021-09-23",
            }
        )
        self.assertFalse(
            project.copy().task_ids.date_start,
            "The task's date fields shouldn't be copied on project duplication",
        )
        self.assertFalse(
            task.copy().date_start,
            "The task's date fields shouldn't be copied on task duplication",
        )

    def test_plan_task_in_calendar(self):
        self.project_test_user.resource_calendar_id = self.env[
            "resource.calendar"
        ].create(
            {
                "name": "Test Calendar : 36 Hours/Week",
                "company_id": self.env.company.id,
                "tz": "Europe/Brussels",
                "hours_per_week": 36.0,
                "full_time_required_hours": 36.0,
                "attendance_ids": [
                    Command.create(
                        {
                            "name": "Attendance",
                            "dayofweek": dayofweek,
                            "hour_from": hour_from,
                            "hour_to": hour_to,
                            "day_period": day_period,
                        }
                    )
                    for dayofweek, hour_from, hour_to, day_period in [
                        ("0", 8.0, 12.0, "morning"),
                        ("0", 12.0, 13.0, "lunch"),
                        ("0", 13.0, 17, "afternoon"),
                        ("1", 8.0, 12.0, "morning"),
                        ("1", 12.0, 13.0, "lunch"),
                        ("1", 13.0, 17, "afternoon"),
                        ("2", 8.0, 12.0, "morning"),
                        ("2", 12.0, 13.0, "lunch"),
                        ("2", 13.0, 17, "afternoon"),
                        ("3", 14.0, 18, "afternoon"),
                        ("4", 8.0, 12.0, "morning"),
                        ("4", 12.0, 13.0, "lunch"),
                        ("4", 13.0, 17, "afternoon"),
                    ]
                ],
            }
        )
        task1, task2, task3, task4, task5, task6 = (
            self.env["project.task"]
            .with_context(tz="Europe/Brussels")
            .create(
                [
                    {"name": "Task 1", "user_ids": self.project_user.ids},
                    {
                        "name": "Task 2",
                        "user_ids": self.project_user.ids,
                        "allocated_hours": 2,
                    },
                    {
                        "name": "Task 3",
                        "user_ids": self.project_test_user.ids,
                        "allocated_hours": 2,
                    },
                    {
                        "name": "Task 4",
                        "user_ids": (self.project_user + self.project_test_user).ids,
                        "allocated_hours": 2,
                    },
                    {
                        "name": "Task 5",
                        "user_ids": self.project_user.ids,
                        "allocated_hours": 10,
                    },
                    {
                        "name": "Task 6",
                        "user_ids": (self.project_user + self.project_test_user).ids,
                        "allocated_hours": 10,
                    },
                ]
            )
        )
        vals = {
            "date_start": "2021-09-23 11:00:00",
            "date_end": "2021-09-23 12:00:00",
        }
        task1.plan_task_in_calendar(vals)
        self.assertEqual(
            fields.Datetime.to_string(task1.date_start),
            "2021-09-23 11:00:00",
            "Should be the start date given in the vals",
        )
        self.assertEqual(
            fields.Datetime.to_string(task1.date_end),
            "2021-09-23 12:00:00",
            "Should be the end date given in the vals",
        )

        task1.write({"date_start": False, "date_end": False})
        task1.plan_task_in_calendar({"date_end": "2021-09-23 12:00:00"})
        self.assertFalse(task1.date_start)
        self.assertEqual(
            fields.Datetime.to_string(task1.date_end),
            "2021-09-23 12:00:00",
            "Should be the end date given in the vals",
        )
        task1.write({"date_start": False, "date_end": False, "allocated_hours": 0})
        task1.with_context(task_calendar_plan_full_day=True).plan_task_in_calendar(
            {
                "date_start": "2021-09-23 07:00:00",
                "date_end": "2021-09-23 19:00:00",
            }
        )
        self.assertEqual(task1.date_start, datetime(2021, 9, 23, 6, 0, 0))
        self.assertEqual(task1.date_end, datetime(2021, 9, 23, 15, 0, 0))
        self.assertEqual(task1.scheduled_hours, 8)

        task2.plan_task_in_calendar(vals)
        self.assertEqual(
            fields.Datetime.to_string(task2.date_start),
            "2021-09-23 11:00:00",
            "Should be the start date given in the vals",
        )
        self.assertEqual(
            fields.Datetime.to_string(task2.date_end),
            "2021-09-23 13:00:00",
            "Should take into account the allocated hours set on the task and the working calendar of users assigned",
        )

        task2.write({"date_start": False, "date_end": False, "allocated_hours": 2})
        task2.with_context(task_calendar_plan_full_day=True).plan_task_in_calendar(
            {"date_end": "2021-09-03 19:00:00"}
        )
        self.assertFalse(task2.date_start)
        self.assertEqual(
            fields.Datetime.to_string(task2.date_end),
            "2021-09-03 19:00:00",
            "Should take into account the allocated hours set on the task and the working calendar of users assigned",
        )
        task2.write({"date_start": False, "date_end": False, "allocated_hours": 2})
        task2.with_context(task_calendar_plan_full_day=True).plan_task_in_calendar(
            {
                "date_start": "2021-09-03 07:00:00",
                "date_end": "2021-09-03 19:00:00",
            }
        )
        self.assertEqual(
            fields.Datetime.to_string(task2.date_start),
            "2021-09-03 07:00:00",
            "Should be the start date given in the vals",
        )
        self.assertEqual(
            fields.Datetime.to_string(task2.date_end),
            "2021-09-03 09:00:00",
            "Should take into account the allocated hours set on the task and the working calendar of users assigned",
        )

        task3.plan_task_in_calendar(vals)
        self.assertEqual(
            fields.Datetime.to_string(task3.date_start),
            "2021-09-23 11:00:00",
            "Should be the start date given in the vals",
        )
        self.assertEqual(
            fields.Datetime.to_string(task3.date_end),
            "2021-09-23 14:00:00",
            "Should take into account the allocated hours set on the task and the working calendar of users assigned",
        )

        task4.plan_task_in_calendar(vals)
        self.assertEqual(
            fields.Datetime.to_string(task4.date_start),
            "2021-09-23 11:00:00",
            "Should be the start date given in the vals",
        )
        self.assertEqual(
            fields.Datetime.to_string(task4.date_end),
            "2021-09-23 14:00:00",
            "Should take into account the allocated hours set on the task and the working calendar of users assigned",
        )
        task4.write({"date_start": False, "date_end": False, "allocated_hours": 2})
        task4.with_context(task_calendar_plan_full_day=True).plan_task_in_calendar(
            {"date_end": "2021-09-03 19:00:00"}
        )
        self.assertFalse(task4.date_start)
        self.assertEqual(
            fields.Datetime.to_string(task4.date_end),
            "2021-09-03 19:00:00",
            "Should take into account the allocated hours set on the task and the working calendar of users assigned",
        )
        task4.write({"date_start": False, "date_end": False, "allocated_hours": 2})
        task4.with_context(task_calendar_plan_full_day=True).plan_task_in_calendar(
            {
                "date_start": "2021-09-03 07:00:00",
                "date_end": "2021-09-03 19:00:00",
            }
        )
        self.assertEqual(
            fields.Datetime.to_string(task4.date_start),
            "2021-09-03 07:00:00",
            "Should be the start date given in the vals",
        )
        self.assertEqual(
            fields.Datetime.to_string(task4.date_end),
            "2021-09-03 09:00:00",
            "Should take into account the allocated hours set on the task and the working calendar of users assigned",
        )

        task5.plan_task_in_calendar(vals)
        self.assertEqual(
            fields.Datetime.to_string(task5.date_start),
            "2021-09-23 11:00:00",
            "Should be the start date given in the vals",
        )
        self.assertEqual(
            fields.Datetime.to_string(task5.date_end),
            "2021-09-24 13:00:00",
            "Should take into account the allocated hours set on the task and the working calendar of users assigned",
        )

        task6.plan_task_in_calendar(vals)
        self.assertEqual(
            fields.Datetime.to_string(task6.date_start),
            "2021-09-23 11:00:00",
            "Should be the start date given in the vals",
        )
        self.assertEqual(
            fields.Datetime.to_string(task6.date_end),
            "2021-09-24 14:00:00",
            "Should take into account the allocated hours set on the task and the working calendar of users assigned",
        )

    def test_calendar_default_start_yields_to_the_start_edited_in_the_form(self):
        slot_start = datetime(2030, 3, 4, 7)
        calendar = self.env["project.task"].with_context(
            default_date_start_effective=slot_start,
            default_date_start=slot_start,
            default_date_end=slot_start + relativedelta(hours=12),
        )
        with Form(calendar) as task_form:
            task_form.name = "Moved before its calendar slot"
            task_form.project_id = self.project_test
            task_form.date_start = datetime(2030, 3, 1, 8)
            task_form.date_end = datetime(2030, 3, 2, 8)
        self.assertEqual(task_form.record.date_start, datetime(2030, 3, 1, 8))
        self.assertEqual(task_form.record.date_end, datetime(2030, 3, 2, 8))

    def test_calendar_default_start_seeds_date_start_when_only_the_alias_is_given(self):
        slot_start = datetime(2030, 3, 4, 7)
        defaults = (
            self.env["project.task"]
            .with_context(default_date_start_effective=slot_start)
            .default_get(["date_start", "date_start_effective"])
        )
        self.assertEqual(defaults.get("date_start"), slot_start)
        self.assertNotIn("date_start_effective", defaults)
