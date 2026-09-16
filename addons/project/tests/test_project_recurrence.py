from datetime import datetime, time, timedelta

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form, TransactionCase, users

from .test_project_base import TestProjectCommon
from odoo.addons.mail.tests.common import mail_new_test_user


class TestProjectRecurrence(TransactionCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        user_group_employee = cls.env.ref("base.group_user")
        user_group_project_user = cls.env.ref("project.group_project_user")
        user_group_project_recurring_task = cls.env.ref(
            "project.group_project_recurring_tasks"
        )
        Users = cls.env["res.users"].with_context({"no_reset_password": True})

        cls.env.user.group_ids += user_group_project_recurring_task
        cls.user_projectuser = Users.create(
            {
                "name": "Armande ProjectUser",
                "login": "armandel",
                "password": "armandel",
                "email": "armande.projectuser@example.com",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            user_group_employee.id,
                            user_group_project_user.id,
                            user_group_project_recurring_task.id,
                        ],
                    )
                ],
            }
        )

        cls.stage_a = cls.env["project.workflow.step"].create({"name": "a"})
        cls.stage_b = cls.env["project.workflow.step"].create({"name": "b"})
        cls.project_recurring = (
            cls.env["project.project"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "Recurring",
                    "workflow_step_ids": [
                        (4, cls.stage_a.id),
                        (4, cls.stage_b.id),
                    ],
                    "allow_recurring_tasks": True,
                }
            )
        )
        cls.user = cls.env["res.users"].create(
            {
                "name": "Recurring Project User",
                "login": "RPU",
                "email": "rp.u@example.com",
            }
        )

        cls.classPatch(cls.env.cr, "now", fields.Datetime.now)

        cls.date_01_01 = datetime.combine(
            datetime.now() + relativedelta(years=-1, month=1, day=1), time(0, 0)
        )

    def test_recurrence_simple(self) -> None:
        with freeze_time(self.date_01_01):
            form = Form(self.env["project.task"])
            form.name = "test recurring task"
            form.project_id = self.project_recurring
            form.recurring_task = True
            form.repeat_interval = 5
            form.repeat_unit = "month"
            form.repeat_type = "forever"
            task = form.save()

            self.assertTrue(bool(task.recurrence_id), "should create a recurrence")

            task.write({"repeat_interval": 2})
            self.assertEqual(
                task.recurrence_id.repeat_interval,
                2,
                "recurrence should be updated",
            )

            task.recurring_task = False
            self.assertFalse(
                bool(task.recurrence_id), "the recurrence should be deleted"
            )

    def test_recurrent_tasks_fields(self) -> None:
        self.env["project.tags"].create(
            {
                "name": "Test Tag",
            }
        )

        with freeze_time(self.date_01_01):
            form = Form(self.env["project.task"])
            form.project_id = self.project_recurring
            form.name = "name"
            form.description = "description"
            form.priority = "1"
            form.step_id = self.stage_b
            form.tag_ids.add(self.env["project.tags"].search([], limit=1))
            form.date_end = self.date_01_01 + relativedelta(weeks=1)

            form.recurring_task = True
            form.repeat_interval = 2
            form.repeat_unit = "month"
            form.repeat_type = "forever"
            task = form.save()
            # not through the form: a layer composing user_ids assigns through its
            # own fields, so the form need not show this one
            task.user_ids = self.user

        with freeze_time(self.date_01_01 + relativedelta(months=1)):
            task.state = "done"
        other_task = task.recurrence_id.task_ids - task

        self.assertEqual(
            other_task.date_end,
            task.date_end + relativedelta(months=2),
            "Next occurrence should have previous deadline + interval * unit",
        )
        for copied_field in [
            "project_id",
            "name",
            "description",
            "tag_ids",
            "user_ids",
        ]:
            self.assertEqual(
                other_task[copied_field],
                task[copied_field],
                f"Next occurrence's {copied_field} should have been copied",
            )

        for reset_field in ["priority", "step_id", "state"]:
            self.assertNotEqual(
                other_task[reset_field],
                task[reset_field],
                f"Next occurrence's {reset_field} should have been reset",
            )

    def test_recurrence_until(self) -> None:
        with freeze_time(self.date_01_01):
            form = Form(self.env["project.task"])
            form.name = "test recurring task"
            form.project_id = self.project_recurring
            form.recurring_task = True
            form.repeat_interval = 1
            form.repeat_unit = "month"
            form.repeat_type = "until"
            form.repeat_until = self.date_01_01 + relativedelta(months=1, days=1)
            form.date_end = self.date_01_01
            task = form.save()

        with freeze_time(self.date_01_01 + relativedelta(days=30)):
            task.state = "done"
        self.assertEqual(
            len(task.recurrence_id.task_ids),
            2,
            "Since this is before repeat_until, next occurrence should have been created",
        )

        last_recurring_task = task.recurrence_id.task_ids.filtered(lambda t: t != task)
        with freeze_time(self.date_01_01 + relativedelta(days=32)):
            last_recurring_task.state = "done"
        self.assertEqual(
            len(task.recurrence_id.task_ids),
            2,
            "Since this is after repeat_until, next occurrence shouldn't have been created",
        )

    def test_recurring_settings_change(self) -> None:
        test_task = self.env["project.task"].create(
            {
                "name": "Recurring Task",
                "project_id": self.project_recurring.id,
                "recurring_task": True,
            }
        )
        self.assertTrue(
            test_task.recurring_task,
            'The "Recurring" feature of the task should be enabled.',
        )
        self.project_recurring.allow_recurring_tasks = False
        self.assertFalse(
            test_task.recurring_task,
            'The "Recurring" feature of the task should be disabled when the project is not recurring anymore.',
        )

    def test_disabling_recurrence(self) -> None:
        with freeze_time(self.date_01_01):
            form = Form(self.env["project.task"])
            form.name = "test recurring task"
            form.project_id = self.project_recurring
            form.recurring_task = True
            form.repeat_interval = 5
            form.repeat_unit = "day"
            form.repeat_type = "forever"
            task = form.save()

        with freeze_time(self.date_01_01 + relativedelta(day=1)):
            task.state = "done"
            other_task = self.project_recurring.task_ids - task

        with freeze_time(self.date_01_01 + relativedelta(day=2)):
            other_task.state = "done"

        task_c, task_b, task_a = self.env["project.task"].search(
            [("project_id", "=", self.project_recurring.id)]
        )

        task_b.recurring_task = False

        self.assertFalse(
            any((task_a + task_b + task_c).mapped("recurring_task")),
            "All tasks in the recurrence should have their recurrence disabled",
        )

    @users("armandel")
    def test_closed_recurring_task(self) -> None:
        form = Form(self.env["project.task"])
        form.name = "test recurring task"
        form.project_id = self.project_recurring
        form.recurring_task = True
        form.repeat_interval = 1
        form.repeat_unit = "day"
        form.repeat_type = "forever"
        task = form.save()

        self.assertEqual(
            len(task.recurrence_id.task_ids),
            1,
            "recurrence should have a single task",
        )
        task.state = "done"
        self.assertEqual(
            len(task.recurrence_id.task_ids),
            2,
            "a new occurrence should have been created",
        )

    def test_recurrence_copy_task_dependency(self) -> None:
        self.project_recurring.allow_dependencies = True
        parent_task = (
            self.env["project.task"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "Recurring Parent Task",
                    "project_id": self.project_recurring.id,
                    "recurring_task": True,
                    "repeat_interval": 2,
                    "repeat_unit": "month",
                    "repeat_type": "forever",
                    "child_ids": [
                        Command.create(
                            {
                                "name": "Node 1",
                                "project_id": self.project_recurring.id,
                            }
                        ),
                        Command.create(
                            {
                                "name": "SuperNode 2",
                                "project_id": self.project_recurring.id,
                                "child_ids": [
                                    Command.create(
                                        {
                                            "name": "Node 2",
                                            "project_id": self.project_recurring.id,
                                        }
                                    )
                                ],
                            }
                        ),
                        Command.create(
                            {
                                "name": "Node 3",
                                "project_id": self.project_recurring.id,
                            }
                        ),
                    ],
                }
            )
        )

        side_task1, side_task2 = (
            self.env["project.task"]
            .with_context({"mail_create_nolog": True})
            .create(
                [
                    {
                        "name": f"Side Task {i + 1}",
                        "project_id": self.project_recurring.id,
                    }
                    for i in range(2)
                ]
            )
        )

        node1 = parent_task.child_ids.filtered(lambda t: t.name == "Node 1")
        node2 = parent_task.child_ids.filtered(
            lambda t: t.name == "SuperNode 2"
        ).child_ids
        node3 = parent_task.child_ids.filtered(lambda t: t.name == "Node 3")

        node1.successor_ids = node2
        node2.successor_ids = node3
        side_task1.successor_ids = node2
        node3.successor_ids = side_task2

        parent_task.state = "done"
        parent_task_copy = self.env["project.task"].browse(
            parent_task.recurrence_id._get_last_task_id_per_recurrence_id().get(
                parent_task.recurrence_id.id
            )
        )
        self.assertNotEqual(
            parent_task.id,
            parent_task_copy.id,
            "The generated recurring task should be different than the original one",
        )

        parent_copy_node1 = parent_task_copy.child_ids.filtered(
            lambda t: t.name.startswith("Node 1")
        )
        parent_copy_node2 = parent_task_copy.child_ids.filtered(
            lambda t: t.name.startswith("SuperNode 2")
        ).child_ids
        parent_copy_node3 = parent_task_copy.child_ids.filtered(
            lambda t: t.name.startswith("Node 3")
        )

        self.assertNotEqual(
            node1.id,
            parent_copy_node1.id,
            "The original and copied node1 should be different",
        )
        self.assertNotEqual(
            node2.id,
            parent_copy_node2.id,
            "The original and copied node2 should be different",
        )
        self.assertNotEqual(
            node3.id,
            parent_copy_node3.id,
            "The original and copied node3 should be different",
        )

        self.assertNotEqual(
            node1.successor_ids.ids,
            parent_copy_node1.successor_ids.ids,
            "The dependencies of the original and copied node1 should be different",
        )
        self.assertEqual(
            node1.predecessor_ids.ids,
            parent_copy_node1.predecessor_ids.ids,
            "The dependencies of the original and copied node1 should be different",
        )
        self.assertNotEqual(
            node2.successor_ids.ids,
            parent_copy_node2.successor_ids.ids,
            "The dependencies of the original and copied node2 should be different",
        )
        self.assertNotEqual(
            node2.predecessor_ids.ids,
            parent_copy_node2.predecessor_ids.ids,
            "The dependencies of the original and copied node2 should be different",
        )
        self.assertEqual(
            node3.successor_ids.ids,
            parent_copy_node3.successor_ids.ids,
            "The dependencies of the original and copied node3 should be different",
        )
        self.assertNotEqual(
            node3.predecessor_ids.ids,
            parent_copy_node3.predecessor_ids.ids,
            "The dependencies of the original and copied node3 should be different",
        )

        self.assertEqual(
            parent_copy_node1.successor_ids.ids,
            parent_copy_node2.ids,
            "Node1copy - Node2copy relation should be present",
        )
        self.assertEqual(
            parent_copy_node2.successor_ids.ids,
            parent_copy_node3.ids,
            "Node2copy - Node3copy relation should be present",
        )
        self.assertEqual(
            parent_copy_node3.successor_ids.ids,
            side_task2.ids,
            "Node3 - SideTask2 relation should be present",
        )

        self.assertEqual(len(parent_copy_node1.predecessor_ids), 0)
        self.assertCountEqual(
            parent_copy_node2.predecessor_ids.ids,
            [parent_copy_node1.id, side_task1.id],
            "Node2copy - Node1copy and Node2copy - SideTask1 relations should be present",
        )
        self.assertEqual(
            parent_copy_node3.predecessor_ids.ids,
            parent_copy_node2.ids,
            "Node3copy - Node2copy relation should be present",
        )

        self.assertEqual(
            node1.successor_ids.ids,
            node2.ids,
            "Node1 - Node2 relation should be present",
        )
        self.assertEqual(
            node2.successor_ids.ids,
            node3.ids,
            "Node2 - Node3 relation should be present",
        )
        self.assertEqual(
            node3.successor_ids.ids,
            side_task2.ids,
            "Node3 - SideTask2 relation should be present",
        )

        self.assertEqual(len(node1.predecessor_ids), 0)
        self.assertCountEqual(
            node2.predecessor_ids.ids,
            [node1.id, side_task1.id],
            "Node2 - Node1 and Node2 - SideTask1 relations should be present",
        )
        self.assertEqual(
            node3.predecessor_ids.ids,
            node2.ids,
            "Node3 - Node2 relation should be present",
        )

        self.assertCountEqual(
            side_task1.successor_ids.ids,
            [node2.id, parent_copy_node2.id],
            "SideTask1 - Node2 and SideTask1 - Node2copy relations should be present",
        )
        self.assertEqual(len(side_task2.successor_ids), 0)

        self.assertEqual(len(side_task1.predecessor_ids), 0)
        self.assertCountEqual(
            side_task2.predecessor_ids.ids,
            [node3.id, parent_copy_node3.id],
            "SideTask2 - Node3 and SideTask2 - Node3copy relations should be present",
        )

    def test_next_occurrence_batch_call(self) -> None:
        tasks = (
            self.env["project.task"]
            .with_context({"mail_create_nolog": True})
            .create(
                [
                    {
                        "name": "Recurring Task 1",
                        "project_id": self.project_recurring.id,
                        "recurring_task": True,
                        "repeat_unit": "week",
                        "repeat_type": "forever",
                        "date_end": "2023-01-01 00:00:00",
                        "child_ids": [
                            Command.create(
                                {
                                    "name": "R1 Sub Task 1",
                                    "project_id": self.project_recurring.id,
                                    "date_end": "2023-01-02 00:00:00",
                                    "child_ids": [
                                        Command.create(
                                            {
                                                "name": "R1 Sub Task 2",
                                                "project_id": self.project_recurring.id,
                                                "date_end": "2023-01-03 00:00:00",
                                            }
                                        )
                                    ],
                                }
                            ),
                        ],
                    },
                    {
                        "name": "Recurring Task 2",
                        "project_id": self.project_recurring.id,
                        "recurring_task": True,
                        "repeat_unit": "week",
                        "repeat_type": "forever",
                        "date_end": "2023-01-04 00:00:00",
                        "child_ids": [
                            Command.create(
                                {
                                    "name": "R2 Sub Task",
                                    "project_id": self.project_recurring.id,
                                    "date_end": "2023-01-05 00:00:00",
                                }
                            ),
                        ],
                    },
                ]
            )
        )
        tasks_copy = self.env["project.task.recurrence"]._create_next_occurrences(tasks)
        self.assertEqual(datetime(2023, 1, 8, 0, 0), tasks_copy[0].date_end)
        self.assertEqual(datetime(2023, 1, 9, 0, 0), tasks_copy[0].child_ids.date_end)
        self.assertEqual(
            datetime(2023, 1, 10, 0, 0),
            tasks_copy[0].child_ids.child_ids.date_end,
        )
        self.assertEqual(datetime(2023, 1, 11, 0, 0), tasks_copy[1].date_end)
        self.assertEqual(datetime(2023, 1, 12, 0, 0), tasks_copy[1].child_ids.date_end)

    def test_recurrent_tasks_without_archive_user(self) -> None:
        task = self.env["project.task"].create(
            {
                "project_id": self.project_recurring.id,
                "name": "Test task",
                "step_id": self.stage_b.id,
                "user_ids": [Command.set([self.user.id, self.user_projectuser.id])],
                "recurring_task": True,
                "repeat_type": "forever",
            }
        )
        self.user_projectuser.action_archive()
        task.write({"state": "done"})
        self.assertEqual((task.recurrence_id.task_ids - task).user_ids, self.user)

    def test_recurrent_sub_tasks_without_archive_user(self) -> None:
        parent_task = self.env["project.task"].create(
            {
                "project_id": self.project_recurring.id,
                "name": "Task A",
                "step_id": self.stage_b.id,
                "recurring_task": True,
                "repeat_type": "forever",
                "child_ids": [
                    Command.create(
                        {
                            "project_id": self.project_recurring.id,
                            "name": "Sub task A",
                            "step_id": self.stage_b.id,
                            "user_ids": [
                                Command.set([self.user.id, self.user_projectuser.id])
                            ],
                        }
                    )
                ],
            }
        )
        self.user_projectuser.action_archive()
        parent_task.write({"state": "done"})
        self.assertEqual(
            (parent_task.recurrence_id.task_ids - parent_task).child_ids.user_ids,
            self.user,
        )

    def test_close_recurring_task_private_project(self) -> None:
        employee = self.env["res.users"].create(
            {
                "name": "Employee",
                "login": "employee",
                "email": "employee@odoo.com",
                "group_ids": [(6, 0, [self.env.ref("project.group_project_user").id])],
            }
        )
        private_project = self.env["project.project"].create(
            {
                "name": "Private Project",
                "privacy_visibility": "followers",
            }
        )
        task = self.env["project.task"].create(
            {
                "name": "Parent Task",
                "project_id": private_project.id,
                "user_ids": [(4, employee.id)],
                "recurring_task": True,
                "repeat_type": "forever",
                "state": "in_progress",
            }
        )

        self.env.invalidate_all()
        task.with_user(employee).write({"state": "done"})
        self.assertEqual(
            task.state,
            "done",
            "The employee should be able to mark the task as done.",
        )


