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
        self.assertEqual(channel_publisher.nbr_infographics, len(channel_publisher.slide_ids.filtered(lambda s: s.slide_type == 'infographic')))
        self.assertEqual(channel_publisher.nbr_presentations, len(channel_publisher.slide_ids.filtered(lambda s: s.slide_type == 'presentation')))
        self.assertEqual(channel_publisher.nbr_documents, len(channel_publisher.slide_ids.filtered(lambda s: s.slide_type == 'document')))
        self.assertEqual(channel_publisher.nbr_videos, len(channel_publisher.slide_ids.filtered(lambda s: s.slide_type == 'video')))
        # slide statistics computation
        self.assertEqual(float_compare(channel_publisher.total_time, sum(s.completion_time for s in channel_publisher.slide_ids), 3), 0)

    @mute_logger('odoo.models')
    def test_channel_user_statistics(self):
        channel_publisher = self.channel.sudo(self.user_publisher)
        channel_publisher.write({
            'visibility': 'invite',
        })
        channel_publisher._action_add_member(self.user_emp.partner_id)

        slides_emp = (self.slide | self.slide_2).sudo(self.user_emp)
        slides_emp.action_view()
        channel_emp = self.channel.sudo(self.user_emp)
        self.assertEqual(channel_emp.completion, math.ceil(100.0 * len(slides_emp) / len(channel_publisher.slide_ids)))
