# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import MockRequest


@tagged('post_install', '-at_install')
class TestWebsiteEventPriceList(TestWebsiteEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.WebsiteSaleController = WebsiteSale()

    def test_pricelist_different_currency(self):
        self.pricelist.write({
            'currency_id': self.env.company.currency_id.id,
            'item_ids': [Command.clear()],
            'name': 'No discount',
        })
        order = self._create_so(
            order_line=[
                Command.create({
                    'event_id': self.event.id,
                    'event_ticket_id': self.ticket.id,
                    'name': self.event.name,
                    'product_id': self.ticket.product_id.id,
                })
            ]
        )
        so_line = order.order_line
        self.assertEqual(so_line.price_reduce_taxexcl, 100)

        # set pricelist to 10% - without discount
        pl2 = self.pricelist.copy({
            'currency_id': self.currency_test.id,
            'item_ids': [(5, 0, 0), (0, 0, {
                'applied_on': '3_global',
                'compute_price': 'percentage',
                'percent_price': 10,
            })],
            'name': 'Percentage Discount',
            'selectable': True,
        })
        with MockRequest(self.env, website=self.website, sale_order_id=order.id) as req:
            self.assertEqual(req.pricelist, self.pricelist)
            self.WebsiteSaleController.pricelist_change(pl2)
            self.assertEqual(so_line.price_reduce_taxexcl, 900, 'Incorrect amount based on the pricelist and its currency.')
