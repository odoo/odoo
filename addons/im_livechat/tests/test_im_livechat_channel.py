from datetime import timedelta

from odoo.tests import new_test_user, tagged
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon
from odoo.addons.im_livechat.tests.test_get_operator import TestGetOperator
from odoo.fields import Command, Datetime


@tagged("-at_install", "post_install")
class TestImLivechatChannel(TestImLivechatCommon, TestGetOperator):
    def test_user_cant_join_livechat_channel(self):
        bob_user = new_test_user(self.env, "bob_user", groups="base.group_user")
        with self.assertRaises(AccessError):
            self.livechat_channel.with_user(bob_user).action_join()

    def test_operator_join_leave_livechat_channel(self):
        bob_operator = new_test_user(
            self.env, "bob_user", groups="base.group_user,im_livechat.im_livechat_group_user"
        )
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(bob_operator).action_join()
        self.assertIn(bob_operator, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(bob_operator).action_quit()
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)

    def test_leave_livechat_channels_when_operator_access_revoked(self):
        bob_operator = new_test_user(
            self.env, "bob_user", groups="im_livechat.im_livechat_group_user"
        )
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(bob_operator).action_join()
        self.assertIn(bob_operator, self.livechat_channel.user_ids)
        livechat_operator_group = self.env.ref("im_livechat.im_livechat_group_user")
        bob_operator.write({
            "group_ids": [Command.unlink(livechat_operator_group.id)],
        })
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)
        bob_operator.write({
            "group_ids": [Command.link(livechat_operator_group.id)],
        })
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)

    def test_leave_livechat_channels_when_manager_access_revoked(self):
        bob_operator = new_test_user(
            self.env, "bob_user", groups="im_livechat.im_livechat_group_manager"
        )
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(bob_operator).action_join()
        self.assertIn(bob_operator, self.livechat_channel.user_ids)
        livechat_manager_group = self.env.ref("im_livechat.im_livechat_group_manager")
        bob_operator.write({
            "group_ids": [Command.unlink(livechat_manager_group.id)],
        })
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)
        bob_operator.write({
            "group_ids": [Command.link(livechat_manager_group.id)],
        })
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)

    def test_leave_livechat_channels_when_operator_removed_from_group(self):
        bob_operator = new_test_user(
            self.env, "bob_user", groups="im_livechat.im_livechat_group_user"
        )
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(bob_operator).action_join()
        self.assertIn(bob_operator, self.livechat_channel.user_ids)
        livechat_operator_group = self.env.ref("im_livechat.im_livechat_group_user")
        livechat_operator_group.write({
            "user_ids": [Command.unlink(bob_operator.id)],
        })
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)
        livechat_operator_group.write({
            "user_ids": [Command.link(bob_operator.id)],
        })
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)

    def test_leave_livechat_channels_when_manager_removed_from_group(self):
        bob_operator = new_test_user(
            self.env, "bob_user", groups="im_livechat.im_livechat_group_manager"
        )
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(bob_operator).action_join()
        self.assertIn(bob_operator, self.livechat_channel.user_ids)
        livechat_manager_group = self.env.ref("im_livechat.im_livechat_group_manager")
        livechat_manager_group.write({
            "user_ids": [Command.unlink(bob_operator.id)],
        })
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)
        livechat_manager_group.write({
            "user_ids": [Command.link(bob_operator.id)],
        })
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)

    def test_review_link(self):
        with self.assertRaises(ValidationError):
            self.livechat_channel.review_link = "javascript:alert('hello')"
        with self.assertRaises(ValidationError):
            self.livechat_channel.review_link = "https://"
        self.livechat_channel.review_link = "https://www.odoo.com"
        self.assertEqual(self.livechat_channel.review_link, "https://www.odoo.com")

    def test_ongoing_session_count(self):
        livechat_channel = self.livechat_channel
        session_1 = self._create_conversation(livechat_channel, livechat_channel.user_ids[0])
        session_2 = self._create_conversation(livechat_channel, livechat_channel.user_ids[0])
        self.assertEqual(livechat_channel.ongoing_session_count, 2)
        session_1.livechat_end_dt = Datetime.now() - timedelta(minutes=4)
        self.assertEqual(livechat_channel.ongoing_session_count, 1)
        session_2.livechat_end_dt = Datetime.now() - timedelta(minutes=2)
        self.assertEqual(livechat_channel.ongoing_session_count, 0)
