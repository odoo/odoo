# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from contextlib import contextmanager

from odoo import http
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.tests.common import TransactionCase, tagged


class TestQweb(TransactionCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_demo.group_ids = cls.env.ref('base.group_user')

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

    def test_render_context_website(self):
        self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'website.dummy',
            'arch_db': '<t t-name="dummy"><span>Stuff</span></t>'
        })
        template = self.env['ir.ui.view'].create({
            'name': 'test',
            'type': 'qweb',
            'key': 'root',
            'arch_db': '''<t t-name="root"><div><t t-call="website.dummy"/></div></t>'''
        })

        result = """<div><span>Stuff</span></div>"""

        rendered = self.env['ir.qweb']._render(template.id)
        self.assertEqual(rendered.strip(), result.strip(), 'First rendering (without website_id)')

        rendered = self.env['ir.qweb'].with_context(website_id=1)._render(template.id)
        self.assertEqual(rendered.strip(), result.strip(), 'Second rendering (with website_id=1)')

        rendered = self.env['ir.qweb'].with_context(website_id=None)._render(template.id)
        self.assertEqual(rendered.strip(), result.strip(), 'Third rendering (with website_id=None)')

        rendered = self.env['ir.qweb'].with_context(website_id=1)._render(template.id)
        self.assertEqual(rendered.strip(), result.strip(), 'Fourth rendering (with website_id=1)')

    def test_render_query_count(self):
        """
        see also test_call_query_count test in base/tests/test_queb.py
        """
        IrUiView = self.env['ir.ui.view']
        IrUiView.create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_unused',
            'arch_db': '''<span>unused</span>''',
        })
        header_0 = IrUiView.create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_header_0',
            'arch_db': '''<span>0</span>''',
        })
        IrUiView.create([{  # website_id=1
            'name': 'test',
            'type': 'qweb',
            'website_id': 1,
            'key': 'base.testing_header_1',
            'arch_db': '''<span>WITH WEBSITE</span>''',
        }, {  # same key but website_id=False
            'name': 'test',
            'type': 'qweb',
            'website_id': False,
            'key': 'base.testing_header_1',
            'arch_db': '''<span>NO WEBSITE</span>''',
        }, {
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_header',
            'arch_db': f'''<t t-name="base.testing_header">
                <t t-call="{header_0.id}"/>
                    <header>header</header>
                <t t-call="base.testing_header_1"/>
            </t>''',
        }, {
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_footer_0',
            'arch_db': '''<span>0</span>''',
        }, {
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_footer_1',
            'arch_db': '''<span>1</span>''',
        }, {  # website_id=False
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_footer',
            'arch_db': '''<t t-name="base.testing_footer">
                <t t-call="base.testing_footer_0"/>
                    <footer>footer</footer>
                <t t-call="base.testing_footer_1"/>
            </t>''',
        }, {  # website_id=1
            'name': 'test',
            'type': 'qweb',
            'website_id': 1,
            'key': 'base.testing_footer',
            'arch_db': '''<t t-name="base.testing_footer">
                <t t-call="base.testing_footer_0"/>
                    <footer>footer WITH WEBSITE</footer>
                <t t-call="base.testing_footer_1"/>
            </t>''',
        }, {
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_layout',
            'arch_db': '''<t t-name="base.testing_layout">
                <section>
                    <div id="header"><t t-call="base.testing_header"/></div>
                    <article><t t-out="0"/></article>
                    <div id="footer"><t t-call="base.testing_footer"/></div>
                </section>
            </t>''',
        }])
        view = IrUiView.create({
            'name': 'test',
            'type': 'qweb',
            'key': 'base.testing_content',
            'arch_db': '''<t t-call="base.testing_layout"><div><t t-call="base.testing_header_0"/><t t-out="doc"/></div></t>''',
        })
        website = self.env['website'].browse(1)
        other_website = self.env['website'].create({'name': 'testing'})

        expected = """
                <section>
                    <div id="header"><span>0</span>
                    <header>header</header><span>NO WEBSITE</span></div>
                    <article><div><span>0</span>%s</div></article>
                    <div id="footer"><span>0</span>
                    <footer>footer</footer><span>1</span></div>
                </section>"""

        expected_website = """
                <section>
                    <div id="header"><span>0</span>
                    <header>header</header><span>WITH WEBSITE</span></div>
                    <article><div><span>0</span>%s</div></article>
                    <div id="footer"><span>0</span>
                    <footer>footer WITH WEBSITE</footer><span>1</span></div>
                </section>"""

        env = self.env(user=self.user_demo, context={
            'lang': 'en_US',
            'website_id': other_website.id,
            'minimal_qcontext': True,
            'cookies_allowed': True,
        })

        # add some website information in cache (default website, lang...)
        env['ir.qweb']._render('base.testing_unused')
        with MockRequest(env, website=website) as request:
            # SELECT res_lang
            # SELECT ir_attachment from res.lang
            # SELECT website.id from domain
            # SELECT website.id ORDER BY sequence (without WHERE)
            request.env['ir.qweb']._render('base.testing_unused')

        # do not count those fetching queries
        env.user.fetch(['name'])
        website.with_env(env).fetch(['name'])
        other_website.with_env(env).fetch(['name'])

        def invalidate(*args):
            if 'templates' in args:
                env.registry.clear_cache('templates')
            if 'view' in args:
                IrUiView.invalidate_model()

        def check(template, name, queries):
            init = env.cr.sql_log_count
            value = str(env['ir.qweb']._render(template, {'doc': name}))
            self.assertEqual(value, expected % name)
            self.assertEqual(env.cr.sql_log_count - init, queries, f'Maximum queries: {queries}')

        def check_website(template, name, queries):
            queries += 1
            init = env.cr.sql_log_count
            with MockRequest(env, website=website) as request:
                value = str(request.env['ir.qweb']._render(template, {'doc': name}))
            self.assertEqual(value, expected_website % name)
            self.assertEqual(env.cr.sql_log_count - init, queries, f'Maximum queries: {queries}')

        # SELECT visibility (from _render) + fields from in cache
        # 'base.testing_content'
        #     SELECT RECURSIVE arch combine
        # 'base.testing_layout', 'base.testing_header_0'
        #     SELECT id + fields from (xmlid + website_id)
        #     SELECT RECURSIVE arch combine => TODO: batch me
        # 'base.testing_header', 'base.testing_footer'
        #     SELECT id + fields from (xmlid + website_id)
        #     SELECT RECURSIVE arch combine => TODO: batch me
        # 'base.testing_header_1', 'base.testing_footer_0', 'base.testing_footer_1'
        #     SELECT id + fields from (xmlid + website_id)
        #     SELECT RECURSIVE arch combine => TODO: batch me

        FIRST_SEARCH_FETCH = 1  # instead of the first SELECT visibility
        OTHER_SEARCH_FETCH = 3  # "SELECT id + fields from xmlid"
        ARCH_COMBINE = 4  # SELECT RECURSIVE arch combine

        invalidate('templates', 'view')
        check('base.testing_content', 'test-cold-0',
              FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 8

        invalidate('templates', 'view')
        check_website('base.testing_content', 'test-cold-0',
                      FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 8

        check('base.testing_content', 'test-cold-0',
              FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 8

        check('base.testing_content', 'test-hot-0', 0)

        check_website('base.testing_content', 'test-hot-0', 0)

        check('base.testing_content', 'test-hot-1', 0)

        check_website('base.testing_content', 'test-hot-1', 0)

        invalidate('view')
        check('base.testing_content', 'test-hot-2', 0)

        invalidate('view')
        check_website('base.testing_content', 'test-hot-2', 0)

        check(view.id, 'test-hot-id', 0)

        check_website(view.id, 'test-hot-id', 0)

        # like 'test-cold-0'
        invalidate('templates')
        check(view.id, 'test-cold-id-1',
              FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 8

        invalidate('templates')
        check(view.id, 'test-cold-id-1',
              0 + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 7

        invalidate('templates')
        check_website(view.id, 'test-cold-id-1',
                      0 + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 7

        # like 'test-cold-0' the first search query is replaced by a fetching
        invalidate('templates', 'view')
        check_website(view.id, 'test-cold-id-2',
                      FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 8

        invalidate('templates', 'view')
        check(view.id, 'test-cold-id-2',
              FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 8

        env = self.env(user=self.user_demo, context={
            'lang': 'en_US',
            'minimal_qcontext': True,
            'cookies_allowed': True,
        })

        # like 'test-cold-0'
        invalidate('templates')
        check('base.testing_content', 'test-cold-1',
              FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 8

        invalidate('templates')
        check_website('base.testing_content', 'test-cold-1',
                      FIRST_SEARCH_FETCH + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 8

        # like 'test-cold-0'
        invalidate('templates')
        check_website(view.id, 'test-cold-id-3',
                      0 + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 7

        invalidate('templates')
        check(view.id, 'test-cold-id-3',
              0 + OTHER_SEARCH_FETCH + ARCH_COMBINE)  # 7


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

    def test_call_query_count_snippets_template(self):
        actual_queries = []
        with contextmanager(lambda: self._patchExecute(actual_queries))():
            with MockRequest(self.env, website=self.env['website'].browse(1)):
                render = self.env['ir.ui.view'].render_public_asset('website.snippets')
                self.assertTrue('data-selector=".s_blockquote"' in render)

        re_sql = re.compile(r'\bir_ui_view\b', re.IGNORECASE)
        ir_ui_view_queries = [q for q in actual_queries if re_sql.search(q)]

        # nb_snippets = 156
        first_search = 1
        t_call_snippets = 3
        fetch_snippets = 0
        get_root_view = 3
        combine_views = 3

        all_ir_ui_view_queries = first_search + t_call_snippets + fetch_snippets + get_root_view + combine_views  # 10
        self.assertEqual(len(ir_ui_view_queries), all_ir_ui_view_queries, f'ir_ui_view queries: {all_ir_ui_view_queries}')

        re_sql = re.compile(r'\bwebsite\b', re.IGNORECASE)
        website_queries = [q for q in actual_queries if re_sql.search(q)]

        self.assertEqual(len(website_queries), 20, f'Maximum queries: {20}')
