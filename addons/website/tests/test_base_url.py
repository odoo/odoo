# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.tests


@odoo.tests.tagged('-at_install', 'post_install')
class TestBaseUrl(odoo.tests.HttpCase):
    def test_base_url(self):
        ICP = self.env['ir.config_parameter']
        Website = self.env['website']

        icp_base_url = ICP.sudo().get_param('web.base.url')
        domain = 'https://www.domain.jke'
        website = Website.create({'name': 'test base url', 'domain': domain})

        # Test URL is correct for the website itself when the domain is set
        self.assertEqual(website.get_base_url(), domain)

        # Test URL is correct for a model without website_id
        without_website_id = self.env['ir.attachment'].create({'name': 'test base url'})
        self.assertEqual(without_website_id.get_base_url(), icp_base_url)

        # Test URL is correct for a model with website_id...
        with_website_id = self.env['res.partner'].create({'name': 'test base url'})

        # ...when no website is set on the model
        with_website_id.website_id = False
        self.assertEqual(with_website_id.get_base_url(), icp_base_url)

        # ...when the website is correctly set
        with_website_id.website_id = website
        self.assertEqual(with_website_id.get_base_url(), domain)

        # ...when the set website doesn't have a domain
        website.domain = False
        self.assertEqual(with_website_id.get_base_url(), icp_base_url)

        # Test URL is correct for the website itself when no domain is set
        self.assertEqual(website.get_base_url(), icp_base_url)
