# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo.tools import config


@odoo.tests.common.tagged('post_install', '-at_install')
class TestWebsiteAssets(odoo.tests.HttpCase):

    def test_01_multi_domain_assets_generation(self):
        Website = self.env['website']
        Attachment = self.env['ir.attachment']
        # Create an additional website to ensure it works in multi-website setup
        Website.create({'name': 'Second Website'})
        # Simulate single website DBs: make sure other website do not interfer
        # (We can't delete those, constraint will most likely be raised)
        [w.write({'domain': f'inactive-{w.id}.test'}) for w in Website.search([])]
        # Don't use HOST, hardcode it so it doesn't get changed one day and make
        # the test useless
        domain_1 = "http://127.0.0.1:%s" % config['http_port']
        domain_2 = "http://localhost:%s" % config['http_port']
        Website.browse(1).domain = domain_1

        self.authenticate('admin', 'admin')
        self.env['web_editor.assets'].with_context(website_id=1).make_scss_customization(
            '/website/static/src/scss/options/colors/user_color_palette.scss',
            {"o-cc1-bg": "'400'"},
        )

        def get_last_backend_asset_attach_id():
            return Attachment.search([
                ('name', '=', 'web.assets_backend.min.js'),
            ], order="id desc", limit=1).id

        def check_asset():
            self.assertEqual(last_backend_asset_attach_id, get_last_backend_asset_attach_id())

        last_backend_asset_attach_id = get_last_backend_asset_attach_id()

        # The first call will generate the assets and populate the cache and
        # take ~100 SQL Queries (~cold state).
        # Any later call to `/web`, regardless of the domain, will take only
        # ~10 SQL Queries (hot state).
        # Without the calls the `check_asset()` (which would raise early and
        # would not call other `url_open()`) and before the fix coming with this
        # test, here is the logs:
        #      "GET /web HTTP/1.1" 200 - 222 0.135 3.840  <-- 222 Queries, ~4s
        #      "GET /web HTTP/1.1" 200 - 181 0.101 3.692  <-- 181 Queries, ~4s
        #      "GET /web HTTP/1.1" 200 - 215 0.121 3.704  <-- 215 Queries, ~4s
        #      "GET /web HTTP/1.1" 200 - 181 0.100 3.616  <-- 181 Queries, ~4s
        # After the fix, here is the logs:
        #      "GET /web HTTP/1.1" 200 - 101 0.043 0.353  <-- 101 Queries, ~0.3s
        #      "GET /web HTTP/1.1" 200 - 11 0.004 0.007   <--  11 Queries, ~10ms
        #      "GET /web HTTP/1.1" 200 - 11 0.003 0.005   <--  11 Queries, ~10ms
        #      "GET /web HTTP/1.1" 200 - 11 0.003 0.008   <--  11 Queries, ~10ms
        self.url_open(domain_1 + '/web')
        check_asset()
        self.url_open(domain_2 + '/web')
        check_asset()
        self.url_open(domain_1 + '/web')
        check_asset()
        self.url_open(domain_2 + '/web')
        check_asset()
        self.url_open(domain_1 + '/web')
        check_asset()

    def test_02_multi_domain_assets_generation(self):
        # Create an additional website to ensure it works in multi-website setup
        website2 = self.env['website'].create({'name': 'Second Website'})

        self.authenticate('admin', 'admin')
        # Edit one of the website to force assets to be different
        self.env['web_editor.assets'].with_context(website_id=1).make_scss_customization(
            '/website/static/src/scss/options/colors/user_color_palette.scss',
            {"o-cc1-bg": "'400'"},
        )

        def get_backend_asset_attach():
            return self.env['ir.attachment'].search([('name', '=', 'web.assets_backend.min.js')])

        self.url_open('/website/force/1')
        self.url_open('/web')
        asset_website1 = get_backend_asset_attach().filtered(lambda r: r.website_id.id == 1)
        self.assertIn(1, get_backend_asset_attach().mapped('website_id').ids)
        self.url_open('/website/force/%s' % website2.id)
        self.url_open('/web')
        asset_website2 = get_backend_asset_attach().filtered(lambda r: r.website_id.id == website2.id)
        self.assertIn(1, get_backend_asset_attach().mapped('website_id').ids)
        self.assertIn(website2.id, get_backend_asset_attach().mapped('website_id').ids)
        self.url_open('/website/force/1')
        self.url_open('/web')
        self.assertIn(1, get_backend_asset_attach().mapped('website_id').ids)
        self.assertIn(website2.id, get_backend_asset_attach().mapped('website_id').ids)
        self.url_open('/website/force/%s' % website2.id)
        self.url_open('/web')
        self.assertEqual(asset_website1, get_backend_asset_attach().filtered(lambda r: r.website_id.id == 1))
        self.assertEqual(asset_website2, get_backend_asset_attach().filtered(lambda r: r.website_id.id == website2.id))
