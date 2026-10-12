# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
from datetime import datetime

from PIL import Image

from odoo.exceptions import AccessError
from odoo.tests import HttpCase, new_test_user, tagged

from odoo.addons.http_routing.tests.common import MockRequest


@tagged('post_install', '-at_install')
class TestWebsiteDuplicate(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('fr_FR')
        cls.source_website = cls.env['website'].create({'name': 'Source Website', 'domain': 'https://source.example.com'})
        website_id = cls.source_website.id
        View = cls.env['ir.ui.view']
        layout = cls.env.ref('website.layout')

        block_view = View.create({
            'name': 'Z block', 'type': 'qweb', 'inherit_id': layout.id, 'website_id': website_id,
            'arch': '<xpath expr="//main" position="before"><div id="o_test_block"/></xpath>',
        })
        View.create([{
            'name': 'Z block content', 'type': 'qweb', 'inherit_id': block_view.id, 'website_id': website_id,
            'arch': '<xpath expr="//div[@id=\'o_test_block\']" position="inside"><div id="o_test_child"/></xpath>',
        }, {
            'name': 'A block class', 'type': 'qweb', 'inherit_id': layout.id, 'website_id': website_id,
            'arch': '<xpath expr="//div[@id=\'o_test_child\']" position="inside"><div class="o_test_class"/></xpath>',
        }])
        # an option of the layout, turned off on the source website only
        option_view = View.create({
            'name': 'Option', 'type': 'qweb', 'key': 'website.test_duplicate_option', 'inherit_id': layout.id,
            'arch': '<xpath expr="//main" position="before"><div class="o_test_option"/></xpath>',
        })
        option_view.with_context(website_id=website_id).active = False

        cls.page = cls.env['website.page'].create({
            'name': 'Duplicate Page', 'type': 'qweb', 'url': '/duplicate-page', 'website_id': website_id,
            'is_published': True, 'published_date': datetime(2026, 1, 1),
            'arch': '<t t-call="website.layout"><div id="wrap">Duplicate page content</div></t>',
        })
        cls.page.update_field_translations('url', {'fr_FR': '/page-dupliquee'})
        cls.menu = cls.env['website.menu'].create({
            'name': 'Duplicate Menu', 'page_id': cls.page.id, 'parent_id': cls.source_website.menu_id.id,
            'website_id': website_id,
        })

    def assertCopied(self, new_website, record, domain=(), fnames=()):
        """ Check that ``record`` is copied once onto ``new_website``, with the
        same values for ``fnames``, and return its copy. """
        copy = record.with_context(active_test=False).search([('website_id', '=', new_website.id), *domain])
        self.assertEqual(len(copy), 1, f"{record} should be copied once")
        for fname in fnames:
            self.assertEqual(copy[fname], record[fname], f"{record}.{fname} should be kept")
        return copy

    def test_duplicate_website(self):
        other_website = self.env['website'].create({'name': 'Other Website'})

        self.env['website.duplicate'].with_context(active_ids=[self.source_website.id, other_website.id]).create({
            'name': 'New Website',
        }).action_duplicate()

        new_websites = self.env['website'].search([('id', '>', other_website.id)], order='id')
        self.assertEqual(new_websites.mapped('name'), ['New Website', 'New Website 2'])
        new_website = new_websites[0]
        View = self.env['ir.ui.view'].with_context(active_test=False)
        self.assertEqual(
            sorted(View.search([('website_id', '=', new_website.id)]).mapped('key')),
            sorted(View.search([('website_id', '=', self.source_website.id)]).mapped('key')),
        )

        new_website.domain = self.base_url()
        page = self.url_open('/duplicate-page').text
        self.assertIn(f'data-website-id="{new_website.id}"', page)
        self.assertIn('Duplicate page content', page)
        self.assertIn('Duplicate Menu', page)
        self.assertIn('o_test_class', page, "The customizations of the source apply on the copy")
        self.assertNotIn('o_test_option', page, "The option turned off on the source is off on the copy")

    def test_duplicate_website_content(self):
        source_website = self.source_website
        theme_view = self.env['theme.ir.ui.view'].create({'name': 'Theme View'})
        self.page.view_id.theme_template_id = theme_view
        self.page.theme_template_id = self.env['theme.website.page'].create({'view_id': theme_view.id})
        self.menu.theme_template_id = self.env['theme.website.menu'].create({'name': 'Theme Menu'})
        protected_page = self.env['website.page'].create({
            'name': 'Protected Page', 'type': 'qweb', 'url': '/duplicate-protected', 'website_id': source_website.id,
            'arch': '<div/>', 'parent_id': self.page.id, 'publish_on': datetime(2099, 1, 1),
            'visibility': 'password', 'visibility_password_display': 'secret',
        })
        listing_view, record_view = self.env['ir.ui.view'].create([{
            'name': name, 'type': 'qweb', 'model': 'res.partner', 'website_id': source_website.id, 'arch': '<div/>',
        } for name in ['Duplicate Listing', 'Duplicate Record']])
        controller_page = self.env['website.controller.page'].create({
            'name': 'Duplicate Partners', 'name_slugified': 'our-partners', 'view_id': listing_view.id,
            'record_view_id': record_view.id, 'website_published': True,
        })
        listing_view.name = 'Partners Listing'
        controller_menu = self.env['website.menu'].create({
            'name': 'Duplicate Partners', 'controller_page_id': controller_page.id,
            'parent_id': source_website.menu_id.id, 'website_id': source_website.id,
        })
        # outside the navigation, like the menus of an event
        outside_menu = self.env['website.menu'].create({'name': 'Duplicate Event', 'website_id': source_website.id})
        asset = self.env['ir.asset'].create({
            'name': 'Duplicate Asset', 'key': 'website.test_duplicate_asset', 'bundle': 'web.assets_frontend',
            'path': 'website/static/src/scss/test_duplicate.scss', 'website_id': source_website.id,
            'theme_template_id': self.env['theme.ir.asset'].create({
                'name': 'Theme Asset', 'bundle': 'web.assets_frontend', 'path': 'test_duplicate.scss',
            }).id,
        })
        theme_attachment, custom_attachment, other_attachment = self.env['ir.attachment'].create([{
            'name': 'theme.png', 'key': 'website.test_duplicate_image', 'raw': b'theme', 'website_id': source_website.id,
            'theme_template_id': self.env['theme.ir.attachment'].create({'name': 'Theme', 'key': 'test_duplicate'}).id,
        }, {
            'name': 'test_duplicate.scss', 'url': '/_custom/web.assets_frontend/website/test_duplicate.scss',
            'raw': b'body {}', 'website_id': source_website.id,
        }, {
            'name': 'other.png', 'raw': b'other', 'website_id': source_website.id,
        }])
        rewrite = self.env['website.rewrite'].create({
            'name': 'Duplicate Redirection', 'redirect_type': '301',
            'url_from': '/duplicate-old', 'url_to': '/duplicate-page',
            'website_id': source_website.id,
        })
        source_website.cookie_policy_id = self.page

        new_website = source_website.copy()

        new_page = self.assertCopied(new_website, self.page, [('url', '=', '/duplicate-page')],
                                     ['is_published', 'published_date', 'theme_template_id'])
        self.assertEqual(new_page.with_context(lang='fr_FR').url, '/page-dupliquee')
        self.assertEqual(new_page.view_id.theme_template_id, theme_view)
        self.assertEqual(new_website.cookie_policy_id, new_page)
        new_protected_page = self.assertCopied(new_website, protected_page, [('url', '=', '/duplicate-protected')],
                                               ['is_published', 'publish_on', 'visibility'])
        self.assertEqual(new_protected_page.parent_id, new_page)
        self.assertEqual(new_protected_page.sudo().visibility_password, protected_page.sudo().visibility_password)

        new_menu = self.assertCopied(new_website, self.menu, [('page_id', '=', new_page.id)], ['theme_template_id'])
        self.assertEqual(new_menu.parent_id, new_website.menu_id)
        self.assertEqual(self.env.ref(new_website._website_xmlid('website.main_menu')), new_website.menu_id)

        new_controller_page = self.assertCopied(new_website, controller_page, (),
                                                ['name', 'name_slugified', 'website_published'])
        self.assertEqual(new_controller_page.record_view_id.website_id, new_website)
        self.assertCopied(new_website, controller_menu, [('controller_page_id', '=', new_controller_page.id)])
        self.assertFalse(outside_menu.search([('website_id', '=', new_website.id), ('name', '=', outside_menu.name)]),
                         "Only the navigation menus are copied")

        self.assertCopied(new_website, asset, (), ['key', 'theme_template_id'])
        self.assertCopied(new_website, theme_attachment, [('key', '!=', False)], ['checksum', 'theme_template_id'])
        self.assertCopied(new_website, custom_attachment, [('url', '=', custom_attachment.url)], ['checksum'])
        self.assertFalse(self.env['ir.attachment'].search([
            ('website_id', '=', new_website.id), ('name', '=', other_attachment.name),
        ]), "Only the theme and customized assets files are copied")
        self.assertCopied(new_website, rewrite, (), ['url_from'])

    def test_duplicate_website_images(self):
        def create_image(**values):
            image = io.BytesIO()
            Image.new('RGB', (4, 4), 'red').save(image, 'PNG')
            return self.env['ir.attachment'].create({
                'name': 'duplicate.png', 'raw': image.getvalue(), 'public': True, 'res_model': 'ir.ui.view',
                'website_id': self.source_website.id, **values,
            })

        uploaded_image = create_image()
        theme_image = create_image(key='website.test_duplicate_image')
        form_file = create_image(res_model='res.partner')

        new_website = self.source_website.copy()

        self.assertFalse(uploaded_image.website_id, "The images uploaded on the source are shared with the copy")
        self.assertEqual([theme_image.website_id, form_file.website_id], [self.source_website] * 2,
                         "Only the uploaded images are shared")

        # the images of the copied pages can be modified from the new website,
        # e.g. cropped
        new_website.domain = self.base_url()
        self.authenticate('admin', 'admin')
        cropped_image = self.make_jsonrpc_request(f'/html_editor/modify_image/{uploaded_image.id}', {
            'data': base64.b64encode(uploaded_image.raw).decode(), 'mimetype': 'image/png', 'name': 'duplicate.png',
        })
        self.assertEqual(self.url_open(cropped_image['original']).headers['Content-Type'], 'image/png')

    def test_duplicate_website_308_redirection(self):
        # the redirections are added to the routing during a request only, and
        # on a running server the routing exists before a redirection is added
        with MockRequest(self.env, website=self.source_website) as request:
            request.env['ir.http'].routing_map()
            request.env['website.rewrite'].create({
                'redirect_type': '308', 'url_from': '/website/info', 'url_to': '/website/information',
                'website_id': self.source_website.id,
            })
            new_website = self.source_website.with_env(request.env).copy()

        new_rewrite = self.env['website.rewrite'].search([('website_id', '=', new_website.id)])
        self.assertEqual(new_rewrite.url_to, '/website/information')

    def test_duplicate_website_access(self):
        designer = new_test_user(self.env, 'duplicate_designer', groups='base.group_user,website.group_website_designer')
        with self.assertRaisesRegex(AccessError, "Only administrators can duplicate a website."):
            self.source_website.with_user(designer).copy()

    def test_duplicate_website_settings(self):
        # API keys, or bound to the domain of the source or to its analytics
        # accounts, like the Google Tag Manager code of the custom code
        source_settings = {
            'google_analytics_key': 'G-DUPLICATE',
            'google_search_console': 'google1234567890123456.html',
            'google_maps_api_key': 'duplicate',
            'plausible_site': 'source.example.com',
            'plausible_shared_key': 'duplicate',
            'custom_code_head': '<script id="o_test_gtm"/>',
            'custom_code_footer': '<noscript id="o_test_gtm"/>',
        }
        self.source_website.write(source_settings)

        new_website = self.source_website.copy()
        self.assertEqual((new_website.name, new_website.domain), ('Source Website (copy)', False))
        self.assertEqual([fname for fname in source_settings if new_website[fname]], [],
                         "The API keys and the settings bound to the domain of the source are not copied")

        new_website = self.source_website.copy({'domain': 'https://copy.example.com'})
        self.assertEqual(new_website.domain, 'https://copy.example.com')
