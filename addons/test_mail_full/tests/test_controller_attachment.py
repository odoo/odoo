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

    def test_mail_attachment_company(self):
        self.authenticate(self.user_admin.login, self.user_admin.login)
        record = self.env['mail.test.attachment.company'].create({})

        self.env.user.company_ids = self.company_2 | self.company_3
        self.opener.cookies['cids'] = f'{self.company_2.id}-{self.company_3.id}'

        attachment_id = self._upload_attachment(record, {})
        attachment = self.env['ir.attachment'].sudo().browse(attachment_id)
        self.assertEqual(attachment.company_id, self.company_2, "Attachment should be assigned to company_2")

        record.company_id = self.company_3
        attachment_id = self._upload_attachment(record, {})
        attachment = self.env['ir.attachment'].sudo().browse(attachment_id)
        self.assertEqual(attachment.company_id, self.company_3, "Attachment should be assigned to company_3")
