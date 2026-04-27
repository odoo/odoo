# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, HttpCase
from odoo.addons.helpdesk.tests.common import HelpdeskCommon

@tagged('-at_install', 'post_install')
class TestHelpdeskSlides(HttpCase, HelpdeskCommon):
    def test_top_channels(self):
        # We first create 7 different channels for our knowledge centre / helpdesk team
        slide_channels = self.env['slide.channel'].create([{
            'name': f'This is channel number {channel_record}',
            'website_published': True,
        } for channel_record in range(1, 8)])

        # Then we need to create some partners for the slide.slide.partner model...
        slide_partners = self.env['res.partner'].create([{
            'name': f"Theodore the {index}'th",
        } for index in range(0, 28)])

        # Now lets create the some slides for our channels
        slides = self.env['slide.slide'].create([{
            'name': f'Slide for channel number {slide_record + 1}',
            'channel_id': slide_channels[slide_record].id,
            'is_published': True,
        } for slide_record in range(0, 7)])

        # Finally it's time to create the slide.slide.partner records for each of the slides (these will count as views)
        partner_ids = slide_partners.ids
        self.env['slide.slide.partner'].create([{
            'slide_id': slide_value.id,
            'partner_id': partner_ids.pop(),
        } for index, slide_value in enumerate(slides) for _ in range(index + 1)])

        self.test_team.website_slide_channel_ids = slide_channels.ids

        self.test_team.invalidate_recordset(['website_top_channels'])

        self.assertEqual(self.test_team.website_top_channels, slide_channels[6:1:-1], 'The top channels should be the ones with the most views, in this case the last 5 from last to first')
