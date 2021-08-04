# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common as slides_common
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_slides.controllers.main import WebsiteSlides


class TestEmbedDetection(slides_common.SlidesCase):

    def setUp(self):
        super(TestEmbedDetection, self).setUp()

        self.website = self.env['website'].search([])[0]
        self.website.domain = "https://example.com/"
        self.slide = self.slide_3

    def test_embed_no_referer(self):
        with MockRequest(self.env, website=self.website):
            embeds = self.env['slide.embed'].search([])
            WebsiteSlides().slides_embed(self.slide.id)
            new_embeds = self.env['slide.embed'].search([])
            self.assertEqual(embeds, new_embeds, "There is no referrer url, we will assume that the slide is not embedded")

    def test_embed_db_url_referer(self):
        with MockRequest(self.env, website=self.website, headers={'Referer': 'https://google.com/'}):
            embeds = self.env['slide.embed'].search([])
            WebsiteSlides().slides_embed(self.slide.id)
            new_embeds = self.env['slide.embed'].search([])
            self.assertEqual(len(embeds), len(new_embeds) - 1, "The referer is https://google.com/ which is not in the domains, so the slide is embedded")

    def test_embed_inside_domain_url_referer(self):
        with MockRequest(self.env, website=self.website, headers={'Referer': 'https://example.com/'}):
            embeds = self.env['slide.embed'].search([])
            WebsiteSlides().slides_embed(self.slide.id)
            new_embeds = self.env['slide.embed'].search([])
            self.assertEqual(embeds, new_embeds, "The referer is the same as the domain of the website, so the slide is not embedded")
