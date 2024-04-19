# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

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

    def test_02_t_cache_invalidation(self):
        self.authenticate(None, None)
        page = self.url_open('/').text # add to cache
        public_assets_links = re.findall(r'(/web/assets/\d+/\w{7}/web.assets_frontend\..+)"/>', page)
        self.assertTrue(public_assets_links)
        self.authenticate('admin', 'admin')
        page = self.url_open('/').text
        admin_assets_links = re.findall(r'(/web/assets/\d+/\w{7}/web.assets_frontend\..+)"/>', page)
        self.assertTrue(admin_assets_links)

        self.assertEqual(public_assets_links, admin_assets_links)

        snippets = self.env['ir.asset'].search([
            ('path', '=like', 'website/static/src/snippets/s_social_media/000.scss'), # arbitrary, a unused css one that doesn't make the page fail when archived.
            ('bundle', '=', 'web.assets_frontend'),
        ])
        self.assertTrue(snippets)
        write_dates = snippets.mapped('write_date')
        snippets.write({'active': False})
        snippets.flush_recordset()
        self.assertNotEqual(write_dates, snippets.mapped('write_date'))

        page = self.url_open('/').text
        new_admin_assets_links = re.findall(r'(/web/assets/\d+/\w{7}/web.assets_frontend\..+)"/>', page)
        self.assertTrue(new_admin_assets_links)

        self.assertEqual(public_assets_links, admin_assets_links)
        self.assertNotEqual(new_admin_assets_links, admin_assets_links, "we expect a change since ir_assets were written")

        self.authenticate(None, None)
        page = self.url_open('/').text

        new_public_assets_links = re.findall(r'(/web/assets/\d+/\w{7}/web.assets_frontend\..+)"/>', page)
        self.assertEqual(new_admin_assets_links, new_public_assets_links, "t-cache should have been invalidated for public user too")

    def test_invalid_unlink(self):
        self.env['ir.attachment'].search([('url', '=like', '/web/assets/%')]).unlink()

        asset_bundle_xmlid = 'web.assets_frontend'
        website_default = self.env['website'].search([], limit=1)

        code = b"document.body.dataset.hello = 'world';"
        attach = self.env['ir.attachment'].create({
            'name': 'EditorExtension.css',
            'mimetype': 'text/css',
            'raw': code,
        })
        custom_url = '/_custom/web/content/%s/%s' % (attach.id, attach.name)
        attach.url = custom_url

        self.env['ir.asset'].create({
            'name': 'EditorExtension',
            'bundle': asset_bundle_xmlid,
            'path': custom_url,
            'website_id': website_default.id,
        })

        website_bundle = self.env['ir.qweb']._get_asset_bundle(asset_bundle_xmlid, assets_params={'website_id': website_default.id})
        self.assertIn(custom_url, [f['url'] for f in website_bundle.files])
        base_website_css_version = website_bundle.get_version('css')

        no_website_bundle = self.env['ir.qweb']._get_asset_bundle(asset_bundle_xmlid)
        self.assertNotIn(custom_url, [f['url'] for f in no_website_bundle.files])
        self.assertNotEqual(no_website_bundle.get_version('css'), base_website_css_version)

        website_attach = website_bundle.css()
        self.assertTrue(website_attach.exists())
        no_website_bundle.css()
        self.assertTrue(website_attach.exists(), 'attachment for website should still exist after generating attachment for no website')


