# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common
from odoo.tests import HttpCase


class TestEmbedDetection(HttpCase, common.SlidesCase):

    @classmethod
    def setUpClass(cls):
        super(TestEmbedDetection, cls).setUpClass()

        cls.website = cls.env['website'].create({
            'name': 'Test Website',
            'domain': 'https://testwebsite.com'
        })

        cls.channel.website_id = cls.website.id

    def test_embed_external_no_referer(self):
        """ When hitting the external URL without a referer header, the global embed record is
        incremented. """
        self.url_open(f'/slides/embed_external/{self.slide.id}')
        embed_views = self.env['slide.embed'].search([('slide_id', '=', self.slide.id)])
        self.assertEqual(len(embed_views), 1)
        self.assertEqual(embed_views.website_name, 'Unknown Website')

    def test_embed_external_referer(self):
        """ When hitting the external URL with a referer header, the embed record is incremented
        based on the referer URL. """

        self.assertFalse(bool(self.env['slide.embed'].search([
            ('slide_id', '=', self.slide.id)
        ])))

        self.url_open(
            f'/slides/embed_external/{self.slide.id}',
            headers={'Referer': 'https://someexternalwebsite.com'}
        )

        embed_views = self.env['slide.embed'].search([('slide_id', '=', self.slide.id)])
        self.assertEqual(len(embed_views), 1)
        self.assertEqual(embed_views.count_views, 1)
        self.assertEqual(embed_views.website_name, 'https://someexternalwebsite.com')

    def test_embed_not_external(self):
        """ When hitting the non-external URL, we should not add a slide_embed record. """
        self.url_open(f'/slides/embed/{self.slide.id}')
        self.assertFalse(bool(self.env['slide.embed'].search([
            ('slide_id', '=', self.slide.id)
        ])))
