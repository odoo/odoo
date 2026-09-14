from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import HttpCase
from odoo.tools import mute_logger
from odoo.tools.safe_eval import safe_eval

from odoo.addons.project.tests.test_access_rights import TestProjectPortalCommon


class TestPortalProject(TestProjectPortalCommon, HttpCase):
    @mute_logger("odoo.addons.base.models.ir_model")
    def test_portal_project_access_rights(self) -> None:
        pigs = self.project_pigs
        pigs.write({"privacy_visibility": "portal"})

        pigs.with_user(self.user_projectuser).read(["user_id"])
        tasks = (
            self.env["project.task"]
            .with_user(self.user_projectuser)
            .search([("project_id", "=", pigs.id)])
        )
        self.assertEqual(
            tasks,
            self.task_1
            | self.task_2
            | self.task_3
            | self.task_4
            | self.task_5
            | self.task_6,
            "access rights: project user should see all tasks of a portal project",
        )

        self.assertRaises(
            AccessError, pigs.with_user(self.user_noone).read, ["user_id"]
        )
        self.assertRaises(
            AccessError,
            self.env["project.task"].with_user(self.user_noone).search,
            [("project_id", "=", pigs.id)],
        )

        pigs.with_user(self.user_projectmanager).message_subscribe(
            partner_ids=[self.user_portal.partner_id.id]
        )
        self.assertRaises(
            AccessError, pigs.with_user(self.user_portal).read, ["user_id"]
        )
        pigs.sudo()._add_collaborators(self.user_portal.partner_id, access_mode="view")
        self.task_1.with_user(self.user_projectuser).message_subscribe(
            partner_ids=[self.user_portal.partner_id.id]
        )
        self.task_3.with_user(self.user_projectuser).message_subscribe(
            partner_ids=[self.user_portal.partner_id.id]
        )
        pigs.with_user(self.user_portal).read(["user_id"])
        self.assertRaises(
            AccessError, pigs.with_user(self.user_public).read, ["user_id"]
        )
        self.assertRaises(
            AccessError,
            self.env["project.task"].with_user(self.user_public).search,
            [],
        )
        self.task_1.with_user(self.user_projectuser).message_unsubscribe(
            partner_ids=[self.user_portal.partner_id.id]
        )
        self.task_3.with_user(self.user_projectuser).message_unsubscribe(
            partner_ids=[self.user_portal.partner_id.id]
        )

    def test_reset_access_token_when_privacy_visibility_changes(self) -> None:
        self.assertNotEqual(
            self.project_pigs.privacy_visibility,
            "portal",
            "Make sure the privacy visibility is not yet the portal one.",
        )
        self.assertFalse(
            self.project_pigs.access_token,
            "The access token should not be set on the project since it is not public",
        )
        self.project_pigs.privacy_visibility = "portal"
        self.assertFalse(
            self.project_pigs.access_token,
            "The access token should not yet available since the project has not been shared yet.",
        )
        wizard = self.env["project.share.wizard"].create(
            {
                "res_model": "project.project",
                "res_id": self.project_pigs.id,
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.partner_1.id,
                        }
                    ),
                ],
            }
        )
        wizard.action_send_mail()
        self.assertEqual(self.task_1.project_id, self.project_pigs)
        self.assertTrue(
            self.project_pigs.access_token,
            "The access token should be set since the project has been shared.",
        )
        access_token = self.project_pigs.access_token
        task_access_token = self.task_1.access_token
        self.project_pigs.privacy_visibility = "followers"
        self.assertFalse(
            self.project_pigs.access_token,
            "The access token should no longer be set since now the project is private.",
        )
        self.assertFalse(
            all(self.project_pigs.task_ids.mapped("access_token")),
            "The access token should no longer be set in any tasks linked to the project since now the project is private.",
        )
        self.project_pigs.privacy_visibility = "portal"
        self.assertFalse(
            self.project_pigs.access_token,
            "The access token should still not be set since now the project has not been shared yet.",
        )
        self.assertFalse(
            all(self.project_pigs.task_ids.mapped("access_token")),
            "The access token should no longer be set in any tasks linked to the project since now the project is private.",
        )
        wizard.action_send_mail()
        self.assertTrue(
            self.project_pigs.access_token,
            "The access token should now be regenerated for this project since that project has been shared to an external partner.",
        )
        self.assertFalse(self.task_1.access_token)
        task_wizard = self.env["portal.share"].create(
            {
                "res_model": "project.task",
                "res_id": self.task_1.id,
                "partner_ids": [
                    Command.link(self.partner_1.id),
                ],
            }
        )
        task_wizard.action_send_mail()
        self.assertTrue(
            self.task_1.access_token,
            "The access token should be set since the task has been shared.",
        )
        self.assertNotEqual(
            self.project_pigs.access_token,
            access_token,
            "The new access token generated for the project should not be the old one.",
        )
        self.assertNotEqual(
            self.task_1.access_token,
            task_access_token,
            "The new access token generated for the task should not be the old one.",
        )
        self.project_pigs.privacy_visibility = "employees"
        self.assertFalse(
            self.project_pigs.access_token,
            "The access token should no longer be set since now the project is only available by internal users.",
        )
        self.assertFalse(
            all(self.project_pigs.task_ids.mapped("access_token")),
            "The access token should no longer be set in any tasks linked to the project since now the project is only available by internal users.",
        )

    def test_search_validates_results(self) -> None:
        project_manager = self.env["res.users"].search(
            [
                (
                    "group_ids",
                    "in",
                    [self.env.ref("project.group_project_manager").id],
                )
            ],
            limit=1,
        )
        self.authenticate(project_manager.login, project_manager.login)
        self.project_1 = self.env["project.project"].create(
            {"name": "Portal Search Project 1"}
        )
        self.project_2 = self.env["project.project"].create(
            {"name": "Portal Search Project 2"}
        )
        self.task_1 = self.env["project.task"].create(
            {
                "name": "Test Task Name Match",
                "project_id": self.project_1.id,
                "user_ids": project_manager,
            }
        )

        self.task_2 = self.env["project.task"].create(
            {
                "name": "Another Task For Searching",
                "project_id": self.project_2.id,
                "user_ids": project_manager,
            }
        )

        url = "/my/tasks"
        response = self.url_open(url)
        self.assertIn(self.task_1.name, response.text)
        self.assertIn(self.task_2.name, response.text)

        url = "/my/tasks?search_in=name&search=Test+Task+Name+Match"
        response = self.url_open(url)
        self.assertIn(self.task_1.name, response.text)
        self.assertNotIn(self.task_2.name, response.text)

        url = "/my/tasks?search_in=project_id&search=%s" % (self.project_1.name)
        response = self.url_open(url)
        self.assertIn(self.task_1.name, response.text)
        self.assertNotIn(self.task_2.name, response.text)

    def test_task_templates_visibility_portal(self) -> None:
        self.authenticate(self.user_portal.login, self.user_portal.login)
        portal_project = self.env["project.project"].create({"name": "Portal Project"})
        portal_project.message_subscribe(partner_ids=[self.user_portal.partner_id.id])
        portal_project._add_collaborators(
            self.user_portal.partner_id, access_mode="view"
        )
        task, task_template = self.env["project.task"].create(
            [
                {
                    "name": "Visible Task",
                    "project_id": portal_project.id,
                },
                {
                    "name": "Invisible Template Task",
                    "project_id": portal_project.id,
                    "is_template": True,
                    "child_ids": [
                        Command.create({"name": "Sub Task of Template Task 1"}),
                        Command.create({"name": "Sub Task of Template Task 2"}),
                    ],
                },
            ]
        )

        my_tasks_response = self.url_open("/my/tasks")
        self.assertIn(task.name, my_tasks_response.text)
        self.assertNotIn(task_template.name, my_tasks_response.text)
        self.assertNotIn(task_template.child_ids[0].name, my_tasks_response.text)
        self.assertNotIn(task_template.child_ids[1].name, my_tasks_response.text)

        sharing_action = self.env.ref("project.project_sharing_project_task_action")
        shared_names = (
            self.env["project.task"]
            .with_user(self.user_portal)
            .search(safe_eval(sharing_action.domain, {"active_id": portal_project.id}))
            .mapped("name")
        )
        self.assertIn(task.name, shared_names)
        self.assertNotIn(task_template.name, shared_names)
        self.assertNotIn(task_template.child_ids[0].name, shared_names)
        self.assertNotIn(task_template.child_ids[1].name, shared_names)

    def test_home_badges_count_what_the_pages_list(self) -> None:
        from odoo.addons.project.controllers.portal import ProjectCustomerPortal

        portal = ProjectCustomerPortal()
        Project = self.env["project.project"]
        Task = self.env["project.task"]
        template_project = Project.create({"name": "A template", "is_template": True})
        Task.create(
            {
                "name": "A template task",
                "project_id": template_project.id,
                "is_template": True,
            }
        )
        self.env.flush_all()

        self.assertEqual(
            Project.search_count(portal._get_domain_project()),
            Project.search_count([("is_template", "=", False)]),
        )
        self.assertNotIn(
            template_project,
            Project.search(portal._get_domain_project()),
            "a template project is not listed, so it must not be counted",
        )
        counted = Task.search(portal._get_domain_task())
        self.assertFalse(
            counted.filtered(lambda t: t.is_template or t.has_template_ancestor),
            "a template task is not listed, so it must not be counted",
        )
