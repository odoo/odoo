# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon


class TestSaleTimesheetMargin(TestStockValuationCommon):

    @classmethod
    def setUpClass(cls):
        super(TestSaleTimesheetMargin, cls).setUpClass()

    def _create_sale_order(self):
        return self.env['sale.order'].create({
            'name': 'Sale order',
            'partner_id': self.env.ref('base.partner_admin').id,
            'partner_invoice_id': self.env.ref('base.partner_admin').id,
        })

    def _create_sale_order_line(self, sale_order, product, quantity, price_unit=0):
        return self.env['sale.order.line'].create({
            'name': 'Sale order',
            'order_id': sale_order.id,
            'price_unit': price_unit,
            'product_id': product.id,
            'product_uom_qty': quantity,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
        })

    def _create_product(self):
        product_template = self.env['product.template'].create({
            'name': 'Super product',
            'type': 'product',
        })
        product_template.categ_id.property_cost_method = 'fifo'
        return product_template.product_variant_ids

    def test_manual_purchase_price(self):
        product = self._create_product()
        product.standard_price = 100
        so = self._create_sale_order()
        self._create_sale_order_line(so, product, 1)
        self.assertEqual(so.order_line.purchase_price, 100)
        so.order_line.purchase_price = 10
        self.assertEqual(so.order_line.purchase_price, 10)

        # send quotation
        email_act = so.action_quotation_send()
        email_ctx = email_act.get('context', {})
        so.with_context(**email_ctx).message_post_with_template(email_ctx.get('default_template_id'))
        self.assertEqual(so.order_line.purchase_price, 10, 'The purchase_price should be 10 and not 100')
