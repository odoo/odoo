# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
import re

from odoo import tools
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.addons.website.tools import MockRequest


class TestQweb(TransactionCaseWithUserDemo):
    def _load(self, module, filepath):
        tools.convert_file(
            self.env, module,
            filepath,
            {}, 'init', False, 'test'
        )

    def test_qweb_cdn(self):
        self._load('test_website', 'tests/template_qweb_test.xml')

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

        html = demo_env['ir.qweb']._render('test_website.test_template', {"user": demo}, website_id=website.id)
        asset_bundle_xmlid = 'test_website.test_bundle'
        qweb = self.env['ir.qweb']
        bundle = qweb._get_asset_bundle(asset_bundle_xmlid, css=True, js=True, assets_params={'website_id': website.id})

        asset_version_js = bundle.get_version('js')
        asset_version_css = bundle.get_version('css')
        css_url, js_url = bundle.get_links()[-2:]

        html = html.strip()
        html = re.sub(r'\?unique=[^"]+', '', html).encode('utf8')

        format_data = {
            "css": css_url,
            "js": js_url,
            "user_id": demo.id,
            "filename": "Marc%20Demo",
            "alt": "Marc Demo",
            "asset_xmlid": asset_bundle_xmlid,
            "asset_version_css": asset_version_css,
            "asset_version_js": asset_version_js,
        }
        self.assertHTMLEqual(html, ("""<!DOCTYPE html>
<html>
    <head>
        <link type="text/css" rel="stylesheet" href="http://test.external.link/style1.css"/>
        <link type="text/css" rel="stylesheet" href="http://test.external.link/style2.css"/>
        <link type="text/css" rel="stylesheet" href="http://test.cdn%(css)s"/>
        <meta/>
        <script type="text/javascript" src="http://test.external.link/javascript1.js"></script>
        <script type="text/javascript" src="http://test.external.link/javascript2.js"></script>
        <script type="text/javascript" src="http://test.cdn%(js)s" onerror="__odooAssetError=1"></script>
    </head>
    <body>
        <img src="http://test.external.link/img.png" loading="lazy"/>
        <img src="http://test.cdn/test_website/static/img.png" loading="lazy"/>
        <a href="http://test.external.link/link">x</a>
        <a href="http://test.cdn/web/content/local_link">x</a>
        <span style="background-image: url(&#39;http://test.cdn/web/image/2&#39;)">xxx</span>
        <div widget="html"><span class="toto">
                span<span class="fa"></span><img src="http://test.cdn/web/image/1" loading="lazy">
            </span></div>
        <div widget="image"><img src="http://test.cdn/web/image/res.users/%(user_id)s/avatar_1920/%(filename)s" class="img img-fluid" alt="%(alt)s" loading="lazy"/></div>
    </body>
</html>""" % format_data).encode('utf8'))

        with MockRequest(self.env, website=website):
            html = demo_env['ir.qweb']._render('test_website.test_template_tatt_qweb', {}, website_id=website.id)
            self.assertHTMLEqual(html, ("""
    <html>
       <body><a href="/">1</a>
        <a>2</a>
        <a>3</a>
        <a>4</a>
        <a href="">5</a></body>
    </html>
    """))
