# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import fields
from odoo.tests import HttpCase, tagged, TransactionCase
from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon


@tagged('post_install', '-at_install')
class TestUi(TestSaleProductAttributeValueCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super(TestUi, cls).setUpClass()
        cls.env.user.partner_id.property_product_pricelist = cls.env.ref('product.list0')
        cls.env['website'].get_current_website().company_id = cls.env.company
        # set currency to not rely on demo data and avoid possible race condition
        cls.currency_ratio = 1.0
        pricelist = cls.env.ref('product.list0')
        new_currency = cls._setup_currency(cls.currency_ratio)
        pricelist.currency_id = new_currency
        pricelist.flush()

    def test_01_admin_shop_sale_coupon_tour(self):
        # pre enable "Show # found" option to avoid race condition...
        self.env.user.write({
            'street': '215 Vine St',
            'phone': '+1 555-555-5555',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_39').id,
        })
        self.env.ref('payment.payment_acquirer_transfer').sudo().company_id = self.env.company
        public_category = self.env['product.public.category'].create({'name': 'Public Category'})

        large_cabinet = self.env['product.product'].create({
            'name': 'Small Cabinet',
            'list_price': 320.0,
            'type': 'consu',
            'is_published': True,
            'sale_ok': True,
            'public_categ_ids': [(4, public_category.id)],
            'taxes_id': False,
        })

        free_large_cabinet = self.env['product.product'].create({
            'name': 'Free Product - Small Cabinet',
            'type': 'service',
            'taxes_id': False,
            'supplier_taxes_id': False,
            'sale_ok': False,
            'purchase_ok': False,
            'invoice_policy': 'order',
            'default_code': 'FREELARGECABINET',
            'categ_id': self.env.ref('product.product_category_all').id,
            'taxes_id': False,
        })

        ten_percent = self.env['product.product'].create({
            'name': '10.0% discount on total amount',
            'type': 'service',
            'taxes_id': False,
            'supplier_taxes_id': False,
            'sale_ok': False,
            'purchase_ok': False,
            'invoice_policy': 'order',
            'default_code': '10PERCENTDISC',
            'categ_id': self.env.ref('product.product_category_all').id,
            'taxes_id': False,
        })

        self.env['coupon.program'].search([]).write({'active': False})

        self.env['coupon.program'].create({
            'name': "Buy 3 Small Cabinets, get one for free",
            'promo_code_usage': 'no_code_needed',
            'discount_apply_on': 'on_order',
            'reward_type': 'product',
            'program_type': 'promotion_program',
            'reward_product_id': large_cabinet.id,
            'rule_min_quantity': 3,
            'rule_products_domain': "[['name', 'ilike', 'Small Cabinet']]",
            'discount_line_product_id': free_large_cabinet.id
        })

        self.env['coupon.program'].create({
            'name': "Code for 10% on orders",
            'promo_code_usage': 'code_needed',
            'promo_code': 'testcode',
            'discount_apply_on': 'on_order',
            'discount_type': 'percentage',
            'discount_percentage': 10.0,
            'program_type': 'promotion_program',
            'discount_line_product_id': ten_percent.id
        })

        self.env.ref("website_sale.search_count_box").write({"active": True})
        self.start_tour("/", 'shop_sale_coupon', login=self.env.user.login)


@tagged('post_install', '-at_install')
class TestWebsiteSaleCoupon(TransactionCase):

    def setUp(self):
        super(TestWebsiteSaleCoupon, self).setUp()
        program = self.env['coupon.program'].create({
            'name': '10% TEST Discount',
            'promo_code_usage': 'code_needed',
            'discount_apply_on': 'on_order',
            'discount_type': 'percentage',
            'discount_percentage': 10.0,
            'program_type': 'coupon_program',
        })

        self.env['coupon.generate.wizard'].with_context(active_id=program.id).create({}).generate_coupon()
        self.coupon = program.coupon_ids[0]

        self.steve = self.env['res.partner'].create({
            'name': 'Steve Bucknor',
            'email': 'steve.bucknor@example.com',
        })
        self.empty_order = self.env['sale.order'].create({
            'partner_id': self.steve.id
        })

    def test_01_gc_coupon(self):
        # 1. Simulate a frontend order (website, product)
        order = self.empty_order
        order.website_id = self.env['website'].browse(1)
        self.env['sale.order.line'].create({
            'product_id': self.env['product.product'].create({
                'name': 'Product A',
                'list_price': 100,
                'sale_ok': True,
            }).id,
            'name': 'Product A',
            'product_uom_qty': 2.0,
            'order_id': order.id,
        })

        # 2. Apply the coupon
        self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
            'coupon_code': self.coupon.code
        }).process_coupon()
        order.recompute_coupon_lines()

        self.assertEqual(len(order.applied_coupon_ids), 1, "The coupon should've been applied on the order")
        self.assertEqual(self.coupon, order.applied_coupon_ids)
        self.assertEqual(self.coupon.state, 'used')

        # 3. Test recent order -> Should not be removed
        order._gc_abandoned_coupons()

        self.assertEqual(len(order.applied_coupon_ids), 1, "The coupon shouldn't have been removed from the order no more than 4 days")
        self.assertEqual(self.coupon.state, 'used', "Should not have been changed")

        # 4. Test order not older than ICP validity -> Should not be removed
        ICP = self.env['ir.config_parameter']
        icp_validity = ICP.create({'key': 'website_sale_coupon.abandonned_coupon_validity', 'value': 5})
        order.flush()
        query = """UPDATE %s SET write_date = %%s WHERE id = %%s""" % (order._table,)
        self.env.cr.execute(query, (fields.Datetime.to_string(fields.datetime.now() - timedelta(days=4, hours=2)), order.id))
        order._gc_abandoned_coupons()

        self.assertEqual(len(order.applied_coupon_ids), 1, "The coupon shouldn't have been removed from the order the order is 4 days old but icp validity is 5 days")
        self.assertEqual(self.coupon.state, 'used', "Should not have been changed (2)")

        # 5. Test order with no ICP and older then 4 default days -> Should be removed
        icp_validity.unlink()
        order._gc_abandoned_coupons()

        self.assertEqual(len(order.applied_coupon_ids), 0, "The coupon should've been removed from the order as more than 4 days")
        self.assertEqual(self.coupon.state, 'new', "Should have been reset.")
