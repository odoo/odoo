# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import werkzeug

import odoo
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
        demo.write({"signature": '''<span class="toto">
                span<span class="fa"></span><img src="/web/image/1"/>
            </span>'''})

        demo_env = self.env(user=demo)

        html = demo_env['ir.qweb'].render('website.test_template', {"user": demo}, website_id= website.id)
        html = html.strip().decode('utf8')
        html = re.sub(r'\?unique=[^"]+', '', html).encode('utf8')

        attachments = demo_env['ir.attachment'].search([('url', '=like', '/web/content/%-%/website.test_bundle.%')])
        self.assertEqual(len(attachments), 2)
        self.assertEqual(html, ("""<!DOCTYPE html>
<html>
    <head>
        <link rel="stylesheet" href="http://test.external.link/style1.css"/>
        <link rel="stylesheet" href="http://test.external.link/style2.css"/>
        <link type="text/css" rel="stylesheet" href="http://test.cdn%(css)s"/>
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
        <span style="background-image: url('http://test.cdn/web/image/2')">xxx</span>
        <div widget="html"><span class="toto">
                span<span class="fa"></span><img src="http://test.cdn/web/image/1">
            </span></div>
        <div widget="image"><img src="http://test.cdn/web/image/res.users/%(user_id)s/image" class="img img-responsive"/></div>
    </body>
</html>""" % {
            "js": attachments[0].url,
            "css": attachments[1].url,
            "user_id": demo.id,
        }).encode('utf8'))

class MockObject(object):
    _log_call = []
    def __init__(self, *args, **kwargs):
        self.__dict__ = kwargs
    def __call__(self, *args, **kwargs):
        self._log_call.append((args, kwargs))
        return self
    def __getitem__(self, index):
        return self

def werkzeugRaiseNotFound(*args, **kwargs):
    raise werkzeug.exceptions.NotFound()

class MockRequest(object):
    """ Class with context manager mocking odoo.http.request for tests """
    def __init__(self, env, website=None, context=None, multilang=True, routing=True):
        app = MockObject(routing={
            'type': 'http',
            'website': True,
            'multilang': multilang,
        })
        app.get_db_router = app.bind = app.match = app
        if not routing:
            app.match = werkzeugRaiseNotFound
        self.request = MockObject(
            env=env, context=context or {}, db=None, debug=False,
            website=website, httprequest=MockObject(
                path='/hello/',
                app=app
            )
        )
        odoo.http._request_stack.push(self.request)
    def __enter__(self):
        return self.request
    def __exit__(self, exc_type, exc_value, traceback):
        odoo.http._request_stack.pop()

class TestQwebProcessAtt(TransactionCase):
    def setUp(self):
        super(TestQwebProcessAtt, self).setUp()
        self.website = self.env['website'].browse(1)
        self.website.language_ids = self.env.ref('base.lang_en') + self.env.ref('base.lang_fr')
        self.website.default_lang_id = self.env.ref('base.lang_en')
        self.website.cdn_activated = True
        self.website.cdn_url = "http://test.cdn"
        self.website.cdn_filters = "\n".join(["^(/[a-z]{2}_[A-Z]{2})?/a$", "^/b$"])

    def _test_att(self, url, expect, tag='a', attribute='href'):
        self.assertEqual(
            self.env['ir.qweb']._post_processing_att(tag, {attribute: url}, {}),
            expect
        )

    def test_process_att_no_request(self):
        # no request so no URL rewriting
        self._test_att('/', {'href': '/'})
        self._test_att('/en_US/', {'href': '/en_US/'})
        self._test_att('/fr_FR/', {'href': '/fr_FR/'})
        # no URL rewritting for CDN
        self._test_att('/a', {'href': '/a'})

    def test_process_att_no_website(self):
        with MockRequest(self.env) as request:
            # no website so URL rewriting
            self._test_att('/', {'href': '/'})
            self._test_att('/en_US/', {'href': '/en_US/'})
            self._test_att('/fr_FR/', {'href': '/fr_FR/'})
            # no URL rewritting for CDN
            self._test_att('/a', {'href': '/a'})

    def test_process_att_monolang_route(self):
        with MockRequest(self.env, website=self.website, multilang=False) as request:
            # lang not changed in URL but CDN enabled
            self._test_att('/a', {'href': 'http://test.cdn/a'})
            self._test_att('/en_US/a', {'href': 'http://test.cdn/en_US/a'})
            self._test_att('/b', {'href': 'http://test.cdn/b'})
            self._test_att('/en_US/b', {'href': '/en_US/b'})

    def test_process_att_no_request_lang(self):
        with MockRequest(self.env, self.website) as request:
            self._test_att('/', {'href': '/'})
            self._test_att('/en_US/', {'href': '/'})
            self._test_att('/fr_FR/', {'href': '/fr_FR/'})

    def test_process_att_with_request_lang(self):
        with MockRequest(self.env, self.website, context={'lang': 'fr_FR'}) as request:
            self._test_att('/', {'href': '/fr_FR/'})
            self._test_att('/en_US/', {'href': '/'})
            self._test_att('/fr_FR/', {'href': '/fr_FR/'})

    def test_process_att_matching_cdn_and_lang(self):
        with MockRequest(self.env, self.website) as request:
            # lang prefix is added before CDN
            self._test_att('/a', {'href': 'http://test.cdn/a'})
            self._test_att('/en_US/a', {'href': 'http://test.cdn/a'})
            self._test_att('/fr_FR/a', {'href': 'http://test.cdn/fr_FR/a'})
            self._test_att('/b', {'href': 'http://test.cdn/b'})
            self._test_att('/en_US/b', {'href': 'http://test.cdn/b'})
            self._test_att('/fr_FR/b', {'href': '/fr_FR/b'})

    def test_process_att_no_route(self):
        with MockRequest(self.env, self.website, context={'lang': 'fr_FR'}, routing=False) as request:
            # default on multilang=True if route is not /{module}/static/
            self._test_att('/web/static/hi', {'href': '/web/static/hi'})
            self._test_att('/my-page', {'href': '/fr_FR/my-page'})

    def test_process_att_url_crap(self):
        with MockRequest(self.env, self.website) as request:
            # #{fragment} is stripped from URL when testing route
            self._test_att('/x#y?z', {'href': '/x#y?z'})
            self.assertEqual(
                request.httprequest.app._log_call[-1],
                (('/x',), {'method': 'POST', 'query_args': None})
            )
            self._test_att('/x?y#z', {'href': '/x?y#z'})
            self.assertEqual(
                request.httprequest.app._log_call[-1],
                (('/x',), {'method': 'POST', 'query_args': 'y'})
            )
