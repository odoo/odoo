# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo.addons.bus.tests.common import BusResult
from odoo.exceptions import AccessError
from odoo.addons.mail.tests import common
from odoo.tests import HttpCase, new_test_user, tagged, users


@tagged("mail_message", "security")
class TestMailMessage(common.MailCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.random_message = cls.partner_admin.message_post(body='Just for reference')

        cls.test_internal_record = cls.env['res.partner'].create({'name': 'Test Internal'})
        cls.test_public_record = cls.env['discuss.channel'].create({
            'channel_type': 'channel',
            'group_public_id': False,
            'name': 'Test Public',
        })
        cls.public_message = cls.test_public_record.with_user(cls.user_employee).message_post(
            body='For Reference',
            message_type='comment',
            subtype_id=cls.env.ref('mail.mt_comment').id,
        )

        html_ref = f"""
<a href="/web#model=mail.message&id={cls.random_message.id}" class="o_message_redirect o_mail_notification"
    data-oe-model="mail.message" data-oe-id="{cls.random_message.id}">View Message</a>
<a href="/web#model=mail.message&id={cls.public_message.id}" class="o_message_redirect o_mail_notification"
    data-oe-model="mail.message" data-oe-id="{cls.public_message.id}">View Message</a>"""
        cls.test_internal_message = cls.test_internal_record.with_user(cls.user_employee).message_post(
            body=Markup(f'<div>Test Body {html_ref}</div>'),
            message_type='comment',
            subtype_id=cls.env.ref('mail.mt_comment').id,
        )
        cls.test_public_message = cls.test_public_record.with_user(cls.user_employee).message_post(
            body=Markup(f'<div>Test Body {html_ref}</div>'),
            message_type='comment',
            subtype_id=cls.env.ref('mail.mt_comment').id,
        )

    def test_access_read_inexisting(self):
        user = new_test_user(self.env, login="Bob", email="bob@test.com")
        inexisting_message = self.env['mail.message'].with_user(user).browse(-434264)
        self.assertFalse(inexisting_message.exists())
        self.assertTrue(inexisting_message.browse().has_access('read'))
        self.assertFalse(inexisting_message.has_access('read'))

    def test_access_read_mc(self):
        self.env['res.company'].invalidate_model(['name'])
        message_c1 = self._add_messages(self.env.company, "Company Note 1", author=self.user_employee.partner_id)
        message_c2 = self._add_messages(self.company_2, "Company Note 2", author=self.user_employee_c2.partner_id)
        message_not_author_but_in_to = self._add_messages(
            self.company_2, "Company Note 3",
            author=self.user_employee_c2.partner_id, partner_ids=self.user_employee.partner_id)
        message_not_author_but_in_cc = self._add_messages(
            self.company_2, "Company Note 4",
            author=self.user_employee_c2.partner_id, partner_cc_ids=self.user_employee.partner_id)
        message_not_author_nor_in_recipients = self._add_messages(
            self.company_2, "Company Note 5",
            author=self.user_employee_c2.partner_id, partner_cc_ids=self.user_employee_c3.partner_id)
        search_result = (
            self.env["mail.message"]
            .with_context(allowed_company_ids=[self.env.company.id])
            .with_user(self.user_employee)
            .search([("model", "=", "res.company")])
        )
        self.assertIn(message_c1, search_result)
        self.assertNotIn(message_c2, search_result)
        self.assertIn(message_not_author_but_in_to, search_result)
        self.assertIn(message_not_author_but_in_cc, search_result)
        self.assertNotIn(message_not_author_nor_in_recipients, search_result)

    def test_access_read_public(self):
        """ Check public access, notably with 2many fields / sudo-ed environment """
        PublicMessage = self.env['mail.message'].with_user(self.user_public)

        # internal message: cannot read except when sudo-ed
        with self.assertRaises(AccessError):
            PublicMessage.browse(self.test_internal_message.id).read(['id'])
        message_internal_su = PublicMessage.sudo().browse(self.test_internal_message.id)
        self.assertFalse(message_internal_su.is_current_user_or_guest_author)
        for access_field in ('res_access_read', 'res_access_write', 'res_access_create', 'res_access_unlink'):
            self.assertFalse(message_internal_su[access_field])
        self.assertEqual(
            message_internal_su.linked_message_ids, self.public_message,
            "Only messages accessible to user are linked, even as sudo")
        self.assertFalse(message_internal_su.message_link_preview_ids)

        # public message: can read
        message_public = PublicMessage.browse(self.test_public_message.id)
        self.assertFalse(message_public.is_current_user_or_guest_author)
        self.assertEqual(
            message_public.linked_message_ids, self.public_message,
            "Only messages accessible to user are linked")
        with self.assertRaises(AccessError):  # field limited to admins
            self.assertFalse(message_public.message_link_preview_ids)
        with self.assertRaises(AccessError):  # field limited to admins
            self.assertFalse(message_public.reaction_ids)

    @users("employee")
    def test_can_star_message_without_write_access(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        message = self.env["mail.message"].sudo().create({
            "author_id": self.partner_admin.id,
            "model": "res.partner",
            "res_id": self.partner_admin.id,
            "body": "Hey this is me!",
        })
        message = message.sudo(False)
        self.env.user.group_ids -= self.env.ref("base.group_partner_manager")
        self.assertFalse(message.has_access("write"))
        self.make_jsonrpc_request(
            "/mail/store", {"fetch_params": [["add_bookmark", {"message_id": message.id}]]},
        )
        self.assertIn(self.env.user.partner_id, message.bookmarked_partner_ids)
        self.make_jsonrpc_request("/mail/store", {"fetch_params": ["remove_all_bookmarks"]})
        self.assertNotIn(self.env.user.partner_id, message.bookmarked_partner_ids)

    @users("employee")
    def test_unlink_failure_message_notify_author(self):
        recipient = new_test_user(self.env(su=True), login="Bob", email="invalid_email_addr")
        with self.mock_mail_gateway():
            message = self.env.user.partner_id.message_post(
                body="Hello world!", partner_ids=recipient.partner_id.ids
            )
        self.assertEqual(message.notification_ids.failure_type, "mail_email_invalid")
        self.assertEqual(message.notification_ids.res_partner_id, recipient.partner_id)
        self.assertEqual(message.notification_ids.author_id, self.env.user.partner_id)
        with self.assertBus(
            [
                BusResult(recipient, "mail.message/delete", {"message_ids": [message.id]}),
                BusResult(self.env.user, "mail.message/delete", {"message_ids": [message.id]}),
            ],
        ):
            message.unlink()
