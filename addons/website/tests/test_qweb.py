# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
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


class TestQwebDataSnippet(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.ui.view'].create({
            'name': 'some_html',
            'type': 'qweb',
            'key': 'website.some_html',
            'arch': '''
                <t t-name="some_html">
                    <article>
                        <span>Hello</span>
                        <t t-out="0"/>
                    </article>
                </t>
            '''
        })

        cls.env['ir.ui.view'].create({
            'name': 's_a',
            'type': 'qweb',
            'key': 'website.s_a',
            'arch': '''
                <t t-name="s_a">
                    <section class="hello">
                        <t t-call="website.some_html"/>
                        <t t-out="0"/>
                    </section>
                </t>
            '''
        })
        cls.env['ir.ui.view'].create({
            'name': 's_b',
            'type': 'qweb',
            'key': 'website.s_b',
            'arch': '''
                <t t-name="s_b">
                    <section class="foo">
                        <t t-snippet-call="website.s_a"/>
                    </section>
                </t>
            '''
        })
        cls.env['ir.ui.view'].create({
            'name': 's_c',
            'type': 'qweb',
            'key': 'website.s_c',
            'arch': '''
                <t t-name="s_c">
                    <t t-call="website.some_html">
                        <p>World!</p>
                    </t>
                </t>
            '''
        })
        cls.env['ir.ui.view'].create({
            'name': 's_d',
            'type': 'qweb',
            'key': 'website.s_d',
            'arch_db': '''
                <t t-name="s_d">
                    <t t-snippet-call="website.s_a">
                        <p>World!</p>
                    </t>
                </t>
            '''
        })

    def _normalize_xml(self, html):
        return "\n".join(
            line.strip() for line in html.strip().splitlines() if line.strip()
    )

    def _render_snippet(self, snippet):
        render_template = self.env['ir.ui.view'].create({
            'name': f't-snippet-call_{snippet}',
            'type': 'qweb',
            'arch': f'''
                <t t-snippet-call="{snippet}"/>
            '''
        })
        return self.env['ir.qweb']._render(render_template.id)

    def test_t_call_inside_snippet(self):
        expected_output = '''
            <section class="hello" data-snippet="s_a">
                <article>
                    <span>Hello</span>
                </article>
            </section>
        '''
        rendered = self._render_snippet('website.s_a')
        self.assertEqual(self._normalize_xml(rendered), self._normalize_xml(expected_output))

    def test_t_snippet_call_inside_snippet(self):
        expected_output = '''
            <section class="foo" data-snippet="s_b">
                <section class="hello" data-snippet="s_a">
                    <article>
                        <span>Hello</span>
                    </article>
                </section>
            </section>
        '''
        rendered = self._render_snippet('website.s_b')
        self.assertEqual(self._normalize_xml(rendered), self._normalize_xml(expected_output))

    def test_t_call_as_snippet_root(self):
        expected_output = '''
            <article data-snippet="s_c">
                <span>Hello</span>
                <p>World!</p>
            </article>
        '''
        rendered = self._render_snippet('website.s_c')
        self.assertEqual(self._normalize_xml(rendered), self._normalize_xml(expected_output))

    def test_t_snippet_call_as_snippet_root(self):
        expected_output = '''
            <section class="hello" data-snippet="s_a">
                <article>
                    <span>Hello</span>
                </article>
                <p>World!</p>
            </section>
        '''
        rendered = self._render_snippet('website.s_d')
        self.assertEqual(self._normalize_xml(rendered), self._normalize_xml(expected_output))
