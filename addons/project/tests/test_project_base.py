from lxml import etree

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, users
from odoo.tests.common import TransactionCase


class TestProjectCommon(TransactionCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.env.company.resource_calendar_id.tz = "Europe/Brussels"

        user_group_partner_manager = cls.env.ref("base.group_partner_manager")
        user_group_employee = cls.env.ref("base.group_user")
        user_group_project_user = cls.env.ref("project.group_project_user")
        user_group_project_manager = cls.env.ref("project.group_project_manager")

        cls.partner_1 = cls.env["res.partner"].create(
            {"name": "Valid Lelitre", "email": "valid.lelitre@agrolait.com"}
        )
        cls.partner_2 = cls.env["res.partner"].create(
            {"name": "Valid Poilvache", "email": "valid.other@gmail.com"}
        )
        cls.partner_3 = cls.env["res.partner"].create(
            {"name": "Valid Poilboeuf", "email": "valid.poilboeuf@gmail.com"}
        )

        Users = cls.env["res.users"].with_context({"no_reset_password": True})
        cls.user_public = Users.create(
            {
                "name": "Bert Tartignole",
                "login": "bert",
                "email": "b.t@example.com",
                "signature": "SignBert",
                "notification_type": "email",
                "group_ids": [(6, 0, [cls.env.ref("base.group_public").id])],
            }
        )
        cls.user_portal = Users.create(
            {
                "name": "Chell Gladys",
                "login": "chell",
                "email": "chell@gladys.portal",
                "signature": "SignChell",
                "notification_type": "email",
                "group_ids": [(6, 0, [cls.env.ref("base.group_portal").id])],
            }
        )
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
                            user_group_partner_manager.id,
                        ],
                    )
                ],
            }
        )
        cls.user_projectmanager = Users.create(
            {
                "name": "Bastien ProjectManager",
                "login": "bastien",
                "email": "bastien.projectmanager@example.com",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            user_group_employee.id,
                            user_group_project_manager.id,
                            user_group_partner_manager.id,
                        ],
                    )
                ],
            }
        )
        cls._employ(cls.user_projectmanager)

        cls.project_pigs = (
            cls.env["project.project"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "Pigs",
                    "privacy_visibility": "employees",
                    "alias_name": "project+pigs",
                    "partner_id": cls.partner_1.id,
                }
            )
        )
        cls.task_1 = (
            cls.env["project.task"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "Pigs UserTask",
                    "user_ids": cls.user_projectuser,
                    "project_id": cls.project_pigs.id,
                }
            )
        )
        cls.task_2 = (
            cls.env["project.task"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "Pigs ManagerTask",
                    "user_ids": cls.user_projectmanager,
                    "project_id": cls.project_pigs.id,
                }
            )
        )

        cls.project_goats = (
            cls.env["project.project"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "Goats",
                    "privacy_visibility": "followers",
                    "alias_name": "project+goats",
                    "partner_id": cls.partner_1.id,
                    "workflow_step_ids": [
                        (
                            0,
                            0,
                            {
                                "name": "New",
                                "sequence": 1,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "name": "Won",
                                "sequence": 10,
                            },
                        ),
                    ],
                }
            )
        )


    @classmethod
    def _employ(cls, users) -> None:
        # a tree carrying project_hr assigns a project only to an employee, so
        # the user this fixture makes a manager is one where hr exists; the
        # project user stays without one, as the tests that employ them expect
        if "hr.employee" not in cls.env:
            return
        cls.env["hr.employee"].create(
            [
                {
                    "name": user.name,
                    "user_id": user.id,
                    "company_id": cls.env.company.id,
                }
                for user in users
            ]
        )


