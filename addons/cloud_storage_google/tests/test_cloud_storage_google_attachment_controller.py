# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re

import odoo
from odoo.tools.misc import file_open
from odoo.tests import Form
from odoo.addons.cloud_storage_google.tests.test_cloud_storage_google import (
    TestCloudStorageGoogleCommon,
)
from odoo.addons.mail.tests.test_attachment_controller import TestAttachmentControllerCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestCloudStorageAttachmentController(
    TestAttachmentControllerCommon, TestCloudStorageGoogleCommon
):
    def test_cloud_storage_google_attachment_upload(self):
        """Test uploading an attachment with google cloud storage."""
        thread = self.env["res.partner"].create({"name": "Test"})
        self.env["ir.config_parameter"].set_param("cloud_storage_provider", "google")
        self._authenticate_user(self.user_demo)

        with file_open("addons/web/__init__.py") as file:
            res = self.url_open(
                url="/mail/attachment/upload",
                data={
                    "csrf_token": odoo.http.Request.csrf_token(self),
                    "is_pending": True,
                    "thread_id": thread.id,
                    "thread_model": thread._name,
                    "cloud_storage": True,
                },
                files={"ufile": file},
            )
            res.raise_for_status()
            attachment = self.env["ir.attachment"].search([], order="id desc", limit=1)
            # ignore signature in url
            content = re.sub(
                r'"url": "https://storage\.googleapis\.com/.*?"',
                '"url": "[url]"',
                res.content.decode("utf-8"),
            )
            self.assertEqual(
                json.loads(content),
                {
                    "data": {
                        "ir.attachment": [
                            {
                                "access_token": False,
                                "checksum": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                                "create_date": odoo.fields.Datetime.to_string(
                                    attachment.create_date
                                ),
                                "filename": "__init__.py",
                                "id": attachment.id,
                                "mimetype": "text/x-python",
                                "name": "__init__.py",
                                "res_name": False,
                                "size": 0,
                                "thread": False,
                                "voice": False,
                                "type": "cloud_storage",
                                "url": "[url]",
                            }
                        ],
                    },
                    "upload_info": {"method": "PUT", "response_status": 200, "url": "[url]"},
                },
            )

    def test_mail_composer_cloud_storage_attachment(self):
        """Ensure cloud attachments are converted to links in outgoing emails."""
        self.env["ir.config_parameter"].set_param("cloud_storage_provider", "google")
        self.env["ir.config_parameter"].set_param("cloud_storage_min_file_size", 1)

        partner = self.env["res.partner"].create({"name": "Cloud Test Partner", "email": "cloud@test.com"})
        cloud_attachment = self.env["ir.attachment"].create({
            "name": "cloud_attachment.txt",
            "type": "cloud_storage",
            "url": "https://storage.googleapis.com/fakebucket/cloud_attachment.txt",
            "res_model": "res.partner",
            "res_id": partner.id,
            "mimetype": "text/plain",
        })

        composer_form = Form(self.env['mail.compose.message'].with_context(
            default_model='res.partner',
            default_res_ids=[partner.id],
            default_composition_mode='comment',
            default_partner_ids=[partner.id],
        ))
        composer_form.body = "<p>Hello</p>"
        composer_form.attachment_ids.add(cloud_attachment)
        composer = composer_form.save()

        with self.mock_mail_gateway(mail_unlink_sent=False):
            composer._action_send_mail()
        sent_mail = next((m for m in self._mails if 'cloud_attachment.txt' in m['body']), None)
        self.assertIsNotNone(sent_mail)
        self.assertIn(self.env['ir.qweb']._render('mail.mail_attachment_links', {'attachments': cloud_attachment}), sent_mail['body'])
