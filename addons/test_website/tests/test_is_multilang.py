# Part of Odoo. See LICENSE file for full copyright and licensing details.
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
        country1 = self.env['res.country'].create({'name': "My Super Country"})

        it.active = True
        be.active = True
        website.domain = 'http://127.0.0.1:8069'  # for _is_canonical_url
        website.default_lang_id = en
        website.language_ids = en + it + be
        params = {
            'src': country1.name,
            'value': country1.name + ' Italia',
            'type': 'model',
            'name': 'res.country,name',
            'res_id': country1.id,
            'lang': it.code,
            'state': 'translated',
        }
        self.env['ir.translation'].create(params)
        params.update({
            'value': country1.name + ' Belgium',
            'lang': be.code,
        })
        self.env['ir.translation'].create(params)
        r = self.url_open('/test_lang_url/%s' % country1.id)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.url.endswith('/test_lang_url/my-super-country-%s' % country1.id))

        r = self.url_open('/%s/test_lang_url/%s' % (it.url_code, country1.id))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.url.endswith('/%s/test_lang_url/my-super-country-italia-%s' % (it.url_code, country1.id)))

        body = lxml.html.fromstring(r.content)
        # Note: this test is indirectly testing the `ref=canonical` tag is correctly set,
        #       as it is required in order for `rel=alternate` tags to be inserted in the DOM
        it_href = body.find('./head/link[@rel="alternate"][@hreflang="it"]').get('href')
        fr_href = body.find('./head/link[@rel="alternate"][@hreflang="fr"]').get('href')
        en_href = body.find('./head/link[@rel="alternate"][@hreflang="en"]').get('href')
        self.assertTrue(it_href.endswith('/%s/test_lang_url/my-super-country-italia-%s' % (it.url_code, country1.id)))
        self.assertTrue(fr_href.endswith('/%s/test_lang_url/my-super-country-belgium-%s' % (be.url_code, country1.id)))
        self.assertTrue(en_href.endswith('/test_lang_url/my-super-country-%s' % country1.id))
