from odoo import Command
from odoo.tests import tagged

from odoo.addons.project.tests.test_project_sharing import TestProjectSharingCommon
from odoo.addons.sms.tests.common import SMSCommon


class TestProjectSharingWithSms(TestProjectSharingCommon, SMSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        project_settings = cls.env["res.config.settings"].create(
            {"group_project_stages": True}
        )
        project_settings.execute()

        cls.sms_template = (
            cls.env["sms.template"]
            .sudo()
            .create(
                {
                    "body": "{{ object.name }}",
                    "model_id": cls.env["ir.model"]
                    .sudo()
                    .search([("model", "=", "project.task")])
                    .id,
                }
            )
        )
        cls.task_stage_with_sms = cls.project_portal.workflow_step_ids[-1]
        cls.task_stage_with_sms.write({"sms_template_id": cls.sms_template.id})

        cls.sms_template_2 = (
            cls.env["sms.template"]
            .sudo()
            .create(
                {
                    "body": "{{ object.name }}",
                    "model_id": cls.env["ir.model"]
                    .sudo()
                    .search([("model", "=", "project.project")])
                    .id,
                }
            )
        )
        cls.project_stage_with_sms = cls.project_portal.phase_id.browse(2)
        cls.project_stage_with_sms.write({"sms_template_id": cls.sms_template_2.id})

        cls.project_portal.write(
            {
                "collaborator_ids": [
                    Command.create(
                        {
                            "partner_id": cls.user_portal.partner_id.id,
                            "access_mode": "advanced_edit",
                        }
                    ),
                ],
            }
        )
        cls.project_portal.partner_id.phone_ids = [
            Command.create({"number": cls.random_numbers[0]})
        ]

    def test_portal_user_can_change_stage_with_sms_template(self):
        with self.mockSMSGateway():
            self.task_portal.with_user(self.user_portal).write(
                {
                    "step_id": self.task_stage_with_sms.id,
                }
            )
        self.assertEqual(self.task_portal.step_id, self.task_stage_with_sms)
        self.assertSMSIapSent([])

        self.task_portal.write(
            {
                "partner_id": self.user_projectuser.partner_id.id,
                "step_id": self.project_portal.workflow_step_ids[0].id,
            }
        )
        with self.mockSMSGateway():
            self.task_portal.with_user(self.user_portal).write(
                {
                    "step_id": self.task_stage_with_sms.id,
                }
            )
        self.assertEqual(self.task_portal.step_id, self.task_stage_with_sms)
        self.assertSMSIapSent(
            [self.user_projectuser.partner_id._phone_get_number().number]
        )

        with self.mockSMSGateway():
            self.project_portal.write(
                {
                    "phase_id": self.project_stage_with_sms.id,
                }
            )
        self.assertEqual(self.project_portal.phase_id, self.project_stage_with_sms)
        self.assertSMSIapSent(
            [self.project_portal.partner_id._phone_get_number().number]
        )

    @tagged("post_install", "-at_install")
    def test_project_user_can_change_stage_with_sms_template(self):
        project_user_group = self.env.ref("project.group_project_user")
        sale_manager_group = self.env.ref("sale.group_sale_manager", False)
        if not sale_manager_group:
            self.skipTest("`sale_sms` not installed")
        self.user_projectuser.write(
            {
                "group_ids": [
                    Command.link(project_user_group.id),
                    Command.link(sale_manager_group.id),
                ]
            }
        )
        self.assertTrue(
            self.task_cow.with_user(self.user_projectuser).has_access("write")
        )
        with self.mockSMSGateway():
            self.task_cow.with_user(self.user_projectuser).write(
                {
                    "step_id": self.task_stage_with_sms.id,
                }
            )
        self.assertEqual(self.task_cow.step_id, self.task_stage_with_sms)
        self.assertSMSIapSent([])

        self.task_cow.write(
            {
                "partner_id": self.user_portal.partner_id.id,
                "step_id": self.project_cows.workflow_step_ids[0].id,
            }
        )
        with self.mockSMSGateway():
            self.task_cow.with_user(self.user_projectuser).write(
                {
                    "step_id": self.task_stage_with_sms.id,
                }
            )
        self.assertEqual(self.task_cow.step_id, self.task_stage_with_sms)
        self.assertSMSIapSent([self.user_portal.partner_id._phone_get_number().number])
