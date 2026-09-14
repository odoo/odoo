from markupsafe import Markup

from odoo import Command
from odoo.modules.module import get_module_path, load_script
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user

from odoo.addons.mail.tests.common import MockEmail

CREDENTIAL_MARKERS = ("token=", "hash=")


@tagged("post_install", "-at_install", "portal")
class TestPortalShareInvitation(MockEmail, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "auth_signup.invitation_scope", "b2c"
        )
        cls.record = cls.env["mail.test.portal"].create({"name": "Shared record"})
        cls.colleague = new_test_user(
            cls.env, "share_colleague", groups="base.group_user"
        )
        cls.portal_user = new_test_user(
            cls.env,
            "share_portal",
            groups="base.group_portal",
            email="share.portal@example.com",
        )
        cls.customer = cls.env["res.partner"].create(
            {"name": "Share Customer", "email": "share.customer@example.com"}
        )

    def _share(self, partners):
        wizard = self.env["portal.share"].create(
            {
                "res_model": self.record._name,
                "res_id": self.record.id,
                "partner_ids": [Command.set(partners.ids)],
            }
        )
        with self.mock_mail_gateway():
            wizard.action_send_mail()

    def _record_messages(self, user):
        return (
            self.env["mail.message"]
            .with_user(user)
            .search(
                [("model", "=", self.record._name), ("res_id", "=", self.record.id)]
            )
        )

    def _invitation(self, partner, marker):
        return self.env["mail.message"].search(
            [
                ("model", "=", self.record._name),
                ("res_id", "=", self.record.id),
                ("partner_ids", "in", partner.ids),
                ("body", "like", marker),
            ]
        )

    def test_invitation_links_stay_out_of_the_document_thread(self):
        self._share(self.portal_user.partner_id | self.customer)

        readable = self._record_messages(self.colleague)
        self.assertTrue(readable)
        for message in readable:
            for marker in CREDENTIAL_MARKERS:
                self.assertNotIn(marker, str(message.body))
        for message in self.record.message_ids:
            for marker in CREDENTIAL_MARKERS:
                self.assertNotIn(marker, str(message.body))

        signup = self._invitation(self.customer, "/web/signup?")
        self.assertEqual(signup.message_type, "user_notification")
        self.assertIn("token=", str(signup.body))
        public = self._invitation(self.portal_user.partner_id, "hash=")
        self.assertEqual(public.message_type, "user_notification")
        self.assertEqual(self._record_messages(self.portal_user), public)

        for partner, marker in (
            (self.customer, "/web/signup?"),
            (self.portal_user.partner_id, "hash="),
        ):
            mail = self._new_mails.filtered(lambda m, p=partner: p in m.recipient_ids)
            self.assertEqual(len(mail), 1)
            self.assertIn(marker, str(mail.body_html))

    def test_one_credential_free_note_records_the_share(self):
        self._share(self.portal_user.partner_id | self.customer)

        notes = self.record.message_ids.filtered(
            lambda message: self.customer.name in str(message.body)
        )
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes.subtype_id, self.env.ref("mail.mt_note"))
        self.assertIn(self.portal_user.partner_id.name, str(notes.body))
        self.assertFalse(notes.partner_ids)
        self.assertIn(notes, self._record_messages(self.colleague))


@tagged("post_install", "-at_install", "portal")
class TestPortalShareInvitationMigration(MockEmail, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.script = load_script(
            f"{get_module_path('portal')}/migrations/1.1/post-migrate.py",
            "portal_1_1_post_migrate",
        )
        cls.record = cls.env["mail.test.portal"].create({"name": "Shared before"})
        cls.customer = cls.env["res.partner"].create(
            {"name": "Earlier Customer", "email": "earlier.customer@example.com"}
        )

    def _note(self, href, partners):
        with self.mock_mail_gateway():
            return self.record.message_post(
                body=Markup('<p><a href="%s">Open</a></p>') % href,
                subtype_xmlid="mail.mt_note",
                partner_ids=partners.ids,
            )

    def test_posted_invitations_become_recipient_notifications(self):
        signup = self._note(
            "https://example.com/web/signup?db=x&token=abc&redirect=%2Fmail%2Fview",
            self.customer,
        )
        public = self._note(
            "https://example.com/mail/view?model=x&res_id=1&pid=7&hash=abc",
            self.customer,
        )
        unaddressed = self._note(
            "https://example.com/mail/view?model=x&res_id=1&pid=7&hash=abc",
            self.env["res.partner"],
        )
        plain = self._note("https://example.com/my/orders", self.customer)
        self.env.flush_all()

        self.script.migrate(self.env.cr, "19.0.1.0")
        self.env.invalidate_all()

        self.assertEqual(signup.message_type, "user_notification")
        self.assertEqual(public.message_type, "user_notification")
        self.assertEqual(unaddressed.message_type, "notification")
        self.assertEqual(plain.message_type, "notification")
        self.assertEqual(signup.partner_ids, self.customer)

    def test_fresh_install_is_noop(self):
        signup = self._note(
            "https://example.com/web/signup?db=x&token=abc", self.customer
        )
        self.env.flush_all()
        self.script.migrate(self.env.cr, None)
        self.env.invalidate_all()
        self.assertEqual(signup.message_type, "notification")
