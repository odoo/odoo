from odoo import Command, fields
from odoo.tests import tagged

from .test_project_base import TestProjectCommon


@tagged("post_install", "-at_install")
class TestElapsedWithoutCalendar(TestProjectCommon):
    def test_elapsed_falls_back_to_wall_clock(self) -> None:
        project = self.env["project.project"].create({"name": "No calendar"})
        step = self.env["project.workflow.step"].create(
            {"name": "S", "project_ids": [Command.link(project.id)]}
        )
        (project.company_id | self.env.company).resource_calendar_id = False
        project.invalidate_recordset(["resource_calendar_id"])
        self.assertFalse(project.resource_calendar_id)

        task = self.env["project.task"].create(
            {"name": "t", "project_id": project.id, "step_id": step.id}
        )
        task.state = "done"
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE project_task SET create_date = %s, date_assign = %s, "
            "date_closed = %s WHERE id = %s",
            (
                "2026-08-03 08:00:00",
                "2026-08-03 12:00:00",
                "2026-08-04 08:00:00",
                task.id,
            ),
        )
        self.env.invalidate_all()
        task.modified(["create_date", "date_assign", "date_closed"])
        self.env.flush_all()

        self.assertEqual(task.lead_time_hours, 24.0)
        self.assertEqual(task.queue_time_hours, 4.0)
        self.assertEqual(task.cycle_time_hours, 20.0)


@tagged("post_install", "-at_install")
class TestElapsedBatching(TestProjectCommon):
    def test_elapsed_matches_the_calendar(self) -> None:
        calendar = self.env.company.resource_calendar_id
        project = self.env["project.project"].create({"name": "Elapsed"})
        project.company_id = self.env.company
        create_date = fields.Datetime.to_datetime("2026-08-03 06:00:00")
        assign = fields.Datetime.to_datetime("2026-08-04 06:00:00")
        closed = fields.Datetime.to_datetime("2026-08-06 15:00:00")

        task = self.env["project.task"].create(
            {"name": "Measured", "project_id": project.id}
        )
        self.env.cr.execute(
            "UPDATE project_task SET create_date = %s WHERE id = %s",
            (create_date, task.id),
        )
        task.invalidate_recordset(["create_date"])
        task.write({"date_assign": assign, "date_closed": closed})
        self.env.flush_all()

        leave_domain = [
            ("company_id", "in", project.company_id.ids),
            ("time_type_id.is_work", "=", False),
        ]
        for label, start, stop, field in (
            ("queue", create_date, assign, "queue_time_hours"),
            ("lead", create_date, closed, "lead_time_hours"),
            ("cycle", assign, closed, "cycle_time_hours"),
        ):
            expected = calendar.get_work_duration_data(
                start, stop, compute_leaves=True, domain=leave_domain
            )["hours"]
            with self.subTest(span=label):
                self.assertAlmostEqual(task[field], expected, places=4)

    def test_elapsed_costs_one_calendar_call_per_batch(self) -> None:
        project = self.env["project.project"].create({"name": "Batched"})
        project.company_id = self.env.company
        tasks = self.env["project.task"].create(
            [{"name": f"B{i}", "project_id": project.id} for i in range(10)]
        )
        self.env.flush_all()

        calls = []
        Calendar = type(self.env["resource.calendar"])
        original = Calendar._work_intervals_batch

        def counting(records, *args, **kwargs):
            calls.append(records.ids)
            return original(records, *args, **kwargs)

        self.patch(Calendar, "_work_intervals_batch", counting)
        tasks.write({"date_closed": fields.Datetime.now()})
        self.env.flush_all()

        self.assertLessEqual(
            len(calls),
            1,
            f"one interval fetch for the whole batch, got {len(calls)}",
        )


@tagged("post_install", "-at_install")
class TestAssignmentStamp(TestProjectCommon):
    def test_empty_assignee_payload_does_not_stamp_date_assign(self) -> None:
        task = self.env["project.task"].create(
            {
                "name": "unassigned",
                "project_id": self.project_pigs.id,
                "user_ids": [Command.set([])],
            }
        )
        self.assertFalse(task.user_ids)
        self.assertFalse(task.date_assign)
