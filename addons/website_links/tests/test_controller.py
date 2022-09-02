# Part of Odoo. See LICENSE file for full copyright and licensing details.

import secrets
from unittest.mock import patch
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestWebsiteLinksRussian(HttpCase):
    """
    Russian has a /r lang alias, this alias collidess with the /r route
    of the link tracker controller. This test suite ensures the link
    tracker is still usable.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.link = cls.env['link.tracker'].create({
            'url': cls.base_url() + '/web/health#0',  # no-op route
        })

        cls.view = cls.env['ir.ui.view'].create({
            'name': 'Base',
            'type': 'qweb',
            'arch': '<div>Welcome to this webpage!</div>',
            'key': 'test.base_view',
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
        no_link_code = self.env['link.tracker.code']._get_random_code_strings()[0]
        self.env['website.page'].create({
            'url': f'/{no_link_code}',
            'view_id': self.view.id,
            'website_published': True,
        })

        res = self.url_open(f'/r/{no_link_code}', allow_redirects=False)
        res.raise_for_status()
        self.assertEqual(res.status_code, 302, "Should be a lang alias redirection")
        self.assertEqual(res.headers.get('Location'), f'{self.base_url()}/ru/{no_link_code}',
            "Should be redirected to /ru as no link exists for the requested code")

        res = self.url_open(res.headers['Location'], allow_redirects=False)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Welcome to this webpage!", res.text)

    def test3_page_collision(self):
        # Create a page with a same URL as the link-tracker code, shall
        # we be allowed to do that??
        self.env['website.page'].create({
            'url': f'/{self.link.code}',
            'view_id': self.view.id,
            'website_published': True,
        })

        # Shall we serve "/r/{code}" that is the russian page or
        # shall we serve "/r/{code}" that is the link tracker?
        res = self.url_open(f'/r/{self.link.code}', allow_redirects=False)
        res.raise_for_status()

        #self.assertEqual(res.status_code, 200, "We decided to serve to webpage")
        #self.assertIn("Welcome to this webpage!", res.text)
        self.assertEqual(res.status_code, 301, "We decided to serve to link-tracker")
        self.assertEqual(res.headers.get('Location'), self.link.url)

    def test4_link_collision(self):
        code = secrets.token_hex(16)
        self.env['website.page'].create({
            'url': f'/{code}',
            'view_id': self.view.id,
            'website_published': True,
        })

        # Create a link-tracker with the same code as an existing
        # webpage url, shall we be able to do that??
        with patch.object(self.registry['link.tracker.code'], '_get_random_code_strings', lambda self, n: [code]):
            link = self.env['link.tracker'].create({
                'url': self.base_url() + '/web/health#1',  # no-op route
            })
            assert link.code == code, (link.code, code)

        # Shall we serve "/r/{code}" that is the russian page or
        # shall we serve "/r/{code}" that is the link tracker?
        res = self.url_open(f'/r/{code}', allow_redirects=False)
        res.raise_for_status()

        #self.assertEqual(res.status_code, 200, "We decided to serve to webpage")
        #self.assertIn("Welcome to this webpage!", res.text)
        self.assertEqual(res.status_code, 301, "We decided to serve to link-tracker")
        self.assertEqual(res.headers.get('Location'), link.url)