class TestRecurrenceDefaults(TestProjectCommon):
    def test_context_default_repeat_until_wins(self) -> None:
        vals = (
            self.env["project.task"]
            .with_context(default_repeat_until="2030-01-01")
            .default_get(["repeat_until"])
        )
        self.assertEqual(str(vals["repeat_until"]), "2030-01-01")

    def test_recurrence_until_requires_valid_future_date(self) -> None:
        Recurrence = self.env["project.task.recurrence"]
        with self.assertRaises(ValidationError):
            Recurrence.create({"repeat_type": "until"})
        today = fields.Date.today()
        with self.assertRaises(ValidationError):
            Recurrence.create(
                {
                    "repeat_type": "until",
                    "repeat_until": today - timedelta(days=1),
                }
            )
        rec = Recurrence.create(
            {
                "repeat_type": "until",
                "repeat_until": today + timedelta(days=30),
            }
        )
        self.assertTrue(rec)

    def test_recurrence_until_respects_user_timezone(self) -> None:
        self.env.user.tz = "Etc/GMT+6"
        step = self.env["project.workflow.step"].create(
            {"name": "S", "project_ids": [(4, self.project_pigs.id)]}
        )
        until = fields.Date.today() + timedelta(days=30)
        rec = self.env["project.task.recurrence"].create(
            {
                "repeat_type": "until",
                "repeat_unit": "day",
                "repeat_interval": 1,
                "repeat_until": until,
            }
        )
        task = self.env["project.task"].create(
            {
                "name": "Recur",
                "project_id": self.project_pigs.id,
                "step_id": step.id,
                "recurrence_id": rec.id,
                "date_end": datetime.combine(until, time(3, 0)),
            }
        )
        created = self.env["project.task.recurrence"]._create_next_occurrences(task)
        self.assertTrue(
            created,
            "boundary occurrence must be created (compared in user tz, not UTC)",
        )


