# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.tests.common import new_test_user
from odoo.tools import mute_logger

from odoo.addons.digest.tests.common import TestDigestCommon


class TestLiveChatDigest(TestDigestCommon):

    @classmethod
    @mute_logger('odoo.models.unlink')
    def setUpClass(cls):
        super().setUpClass()
        other_user = new_test_user(cls.env, "Other User")
        cls.env["discuss.channel"].search([("channel_type", "=", "livechat")]).unlink()
        with (
            freeze_time(fields.Datetime.now() - datetime.timedelta(days=10)),
            patch.object(cls.env.cr, "_now", datetime.datetime.now() - datetime.timedelta(days=10)),
        ):
            # this channel is created out of the date range of the digest
            # so it should be ignored in the computation of the KPI
            old_channel = cls.env["discuss.channel"].create(
                {
                    "name": "Channel 4",
                    "channel_type": "livechat",
                    "livechat_rating": "1",
                }
            )
        new_channels = cls.env["discuss.channel"].create(
            [
                {
                    "name": "Channel 1",
                    "channel_type": "livechat",
                    "livechat_rating": "5",
                },
                {
                    "name": "Channel 2",
                    "channel_type": "livechat",
                    "livechat_rating": "3",
                },
                {
                    "name": "Channel 3",
                    "channel_type": "livechat",
                    "livechat_rating": "1",
                },
                {
                    "name": "Channel 5",
                    "channel_type": "livechat",
                    "livechat_rating": False,
                },
            ]
        )
        cls.channels = old_channel | new_channels
        cls.channels[0:5]._add_members(users=cls.env.user)
        cls.channels[2]._add_members(users=other_user)

    def test_kpi_livechat_rating_value(self):
        self.assertEqual(round(self.digest_1.kpi_livechat_rating_value, 2), 50.00)
