# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html
from werkzeug.urls import url_encode

from odoo.tests import HttpCase, tagged
from odoo.addons.website.tools import MockRequest
from odoo.tests.common import HOST
from odoo.tools import config


@tagged('post_install', '-at_install', 'website_snippets')
class TestSnippets(HttpCase):

    def test_01_empty_parents_autoremove(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'snippet_empty_parent_autoremove', login='admin')

    def test_02_default_shape_gets_palette_colors(self):
        self.start_tour('/@/', 'default_shape_gets_palette_colors', login='admin')

    def test_03_snippets_all_drag_and_drop(self):
        with MockRequest(self.env, website=self.env['website'].browse(1)):
            snippets_template = self.env['ir.ui.view'].render_public_asset('website.snippets')
        html_template = html.fromstring(snippets_template)
        data_snippet_els = html_template.xpath("//*[@class='o_panel' and not(contains(@class, 'd-none'))]//*[@data-snippet]")
        blacklist = [
            's_facebook_page',  # avoid call to external services (facebook.com)
            's_map',  # avoid call to maps.google.com
            's_instagram_page',  # avoid call to instagram.com
        ]
        snippets_names = ','.join(set(el.attrib['data-snippet'] for el in data_snippet_els if el.attrib['data-snippet'] not in blacklist))
        snippets_names_encoded = url_encode({'snippets_names': snippets_names})
        path = url_encode({
            'path': '/?' + snippets_names_encoded
        })
        self.start_tour("/web#action=website.website_preview&%s" % path, "snippets_all_drag_and_drop", login='admin', timeout=300)

    def test_04_countdown_preview(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'snippet_countdown', login='admin')

    def test_05_social_media(self):
        IrAttachment = self.env['ir.attachment']
        base = "http://%s:%s" % (HOST, config['http_port'])
        IrAttachment.create({
            'public': True,
            'name': 's_banner_default_image.jpg',
            'type': 'url',
            'url': base + '/web/image/website.s_banner_default_image',
        })
        self.start_tour(self.env['website'].get_client_action_url('/'), 'snippet_social_media', login="admin")
        self.assertEqual(
            self.env['website'].browse(1).social_instagram,
            'https://instagram.com/odoo.official/',
            'Social media should have been updated'
        )

    def test_06_snippet_popup_add_remove(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'snippet_popup_add_remove', login='admin')

    def test_07_image_gallery(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'snippet_image_gallery', login='admin')

    def test_08_table_of_content(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'snippet_table_of_content', login='admin')

    def test_09_snippet_image_gallery(self):
        IrAttachment = self.env['ir.attachment']
        base = "http://%s:%s" % (HOST, config['http_port'])
        IrAttachment.create({
            'public': True,
            'name': 's_default_image.jpg',
            'type': 'url',
            'url': base + '/web/image/website.s_banner_default_image.jpg',
        })
        IrAttachment.create({
            'public': True,
            'name': 's_default_image2.jpg',
            'type': 'url',
            'url': base + '/web/image/website.s_banner_default_image.jpg',
        })
        self.start_tour("/", "snippet_image_gallery_remove", login='admin')

    def test_10_parallax(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'test_parallax', login='admin')

    def test_11_snippet_popup_display_on_click(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'snippet_popup_display_on_click', login='admin')

    def test_12_snippet_images_wall(self):
        self.start_tour('/', 'snippet_images_wall', login='admin')

    def test_snippet_popup_with_scrollbar_and_animations(self):
        website = self.env.ref('website.default_website')
        website.cookies_bar = True
        self.start_tour(self.env['website'].get_client_action_url('/'), 'snippet_popup_and_scrollbar', login='admin')
        self.start_tour(self.env['website'].get_client_action_url('/'), 'snippet_popup_and_animations', login='admin')

    def test_drag_and_drop_on_non_editable(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'test_drag_and_drop_on_non_editable', login='admin')
