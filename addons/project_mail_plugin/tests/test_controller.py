# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import base64
from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.mail_plugin.tests.common import TestMailPluginControllerCommon, mock_auth_method_outlook


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestMailPluginProjectController(TestMailPluginControllerCommon):
    def test_user_lang(self):
        """Verify that we translate field in the user language."""
        self.env["res.lang"]._activate_lang("fr_BE")
        self.env["res.lang"]._activate_lang("es_ES")
        project = self.env["project.project"].create({"name": "Test Mail Plugin"})
        project.with_context(lang="fr_BE").name = "[FR] Test Mail Plugin"
        self.assertEqual(project.name, "Test Mail Plugin")

        for lang, expected in (
            (False, "Test Mail Plugin"),
            ("en_US", "Test Mail Plugin"),
            ("fr_BE", "[FR] Test Mail Plugin"),
            ("es_ES", "Test Mail Plugin"),  # no translation
        ):
            self.user_test.lang = lang

            data = {
                "id": 0,
                "jsonrpc": "2.0",
                "method": "call",
                "params": {"query": "Test Mail Plugin"},
            }

            with patch.object(
                type(self.env["res.users.apikeys"]),
                "_check_credentials",
                new=lambda *args, **kwargs: self.user_test.id,
            ):
                result = self.url_open(
                    "/mail_plugin/search_records/project.project",
                    data=json.dumps(data).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "dummy",
                    },
                )

            result, total_count = result.json().get("result")
            self.assertEqual(len(result), 1)
            self.assertEqual(total_count, 1)
            self.assertEqual(result[0]["id"], project.id)
            self.assertEqual(result[0]["name"], expected)

    @mock_auth_method_outlook('employee')
    def test_project_task_create_nameless_attachment(self):
        self.user_test.group_ids |= self.env.ref('project.group_project_manager')

        # Create a test project required by the endpoint
        project = self.env['project.project'].create({
            'name': 'Test Project',
        })

        image_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
            'AAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )
        image_name = 'image.png'

        # Create contacts
        partner1 = self.env['res.partner'].create({
            'name': 'Named Image Partner',
            'email': 'named.image@example.com',
        })

        partner2 = self.env['res.partner'].create({
            'name': 'Nameless Image Partner',
            'email': 'nameless.image@example.com',
        })

        # Control Case: Named Attachment
        named_params = {
            'email_subject': 'Named Attachment Task Test',
            'email_body': '<p>Body with inline image</p>',
            'project_id': project.id,
            'partner_id': partner1.id,
            'partner_email': partner1.email,
            'partner_name': partner1.name,
            'attachments': [[
                image_name,
                base64.b64encode(image_data).decode('utf-8'),
            ]],
        }

        named_result = self.make_jsonrpc_request(
            route='/mail_plugin/task/create',
            params=named_params,
        )

        task_id = named_result.get('id') or named_result.get('task_id')
        self.assertTrue(task_id, msg="Task was not created successfully for named attachments.")

        named_attachment = self.env['ir.attachment'].search([
            ('res_model', '=', 'project.task'),
            ('res_id', '=', task_id),
        ], limit=1)

        self.assertTrue(named_attachment.exists(), msg="Attachment record was not found.")
        self.assertEqual(named_attachment.name, image_name)

        # Regression Case: Nameless Attachments (name is False)
        nameless_params = {
            'email_subject': 'Nameless Attachment Task Test',
            'email_body': '<p>Body with inline image</p>',
            'project_id': project.id,
            'partner_id': partner2.id,
            'partner_email': partner2.email,
            'partner_name': partner2.name,
            'attachments': [
                [False, base64.b64encode(image_data).decode('utf-8')],
                [False, base64.b64encode(image_data).decode('utf-8')],
            ],
        }

        nameless_result = self.make_jsonrpc_request(
            route='/mail_plugin/task/create',
            params=nameless_params,
        )

        nameless_task_id = nameless_result.get('id') or nameless_result.get('task_id')
        self.assertTrue(nameless_task_id, msg="Task was not created successfully for nameless attachments.")

        nameless_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'project.task'),
            ('res_id', '=', nameless_task_id),
        ])

        self.assertEqual(len(nameless_attachments), 2, msg="Expected 2 attachments to be created.")
        for nameless_attachment in nameless_attachments:
            self.assertTrue(nameless_attachment.exists())
            self.assertTrue(bool(nameless_attachment.name), msg="Attachment name is empty or False.")
