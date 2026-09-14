import logging
from urllib.parse import parse_qs, urlsplit

from odoo.exceptions import AccessError
from odoo.fields import Command, Domain
from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from .test_project_base import TestProjectCommon

_logger = logging.getLogger(__name__)


class TestProjectSharingCommon(TestProjectCommon):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        project_sharing_stages_vals_list = [
            (0, 0, {"name": "To Do", "sequence": 1}),
            (
                0,
                0,
                {
                    "name": "Done",
                    "sequence": 10,
                    "fold": True,
                    "rating_template_id": cls.env.ref(
                        "project.rating_project_request_email_template"
                    ).id,
                },
            ),
        ]

        cls.partner_portal = cls.env["res.partner"].create(
            {
                "name": "Chell Gladys",
                "email": "chell@gladys.portal",
                "company_id": False,
                "user_ids": [Command.link(cls.user_portal.id)],
            }
        )

        cls.project_cows = (
            cls.env["project.project"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "Cows",
                    "privacy_visibility": "portal",
                    "alias_name": "project+cows",
                    "workflow_step_ids": project_sharing_stages_vals_list,
                }
            )
        )
        cls.project_portal = (
            cls.env["project.project"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "Portal",
                    "privacy_visibility": "portal",
                    "alias_name": "project+portal",
                    "partner_id": cls.user_portal.partner_id.id,
                    "workflow_step_ids": project_sharing_stages_vals_list,
                }
            )
        )
        cls.project_portal.message_subscribe(partner_ids=[cls.partner_portal.id])

        cls.project_no_collabo = (
            cls.env["project.project"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "No Collabo",
                    "privacy_visibility": "followers",
                    "alias_name": "project+nocollabo",
                }
            )
        )

        cls.task_cow = (
            cls.env["project.task"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "Cow UserTask",
                    "user_ids": cls.user_projectuser,
                    "project_id": cls.project_cows.id,
                }
            )
        )
        cls.task_portal = (
            cls.env["project.task"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "Portal UserTask",
                    "user_ids": cls.user_projectuser,
                    "project_id": cls.project_portal.id,
                }
            )
        )
        cls.task_no_collabo = (
            cls.env["project.task"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "No Collabo Task",
                    "project_id": cls.project_no_collabo.id,
                }
            )
        )

        cls.task_tag = cls.env["project.tags"].create({"name": "Foo"})

        cls.project_sharing_form_view_xml_id = (
            "project.project_sharing_project_task_view_form"
        )

    def get_project_sharing_form_view(self, record, with_user=None) -> None:
        return Form(
            record.with_user(with_user or self.env.user),
            view=self.project_sharing_form_view_xml_id,
        )

    def get_project_share_link(self) -> None:
        self.env["project.share.wizard"].create(
            {
                "res_model": "project.project",
                "res_id": self.project_no_collabo.id,
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                            "access_mode": "advanced_edit",
                        }
                    ),
                ],
            }
        ).action_send_mail()
        return self.env["mail.message"].search(
            [
                ("partner_ids", "in", self.user_portal.partner_id.id),
            ]
        )


