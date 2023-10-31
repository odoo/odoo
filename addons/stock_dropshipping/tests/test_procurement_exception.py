# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form


class TestProcurementException(common.TransactionCase):

    def test_00_procurement_exception(self):

        res_partner_2 = self.env['res.partner'].create({'name': 'My Test Partner'})
        res_partner_address = self.env['res.partner'].create({
            'name': 'My Test Partner Address',
            'parent_id': res_partner_2.id,
        })

        # I create a product with no supplier define for it.
        product_form = Form(self.env['product.product'])
        product_form.name = 'product with no seller'
        product_form.list_price = 20.00
        product_form.categ_id = self.env.ref('product.product_category_1')
        product_with_no_seller = product_form.save()

        product_with_no_seller.standard_price = 70.0

        # I create a sales order with this product with route dropship.
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = res_partner_2
        so_form.partner_invoice_id = res_partner_address
        so_form.partner_shipping_id = res_partner_address
        so_form.payment_term_id = self.env.ref('account.account_payment_term_end_following_month')
        with so_form.order_line.new() as line:
            line.product_id = product_with_no_seller
            line.product_uom_qty = 3
            line.route_id = self.env.ref('stock_dropshipping.route_drop_shipping')
        sale_order_route_dropship01 = so_form.save()

        # I confirm the sales order, but it will raise an error
        with self.assertRaises(Exception):
            sale_order_route_dropship01.action_confirm()

        # I set the at least one supplier on the product.
        with Form(product_with_no_seller) as f:
            with f.seller_ids.new() as seller:
                seller.delay = 1
                seller.name = res_partner_2
                seller.min_qty = 2.0

        # I confirm the sales order, no error this time
        sale_order_route_dropship01.action_confirm()

        # I check a purchase quotation was created.
        purchase = self.env['purchase.order.line'].search([
            ('sale_line_id', '=', sale_order_route_dropship01.order_line.ids[0])]).order_id

        self.assertTrue(purchase, 'No Purchase Quotation is created')