class TestRecurrenceSeriesDates(TestProjectCommon):
    def setUp(self) -> None:
        super().setUp()
        self.env = self.env(context=dict(self.env.context, tz="UTC"))
        self.Recurrence = self.env["project.task.recurrence"]
        step = self.env["project.workflow.step"].create(
            {"name": "S", "project_ids": [Command.link(self.project_pigs.id)]}
        )
        self.recurrence = self.Recurrence.create(
            {"repeat_interval": 1, "repeat_unit": "month", "repeat_type": "forever"}
        )
        self.task = self.env["project.task"].create(
            {
                "name": "Month end",
                "project_id": self.project_pigs.id,
                "step_id": step.id,
                "recurrence_id": self.recurrence.id,
                "recurring_task": True,
                "date_start": datetime(2030, 1, 30, 10, 0),
                "date_end": datetime(2030, 1, 31, 10, 0),
            }
        )

    def test_a_month_end_series_returns_to_the_month_end(self) -> None:
        february = self.Recurrence._create_next_occurrences(self.task)
        self.assertRecordValues(
            february,
            [
                {
                    "date_start": datetime(2030, 2, 27, 10, 0),
                    "date_end": datetime(2030, 2, 28, 10, 0),
                }
            ],
        )
        march = self.Recurrence._create_next_occurrences(february)
        self.assertRecordValues(
            march,
            [
                {
                    "date_start": datetime(2030, 3, 30, 10, 0),
                    "date_end": datetime(2030, 3, 31, 10, 0),
                }
            ],
        )

    def test_a_series_counts_from_the_field_it_was_anchored_on(self) -> None:
        self.task.date_end = False
        self.task.date_start = datetime(2030, 1, 10, 10, 0)
        february = self.Recurrence._create_next_occurrences(self.task)
        self.assertEqual(february.date_start, datetime(2030, 2, 10, 10, 0))
        february.date_end = datetime(2030, 2, 28, 10, 0)
        march = self.Recurrence._create_next_occurrences(february)
        self.assertEqual(march.date_end, datetime(2030, 3, 28, 10, 0))

    def test_the_dates_do_not_depend_on_the_closer_timezone(self) -> None:
        self.task.company_id.partner_id.tz = "UTC"
        self.task.date_end = datetime(2030, 1, 30, 20, 0)
        task = self.task.with_context(tz="Asia/Tokyo")
        february = self.Recurrence.with_context(
            tz="Asia/Tokyo"
        )._create_next_occurrences(task)
        self.assertEqual(february.date_end, datetime(2030, 2, 28, 20, 0))

    def test_rescheduling_one_occurrence_keeps_the_series_on_its_dates(self) -> None:
        february = self.Recurrence._create_next_occurrences(self.task)
        february.write(
            {
                "date_start": datetime(2030, 3, 2, 10, 0),
                "date_end": datetime(2030, 3, 3, 10, 0),
            }
        )
        march = self.Recurrence._create_next_occurrences(february)
        self.assertEqual(march.date_end, datetime(2030, 3, 31, 10, 0))

    def test_changing_the_rule_starts_the_series_again_from_that_occurrence(
        self,
    ) -> None:
        february = self.Recurrence._create_next_occurrences(self.task)
        february.write({"repeat_interval": 2, "recurrence_update": "all"})
        april = self.Recurrence._create_next_occurrences(february)
        self.assertEqual(april.date_end, datetime(2030, 4, 28, 10, 0))

    def test_shifting_the_series_moves_its_dates(self) -> None:
        february = self.Recurrence._create_next_occurrences(self.task)
        february.write(
            {
                "date_end": datetime(2030, 3, 2, 10, 0),
                "recurrence_update": "subsequent",
            }
        )
        march = self.Recurrence._create_next_occurrences(february)
        self.assertEqual(march.date_end, datetime(2030, 4, 2, 10, 0))


