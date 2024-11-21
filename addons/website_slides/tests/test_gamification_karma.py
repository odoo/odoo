# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger


@tagged('gamification')
class TestKarmaGain(common.SlidesCase):

    def setUp(self):
        super(TestKarmaGain, self).setUp()

        self.channel_2 = self.env['slide.channel'].with_user(self.user_officer).create({
            'name': 'Test Channel 2',
            'channel_type': 'training',
            'promote_strategy': 'most_voted',
            'enroll': 'public',
            'visibility': 'public',
            'is_published': True,
            'karma_gen_channel_finish': 100,
            'karma_gen_channel_rank': 10,
        })

        self.slide_2_0, self.slide_2_1 = self.env['slide.slide'].with_user(self.user_officer).create([
            {'name': 'How to travel through space and time',
             'channel_id': self.channel_2.id,
             'slide_category': 'document',
             'is_published': True,
             'completion_time': 2.0,
            },
            {'name': 'How to duplicate yourself',
             'channel_id': self.channel_2.id,
             'slide_category': 'document',
             'is_published': True,
             'completion_time': 2.0,
            }
        ])

    @mute_logger('odoo.models')
    @users('user_emp', 'user_portal', 'user_officer')
    def test_karma_gain(self):
        user = self.env.user
        user.write({'karma': 0})
        computed_karma = 0

        # Add the user to the course
        (self.channel | self.channel_2)._action_add_members(user.partner_id)
        self.assertEqual(user.karma, 0)

        # Finish the Course
        self.slide.with_user(user).action_mark_completed()
        self.assertFalse(self.channel.with_user(user).completed)
        self.slide_2.with_user(user).action_mark_completed()

        # answer a quizz question
        self.slide_3.with_user(user).action_set_viewed(quiz_attempts_inc=True)
        self.slide_3.with_user(user)._action_mark_completed()
        computed_karma += self.slide_3.quiz_first_attempt_reward
        computed_karma += self.channel.karma_gen_channel_finish
        self.assertTrue(self.channel.with_user(user).completed)
        self.assertEqual(user.karma, computed_karma)

        # Mark the quiz as not completed.
        # The course remains completed once completed. No karma change.
        self.slide_3.with_user(user).action_mark_uncompleted()
        computed_karma -= self.slide_3.quiz_first_attempt_reward
        self.assertTrue(self.channel.with_user(user).completed)
        self.assertEqual(user.karma, computed_karma)

        # Re-submit the quiz, we should consider it as the second attempt
        self.slide_3.with_user(user).action_set_viewed(quiz_attempts_inc=True)
        self.slide_3.with_user(user)._action_mark_completed()
        computed_karma += self.slide_3.quiz_second_attempt_reward
        self.assertTrue(self.channel.with_user(user).completed)
        self.assertEqual(user.karma, computed_karma)

        # Begin then finish the second Course
        self.slide_2_0.with_user(user).action_mark_completed()
        self.assertFalse(self.channel_2.with_user(user).completed)
        self.assertEqual(user.karma, computed_karma)

        self.slide_2_1.with_user(user).action_mark_completed()
        self.assertTrue(self.channel_2.with_user(user).completed)
        computed_karma += self.channel_2.karma_gen_channel_finish
        self.assertEqual(user.karma, computed_karma)

        # Vote for a slide: Karma should not move
        slide_user = self.slide.with_user(user)
        slide_user.action_like()
        self.assertEqual(user.karma, computed_karma)

        slide_user.action_dislike()
        self.assertEqual(user.karma, computed_karma)

        # Leave the finished course - karma should not move as we only archive membership
        self.channel._remove_membership(user.partner_id.ids)
        self.assertEqual(user.karma, computed_karma)

        # Unarchive the partner. Karma should not move. Course should be completed.
        self.channel._action_add_members(user.partner_id)
        self.assertTrue(self.channel_2.with_user(user).completed)
        self.assertEqual(user.karma, computed_karma)

    @mute_logger('odoo.models')
    @users('user_emp', 'user_portal', 'user_officer')
    def test_karma_gain_multiple_course(self):
        user = self.env.user
        user.write({'karma': 0})
        computed_karma = 0

        # Finish two course at the same time (should not ever happen but hey, we never know)
        (self.channel | self.channel_2)._action_add_members(user.partner_id)

        computed_karma += self.channel.karma_gen_channel_finish + self.channel_2.karma_gen_channel_finish
        (self.slide | self.slide_2 | self.slide_3 | self.slide_2_0 | self.slide_2_1).with_user(user)._action_mark_completed()
        self.assertEqual(user.karma, computed_karma)

    @mute_logger('odoo.models')
    def test_karma_gain_multiple_course_multiple_users(self):
        users = self.user_emp | self.user_portal
        users.write({'karma': 0})

        (self.channel | self.channel_2)._action_add_members(users.partner_id)
        channel_partners = self.env['slide.channel.partner'].sudo().search([('partner_id', 'in', users.partner_id.ids)])
        self.assertEqual(len(channel_partners), 4)

        # Set courses as completed and update karma
        with self.assertQueryCount(57):  # com 55
            channel_partners._post_completion_update_hook()

        computed_karma = self.channel.karma_gen_channel_finish + self.channel_2.karma_gen_channel_finish

        for user in users:
            self.assertEqual(user.karma, computed_karma)
            user_trackings = user.karma_tracking_ids
            self.assertEqual(len(user_trackings), 2)

            self.assertEqual(user_trackings[0].new_value, computed_karma)
            self.assertEqual(user_trackings[0].old_value, self.channel_2.karma_gen_channel_finish)
            self.assertEqual(user_trackings[0].origin_ref, self.channel_2)

            self.assertEqual(user_trackings[1].new_value, self.channel.karma_gen_channel_finish)
            self.assertEqual(user_trackings[1].old_value, 0)
            self.assertEqual(user_trackings[1].origin_ref, self.channel)

        # now, remove the membership in batch, on multiple users - karma should not move as we only archive membership
        with self.assertQueryCount(10):
            (self.channel | self.channel_2)._remove_membership(users.partner_id.ids)

        for user in users:
            self.assertEqual(user.karma, computed_karma)
            user_trackings = user.karma_tracking_ids
            self.assertEqual(len(user_trackings), 2)

            self.assertEqual(user_trackings[0].new_value, computed_karma)
            self.assertEqual(user_trackings[0].old_value, self.channel.karma_gen_channel_finish)
            self.assertEqual(user_trackings[0].origin_ref, self.channel_2)

            self.assertEqual(user_trackings[1].new_value, self.channel.karma_gen_channel_finish)
            self.assertEqual(user_trackings[1].old_value, 0)
            self.assertEqual(user_trackings[1].origin_ref, self.channel)
