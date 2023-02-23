# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
import re

from odoo import tools
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.modules.module import get_module_resource


class TestQweb(TransactionCaseWithUserDemo):
    def _load(self, module, *args):
        tools.convert_file(
            self.env, 'test_website',
            get_module_resource(module, *args),
            {}, 'init', False, 'test'
        )

    def test_qweb_cdn(self):
        self._load('test_website', 'tests', 'template_qweb_test.xml')

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
        asset_data = etree.HTML(html).xpath('//*[@data-asset-bundle]')[0]
        asset_xmlid = asset_data.attrib.get('data-asset-bundle')
        asset_version = asset_data.attrib.get('data-asset-version')

        html = html.strip()
        html = re.sub(r'\?unique=[^"]+', '', html).encode('utf8')

        format_data = {
            "js": f"/web/assets/{asset_version}/we_{website.id}/test_website.test_bundle.min.js",
            "css": f"/web/assets/{asset_version}/we_{website.id}/test_website.test_bundle.min.css",
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
