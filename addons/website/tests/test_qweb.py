# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.tests import HttpCase, tagged
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.addons.website.tools import MockRequest
from odoo.tests.common import TransactionCase


class TestQweb(TransactionCaseWithUserDemo):
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
            self._test_att('/', {'href': '/fr'})
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


@tagged('-at_install', 'post_install')
class TestQwebWebsite(HttpCase):
    def setUp(self):
        super(HttpCase, self).setUp()
        self.website = self.env.ref('website.default_website')
        self.env['res.lang']._activate_lang('fr_FR')
        self.website.language_ids = self.env.ref('base.lang_en') + self.env.ref('base.lang_fr')
        self.website.default_lang_id = self.env.ref('base.lang_en')

    def test_translation_cache(self):
        View = self.env['ir.ui.view']
        Page = self.env['website.page']

        home_1 = View.create({
            'name': 'Test Home',
            'type': 'qweb',
            'arch': '''
                <section>
                    <div>content <a href="/view-en">test</a> and <a href="/view-en">test</a></div>
                </section>''',
            'key': 'test.view_1',
        })
        page_home_1 = Page.create({
            'view_id': home_1.id,
            'website_id': self.website.id,
            'url': '/page_home_1',
            'is_published': True,
        })

        view_data = View.create({
            'name': 'Test View 1',
            'type': 'qweb',
            'arch': '''
                <section>
                    <div>content <a href="">test</a> rest</div>
                </section>''',
            'key': 'test.view_data',
        })
        Page.create({
            'view_id': view_data.id,
            'url': '/view-en',
            'is_published': True,
        })

        with MockRequest(self.env, website=self.website, context={'lang': 'fr_FR'}):
            self.authenticate('admin', 'admin')

            # read with debug (or use 2 different websites with different values
            # for block_third_party_domains). Method _post_processing_att
            # changes the value but the result is put in a static string. When
            # the user goes to an other page with other post-processing
            # information, the result can be wrong.
            self.session.debug = '1'
            http.root.session_store.save(self.session)

            # load french static node
            r = self.url_open(f'/fr{page_home_1.url}')
            # because debug => no post-processing
            self.assertIn('href="/view-en"', r.text)

            # read with t-cache
            self.session.debug = ''
            http.root.session_store.save(self.session)

            # use french static node cache
            r = self.url_open(f'/fr{page_home_1.url}')
            self.assertIn('href="/fr/view-en"', r.text)
            self.assertNotIn('href="/view-fr"', r.text)
