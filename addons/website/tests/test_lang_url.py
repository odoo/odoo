# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.http_routing.models.ir_http import url_lang
from odoo.addons.website.tools import MockRequest
from odoo.tests import HttpCase, tagged
from odoo.tests.common import HOST


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
            self.assertEqual(url_lang('', '[lang]'), '/[lang]/hello', "`[lang]` is used to be replaced in the url_return after installing a language, it should not be replaced or removed.")

    def test_02_url_redirect(self):
        url = '/fr_WHATEVER/contactus'
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.url.endswith('/fr/contactus'), "fr_WHATEVER should be forwarded to 'fr_FR' lang as closest match")

        url = '/fr_FR/contactus'
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.url.endswith('/fr/contactus'), "lang in url should use url_code ('fr' in this case)")

    def test_03_url_cook_lang_not_available(self):
        """ An activated res.lang should not be displayed in the frontend if not a website lang. """
        self.website.language_ids = self.env.ref('base.lang_en')
        r = self.url_open('/fr/contactus')
        self.assertTrue('lang="en-US"' in r.text, "french should not be displayed as not a frontend lang")

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
        self.assertTrue('"lang": "en_US"' in r.text, "ensure english was loaded")

        # 2. Remove en_US from frontend
        self.website.language_ids = self.lang_fr
        self.website.default_lang_id = self.lang_fr

        # 3. Ensure visiting /contactus do not crash
        url = '/contactus'
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue('lang="fr-FR"' in r.text, "Ensure contactus did not soft crash + loaded in correct lang")


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
            if expected_url.startswith('/'):
                expected_url = "http://%s:%s%s" % (HOST, odoo.tools.config['http_port'], expected_url)
            if not msg:
                msg = 'Url <%s> differ from <%s>.' % (url, expected_url)

            r = self.url_open(url, head=True)
            self.assertEqual(r.status_code, code)
            self.assertEqual(r.headers.get('Location'), expected_url, msg)

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
