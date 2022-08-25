# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
import re

from odoo import http, tools
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.addons.website.tools import MockRequest
from odoo.modules.module import get_module_resource
from odoo.tests.common import TransactionCase


class TestQweb(TransactionCaseWithUserDemo):
    def _load(self, module, *args):
        tools.convert_file(self.cr, 'website',
                           get_module_resource(module, *args),
                           {}, 'init', False, 'test')

    def test_qweb_post_processing_att(self):
        website = self.env.ref('website.default_website')
        t = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'arch_db': '''<t t-name="attr-escaping">
                <img src="http://test.external.img/img.png"/>
                <img t-att-src="url"/>
            </t>'''
        })
        result = """
                <img src="http://test.external.img/img.png" loading="lazy"/>
                <img src="http://test.external.img/img2.png" loading="lazy"/>
            """
        rendered = self.env['ir.qweb']._render(t.id, {'url': 'http://test.external.img/img2.png'}, website_id=website.id)
        self.assertEqual(rendered.strip(), result.strip())

    def test_qweb_cdn(self):
        self._load('website', 'tests', 'template_qweb_test.xml')

        website = self.env.ref('website.default_website')
        website.write({
            "cdn_activated": True,
            "cdn_url": "http://test.cdn"
        })

        demo = self.env['res.users'].search([('login', '=', 'demo')])[0]
        demo.write({"signature": '''<span class="toto">
                span<span class="fa"></span><img src="/web/image/1"/>
            </span>'''})

        demo_env = self.env(user=demo)

        html = demo_env['ir.qweb']._render('website.test_template', {"user": demo}, website_id= website.id)
        asset_data = etree.HTML(html).xpath('//*[@data-asset-bundle]')[0]
        asset_xmlid = asset_data.attrib.get('data-asset-bundle')
        asset_version = asset_data.attrib.get('data-asset-version')

        html = html.strip()
        html = re.sub(r'\?unique=[^"]+', '', html).encode('utf8')

        attachments = demo_env['ir.attachment'].search([('url', '=like', '/web/assets/%-%/website.test_bundle.%')])
        self.assertEqual(len(attachments), 2)

        format_data = {
            "js": attachments[0].url,
            "css": attachments[1].url,
            "user_id": demo.id,
            "filename": "Marc%20Demo",
            "alt": "Marc Demo",
            "asset_xmlid": asset_xmlid,
            "asset_version": asset_version,
        }
        self.assertHTMLEqual(html, ("""<!DOCTYPE html>
<html>
    <head>
        <link type="text/css" rel="stylesheet" href="http://test.external.link/style1.css"/>
        <link type="text/css" rel="stylesheet" href="http://test.external.link/style2.css"/>
        <link type="text/css" rel="stylesheet" href="http://test.cdn%(css)s" data-asset-bundle="%(asset_xmlid)s" data-asset-version="%(asset_version)s"/>
        <meta/>
        <script type="text/javascript" src="http://test.external.link/javascript1.js"></script>
        <script type="text/javascript" src="http://test.external.link/javascript2.js"></script>
        <script type="text/javascript" src="http://test.cdn%(js)s" data-asset-bundle="%(asset_xmlid)s" data-asset-version="%(asset_version)s"></script>
    </head>
    <body>
        <img src="http://test.external.link/img.png" loading="lazy"/>
        <img src="http://test.cdn/website/static/img.png" loading="lazy"/>
        <a href="http://test.external.link/link">x</a>
        <a href="http://test.cdn/web/content/local_link">x</a>
        <span style="background-image: url(&#39;http://test.cdn/web/image/2&#39;)">xxx</span>
        <div widget="html"><span class="toto">
                span<span class="fa"></span><img src="http://test.cdn/web/image/1" loading="lazy">
            </span></div>
        <div widget="image"><img src="http://test.cdn/web/image/res.users/%(user_id)s/avatar_1920/%(filename)s" class="img img-fluid" alt="%(alt)s" loading="lazy"/></div>
    </body>
</html>""" % format_data).encode('utf8'))


