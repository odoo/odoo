# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon
from odoo.addons.website_sale.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class TestWebsiteEventPriceList(TestWebsiteEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.WebsiteSaleController = WebsiteSale()

    def test_pricelist_different_currency(self):
        self.env['product.pricelist'].search([('id', '!=', self.pricelist.id)]).action_archive()
        self.pricelist.write({
            'currency_id': self.env.company.currency_id.id,
            'item_ids': [Command.clear()],
            'name': 'No discount',
        })
        so_line = self.env['sale.order.line'].create({
            'event_id': self.event.id,
            'event_ticket_id': self.ticket.id,
            'name': self.event.name,
            'order_id': self.so.id,
            'product_id': self.ticket.product_id.id,
            'product_uom_qty': 1,
        })
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
        })
        self.so._cart_update_pricelist(pricelist_id=pl2.id)
        self.assertEqual(so_line.price_reduce_taxexcl, 900, 'Incorrect amount based on the pricelist and its currency.')
