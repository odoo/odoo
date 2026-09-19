from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import freeze_time, tagged

from .test_project_base import TestProjectCommon


@tagged("post_install", "-at_install")
class TestCpmFieldOwnership(TestProjectCommon):
    def test_cpm_fields_are_stored_and_distinct(self) -> None:
        Task = self.env["project.task"]
        for fname in ("cpm_date_start", "cpm_date_end"):
            field = Task._fields[fname]
            self.assertTrue(field.store, f"{fname} must be stored")
            self.assertFalse(field.compute, f"{fname} must not be computed")
            self.assertFalse(
                getattr(field, "inverse", None), f"{fname} must have no inverse"
            )

    def test_cpm_does_not_touch_user_entered_dates(self) -> None:
        project = self.env["project.project"].create(
            {"name": "CPM ownership", "allow_dependencies": True}
        )
        step = self.env["project.workflow.step"].create(
            {"name": "S", "project_ids": [Command.link(project.id)]}
        )
        task = self.env["project.task"].create(
            {
                "name": "scheduled",
                "project_id": project.id,
                "step_id": step.id,
                "date_start": "2026-08-03 08:00:00",
                "date_end": "2026-08-07 17:00:00",
            }
        )
        successor = self.env["project.task"].create(
            {"name": "succ", "project_id": project.id, "step_id": step.id}
        )
        successor.predecessor_ids = task
        before = (task.date_start, task.date_end, task.scheduled_hours)

        project.action_compute_critical_path()
        task.invalidate_recordset()

        self.assertEqual(
            (task.date_start, task.date_end, task.scheduled_hours),
            before,
            "CPM must write only its own fields",
        )

    def test_cpm_preserves_the_deadline_of_unscheduled_tasks(self) -> None:
        project = self.env["project.project"].create(
            {"name": "CPM deadlines", "allow_dependencies": True}
        )
        step = self.env["project.workflow.step"].create(
            {"name": "S", "project_ids": [Command.link(project.id)]}
        )
        deadline = fields.Datetime.to_datetime("2026-12-31 17:00:00")
        tasks = self.env["project.task"].create(
            [
                {
                    "name": name,
                    "project_id": project.id,
                    "step_id": step.id,
                    "date_end": deadline,
                    "planned_hours": 8.0,
                }
                for name in ("A", "B")
            ]
        )
        tasks[1].predecessor_ids = tasks[0]

        project.action_compute_critical_path()
        tasks.invalidate_recordset()

        for task in tasks:
            self.assertEqual(task.date_end, deadline, "deadline must survive CPM")

    def test_cpm_schedule_shape_is_stable_across_runs(self) -> None:
        project = self.env["project.project"].create(
            {"name": "CPM stability", "allow_dependencies": True}
        )
        step = self.env["project.workflow.step"].create(
            {"name": "S", "project_ids": [Command.link(project.id)]}
        )
        a, b = self.env["project.task"].create(
            [
                {
                    "name": name,
                    "project_id": project.id,
                    "step_id": step.id,
                    "planned_hours": 8.0,
                }
                for name in ("A", "B")
            ]
        )
        b.predecessor_ids = a

        def shape():
            (a + b).invalidate_recordset()
            return [
                (
                    t.cpm_date_end - t.cpm_date_start,
                    round(t.total_float, 4),
                    t.is_critical_path,
                )
                for t in (a + b)
            ]

        with freeze_time("2026-08-03 08:00:00"):
            project.action_compute_critical_path()
            first = shape()
            project.action_compute_critical_path()
            project.action_compute_critical_path()
            self.assertEqual(shape(), first, "the schedule shape must not drift")

    def test_cpm_duration_is_duration_not_effort(self) -> None:
        project = self.env["project.project"].create({"name": "CPM duration"})
        step = self.env["project.workflow.step"].create(
            {"name": "S", "project_ids": [Command.link(project.id)]}
        )
        task = self.env["project.task"].create(
            {
                "name": "one working week",
                "project_id": project.id,
                "step_id": step.id,
                "date_start": "2026-08-03 08:00:00",
                "date_end": "2026-08-07 17:00:00",
            }
        )
        self.assertEqual(
            task._get_cpm_duration_hours(),
            task.scheduled_hours,
            "a scheduled activity's duration is its working span",
        )

    def test_cpm_survives_a_company_without_a_calendar(self) -> None:
        project = self.env["project.project"].create(
            {"name": "CPM no calendar", "allow_dependencies": True}
        )
        step = self.env["project.workflow.step"].create(
            {"name": "S", "project_ids": [Command.link(project.id)]}
        )
        a, b = self.env["project.task"].create(
            [
                {
                    "name": name,
                    "project_id": project.id,
                    "step_id": step.id,
                    "planned_hours": 8.0,
                }
                for name in ("A", "B")
            ]
        )
        b.predecessor_ids = a
        project.company_id.resource_calendar_id = False
        project.invalidate_recordset(["resource_calendar_id"])

        project.action_compute_critical_path()
        project.action_level_resources()

    def test_cpm_honours_plain_m2m_dependencies(self) -> None:
        project = self.env["project.project"].create(
            {"name": "CPM edges", "allow_dependencies": True}
        )
        step = self.env["project.workflow.step"].create(
            {"name": "S", "project_ids": [Command.link(project.id)]}
        )
        x, y, z = self.env["project.task"].create(
            [
                {
                    "name": name,
                    "project_id": project.id,
                    "step_id": step.id,
                    "planned_hours": 8.0,
                }
                for name in ("X", "Y", "Z")
            ]
        )
        self.env["project.task.dependency"].create(
            {"task_id": y.id, "depends_on_id": x.id}
        )
        z.predecessor_ids = y

        project.action_compute_critical_path()
        (x + y + z).invalidate_recordset()

        self.assertGreaterEqual(
            z.cpm_date_start,
            y.cpm_date_end,
            "the M2M-only successor must still be scheduled after its predecessor",
        )


