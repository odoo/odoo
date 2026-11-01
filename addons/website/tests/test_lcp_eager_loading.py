from lxml.html import document_fromstring

from odoo.tests.common import HttpCase, tagged

MOBILE_MEDIA = '(max-width: 991.98px)'
DESKTOP_MEDIA = '(min-width: 992px)'


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
                            <img src="/web/image/1" class="hero"/>
                            <div class="cover" style="background-image: url('/web/image/404')"/>
                            <span t-field="website.logo" t-options-widget="'image'"/>
                        </div>
                    </t>
                </t>''',
        })

    def setUp(self):
        super().setUp()
        self.patch(self.registry['website.page'], '_CACHE_DURATION', 0)

    def _fetch(self):
        return document_fromstring(self.url_open('/lcp-test').content)

    def _preloads_by_media(self, tree):
        preloads = tree.xpath('//head/link[@rel="preload"][@as="image"][@fetchpriority="high"]')
        return {preload.get('media'): preload.get('href') for preload in preloads}

    def test_stored_img_and_background_use_device_preload_links(self):
        self.page.write({
            'website_lcp_image_desktop': '/web/image/1',
            'website_lcp_image_mobile': '/web/image/404',
        })
        tree = self._fetch()
        self.assertEqual(self._preloads_by_media(tree), {
            MOBILE_MEDIA: '/web/image/404',
            DESKTOP_MEDIA: '/web/image/1',
        })

    def test_page_without_stored_images_has_no_preload_links(self):
        tree = self._fetch()
        self.assertFalse(self._preloads_by_media(tree))

    def test_only_the_stored_device_image_is_preloaded(self):
        self.page.website_lcp_image_desktop = '/web/image/1'
        tree = self._fetch()
        self.assertEqual(self._preloads_by_media(tree), {
            DESKTOP_MEDIA: '/web/image/1',
        })

    def test_same_image_is_preloaded_for_both_device_sizes(self):
        self.page.write({
            'website_lcp_image_desktop': '/web/image/1',
            'website_lcp_image_mobile': '/web/image/1',
        })
        tree = self._fetch()
        self.assertEqual(self._preloads_by_media(tree), {
            MOBILE_MEDIA: '/web/image/1',
            DESKTOP_MEDIA: '/web/image/1',
        })

    def test_an_image_field_can_be_preloaded(self):
        tree = self._fetch()
        field_src = next(
            image.get('src')
            for image in tree.xpath('//img')
            if '/web/image/website' in (image.get('src') or '')
        )
        self.page.website_lcp_image_desktop = field_src
        tree = self._fetch()
        self.assertEqual(self._preloads_by_media(tree), {
            DESKTOP_MEDIA: field_src,
        })
