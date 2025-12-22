# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.event_booth_sale.tests.common import TestEventBoothSaleCommon
from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon
from odoo.addons.website_sale.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class TestWebsiteBoothPriceList(TestEventBoothSaleCommon, TestWebsiteEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.WebsiteSaleController = WebsiteSale()
        cls.booth_1 = cls.env['event.booth'].create({
            'booth_category_id': cls.event_booth_category_1.id,
            'event_id': cls.event.id,
            'name': 'Test Booth 1',
        })

        cls.booth_2 = cls.env['event.booth'].create({
            'booth_category_id': cls.event_booth_category_1.id,
            'event_id': cls.event.id,
            'name': 'Test Booth 2',
        })

    def test_pricelist_different_currency(self):
        self.env['product.pricelist'].search([('id', '!=', self.pricelist.id)]).action_archive()
        self.pricelist.write({
            'currency_id': self.env.company.currency_id.id,
            'item_ids': [(5, 0, 0)],
            'name': 'Test Pricelist (no discount)',
        })
        so_line = self.env['sale.order.line'].create({
            'event_booth_category_id': self.event_booth_category_1.id,
            'event_booth_pending_ids': (self.booth_1 + self.booth_2).ids,
            'event_id': self.event.id,
            'order_id': self.so.id,
            'product_id': self.event_booth_product.id,
        })
        self.assertEqual(so_line.price_reduce_taxexcl, 40)

        # set pricelist to 10% - without discount
        pl2 = self.pricelist.copy({
            'currency_id': self.currency_test.id,
            'item_ids': [(5, 0, 0), (0, 0, {
                'applied_on': '3_global',
                'compute_price': 'percentage',
                'percent_price': 10,
            })],
            'name': 'Test pricelist (with discount)',
        })
        self.so._cart_update_pricelist(pricelist_id=pl2.id)
        self.assertEqual(so_line.price_reduce_taxexcl, 360, 'Incorrect amount based on the pricelist "Without Discount" and its currency.')
