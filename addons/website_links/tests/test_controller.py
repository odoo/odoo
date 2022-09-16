# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestWebsiteLinksRussian(HttpCase):
    """
    The /r URL prefix is considered as an alias to /ru by the "nearest
    lang" algorithm of our http router (http_routing match). This test
    suite makes sure that there the link-tracker "/r" controller is not
    affected by any (wrong) /ru redirection.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.link = cls.env['link.tracker'].create({
            'url': cls.base_url() + '/web/health',  # no-op route
        })

        # Courtesy of website/tests/test_lang_url.py
        website = cls.env.ref('website.default_website')
        lang_en = cls.env.ref('base.lang_en')
        lang_ru = cls.env['res.lang']._activate_lang('ru_RU')
        website.language_ids = lang_en + lang_ru
        website.default_lang_id = lang_en

    def test0_direct_link_tracker(self):
        res = self.url_open(f'/r/{self.link.code}', allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 301, "Should be link-tracking redirection")
        self.assertEqual(res.headers.get('Location'), self.link.url,
            "Should not be redirected to /ru")

    def test1_russian_link_tracker(self):
        res = self.url_open(f'/r/r/{self.link.code}', allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 301, "Should be a lang alias redirection")
        self.assertEqual(res.headers.get('Location'), f'{self.base_url()}/ru/r/{self.link.code}',
            "Should be redirected to /ru as r is an alias for ru (russian)")

        res = self.url_open(res.headers['Location'], allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 301, "Should be a link-tracking redirection")
        self.assertEqual(res.headers.get('Location'), self.link.url,
            "Should not be redirected to /ru")

    def test2_russian_page(self):
        # This generate a new unused link
        no_link_code = self.env['link.tracker.code']._get_random_code_strings()[0]

        view = self.env['ir.ui.view'].create({
            'name': 'Base',
            'type': 'qweb',
            'arch': '<div>Welcome to this webpage!</div>',
            'key': 'test.base_view',
        })
        self.env['website.page'].create({
            'url': f'/{no_link_code}',
            'view_id': view.id,
            'website_published': True,
        })

        res = self.url_open(f'/r/{no_link_code}', allow_redirects=False)
        self.assertEqual(res.status_code, 404, "No link tracker exists for the requested code")