class TestProjectBase(TestProjectCommon):
    def test_delete_project_with_tasks(self) -> None:
        task_type = self.env["project.workflow.step"].create(
            {"name": "Won", "sequence": 1, "fold": True}
        )
        project_unlink = (
            self.env["project.project"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "rev",
                    "privacy_visibility": "employees",
                    "alias_name": "rev",
                    "partner_id": self.partner_1.id,
                    "workflow_step_ids": task_type,
                }
            )
        )

        self.env["project.task"].with_context({"mail_create_nolog": True}).create(
            {
                "name": "Pigs UserTask",
                "user_ids": self.user_projectuser,
                "project_id": project_unlink.id,
                "step_id": task_type.id,
            }
        )

        task_count = len(project_unlink.task_ids)
        self.assertEqual(task_count, 1, "The project should have 1 task")

        project_unlink.unlink()
        self.assertNotEqual(
            task_count,
            0,
            "The all tasks linked to project should be deleted when user delete the project",
        )

    def test_auto_assign_stages_when_importing_tasks(self) -> None:
        seeded = self.project_pigs.workflow_step_ids
        self.assertEqual(len(seeded), 1, "a project starts with one column")
        self.assertEqual(len(self.project_goats.workflow_step_ids), 2)
        first_stage = self.project_goats.workflow_step_ids[0]
        self.env["project.task"]._load_records_create(
            [
                {
                    "name": "First Task",
                    "project_id": self.project_pigs.id,
                    "step_id": first_stage.id,
                }
            ]
        )
        self.assertEqual(self.project_pigs.workflow_step_ids, seeded | first_stage)
        self.env["project.task"]._load_records_create(
            [
                {
                    "name": "task",
                    "project_id": self.project_pigs.id,
                    "step_id": stage.id,
                }
                for stage in self.project_goats.workflow_step_ids
            ]
        )
        self.assertEqual(
            self.project_pigs.workflow_step_ids,
            seeded | self.project_goats.workflow_step_ids,
        )

    def test_filter_visibility_unread_messages(self) -> None:
        user1 = self.user_projectuser
        user2 = self.user_projectuser.copy()
        user1.notification_type = "email"
        user2.notification_type = "inbox"
        for user, filter_visible_expected in ((user1, False), (user2, True)):
            Task = self.env["project.task"].with_user(user)
            arch = Task.get_view(self.env.ref("project.view_task_search_form").id)[
                "arch"
            ]
            tree = etree.fromstring(arch)
            self.assertEqual(
                bool(tree.xpath('//filter[@name="message_needaction"]')),
                filter_visible_expected,
            )

    @users("bastien")
    def test_search_favorite_order(self) -> None:
        self.project_goats.favorite_user_ids += self.user_projectmanager
        self.env.cr.flush()

        Project = self.env["project.project"]
        project_ids = [self.project_pigs.id, self.project_goats.id]
        domain = [("id", "in", project_ids)]

        self.assertEqual(
            Project.search(domain, order="is_user_favorite desc")[0],
            self.project_goats,
        )
        self.assertEqual(
            Project.search(domain, order="is_user_favorite")[-1], self.project_goats
        )

        self.assertTrue(self.project_pigs.id < self.project_goats.id)
        self.assertEqual(Project.search(domain, order="id").ids, project_ids)

    @users("bastien")
    def test_edit_favorite(self) -> None:
        project1, project2 = projects = self.env["project.project"].create(
            [
                {
                    "name": "Project Test1",
                },
                {
                    "name": "Project Test2",
                    "is_user_favorite": True,
                },
            ]
        )
        self.assertFalse(project1.is_user_favorite)
        self.assertTrue(project2.is_user_favorite)
        project1.is_user_favorite = True
        project2.is_user_favorite = False
        projects.invalidate_recordset(["is_user_favorite"])
        self.assertTrue(project1.is_user_favorite)
        self.assertFalse(project2.is_user_favorite)

    @users("bastien")
    def test_create_favorite_from_project_form(self) -> None:
        Project = self.env["project.project"]
        form1 = Form(Project)
        form1.name = "Project Test1"
        self.assertFalse(form1.is_user_favorite)
        project1 = form1.save()
        self.assertFalse(project1.is_user_favorite)

        form2 = Form(Project)
        form2.name = "Project Test2"
        form2.is_user_favorite = True
        self.assertTrue(form2.is_user_favorite)
        project2 = form2.save()
        self.assertTrue(project2.is_user_favorite)

    @users("bastien")
    def test_edit_favorite_from_project_form(self) -> None:
        project1, project2 = self.env["project.project"].create(
            [
                {
                    "name": "Project Test1",
                },
                {
                    "name": "Project Test2",
                    "is_user_favorite": True,
                },
            ]
        )
        with Form(project1) as form:
            form.is_user_favorite = True
        self.assertTrue(project1.is_user_favorite)

        with Form(project2) as form:
            form.is_user_favorite = False
        self.assertFalse(project2.is_user_favorite)

    def test_change_project_or_partner_company(self) -> None:
        company_1 = self.env.company
        company_2 = self.env["res.company"].create({"name": "Company 2"})
        partner = self.env["res.partner"].create(
            {
                "name": "Partner",
            }
        )
        self.project_pigs.partner_id = partner

        self.assertFalse(partner.company_id)
        self.assertFalse(self.project_pigs.company_id)
        self.project_pigs.company_id = company_1
        self.assertEqual(
            self.project_pigs.company_id,
            company_1,
            "The company of the project should have been updated.",
        )
        self.project_pigs.company_id = False
        partner.company_id = company_1

        self.assertEqual(
            partner.company_id,
            self.project_pigs.company_id,
            "The company of the project should have been updated.",
        )

        with self.assertRaises(UserError):
            self.project_pigs.company_id = company_2
        with self.assertRaises(UserError):
            partner.company_id = company_2
        partner.company_id = False
        self.project_pigs.company_id = False
        self.assertFalse(
            self.project_pigs.company_id,
            "The company of the project should have been set to False.",
        )
        self.project_pigs.company_id = company_1
        self.project_goats.company_id = company_1
        self.project_goats.partner_id = partner
        with self.assertRaises(UserError):
            self.project_goats.partner_id.company_id = company_2

        with self.assertRaises(UserError):
            partner.company_id = company_2
        self.project_pigs.company_id = company_2
        self.assertEqual(
            self.project_pigs.company_id,
            company_2,
            "The company of the project should have been updated.",
        )
        self.project_pigs.company_id = False
        self.assertFalse(
            self.project_pigs.company_id,
            "The company of the project should have been set to False.",
        )
        self.project_pigs.company_id = company_1
        partner.company_id = company_1
        self.assertEqual(
            partner.company_id,
            company_1,
            "The company of the partner should have been updated.",
        )

    def test_add_customer_rating_project(self) -> None:
        rate = self.env["rating.rating"].create(
            {
                "res_id": self.task_1.id,
                "parent_res_id": self.project_pigs.id,
                "res_model_id": self.env["ir.model"]._get("project.task").id,
                "parent_res_model_id": self.env["ir.model"]._get("project.project").id,
            }
        )
        rating = 5

        self.task_1.rating_apply(rating, token=rate.access_token)

        self.project_pigs.invalidate_recordset(["rating_child_ids", "rating_ids"])
        self.assertEqual(
            len(self.project_pigs.rating_child_ids),
            1,
            "There should be 1 rating linked to the project through its tasks",
        )
        self.assertFalse(
            self.project_pigs.rating_ids,
            "the project itself was not rated, only its task",
        )

    def test_planned_dates_consistency_for_project(self) -> None:
        goats = self.project_goats
        self.assertFalse(goats.date_start)
        self.assertFalse(goats.date)

        goats.write({"date_start": "2021-09-27", "date": "2021-09-28"})
        self.assertEqual(fields.Date.to_string(goats.date_start), "2021-09-27")
        self.assertEqual(fields.Date.to_string(goats.date), "2021-09-28")

        goats.write({"date_start": "2021-09-26"})
        self.assertEqual(fields.Date.to_string(goats.date_start), "2021-09-26")
        self.assertEqual(fields.Date.to_string(goats.date), "2021-09-28")
        goats.write({"date": "2021-09-29"})
        self.assertEqual(fields.Date.to_string(goats.date), "2021-09-29")

        with self.assertRaises(UserError):
            goats.date_start = False
        with self.assertRaises(UserError):
            goats.write({"date": False})
        goats.invalidate_recordset(["date_start", "date"])
        self.assertEqual(fields.Date.to_string(goats.date_start), "2021-09-26")
        self.assertEqual(fields.Date.to_string(goats.date), "2021-09-29")

        goats.write({"date_start": False, "date": False})
        self.assertFalse(goats.date_start)
        self.assertFalse(goats.date)

        with self.assertRaises(UserError):
            goats.write({"date_start": "2021-09-27"})
        with self.assertRaises(UserError):
            goats.write({"date": "2021-09-28"})
        goats.invalidate_recordset(["date_start", "date"])
        self.assertFalse(goats.date_start)
        self.assertFalse(goats.date)

        pigs = self.project_pigs
        projects = goats + pigs
        projects.write({"date_start": "2021-09-20", "date": "2021-09-28"})
        for p in projects:
            self.assertEqual(fields.Date.to_string(p.date_start), "2021-09-20")
            self.assertEqual(fields.Date.to_string(p.date), "2021-09-28")

        projects.write({"date_start": "2021-09-22"})
        for p in projects:
            self.assertEqual(fields.Date.to_string(p.date_start), "2021-09-22")
            self.assertEqual(fields.Date.to_string(p.date), "2021-09-28")

        goats.write({"date_start": False, "date": False})
        with self.assertRaises(UserError):
            projects.write({"date_start": "2021-09-25"})
        projects.invalidate_recordset(["date_start", "date"])
        self.assertFalse(goats.date_start)
        self.assertEqual(fields.Date.to_string(pigs.date_start), "2021-09-22")

        pigs.write({"date_start": False, "date": False})
        projects.write({"date_start": False, "date": False})
        for p in projects:
            self.assertFalse(p.date_start)
            self.assertFalse(p.date)

    def test_create_task_in_batch_with_email_cc(self) -> None:
        user_a, user_b, user_c = self.env["res.users"].create(
            [
                {
                    "name": "user A",
                    "login": "loginA",
                    "email": "email@bisous1",
                },
                {
                    "name": "user B",
                    "login": "loginB",
                    "email": "email@bisous2",
                },
                {
                    "name": "user C",
                    "login": "loginC",
                    "email": "email@bisous3",
                },
            ]
        )
        partner = self.env["res.partner"].create(
            {
                "name": "partner",
                "email": "email@bisous4",
            }
        )
        task_1, task_2 = (
            self.env["project.task"]
            .with_context({"mail_create_nolog": True})
            .create(
                [
                    {
                        "name": "task 1",
                        "project_id": self.project_pigs.id,
                        "email_cc": "email@bisous1, email@bisous2, email@bisous4",
                    },
                    {
                        "name": "task 2",
                        "project_id": self.project_pigs.id,
                        "email_cc": "email@bisous3, email@bisous2, email@bisous4",
                    },
                ]
            )
        )
        self.assertTrue(user_a.partner_id in task_1.message_partner_ids)
        self.assertTrue(user_b.partner_id in task_1.message_partner_ids)
        self.assertFalse(user_c.partner_id in task_1.message_partner_ids)
        self.assertFalse(partner in task_1.message_partner_ids)
        self.assertFalse(user_a.partner_id in task_2.message_partner_ids)
        self.assertTrue(user_b.partner_id in task_2.message_partner_ids)
        self.assertTrue(user_c.partner_id in task_2.message_partner_ids)
        self.assertFalse(partner in task_2.message_partner_ids)

    def test_create_private_task_in_batch(self) -> None:
        task_0, task_1 = (
            self.env["project.task"]
            .create(
                [
                    {
                        "name": f"task {i}",
                        "user_ids": self.env.user.ids,
                        "project_id": False,
                    }
                    for i in range(2)
                ]
            )
            .copy()
        )
        self.assertEqual(task_0.name, "task 0 (copy)")
        self.assertEqual(task_1.name, "task 1 (copy)")

    def test_duplicate_project_with_tasks(self) -> None:
        project = self.env["project.project"].create(
            {
                "name": "Project",
            }
        )
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": project.id,
            }
        )

        project_dup = project.copy()
        self.assertTrue(
            project_dup.active,
            "Active project should remain active when duplicating an active project",
        )
        self.assertEqual(
            project_dup.task_count,
            1,
            "Duplicated project should have as many tasks as orginial project",
        )
        self.assertTrue(
            project_dup.task_ids.active,
            "Active task should remain active when duplicating an active project",
        )

        task.active = False
        project_dup = project.copy()
        self.assertTrue(
            project_dup.active,
            "Active project should remain active when duplicating an active project",
        )
        self.assertFalse(
            project_dup.task_ids.active,
            "Archived task should remain archived when duplicating an active project",
        )

        project.active = False
        project_dup = project.copy()
        self.assertTrue(
            project_dup.active, "The new project should be active by default"
        )
        self.assertTrue(
            project_dup.task_ids.active,
            "Archived task should be active when duplicating an archived project",
        )

    def test_create_analytic_account_batch(self) -> None:
        projects = self.env["project.project"].create(
            [
                {
                    "name": f"Project {x}",
                }
                for x in range(10)
            ]
        )
        projects._create_analytic_account()
        self.assertEqual(
            projects.mapped("name"),
            projects.account_id.mapped("name"),
            "The analytic accounts names should match with the projects.",
        )

    def test_task_count(self) -> None:
        project1, project2 = self.env["project.project"].create(
            [
                {"name": "project1"},
                {"name": "project2"},
            ]
        )
        self.env["project.task"].with_context(default_project_id=project1.id).create(
            [
                {"name": "task1"},
                {"name": "task2", "state": "done"},
                {
                    "name": "task3",
                    "child_ids": [
                        Command.create({"name": "subtask1", "project_id": project1.id}),
                        Command.create(
                            {
                                "name": "subtask2",
                                "project_id": project1.id,
                                "state": "canceled",
                            }
                        ),
                        Command.create({"name": "subtask3", "project_id": project2.id}),
                        Command.create(
                            {
                                "name": "subtask4",
                                "project_id": project1.id,
                                "child_ids": [
                                    Command.create(
                                        {
                                            "name": "subsubtask41",
                                            "project_id": project2.id,
                                        }
                                    ),
                                    Command.create(
                                        {
                                            "name": "subsubtask42",
                                            "project_id": project1.id,
                                        }
                                    ),
                                ],
                            }
                        ),
                        Command.create(
                            {
                                "name": "subtask5",
                                "state": "done",
                                "project_id": project1.id,
                                "child_ids": [
                                    Command.create(
                                        {
                                            "name": "subsubtask51",
                                            "project_id": project1.id,
                                            "state": "done",
                                        }
                                    ),
                                ],
                            }
                        ),
                    ],
                },
            ]
        )
        self.assertEqual(project1.task_count, 9)
        self.assertEqual(project1.open_task_count, 5)
        self.assertEqual(project1.closed_task_count, 4)
        self.assertEqual(project2.task_count, 2)
        self.assertEqual(project2.open_task_count, 2)
        self.assertEqual(project2.closed_task_count, 0)

    def test_archived_duplicate_task(self) -> None:
        project = self.env["project.project"].create(
            {
                "name": "Project",
            }
        )
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": project.id,
            }
        )
        copy_task1 = task.copy()
        self.assertTrue(
            copy_task1.active,
            "Active task should be active when duplicating an active task",
        )
        task.active = False
        copy_task2 = task.copy()
        self.assertTrue(
            copy_task2.active,
            "Archived task should be active when duplicating an archived task",
        )

    def test_duplicate_doesnt_copy_date(self) -> None:
        project = self.env["project.project"].create(
            {
                "name": "Project",
                "date_start": "2021-09-20",
                "date": "2021-09-28",
            }
        )
        task = self.env["project.task"].create(
            {
                "name": "Task",
                "project_id": project.id,
                "date_end": "2021-09-26",
            }
        )
        project_copy = project.copy()
        self.assertFalse(
            project_copy.date_start,
            "The project's date fields shouldn't be copied on project duplication",
        )
        self.assertFalse(
            project_copy.date,
            "The project's date fields shouldn't be copied on project duplication",
        )
        self.assertFalse(
            project_copy.task_ids.date_end,
            "The task's date fields shouldn't be copied on project duplication",
        )
        self.assertFalse(
            task.copy().date_end,
            "The task's date fields shouldn't be copied on task duplication",
        )

    def test_task_ids_is_the_only_task_relation(self) -> None:
        Project = self.env["project.project"]
        self.assertNotIn(
            "tasks", Project._fields, "the duplicate relation must be gone"
        )
        field = Project._fields["task_ids"]
        self.assertEqual(field.comodel_name, "project.task")
        self.assertEqual(field.inverse_name, "project_id")

    def test_task_ids_returns_closed_tasks_too(self) -> None:
        project = self.env["project.project"].create({"name": "Both"})
        open_task, closed_task = self.env["project.task"].create(
            [
                {"name": "open", "project_id": project.id},
                {"name": "closed", "project_id": project.id},
            ]
        )
        closed_task.state = "done"
        project.invalidate_recordset(["task_ids"])
        self.assertEqual(project.task_ids, open_task | closed_task)
