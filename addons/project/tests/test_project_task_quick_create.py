from odoo.tests import Form

from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestProjectTaskQuickCreate(TestProjectCommon):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user1, cls.user2 = (
            cls.env["res.users"]
            .with_context({"no_reset_password": True})
            .create(
                [
                    {
                        "name": "Raouf 1",
                        "login": "raouf1",
                        "password": "raouf1aa",
                        "email": "raouf1@example.com",
                    },
                    {
                        "name": "Raouf 2",
                        "login": "raouf2",
                        "password": "raouf2aa",
                        "email": "raouf2@example.com",
                    },
                ]
            )
        )

    def test_create_task_with_valid_expressions(self) -> None:
        valid_expressions = {
            "task A 30X 2.5x #Tag1 #tag2 @Armande @Bast @raouf1 @raouf2 !": (
                "task A 30X 2.5x",
                2,
                4,
                "1",
                0,
            ),
            "task A 30X 2.5x #Tag1 #tag2 #tag3 @Armande @Bast @raouf1 ! @raouf2": (
                "task A 30X 2.5x",
                3,
                4,
                "1",
                0,
            ),
            "task A ! 30X 2.5x #Tag1 #tag2 #tag3 @Armande @Bast ! @raouf1 #tag4": (
                "task A 30X 2.5x",
                4,
                3,
                "1",
                0,
            ),
            "task A": ("task A", 0, 0, "0", 0),
            "task A !": ("task A", 0, 0, "1", 0),
            "task A 30X   2.5x #Tag1 #tag2     #tag3    @Armande      @Bast @raouf1 @raouf2": (
                "task A 30X   2.5x",
                3,
                4,
                "0",
                0,
            ),
            "task A 30X 2.5x #Tag1 @Armande #tag3 @Bast @raouf1 #tag2 @raouf2 #tag4": (
                "task A 30X 2.5x",
                4,
                4,
                "0",
                0,
            ),
            "task A 30X #tag1 @raouf1 Nothing !": (
                "task A 30X #tag1 @raouf1 Nothing",
                0,
                0,
                "1",
                0,
            ),
            "task A 30X 2.5x #Tag1 #tag2 #tag3 @Armande @Bast @raouf !": (
                "task A 30X 2.5x @raouf",
                3,
                2,
                "1",
                0,
            ),
            "task A 30X 2.5x #Tag1 #tag2 #tag3 @Armande @Bastttt @raouf1 @raouf2 !": (
                "task A 30X 2.5x @Bastttt",
                3,
                3,
                "1",
                0,
            ),
            "task A 30X 2.5x #TAG1 #tag1 #TAG2": (
                "task A 30X 2.5x",
                2,
                0,
                "0",
                0,
            ),
            "task A 30X 2.5x #Tag1 #tag2 @Armande @Bast @raouf1 @raouf2 !!": (
                "task A 30X 2.5x",
                2,
                4,
                "2",
                0,
            ),
            "task A !!": ("task A", 0, 0, "2", 0),
            "task A 30X 2.5x #Tag1 #tag2 #tag3 @Armande @Bastttt @raouf1 @raouf2 !!": (
                "task A 30X 2.5x @Bastttt",
                3,
                3,
                "2",
                0,
            ),
            "task A 30X 2.5x #Tag1 #tag2 @Armande @Bast @raouf1 @raouf2 !!!": (
                "task A 30X 2.5x",
                2,
                4,
                "3",
                0,
            ),
            "task A !!!": ("task A", 0, 0, "3", 0),
            "task A 30X 2.5x #Tag1 #tag2 #tag3 @Armande @Bastttt @raouf1 @raouf2 !!!": (
                "task A 30X 2.5x @Bastttt",
                3,
                3,
                "3",
                0,
            ),
        }

        for expression, values in valid_expressions.items():
            task_form = Form(
                self.env["project.task"].with_context(
                    {
                        "tracking_disable": True,
                        "default_project_id": self.project_pigs.id,
                    }
                ),
                view="project.quick_create_task_form",
            )
            task_form.display_name = expression
            task = task_form.save()
            results = (
                task.name,
                len(task.tag_ids),
                len(task.user_ids),
                task.priority,
                task.allocated_hours,
            )
            self.assertEqual(results, values)

    def test_create_task_with_invalid_expressions(self) -> None:
        invalid_expressions = (
            "#tag1 #tag2 #tag3 @Armande @Bast @raouf1 @raouf2",
            "@Armande @Bast @raouf1 @raouf2",
            "!",
            "task A!",
            "task A!!",
            "task A!!!",
            "!!",
            "!!!",
            "!! @Armande",
            "!!! #tag1",
        )

        for expression in invalid_expressions:
            task_form = Form(
                self.env["project.task"].with_context(
                    {
                        "tracking_disable": True,
                        "default_project_id": self.project_pigs.id,
                    }
                ),
                view="project.quick_create_task_form",
            )
            task_form.display_name = expression
            task = task_form.save()
            results = (
                task.name,
                len(task.tag_ids),
                len(task.user_ids),
                task.priority,
                task.allocated_hours,
            )
            self.assertEqual(results, (expression, 0, 0, "0", 0))

    def test_set_stage_on_project_from_task(self) -> None:
        new_stage = self.env["project.workflow.step"].create(
            {
                "name": "New Stage",
            }
        )
        self.env["project.task"].create(
            {
                "name": "Test Task",
                "step_id": new_stage.id,
                "project_id": self.project_pigs.id,
            }
        )
        self.assertIn(
            new_stage,
            self.project_pigs.workflow_step_ids,
            "Task stage is not set in project",
        )

    def test_create_task_with_default_value(self) -> None:
        self.project_pigs.write(
            {
                "company_id": self.env.company,
            }
        )
        project_ids = self.env["project.project"].search([]).ids
        self.env["ir.default"].discard_values("project.task", "project_id", project_ids)
        self.env["ir.default"].set("project.task", "project_id", self.project_pigs.id)
        field_specs = {"project_id": {}, "company_id": {"fields": {}}}
        task_values = self.env["project.task"].onchange({}, [], field_specs)["value"]
        self.assertEqual(
            task_values["project_id"],
            self.project_pigs.id,
            "The task project_id should be set",
        )

    def test_quick_create_survives_a_regex_metacharacter_in_a_mention(self) -> None:
        Task = self.env["project.task"].with_context(
            default_project_id=self.project_pigs.id
        )
        for title in ("Fix login @foo(", "Fix login @a[b", "Fix login @foo( !!"):
            with self.subTest(title=title):
                task = Task.create({"display_name": title})
                self.assertTrue(task.name)

    def test_a_resolvable_mention_still_assigns(self) -> None:
        task = (
            self.env["project.task"]
            .with_context(default_project_id=self.project_pigs.id)
            .create({"display_name": "Fix login @raouf1"})
        )
        self.assertIn(self.user1, task.user_ids)
        self.assertEqual(task.name, "Fix login")
