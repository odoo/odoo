from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import TransactionCase


class TestChannelAutoSubscribe(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base.group_user")
        cls.group_admin = cls.env.ref("base.group_system")
        cls.user_admin = cls.env.ref('base.user_admin')
        cls.company_a, cls.company_b = cls.env["res.company"].create([
            {"name": "Company A"}, {"name": "Company B"},
        ])
        cls.user_a = mail_new_test_user(
            cls.env,
            login='User A',
            company_id=cls.company_a.id,
            groups="base.group_system",
        )
        cls.user_b = mail_new_test_user(
            cls.env,
            login='User B',
            company_id=cls.company_b.id,
            groups="base.group_user",
        )
        cls.both_partners = cls.user_a.partner_id | cls.user_b.partner_id
        cls.all_partners = cls.user_admin.partner_id | cls.both_partners

    def test_channel_auto_subscribe_all_users(self):
        channel = self.env["discuss.channel"].create({
            "name": "Test all auto subscribe",
            "auto_subscribe": True,
        })
        self.assertEqual(channel.channel_partner_ids, self.all_partners)

    def test_channel_company_auto_subscribe(self):
        channel = self.env["discuss.channel"].create({
            "name": "Test company auto subscribe",
            "auto_subscribe": True,
            "auto_subscribe_company_ids": [Command.link(self.company_a.id)],
        })
        self.assertEqual(channel.channel_partner_ids, self.user_a.partner_id)

        channel.write({"auto_subscribe_company_ids": [Command.link(self.company_b.id)]})
        self.assertEqual(
            channel.channel_partner_ids, self.both_partners,
        )

    def test_channel_group_auto_subscribe(self):
        channel = self.env["discuss.channel"].create({
            "name": "Test group auto subscribe",
            "auto_subscribe": True,
            "group_ids": [Command.link(self.group_admin.id)],
        })
        self.assertEqual(
            channel.channel_partner_ids, self.user_admin.partner_id | self.user_a.partner_id,
        )
        channel.write({"group_ids": [Command.link(self.group_user.id)]})
        self.assertEqual(channel.channel_partner_ids, self.all_partners)

    def test_channel_company_group_auto_subscribe(self):
        channel = self.env["discuss.channel"].create({
            "name": "Test company group auto subscribe",
            "auto_subscribe": True,
            "auto_subscribe_company_ids": [Command.link(self.company_a.id)],
            "group_ids": [Command.link(self.group_user.id)],
        })
        # only users of 'Company A' who belong to group 'Role / User' should be subscribed.
        self.assertEqual(
            channel.channel_partner_ids, self.user_a.partner_id,
        )

    def test_user_auto_subscribed_only_once(self):
        channel = self.env["discuss.channel"].create({
            "name": "Test user auto subscribed only once",
            "auto_subscribe": True,
            "group_ids": [Command.link(self.group_admin.id)],
        })
        self.assertEqual(
            channel.channel_partner_ids, self.user_admin.partner_id | self.user_a.partner_id,
        )
        # 'User A' leaves the channel
        channel.with_user(self.user_a).action_unfollow()
        self.assertEqual(
            channel.channel_partner_ids, self.user_admin.partner_id,
        )
        channel.write({"group_ids": [Command.link(self.group_user.id)]})
        self.assertEqual(
            channel.channel_partner_ids, self.user_admin.partner_id | self.user_b.partner_id,
        )
        self.assertNotIn(self.user_a.partner_id, channel.channel_partner_ids)
