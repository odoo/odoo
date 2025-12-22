from odoo.addons.mail.tests.common import MailCommon
from odoo.exceptions import AccessError


class TestDiscussAttachment(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channel = cls.env["discuss.channel"]._create_channel(name="Channel", group_id=None)
        cls.channel._add_members(users=cls.user_admin | cls.user_employee)

    def _create_attachment(self, author):
        attachment = self.env["ir.attachment"].create({
            "name": "Attachment",
            "res_model": "discuss.channel",
            "res_id": self.channel.id
        })
        self.env["mail.message"].create({
            "model": "discuss.channel",
            "res_id": self.channel.id,
            "author_id": author.partner_id.id,
            "attachment_ids": attachment.ids,
        })
        return attachment

    def _execute_subtest_delete(self, user, author, allowed, channel_role=None):
        with self.subTest(user=user.name, author=author.name, channel_role=channel_role):
            attachment = self._create_attachment(author)
            if channel_role:
                self.channel.channel_member_ids.filtered(
                    lambda m: m.partner_id == user.partner_id
                ).channel_role = channel_role
            if allowed:
                attachment.with_user(user).unlink()
                self.assertFalse(attachment.exists())
            else:
                with self.assertRaises(AccessError):
                    attachment.with_user(user).unlink()

    def test_delete_attachment(self):
        self._execute_subtest_delete(self.user_employee, author=self.user_employee, allowed=True)
        self._execute_subtest_delete(self.user_employee, author=self.user_admin, allowed=False)
        self._execute_subtest_delete(self.user_employee, author=self.user_admin, allowed=True, channel_role="admin")
        self._execute_subtest_delete(self.user_employee, author=self.user_admin, allowed=True, channel_role="owner")
        self._execute_subtest_delete(self.user_admin, author=self.user_employee, allowed=True)
