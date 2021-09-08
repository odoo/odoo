# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.tests import HttpCase


class TestEmbedDetection(HttpCase):

    def setUp(self):
        super(TestEmbedDetection, self).setUp()
        self.website_true_url = self.env['website'].create({
            'name': 'a_website',
            'domain': 'https://trueurl.com'
        })
        self.website_other = self.env['website'].create({
            'name': 'another_website',
            'domain': 'https://otherurl.com'
        })

        self.channel_with_website = self.env['slide.channel'].create({
            'name': 'Website Channel',
            'promote_strategy': 'most_voted',
            'visibility': 'public',
            'is_published': True,
            'website_id': self.website_true_url.id
        })
        self.channel_with_another_website = self.env['slide.channel'].create({
            'name': 'Another Website Channel',
            'promote_strategy': 'most_voted',
            'visibility': 'public',
            'is_published': True,
            'website_id': self.website_other.id
        })
        self.channel_no_website = self.env['slide.channel'].create({
            'name': 'Test Channel',
            'promote_strategy': 'most_voted',
            'visibility': 'public',
            'is_published': True,
        })

        self.slide_no_website = self.env['slide.slide'].create({
            'name': 'Radioactive meditation : The Art of Growing a Third Ear with your Mind',
            'channel_id': self.channel_no_website.id,
            'slide_type': 'document',
            'is_published': True,
        })
        self.slide_website = self.env['slide.slide'].create({
            'name': 'Biology 101 : How to create Zombies',
            'channel_id': self.channel_with_website.id,
            'slide_type': 'document',
            'is_published': True,
        })

        self.csrf_token_data = {'csrf_token': http.WebRequest.csrf_token(self)}

    def test_01_no_referer_no_website_id(self):
        """
        No referer, slide available for all websites -> Not embedded
        """
        headers = {
            'Referer': ''
        }
        embeds = self.env['slide.embed'].search([])
        self.url_open(f'/slides/embed/{self.slide_no_website.id}', data=self.csrf_token_data, headers=headers)
        new_embeds = self.env['slide.embed'].search([])
        self.assertEqual(embeds, new_embeds, "There is no referer, we will assume it's not embedded")

    def test_02_no_referer_with_website(self):
        """
        No referer, slide just available for one website -> Not embedded
        """
        headers = {
            'Referer': ''
        }
        embeds = self.env['slide.embed'].search([])
        self.url_open(f'/slides/embed/{self.slide_website.id}', data=self.csrf_token_data, headers=headers)
        new_embeds = self.env['slide.embed'].search([])
        self.assertEqual(embeds, new_embeds, "There is no referer, we will assume it's not embedded")

    def test_03_referer_ill_formed(self):
        """
        No usable information in the referer -> Not embedded
        """
        headers = {
            'Referer': 'hello'
        }
        embeds = self.env['slide.embed'].search([])
        self.url_open(f'/slides/embed/{self.slide_no_website.id}', data=self.csrf_token_data, headers=headers)
        new_embeds = self.env['slide.embed'].search([])
        self.assertEqual(embeds, new_embeds, "No usable information in the referer (and no website), we will assume it's not embedded")

        embeds = self.env['slide.embed'].search([])
        self.url_open(f'/slides/embed/{self.slide_website.id}', data=self.csrf_token_data, headers=headers)
        new_embeds = self.env['slide.embed'].search([])
        self.assertEqual(embeds, new_embeds, "No usable information in the referer (and website), we will assume it's not embedded")

    def test_04_referer_outside_no_website(self):
        """
        Referer outside of DB and no website_id -> Embedded
        """
        headers = {
            'Referer': 'https://jagnkjllngnlnafja.com'
        }
        embeds = self.env['slide.embed'].search([])
        self.url_open(f'/slides/embed/{self.slide_no_website.id}', data=self.csrf_token_data, headers=headers)
        new_embeds = self.env['slide.embed'].search([])
        self.assertNotEqual(embeds, new_embeds, "That website is not part of the domains of the DB, so embedded")

    def test_05_referer_outside_with_website(self):
        """
        Referer outside of DB and website_id -> Embedded
        """
        headers = {
            'Referer': 'https://jagnkjllngnlnafja.com'
        }
        embeds = self.env['slide.embed'].search([])
        self.url_open(f'/slides/embed/{self.slide_website.id}', data=self.csrf_token_data, headers=headers)
        new_embeds = self.env['slide.embed'].search([])
        self.assertNotEqual(embeds, new_embeds, "That website is not equal to the website domain, so embedded")

    def test_06_referer_inside_no_website(self):
        """
        Referer inside of the DB and no website_id (available for all websites) -> Not Embedded
        """
        headers = {
            'Referer': self.website_true_url.domain
        }
        embeds = self.env['slide.embed'].search([])
        self.url_open(f'/slides/embed/{self.slide_no_website.id}', data=self.csrf_token_data, headers=headers)
        new_embeds = self.env['slide.embed'].search([])
        self.assertEqual(embeds, new_embeds, "That website is part of the domains of the DB and the slide is available for all domains, so not embedded")

    def test_07_referer_inside_correct_website(self):
        """
        Referer inside of DB and correspond to the slide website -> Not embedded
        """
        headers = {
            'Referer': self.website_true_url.domain
        }
        embeds = self.env['slide.embed'].search([])
        self.url_open(f'/slides/embed/{self.slide_website.id}', data=self.csrf_token_data, headers=headers)
        new_embeds = self.env['slide.embed'].search([])
        self.assertEqual(embeds, new_embeds, "That website is equal to the slide website, so not embedded")

    def test_08_referer_inside_incorrect_website(self):
        """
        Referer outside of DB and website_id -> Embedded
        """
        headers = {
            'Referer': self.website_true_url.domain
        }
        self.slide_website.channel_id = self.channel_with_another_website

        embeds = self.env['slide.embed'].search([])
        self.url_open(f'/slides/embed/{self.slide_website.id}', data=self.csrf_token_data, headers=headers)
        new_embeds = self.env['slide.embed'].search([])
        self.assertNotEqual(embeds, new_embeds, "That website is not equal to the slide website, so embedded")

    def test_09_longer_referer_inside_correct_website(self):
        """
        Testing for referer_url equality will fail this test, since it's here to test that we actually check for the
        domain of the referer url
        Referer inside the correct website but with a longer URL -> Not embedded
        """
        headers = {
            'Referer': self.website_true_url.domain + '/some_page/with_html.html'
        }
        embeds = self.env['slide.embed'].search([])
        self.url_open(f'/slides/embed/{self.slide_website.id}', data=self.csrf_token_data, headers=headers)
        new_embeds = self.env['slide.embed'].search([])
        self.assertEqual(embeds, new_embeds, "That website is equal to the slide website, so not embedded")
