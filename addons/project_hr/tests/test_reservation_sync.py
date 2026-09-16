from datetime import datetime

from psycopg import IntegrityError

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestReservationSync(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_home = cls.env["res.company"].create(
            {"name": "Home Co", "resource_calendar_id": False}
        )
        cls.company_foreign = cls.env["res.company"].create(
            {"name": "Foreign Co", "resource_calendar_id": False}
        )
        std_attendance = [
            (
                0,
                0,
                {
                    "name": "Morning",
                    "dayofweek": str(d),
                    "hour_from": 8,
                    "hour_to": 12,
                    "day_period": "morning",
                },
            )
            for d in range(5)
        ] + [
            (
                0,
                0,
                {
                    "name": "Afternoon",
                    "dayofweek": str(d),
                    "hour_from": 13,
                    "hour_to": 17,
                    "day_period": "afternoon",
                },
            )
            for d in range(5)
        ]
        home_cal = cls.env["resource.calendar"].create(
            {
                "name": "Home 40h",
                "tz": "UTC",
                "company_id": cls.company_home.id,
                "attendance_ids": std_attendance,
            }
        )
        foreign_cal = cls.env["resource.calendar"].create(
            {
                "name": "Foreign 40h",
                "tz": "UTC",
                "company_id": cls.company_foreign.id,
                "attendance_ids": std_attendance,
            }
        )
        cls.company_home.resource_calendar_id = home_cal
        cls.company_foreign.resource_calendar_id = foreign_cal

        cls.user_with_resource = cls.env["res.users"].create(
            {
                "name": "Home Worker",
                "login": "home.worker@test",
                "tz": "UTC",
                "company_id": cls.company_home.id,
                "company_ids": [
                    Command.set([cls.company_home.id, cls.company_foreign.id])
                ],
                "group_ids": [
                    Command.link(cls.env.ref("base.group_user").id),
                    Command.link(cls.env.ref("project.group_project_user").id),
                ],
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Home Worker",
                "user_id": cls.user_with_resource.id,
                "company_id": cls.company_home.id,
                "tz": "UTC",
            }
        )

        cls.project = cls.env["project.project"].create(
            {"name": "Test Project", "company_id": cls.company_home.id}
        )
        cls.scheduled_vals = {
            "date_start": datetime(2026, 5, 4, 8, 0),
            "date_end": datetime(2026, 5, 4, 17, 0),
        }

    def test_create_with_assignee_generates_reservation(self):
        task = self.env["project.task"].create(
            {
                "name": "Create + assignee",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
                **self.scheduled_vals,
            }
        )
        self.assertEqual(len(task.reservation_ids), 1)
        self.assertEqual(task.reservation_ids.resource_id, self.employee.resource_id)

    def test_create_without_dates_does_not_generate_reservation(self):
        task = self.env["project.task"].create(
            {
                "name": "Unscheduled",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
            }
        )
        self.assertFalse(task.reservation_ids)

    def test_adding_employee_to_existing_task_creates_reservation(self):
        task = self.env["project.task"].create(
            {
                "name": "Existing task",
                "project_id": self.project.id,
                **self.scheduled_vals,
            }
        )
        self.assertFalse(task.reservation_ids)

        task.write({"employee_ids": [Command.link(self.employee.id)]})

        self.assertEqual(
            len(task.reservation_ids),
            1,
            "Adding an assignee with a resource must auto-create its reservation",
        )
        self.assertEqual(task.reservation_ids.resource_id, self.employee.resource_id)

    def test_removing_employee_from_task_removes_its_reservation(self):
        task = self.env["project.task"].create(
            {
                "name": "To be unassigned",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
                **self.scheduled_vals,
            }
        )
        self.assertEqual(len(task.reservation_ids), 1)

        task.write({"employee_ids": [Command.unlink(self.employee.id)]})

        self.assertFalse(
            task.reservation_ids,
            "Unassigning the last employee must clear the reservation",
        )

    def test_changing_dates_updates_reservation_range(self):
        task = self.env["project.task"].create(
            {
                "name": "Reschedule me",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
                **self.scheduled_vals,
            }
        )
        reservation = task.reservation_ids
        self.assertEqual(len(reservation), 1)
        new_start = datetime(2026, 6, 1, 8, 0)
        new_end = datetime(2026, 6, 1, 17, 0)

        task.write({"date_start": new_start, "date_end": new_end})

        self.assertEqual(reservation.date_start, new_start)
        self.assertEqual(reservation.date_end, new_end)

    def test_renaming_task_updates_reservation_name(self):
        task = self.env["project.task"].create(
            {
                "name": "Old title",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
                **self.scheduled_vals,
            }
        )
        reservation = task.reservation_ids
        self.assertEqual(len(reservation), 1)

        task.name = "New title"

        self.assertEqual(
            reservation.name,
            task.display_name,
            "renaming the task must relabel its reservation",
        )
        self.assertIn("New title", reservation.name)

    def test_clearing_dates_removes_reservations(self):
        task = self.env["project.task"].create(
            {
                "name": "Unschedule me",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
                **self.scheduled_vals,
            }
        )
        self.assertEqual(len(task.reservation_ids), 1)

        task.write({"date_start": False, "date_end": False})

        self.assertFalse(task.reservation_ids)

    def test_assigning_employee_from_foreign_company_resolves_resource(self):
        task = self.env["project.task"].create(
            {
                "name": "Cross-company edit",
                "project_id": self.project.id,
                **self.scheduled_vals,
            }
        )
        self.assertFalse(task.reservation_ids)

        task.with_company(self.company_foreign).write(
            {"employee_ids": [Command.link(self.employee.id)]}
        )

        self.assertEqual(len(task.reservation_ids), 1)
        self.assertEqual(task.reservation_ids.resource_id, self.employee.resource_id)

    def test_foreign_company_edit_preserves_existing_reservations(self):
        task = self.env["project.task"].create(
            {
                "name": "Keep me",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
                **self.scheduled_vals,
            }
        )
        reservation = task.reservation_ids
        self.assertEqual(len(reservation), 1)

        task.with_company(self.company_foreign).write({"allocated_percentage": 75.0})

        self.assertTrue(
            reservation.exists(),
            "Existing reservations must survive foreign-company writes.",
        )

    def _create_second_assignee(self):
        user = self.env["res.users"].create(
            {
                "name": "Second Worker",
                "login": "second.worker@test",
                "tz": "UTC",
                "company_id": self.company_home.id,
                "company_ids": [Command.set([self.company_home.id])],
                "group_ids": [
                    Command.link(self.env.ref("base.group_user").id),
                    Command.link(self.env.ref("project.group_project_user").id),
                ],
            }
        )
        employee = self.env["hr.employee"].create(
            {
                "name": "Second Worker",
                "user_id": user.id,
                "company_id": self.company_home.id,
                "tz": "UTC",
            }
        )
        return user, employee

    def test_multi_employee_creates_one_reservation_each(self):
        _, second_employee = self._create_second_assignee()
        task = self.env["project.task"].create(
            {
                "name": "Multi-assigned",
                "project_id": self.project.id,
                "employee_ids": [Command.set([self.employee.id, second_employee.id])],
                **self.scheduled_vals,
            }
        )
        self.assertEqual(len(task.reservation_ids), 2)
        self.assertEqual(
            task.reservation_ids.mapped("resource_id").sorted("id"),
            (self.employee.resource_id | second_employee.resource_id).sorted("id"),
        )

    def test_removing_one_of_several_employees_only_clears_its_reservation(self):
        _, second_employee = self._create_second_assignee()
        task = self.env["project.task"].create(
            {
                "name": "Multi then trim",
                "project_id": self.project.id,
                "employee_ids": [Command.set([self.employee.id, second_employee.id])],
                **self.scheduled_vals,
            }
        )
        self.assertEqual(len(task.reservation_ids), 2)

        task.write({"employee_ids": [Command.unlink(self.employee.id)]})

        self.assertEqual(len(task.reservation_ids), 1)
        self.assertEqual(task.reservation_ids.resource_id, second_employee.resource_id)

    def test_archiving_task_archives_its_reservations(self):
        task = self.env["project.task"].create(
            {
                "name": "Archive me",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
                **self.scheduled_vals,
            }
        )
        reservation_id = task.reservation_ids.id
        reservation_no_filter = (
            self.env["resource.reservation"]
            .with_context(active_test=False)
            .browse(reservation_id)
        )

        task.action_archive()

        self.assertFalse(reservation_no_filter.active)
        self.assertFalse(
            task.reservation_ids,
            "Archived reservations must drop out of the default O2M.",
        )

    def test_unarchiving_task_restores_its_reservations(self):
        task = self.env["project.task"].create(
            {
                "name": "Roundtrip",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
                **self.scheduled_vals,
            }
        )
        task.action_archive()
        task.action_unarchive()

        self.assertEqual(
            len(task.reservation_ids),
            1,
            "Restoring the task must surface its reservation again.",
        )
        self.assertTrue(task.reservation_ids.active)

    def test_writing_user_ids_assigns_the_users_employee(self):
        task = self.env["project.task"].create(
            {
                "name": "user_ids assignment",
                "project_id": self.project.id,
                # explicitly nobody: a task created outside a project-scoped context
                # is otherwise assigned to whoever created it
                "user_ids": [],
                **self.scheduled_vals,
            }
        )
        self.assertFalse(task.employee_ids)

        task.write({"user_ids": [Command.link(self.user_with_resource.id)]})

        self.assertEqual(task.employee_ids, self.employee)
        self.assertEqual(task.user_ids, self.user_with_resource)
        self.assertTrue(task.reservation_ids)

    def test_reassigning_employee_user_repropagates_task_user_ids(self):
        task = self.env["project.task"].create(
            {
                "name": "User repropagation",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
                "direct_user_ids": [],
            }
        )
        self.assertEqual(task.user_ids, self.user_with_resource)

        new_user = self.env["res.users"].create(
            {
                "name": "Relinked User",
                "login": "relinked.task@test",
                "company_id": self.company_home.id,
                "company_ids": [Command.set([self.company_home.id])],
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )
        self.employee.user_id = new_user

        self.assertEqual(
            task.user_ids,
            new_user,
            "user_ids must follow the employee's relinked user.",
        )

    def test_reassigning_employee_user_repropagates_project_user_id(self):
        project = self.env["project.project"].create(
            {
                "name": "PM repropagation",
                "company_id": self.company_home.id,
                "employee_id": self.employee.id,
            }
        )
        self.assertEqual(project.user_id, self.user_with_resource)

        new_user = self.env["res.users"].create(
            {
                "name": "Relinked Manager",
                "login": "relinked.project@test",
                "company_id": self.company_home.id,
                "company_ids": [Command.set([self.company_home.id])],
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )
        self.employee.user_id = new_user

        self.assertEqual(
            project.user_id,
            new_user,
            "user_id must follow the employee's relinked user.",
        )

    def test_planned_hours_default_from_range(self):
        task = (
            self.env["project.task"]
            .with_company(self.company_home)
            .create(
                {
                    "name": "Planned default",
                    "project_id": self.project.id,
                    "date_start": datetime(2026, 5, 4, 8, 0),
                    "date_end": datetime(2026, 5, 4, 17, 0),
                }
            )
        )
        self.assertEqual(task.planned_hours, 8.0)

    def test_planned_hours_user_override_persists(self):
        task = (
            self.env["project.task"]
            .with_company(self.company_home)
            .create(
                {
                    "name": "Planned override",
                    "project_id": self.project.id,
                    "date_start": datetime(2026, 5, 4, 8, 0),
                    "date_end": datetime(2026, 5, 4, 17, 0),
                    "planned_hours": 20.0,
                }
            )
        )
        self.assertEqual(task.planned_hours, 20.0)

    def test_allocated_hours_single_user_sums_one_reservation(self):
        half_calendar = self.env["resource.calendar"].create(
            {
                "name": "Half Day",
                "tz": "UTC",
                "company_id": self.company_home.id,
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Mon AM",
                            "dayofweek": "0",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    )
                ],
            }
        )
        self.employee.resource_calendar_id = half_calendar
        task = self.env["project.task"].create(
            {
                "name": "Half day single user",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
                "date_start": datetime(2026, 5, 4, 8, 0),
                "date_end": datetime(2026, 5, 4, 17, 0),
            }
        )
        self.assertEqual(len(task.reservation_ids), 1)
        self.assertEqual(task.allocated_hours, 4.0)

    def test_allocated_hours_multi_user_sums_reservations(self):
        _, second_employee = self._create_second_assignee()
        task = (
            self.env["project.task"]
            .with_company(self.company_home)
            .create(
                {
                    "name": "Multi user",
                    "project_id": self.project.id,
                    "employee_ids": [
                        Command.set([self.employee.id, second_employee.id])
                    ],
                    "date_start": datetime(2026, 5, 4, 8, 0),
                    "date_end": datetime(2026, 5, 4, 17, 0),
                }
            )
        )
        self.assertEqual(len(task.reservation_ids), 2)
        self.assertEqual(task.allocated_hours, 16.0)

    def test_allocated_hours_zero_user_returns_zero(self):
        task = (
            self.env["project.task"]
            .with_company(self.company_home)
            .create(
                {
                    "name": "No assignee",
                    "project_id": self.project.id,
                    "date_start": datetime(2026, 5, 4, 8, 0),
                    "date_end": datetime(2026, 5, 4, 17, 0),
                }
            )
        )
        self.assertFalse(task.employee_ids)
        self.assertEqual(task.allocated_hours, 0.0)
        self.assertEqual(task.planned_hours, 8.0)
        self.assertEqual(task.allocation_state, "unallocated")

    def test_allocated_hours_scales_by_allocated_percentage(self):
        task = self.env["project.task"].create(
            {
                "name": "50%",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
                "date_start": datetime(2026, 5, 4, 8, 0),
                "date_end": datetime(2026, 5, 4, 17, 0),
                "allocated_percentage": 50.0,
            }
        )
        self.assertEqual(task.allocated_hours, 4.0)

    def test_planned_hours_honors_allocated_percentage(self):
        task = self.env["project.task"].create(
            {
                "name": "Half-time plan",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
                "date_start": datetime(2026, 5, 4, 8, 0),
                "date_end": datetime(2026, 5, 4, 17, 0),
                "allocated_percentage": 50.0,
            }
        )
        self.assertEqual(task.scheduled_hours, 8.0)
        self.assertEqual(task.planned_resources, 1)
        self.assertEqual(task.planned_hours, 4.0)
        self.assertEqual(task.allocated_hours, 4.0)
        self.assertEqual(task.allocation_state, "allocated")

    def test_planned_resources_default_one(self):
        task = (
            self.env["project.task"]
            .with_company(self.company_home)
            .create(
                {
                    "name": "Default resources",
                    "project_id": self.project.id,
                    "date_start": datetime(2026, 5, 4, 8, 0),
                    "date_end": datetime(2026, 5, 4, 17, 0),
                }
            )
        )
        self.assertEqual(task.planned_resources, 1)
        self.assertEqual(task.scheduled_hours, 8.0)
        self.assertEqual(task.planned_hours, 8.0)

    def test_planned_resources_doubles_planned_hours(self):
        task = (
            self.env["project.task"]
            .with_company(self.company_home)
            .create(
                {
                    "name": "Two resources",
                    "project_id": self.project.id,
                    "date_start": datetime(2026, 5, 4, 8, 0),
                    "date_end": datetime(2026, 5, 4, 17, 0),
                    "planned_resources": 2,
                }
            )
        )
        self.assertEqual(task.scheduled_hours, 8.0)
        self.assertEqual(task.planned_hours, 16.0)

    def test_planned_resources_must_be_positive(self):
        with (
            self.assertRaises(IntegrityError),
            self.cr.savepoint(),
            mute_logger("odoo.db"),
        ):
            self.env["project.task"].create(
                {
                    "name": "Zero resources",
                    "project_id": self.project.id,
                    "planned_resources": 0,
                }
            )

        with (
            self.assertRaises(IntegrityError),
            self.cr.savepoint(),
            mute_logger("odoo.db"),
        ):
            self.env["project.task"].create(
                {
                    "name": "Negative resources",
                    "project_id": self.project.id,
                    "planned_resources": -1,
                }
            )

    def test_planned_hours_inverse_posts_on_manual_override(self):
        task = self.env["project.task"].create(
            {
                "name": "Override case",
                "project_id": self.project.id,
                "date_start": datetime(2026, 5, 4, 8, 0),
                "date_end": datetime(2026, 5, 4, 17, 0),
            }
        )
        baseline = self.env["mail.message"].search_count(
            [("res_id", "=", task.id), ("model", "=", "project.task")]
        )

        task.write({"planned_resources": 2})
        self.assertEqual(task.planned_hours, 16.0)
        after_recompute = self.env["mail.message"].search_count(
            [("res_id", "=", task.id), ("model", "=", "project.task")]
        )
        self.assertLessEqual(after_recompute - baseline, 1)
        override_msgs = self.env["mail.message"].search(
            [
                ("res_id", "=", task.id),
                ("model", "=", "project.task"),
                ("body", "ilike", "manually overridden"),
            ]
        )
        self.assertFalse(
            override_msgs,
            "Recompute should not trigger override message.",
        )

        task.write({"planned_hours": 99.0})
        override_msgs = self.env["mail.message"].search(
            [
                ("res_id", "=", task.id),
                ("model", "=", "project.task"),
                ("body", "ilike", "manually overridden"),
            ]
        )
        self.assertEqual(len(override_msgs), 1)

    def test_allocation_state_unestimated(self):
        task = (
            self.env["project.task"]
            .with_company(self.company_home)
            .create({"name": "No dates", "project_id": self.project.id})
        )
        self.assertEqual(task.allocation_state, "unestimated")

    def test_allocation_state_unallocated(self):
        task = (
            self.env["project.task"]
            .with_company(self.company_home)
            .create(
                {
                    "name": "Not assigned",
                    "project_id": self.project.id,
                    "date_start": datetime(2026, 5, 4, 8, 0),
                    "date_end": datetime(2026, 5, 4, 17, 0),
                }
            )
        )
        self.assertEqual(task.planned_hours, 8.0)
        self.assertEqual(task.allocated_hours, 0.0)
        self.assertEqual(task.allocation_state, "unallocated")

    def test_allocation_state_allocated(self):
        task = (
            self.env["project.task"]
            .with_company(self.company_home)
            .create(
                {
                    "name": "Allocated",
                    "project_id": self.project.id,
                    "employee_ids": [Command.link(self.employee.id)],
                    "date_start": datetime(2026, 5, 4, 8, 0),
                    "date_end": datetime(2026, 5, 4, 17, 0),
                }
            )
        )
        self.assertEqual(task.planned_hours, 8.0)
        self.assertEqual(task.allocated_hours, 8.0)
        self.assertEqual(task.allocation_state, "allocated")

    def test_allocation_state_under_allocated(self):
        task = (
            self.env["project.task"]
            .with_company(self.company_home)
            .create(
                {
                    "name": "Partial",
                    "project_id": self.project.id,
                    "planned_resources": 2,
                    "employee_ids": [Command.link(self.employee.id)],
                    "date_start": datetime(2026, 5, 4, 8, 0),
                    "date_end": datetime(2026, 5, 4, 17, 0),
                }
            )
        )
        self.assertEqual(task.planned_hours, 16.0)
        self.assertEqual(task.allocated_hours, 8.0)
        self.assertEqual(task.allocation_state, "under_allocated")

    def test_allocation_state_over_allocated(self):
        _, second_employee = self._create_second_assignee()
        task = (
            self.env["project.task"]
            .with_company(self.company_home)
            .create(
                {
                    "name": "Overplanned",
                    "project_id": self.project.id,
                    "employee_ids": [
                        Command.set([self.employee.id, second_employee.id])
                    ],
                    "date_start": datetime(2026, 5, 4, 8, 0),
                    "date_end": datetime(2026, 5, 4, 17, 0),
                }
            )
        )
        self.assertEqual(task.planned_hours, 8.0)
        self.assertEqual(task.allocated_hours, 16.0)
        self.assertEqual(task.allocation_state, "over_allocated")

    def test_changing_employee_resource_updates_existing_reservations(self):
        task = self.env["project.task"].create(
            {
                "name": "Resource swap",
                "project_id": self.project.id,
                "employee_ids": [Command.link(self.employee.id)],
                **self.scheduled_vals,
            }
        )
        original_resource = self.employee.resource_id
        self.assertEqual(task.reservation_ids.resource_id, original_resource)

        replacement = self.env["resource.resource"].create(
            {
                "name": "Replacement Resource",
                "calendar_id": self.company_home.resource_calendar_id.id,
                "company_id": self.company_home.id,
            }
        )
        self.employee.resource_id = replacement

        self.assertEqual(
            len(task.reservation_ids),
            1,
            "Swapping the employee's resource must not duplicate reservations.",
        )
        self.assertEqual(
            task.reservation_ids.resource_id,
            replacement,
            "The reservation must follow the employee's current resource.",
        )
