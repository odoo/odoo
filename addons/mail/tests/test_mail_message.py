# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.bus.tests.common import BusResult
from odoo.addons.mail.models import mail_message as mail_message_module
from odoo.addons.mail.tests import common
from odoo.exceptions import UserError
from odoo.tests import HttpCase, new_test_user, tagged, users

from unittest.mock import patch


@tagged("mail_message")
class TestMailMessage(common.MailCommon, HttpCase):

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

    def test_mail_message_read_inexisting(self):
        user = new_test_user(self.env, login="Bob", email="bob@test.com")
        inexisting_message = self.env['mail.message'].with_user(user).browse(-434264)
        self.assertFalse(inexisting_message.exists())
        self.assertTrue(inexisting_message.browse().has_access('read'))
        self.assertFalse(inexisting_message.has_access('read'))

    def test_mail_message_read_access(self):
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

    def test_mail_message_read_access_search_with_limit(self):
        ids = []
        ids += self._add_messages(self.env.company, "Accessible notes", count=5).ids
        ids += self._add_messages(self.company_2, "Inccessible notes", count=5).ids
        ids += self._add_messages(self.env.company, "Accessible notes", count=5).ids
        messages = (self.env["mail.message"]
            .with_user(self.user_employee)
            .with_context(allowed_company_ids=[self.env.company.id])
        ).browse(ids)
        accessible = messages._filtered_access('read')
        self.assertEqual(len(accessible), 10)
        domain = [('id', 'in', ids)]

        self.assertEqual(messages.search(domain, limit=100), accessible)
        self.assertEqual(messages.sudo().search(domain, limit=100), messages)

        Message = self.registry[messages._name]
        with (
            patch.object(mail_message_module, 'IN_MAX', 3),
            patch.object(Message, '_search', autospec=True, side_effect=Message._search) as search_func,
        ):
            self.assertEqual(messages.search(domain, limit=100), accessible)
            self.assertGreaterEqual(search_func.call_count, 4)

    def test_mail_message_read_access_read_group_with_limit(self):
        ids = []
        ids += self._add_messages(self.company_2, "Inccessible notes", count=5, subject="Subject 1").ids
        ids += self._add_messages(self.env.company, "Accessible notes", count=5, subject="Subject 2").ids
        messages = (self.env["mail.message"]
            .with_user(self.user_employee)
            .with_context(allowed_company_ids=[self.env.company.id])
        ).browse(ids)
        accessible = messages._filtered_access('read')
        self.assertEqual(len(accessible), 5)

        with patch.object(mail_message_module, 'MAX_SEARCH_LIMIT', 5):
            with self.assertRaisesRegex(UserError, "Please apply additional filters"):
                messages.formatted_read_group(
                    [("id", "in", ids)],
                    ["subject"],
                    ["id:count"],
                    limit=100,
                )

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

    @users("employee")
    def test_messaging_menu_initialize_counters(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        partner = self.env.user.partner_id
        values = {"model": "res.partner", "res_id": partner.id, "body": "Hey"}
        bookmarked = self.env["mail.message"].create(
            {**values, "bookmarked_partner_ids": [(4, partner.id)]},
        )
        notified = self.env["mail.message"].create({
            **values,
            "notification_ids": [(0, 0, {"res_partner_id": partner.id, "notification_type": "inbox"})],
        })
        self.env["mail.message"].create(values)
        data = self.make_jsonrpc_request(
            "/mail/store",
            {"fetch_params": [[
                "/mail/messaging_menu/initialize_counters",
                {"filter_id_by_tab_id_by_record_type": {
                    "mail.message": {"bookmark": None, "notification": "notification_unread"},
                }},
            ]]},
        )
        counter_ids_by_tab = {
            tab["id"]: tab["init_counter_ids"] for tab in data["MessagingMenuTab"]
        }
        self.assertEqual(counter_ids_by_tab["bookmark"], bookmarked.ids)
        self.assertEqual(counter_ids_by_tab["notification"], notified.ids)

    @users("employee")
    def test_messaging_menu_initialize_counters_channel(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        group = self.env["discuss.channel"].with_user(self.user_admin)._create_group(
            users_to=self.env.user,
        )
        group.message_post(body="Hey", message_type="comment")
        data = self.make_jsonrpc_request(
            "/mail/store",
            {"fetch_params": [[
                "/mail/messaging_menu/initialize_counters",
                {"filter_id_by_tab_id_by_record_type": {
                    "discuss.channel": {"chat": "chat_unread"},
                }},
            ]]},
        )
        counter_ids_by_tab = {
            tab["id"]: tab["init_counter_ids"] for tab in data["MessagingMenuTab"]
        }
        self.assertEqual(counter_ids_by_tab["chat"], group.ids)

    @users("employee")
    def test_messaging_menu_channel_tab(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        Channel = self.env["discuss.channel"].with_user(self.user_admin)
        pinned, needaction, other = Channel.create(
            [{"name": name, "channel_type": "channel"} for name in ("pinned", "needaction", "other")],
        )
        pinned._add_members(users=self.env.user)
        pinned.message_post(body="Hey", message_type="comment")
        self.env["mail.message"].sudo().create({
            "model": "discuss.channel",
            "res_id": needaction.id,
            "body": "Hey",
            "message_type": "comment",
            "notification_ids": [
                (0, 0, {"res_partner_id": self.env.user.partner_id.id, "notification_type": "inbox"}),
            ],
        })
        fetch_params = [
            ["/mail/messaging_menu/discuss.channel/load_more", {"tab_id": "channel", "limit": 30}],
            [
                "/mail/messaging_menu/initialize_counters",
                {"filter_id_by_tab_id_by_record_type": {"discuss.channel": {"channel": None}}},
            ],
        ]
        tab_channels = pinned | needaction
        data = self.make_jsonrpc_request("/mail/store", {"fetch_params": fetch_params})
        # only the channels of this test: the employee is also in the general channel
        test_ids = set((tab_channels | other).ids)
        loaded_ids = {channel["id"] for channel in data["discuss.channel"]}
        self.assertEqual(loaded_ids & test_ids, set(tab_channels.ids))
        counter_ids_by_tab = {
            tab["id"]: tab["init_counter_ids"] for tab in data["MessagingMenuTab"]
        }
        self.assertEqual(set(counter_ids_by_tab["channel"]) & test_ids, set(tab_channels.ids))
