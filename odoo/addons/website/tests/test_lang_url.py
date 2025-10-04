# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import lxml.html
from urllib.parse import urlparse

from odoo.addons.http_routing.models.ir_http import url_lang
from odoo.addons.website.tools import MockRequest
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestLangUrl(HttpCase):
    def setUp(self):
        super(TestLangUrl, self).setUp()

        # Simulate multi lang without loading translations
        self.website = self.env.ref('website.default_website')
        self.lang_fr = self.env['res.lang']._activate_lang('fr_FR')
        self.lang_fr.write({'url_code': 'fr'})
        self.website.language_ids = self.env.ref('base.lang_en') + self.lang_fr
        self.website.default_lang_id = self.env.ref('base.lang_en')

    def test_01_url_lang(self):
        with MockRequest(self.env, website=self.website):
            self.assertEqual(url_lang('', '[lang]'), '/[lang]/mockrequest', "`[lang]` is used to be replaced in the url_return after installing a language, it should not be replaced or removed.")

    def test_02_url_redirect(self):
        url = '/fr_WHATEVER/contactus'
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.url.endswith('/fr/contactus'), f"fr_WHATEVER should be forwarded to 'fr_FR' lang as closest match, url: {r.url}")

        url = '/fr_FR/contactus'
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.url.endswith('/fr/contactus'), f"lang in url should use url_code ('fr' in this case), url: {r.url}")

    def test_03_url_cook_lang_not_available(self):
        """ An activated res.lang should not be displayed in the frontend if not a website lang. """
        self.website.language_ids = self.env.ref('base.lang_en')
        r = self.url_open('/fr/contactus')

        if 'lang="en-US"' not in r.text:
            doc = lxml.html.document_fromstring(r.text)
            self.assertEqual(doc.get('lang'), 'en-US', "french should not be displayed as not a frontend lang")

    def test_04_url_cook_lang_not_available(self):
        """ `nearest_lang` should filter out lang not available in frontend.
        Eg: 1. go in backend in english -> request.context['lang'] = `en_US`
            2. go in frontend, the request.context['lang'] is passed through
               `nearest_lang` which should not return english. More then a
               misbehavior it will crash in website language selector template.
        """
        # 1. Load backend
        self.authenticate('admin', 'admin')
        r = self.url_open('/web')
        self.assertEqual(r.status_code, 200)

        for line in r.text.splitlines():
            _, match, session_info_str = line.partition('odoo.__session_info__ = ')
            if match:
                session_info = json.loads(session_info_str[:-1])
                self.assertEqual(session_info['user_context']['lang'], 'en_US', "ensure english was loaded")
                break
        else:
            raise ValueError('Session info not found in web page')

        # 2. Remove en_US from frontend
        self.website.language_ids = self.lang_fr
        self.website.default_lang_id = self.lang_fr

        # 3. Ensure visiting /contactus do not crash
        url = '/contactus'
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)

        if 'lang="fr-FR"' not in r.text:
            doc = lxml.html.document_fromstring(r.text)
            self.assertEqual(doc.get('lang'), 'fr-FR', "Ensure contactus did not soft crash + loaded in correct lang")

    def test_05_invalid_ipv6_url(self):
        view = self.env['ir.ui.view'].create({
            'name': 'Base',
            'type': 'qweb',
            'arch': '<a id="foo" href="http://]">Invalid IP V6</a>',
            'key': 'test.invalid_ipv6_view',
        })

        self.env['website.page'].create({
            'view_id': view.id,
            'url': '/page_invalid_ipv6_url',
            'is_published': True,
        })
        r = self.url_open('/page_invalid_ipv6_url')
        self.assertEqual(r.status_code, 200, 'The page must still load despite the invalid link')
        doc = lxml.html.document_fromstring(r.text)
        [anchor] = doc.xpath('//a[@id="foo"]')
        self.assertEqual(anchor.get('href'), 'http://]', 'The invalid IP URL must be left untouched')

    def test_06_reroute_unicode(self):
        res = self.url_open('/fr/привет')
        self.assertEqual(res.status_code, 404, "Rerouting didn't crash because of unicode path")

        res = self.url_open('/fr/path?привет=1')
        self.assertEqual(res.status_code, 404, "Rerouting didn't crash because of unicode query-string")

    def test_07_nolang_prefix_underscore(self):
        res = self.url_open('/_not_a_lang', allow_redirects=False)
        self.assertEqual(res.status_code, 404, "Should not consider /_not_a_lang as a lang")
        self.assertURLEqual(res.url, '/_not_a_lang', "Should use /_not_a_lang as the path and not a lang")


@tagged('-at_install', 'post_install')
class TestControllerRedirect(TestLangUrl):
    def setUp(self):
        self.page = self.env['website.page'].create({
            'name': 'Test View',
            'type': 'qweb',
            'arch': '''<t t-call="website.layout">Test View Page</t>''',
            'key': 'test.test_view',
            'url': '/page_1',
            'is_published': True,
        })
        super().setUp()

    def test_01_controller_redirect(self):
        """ Trailing slash URLs should be redirected to non-slash URLs (unless
            the controller explicitly specifies a trailing slash in the route).
        """

        def assertUrlRedirect(url, expected_url, msg="", code=301):
            if not msg:
                msg = 'Url <%s> differ from <%s>.' % (url, expected_url)

            r = self.url_open(url, head=True)
            self.assertEqual(r.status_code, code)
            parsed_location = urlparse(r.headers.get('Location', ''))
            parsed_expected_url = urlparse(expected_url)
            self.assertEqual(parsed_location.path, parsed_expected_url.path, msg)
            self.assertEqual(parsed_location.query, parsed_expected_url.query, msg)

        self.authenticate('admin', 'admin')

        # Controllers
        assertUrlRedirect('/my/', '/my', "Check for basic controller.")
        assertUrlRedirect('/my/?a=b', '/my?a=b', "Check for basic controller + URL params.")
        # website.page
        assertUrlRedirect('/page_1/', '/page_1', "Check for website.page.")
        assertUrlRedirect('/page_1/?a=b', '/page_1?a=b', "Check for website.page + URL params.")

        # == Same with language ==
        # Controllers
        assertUrlRedirect('/fr/my/', '/fr/my', "Check for basic controller with language in URL.")
        assertUrlRedirect('/fr/my/?a=b', '/fr/my?a=b', "Check for basic controller with language in URL + URL params.")
        # Homepage (which is a controller)
        assertUrlRedirect('/fr/', '/fr', "Check for homepage + language.")
        assertUrlRedirect('/fr/?a=b', '/fr?a=b', "Check for homepage + language + URL params")
        # website.page
        assertUrlRedirect('/fr/page_1/', '/fr/page_1', "Check for website.page with language in URL.")
        assertUrlRedirect('/fr/page_1/?a=b', '/fr/page_1?a=b', "Check for website.page with language in URL + URL params.")
