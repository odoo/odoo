# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml.html import document_fromstring

import odoo.tests


class TestUrlCommon(odoo.tests.HttpCase):
    def setUp(self):
        super(TestUrlCommon, self).setUp()
        self.domain = 'http://' + odoo.tests.HOST
        self.website = self.env['website'].create({
            'name': 'test base url',
            'domain': self.domain,
        })

        lang_fr = self.env['res.lang']._activate_lang('fr_FR')
        self.website.language_ids = self.env.ref('base.lang_en') + lang_fr
        self.website.default_lang_id = self.env.ref('base.lang_en')

    def _assertCanonical(self, url, canonical_url):
        res = self.url_open(url)
        canonical_link = document_fromstring(res.content).xpath("/html/head/link[@rel='canonical']")
        self.assertEqual(len(canonical_link), 1)
        self.assertEqual(canonical_link[0].attrib["href"], canonical_url)


@odoo.tests.tagged('-at_install', 'post_install')
class TestBaseUrl(TestUrlCommon):
    def test_01_base_url(self):
        ICP = self.env['ir.config_parameter']
        icp_base_url = ICP.sudo().get_param('web.base.url')

        # Test URL is correct for the website itself when the domain is set
        self.assertEqual(self.website.get_base_url(), self.domain)

        # Test URL is correct for a model without website_id
        without_website_id = self.env['ir.attachment'].create({'name': 'test base url'})
        self.assertEqual(without_website_id.get_base_url(), icp_base_url)

        # Test URL is correct for a model with website_id...
        with_website_id = self.env['res.partner'].create({'name': 'test base url'})

        # ...when no website is set on the model
        with_website_id.website_id = False
        self.assertEqual(with_website_id.get_base_url(), icp_base_url)

        # ...when the website is correctly set
        with_website_id.website_id = self.website
        self.assertEqual(with_website_id.get_base_url(), self.domain)

        # ...when the set website doesn't have a domain
        self.website.domain = False
        self.assertEqual(with_website_id.get_base_url(), icp_base_url)

        # Test URL is correct for the website itself when no domain is set
        self.assertEqual(self.website.get_base_url(), icp_base_url)

    def test_02_canonical_url(self):
        self._assertCanonical('/', self.domain + '/')
        self._assertCanonical('/?debug=1', self.domain + '/')
        self._assertCanonical('/a-page', self.domain + '/a-page')
        self._assertCanonical('/en_US', self.domain + '/')
        self._assertCanonical('/fr_FR', self.domain + '/fr/')
