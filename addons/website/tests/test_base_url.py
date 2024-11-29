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

        # Test URL is correctly auto fixed
        domains = [
            # trailing /
            ("https://www.monsite.com/", "https://www.monsite.com"),
            # no scheme
            ("www.monsite.com", "https://www.monsite.com"),
            ("monsite.com", "https://monsite.com"),
            # respect scheme
            ("https://www.monsite.com", "https://www.monsite.com"),
            ("http://www.monsite.com", "http://www.monsite.com"),
            # respect port
            ("www.monsite.com:8069", "https://www.monsite.com:8069"),
            ("www.monsite.com:8069/", "https://www.monsite.com:8069"),
            # no guess wwww
            ("monsite.com", "https://monsite.com"),
            # mix
            ("www.monsite.com/", "https://www.monsite.com"),
        ]
        for (domain, expected) in domains:
            self.website.domain = domain
            self.assertEqual(self.website.get_base_url(), expected)

    def test_02_canonical_url(self):
        # test does not work in local due to port
        self._assertCanonical('/', self.website.get_base_url() + '/')
        self._assertCanonical('/?debug=1', self.website.get_base_url() + '/')
        self._assertCanonical('/a-page', self.website.get_base_url() + '/a-page')
        self._assertCanonical('/en_US', self.website.get_base_url() + '/')
        self._assertCanonical('/fr_FR', self.website.get_base_url() + '/fr')


@odoo.tests.tagged('-at_install', 'post_install')
class TestGetBaseUrl(odoo.tests.TransactionCase):
    def test_01_get_base_url(self):
        # Setup
        web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        company_1 = self.env['res.company'].create({
            'name': 'Company 1',
        })
        company_2 = self.env['res.company'].create({
            'name': 'Company 2',
        })

        # Finish setup & Check cache
        self.assertFalse(company_1.website_id, "No website yet created for this company.")
        website_1_domain = 'https://my-website.net'
        website_1 = self.env['website'].create({
            'name': 'Website Test 1',
            'domain': website_1_domain,
            'company_id': company_1.id,
        })
        self.assertEqual(website_1, company_1.website_id, "Company cache for `website_id` should have been invalidated and recomputed.")

        # Check `get_base_url()` through `website_id` & `company_id` properties
        attach = self.env['ir.attachment'].create({'name': 'test base url', 'website_id': website_1.id})
        self.assertEqual(attach.get_base_url(), website_1_domain, "Domain should be the one from the record.website_id.")
        attach.write({'company_id': company_2.id, 'website_id': False})
        self.assertEqual(attach.get_base_url(), web_base_url,
                         "Domain should be the one from the ICP as the record as no website_id, and it's company_id has no website_id.")
        attach.write({'company_id': company_1.id})
        self.assertEqual(attach.get_base_url(), website_1_domain, "Domain should be the one from the record.company_id.website_id.")

        # Check advanced cache behavior..
        website_2_domain = 'https://my-website-2.net'
        website_2 = self.env['website'].create({
            'name': 'Website Test 2',
            'domain': website_2_domain,
            'company_id': company_1.id,
            'sequence': website_1.sequence - 1,
        })
        # .. on create ..
        self.assertEqual(attach.get_base_url(), website_2_domain,
                         "Domain should be the one from the record.company_id.website_id and company_1.website_id should be the one with lowest sequence.")
        website_1.sequence = website_2.sequence - 1
        # .. on `sequence` write ..
        self.assertEqual(attach.get_base_url(), website_1_domain,
                         "Lowest sequence is now website_2, so record.company_id.website_id should be website_1 as cache should be invalidated.")
        website_1.company_id = company_2.id
        # .. on `company_id` write..
        self.assertEqual(attach.get_base_url(), website_2_domain, "Cache should be recomputed, only website_1 remains for company_2.")
        website_2.unlink()
        # .. on unlink ..
        self.assertEqual(attach.get_base_url(), web_base_url, "Cache should be recomputed, no more website for company_1.")

    def test_02_get_base_url_recordsets(self):
        Attachment = self.env['ir.attachment']
        web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        self.assertEqual(Attachment.get_base_url(), web_base_url, "Empty recordset should get ICP value.")

        with self.assertRaises(ValueError):
            # if more than one record, an error we should be raised
            Attachment.search([], limit=2).get_base_url()
