# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo.modules.module import get_module_resource
from odoo.tests.common import TransactionCase


class TestQweb(TransactionCase):
    def _load(self, module, *args):
        tools.convert_file(self.cr, 'website',
                           get_module_resource(module, *args),
                           {}, 'init', False, 'test', self.registry._assertion_report)

    def test_qweb_cdn(self):
        self._load('website', 'tests', 'template_qweb_test.xml')

        website = self.env['website'].browse(1)
        website.write({
            "cdn_activated": True,
            "cdn_url": "http://test.cdn"
        })

        demo = self.env['res.users'].search([('login', '=', 'demo')])[0]
        demo_env = self.env(user=demo)

        html = demo_env['ir.qweb'].render('website.test_template', {}, website_id= website.id)

        attachments = demo_env['ir.attachment'].search([('url', '=like', '/web/content/%-%/website.test_bundle.%')])
        self.assertEquals(len(attachments), 2)
        self.assertEqual(html.strip(), """<!DOCTYPE html>
<html>
    <head>
        <link rel="stylesheet" href="http://test.external.link/style1.css"/>
        <link rel="stylesheet" href="http://test.external.link/style2.css"/>
        <link href="http://test.cdn%(css)s" rel="stylesheet"/>
        <meta/>
        <script type="text/javascript" src="http://test.external.link/javascript1.js"></script>
        <script type="text/javascript" src="http://test.external.link/javascript2.js"></script>
        <script type="text/javascript" src="http://test.cdn%(js)s"></script>
    </head>
    <body>
        <img src="http://test.external.link/img.png"/>
        <img src="http://test.cdn/website/static/img.png"/>
        <a href="http://test.external.link/link">x</a>
        <a href="http://test.cdn/web/content/local_link">x</a>
    </body>
</html>""" % {"js": attachments[0].url, "css": attachments[1].url})
