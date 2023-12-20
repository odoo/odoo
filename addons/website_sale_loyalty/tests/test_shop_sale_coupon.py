# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged, TransactionCase
from odoo.addons.sale.tests.test_sale_product_attribute_value_config import TestSaleProductAttributeValueCommon


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
