# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch

from odoo.sql_db import Cursor

from odoo.addons.social_test_full.tests.common import SocialTestFullCase


class TestSocialBasic(SocialTestFullCase):
    def test_split_per_media(self):
        images = self.env["ir.attachment"].create(
            [{"name": "img.jpg"} for _ in range(3)]
        )
        post = self.env["social.post"].create(
            {
                # Facebook - Twitter - Push Notification
                "account_ids": (self.accounts[1:3] + self.accounts[4]).ids,
                "image_ids": images[0].ids,
                "message": "test",
            }
        )
        self.assertEqual(post.facebook_message, "test")
        self.assertEqual(post.twitter_message, "test")
        self.assertEqual(post.push_notification_message, "test")
        self.assertEqual(post.facebook_image_ids, images[0])
        self.assertEqual(post.twitter_image_ids, images[0])

        post.message = "test 2"
        post.image_ids = images.ids
        self.assertEqual(post.facebook_message, "test 2")
        self.assertEqual(post.twitter_message, "test 2")
        self.assertEqual(post.push_notification_message, "test 2")
        self.assertEqual(post.facebook_image_ids, images)
        self.assertEqual(post.twitter_image_ids, images)

        post.is_split_per_media = True
        post.facebook_message = "test fb"
        post.twitter_image_ids = images[1].ids
        self.assertEqual(post.facebook_message, "test fb")
        self.assertEqual(post.twitter_message, "test 2")
        self.assertEqual(post.push_notification_message, "test 2")
        self.assertEqual(post.facebook_image_ids, images)
        self.assertEqual(post.twitter_image_ids, images[1])

        post.action_post()
        self.assertEqual(post.live_post_ids[0].message, "test fb")
        self.assertEqual(post.live_post_ids[0].image_ids, images)
        self.assertEqual(post.live_post_ids[1].message, "test 2")
        self.assertEqual(post.live_post_ids[1].image_ids, images[1])
        self.assertEqual(post.live_post_ids[2].message, "test 2")
        self.assertFalse(post.live_post_ids[2].image_ids)

    @freeze_time("2022-01-02")
    @patch.object(Cursor, "now", lambda *args, **kwargs: datetime(2022, 1, 2))
    def test_utm_source_name(self):
        post_1, post_2 = self.env["social.post"].create(
            [
                {
                    "account_ids": [(4, self.accounts[2].id)],
                    "is_split_per_media": True,
                    "twitter_message": "Twitter",
                },
                {
                    "account_ids": [(4, self.accounts[1].id)],
                    "message": "Message",
                    "is_split_per_media": True,
                },
            ]
        )

        self.assertEqual(post_1.name, "Twitter (Social Post created on 2022-01-02)")
        self.assertEqual(post_2.name, "Message (Social Post created on 2022-01-02)")

        post_1.twitter_message = "Twitter 2"
        self.assertEqual(post_1.name, "Twitter 2 (Social Post created on 2022-01-02)")
