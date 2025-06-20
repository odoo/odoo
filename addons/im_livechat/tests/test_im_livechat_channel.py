from odoo.tests import new_test_user, tagged
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon
from odoo.addons.im_livechat.tests.test_get_operator import TestGetOperator
from odoo.fields import Command


@tagged("-at_install", "post_install")
class TestImLivechatChannel(TestGetOperator, TestImLivechatCommon):
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

    def test_livechat_channel_computed_values(self):
        livechat_channel1 = self.livechat_channel
        operators = livechat_channel1.user_ids
        self._create_chat(livechat_channel1, operators[0])
        self.assertEqual(
            livechat_channel1.total_conversations,
            1,
            'Total conversations of a livechat channel should be equal to the sum of all active livechat sessions of that livechat channel with an operator.'
        )
        livechat_channel1.max_sessions_mode = 'limited'
        livechat_channel1.max_sessions = 2
        self._create_chat(livechat_channel1, operators[1], in_call=True)
        livechat_channel1.block_assignment_during_call = True
        self.assertEqual(
            livechat_channel1.total_capacity,
            9,  # operators not in call (4) * max_sessions (2) + operators in call (1) = 9
            'Total capacity should be equal to (operators not in call) * (max_sessions) + (operators in call) when number of sessions is limited and assignment of new sessions during a call is not allowed.'
        )
        livechat_channel2 = self.env["im_livechat.channel"].create({
            "name": "Second Livechat Channel", "user_ids": [Command.link(operators[0].id)],
        })
        self.assertEqual(
            livechat_channel2.user_ids[0].with_context(channel_id=livechat_channel2.id).ongoing_conversations,
            0,
            'Ongoing conversations should either match the operator\'s active sessions in a livechat channel if a channel is passed via context, or reflect the operator\'s active livechat sessions across all livechat channels.'
        )
