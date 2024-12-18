# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from unittest.mock import patch

import odoo
from odoo import Command, fields
from odoo.tests import HttpCase
from odoo.tests.common import new_test_user, users
from odoo.addons.mail.tests.common import MailCommon



@odoo.tests.tagged("-at_install", "post_install")
class TestGetOperator(MailCommon, HttpCase):
    def _create_operator(self, lang_code=None, country_code=None, expertises=None):
        operator = new_test_user(
            self.env(su=True), login=f"operator_{lang_code or country_code}_{self.operator_id}"
        )
        operator.res_users_settings_id.livechat_expertise_ids = expertises
        operator.partner_id = self.env["res.partner"].create(
            {
                "name": f"Operator {lang_code or country_code}",
                "lang": lang_code,
                "country_id": self.env["res.country"].search([("code", "=", country_code)]).id
                if country_code
                else None,
            }
        )
        self.env["bus.presence"].create({"user_id": operator.id, "status": "online"})  # Simulate online status
        self.operator_id += 1
        return operator

    def _create_chat(self, livechat, operator, in_call=False):
        channel = self.env["discuss.channel"].create(
            {
                "name": "Visitor 1",
                "channel_type": "livechat",
                "livechat_active": True,
                "livechat_channel_id": livechat.id,
                "livechat_operator_id": operator.partner_id.id,
                "channel_member_ids": [Command.create({"partner_id": operator.partner_id.id})],
                "last_interest_dt": fields.Datetime.now(),
            }
        )
        if in_call:
            member = self.env["discuss.channel.member"].search(
                [("partner_id", "=", operator.partner_id.id), ("channel_id", "=", channel.id)]
            )
            self.env["discuss.channel.rtc.session"].sudo().create(
                {"channel_id": channel.id, "channel_member_id": member.id}
            )
        return channel

    def setUp(self):
        super().setUp()
        self.operator_id = 0
        self.env["res.lang"].with_context(active_test=False).search(
            [("code", "in", ["fr_FR", "es_ES", "de_DE", "en_US"])]
        ).write({"active": True})
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

    def test_get_by_expertise(self):
        dog_expert = self.env["im_livechat.expertise"].create({"name": "dog"})
        cat_expert = self.env["im_livechat.expertise"].create({"name": "cat"})
        operator_dog = self._create_operator(expertises=dog_expert)
        operator_car = self._create_operator(expertises=cat_expert)
        all_operators = operator_dog + operator_car
        pets_support = self.env["im_livechat.channel"].create(
            {"name": "Pets", "user_ids": all_operators.ids}
        )
        self.assertEqual(operator_dog, pets_support._get_operator(expertises=dog_expert))
        self.assertEqual(operator_car, pets_support._get_operator(expertises=cat_expert))

    def test_get_by_expertise_amongst_same_language(self):
        dog_expert = self.env["im_livechat.expertise"].create({"name": "dog"})
        cat_expert = self.env["im_livechat.expertise"].create({"name": "cat"})
        operator_fr_dog = self._create_operator("fr_FR", expertises=dog_expert)
        operator_fr_cat = self._create_operator("fr_FR", expertises=cat_expert)
        operator_fr_dog_cat = self._create_operator("fr_FR", expertises=dog_expert + cat_expert)
        operator_en_dog = self._create_operator("en_US", expertises=dog_expert)
        operator_en_cat = self._create_operator("en_US", expertises=cat_expert)
        all_operators = (
            operator_fr_dog
            + operator_fr_cat
            + operator_fr_dog_cat
            + operator_en_dog
            + operator_en_cat
        )
        pets_support = self.env["im_livechat.channel"].create(
            {"name": "Pets", "user_ids": all_operators.ids}
        )
        self.assertEqual(
            operator_fr_dog, pets_support._get_operator(lang="fr_FR", expertises=dog_expert)
        )
        self.assertEqual(
            operator_en_cat, pets_support._get_operator(lang="en_US", expertises=cat_expert)
        )
        self.assertEqual(
            operator_fr_dog_cat, pets_support._get_operator(lang="fr_FR", expertises=dog_expert + cat_expert)
        )
        self.assertEqual(
            operator_en_dog, pets_support._get_operator(lang="en_US", expertises=dog_expert + cat_expert)
        )

    @users("employee")
    def test_max_sessions_mode_limited(self):
        """Test operator is not available when they reached the livechat channel limit."""
        operator = self._create_operator()
        livechat_channel_data = {
            "name": "Livechat Channel",
            "user_ids": operator,
            "max_sessions_mode": "limited",
            "max_sessions": 2,
        }
        livechat_channel = self.env["im_livechat.channel"].sudo().create(livechat_channel_data)
        self.assertEqual(livechat_channel.available_operator_ids, operator)
        self._create_chat(livechat_channel, operator)
        self.assertEqual(livechat_channel.available_operator_ids, operator)
        self._create_chat(livechat_channel, operator)
        self.assertFalse(livechat_channel.available_operator_ids)

    @users("employee")
    def test_max_sessions_mode_limited_multi_operators(self):
        """Test second operator is available when first operator reached the livechat channel
        limit."""
        operator_1 = self._create_operator()
        operator_2 = self._create_operator()
        livechat_channel_data = {
            "name": "Livechat Channel",
            "user_ids": operator_1 + operator_2,
            "max_sessions_mode": "limited",
            "max_sessions": 2,
        }
        livechat_channel = self.env["im_livechat.channel"].sudo().create(livechat_channel_data)
        self._create_chat(livechat_channel, operator_1)
        self.assertEqual(livechat_channel.available_operator_ids, operator_1 + operator_2)
        self._create_chat(livechat_channel, operator_1)
        self.assertEqual(livechat_channel.available_operator_ids, operator_2)
        self._create_chat(livechat_channel, operator_2)
        self.assertEqual(livechat_channel.available_operator_ids, operator_2)

    @users("employee")
    def test_max_sessions_mode_limited_operator_in_call_no_new_sessions(self):
        """Test operator is not available when they are in call, even below the livechat channel
        limit."""
        operator = self._create_operator()
        livechat_channel_data = {
            "name": "Livechat Channel",
            "user_ids": operator,
            "max_sessions_mode": "limited",
            "max_sessions": 2,
        }
        livechat_channel = self.env["im_livechat.channel"].sudo().create(livechat_channel_data)
        self._create_chat(livechat_channel, operator, in_call=True)
        self.assertFalse(livechat_channel.available_operator_ids)

    @users("employee")
    def test_max_sessions_mode_multi_channel(self):
        """Test operator is available in second channel even when they reached the livechat channel
        limit on the first channel."""
        operator = self._create_operator()
        livechat_channels_data = [
            {
                "name": "Livechat Channel",
                "user_ids": [operator.id],
                "max_sessions_mode": "limited",
                "max_sessions": 2,
            },
            {
                "name": "Livechat Channel",
                "user_ids": [operator.id],
            },
        ]
        livechat_channels = self.env["im_livechat.channel"].sudo().create(livechat_channels_data)
        self._create_chat(livechat_channels[0], operator)
        self._create_chat(livechat_channels[0], operator)
        self.assertFalse(livechat_channels[0].available_operator_ids)
        self.assertEqual(livechat_channels[1].available_operator_ids, operator)

    @users("employee")
    def test_operator_max(self):
        operator = self._create_operator()
        livechat_channels_data = [
            {
                "name": "Livechat Channel",
                "user_ids": [operator.id],
                "max_sessions_mode": "limited",
                "max_sessions": 2,
            },
            {
                "name": "Livechat Channel",
                "user_ids": [operator.id],
            },
        ]
        livechat_channels = self.env["im_livechat.channel"].sudo().create(livechat_channels_data)
        self._create_chat(livechat_channels[1], operator)
        self._create_chat(livechat_channels[1], operator)
        self.assertEqual(livechat_channels[0].available_operator_ids, operator)

    @users("employee")
    def test_operator_expired_channel(self):
        operator = self._create_operator()
        livechat_channel_data = {
            "name": "Livechat Channel",
            "user_ids": [operator.id],
            "max_sessions_mode": "limited",
            "max_sessions": 1,
        }
        livechat_channel = self.env["im_livechat.channel"].sudo().create(livechat_channel_data)
        channel_data = {
            "name": "Visitor 1",
            "channel_type": "livechat",
            "livechat_active": True,
            "livechat_channel_id": livechat_channel.id,
            "livechat_operator_id": operator.partner_id.id,
            "channel_member_ids": [Command.create({"partner_id": operator.partner_id.id})],
            "last_interest_dt": fields.Datetime.now() - timedelta(minutes=4),
        }
        channel = self.env["discuss.channel"].create(channel_data)
        self.assertFalse(livechat_channel.available_operator_ids)
        channel.write({"last_interest_dt": fields.Datetime.now() - timedelta(minutes=20)})
        self.assertEqual(livechat_channel.available_operator_ids, operator)

    @users("employee")
    def test_non_member_operator_availability(self):
        """Test the availability of an operator not member of any livechat channel is properly
        computed when explicitly passing them to _get_available_operators_by_livechat_channel."""
        operator = self._create_operator()
        livechat_channels_data = [
            {
                "name": "Livechat Channel 1",
                "max_sessions_mode": "limited",
                "max_sessions": 2,
            },
            {
                "name": "Livechat Channel 2",
            },
        ]
        livechat_channels = self.env["im_livechat.channel"].sudo().create(livechat_channels_data)
        self.assertFalse(livechat_channels[0].available_operator_ids)
        self.assertFalse(livechat_channels[1].available_operator_ids)
        self.assertEqual(
            livechat_channels._get_available_operators_by_livechat_channel(operator),
            {
                livechat_channels[0]: operator,
                livechat_channels[1]: operator,
            },
        )
        self._create_chat(livechat_channels[0], operator)
        self._create_chat(livechat_channels[0], operator)
        self.assertEqual(
            livechat_channels._get_available_operators_by_livechat_channel(operator),
            {
                livechat_channels[0]: self.env["res.users"],
                livechat_channels[1]: operator,
            },
        )
        self.env["bus.presence"].search([("user_id", "=", operator.id)]).status = "offline"
        self.assertEqual(
            livechat_channels._get_available_operators_by_livechat_channel(operator),
            {
                livechat_channels[0]: self.env["res.users"],
                livechat_channels[1]: self.env["res.users"],
            },
        )

    @users("employee")
    def test_get_non_member_operator(self):
        """Test _get_operator works with a given list of operators that are not members of the
        livechat channel"""
        operator_1 = self._create_operator(lang_code="fr_FR")
        operator_2 = self._create_operator(lang_code="en_US")
        all_operators = operator_1 + operator_2
        livechat_channel_data = {"name": "Livechat Channel 2"}
        livechat_channel = self.env["im_livechat.channel"].sudo().create(livechat_channel_data)
        self.assertFalse(livechat_channel._get_operator())
        self.assertFalse(
            livechat_channel._get_operator(previous_operator_id=operator_1.partner_id.id)
        )
        self.assertEqual(livechat_channel._get_operator(users=all_operators), operator_1)
        self.assertEqual(
            livechat_channel._get_operator(previous_operator_id=operator_2.partner_id.id, users=all_operators),
            operator_2,
        )
        self.assertEqual(
            livechat_channel._get_operator(lang="en_US", users=all_operators), operator_2
        )
