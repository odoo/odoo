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

            self.assertEquals(fr_prefix + '/get', body.find('./a[@id="get"]').get('href'))
            self.assertEquals(fr_prefix + '/post', body.find('./form[@id="post"]').get('action'))
            self.assertEquals(fr_prefix + '/get_post', body.find('./a[@id="get_post"]').get('href'))
            self.assertEquals('/get_post_nomultilang', body.find('./a[@id="get_post_nomultilang"]').get('href'))
