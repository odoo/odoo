# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common as slides_common


class TestSlideInternals(slides_common.SlidesCase):

    def test_change_content_type(self):
        """ To prevent constraint violation when changing type from video to webpage and vice-versa """
        slide = self.env['slide.slide'].create({
            'channel_id': self.channel.id,
            'slide_type': 'video',
            'is_published': True,
            'url': 'https://youtu.be/W0JQcpGLSFw',
        })

        slide.write({'slide_type': 'webpage', 'html_content': '<p>Hello</p>'})
        self.assertTrue(slide.html_content)
        self.assertFalse(slide.url)

        slide.slide_type = 'document'
        self.assertFalse(slide.html_content)
