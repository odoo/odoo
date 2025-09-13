import odoo
from odoo import Command
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon

from unittest.mock import patch


@odoo.tests.tagged("-at_install", "post_install")
class TestGetOperator(TestImLivechatCommon):
    def _create_chat(self, livechat, operator, in_call=False):
        channel = self.env["discuss.channel"].create(
            {
                "name": "Visitor 1",
                "channel_type": "livechat",
                "livechat_active": True,
                "livechat_channel_id": livechat.id,
                "livechat_operator_id": operator.partner_id.id,
                "channel_member_ids": [Command.create({"partner_id": operator.partner_id.id})],
            }
        )
        channel.with_user(operator).message_post(body="Hello, how can I help you?")
        if in_call:
            self.env["discuss.channel.rtc.session"].create(
                {
                    "channel_id": channel.id,
                    "channel_member_id": self.env["discuss.channel.member"]
                    .search([["partner_id", "=", operator.partner_id.id], ["channel_id", "=", channel.id]])
                    .id,
                }
            )
        return channel

    def setUp(self):
        super().setUp()
        self.operator_id = 0
        random_choice_patch = patch("random.choice", lambda arr: arr[0])
        self.startPatcher(random_choice_patch)

    def test_get_by_lang(self):
        fr_operator = self._create_operator("fr_FR")
        en_operator = self._create_operator("en_US")
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [fr_operator.id, en_operator.id],
            }
        )
        self.assertEqual(fr_operator, livechat_channel._get_operator(lang="fr_FR"))
        self.assertEqual(en_operator, livechat_channel._get_operator(lang="en_US"))

    def test_get_by_lang_both_operator_active(self):
        fr_operator = self._create_operator("fr_FR")
        en_operator = self._create_operator("en_US")
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [fr_operator.id, en_operator.id],
            }
        )
        self._create_chat(livechat_channel, fr_operator)
        self._create_chat(livechat_channel, en_operator)
        self._create_chat(livechat_channel, en_operator)
        self.assertEqual(en_operator, livechat_channel._get_operator(lang="en_US"))

    def test_get_by_lang_no_operator_matching_lang(self):
        fr_operator = self._create_operator("fr_FR")
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [fr_operator.id],
            }
        )
        self.assertEqual(fr_operator, livechat_channel._get_operator(lang="en_US"))

    def test_get_by_country(self):
        fr_operator = self._create_operator(country_code="FR")
        en_operator = self._create_operator(country_code="US")
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [fr_operator.id, en_operator.id],
            }
        )
        self.assertEqual(
            fr_operator,
            livechat_channel._get_operator(country_id=self.env["res.country"].search([("code", "=", "FR")]).id),
        )
        self.assertEqual(
            en_operator,
            livechat_channel._get_operator(country_id=self.env["res.country"].search([("code", "=", "US")]).id),
        )

    def test_get_by_country_no_operator_matching_country(self):
        fr_operator = self._create_operator(country_code="FR")
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [fr_operator.id],
            }
        )
        self.assertEqual(
            fr_operator,
            livechat_channel._get_operator(country_id=self.env["res.country"].search([("code", "=", "US")]).id),
        )

    def test_get_by_lang_and_country_prioritize_lang(self):
        fr_operator = self._create_operator("fr_FR", "FR")
        en_operator = self._create_operator("en_US", "US")
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [fr_operator.id, en_operator.id],
            }
        )
        self.assertEqual(
            fr_operator,
            livechat_channel._get_operator(
                lang="fr_FR", country_id=self.env["res.country"].search([("code", "=", "US")]).id
            ),
        )
        self.assertEqual(
            en_operator,
            livechat_channel._get_operator(
                lang="en_US", country_id=self.env["res.country"].search([("code", "=", "FR")]).id
            ),
        )

    def test_operator_in_call_no_more_than_two_chats(self):
        first_operator = self._create_operator("fr_FR", "FR")
        second_operator = self._create_operator("fr_FR", "FR")
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [first_operator.id, second_operator.id],
            }
        )
        self._create_chat(livechat_channel, first_operator)
        self._create_chat(livechat_channel, first_operator)
        # Previous operator is not in a call so it should be available, even if
        # he already has two ongoing chats.
        self.assertEqual(
            first_operator, livechat_channel._get_operator(previous_operator_id=first_operator.partner_id.id)
        )
        self._create_chat(livechat_channel, first_operator, in_call=True)
        # Previous operator is in a call so it should not be available anymore.
        self.assertEqual(
            second_operator, livechat_channel._get_operator(previous_operator_id=first_operator.partner_id.id)
        )

    def test_priority_by_number_of_chat(self):
        first_operator = self._create_operator()
        second_operator = self._create_operator()
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [first_operator.id, second_operator.id],
            }
        )
        self._create_chat(livechat_channel, first_operator)
        self._create_chat(livechat_channel, second_operator)
        self._create_chat(livechat_channel, second_operator)
        self.assertEqual(first_operator, livechat_channel._get_operator())

    def test_in_call_operator_not_prioritized(self):
        first_operator = self._create_operator()
        second_operator = self._create_operator()
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [first_operator.id, second_operator.id],
            }
        )
        self._create_chat(livechat_channel, first_operator, in_call=True)
        self._create_chat(livechat_channel, second_operator)
        self.assertEqual(second_operator, livechat_channel._get_operator())

    def test_priority_by_number_of_chat_with_call_limit_not_exceeded(self):
        first_operator = self._create_operator()
        second_operator = self._create_operator()
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [first_operator.id, second_operator.id],
            }
        )
        self._create_chat(livechat_channel, first_operator, in_call=True)
        self._create_chat(livechat_channel, second_operator)
        self._create_chat(livechat_channel, second_operator)
        self.assertEqual(first_operator, livechat_channel._get_operator())

    def test_priority_by_number_of_chat_all_operators_exceed_limit(self):
        first_operator = self._create_operator()
        second_operator = self._create_operator()
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [first_operator.id, second_operator.id],
            }
        )
        self._create_chat(livechat_channel, first_operator, in_call=True)
        self._create_chat(livechat_channel, first_operator)
        self._create_chat(livechat_channel, second_operator, in_call=True)
        self._create_chat(livechat_channel, second_operator)
        self._create_chat(livechat_channel, second_operator)
        self.assertEqual(first_operator, livechat_channel._get_operator())

    def test_operator_freed_after_chat_ends(self):
        first_operator = self._create_operator()
        second_operator = self._create_operator()
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [first_operator.id, second_operator.id],
            }
        )
        self.assertEqual(first_operator, livechat_channel._get_operator())
        chat = self._create_chat(livechat_channel, first_operator)
        self.assertEqual(second_operator, livechat_channel._get_operator())
        chat.livechat_active = False
        chat.flush_recordset(["livechat_active"])
        self.assertEqual(first_operator, livechat_channel._get_operator())
