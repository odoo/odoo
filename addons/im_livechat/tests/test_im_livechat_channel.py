# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon
from odoo.addons.im_livechat.tests.test_get_operator import TestGetOperator
from odoo.fields import Command, Datetime


class TestImLivechatChannel(TestImLivechatCommon, TestGetOperator):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_mail_common()
        cls._setup_livechat_common()
        cls.diana_agent = new_test_user(
            cls.env,
            "diana_agent",
            groups="im_livechat.im_livechat_group_user",
        )
        cls.laura_manager = new_test_user(
            cls.env,
            "laura_manager",
            groups="im_livechat.im_livechat_group_manager",
        )

    def test_user_cant_join_livechat_channel(self):
        with self.assertRaises(AccessError):
            self.livechat_channel.with_user(self.user_employee).action_join()

    def test_operator_join_leave_livechat_channel(self):
        self.assertNotIn(self.diana_agent, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(self.diana_agent).action_join()
        self.assertIn(self.diana_agent, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(self.diana_agent).action_quit()
        self.assertNotIn(self.diana_agent, self.livechat_channel.user_ids)

    def test_leave_livechat_channels_when_operator_access_revoked(self):
        self.assertNotIn(self.diana_agent, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(self.diana_agent).action_join()
        self.assertIn(self.diana_agent, self.livechat_channel.user_ids)
        livechat_operator_group = self.env.ref("im_livechat.im_livechat_group_user")
        self.diana_agent.write({
            "group_ids": [Command.unlink(livechat_operator_group.id)],
        })
        self.assertNotIn(self.diana_agent, self.livechat_channel.user_ids)
        self.diana_agent.write({
            "group_ids": [Command.link(livechat_operator_group.id)],
        })
        self.assertNotIn(self.diana_agent, self.livechat_channel.user_ids)

    def test_leave_livechat_channels_when_manager_access_revoked(self):
        self.assertNotIn(self.laura_manager, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(self.laura_manager).action_join()
        self.assertIn(self.laura_manager, self.livechat_channel.user_ids)
        livechat_manager_group = self.env.ref("im_livechat.im_livechat_group_manager")
        self.laura_manager.write({
            "group_ids": [Command.unlink(livechat_manager_group.id)],
        })
        self.assertNotIn(self.laura_manager, self.livechat_channel.user_ids)
        self.laura_manager.write({
            "group_ids": [Command.link(livechat_manager_group.id)],
        })
        self.assertNotIn(self.laura_manager, self.livechat_channel.user_ids)

    def test_leave_livechat_channels_when_operator_removed_from_group(self):
        self.assertNotIn(self.diana_agent, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(self.diana_agent).action_join()
        self.assertIn(self.diana_agent, self.livechat_channel.user_ids)
        livechat_operator_group = self.env.ref("im_livechat.im_livechat_group_user")
        livechat_operator_group.write({
            "user_ids": [Command.unlink(self.diana_agent.id)],
        })
        self.assertNotIn(self.diana_agent, self.livechat_channel.user_ids)
        livechat_operator_group.write({
            "user_ids": [Command.link(self.diana_agent.id)],
        })
        self.assertNotIn(self.diana_agent, self.livechat_channel.user_ids)

    def test_leave_livechat_channels_when_manager_removed_from_group(self):
        self.assertNotIn(self.laura_manager, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(self.laura_manager).action_join()
        self.assertIn(self.laura_manager, self.livechat_channel.user_ids)
        livechat_manager_group = self.env.ref("im_livechat.im_livechat_group_manager")
        livechat_manager_group.write({
            "user_ids": [Command.unlink(self.laura_manager.id)],
        })
        self.assertNotIn(self.laura_manager, self.livechat_channel.user_ids)
        livechat_manager_group.write({
            "user_ids": [Command.link(self.laura_manager.id)],
        })
        self.assertNotIn(self.laura_manager, self.livechat_channel.user_ids)

    def test_review_link(self):
        with self.assertRaises(ValidationError):
            self.livechat_channel.review_link = "javascript:alert('hello')"
        with self.assertRaises(ValidationError):
            self.livechat_channel.review_link = "https://"
        self.livechat_channel.review_link = "https://www.odoo.com"
        self.assertEqual(self.livechat_channel.review_link, "https://www.odoo.com")

    def test_ongoing_session_count(self):
        self.authenticate(None, None)
        john = self._create_operator("fr_FR")
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Livechat Channel", "user_ids": [john.id]},
        )
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"channel_id": livechat_channel.id},
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertEqual(livechat_channel.ongoing_session_count, 1)
        channel.livechat_end_dt = Datetime.now() - timedelta(minutes=2)
        self.assertEqual(livechat_channel.ongoing_session_count, 0)
