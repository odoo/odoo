# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.bus.tests.common import BusResult
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
class TestAttachmentController(MailControllerAttachmentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        admin_record, readonly_record = cls.env["mail.test.access"].create(
            [
                {"access": "admin", "name": "Admin"},
                {"access": "internal_ro", "name": "Read only"},
            ],
        )
        cls.admin_attachment, cls.deleted_attachment, cls.readonly_attachment = cls.env[
            "ir.attachment"
        ].create(
            [
                {"name": "Admin", "res_id": admin_record.id, "res_model": admin_record._name},
                {"name": "Deleted"},
                {
                    "name": "Read only",
                    "res_id": readonly_record.id,
                    "res_model": readonly_record._name,
                },
            ],
        )
        cls.deleted_attachment.unlink()
        channel = cls.env["discuss.channel"]._create_channel(name="Channel", group_id=None)
        channel._add_members(guests=cls.guest)
        cls.channel_attachment = cls.env["ir.attachment"].create(
            {"name": "Channel", "res_id": channel.id, "res_model": channel._name},
        )
        channel.message_post(attachment_ids=cls.channel_attachment.ids)

    def test_independent_attachment_delete(self):
        """Test access to delete an attachment whether or not limited `ownership_token` is sent"""
        self._execute_subtests_delete(self.all_users, token=True, allowed=True)
        self._execute_subtests_delete(self.user_admin, token=False, allowed=True)
        self._execute_subtests_delete(
            (self.guest, self.user_employee, self.user_portal, self.user_public),
            token=False,
            allowed=False,
        )

    def test_attachment_delete_linked_to_thread(self):
        """Test access to delete an attachment associated with a thread
        whether or not limited `ownership_token` is sent"""
        thread = self.env["mail.test.simple"].create({"name": "Test"})
        self._execute_subtests_delete(self.all_users, token=True, allowed=True, thread=thread)
        self._execute_subtests_delete(
            (self.user_admin, self.user_employee),
            token=False,
            allowed=True,
            thread=thread,
        )
        self._execute_subtests_delete(
            (self.guest, self.user_portal, self.user_public),
            token=False,
            allowed=False,
            thread=thread,
        )

    def test_attachment_delete_not_found(self):
        """Test a 404 notifies the user or guest to remove an attachment they cannot read,
        but not one they can read without being allowed to delete it."""
        for pseudo_user, attachment, channels in (
            (self.user_employee, self.admin_attachment, [self.user_employee]),
            (self.user_employee, self.deleted_attachment, [self.user_employee]),
            (self.user_employee, self.readonly_attachment, []),
            (self.guest, self.deleted_attachment, [self.guest]),
            (self.guest, self.channel_attachment, []),
        ):
            self._authenticate_pseudo_user(pseudo_user)
            notifications = [
                BusResult(channel, "ir.attachment/delete", {"id": attachment.id})
                for channel in channels
            ]
            with (
                self.subTest(user=pseudo_user.name, attachment_id=attachment.id),
                self.assertBus(notifications),
            ):
                res = self.url_open(
                    "/mail/attachment/delete",
                    json={"params": {"attachment_id": attachment.id}},
                )
                self.assertEqual(res.json()["error"]["code"], 404)

    def test_upload_multi_company(self):
        record = self.user_employee.partner_id
        record.company_id = self.user_employee.company_id
        self.authenticate(self.user_admin.login, self.user_admin.login)
        self.assertTrue(record.company_id)  # Ensure the thread has a company
        test_cases = [
            ({}, self.user_employee.company_id),
            (
                {
                    "cookies": {
                        "cids": f"{self.company_2.id}-{self.company_3.id}",
                    },
                },
                self.company_2,
            ),
            (
                {
                    "cookies": {
                        "cids": f"{self.company_2.id}-{self.user_admin.company_id.id}",
                    },
                },
                self.user_admin.company_id,
            ),
        ]
        for kwargs, expected_company in test_cases:
            with self.subTest(expected_company=expected_company):
                record.company_id = False if kwargs else record.company_id
                attachment = self.env["ir.attachment"].browse(
                    self._upload_attachment(record, kwargs)
                )
                self.assertEqual(attachment.company_id, expected_company)

    def test_delete_non_comment_message_attachment(self):
        msg = self.env["mail.message"].with_user(self.user_employee).create({
            "message_type": "notification",
            "body": 'taratata <img src="data:image/png;base64,iV/+OkI=" width="2"> <img src="data:image/png;base64,iV/+OkI=" width="2">',
            "model": "res.partner",
            "res_id": self.partner_admin.id,
        })

        self.assertEqual(len(msg.attachment_ids), 1)
        attachment = msg.attachment_ids[0]
        self.make_jsonrpc_request("/mail/attachment/delete", params={
            "attachment_id": attachment.id,
            "access_token": attachment._get_ownership_token()
        })
        self.assertFalse(msg.attachment_ids)
