# Part of Odoo. See LICENSE file for full copyright and licensing details.
from urllib.parse import urlparse
import odoo.tests
import lxml


@odoo.tests.common.tagged('post_install', '-at_install')
class TestIsMultiLang(odoo.tests.HttpCase):

    def test_01_is_multilang_url(self):
        website = self.env['website'].search([], limit=1)
        fr = self.env.ref('base.lang_fr').sudo()
        en = self.env.ref('base.lang_en').sudo()

        fr.active = True
        fr_prefix = "/" + fr.iso_code

        website.default_lang_id = en
        website.language_ids = en + fr

        for data in [None, {'post': True}]: # GET / POST
            body = lxml.html.fromstring(self.url_open('/fr/multi_url', data=data).content)

            self.assertEqual(fr_prefix + '/get', body.find('./a[@id="get"]').get('href'))
            self.assertEqual(fr_prefix + '/post', body.find('./form[@id="post"]').get('action'))
            self.assertEqual(fr_prefix + '/get_post', body.find('./a[@id="get_post"]').get('href'))
            self.assertEqual('/get_post_nomultilang', body.find('./a[@id="get_post_nomultilang"]').get('href'))

    def test_02_url_lang_code_underscore(self):
        website = self.env['website'].browse(1)
        it = self.env.ref('base.lang_it').sudo()
        en = self.env.ref('base.lang_en').sudo()
        be = self.env.ref('base.lang_fr_BE').sudo()
        country1 = self.env['res.country'].create({'name': "My Super Country", 'code': 'ZV'})

        it.active = True
        be.active = True
        website.domain = self.base_url()  # for _is_canonical_url
        website.default_lang_id = en
        website.language_ids = en + it + be
        country1.update_field_translations('name', {
            it.code: country1.name + ' Italia',
            be.code: country1.name + ' Belgium'
        })

        r = self.url_open(f'/test_lang_url/{country1.id}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(urlparse(r.url).path, f'/test_lang_url/my-super-country-{country1.id}')

        r = self.url_open(f'/{it.url_code}/test_lang_url/{country1.id}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(urlparse(r.url).path, f'/{it.url_code}/test_lang_url/my-super-country-italia-{country1.id}')

        body = lxml.html.fromstring(r.content)
        # Note: this test is indirectly testing the `ref=canonical` tag is correctly set,
        #       as it is required in order for `rel=alternate` tags to be inserted in the DOM
        it_href = body.find('./head/link[@rel="alternate"][@hreflang="it"]').get('href')
        fr_href = body.find('./head/link[@rel="alternate"][@hreflang="fr"]').get('href')
        en_href = body.find('./head/link[@rel="alternate"][@hreflang="en"]').get('href')

        self.assertEqual(urlparse(it_href).path, f'/{it.url_code}/test_lang_url/my-super-country-italia-{country1.id}')
        self.assertEqual(urlparse(fr_href).path, f'/{be.url_code}/test_lang_url/my-super-country-belgium-{country1.id}')
        self.assertEqual(urlparse(en_href).path, f'/test_lang_url/my-super-country-{country1.id}')

    def test_03_head_alternate_href(self):
        website = self.env['website'].search([], limit=1)
        be = self.env.ref('base.lang_fr_BE').sudo()
        en = self.env.ref('base.lang_en').sudo()

        be.active = True
        be_prefix = "/" + be.iso_code

        website.default_lang_id = en
        website.language_ids = en + be

        # alternate href should be use the current url.
        self.url_open(be_prefix)
        self.url_open(be_prefix + '/contactus')
        r = self.url_open(be_prefix)
        self.assertRegex(r.text, r'<link rel="alternate" hreflang="en" href="http://[^"]+/"/>')
        r = self.url_open(be_prefix + '/contactus')
        self.assertRegex(r.text, r'<link rel="alternate" hreflang="en" href="http://[^"]+/contactus"/>')

    def test_04_multilang_false(self):
        website = self.env['website'].search([], limit=1)
        fr = self.env.ref('base.lang_fr').sudo()
        en = self.env.ref('base.lang_en').sudo()
        fr.active = True

        website.default_lang_id = en
        website.language_ids = en + fr
        self.opener.cookies['frontend_lang'] = fr.iso_code

        res = self.url_open('/get_post_nomultilang', allow_redirects=False)
        res.raise_for_status()

        self.assertEqual(res.status_code, 200, "Should not be redirected")
