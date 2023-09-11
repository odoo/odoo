import odoo
from odoo.tests import HttpCase
from odoo.tests.common import new_test_user


@odoo.tests.tagged("-at_install", "post_install")
class TestGetRandomOperator(HttpCase):
    def _create_operator(self, lang_code=None, country_code=None):
        operator = new_test_user(self.env, login=f"operator_{lang_code or country_code}_{self.operator_id}")
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

    def setUp(self):
        super().setUp()
        self.operator_id = 0
        self.env["res.lang"].with_context(active_test=False).search(
            [("code", "in", ["fr_FR", "es_ES", "de_DE", "en_US"])]
        ).write({"active": True})

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
        fist_operator = self._create_operator("fr_FR", "FR")
        second_operator = self._create_operator("fr_FR", "FR")
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [fist_operator.id, second_operator.id],
            }
        )
        channel_1_info = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "anonymous_name": "Visitor 1",
                "channel_id": livechat_channel.id,
                "previous_operator_id": fist_operator.partner_id.id,
                "persisted": True,
            },
        )
        channel_2_info = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "anonymous_name": "Visitor 2",
                "channel_id": livechat_channel.id,
                "previous_operator_id": fist_operator.partner_id.id,
                "persisted": True,
            },
        )
        # Only channels with messages within the last 30 minutes are considered
        # as active, mark them as active now.
        self.env["mail.message"].create(
            [
                {
                    "model": "discuss.channel",
                    "res_id": channel_1_info["id"],
                    "body": "Hello, I'm visitor 1",
                },
                {
                    "model": "discuss.channel",
                    "res_id": channel_2_info["id"],
                    "body": "Hello, I'm visitor 2",
                },
            ]
        )
        # Previous operator is not in a call so it should be available, even if
        # he already has two ongoing chats.
        self.assertEqual(
            fist_operator, livechat_channel._get_operator(previous_operator_id=fist_operator.partner_id.id)
        )
        self.env["discuss.channel.rtc.session"].create(
            {
                "channel_id": channel_1_info["id"],
                "channel_member_id": self.env["discuss.channel.member"]
                .search([["partner_id", "=", fist_operator.partner_id.id], ["channel_id", "=", channel_1_info["id"]]])
                .id,
            }
        )
        # Previous operator is in a call so it should not be available anymore.
        self.assertEqual(
            second_operator, livechat_channel._get_operator(previous_operator_id=fist_operator.partner_id.id)
        )

    def test_find_less_active_operator_ids(self):
        # The one with less chats should be returned
        self.assertEqual(
            [1],
            self.env["im_livechat.channel"]._find_less_active_operator_ids(
                {
                    1: {"count": 1, "in_call": False},
                    2: {"count": 2, "in_call": False},
                }
            ),
        )
        # The one with less chats is in a call but has only 1 chat, it should
        # be returned
        self.assertEqual(
            [1],
            self.env["im_livechat.channel"]._find_less_active_operator_ids(
                {
                    1: {"count": 1, "in_call": True},
                    2: {"count": 2, "in_call": False},
                }
            ),
        )
        # The one with less chats is in a call and already has 2 chats, it
        # should not be returned
        self.assertEqual(
            [2],
            self.env["im_livechat.channel"]._find_less_active_operator_ids(
                {
                    1: {"count": 2, "in_call": True},
                    2: {"count": 3, "in_call": False},
                }
            ),
        )
        # Both are not in a call, both have the same number of chats, both
        # should be returned
        self.assertEqual(
            [1, 2],
            self.env["im_livechat.channel"]._find_less_active_operator_ids(
                {
                    1: {"count": 3, "in_call": False},
                    2: {"count": 3, "in_call": False},
                }
            ),
        )
        # Both are in a call, both have the same number of chats, both should
        # be returned
        self.assertEqual(
            [1, 2],
            self.env["im_livechat.channel"]._find_less_active_operator_ids(
                {
                    1: {"count": 3, "in_call": True},
                    2: {"count": 3, "in_call": True},
                }
            ),
        )
        # Both have the same number of chats, one is in a call with less than
        # 2 chats,  both should be returned
        self.assertEqual(
            [1, 2],
            self.env["im_livechat.channel"]._find_less_active_operator_ids(
                {
                    1: {"count": 1, "in_call": True},
                    2: {"count": 1, "in_call": False},
                }
            ),
        )
