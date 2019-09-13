# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common


class TestCoursePurchaseFlow(common.SlidesCase):
    def test_course_purchase_flow(self):
        # Step1: create a course product and assign it to 2 slide.channels
        course_product = self.env['product.product'].create({
            'name': "Course Product",
            'standard_price': 100,
            'list_price': 150,
            'type': 'service',
            'invoice_policy': 'order',
            'is_published': True,
        })

        self.channel.write({
            'enroll': 'payment',
            'product_id': course_product.id
        })

        self.channel_2 = self.env['slide.channel'].with_user(self.user_publisher).create({
            'name': 'Test Channel',
            'enroll': 'payment',
            'product_id': course_product.id
        })

        # Step 2: create a sale_order with the course product
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {
                    'name': course_product.name,
                    'product_id': course_product.id,
                    'product_uom_qty': 1,
                    'price_unit': course_product.list_price,
                })
            ],
        })

        sale_order.action_confirm()

        # Step 3: check that the customer is now a member of both channel
        self.assertIn(self.customer, self.channel.partner_ids)
        self.assertIn(self.customer, self.channel_2.partner_ids)
