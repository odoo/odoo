import odoo
from odoo.addons.mail.tests.common_controllers import MailControllerAttachmentCommon


@odoo.tests.tagged("-at_install", "post_install", "mail_controller")
class TestPortalAttachmentController(MailControllerAttachmentCommon):

    def test_attachment_upload_portal(self):
        """Test access to upload an attachment on portal"""
        record = self.env["mail.test.portal.no.partner"].create({"name": "Test"})
        token, bad_token, sign, bad_sign, _ = self._get_sign_token_params(record)
        self._execute_subtests(
            record,
            (
                (self.user_public, False),
                (self.user_public, True, token),
                (self.user_public, True, sign),
                (self.guest, False),
                (self.guest, True, token),
                (self.guest, True, sign),
                (self.user_portal, False),
                (self.user_portal, False, bad_token),
                (self.user_portal, False, bad_sign),
                (self.user_portal, True, token),
                (self.user_portal, True, sign),
                (self.user_employee, True),
                (self.user_employee, True, bad_token),
                (self.user_employee, True, bad_sign),
                (self.user_employee, True, token),
                (self.user_employee, True, sign),
                (self.user_admin, True),
                (self.user_admin, True, bad_token),
                (self.user_admin, True, bad_sign),
                (self.user_admin, True, token),
                (self.user_admin, True, sign),
            ),
        )

    def test_delete_attachment_as_internal_with_token(self):
        record = self.env["mail.test.portal"].create(
            {"name": "Test", "partner_id": self.partner_portal.id}
        )
        token_param = {"token": record._portal_ensure_token()}
        self._authenticate_pseudo_user(self.user_portal)
        attachment_id = self._upload_attachment(record, token_param)
        attachment = self.env["ir.attachment"].sudo().search([("id", "=", attachment_id)])
        message = record.message_post(
            body="hello!", author_id=self.partner_portal.id, attachment_ids=attachment.ids
        )
        self.assertTrue(message.attachment_ids)
        self._authenticate_pseudo_user(self.user_employee)
        with self.assertRaises(odoo.tests.common.JsonRpcException) as exc:
            self._delete_attachment(attachment, {})
        self.assertEqual(exc.exception.args[0], "werkzeug.exceptions.NotFound")
        self._delete_attachment(attachment, token_param)
