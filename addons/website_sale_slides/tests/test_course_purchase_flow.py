# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common
from odoo.tests.common import users


class TestCoursePurchaseFlow(common.SlidesCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_salesman = cls.env['res.users'].create({
            'name': 'salesman',
            'login': 'salesman',
            'email': 'salesman007@example.com',
            'group_ids': [(6, 0, cls.env.ref('sales_team.group_sale_salesman').ids)],
        })

        cls.course_product = cls.env['product.product'].create({
            'name': "Course Product",
            'standard_price': 100,
            'list_price': 150,
            'type': 'service',
            'invoice_policy': 'order',
            'is_published': True,
        })

    def test_course_purchase_flow(self):
        # Step1: assign a course product to 2 slide.channels
        self.channel.write({
            'enroll': 'payment',
            'product_id': self.course_product.id
        })

        self.channel_2 = self.env['slide.channel'].with_user(self.user_officer).create({
            'name': 'Test Channel',
            'enroll': 'payment',
            'product_id': self.course_product.id,
            'is_published': True,
        })

        # Step 2: create a sale_order with the course product
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {
                    'name': self.course_product.name,
                    'product_id': self.course_product.id,
                    'product_uom_qty': 1,
                    'price_unit': self.course_product.list_price,
                })
            ],
        })

        sale_order.action_confirm()

        # Step 3: check that the customer is now a member of both channel
        self.assertIn(self.customer, self.channel.partner_ids)
        self.assertIn(self.customer, self.channel_2.partner_ids)

        # Step 4: Same test as salesman
        salesman_sale_order = self.env['sale.order'].with_user(self.user_salesman).create({
            'partner_id': self.user_portal.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.course_product.name,
                    'product_id': self.course_product.id,
                    'product_uom_qty': 1,
                    'price_unit': self.course_product.list_price,
                })
            ],
        })

        salesman_sale_order.action_confirm()

        self.assertIn(self.user_portal.partner_id, self.channel.partner_ids)
        self.assertIn(self.user_portal.partner_id, self.channel_2.partner_ids)

    @users('user_officer')
    def test_course_product_published_synch(self):
        """ Test the synchronization between a course and its product """
        course_1 = self.env['slide.channel'].create({
            'name': 'Test Channel 1',
            'enroll': 'payment',
            'product_id': self.course_product.id,
        })
        course_2 = self.env['slide.channel'].create({
            'name': 'Test Channel 2',
            'enroll': 'payment',
            'product_id': self.course_product.id,
            'is_published': True,
        })

        # The course_1 is not published by default which doesn't impact the product
        self.assertFalse(course_1.is_published)
        self.assertTrue(self.course_product.is_published)

        course_1.is_published = True

        # The course_1 and the product are published
        self.assertTrue(course_1.is_published)
        self.assertTrue(self.course_product.is_published)

        self.course_product.is_published = False

        # Unpublishing the product should not change the course_1
        self.assertTrue(course_1.is_published)
        self.assertFalse(self.course_product.is_published)

        course_1.is_published = False

        self.assertFalse(course_1.is_published)
        self.assertFalse(self.course_product.is_published)

        course_1.is_published = True

        # Publishing the course_1 should publish the product
        self.assertTrue(course_1.is_published)
        self.assertTrue(self.course_product.is_published)

        (course_1 + course_2).write({'is_published': False})

        # If all course linked to a product are unpublished, we unpublished the product
        self.assertFalse(course_1.is_published)
        self.assertFalse(course_2.is_published)
        self.assertFalse(self.course_product.is_published)
