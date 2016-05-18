from openerp.tests.common import TransactionCase
from mock import patch


class TestWebsitePriceList(TransactionCase):

    # Mock nedded because request.session doesn't exist during test
    def _get_pricelist_available(self, cr, uid, show_visible=False, context=None):
        return self.get_pl(context.get('show'), context.get('current_pl'), context.get('country'))

    def setUp(self):
        super(TestWebsitePriceList, self).setUp()
        self.website = self.registry('website').browse(self.cr, self.uid, 1)
        self.website.pricelist_id = self.registry('ir.model.data').xmlid_to_res_id(self.cr, self.uid, 'product.list0')
        self.patcher = patch('openerp.addons.website_sale.models.sale_order.website.get_pricelist_available', wraps=self._get_pricelist_available)
        self.mock_get_pricelist_available = self.patcher.start()

    def get_pl(self, show, current_pl, country):
        pl_ids = self.website._get_pl(
            country,
            show,
            self.website.pricelist_id.id,
            current_pl,
            self.website.website_pricelist_ids
        )
        return self.env['product.pricelist'].browse(pl_ids)

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
        christmas_pl = self.registry('ir.model.data').xmlid_to_res_id(self.cr, self.uid, 'website_sale.list_christmas')
        context = {
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
            context['country'] = country
            available = self.website.with_context(context).is_pricelist_available(christmas_pl)
            if result:
                self.assertTrue(available)
            else:
                self.assertFalse(available)

    def tearDown(self):
        self.patcher.stop()
        super(TestWebsitePriceList, self).tearDown()
