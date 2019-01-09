# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
from odoo.tests.common import TransactionCase


class TestWebsitePriceList(TransactionCase):

    # Mock nedded because request.session doesn't exist during test
    def _get_pricelist_available(self, show_visible=False):
        return self.get_pl(self.args.get('show'), self.args.get('current_pl'), self.args.get('country'))

    def setUp(self):
        super(TestWebsitePriceList, self).setUp()
        self.env.user.partner_id.country_id = False  # Remove country to avoid property pricelist computed.
        self.website = self.env['website'].browse(1)
        self.website.user_id = self.env.user

        self.env['product.pricelist'].search([]).write({'website_id': False})
        website_pls = ('list_benelux', 'list_christmas', 'list_europe')
        for pl in website_pls:
            self.env.ref('website_sale.' + pl).website_id = self.website.id
        self.env.ref('product.list0').website_id = self.website.id
        self.env.ref('website_sale.list_benelux').selectable = True
        self.website.pricelist_id = self.ref('product.list0')

        ca_group = self.env['res.country.group'].create({
            'name': 'Canada',
            'country_ids': [(6, 0, [self.ref('base.ca')])]
        })
        self.env['product.pricelist'].create({
            'name': 'Canada',
            'selectable': True,
            'website_id': self.website.id,
            'country_group_ids': [(6, 0, [ca_group.id])],
            'sequence': 10
        })
        patcher = patch('odoo.addons.website_sale.models.website.Website.get_pricelist_available', wraps=self._get_pricelist_available)
        patcher.start()
        self.addCleanup(patcher.stop)

    def get_pl(self, show, current_pl, country):
        pls = self.website._get_pl(
            country,
            show,
            self.website.pricelist_id.id,
            current_pl,
            self.website.pricelist_ids
        )
        return pls

    def test_get_pricelist_available_show(self):
        show = True
        current_pl = False

        country_list = {
            False: ['Public Pricelist', 'EUR', 'Benelux', 'Canada'],
            'BE': ['EUR', 'Benelux'],
            'IT': ['EUR'],
            'CA': ['Canada'],
            'US': ['Public Pricelist', 'EUR', 'Benelux', 'Canada']
        }
        for country, result in country_list.items():
            pls = self.get_pl(show, current_pl, country)
            self.assertEquals(len(set(pls.mapped('name')) & set(result)), len(pls), 'Test failed for %s (%s %s vs %s %s)'
                              % (country, len(pls), pls.mapped('name'), len(result), result))

    def test_get_pricelist_available_not_show(self):
        show = False
        current_pl = False

        country_list = {
            False: ['Public Pricelist', 'EUR', 'Benelux', 'Christmas', 'Canada'],
            'BE': ['EUR', 'Benelux', 'Christmas'],
            'IT': ['EUR', 'Christmas'],
            'US': ['Public Pricelist', 'EUR', 'Benelux', 'Christmas', 'Canada'],
            'CA': ['Canada']
        }

        for country, result in country_list.items():
            pls = self.get_pl(show, current_pl, country)
            self.assertEquals(len(set(pls.mapped('name')) & set(result)), len(pls), 'Test failed for %s (%s %s vs %s %s)'
                              % (country, len(pls), pls.mapped('name'), len(result), result))

    def test_get_pricelist_available_promocode(self):
        christmas_pl = self.ref('website_sale.list_christmas')
        public_pl = self.ref('product.list0')
        self.args = {
            'show': False,
            'current_pl': public_pl,
        }

        country_list = {
            False: True,
            'BE': True,
            'IT': True,
            'US': True,
            'CA': False
        }

        for country, result in country_list.items():
            self.args['country'] = country
            # mock patch method could not pass env context
            available = self.website.is_pricelist_available(christmas_pl)
            if result:
                self.assertTrue(available, 'AssertTrue failed for %s' % country)
            else:
                self.assertFalse(available, 'AssertFalse failed for %s' % country)

    def test_get_pricelist_available_show_with_auto_property(self):
        show = True
        self.env.user.partner_id.country_id = self.env.ref('base.be')  # Add EUR pricelist auto
        current_pl = False

        country_list = {
            False: ['Public Pricelist', 'EUR', 'Benelux', 'Canada'],
            'BE': ['EUR', 'Benelux'],
            'IT': ['EUR'],
            'CA': ['EUR', 'Canada'],
            'US': ['Public Pricelist', 'EUR', 'Benelux', 'Canada']
        }
        for country, result in country_list.items():
            pls = self.get_pl(show, current_pl, country)
            self.assertEquals(len(set(pls.mapped('name')) & set(result)), len(pls), 'Test failed for %s (%s %s vs %s %s)'
                              % (country, len(pls), pls.mapped('name'), len(result), result))
