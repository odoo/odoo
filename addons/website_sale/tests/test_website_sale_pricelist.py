# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from mock import patch
from odoo.tests.common import TransactionCase


class TestWebsitePriceList(TransactionCase):

    # Mock nedded because request.session doesn't exist during test
    def _get_pricelist_available(self, show_visible=False):
        return self.get_pl(self.args.get('show'), self.args.get('current_pl'), self.args.get('country'))

    def setUp(self):
        super(TestWebsitePriceList, self).setUp()
        self.website = self.env['website'].browse(1)
        self.website.pricelist_id = self.ref('product.list0')
        self.patcher = patch('odoo.addons.website_sale.models.sale_order.Website.get_pricelist_available', wraps=self._get_pricelist_available)
        self.mock_get_pricelist_available = self.patcher.start()

    def get_pl(self, show, current_pl, country):
        pls = self.website._get_pl(
            country,
            show,
            self.website.pricelist_id.id,
            current_pl,
            self.website.website_pricelist_ids
        )
        return pls

    def test_get_pricelist_available_show(self):
        show = True
        current_pl = False

        country_list = {
            False: 2,
            'BE': 2,
            'IT': 1,
            'US': 1,
            'AF': 2
        }
        for country, result in country_list.items():
            pls = self.get_pl(show, current_pl, country)
            self.assertEquals(len(pls), result)

    def test_get_pricelist_available_not_show(self):
        show = False
        current_pl = False

        country_list = {
            False: 3,
            'BE': 3,
            'IT': 1,
            'US': 1,
            'AF': 3
        }

        for country, result in country_list.items():
            pls = self.get_pl(show, current_pl, country)
            self.assertEquals(len(pls), result)

    def test_get_pricelist_available_promocode(self):
        christmas_pl = self.ref('website_sale.list_christmas')
        self.args = {
            'show': True,
            'current_pl': christmas_pl,
        }

        country_list = {
            False: True,
            'BE': True,
            'IT': False,
            'US': False,
        }

        for country, result in country_list.items():
            self.args['country'] = country
            # mock patch method could not pass env context
            available = self.website.is_pricelist_available(christmas_pl)
            if result:
                self.assertTrue(available)
            else:
                self.assertFalse(available)

    def tearDown(self):
        self.patcher.stop()
        super(TestWebsitePriceList, self).tearDown()
