# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestGetCurrentWebsite(TransactionCase):

    def test_01_get_current_website_id(self):
        """Make sure `_get_current_website_id works`."""

        Website = self.env['website']

        # clean initial state
        website1 = Website.browse(1)
        website1.domain = ''
        website1.country_group_ids = False

        website2 = Website.browse(2)
        website2.domain = ''
        website2.country_group_ids = False

        country1 = self.env['res.country'].create({'name': "My Country 1"})
        country2 = self.env['res.country'].create({'name': "My Country 2"})
        country3 = self.env['res.country'].create({'name': "My Country 3"})
        country4 = self.env['res.country'].create({'name': "My Country 4"})
        country5 = self.env['res.country'].create({'name': "My Country 5"})

        country_group_1_2 = self.env['res.country.group'].create({
            'name': "My Country Group 1-2",
            'country_ids': [(6, 0, (country1 + country2 + country5).ids)],
        })
        country_group_3 = self.env['res.country.group'].create({
            'name': "My Country Group 3",
            'country_ids': [(6, 0, (country3 + country5).ids)],
        })

        # CASE: no domain, no country: get first
        self.assertEqual(Website._get_current_website_id('', False), website1.id)
        self.assertEqual(Website._get_current_website_id('', country3.id), website1.id)

        # CASE: no domain, given country: get by country
        website1.country_group_ids = country_group_1_2
        website2.country_group_ids = country_group_3

        self.assertEqual(Website._get_current_website_id('', country1.id), website1.id)
        self.assertEqual(Website._get_current_website_id('', country2.id), website1.id)
        self.assertEqual(Website._get_current_website_id('', country3.id), website2.id)

        # CASE: no domain, wrong country: get first
        self.assertEqual(Website._get_current_website_id('', country4.id), website1.id)

        # CASE: no domain, multiple country: get first
        self.assertEqual(Website._get_current_website_id('', country5.id), website1.id)

        # setup domain
        website1.domain = 'my-site-1.fr'
        website2.domain = 'https://my2ndsite.com:80'

        website1.country_group_ids = False
        website2.country_group_ids = False

        # CASE: domain set: get matching domain
        self.assertEqual(Website._get_current_website_id('my-site-1.fr', False), website1.id)

        # CASE: domain set: get matching domain (scheme and port supported)
        self.assertEqual(Website._get_current_website_id('my-site-1.fr:8069', False), website1.id)

        self.assertEqual(Website._get_current_website_id('my2ndsite.com:80', False), website2.id)
        self.assertEqual(Website._get_current_website_id('my2ndsite.com:8069', False), website2.id)
        self.assertEqual(Website._get_current_website_id('my2ndsite.com', False), website2.id)

        # CASE: domain set, wrong domain: get first
        self.assertEqual(Website._get_current_website_id('test.com', False), website1.id)

        # CASE: subdomain: not supported
        self.assertEqual(Website._get_current_website_id('www.my2ndsite.com', False), website1.id)

        # CASE: domain set, given country: get by domain in priority
        website1.country_group_ids = country_group_1_2
        website2.country_group_ids = country_group_3

        self.assertEqual(Website._get_current_website_id('my2ndsite.com', country1.id), website2.id)
        self.assertEqual(Website._get_current_website_id('my2ndsite.com', country2.id), website2.id)
        self.assertEqual(Website._get_current_website_id('my-site-1.fr', country3.id), website1.id)

        # CASE: domain set, wrong country: get first for domain
        self.assertEqual(Website._get_current_website_id('my2ndsite.com', country4.id), website2.id)

        # CASE: domain set, multiple country: get first for domain
        website1.domain = website2.domain
        self.assertEqual(Website._get_current_website_id('my2ndsite.com', country5.id), website1.id)

        # CASE: overlapping domain: get exact match
        website1.domain = 'site-1.com'
        website2.domain = 'even-better-site-1.com'
        self.assertEqual(Website._get_current_website_id('site-1.com', False), website1.id)
        self.assertEqual(Website._get_current_website_id('even-better-site-1.com', False), website2.id)

        # CASE: case insensitive
        website1.domain = 'Site-1.com'
        website2.domain = 'Even-Better-site-1.com'
        self.assertEqual(Website._get_current_website_id('sitE-1.com', False), website1.id)
        self.assertEqual(Website._get_current_website_id('even-beTTer-site-1.com', False), website2.id)

        # CASE: same domain, different port
        website1.domain = 'site-1.com:80'
        website2.domain = 'site-1.com:81'
        self.assertEqual(Website._get_current_website_id('site-1.com:80', False), website1.id)
        self.assertEqual(Website._get_current_website_id('site-1.com:81', False), website2.id)
        self.assertEqual(Website._get_current_website_id('site-1.com:82', False), website1.id)
        self.assertEqual(Website._get_current_website_id('site-1.com', False), website1.id)

    def test_02_signup_user_website_id(self):
        website = self.env['website'].browse(1)
        website.specific_user_account = True

        user = self.env['res.users'].create({'website_id': website.id, 'login': 'sad@mail.com', 'name': 'Hope Fully'})
        self.assertTrue(user.website_id == user.partner_id.website_id == website)
