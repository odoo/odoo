import json
import re

import odoo
from odoo.tools.misc import file_open
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.cloud_storage_google.tests.test_cloud_storage_google import TestCloudStorageGoogleCommon


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
class TestCloudStorageAttachmentController(HttpCaseWithUserDemo, TestCloudStorageGoogleCommon):
    def test_cloud_storage_google_attachment_upload(self):
        """Test uploading an attachment with google cloud storage."""
        thread = self.env["res.partner"].create({"name": "Test"})
        self.env["ir.config_parameter"].set_param("cloud_storage_provider", "google")
        self.authenticate(self.user_demo.login, self.user_demo.login)

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
                                "id": attachment.id,
                                "mimetype": "text/x-python",
                                "name": "__init__.py",
                                "res_name": False,
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