@tagged("post_install", "-at_install")
class TestDependencyStoresAgree(TestProjectCommon):
    def setUp(self) -> None:
        super().setUp()
        self.project = self.env["project.project"].create(
            {"name": "Deps", "allow_dependencies": True}
        )
        self.step = self.env["project.workflow.step"].create(
            {"name": "S", "project_ids": [Command.link(self.project.id)]}
        )
        self.a, self.b = self.env["project.task"].create(
            [
                {"name": n, "project_id": self.project.id, "step_id": self.step.id}
                for n in ("A", "B")
            ]
        )

    def _rows(self, task):
        return self.env["project.task.dependency"].search([("task_id", "=", task.id)])

    def test_successor_ids_link_materialises_a_typed_row(self) -> None:
        self.a.write({"successor_ids": [Command.link(self.b.id)]})
        self.assertIn(self.a, self.b.predecessor_ids)
        rows = self._rows(self.b)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.depends_on_id, self.a)

    def test_successor_ids_at_create_materialises_a_typed_row(self) -> None:
        task = self.env["project.task"].create(
            {
                "name": "C",
                "project_id": self.project.id,
                "successor_ids": [Command.link(self.b.id)],
            }
        )
        self.assertIn(task, self.b.predecessor_ids)
        self.assertEqual(self._rows(self.b).depends_on_id, task)

    def test_copy_preserves_dependency_type_and_lag(self) -> None:
        self.b.write({"predecessor_ids": [Command.link(self.a.id)]})
        self._rows(self.b).write({"dependency_type": "ss", "lag_hours": 24.0})

        copied = self.project.copy()
        rows = self.env["project.task.dependency"].search(
            [("project_id", "=", copied.id)]
        )
        self.assertEqual(len(rows), 1, "the copied project carries the dependency")
        self.assertEqual(rows.dependency_type, "ss")
        self.assertEqual(rows.lag_hours, 24.0)

    def test_m2m_link_materialises_a_typed_row(self) -> None:
        self.b.predecessor_ids = self.a
        rows = self._rows(self.b)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.depends_on_id, self.a)
        self.assertEqual(rows.dependency_type, "fs")
        self.assertEqual(rows.lag_hours, 0.0)

    def test_m2m_link_on_create_materialises_a_typed_row(self) -> None:
        task = self.env["project.task"].create(
            {
                "name": "C",
                "project_id": self.project.id,
                "step_id": self.step.id,
                "predecessor_ids": [Command.link(self.a.id)],
            }
        )
        self.assertEqual(self._rows(task).depends_on_id, self.a)

    def test_m2m_unlink_removes_the_typed_row(self) -> None:
        self.b.predecessor_ids = self.a
        self.assertTrue(self._rows(self.b))
        self.b.predecessor_ids = [Command.clear()]
        self.assertFalse(self._rows(self.b))

    def test_typed_row_edit_is_not_undone_by_the_reverse_sync(self) -> None:
        dependency = self.env["project.task.dependency"].create(
            {
                "task_id": self.b.id,
                "depends_on_id": self.a.id,
                "dependency_type": "ss",
                "lag_hours": 4.0,
            }
        )
        self.assertEqual(self.b.predecessor_ids, self.a)
        self.assertEqual(dependency.dependency_type, "ss")
        self.assertEqual(dependency.lag_hours, 4.0)
        self.assertEqual(len(self._rows(self.b)), 1)

    def test_typed_row_unlink_removes_the_m2m_link(self) -> None:
        dependency = self.env["project.task.dependency"].create(
            {"task_id": self.b.id, "depends_on_id": self.a.id}
        )
        dependency.unlink()
        self.assertFalse(self.b.predecessor_ids)
        self.assertFalse(self._rows(self.b))

    def test_a_cycle_formed_within_one_batch_is_refused(self) -> None:
        c = self.env["project.task"].create(
            {"name": "C", "project_id": self.project.id, "step_id": self.step.id}
        )
        with self.assertRaises(ValidationError):
            self.env["project.task.dependency"].create(
                [
                    {"task_id": self.b.id, "depends_on_id": self.a.id},
                    {"task_id": c.id, "depends_on_id": self.b.id},
                    {"task_id": self.a.id, "depends_on_id": c.id},
                ]
            )

    def test_an_acyclic_batch_is_accepted(self) -> None:
        c = self.env["project.task"].create(
            {"name": "C", "project_id": self.project.id, "step_id": self.step.id}
        )
        self.env["project.task.dependency"].create(
            [
                {"task_id": self.b.id, "depends_on_id": self.a.id},
                {"task_id": c.id, "depends_on_id": self.b.id},
            ]
        )
        self.env.flush_all()
        self.assertIn(self.a, self.b.predecessor_ids)
        self.assertIn(self.b, c.predecessor_ids)
        self.assertEqual(
            self.env["project.task.dependency"].search_count(
                [("project_id", "=", self.project.id)]
            ),
            2,
        )

    def test_cycle_detection_spans_projects(self) -> None:
        other = self.env["project.project"].create(
            {"name": "Other", "allow_dependencies": True}
        )
        other_step = self.env["project.workflow.step"].create(
            {"name": "S", "project_ids": [Command.link(other.id)]}
        )
        bridge = self.env["project.task"].create(
            {"name": "bridge", "project_id": other.id, "step_id": other_step.id}
        )
        Dependency = self.env["project.task.dependency"]
        Dependency.create({"task_id": bridge.id, "depends_on_id": self.a.id})
        Dependency.create({"task_id": self.b.id, "depends_on_id": bridge.id})
        with self.assertRaises(ValidationError):
            Dependency.create({"task_id": self.a.id, "depends_on_id": self.b.id})

    def test_self_dependency_is_a_cycle(self) -> None:
        with self.assertRaises(Exception):
            self.env["project.task.dependency"].create(
                {"task_id": self.a.id, "depends_on_id": self.a.id}
            )

    def test_critical_path_cycle_guard(self) -> None:
        project = self.env["project.project"].create(
            {
                "name": "CycleProj",
                "allow_dependencies": True,
            }
        )
        task_a = self.env["project.task"].create(
            {"name": "A", "project_id": project.id}
        )
        task_b = self.env["project.task"].create(
            {"name": "B", "project_id": project.id}
        )
        self.env["project.task.dependency"].create(
            {
                "task_id": task_b.id,
                "depends_on_id": task_a.id,
            }
        )
        self.env.cr.execute(
            """INSERT INTO project_task_dependency
               (task_id, depends_on_id, dependency_type, lag_hours)
               VALUES (%s, %s, 'fs', 0.0)""",
            (task_a.id, task_b.id),
        )
        self.env.invalidate_all()
        with self.assertRaises(UserError):
            project.action_compute_critical_path()

    def test_cpm_float_and_critical_path(self) -> None:
        project = self.env["project.project"].create(
            {"name": "CPM", "allow_dependencies": True}
        )

        def mk(name, hours):
            return self.env["project.task"].create(
                {
                    "name": name,
                    "project_id": project.id,
                    "allocated_hours": hours,
                }
            )

        a, b, c, d = mk("A", 8), mk("B", 4), mk("C", 2), mk("D", 2)
        b.predecessor_ids = a
        c.predecessor_ids = a
        d.predecessor_ids = b + c
        project.action_compute_critical_path()
        (a + b + c + d).invalidate_recordset(["total_float", "is_critical_path"])
        self.assertTrue(
            a.is_critical_path and b.is_critical_path and d.is_critical_path
        )
        self.assertFalse(c.is_critical_path)
        self.assertAlmostEqual(c.total_float, 2.0, places=2)
        for t in (a, b, d):
            self.assertAlmostEqual(t.total_float, 0.0, places=2)

    def test_cpm_long_chain_no_recursion_error(self) -> None:
        project = self.env["project.project"].create(
            {"name": "DeepCPM", "allow_dependencies": True}
        )
        depth = 1200
        tasks = (
            self.env["project.task"]
            .create(
                [
                    {"name": f"T{i}", "project_id": project.id, "allocated_hours": 1.0}
                    for i in range(depth)
                ]
            )
            .sorted("id")
        )
        for i in range(1, depth):
            tasks[i].predecessor_ids = tasks[i - 1]
        project.action_compute_critical_path()
        tasks[-1].invalidate_recordset(["is_critical_path"])
        self.assertTrue(tasks[-1].is_critical_path, "the whole chain is critical")