@odoo.tests.tagged('-at_install', 'post_install')
class TestWebAssets(odoo.tests.HttpCase):
    def test_assets_url_validation(self):
        website_id = self.env['website'].search([], limit=1, order='id desc').id

        with odoo.tools.mute_logger('odoo.addons.web.controllers.binary'):
            self.assertEqual(
                self.url_open(f'/web/assets/{website_id}/debug/hello/web.assets_frontend.css', allow_redirects=False).status_code,
                404,
                "unexpected direction extra",
            )
            self.assertEqual(
                self.url_open(f'/web/assets/{website_id}/debug/web.assets_f_ontend.js', allow_redirects=False).status_code,
                404,
                "bundle name contains `_` and should be escaped wildcard",
            )
            self.assertEqual(
                self.url_open(f'/web/assets/{website_id}/debug/web.assets_frontend.rtl.js', allow_redirects=False).status_code,
                404,
                "js cannot have `rtl` has extra",
            )
            self.assertEqual(
                self.url_open(f'/web/assets/{website_id}/debug/web.assets_frontend.rtl.js', allow_redirects=False).status_code,
                404,
                "js cannot have `rtl` has extra",
            )
            self.assertEqual(
                self.url_open(f'/web/{website_id+1}/assets/debug/web.assets_frontend.css', allow_redirects=False).status_code,
                404,
                "website_id does not exist",
            )
            self.assertEqual(
                self.url_open(f'/web/assets/{website_id}/debug/web.assets_frontend.aa.css', allow_redirects=False).status_code,
                404,
                "invalid direction",
            )
            self.assertEqual(
                self.url_open(f'/web/assets/{website_id}/any/web.assets_frontend.min.rtl.css', allow_redirects=False).status_code,
                404,
                "min and direction inverted",
            )
            self.assertEqual(
                self.url_open(f'/web/assets/{website_id}/any/web.assets_frontend.js', allow_redirects=False).status_code,
                404,
                "missing min in non debug mode",
            )

        self.assertEqual(
            self.url_open('/web/assets/debug/web.assets_frontend.css', allow_redirects=False).status_code,
            200,
        )
        self.assertEqual(
            self.url_open('/web/assets/debug/web.assets_frontend.js', allow_redirects=False).status_code,
            200,
        )
        self.assertEqual(
            self.url_open('/web/assets/debug/web.assets_frontend.rtl.css', allow_redirects=False).status_code,
            200,
        )
        self.assertEqual(
            self.url_open(f'/web/assets/{website_id}/debug/web.assets_frontend.css', allow_redirects=False).status_code,
            200,
        )
        self.assertEqual(
            self.url_open(f'/web/assets/{website_id}/debug/web.assets_frontend.rtl.css', allow_redirects=False).status_code,
            200,
        )
        self.assertEqual(
            self.url_open(f'/web/assets/{website_id}/debug/web.assets_frontend.js', allow_redirects=False).status_code,
            200,
        )
        self.assertEqual(
            self.url_open(f'/web/assets/{website_id}/any/web.assets_frontend.rtl.min.css', allow_redirects=False).status_code,
            200,
        )

        self.assertEqual(
            self.url_open(f'/web/assets/{website_id}/any/web.assets_frontend.min.css', allow_redirects=False).status_code,
            200,
        )
        self.assertEqual(
            self.url_open(f'/web/assets/{website_id}/any/web.assets_frontend.min.js', allow_redirects=False).status_code,
            200,
        )

        # redirect urls
        invalid_version = '1234567'
        self.assertEqual(
            self.url_open(f'/web/assets/{website_id}/{invalid_version}/web.assets_frontend.min.css', allow_redirects=False).headers['location'].split('/assets/')[1],
            self.env['ir.qweb']._get_asset_bundle('web.assets_frontend', assets_params={'website_id': website_id}).get_link('css').split('/assets/')[1],
        )

    def test_ensure_correct_website_asset(self):
        # when searching for an attachment, if the unique a wildcard, we want to ensute that we don't match a website one when seraching a no website one.
        # this test should also wheck that the clean_attachement does not erase a website_attachement after generating a base attachment
        website_id = self.env['website'].search([], limit=1, order='id desc').id
        unique = self.env['ir.qweb']._get_asset_bundle('web.assets_frontend').get_version('js')
        base_url = self.env['ir.asset']._get_asset_bundle_url('web.assets_frontend.min.js', '%', {})
        base_url_versioned = self.env['ir.asset']._get_asset_bundle_url('web.assets_frontend.min.js', unique, {})
        website_url = self.env['ir.asset']._get_asset_bundle_url('web.assets_frontend.min.js', '%', {'website_id': website_id})
        # we expect the unique to be the same in this case, but there is no garantee
        website_url_versioned = self.env['ir.asset']._get_asset_bundle_url('web.assets_frontend.min.js', unique, {'website_id': website_id})

        self.env['ir.attachment'].search([('url', '=like', '%web.assets_frontend.min.js')]).unlink()

        # generate website assets
        self.assertEqual(self.url_open(website_url, allow_redirects=False).status_code, 200)
        self.assertEqual(
            self.env['ir.attachment'].search([('url', '=like', '%web.assets_frontend.min.js')]).mapped('url'),
            [website_url_versioned],
            'Only the website asset is expected to be present',
        )

        # generate base assets
        with self.assertLogs() as logs:
            self.assertEqual(self.url_open(base_url, allow_redirects=False).status_code, 200)
        self.assertEqual(
            f'Found a similar attachment for /web/assets/{unique}/web.assets_frontend.min.js, copying from /web/assets/{website_id}/{unique}/web.assets_frontend.min.js',
            logs.records[0].message,
            'The attachment was expected to be linked to an existing one')
        self.assertEqual(
            self.env['ir.attachment'].search([('url', '=like', '%web.assets_frontend.min.js')]).mapped('url'),
            [base_url_versioned, website_url_versioned],
            'base asset is expected to be present',
        )
