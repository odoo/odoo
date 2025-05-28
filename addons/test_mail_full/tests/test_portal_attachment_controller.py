# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.test_attachment_controller import TestAttachmentControllerCommon


@odoo.tests.tagged("-at_install", "post_install")
class TestPortalAttachmentController(TestAttachmentControllerCommon):
    def test_attachment_upload_portal(self):
        """Test access to upload an attachment on portal"""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token = record._portal_ensure_token()
        partner = self.env["res.partner"].create({"name": "Sign Partner"})
        _hash = record._sign_token(partner.id)
        token_param = {"token": token}
        incorrect_token_param = {"token": "incorrect token"}
        hash_pid_param = {"hash": _hash, "pid": partner.id}
        incorrect_hash_pid_param = {"hash": "incorrect hash", "pid": partner.id}
        self._execute_subtests(
            record,
            (
                (self.user_public, False),
                (self.user_public, True, token_param),
                (self.user_public, True, hash_pid_param),
                (self.guest, False),
                (self.guest, True, token_param),
                (self.guest, True, hash_pid_param),
                (self.user_portal, False),
                (self.user_portal, False, incorrect_token_param),
                (self.user_portal, False, incorrect_hash_pid_param),
                (self.user_portal, True, token_param),
                (self.user_portal, True, hash_pid_param),
                (self.user_employee, True),
                (self.user_employee, True, token_param),
                (self.user_employee, True, hash_pid_param),
                (self.user_demo, True),
                (self.user_demo, True, token_param),
                (self.user_demo, True, hash_pid_param),
                (self.user_admin, True),
                (self.user_admin, True, incorrect_token_param),
                (self.user_admin, True, incorrect_hash_pid_param),
                (self.user_admin, True, token_param),
                (self.user_admin, True, hash_pid_param),
            ),
        )

    def test_delete_attachment_as_internal_with_token(self):
        record = self.env["mail.test.portal"].create(
            {"name": "Test", "partner_id": self.partner_portal.id}
        )
        token_param = {"token": record._portal_ensure_token()}
        self._authenticate_user(self.user_portal)
        attachment_id = self._upload_attachment(record.id, "mail.test.portal", token_param)
        attachment = self.env["ir.attachment"].sudo().search([("id", "=", attachment_id)])
        message = record.message_post(
            body="hello!", author_id=self.partner_portal.id, attachment_ids=attachment.ids
        )
        self.assertTrue(message.attachment_ids)
        self._authenticate_user(self.user_employee)
        with self.assertRaises(odoo.tests.common.JsonRpcException) as exc:
            self._delete_attachment(attachment, {})
        self.assertEqual(exc.exception.args[0], "werkzeug.exceptions.NotFound")
        self._delete_attachment(attachment, token_param)