@tagged("project_sharing")
class TestProjectSharing(TestProjectSharingCommon):
    def test_portal_rating_batches_statistics_for_a_real_thread(self):
        task = self.env["project.task"].create(
            {
                "name": "Rating statistics challenge",
                "project_id": self.project_portal.id,
            }
        )
        messages = self.env["mail.message"].create(
            [
                {
                    "body": f"Rated comment {index}",
                    "model": task._name,
                    "res_id": task.id,
                }
                for index in range(30)
            ]
        )
        self.env["rating.rating"].create(
            [
                {
                    "message_id": message.id,
                    "res_model_id": self.env["ir.model"]._get(task._name).id,
                    "res_id": task.id,
                    "rating": 5,
                    "consumed": True,
                }
                for message in messages
            ]
        )
        messages.portal_message_format(options={"rating_include": True})
        costs = []
        for batch in (messages[:3], messages):
            self.env.flush_all()
            self.env.invalidate_all()
            before = self.env.cr.sql_statement_count
            values = batch.portal_message_format(options={"rating_include": True})
            costs.append(self.env.cr.sql_statement_count - before)
            self.assertEqual(len(values), len(batch))
            for value in values:
                self.assertEqual(value["rating_stats"]["total"], 30)
                self.assertEqual(value["rating_stats"]["avg"], 5)
        _logger.debug(
            "Portal rating metadata and thread-statistics SQL for 3/30 comments: %s",
            costs,
        )
        self.assertLessEqual(costs[1], costs[0] + 2)

    def test_cross_project_subtask_link_has_a_separate_sharing_parameter(self):
        projects = self.env["project.project"].create(
            [
                {"name": "Shared parent", "privacy_visibility": "portal"},
                {"name": "Shared child", "privacy_visibility": "portal"},
            ]
        )
        parent = self.env["project.task"].create(
            {
                "name": "Parent",
                "project_id": projects[0].id,
            }
        )
        child = self.env["project.task"].create(
            {
                "name": "Child",
                "project_id": projects[1].id,
                "parent_id": parent.id,
            }
        )
        action = parent.action_project_sharing_open_subtasks()
        self.assertEqual(action["type"], "ir.actions.act_url")
        query = parse_qs(urlsplit(action["url"]).query)
        _logger.debug("Cross-project subtask link query keys=%s", sorted(query))
        self.assertEqual(query["access_token"], [child.access_token])
        self.assertEqual(query["project_sharing"], ["1"])

    def test_project_share_wizard(self) -> None:
        self.project_portal.message_unsubscribe(
            partner_ids=self.user_portal.partner_id.ids
        )
        project_share_form = Form(
            self.env["project.share.wizard"].with_context(
                active_model="project.project", active_id=self.project_portal.id
            )
        )
        self.assertFalse(
            project_share_form.collaborator_ids,
            "No collaborator should be in the wizard.",
        )
        with self.assertRaises(
            AccessError,
            msg="A portal user who is not a collaborator cannot reach the project.",
        ):
            self.project_portal.with_user(
                self.user_portal
            )._is_project_sharing_accessible()
        with project_share_form.collaborator_ids.new() as collaborator_form:
            collaborator_form.partner_id = self.user_portal.partner_id
            collaborator_form.access_mode = "edit"
        project_share_wizard = project_share_form.save()
        project_share_wizard.action_send_mail()
        self.assertEqual(
            self.project_portal.collaborator_ids.mapped(
                lambda c: (c.partner_id, c.access_mode)
            ),
            [(self.user_portal.partner_id, "edit")],
        )
        self.assertTrue(
            self.project_portal.with_user(
                self.user_portal
            )._is_project_sharing_accessible(),
            "The collaborator reaches the project through project sharing.",
        )
        project_share_wizard = (
            self.env["project.share.wizard"]
            .with_context(
                active_model="project.project", active_id=self.project_portal.id
            )
            .new({})
        )
        self.assertEqual(
            project_share_wizard.collaborator_ids.mapped(
                lambda c: (c.partner_id, c.access_mode)
            ),
            [(self.user_portal.partner_id, "edit")],
            "The wizard reopens on the collaborators and their modes.",
        )

    def test_project_share_wizard_adds_a_collaborator_beside_an_existing_one(
        self,
    ) -> None:
        ProjectShare = self.env["project.share.wizard"].with_context(
            active_model="project.project", active_id=self.project_portal.id
        )
        self.project_portal.write(
            {
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.partner_1.id,
                            "access_mode": "advanced_edit",
                        }
                    ),
                ],
            }
        )
        project_share_form = Form(ProjectShare)
        self.assertEqual(len(project_share_form.collaborator_ids), 1)
        with project_share_form.collaborator_ids.new() as collaborator_form:
            collaborator_form.partner_id = self.user_portal.partner_id
            collaborator_form.access_mode = "edit"
        project_share_form.save().action_send_mail()

        modes = {
            c.partner_id: c.access_mode for c in self.project_portal.collaborator_ids
        }
        self.assertEqual(
            modes,
            {self.partner_1: "advanced_edit", self.user_portal.partner_id: "edit"},
        )
        self.assertEqual(
            {
                c.partner_id: c.access_mode
                for c in ProjectShare.new({}).collaborator_ids
            },
            modes,
        )

    def test_project_share_wizard_remove_collaborators(self) -> None:
        PortalShare = self.env["project.share.wizard"].with_context(
            active_model="project.project", active_id=self.project_portal.id
        )
        self.project_portal.write(
            {
                "collaborator_ids": [
                    Command.create({"partner_id": self.user_portal.partner_id.id}),
                    Command.create(
                        {"partner_id": self.partner_1.id, "access_mode": "edit"}
                    ),
                ],
            }
        )
        self.project_portal.message_subscribe(
            partner_ids=[self.partner_2.id, self.user_portal.partner_id.id]
        )
        with Form(PortalShare) as project_share_form:
            self.assertEqual(
                {
                    vals["partner_id"]: vals["access_mode"]
                    for vals in project_share_form.collaborator_ids._field_value._data.values()
                },
                {self.user_portal.partner_id.id: "view", self.partner_1.id: "edit"},
                "Only collaborators are listed; a follower is not a collaborator.",
            )
            while project_share_form.collaborator_ids:
                project_share_form.collaborator_ids.remove(0)

        self.assertTrue(
            self.project_portal.collaborator_ids,
            "the collaborators must survive a dialog that was never shared",
        )
        project_share_form.record.action_send_mail()

        self.assertFalse(self.project_portal.collaborator_ids)
        self.assertIn(
            self.partner_2,
            self.project_portal.message_partner_ids,
            "A follower who never collaborated keeps following.",
        )
        self.assertNotIn(
            self.user_portal.partner_id,
            self.project_portal.message_partner_ids,
            "A revoked collaborator stops following.",
        )

    def test_project_share_wizard_alter_access_mode_collaborators(self) -> None:
        ProjectShare = self.env["project.share.wizard"].with_context(
            active_model="project.project", active_id=self.project_portal.id
        )
        self.project_portal.write(
            {
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                            "access_mode": "advanced_edit",
                        }
                    ),
                    Command.create(
                        {"partner_id": self.partner_1.id, "access_mode": "edit"}
                    ),
                ],
                "message_partner_ids": [
                    Command.link(self.partner_2.id),
                ],
            }
        )
        with Form(ProjectShare) as project_share_form:
            for index in range(len(project_share_form.collaborator_ids.ids)):
                with project_share_form.collaborator_ids.edit(
                    index
                ) as collaborator_form:
                    if collaborator_form.partner_id == self.user_portal.partner_id:
                        collaborator_form.access_mode = "edit"
            with project_share_form.collaborator_ids.new() as collaborator_form:
                collaborator_form.partner_id = self.partner_2
                collaborator_form.access_mode = "advanced_edit"

        self.assertEqual(
            len(self.project_portal.collaborator_ids),
            2,
            "the access change must not land until the dialog is shared",
        )
        project_share_form.record.action_send_mail()

        self.assertEqual(
            {c.partner_id: c.access_mode for c in self.project_portal.collaborator_ids},
            {
                self.user_portal.partner_id: "edit",
                self.partner_1: "edit",
                self.partner_2: "advanced_edit",
            },
        )

    def test_project_sharing_access(self) -> None:
        with self.assertRaises(
            AccessError,
            msg="The public user should not have any access to project sharing feature of the portal project.",
        ):
            self.project_portal.with_user(
                self.user_public
            )._is_project_sharing_accessible()
        self.assertTrue(
            self.project_portal.with_user(
                self.user_projectuser
            )._is_project_sharing_accessible(),
            "The internal user should have all accesses to project sharing feature of the portal project.",
        )
        self.assertFalse(
            self.project_portal.with_user(
                self.user_portal
            )._is_project_sharing_accessible(),
            "The portal user should not have any access to project sharing feature of the portal project.",
        )
        self.project_portal.write(
            {
                "collaborator_ids": [
                    Command.create({"partner_id": self.user_portal.partner_id.id})
                ]
            }
        )
        self.assertTrue(
            self.project_portal.with_user(
                self.user_portal
            )._is_project_sharing_accessible(),
            "The portal user can access to project sharing feature of the portal project.",
        )

    @mute_logger("odoo.addons.base.models.ir_model", "odoo.addons.base.models.ir_rule")
    def test_create_task_in_project_sharing(self) -> None:
        Task = self.env["project.task"].with_context(
            {
                "tracking_disable": True,
                "default_project_id": self.project_portal.id,
                "default_user_ids": [(4, self.user_portal.id)],
            }
        )
        with self.assertRaises(
            AccessError,
            msg="Should not accept the portal user create a task in the project when he has not the edit access right.",
        ):
            with self.get_project_sharing_form_view(Task, self.user_portal) as form:
                form.name = "Test"
                task = form.save()

        self.project_portal.write(
            {
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                            "access_mode": "edit",
                        }
                    ),
                ],
            }
        )
        with self.get_project_sharing_form_view(Task, self.user_portal) as form:
            form.name = "Test"
            with form.child_ids.new() as subtask_form:
                subtask_form.name = "Test Subtask"
            task = form.save()
            self.assertEqual(task.name, "Test")
            self.assertEqual(task.project_id, self.project_portal)
            self.assertFalse(task.portal_user_names)
            self.assertTrue(task.step_id)

            self.assertEqual(task.child_ids.name, "Test Subtask")
            self.assertEqual(task.child_ids.project_id, self.project_portal)
            self.assertFalse(
                task.child_ids.portal_user_names,
                "by default no user should be assigned to a subtask created by the portal user.",
            )
            self.assertFalse(
                task.child_ids.user_ids,
                "No user should be assigned to the new subtask.",
            )

            with self.assertRaises(
                AssertionError,
                msg="Should not accept the portal user changes the project of the task.",
            ):
                form.project_id = self.project_cows
                task = form.save()

        Task = Task.with_user(self.user_portal)

        task = Task.create({"name": "foo", "parent_id": self.task_portal.id})
        self.assertEqual(task.parent_id, self.task_portal)
        with self.assertRaises(
            AccessError,
            msg="Should not accept the portal user to set a parent task he doesn't have access to.",
        ):
            Task.create({"name": "foo", "parent_id": self.task_no_collabo.id})
        with self.assertRaises(
            AccessError,
            msg="Should not accept the portal user to set a parent task he doesn't have access to.",
        ):
            task = Task.with_context(default_parent_id=self.task_no_collabo.id).create(
                {"name": "foo"}
            )

        with self.assertRaisesRegex(AccessError, "top-secret records"):
            Task.create(
                {
                    "name": "foo",
                    "child_ids": [
                        Command.update(self.task_no_collabo.id, {"name": "Foo"})
                    ],
                }
            )
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            Task.create(
                {
                    "name": "foo",
                    "child_ids": [Command.delete(self.task_no_collabo.id)],
                }
            )
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            Task.create(
                {
                    "name": "foo",
                    "child_ids": [Command.unlink(self.task_no_collabo.id)],
                }
            )
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            Task.create(
                {
                    "name": "foo",
                    "child_ids": [Command.link(self.task_no_collabo.id)],
                }
            )
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            Task.create(
                {
                    "name": "foo",
                    "child_ids": [Command.set([self.task_no_collabo.id])],
                }
            )

        with self.assertRaisesRegex(AccessError, "top-secret records"):
            Task.with_context(
                default_child_ids=[
                    Command.update(self.task_no_collabo.id, {"name": "Foo"})
                ]
            ).create({"name": "foo"})
        with Task.env.cr.savepoint() as sp:
            task = Task.with_context(
                default_child_ids=[Command.delete(self.task_no_collabo.id)]
            ).create({"name": "foo"})
            task.env.invalidate_all()
            self.assertTrue(
                self.task_no_collabo.exists(),
                "Task should still be there, no delete is sent",
            )
            sp.rollback()
        with self.env.cr.savepoint() as sp:
            self.task_no_collabo.parent_id = self.task_no_collabo.create(
                {"name": "parent collabo"}
            )
            task = Task.with_context(
                default_child_ids=[Command.unlink(self.task_no_collabo.id)]
            ).create({"name": "foo"})
            task.env.invalidate_all()
            self.assertTrue(
                self.task_no_collabo.parent_id,
                "Task should still be there, no delete is sent",
            )
            sp.rollback()
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task = Task.with_context(
                default_child_ids=[Command.link(self.task_no_collabo.id)]
            ).create({"name": "foo"})
            task.env.invalidate_all()
            self.assertFalse(task.child_ids)
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task = Task.with_context(
                default_child_ids=[Command.set([self.task_no_collabo.id])]
            ).create({"name": "foo"})
            task.env.invalidate_all()
            self.assertFalse(task.child_ids)

        with self.assertRaisesRegex(
            AccessError, "not allowed to create 'Project Tags'"
        ):
            Task.create({"name": "foo", "tag_ids": [Command.create({"name": "Bar"})]})
        with self.assertRaisesRegex(
            AccessError, "not allowed to modify 'Project Tags'"
        ):
            Task.create(
                {
                    "name": "foo",
                    "tag_ids": [Command.update(self.task_tag.id, {"name": "Bar"})],
                }
            )
        with self.assertRaisesRegex(
            AccessError, "not allowed to delete 'Project Tags'"
        ):
            Task.create({"name": "foo", "tag_ids": [Command.delete(self.task_tag.id)]})

        with self.assertRaisesRegex(
            AccessError, "not allowed to create 'Project Tags'"
        ):
            Task.with_context(default_tag_ids=[Command.create({"name": "Bar"})]).create(
                {"name": "foo"}
            )
        with Task.env.cr.savepoint() as sp:
            task = Task.with_context(
                default_tag_ids=[Command.update(self.task_tag.id, {"name": "Bar"})]
            ).create({"name": "foo"})
            task.env.invalidate_all()
            self.assertNotEqual(self.task_tag.name, "Bar")
            sp.rollback()
        with Task.env.cr.savepoint() as sp:
            Task.with_context(
                default_tag_ids=[Command.delete(self.task_tag.id)]
            ).create({"name": "foo"})
            task.env.invalidate_all()
            self.assertTrue(self.task_tag.exists())
            sp.rollback()

        task = Task.create(
            {
                "name": "foo",
                "color": 1,
                "tag_ids": [Command.link(self.task_tag.id)],
            }
        )
        self.assertEqual(task.color, 1)
        self.assertEqual(task.tag_ids, self.task_tag)

        task = Task.create(
            {
                "name": "foo",
                "color": 4,
                "tag_ids": [Command.set([self.task_tag.id])],
            }
        )
        self.assertEqual(task.color, 4)
        self.assertEqual(task.tag_ids, self.task_tag)

    @mute_logger("odoo.addons.base.models.ir_model", "odoo.addons.base.models.ir_rule")
    def test_edit_task_in_project_sharing(self) -> None:
        with self.assertRaises(
            AccessError,
            msg="Should not accept the portal user create a task in the project when he has not the edit access right.",
        ):
            with self.get_project_sharing_form_view(
                self.task_cow.with_context(
                    {
                        "tracking_disable": True,
                        "default_project_id": self.project_cows.id,
                    }
                ),
                self.user_portal,
            ) as form:
                form.name = "Test"
                task = form.save()

        project_share_wizard = self.env["project.share.wizard"].create(
            {
                "res_model": "project.project",
                "res_id": self.project_cows.id,
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                            "access_mode": "edit",
                        }
                    ),
                ],
            }
        )
        project_share_wizard.action_send_mail()
        self.task_cow.message_subscribe(partner_ids=self.user_portal.partner_id.ids)
        with self.get_project_sharing_form_view(
            self.task_cow.with_context(
                {
                    "tracking_disable": True,
                    "default_project_id": self.project_cows.id,
                    "uid": self.user_portal.id,
                }
            ),
            self.user_portal,
        ) as form:
            form.name = "Test"
            task = form.save()
            self.assertEqual(task.name, "Test")
            self.assertEqual(task.project_id, self.project_cows)

        with self.assertRaises(
            AssertionError,
            msg="Should not accept the portal user changes the project of the task.",
        ):
            with self.get_project_sharing_form_view(task, self.user_portal) as form:
                form.project_id = self.project_portal

        with self.get_project_sharing_form_view(task, self.user_portal) as form:
            with form.child_ids.new() as subtask_form:
                subtask_form.name = "Test Subtask"
                with self.assertRaises(
                    AssertionError,
                    msg="Should not accept the portal user changes the project of the task.",
                ):
                    subtask_form.project_id = self.project_portal
        self.assertEqual(task.child_ids.name, "Test Subtask")
        self.assertEqual(task.child_ids.project_id, self.project_cows)
        self.assertFalse(
            task.child_ids.portal_user_names,
            "by default no user should be assigned to a subtask created by the portal user.",
        )
        self.assertFalse(
            task.child_ids.user_ids,
            "No user should be assigned to the new subtask.",
        )

        task2 = (
            self.env["project.task"]
            .with_context(
                {
                    "tracking_disable": True,
                    "default_project_id": self.project_cows.id,
                    "default_user_ids": [Command.set(self.user_portal.ids)],
                }
            )
            .with_user(self.user_portal)
            .create({"name": "Test"})
        )
        self.assertFalse(
            task2.portal_user_names,
            "the portal user should not be assigned when the portal user creates a task into the project shared.",
        )

        with self.get_project_sharing_form_view(task, self.user_portal) as form:
            with form.child_ids.new() as subtask_form:
                subtask_form.name = "Test Subtask"
        self.assertEqual(
            len(task.child_ids),
            2,
            "Check 2 subtasks has correctly been created by the user portal.",
        )

        task.write({"parent_id": self.task_portal.id})
        self.assertEqual(task.parent_id, self.task_portal)
        with self.assertRaises(
            AccessError,
            msg="Should not accept the portal user to set a parent task he doesn't have access to.",
        ):
            task.write({"parent_id": self.task_no_collabo.id})

        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task.write(
                {
                    "child_ids": [
                        Command.update(self.task_no_collabo.id, {"name": "Foo"})
                    ]
                }
            )
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task.write({"child_ids": [Command.delete(self.task_no_collabo.id)]})
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task.write({"child_ids": [Command.unlink(self.task_no_collabo.id)]})
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task.write({"child_ids": [Command.link(self.task_no_collabo.id)]})
        with self.assertRaisesRegex(AccessError, "top-secret records"):
            task.write({"child_ids": [Command.set([self.task_no_collabo.id])]})

        with self.assertRaisesRegex(
            AccessError, "not allowed to create 'Project Tags'"
        ):
            task.write({"tag_ids": [Command.create({"name": "Bar"})]})
        with self.assertRaisesRegex(
            AccessError, "not allowed to modify 'Project Tags'"
        ):
            task.write({"tag_ids": [Command.update(self.task_tag.id, {"name": "Bar"})]})
        with self.assertRaisesRegex(
            AccessError, "not allowed to delete 'Project Tags'"
        ):
            task.write({"tag_ids": [Command.delete(self.task_tag.id)]})

        task.write({"tag_ids": [Command.link(self.task_tag.id)]})
        self.assertEqual(task.tag_ids, self.task_tag)

        task.write({"tag_ids": [Command.unlink(self.task_tag.id)]})
        self.assertFalse(task.tag_ids)

        task.write({"tag_ids": [Command.link(self.task_tag.id)]})
        task.write({"tag_ids": [Command.clear()]})
        self.assertFalse(task.tag_ids, [])

        task.write({"tag_ids": [Command.set([self.task_tag.id])]})
        self.assertEqual(task.tag_ids, self.task_tag)

        self.env["project.share.wizard"].create(
            {
                "res_model": "project.project",
                "res_id": self.project_cows.id,
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                            "access_mode": "edit",
                        }
                    ),
                ],
            }
        ).action_send_mail()
        self.assertEqual(self.project_cows.collaborator_ids.access_mode, "edit")

        task.sudo().message_partner_ids -= self.user_portal.partner_id
        task.write({"name": "foo"})
        self.assertEqual(task.name, "foo", "Following is not what grants editing.")
        other_step = self.project_cows.workflow_step_ids - task.step_id
        with self.assertRaises(AccessError):
            task.write({"step_id": other_step[:1].id})

        self.env["project.share.wizard"].create(
            {
                "res_model": "project.project",
                "res_id": self.project_cows.id,
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                            "access_mode": "view",
                        }
                    ),
                    Command.create(
                        {
                            "partner_id": self.env["res.partner"]
                            .create({"name": "Alain"})
                            .id,
                            "access_mode": "edit",
                        }
                    ),
                ],
            }
        ).action_send_mail()
        self.assertTrue(
            self.env.ref("project.project_task_rule_portal_project_sharing").active
        )

        task.sudo().message_partner_ids += self.user_portal.partner_id
        with self.assertRaises(AccessError):
            task.write({"name": "foo"})

    def test_portal_user_cannot_see_all_assignees(self) -> None:
        self.task_cow.write({"user_ids": [Command.link(self.user_projectmanager.id)]})
        with self.assertRaises(
            AccessError,
            msg="Should not accept the portal user to access to a task he does not follow it and its project.",
        ):
            self.task_cow.with_user(self.user_portal).read(["portal_user_names"])
        self.assertEqual(
            len(self.task_cow.user_ids),
            2,
            "2 users should be assigned in this task.",
        )

        project_share_wizard = self.env["project.share.wizard"].create(
            {
                "res_model": "project.project",
                "res_id": self.project_cows.id,
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                            "access_mode": "edit",
                        }
                    ),
                ],
            }
        )
        project_share_wizard.action_send_mail()
        self.task_cow.message_subscribe(partner_ids=self.user_portal.partner_id.ids)
        self.assertFalse(
            self.task_cow.with_user(self.user_portal).user_ids,
            "the portal user should see no assigness in the task.",
        )
        task_portal_read = self.task_cow.with_user(self.user_portal).read(
            ["portal_user_names"]
        )
        self.assertEqual(
            self.task_cow.portal_user_names,
            task_portal_read[0]["portal_user_names"],
            "the portal user should see assignees name in the task via the `portal_user_names` field.",
        )

    def test_portal_user_can_change_stage_with_rating(self) -> None:
        self.project_portal.write(
            {
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                            "access_mode": "advanced_edit",
                        }
                    ),
                ],
            }
        )
        stage = self.project_portal.workflow_step_ids[-1]
        stage.write(
            {
                "rating_active": True,
                "rating_status": "stage",
            }
        )
        self.task_portal.with_user(self.user_portal).write({"step_id": stage.id})

    def test_orm_method_with_true_false_domain(self) -> None:
        domain = Domain("id", "=", self.task_portal.id)
        self.project_portal.write(
            {
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                        }
                    )
                ],
            }
        )
        task = self.env["project.task"].with_user(self.user_portal).search(domain)
        self.assertTrue(task, "The task should be found.")
        task = self.env["project.task"].with_user(self.user_portal).search(Domain.FALSE)
        self.assertFalse(
            task,
            "No task should be found since the domain contained a falsy tuple.",
        )

        task_read_group = self.env["project.task"].formatted_read_group(
            domain,
            aggregates=["id:min", "__count"],
        )
        self.assertEqual(
            task_read_group[0]["__count"],
            1,
            "The task should be found with the formatted_read_group method containing a truly tuple.",
        )
        self.assertEqual(
            task_read_group[0]["id:min"],
            self.task_portal.id,
            "The task should be found with the formatted_read_group method containing a truly tuple.",
        )

        task_read_group = self.env["project.task"].formatted_read_group(
            Domain.FALSE,
            aggregates=["__count"],
        )
        self.assertFalse(
            task_read_group[0]["__count"],
            "No result should found with the formatted_read_group since the domain is falsy.",
        )

    def test_milestone_read_access_right(self) -> None:
        project_milestone = self.env["project.milestone"].create(
            {
                "name": "Test Project Milestone",
                "project_id": self.project_portal.id,
            }
        )
        with self.assertRaises(
            AccessError,
            msg="Should not accept the portal user to access to a milestone if he's not a collaborator of its project.",
        ):
            project_milestone.with_user(self.user_portal).read(["name"])

        self.project_portal.write(
            {
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                        }
                    )
                ],
            }
        )
        project_milestone.with_user(self.user_portal).read(["name"])
        with self.assertRaises(
            AccessError,
            msg="Should not accept the portal user to update a milestone.",
        ):
            project_milestone.with_user(self.user_portal).write(["name"])
        with self.assertRaises(
            AccessError,
            msg="Should not accept the portal user to delete a milestone.",
        ):
            project_milestone.with_user(self.user_portal).unlink()
        with self.assertRaises(
            AccessError,
            msg="Should not accept the portal user to create a milestone.",
        ):
            self.env["project.milestone"].with_user(self.user_portal).create(
                {
                    "name": "Test Project new Milestone",
                    "project_id": self.project_portal.id,
                }
            )

    def test_add_followers_from_share_edit_wizard(self) -> None:
        company_partner = self.env.company.partner_id
        partners = partner_a, partner_b, partner_d = self.env["res.partner"].create(
            [
                {"name": "Solanum", "parent_id": company_partner.id},
                {"name": "Zana", "parent_id": company_partner.id},
                {"name": "Thresh"},
            ]
        )
        partners |= company_partner
        project_to_share = self.env["project.project"].create(
            {"name": "project to share"}
        )
        (
            task_with_partner_1,
            task_with_partner_2,
            task_with_parent_partner,
            task_without_partner,
        ) = self.env["project.task"].create(
            [
                {
                    "name": "Task with partner 1",
                    "partner_id": partner_a.id,
                    "project_id": project_to_share.id,
                },
                {
                    "name": "Task with partner 2",
                    "partner_id": partner_b.id,
                    "project_id": project_to_share.id,
                },
                {
                    "name": "Task with company",
                    "partner_id": company_partner.id,
                    "project_id": project_to_share.id,
                },
                {
                    "name": "Task with no partner",
                    "project_id": project_to_share.id,
                },
            ]
        )
        project_to_share._add_followers(partners)

        self.assertEqual(
            partners,
            project_to_share.message_partner_ids,
            "All the partner should be set as a new follower of the project",
        )
        self.assertEqual(
            partner_a,
            task_with_partner_1.message_partner_ids,
            "Only the first partner should be set as a new follower for the task 1",
        )
        self.assertEqual(
            partner_b,
            task_with_partner_2.message_partner_ids,
            "Only the second partner should be set as a new follower for the task 2",
        )
        self.assertEqual(
            partners - partner_d,
            task_with_parent_partner.message_partner_ids,
            "The first, second, and the company partner should be set as new followers for the task 3 because the partner of this task is the parent of the other 2",
        )
        self.assertFalse(
            task_without_partner.message_partner_ids,
            "Since this task has no partner, no follower should be added",
        )

    def test_project_manager_remains_follower_after_sharing(self) -> None:
        project = (
            self.env["project.project"]
            .with_context({"mail_create_nolog": True})
            .create(
                {
                    "name": "project",
                    "privacy_visibility": "followers",
                    "user_id": self.user_projectmanager.id,
                }
            )
        )
        self.assertIn(
            self.user_projectmanager.partner_id,
            project.message_partner_ids,
            "Project manager should be a follower of the project",
        )
        project_share_wizard = self.env["project.share.wizard"].create(
            {
                "res_model": "project.project",
                "res_id": project.id,
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": self.user_portal.partner_id.id,
                            "access_mode": "view",
                        }
                    ),
                ],
            }
        )
        project_share_wizard.action_send_mail()
        self.assertIn(
            self.user_projectmanager.partner_id,
            project.message_partner_ids,
            "Project manager should still be a follower after sharing the project",
        )
        self.assertEqual(
            project.message_partner_ids,
            self.user_projectmanager.partner_id,
            "Sharing grants access without subscribing the collaborator.",
        )

    def test_portal_user_with_edit_rights_can_close_recurring_task(
        self,
    ) -> None:
        portal_user = self.env["res.users"].create(
            {
                "name": "Portal User",
                "login": "portaluser",
                "email": "portaluser@odoo.com",
                "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        project = self.env["project.project"].create(
            {
                "name": "Project with Portal User",
            }
        )
        project.task_ids = [
            Command.create(
                {
                    "name": "Recurrent Task",
                    "recurring_task": True,
                    "repeat_type": "forever",
                }
            )
        ]
        self.env["project.share.wizard"].create(
            {
                "res_model": "project.project",
                "res_id": project.id,
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": portal_user.partner_id.id,
                            "access_mode": "edit",
                        }
                    ),
                ],
            }
        ).action_send_mail()
        task = project.task_ids[0]
        self.env.invalidate_all()
        task.with_user(portal_user).write({"state": "done"})
        self.assertEqual(
            task.state,
            "done",
            "The portal user with edit rights should be able to mark the task as done.",
        )
        next_task = task.recurrence_id.task_ids.filtered(lambda t: t != task)
        self.assertTrue(
            next_task,
            "The next occurrence of the recurrent task should be created.",
        )