class TestQwebProcessAtt(TransactionCase):
    def setUp(self):
        super(TestQwebProcessAtt, self).setUp()
        self.website = self.env.ref('website.default_website')
        self.env['res.lang']._activate_lang('fr_FR')
        self.website.language_ids = self.env.ref('base.lang_en') + self.env.ref('base.lang_fr')
        self.website.default_lang_id = self.env.ref('base.lang_en')
        self.website.cdn_activated = True
        self.website.cdn_url = "http://test.cdn"
        self.website.cdn_filters = "\n".join(["^(/[a-z]{2}_[A-Z]{2})?/a$", "^(/[a-z]{2})?/a$", "^/b$"])

    def _test_att(self, url, expect, tag='a', attribute='href'):
        self.assertEqual(
            self.env['ir.qweb']._post_processing_att(tag, {attribute: url}),
            expect
        )

    def test_process_att_no_request(self):
        # no request so no URL rewriting
        self._test_att('/', {'href': '/'})
        self._test_att('/en', {'href': '/en'})
        self._test_att('/fr', {'href': '/fr'})
        # no URL rewritting for CDN
        self._test_att('/a', {'href': '/a'})

    def test_process_att_no_website(self):
        with MockRequest(self.env):
            # no website so URL rewriting
            self._test_att('/', {'href': '/'})
            self._test_att('/en', {'href': '/en'})
            self._test_att('/fr', {'href': '/fr'})
            # no URL rewritting for CDN
            self._test_att('/a', {'href': '/a'})

    def test_process_att_monolang_route(self):
        with MockRequest(self.env, website=self.website, multilang=False):
            # lang not changed in URL but CDN enabled
            self._test_att('/a', {'href': 'http://test.cdn/a'})
            self._test_att('/en/a', {'href': 'http://test.cdn/en/a'})
            self._test_att('/b', {'href': 'http://test.cdn/b'})
            self._test_att('/en/b', {'href': '/en/b'})

    def test_process_att_no_request_lang(self):
        with MockRequest(self.env, website=self.website):
            self._test_att('/', {'href': '/'})
            self._test_att('/en/', {'href': '/'})
            self._test_att('/fr/', {'href': '/fr/'})
            self._test_att('/fr', {'href': '/fr'})

    def test_process_att_with_request_lang(self):
        with MockRequest(self.env, website=self.website, context={'lang': 'fr_FR'}):
            self._test_att('/', {'href': '/fr/'})
            self._test_att('/en/', {'href': '/'})
            self._test_att('/fr/', {'href': '/fr/'})
            self._test_att('/fr', {'href': '/fr'})

    def test_process_att_matching_cdn_and_lang(self):
        with MockRequest(self.env, website=self.website):
            # lang prefix is added before CDN
            self._test_att('/a', {'href': 'http://test.cdn/a'})
            self._test_att('/en/a', {'href': 'http://test.cdn/a'})
            self._test_att('/fr/a', {'href': 'http://test.cdn/fr/a'})
            self._test_att('/b', {'href': 'http://test.cdn/b'})
            self._test_att('/en/b', {'href': 'http://test.cdn/b'})
            self._test_att('/fr/b', {'href': '/fr/b'})

    def test_process_att_no_route(self):
        with MockRequest(self.env, website=self.website, context={'lang': 'fr_FR'}, routing=False):
            # default on multilang=True if route is not /{module}/static/
            self._test_att('/web/static/hi', {'href': '/web/static/hi'})
            self._test_att('/my-page', {'href': '/fr/my-page'})

    def test_process_att_url_crap(self):
        with MockRequest(self.env, website=self.website):
            match = http.root.get_db_router.return_value.bind.return_value.match
            # #{fragment} is stripped from URL when testing route
            self._test_att('/x#y?z', {'href': '/x#y?z'})
            match.assert_called_with('/x', method='POST', query_args=None)

            match.reset_calls()
            self._test_att('/x?y#z', {'href': '/x?y#z'})
            match.assert_called_with('/x', method='POST', query_args='y')
