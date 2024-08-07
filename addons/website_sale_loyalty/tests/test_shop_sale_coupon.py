# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.sale.tests.test_sale_product_attribute_value_config import (
    TestSaleProductAttributeValueCommon,
)
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_loyalty.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class WebsiteSaleLoyaltyTestUi(TestSaleProductAttributeValueCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.user_admin').write({
            'company_id': cls.env.company.id,
            'company_ids': [(4, cls.env.company.id)],
            'name': 'Mitchell Admin',
            'street': '215 Vine St',
            'phone': '+1 555-555-5555',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env.ref('base.state_us_39').id,
        })
        cls.env.ref('base.user_admin').sudo().partner_id.company_id = cls.env.company
        cls.env.ref('website.default_website').company_id = cls.env.company

    def test_01_admin_shop_sale_loyalty_tour(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.sudo().write({
            'state': 'enabled',
            'is_published': True,
            'company_id': self.env.company.id,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        # pre enable "Show # found" option to avoid race condition...
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
            'supplier_taxes_id': False,
            'sale_ok': False,
            'purchase_ok': False,
            'invoice_policy': 'order',
            'default_code': '10PERCENTDISC',
            'categ_id': self.env.ref('product.product_category_all').id,
            'taxes_id': False,
        })

        self.env['loyalty.program'].search([]).write({'active': False})

        self.env['loyalty.program'].create({
            'name': 'Buy 4 Small Cabinets, get one for free',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'minimum_qty': 4,
                'product_ids': large_cabinet,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': large_cabinet.id,
                'discount_line_product_id': free_large_cabinet.id,
            })]
        })

        self.env['loyalty.program'].create({
            'name': 'Code for 10% on orders',
            'trigger': 'with_code',
            'rule_ids': [(0, 0, {
                'mode': 'with_code',
                'code': 'testcode',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
                'discount_line_product_id': ten_percent.id,
            })],
        })

        vip_program = self.env['loyalty.program'].create({
            'name': 'VIP',
            'trigger': 'auto',
            'program_type': 'loyalty',
            'portal_visible': True,
            'applies_on': 'both',
            'rule_ids': [(0, 0, {
                'mode': 'auto',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 21,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
                'required_points': 50,
            })],
        })

        self.env['loyalty.card'].create({
            'partner_id': self.env.ref('base.partner_admin').id,
            'program_id': vip_program.id,
            'point_name': "Points",
            'points': 371.03,
        })

        self.env.ref("website_sale.reduction_code").write({"active": True})
        self.start_tour("/", 'shop_sale_loyalty', login="admin")

    def test_02_admin_shop_gift_card_tour(self):
        # pre enable "Show # found" option to avoid race condition...
        public_category = self.env['product.public.category'].create({'name': 'Public Category'})

        gift_card = self.env['product.product'].create({
            'name': 'TEST - Gift Card',
            'list_price': 50,
            'type': 'service',
            'is_published': True,
            'sale_ok': True,
            'public_categ_ids': [(4, public_category.id)],
            'taxes_id': False,
        })
        self.env['product.product'].create({
            'name': 'TEST - Small Drawer',
            'list_price': 50,
            'type': 'consu',
            'is_published': True,
            'sale_ok': True,
            'public_categ_ids': [(4, public_category.id)],
            'taxes_id': False,
        })
        # Disable any other program
        self.env['loyalty.program'].search([]).write({'active': False})

        gift_card_program = self.env['loyalty.program'].create({
            'name': 'Gift Cards',
            'program_type': 'gift_card',
            'applies_on': 'future',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'reward_point_amount': 1,
                'reward_point_mode': 'money',
                'reward_point_split': True,
                'product_ids': gift_card,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 1,
                'discount_applicability': 'order',
                'required_points': 1,
                'description': 'PAY WITH GIFT CARD',
            })],
        })
        # Another program for good measure
        self.env['loyalty.program'].create({
            'name': '10% Discount',
            'applies_on': 'current',
            'trigger': 'with_code',
            'program_type': 'promotion',
            'rule_ids': [(0, 0, {
                'mode': 'with_code',
                'code': '10PERCENT',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        })
        # Create a gift card to be used
        self.env['loyalty.card'].create({
            'program_id': gift_card_program.id,
            'points': 50,
            'code': 'GIFT_CARD',
        })

        self.env.ref("website_sale.reduction_code").write({"active": True})
        self.start_tour('/', 'shop_sale_gift_card', login='admin')

        self.assertEqual(len(gift_card_program.coupon_ids), 2, 'There should be two coupons, one with points, one without')
        self.assertEqual(len(gift_card_program.coupon_ids.filtered('points')), 1, 'There should be two coupons, one with points, one without')

    def test_02_admin_shop_ewallet_tour(self):
        public_category = self.env['product.public.category'].create({'name': 'Public Category'})
        self.env['product.product'].create({
            'name': 'TEST - Small Drawer',
            'list_price': 50,
            'type': 'consu',
            'is_published': True,
            'sale_ok': True,
            'public_categ_ids': [(4, public_category.id)],
            'taxes_id': False,
        })
        # Disable any other program
        self.env['loyalty.program'].search([]).write({'active': False})
        ewallet_program = self.env['loyalty.program'].create({
            'name': 'ewallet - test',
            'applies_on': 'future',
            'trigger': 'auto',
            'program_type': 'ewallet',
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 1,
            })],
        })
        ewallet_program.currency_id = self.env.ref('base.USD')
        self.env['loyalty.card'].create({
            'partner_id': self.env.ref('base.partner_admin').id,
            'program_id': ewallet_program.id,
            'points': 1000,
        })
        self.start_tour('/', 'shop_sale_ewallet', login='admin')


