# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import lxml.html
from urllib.parse import urlparse

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
            self.assertEqual(self.env['ir.http']._url_for('', '[lang]'), '/[lang]/mockrequest', "`[lang]` is used to be replaced in the url_return after installing a language, it should not be replaced or removed.")

    def test_02_url_redirect(self):
        url = '/fr_WHATEVER/contactus'
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)
        self.assertURLEqual(r.url, '/fr/contactus', f"fr_WHATEVER should be forwarded to 'fr_FR' lang as closest match, url: {r.url}")

        url = '/fr_FR/contactus'
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)
        self.assertURLEqual(r.url, '/fr/contactus', f"lang in url should use url_code ('fr' in this case), url: {r.url}")

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
        r = self.url_open('/odoo')
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


@tagged('-at_install', 'post_install')
class TestTranslateUrl(TestLangUrl):
    def setUp(self):
        super().setUp()
        self.base = self.base_url()
        view_test_translate_url = self.env['ir.ui.view'].create({
            'name': 'NewPage',
            'type': 'qweb',
            'arch': '<div>NewPage</div>',
            'key': 'test.view_test_translate_url',
        })
        self.name_page_en = '/page-en'
        self.page = self.env['website.page'].create({
            'view_id': view_test_translate_url.id,
            'url': self.name_page_en,
            'is_published': True,
            'website_id': self.website.id,
        })
        self.name_page_fr = '/page-fr'
        self.page.with_context(lang='fr_FR').url = self.name_page_fr

    def test_access_translated_url(self):
        # Trying to access the french url of a page (without the lang in the
        # url) if the website language is in english should redirect to the
        # english url of this page.
        r = self.url_open(self.name_page_fr)
        self.assertEqual(r.history[0].status_code, 303)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.url, self.base + self.name_page_en)

        # Trying to access the french url of a page (with the lang in the url)
        # should change the website language to french and access the french url
        # of the page.
        r = self.url_open('/fr' + self.name_page_fr)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.url, self.base + '/fr' + self.name_page_fr)

        # Trying to access the english url of a page (without the lang in the
        # url) if the website language is in french should redirect to the
        # french url of this page.
        r = self.url_open(self.name_page_en)
        self.assertEqual(r.history[0].status_code, 303)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.url, self.base + '/fr' + self.name_page_fr)

    def test_access_translated_homepage(self):
        # From the homepage, changing the language of the website should
        # redirect to the french url of the specific homepage.
        name_homepage_url_fr = '/accueil'
        homepage_domain = [('url', '=', '/')] + self.website.website_domain()
        homepage_specific = self.env['website.page'].search(homepage_domain, order='website_id asc', limit=1)
        homepage_specific.with_context(lang='fr_FR').url = name_homepage_url_fr
        r = self.url_open('/fr')
        self.assertEqual(r.history[0].status_code, 303)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.url, self.base + '/fr' + name_homepage_url_fr)

    def test_translate_url_exists_in_other_language(self):
        # It should be possible to translate the url of a page with a url that
        # exists in another language.
        self.start_tour('/contactus', 'translate_url_exists_in_other_language', login='admin')
        r = self.url_open('/fr/page-en')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.url, self.base + '/fr/page-en')

    def test_translate_url_exists_in_current_language(self):
        # It should not be possible to have two url that are the same in the
        # same language
        self.start_tour('/contactus', 'translate_url_exists_in_same_language', login='admin')
        r = self.url_open('/fr/page-fr-1')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.url, self.base + '/fr/page-fr-1')

    def test_update_url_impact_homepage_url(self):
        # If a page url is the website homepage url, updating this url through
        # the "translate" modal should also update the homepage url if the
        # translation is done in the website default language.
        self.website.homepage_url = '/contactus'
        self.website.default_lang_id = self.lang_fr
        self.start_tour('/contactus', 'update_homepage_url', login='admin')
        self.assertEqual(self.website.homepage_url, '/contactus-fr')

    def test_new_homepage_impact_homepage_url_translations(self):
        # Using a page as the default website page should update the website
        # homepage url.
        self.website.default_lang_id = self.lang_fr
        self.page.is_homepage = True
        self.assertEqual(self.website.homepage_url, self.name_page_fr)
        self.page.is_homepage = False
        self.assertEqual(self.website.homepage_url, '')

    def test_redirect_on_new_url(self):
        # If the user modifies a url in the website default language, it should
        # have the possibility to create a url redirection.
        self.website.default_lang_id = self.lang_fr
        self.start_tour('/contactus', 'update_default_lang_website_url', login='admin')
        website_rewrite = self.env['website.rewrite'].search([('url_from', '=', '/contactus'), ('url_to', '=', '/contactus-fr')])
        self.assertEqual(len(website_rewrite), 1, "A rewrite route should have been created")