class TestRecurrenceUpdateScope(TestProjectCommon):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.step = cls.env["project.workflow.step"].create(
            {"name": "S", "project_ids": [Command.link(cls.project_pigs.id)]}
        )
        cls.recurrence = cls.env["project.task.recurrence"].create(
            {"repeat_interval": 1, "repeat_unit": "week", "repeat_type": "forever"}
        )
        cls.first, cls.second, cls.third = cls.env["project.task"].create(
            [
                {
                    "name": "Occurrence",
                    "project_id": cls.project_pigs.id,
                    "step_id": cls.step.id,
                    "recurrence_id": cls.recurrence.id,
                    "recurring_task": True,
                    "date_end": datetime(2035, 3, 1, 12, 0) + timedelta(weeks=i),
                }
                for i in range(3)
            ]
        )

    def test_this_touches_only_the_edited_task(self) -> None:
        self.second.write({"name": "Renamed", "recurrence_update": "this"})
        self.assertEqual(self.second.name, "Renamed")
        self.assertEqual(self.first.name, "Occurrence")
        self.assertEqual(self.third.name, "Occurrence")

    def test_this_is_the_default_when_the_key_is_absent(self) -> None:
        self.second.write({"name": "Renamed"})
        self.assertEqual(self.first.name, "Occurrence")
        self.assertEqual(self.third.name, "Occurrence")

    def test_subsequent_reaches_this_task_and_the_later_ones(self) -> None:
        self.second.write({"name": "Renamed", "recurrence_update": "subsequent"})
        self.assertEqual(
            self.first.name, "Occurrence", "an earlier occurrence must be left alone"
        )
        self.assertEqual(self.second.name, "Renamed")
        self.assertEqual(self.third.name, "Renamed")

    def test_all_reaches_every_occurrence(self) -> None:
        self.second.write({"name": "Renamed", "recurrence_update": "all"})
        self.assertEqual(self.first.name, "Renamed")
        self.assertEqual(self.second.name, "Renamed")
        self.assertEqual(self.third.name, "Renamed")

    def test_a_deadline_shifts_the_series_instead_of_flattening_it(self) -> None:
        original = {task: task.date_end for task in (self.first, self.third)}
        self.second.write(
            {
                "date_end": self.second.date_end + timedelta(days=2),
                "recurrence_update": "subsequent",
            }
        )
        self.assertEqual(
            self.first.date_end, original[self.first], "earlier occurrence unmoved"
        )
        self.assertEqual(
            self.third.date_end,
            original[self.third] + timedelta(days=2),
            "a later occurrence moves by the same delta, keeping the spacing",
        )

    def test_an_undated_occurrence_is_not_shifted(self) -> None:
        self.third.date_end = False
        self.second.write(
            {
                "date_end": self.second.date_end + timedelta(days=2),
                "recurrence_update": "all",
            }
        )
        self.assertFalse(
            self.third.date_end, "nothing to shift, and nothing invented either"
        )

    def test_changing_the_rule_for_part_of_the_series_is_refused(self) -> None:
        with self.assertRaises(UserError):
            self.second.write({"repeat_interval": 3, "recurrence_update": "subsequent"})
        self.assertEqual(self.recurrence.repeat_interval, 1)

    def test_changing_the_rule_for_all_is_allowed(self) -> None:
        self.second.write({"repeat_interval": 3, "recurrence_update": "all"})
        self.assertEqual(self.recurrence.repeat_interval, 3)

    def test_scope_needs_a_single_task(self) -> None:
        with self.assertRaises(ValueError):
            (self.first | self.third).write(
                {"name": "Renamed", "recurrence_update": "all"}
            )

    def test_create_tolerates_the_scope_key(self) -> None:
        task = self.env["project.task"].create(
            {
                "name": "Fresh",
                "project_id": self.project_pigs.id,
                "recurrence_update": "all",
            }
        )
        self.assertEqual(task.name, "Fresh")

    def test_a_portal_user_may_not_scope_an_edit(self) -> None:
        portal = mail_new_test_user(
            self.env, "recurrence_portal", groups="base.group_portal"
        )
        self.project_pigs.privacy_visibility = "portal"
        self.project_pigs.message_subscribe(partner_ids=[portal.partner_id.id])
        with self.assertRaises(AccessError):
            self.second.with_user(portal).write(
                {"name": "Renamed", "recurrence_update": "all"}
            )

    def test_a_task_outside_any_recurrence_ignores_the_scope(self) -> None:
        loner = self.env["project.task"].create(
            {"name": "Alone", "project_id": self.project_pigs.id}
        )
        loner.write({"name": "Still alone", "recurrence_update": "all"})
        self.assertEqual(loner.name, "Still alone")
