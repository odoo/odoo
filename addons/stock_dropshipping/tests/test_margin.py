# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged('post_install', '-at_install')
class TestDropshipMargin(TestStockValuationCommon):

    _test_user_groups = (
        'sales_team.group_sale_salesman',  # sale.order margins are the subject
        'purchase.group_purchase_user',  # purchase order feeding the margin valuation
        'stock.group_stock_manager',  # dropship picking validation
        'product.group_product_manager',  # route and vendor price on the product
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env['res.partner'].create({'name': 'Customer'})

    def test_dropship_fifo_purchase_price(self):
        """ Check that when the product is dropshipped, the purchase_price used is based on the unit
        price of the purchase order.
        """
        dropship_route = self.env.ref('stock_dropshipping.route_drop_shipping')
        self.product_fifo_auto.write({
            'seller_ids': [Command.create({'partner_id': self.vendor.id, 'price': 20})],
            'route_ids': [Command.link(dropship_route.id)]
        })
        # create and confirm SO and PO
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [Command.create({
                'product_id': self.product_fifo_auto.id,
                'product_uom_qty': 1.0,
            })],
        })
        so.action_confirm()
        po = self.env['purchase.order'].search([
            ('origin', '=', so.name),
            ('partner_id', '=', self.vendor.id),
        ], limit=1)
        po.button_confirm()

        # until dropship validation, purchase price of the sale order line is the product's standard price
        self.assertEqual(self.product_fifo_auto.standard_price, 10)
        self.assertEqual(so.order_line.purchase_price, 10)

        # after dropship validation, purchase price of the sale order line is the PO's unit cost
        so.picking_ids.button_validate()
        self.assertEqual(po.order_line.price_unit, 20)
        self.assertEqual(so.order_line.purchase_price, 20)
