# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import math

from odoo.addons.website_slides.tests import common
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger, float_compare


@tagged('functional')
class TestStatistics(common.SlidesCase):

    def setUp(self):
        super(TestStatistics, self).setUp()

        self.slide_2 = self.env['slide.slide'].sudo(self.user_publisher).create({
            'name': 'How To Cook For Humans',
            'channel_id': self.channel.id,
            'slide_type': 'presentation',
            'website_published': True,
            'completion_time': 3.0,
        })
        self.slide_3 = self.env['slide.slide'].sudo(self.user_publisher).create({
            'name': 'How To Cook Humans For Humans',
            'channel_id': self.channel.id,
            'slide_type': 'document',
            'website_published': True,
            'completion_time': 1.5,
        })

    @mute_logger('odoo.models')
    def test_channel_statistics(self):
        channel_publisher = self.channel.sudo(self.user_publisher)
        # slide type computation
        self.assertEqual(channel_publisher.total_slides, len(channel_publisher.slide_ids))
        self.assertEqual(channel_publisher.nbr_infographic, len(channel_publisher.slide_ids.filtered(lambda s: s.slide_type == 'infographic')))
        self.assertEqual(channel_publisher.nbr_presentation, len(channel_publisher.slide_ids.filtered(lambda s: s.slide_type == 'presentation')))
        self.assertEqual(channel_publisher.nbr_document, len(channel_publisher.slide_ids.filtered(lambda s: s.slide_type == 'document')))
        self.assertEqual(channel_publisher.nbr_video, len(channel_publisher.slide_ids.filtered(lambda s: s.slide_type == 'video')))
        # slide statistics computation
        self.assertEqual(float_compare(channel_publisher.total_time, sum(s.completion_time for s in channel_publisher.slide_ids), 3), 0)
        # members computation
        self.assertEqual(channel_publisher.members_count, 1)
        channel_publisher.action_add_member()
        self.assertEqual(channel_publisher.members_count, 1)
        channel_publisher._action_add_members(self.user_emp.partner_id)
        self.assertEqual(channel_publisher.members_count, 2)
        self.assertEqual(channel_publisher.partner_ids, self.user_publisher.partner_id | self.user_emp.partner_id)

    @mute_logger('odoo.models')
    def test_channel_user_statistics(self):
        channel_publisher = self.channel.sudo(self.user_publisher)
        channel_publisher.write({
            'enroll': 'invite',
        })
        channel_publisher._action_add_members(self.user_emp.partner_id)
        channel_emp = self.channel.sudo(self.user_emp)

        slides_emp = (self.slide | self.slide_2).sudo(self.user_emp)
        slides_emp.action_set_viewed()
        self.assertEqual(channel_emp.completion, 0)

        slides_emp.action_set_completed()
        channel_emp.invalidate_cache()
        self.assertEqual(
            channel_emp.completion,
            math.ceil(100.0 * len(slides_emp) / len(channel_publisher.slide_ids)))
        self.assertFalse(channel_emp.completed)

        self.slide_3.sudo(self.user_emp).action_set_completed()
        self.assertEqual(channel_emp.completion, 100)
        self.assertTrue(channel_emp.completed)

    @mute_logger('odoo.models')
    def test_channel_user_statistics_complete_check_member(self):
        (self.slide | self.slide_2).write({'is_preview': True})
        slides_emp = (self.slide | self.slide_2).sudo(self.user_emp)
        slides_emp.read(['name'])
        with self.assertRaises(UserError):
            slides_emp.action_set_completed()

    @mute_logger('odoo.models')
    def test_channel_user_statistics_view_check_member(self):
        (self.slide | self.slide_2).write({'is_preview': True})
        slides_emp = (self.slide | self.slide_2).sudo(self.user_emp)
        slides_emp.read(['name'])
        with self.assertRaises(UserError):
            slides_emp.action_set_viewed()

    def test_slide_user_statistics(self):
        channel_publisher = self.channel.sudo(self.user_publisher)
        channel_publisher._action_add_members(self.user_emp.partner_id)

        slide_emp = self.slide.sudo(self.user_emp)
        self.assertEqual(slide_emp.likes, 0)
        self.assertEqual(slide_emp.dislikes, 0)
        self.assertEqual(slide_emp.user_vote, 0)
        slide_emp.action_like()
        self.assertEqual(slide_emp.likes, 1)
        self.assertEqual(slide_emp.dislikes, 0)
        self.assertEqual(slide_emp.user_vote, 1)
        slide_emp.action_dislike()
        self.assertEqual(slide_emp.likes, 0)
        self.assertEqual(slide_emp.dislikes, 0)
        self.assertEqual(slide_emp.user_vote, 0)
        slide_emp.action_dislike()
        self.assertEqual(slide_emp.likes, 0)
        self.assertEqual(slide_emp.dislikes, 1)
        self.assertEqual(slide_emp.user_vote, -1)

    def test_slide_statistics(self):
        channel_publisher = self.channel.sudo(self.user_publisher)
        channel_publisher._action_add_members(self.user_emp.partner_id)

        self.assertEqual(self.slide.slide_views, 0)
        self.assertEqual(self.slide.public_views, 0)

        self.slide.write({'public_views': 4})

        self.assertEqual(self.slide.slide_views, 0)
        self.assertEqual(self.slide.public_views, 4)
        self.assertEqual(self.slide.total_views, 4)

        slide_emp = self.slide.sudo(self.user_emp)
        slide_emp.action_set_viewed()

        self.assertEqual(slide_emp.slide_views, 1)
        self.assertEqual(slide_emp.public_views, 4)
        self.assertEqual(slide_emp.total_views, 5)
