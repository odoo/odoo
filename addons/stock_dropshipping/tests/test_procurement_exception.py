# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestProcurementException(common.TransactionCase):

    def test_00_procurement_exception(self):

        # I create a product with no supplier define for it.
        product_with_no_seller = self.env['product.product'].create({
            "name": 'product with no seller',
            'list_price': 20.00,
            'standard_price': 15.00,
            'categ_id': self.env.ref('product.product_category_1').id,
        })

        # I create a sales order with this product with route dropship.
        sale_order_route_dropship01 = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_2').id,
            'partner_invoice_id': self.env.ref('base.res_partner_address_3').id,
            'partner_shipping_id': self.env.ref('base.res_partner_address_3').id,
            'note': 'crossdock route',
            'payment_term_id': self.env.ref('account.account_payment_term').id,
            'order_line': [(0, 0, {
                'product_id': product_with_no_seller.id,
                'product_uom_qty': 1,
                'route_id': self.env.ref('stock_dropshipping.route_drop_shipping').id,
            })]
        })

        # I confirm the sales order, but it will raise an error
        with self.assertRaises(Exception):
            sale_order_route_dropship01.action_confirm()

        # I set the at least one supplier on the product.
        product_with_no_seller.write({
            'seller_ids': [(0, 0, {
                'delay': 1,
                'name': self.env.ref('base.res_partner_2').id,
                'min_qty': 2.0
            })]
        })

        # I confirm the sales order, no error this time
        sale_order_route_dropship01.action_confirm()

        # I check a purchase quotation was created.
        purchase = self.env['purchase.order.line'].search([
            ('sale_line_id', '=', sale_order_route_dropship01.order_line.ids[0])]).order_id

        self.assertTrue(purchase, 'No Purchase Quotation is created')
