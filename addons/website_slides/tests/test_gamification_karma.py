from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger

from odoo.addons.website_slides.tests import common


@tagged("gamification")
class TestKarmaGain(common.SlidesCase):
    def setUp(self):
        super().setUp()

        self.channel_2 = (
            self.env["slide.channel"]
            .with_user(self.user_officer)
            .create(
                {
                    "name": "Test Channel 2",
                    "channel_type": "training",
                    "promote_strategy": "most_voted",
                    "enroll": "public",
                    "visibility": "public",
                    "is_published": True,
                    "karma_gen_channel_finish": 100,
                    "karma_gen_channel_rank": 10,
                }
            )
        )

        self.slide_2_0, self.slide_2_1 = (
            self.env["slide.slide"]
            .with_user(self.user_officer)
            .create(
                [
                    {
                        "name": "How to travel through space and time",
                        "channel_id": self.channel_2.id,
                        "slide_category": "document",
                        "is_published": True,
                        "completion_time": 2.0,
                    },
                    {
                        "name": "How to duplicate yourself",
                        "channel_id": self.channel_2.id,
                        "slide_category": "document",
                        "is_published": True,
                        "completion_time": 2.0,
                    },
                ]
            )
        )

    @mute_logger("odoo.models")
    @users("user_emp", "user_portal", "user_officer")
    def test_karma_gain(self):
        user = self.env.user
        user.write({"karma": 0})
        computed_karma = 0

        (self.channel | self.channel_2)._action_add_members(user.partner_id)
        self.assertEqual(user.karma, 0)

        self.slide.with_user(user).action_mark_completed()
        self.assertFalse(self.channel.with_user(user).completed)
        self.slide_2.with_user(user).action_mark_completed()

        self.slide_3.with_user(user).action_set_viewed(quiz_attempts_inc=True)
        self.slide_3.with_user(user)._action_mark_completed()
        computed_karma += self.slide_3.quiz_first_attempt_reward
        computed_karma += self.channel.karma_gen_channel_finish
        self.assertTrue(self.channel.with_user(user).completed)
        self.assertEqual(user.karma, computed_karma)

        self.slide_3.with_user(user).action_mark_uncompleted()
        computed_karma -= self.slide_3.quiz_first_attempt_reward
        self.assertTrue(self.channel.with_user(user).completed)
        self.assertEqual(user.karma, computed_karma)

        self.slide_3.with_user(user).action_set_viewed(quiz_attempts_inc=True)
        self.slide_3.with_user(user)._action_mark_completed()
        computed_karma += self.slide_3.quiz_second_attempt_reward
        self.assertTrue(self.channel.with_user(user).completed)
        self.assertEqual(user.karma, computed_karma)

        self.slide_2_0.with_user(user).action_mark_completed()
        self.assertFalse(self.channel_2.with_user(user).completed)
        self.assertEqual(user.karma, computed_karma)

        self.slide_2_1.with_user(user).action_mark_completed()
        self.assertTrue(self.channel_2.with_user(user).completed)
        computed_karma += self.channel_2.karma_gen_channel_finish
        self.assertEqual(user.karma, computed_karma)

        slide_user = self.slide.with_user(user)
        slide_user.action_like()
        self.assertEqual(user.karma, computed_karma)

        slide_user.action_dislike()
        self.assertEqual(user.karma, computed_karma)

        self.channel._remove_membership(user.partner_id.ids)
        self.assertEqual(user.karma, computed_karma)

        self.channel._action_add_members(user.partner_id)
        self.assertTrue(self.channel_2.with_user(user).completed)
        self.assertEqual(user.karma, computed_karma)

    @mute_logger("odoo.models")
    @users("user_emp", "user_portal", "user_officer")
    def test_karma_gain_multiple_course(self):
        user = self.env.user
        user.write({"karma": 0})
        computed_karma = 0

        (self.channel | self.channel_2)._action_add_members(user.partner_id)

        computed_karma += (
            self.channel.karma_gen_channel_finish
            + self.channel_2.karma_gen_channel_finish
        )
        (
            self.slide | self.slide_2 | self.slide_3 | self.slide_2_0 | self.slide_2_1
        ).with_user(user)._action_mark_completed()
        self.assertEqual(user.karma, computed_karma)

    @mute_logger("odoo.models")
    def test_karma_gain_multiple_course_multiple_users(self):
        users = self.user_emp | self.user_portal
        users.write({"karma": 0})

        (self.channel | self.channel_2)._action_add_members(users.partner_id)
        channel_partners = (
            self.env["slide.channel.partner"]
            .sudo()
            .search([("partner_id", "in", users.partner_id.ids)])
        )
        self.assertEqual(len(channel_partners), 4)

        # Set courses as completed and update karma
        # Recalibrated: this test could not run at all on the fork (setUpClass
        # raised AccessError building the quiz survey as an officer), so the old
        # 74 predated the fork's quiz→survey.question rework. The per-user slide
        # fields are now correctly keyed per uid (depends_context), so reading
        # them for two members no longer collides on one shared cache entry.
        # This bound is not architecturally O(1) in the number of members/
        # channels; a future batching fix that lowers it is welcome, but any
        # bump of this literal should first check whether the new count still
        # scales with the fixture size here (4 members, 2 channels) rather
        # than blindly re-measuring and pasting in whatever comes out.
        with self.assertQueryCount(76):
            channel_partners._post_completion_update_hook()

        computed_karma = (
            self.channel.karma_gen_channel_finish
            + self.channel_2.karma_gen_channel_finish
        )

        for user in users:
            self.assertEqual(user.karma, computed_karma)
            user_trackings = user.karma_tracking_ids
            self.assertEqual(len(user_trackings), 2)

            self.assertEqual(user_trackings[0].new_value, computed_karma)
            self.assertEqual(
                user_trackings[0].old_value, self.channel_2.karma_gen_channel_finish
            )
            self.assertEqual(user_trackings[0].origin_ref, self.channel_2)

            self.assertEqual(
                user_trackings[1].new_value, self.channel.karma_gen_channel_finish
            )
            self.assertEqual(user_trackings[1].old_value, 0)
            self.assertEqual(user_trackings[1].origin_ref, self.channel)

        # now, remove the membership in batch, on multiple users - karma should not move as we only archive membership
        # Recalibrated from 9 alongside the count above (resurrected test).
        # Same caveat as the 76 above: re-derive against this fixture's size
        # before bumping, don't just paste in a new measurement.
        with self.assertQueryCount(10):
            (self.channel | self.channel_2)._remove_membership(users.partner_id.ids)

        for user in users:
            self.assertEqual(user.karma, computed_karma)
            user_trackings = user.karma_tracking_ids
            self.assertEqual(len(user_trackings), 2)

            self.assertEqual(user_trackings[0].new_value, computed_karma)
            self.assertEqual(
                user_trackings[0].old_value, self.channel.karma_gen_channel_finish
            )
            self.assertEqual(user_trackings[0].origin_ref, self.channel_2)

            self.assertEqual(
                user_trackings[1].new_value, self.channel.karma_gen_channel_finish
            )
            self.assertEqual(user_trackings[1].old_value, 0)
            self.assertEqual(user_trackings[1].origin_ref, self.channel)