@tagged('post_install', '-at_install')
class TestWebsiteSaleCoupon(HttpCase):

    @classmethod
    def setUpClass(cls):
        super(TestWebsiteSaleCoupon, cls).setUpClass()
        program = cls.env['loyalty.program'].create({
            'name': '10% TEST Discount',
            'trigger': 'with_code',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {})],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
            })],
        })

        cls.env['loyalty.generate.wizard'].with_context(active_id=program.id).create({
            'coupon_qty': 1,
            'points_granted': 1
        }).generate_coupons()
        cls.coupon = program.coupon_ids[0]

        cls.steve = cls.env['res.partner'].create({
            'name': 'Steve Bucknor',
            'email': 'steve.bucknor@example.com',
        })
        cls.empty_order = cls.env['sale.order'].create({
            'partner_id': cls.steve.id
        })

    def _apply_promo_code(self, order, code, no_reward_fail=True):
        status = order._try_apply_code(code)
        if 'error' in status:
            raise ValidationError(status['error'])
        if not status and no_reward_fail:
            # Can happen if global discount got filtered out in `_get_claimable_rewards`
            raise ValidationError('No reward to claim with this coupon')
        coupons = self.env['loyalty.card']
        rewards = self.env['loyalty.reward']
        for coupon, coupon_rewards in status.items():
            coupons |= coupon
            rewards |= coupon_rewards
        if len(coupons) == 1 and len(rewards) == 1:
            status = order._apply_program_reward(rewards, coupons)
            if 'error' in status:
                raise ValidationError(status['error'])

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
        self._apply_promo_code(order, self.coupon.code)

        self.assertEqual(len(order.applied_coupon_ids), 1, "The coupon should've been applied on the order")
        self.assertEqual(self.coupon, order.applied_coupon_ids)

        # 3. Test recent order -> Should not be removed
        order._gc_abandoned_coupons()

        self.assertEqual(len(order.applied_coupon_ids), 1, "The coupon shouldn't have been removed from the order no more than 4 days")

        # 4. Test order not older than ICP validity -> Should not be removed
        ICP = self.env['ir.config_parameter']
        icp_validity = ICP.create({'key': 'website_sale_coupon.abandonned_coupon_validity', 'value': 5})
        self.env.flush_all()
        query = """UPDATE %s SET write_date = %%s WHERE id = %%s""" % (order._table,)
        self.env.cr.execute(query, (fields.Datetime.to_string(fields.datetime.now() - timedelta(days=4, hours=2)), order.id))
        order._gc_abandoned_coupons()

        self.assertEqual(len(order.applied_coupon_ids), 1, "The coupon shouldn't have been removed from the order the order is 4 days old but icp validity is 5 days")

        # 5. Test order with no ICP and older then 4 default days -> Should be removed
        icp_validity.unlink()
        order._gc_abandoned_coupons()

        self.assertEqual(len(order.applied_coupon_ids), 0, "The coupon should've been removed from the order as more than 4 days")

    def test_02_apply_discount_code_program_multi_rewards(self):
        """
            Check the triggering of a promotion program based on a promo code with multiple rewards
        """
        self.env['loyalty.program'].search([]).write({'active': False})
        chair = self.env['product.product'].create({
            'name': 'Super Chair', 'list_price': 1000, 'website_published': True
        })
        self.discount_code_program_multi_rewards = self.env['loyalty.program'].create({
            'name': 'Discount code program',
            'program_type': 'promo_code',
            'applies_on': 'current',
            'trigger': 'with_code',
            'rule_ids': [(0, 0, {
                'code': '12345',
                'reward_point_amount': 1,
                'reward_point_mode': 'order',
            })],
            'reward_ids': [
                (0, 0, {
                    'reward_type': 'discount',
                    'discount': 10,
                    'discount_applicability': 'specific',
                    'required_points': 1,
                    'discount_product_ids': chair,
                }),
                (0, 0, {
                    'reward_type': 'discount',
                    'discount': 50,
                    'discount_applicability': 'order',
                    'required_points': 1,
                }),
            ],
        })
        self.start_tour('/', 'apply_discount_code_program_multi_rewards', login='admin')

    def test_03_remove_coupon(self):
        # 1. Simulate a frontend order (website, product)
        order = self.empty_order
        order.website_id = self.env['website'].browse(1)
        self.env['sale.order.line'].create({
            'product_id': self.env['product.product'].create({
                'name': 'Product A', 'list_price': 100, 'sale_ok': True
            }).id,
            'name': 'Product A',
            'order_id': order.id,
        })

        # 2. Apply the coupon
        self._apply_promo_code(order, self.coupon.code)

        # 3. Remove the coupon
        coupon_line = order.website_order_line.filtered(
            lambda l: l.coupon_id and l.coupon_id.id == self.coupon.id
        )

        kwargs = {
            'line_id': None, 'product_id': coupon_line.product_id.id, 'add_qty': None, 'set_qty': 0
        }
        order._cart_update(**kwargs)

        msg = "The coupon should've been removed from the order"
        self.assertEqual(len(order.applied_coupon_ids), 0, msg=msg)

    def test_04_apply_coupon_code_twice(self):
        """This test ensures that applying a coupon with code twice will:
            1. Raise an error
            2. Not delete the coupon
        """
        website = self.env['website'].browse(1)

        # Create product
        product = self.env['product.product'].create({
            'name': 'Product',
            'list_price': 100,
            'sale_ok': True,
            'taxes_id': [],
        })

        order = self.empty_order
        order.write({
            'website_id': website.id,
            'order_line': [
                Command.create({
                    'product_id': product.id,
                }),
            ]
        })

        WebsiteSaleController = WebsiteSale()

        installed_modules = set(self.env['ir.module.module'].search([
            ('state', '=', 'installed'),
        ]).mapped('name'))
        for _ in http._generate_routing_rules(installed_modules, nodb_only=False):
            pass

        with MockRequest(self.env, website=website, sale_order_id=order.id) as request:
            # Check the base cart value
            self.assertEqual(order.amount_total, 100.0, "The base cart value is incorrect.")

            # Apply coupon for the first time
            WebsiteSaleController.pricelist(promo=self.coupon.code)

            # Check that the coupon has been applied
            self.assertEqual(order.amount_total, 90.0, "The coupon is not applied.")

            # Apply the coupon again
            WebsiteSaleController.pricelist(promo=self.coupon.code)
            WebsiteSaleController.cart()
            error_msg = request.session.get('error_promo_code')

            # Check that the coupon stay applied
            self.assertEqual(bool(error_msg), True, "Apply a coupon twice should display an error message")
            self.assertEqual(order.amount_total, 90.0, "Apply a coupon twice shouldn't delete it")

    def test_03_remove_coupon_with_different_taxes_on_products(self):
        """
        Tests the removal of a coupon from an order containing products with various tax rates,
        ensuring that the system correctly handles multiple coupon lines created
        for each unique tax scenario.

        Background:
            An order may include products with different tax implications,
            such as non-taxed products, products with a single tax rate,
            and products with multiple tax rates. When a coupon is applied,
            it creates separate coupon lines for each distinct tax situation
            (non-taxed, individual taxes, and combinations of taxes).
            This test verifies that the coupon deletion process accurately removes
            all associated coupon lines, maintaining the financial accuracy of the order.

        Steps:
            1. Create an order with products subject to different tax scenarios:
            - Non-taxed product 'Product A'
            - Product 'Product B' with Tax A
            - Product 'Product C' with Tax B
            - Product 'Product D' subject to both Tax A and Tax B
            2. Apply a coupon, which generates four distinct coupon lines
                to reflect each tax scenario.
            3. Remove the coupon and verify that all coupon lines are removed and
                that no coupons remain applied.
        """
        # Create 2 Taxes
        tax_a = self.env['account.tax'].create({
            'name': 'Tax A',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 15,
        })
        tax_b = tax_a.copy({'name': 'Tax B'})

        # Create 4 products subject to different tax
        products_data = [
            ('Product A', []),
            ('Product B', [tax_a.id]),
            ('Product C', [tax_b.id]),
            ('Product D', [tax_a.id, tax_b.id]),
        ]

        products = self.env['product.product'].create(
            [{
                'name': name,
                'list_price': 100,
                'sale_ok': True,
                'taxes_id': [Command.set(taxes_id)],
            } for name, taxes_id in products_data]
        )

        order = self.empty_order
        order.write({
            'website_id': self.env['website'].browse(1),
            'order_line': [Command.create({'product_id': product.id}) for product in products],
        })

        msg = "There should only be 4 lines for the 4 products."
        self.assertEqual(len(order.order_line), 4, msg=msg)

        # 2. Apply the coupon
        self._apply_promo_code(order, self.coupon.code)

        msg = (
            "4 additional lines should have been added to the sale orders"
            "after application of the coupon for each separate tax situation."
        )
        self.assertEqual(len(order.order_line), 8, msg=msg)

        # 3. Remove the coupon
        coupon_line = order.website_order_line.filtered(
            lambda line: line.coupon_id and line.coupon_id.id == self.coupon.id
        )
        order._cart_update(
            line_id=None,
            product_id=coupon_line.product_id.id,
            add_qty=None,
            set_qty=0,
        )

        msg = "All coupon lines should have been removed from the order."
        self.assertEqual(len(order.applied_coupon_ids), 0, msg=msg)
        self.assertEqual(len(order.order_line), 4, msg=msg)
