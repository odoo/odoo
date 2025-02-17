# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from requests.exceptions import HTTPError

import odoo
from odoo.tools import file_open, mute_logger
from odoo.addons.mail.tests.test_controller_common import TestControllerCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestAttachmentControllerCommon(TestControllerCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def _execute_subtests(self, record, subtests):
        for data_user, allowed, *args in subtests:
            route_kw = args[0] if args else {}
            user = data_user if data_user._name == "res.users" else self.user_public
            guest = data_user if data_user._name == "mail.guest" else self.env["mail.guest"]
            self._authenticate_user(user=user, guest=guest)
            with self.subTest(record=record, user=user.name, guest=guest.name, route_kw=route_kw):
                if allowed:
                    attachment_id = self._upload_attachment(record.id, record._name, route_kw)
                    attachment = (
                        self.env["ir.attachment"].sudo().search([("id", "=", attachment_id)])
                    )
                    self.assertTrue(attachment)
                    self._delete_attachment(attachment, route_kw)
                    self.assertFalse(attachment.exists())
                else:
                    with self.assertRaises(
                        HTTPError, msg="upload attachment should raise NotFound"
                    ):
                        self._upload_attachment(record.id, record._name, route_kw)

    def _upload_attachment(self, thread_id, thread_model, route_kw):
        with mute_logger("odoo.http"), file_open("addons/web/__init__.py") as file:
            res = self.url_open(
                url="/mail/attachment/upload",
                data={
                    "csrf_token": odoo.http.Request.csrf_token(self),
                    "is_pending": True,
                    "thread_id": thread_id,
                    "thread_model": thread_model,
                    **route_kw,
                },
                files={"ufile": file},
            )
            res.raise_for_status()
            return json.loads(res.content.decode("utf-8"))["data"]["ir.attachment"][0]["id"]

    def _delete_attachment(self, attachment, route_kw):
        self.make_jsonrpc_request(
            route="/mail/attachment/delete",
            params={
                "attachment_id": attachment["id"],
                "access_token": attachment["access_token"],
                **route_kw,
            },
        )


@odoo.tests.tagged("-at_install", "post_install")
class TestAttachmentController(TestAttachmentControllerCommon):
    def test_attachment_partner(self):
        """Test access to upload an attachment on a non channel thread"""
        record = self.user_demo.partner_id
        self._execute_subtests(
            record,
            (
                (self.guest, False),
                (self.user_admin, True),
                (self.user_demo, True),
                (self.user_employee, False),
                (self.user_portal, False),
                (self.user_public, False),
            ),
        )

    def test_send_attachment_without_body(self):
        self.start_tour("/odoo/discuss", "create_thread_for_attachment_without_body",login="admin")
