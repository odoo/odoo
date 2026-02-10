# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from odoo.addons.digest.tests.common import TestDigestCommon
from odoo.tools import mute_logger
from odoo import fields


class TestLiveChatDigest(TestDigestCommon):
    @classmethod
    @mute_logger("odoo.models.unlink")
    def setUpClass(cls):
        super().setUpClass()

        other_partner = cls.env["res.partner"].create({"name": "Other Partner"})
        cls.channels = cls.env["discuss.channel"].create(
            [
                {
                    "name": "Channel 1",
                    "channel_type": "livechat",
                    "livechat_rating": 3,
                    "livechat_end_dt": fields.Datetime.now(),
                },
                {
                    "name": "Channel 2",
                    "channel_type": "livechat",
                    "livechat_rating": 2,
                    "livechat_end_dt": fields.Datetime.now(),
                },
                {
                    "name": "Channel 3",
                    "channel_type": "livechat",
                    "livechat_rating": 1,
                    "livechat_end_dt": fields.Datetime.now(),
                },
                {
                    "name": "Channel 4",
                    "channel_type": "livechat",
                    "livechat_rating": 1,
                    "livechat_end_dt": fields.Datetime.now() - datetime.timedelta(days=10),
                },
                {
                    "name": "Channel 5",
                    "channel_type": "livechat",
                    "livechat_rating": False,
                },
            ]
        )
        cls.channels[0:5]._add_members(users=cls.env.user)
        cls.channels[2]._add_members(partners=other_partner)

    def test_kpi_livechat_rating_value(self):
        # 1/3 of the ratings have 2/2 note others should be ignored
        self.assertEqual(round(self.digest_1.kpi_livechat_rating_value, 2), 33.33)
