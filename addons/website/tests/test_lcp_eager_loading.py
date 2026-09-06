from lxml.html import document_fromstring

from odoo.tests.common import HttpCase, tagged

DESKTOP_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0 Safari/537.36'
)
MOBILE_UA = (
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36'
)


@tagged('post_install', '-at_install')
class TestLcpEagerLoading(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref('base.default_website')
        cls.page = cls.env['website.page'].create({
            'name': 'LCP Test',
            'type': 'qweb',
            'key': 'website.lcp_test',
            'url': '/lcp-test',
            'is_published': True,
            'arch': '''
                <t name="LCP Test" t-name="website.lcp_test">
                    <t t-call="website.layout">
                        <div id="wrap">
                            <img data-original-src="/web/image/999" src="/web/image/1" class="hero"/>
                            <img src="/web/image/2" class="other"/>
                            <span t-field="website.logo" t-options-widget="'image'"/>
                        </div>
                    </t>
                </t>''',
        })

    def setUp(self):
        super().setUp()
        self.patch(self.registry['website.page'], '_CACHE_DURATION', 0)

    def _fetch(self, user_agent=DESKTOP_UA):
        res = self.url_open('/lcp-test', headers={'User-Agent': user_agent})
        return res, document_fromstring(res.content)

    def _image(self, tree, needle):
        return next(img for img in tree.xpath('//img') if needle in (img.get('src') or ''))

    def _preloads(self, tree):
        return tree.xpath('//head/link[@rel="preload"][@as="image"][@fetchpriority="high"]')

    def _assert_priority(self, image):
        self.assertEqual(image.get('loading'), 'eager')
        self.assertEqual(image.get('fetchpriority'), 'high')

    def _assert_no_priority(self, image):
        self.assertEqual(image.get('loading'), 'lazy')
        self.assertIsNone(image.get('fetchpriority'))

    def test_stored_image_is_eager_for_its_device_only(self):
        self.page.write({
            'website_lcp_image_desktop': '/web/image/1',
            'website_lcp_image_mobile': '/web/image/2',
        })
        for user_agent, eager, lazy in [
            (DESKTOP_UA, '/web/image/1', '/web/image/2'),
            (MOBILE_UA, '/web/image/2', '/web/image/1'),
        ]:
            with self.subTest(user_agent=user_agent):
                _, tree = self._fetch(user_agent)
                self._assert_priority(self._image(tree, eager))
                self._assert_no_priority(self._image(tree, lazy))

    def test_page_without_a_stored_image_keeps_every_image_lazy(self):
        _, tree = self._fetch()
        for image in tree.xpath('//img'):
            self._assert_no_priority(image)
        self.assertFalse(self._preloads(tree))

    def test_stored_background_is_preloaded_in_the_head(self):
        self.page.website_lcp_image_desktop = '/web/image/404'
        res, tree = self._fetch()
        self.assertEqual(self._preloads(tree)[0].get('href'), '/web/image/404')
        self.assertNotIn(b'loading="eager"', res.content)

    def test_a_matched_image_is_not_also_preloaded(self):
        self.page.website_lcp_image_desktop = '/web/image/1'
        _, tree = self._fetch()
        self.assertFalse(self._preloads(tree))

    def test_the_query_string_is_ignored_when_matching(self):
        self.page.website_lcp_image_desktop = '/web/image/1?unique=stale'
        _, tree = self._fetch()
        self._assert_priority(self._image(tree, '/web/image/1'))

    def test_every_copy_of_the_stored_image_is_marked(self):
        self.page.arch = '''
            <t name="LCP Test" t-name="website.lcp_test">
                <t t-call="website.layout">
                    <div id="wrap">
                        <img src="/web/image/1" class="mobile-hero"/>
                        <img src="/web/image/2" class="other"/>
                        <img src="/web/image/1" class="desktop-hero"/>
                    </div>
                </t>
            </t>'''
        self.page.website_lcp_image_desktop = '/web/image/1'
        _, tree = self._fetch()
        copies = [img for img in tree.xpath('//img') if '/web/image/1' in (img.get('src') or '')]
        self.assertEqual(len(copies), 2)
        for image in copies:
            self._assert_priority(image)
        self._assert_no_priority(self._image(tree, '/web/image/2'))

    def test_data_attributes_holding_a_url_are_not_matched(self):
        self.page.website_lcp_image_desktop = '/web/image/999'
        res, tree = self._fetch()
        self.assertNotIn(b'loading="eager"', res.content)
        self.assertEqual(self._preloads(tree)[0].get('href'), '/web/image/999')

    def test_an_image_field_can_be_the_stored_image(self):
        _, tree = self._fetch()
        field_src = self._image(tree, '/web/image/website').get('src')
        self.page.website_lcp_image_desktop = field_src
        _, tree = self._fetch()
        self._assert_priority(self._image(tree, '/web/image/website'))

    def test_hinted_pages_vary_by_user_agent(self):
        self.page.website_lcp_image_desktop = '/web/image/1'
        res, _ = self._fetch()
        self.assertIn('User-Agent', res.headers.get('Vary', ''))

    def test_unhinted_pages_do_not_vary(self):
        res, _ = self._fetch()
        self.assertNotIn('User-Agent', res.headers.get('Vary', ''))

    def test_cached_pages_keep_the_hint_of_their_device(self):
        self.patch(self.registry['website.page'], '_CACHE_DURATION', 3600)
        self.page.write({
            'website_lcp_image_desktop': '/web/image/1',
            'website_lcp_image_mobile': '/web/image/2',
        })
        for user_agent, eager in [
            (DESKTOP_UA, '/web/image/1'),
            (MOBILE_UA, '/web/image/2'),
            (DESKTOP_UA, '/web/image/1'),
        ]:
            with self.subTest(user_agent=user_agent):
                res, tree = self._fetch(user_agent)
                self._assert_priority(self._image(tree, eager))
                self.assertEqual(res.content.count(b'fetchpriority="high"'), 1)
