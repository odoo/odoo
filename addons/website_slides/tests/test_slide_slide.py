# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common as slides_common


class TestSlideInternals(slides_common.SlidesCase):

    def test_change_content_type(self):
        """ To prevent constraint violation when changing type from video to article and vice-versa """
        slide = self.env['slide.slide'].create({
            'name': 'dummy',
            'channel_id': self.channel.id,
            'slide_category': 'video',
            'is_published': True,
            'url': 'https://youtu.be/W0JQcpGLSFw',
        })

        slide.write({'slide_category': 'article', 'html_content': '<p>Hello</p>'})
        self.assertTrue(slide.html_content)
        self.assertFalse(slide.url)

        slide.slide_category = 'document'
        self.assertFalse(slide.html_content)
