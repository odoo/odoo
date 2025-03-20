# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo import Command
from odoo.tests import tagged

from odoo.addons.pos_loyalty.tests.test_common import TestPoSLoyaltyDataHttpCommon
from odoo.addons.point_of_sale.tests.common_setup_methods import setup_product_combo_items


@tagged("post_install", "-at_install")
class TestUi(TestPoSLoyaltyDataHttpCommon):
    def test_pos_loyalty_tour_basic(self):
        """PoS Loyalty Basic Tour"""
        ##
        # Tour Part 1
        # This part will generate coupons for `auto_promo_program_next`
        # that will be used in the second part of the tour.
        #
        self.start_pos_tour("PosLoyaltyTour1")

        # check coupon usage
        self.assertEqual(self.coupon1.points, 0, 'The coupon should have consumed its points.')
        self.assertEqual(self.coupon2.points, 4.5, 'The coupon was used but never validated.')
        # check pos_order_count in each program
        self.assertEqual(self.auto_promo_program_current.pos_order_count, 3)
        self.assertEqual(self.auto_promo_program_next.pos_order_count, 0)
        self.assertEqual(self.code_promo_program.pos_order_count, 1)
        self.assertEqual(self.coupon_program.pos_order_count, 1)
        # check number of generated coupons
        self.assertEqual(len(self.auto_promo_program_next.coupon_ids), 5)
        # check number of orders in the session
        pos_session = self.pos_config.current_session_id
        self.assertEqual(
            len(pos_session.order_ids), 5, msg="5 orders were made in tour part1."
        )

        ##
        # Tour Part 2
        # The coupons generated in the first part will be used in this tour.
        #

        # Manually set the code for some `auto_promo_program_next` coupons
        # to be able to use them in defining the part2 tour.
        (
            promo_coupon1,
            promo_coupon2,
            promo_coupon3,
            promo_coupon4,
            *_,
        ) = self.auto_promo_program_next.coupon_ids
        promo_coupon1.write({"code": "123456"})
        promo_coupon2.write({"code": "345678"})
        promo_coupon3.write({"code": "567890"})
        promo_coupon4.write({"code": "098765"})

        self.coupon2.points = 6
        self.coupon3.points = 3

        # use here the generated coupon
        self.start_pos_tour("PosLoyaltyTour2")
        # check pos_order_count in each program
        self.assertEqual(self.auto_promo_program_current.pos_order_count, 6)
        self.assertEqual(self.auto_promo_program_next.pos_order_count, 2)
        self.assertEqual(self.code_promo_program.pos_order_count, 2)
        self.assertEqual(self.coupon_program.pos_order_count, 3)

    def test_loyalty_validity_dates_and_use(self):
        # Tests date validity and max usage for an automatic program.
        self.auto_promo_program_current.write({
            'date_to': date.today() - timedelta(days=2),
            'limit_usage': True,
            'max_usage': 1,
        })

        # First tour check that the promotion is not applied
        self.start_pos_tour("PosLoyaltyValidity1")
        self.auto_promo_program_current.write({
            'date_to': date.today() + timedelta(days=2),
        })

        # Second tour that does 2 orders, the first should have the rewards, the second should not
        self.start_pos_tour("PosLoyaltyValidity2")

    def test_loyalty_free_product_rewards(self):
        free_product = self.env['loyalty.program'].create({
            'name': 'Buy 2 Take 1 Awesome Item',  # Old desk orgganizer
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_ids': self.product_awesome_item.product_variant_id.ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 0,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.product_awesome_item.product_variant_id.id,
                'reward_product_qty': 1,
                'required_points': 2,
            })],
        })
        free_other_product = self.env['loyalty.program'].create({
            'name': 'Buy 3 Awesome Thing, Take 1 Quality Thing',  # magnetic -> whiteboard pen
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_ids': self.product_awesome_thing.product_variant_ids.ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 0,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.product_quality_thing.product_variant_id.id,
                'reward_product_qty': 1,
                'required_points': 3,
            })],
        })
        free_multi_product = self.env['loyalty.program'].create({
            'name': '2 items of Quality, get Awesome free',  # shelves -> deskpad / monitor
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_ids': (self.product_quality_thing.product_variant_id | self.product_quality_article.product_variant_id).ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 0,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_tag_id': self.env['product.tag'].create({
                    'name': 'reward_product_tag',
                    'product_product_ids': (self.product_awesome_item.product_variant_id | self.product_awesome_article.product_variant_id).ids,
                }).id,
                'reward_product_qty': 1,
                'required_points': 2,
            })],
        })

        self.disable_test_program()
        self.start_pos_tour("PosLoyaltyFreeProductTour")

        # Keep the tour to generate 4 orders for the free_product and free_other_product programs.
        # 2 of them don't use a program.
        # 1 uses free_product.
        # 1 uses free_other_product.
        # This is to take into account the fact that during tours, we can't test the "non-occurence" of something.
        # It would be nice to have a check like: Validate that a reward is "not" there.
        self.assertEqual(free_product.pos_order_count, 1)
        self.assertEqual(free_other_product.pos_order_count, 2)

        # There is the 5th order that tests multi_product reward.
        # It attempted to add one reward product, removed it, then add the second.
        # The second reward was synced with the order.
        self.assertEqual(free_multi_product.pos_order_count, 1)

    def test_loyalty_free_product_loyalty_program(self):
        # In this program, each whiteboard pen gives 1 point.
        # 4 points can be used to get a free whiteboard pen.
        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Buy 4 Awesome Item, Take 1 Awesome Item',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [(0, 0, {
                'product_ids': self.product_awesome_item.product_variant_id.ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.product_awesome_item.product_variant_id.id,
                'reward_product_qty': 1,
                'required_points': 4,
            })],
        })

        self.disable_test_program()
        self.start_pos_tour("PosLoyaltyLoyaltyProgram1")
        partner_one_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == self.partner_one.id)
        self.assertEqual(loyalty_program.pos_order_count, 1)
        self.assertAlmostEqual(partner_one_card.points, 4)

        # Part 2
        self.start_pos_tour("PosLoyaltyLoyaltyProgram2")
        self.assertEqual(loyalty_program.pos_order_count, 2, msg='Only 2 orders should have reward lines.')
        self.assertAlmostEqual(partner_one_card.points, 1)

        partner_two_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == self.partner_two.id)
        partner_three_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == self.partner_three.id)

        self.assertAlmostEqual(partner_two_card.points, 3, msg='Reference: Order3_BBB')
        self.assertAlmostEqual(partner_three_card.points, 4, msg='Reference: Order2_CCC')
        reward_orderline = self.pos_config.current_session_id.order_ids[-1].lines.filtered(lambda line: line.is_reward_line)
        self.assertEqual(len(reward_orderline.ids), 0, msg='Reference: Order4_no_reward. Last order should have no reward line.')

        # Part 3
        self.env['loyalty.card'].create({
            'partner_id': self.partner_four.id,
            'program_id': loyalty_program.id,
            'points': 100,
        })
        self.start_pos_tour("PosLoyaltyChangeRewardQty")

    def test_loyalty_free_product_zero_sale_price_loyalty_program(self):
        # In this program, each $ spent gives 1 point.
        # 5 points can be used to get a free whiteboard pen.
        # and the whiteboard pen sale price is zero
        self.product_awesome_item.write({'list_price': 1})
        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Loyalty Program',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [(0, 0, {
                'reward_point_amount': 1,
                'reward_point_mode': 'money',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.product_quality_item.product_variant_id.id,
                'reward_product_qty': 1,
                'required_points': 5,
            })],
        })

        self.disable_test_program()
        self.start_pos_tour("PosLoyaltyLoyaltyProgram3")
        partner_one_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == self.partner_one.id)
        self.assertEqual(loyalty_program.pos_order_count, 1)
        self.assertAlmostEqual(partner_one_card.points, 0.0)

    def test_pos_loyalty_tour_max_amount(self):
        self.product_awesome_item.write({
            'taxes_id': [(4, self.tax_05_include.id)],
        })
        self.product_awesome_thing.write({
            'taxes_id': [(4, self.tax_10_include.id)],
        })
        self.disable_test_program()
        self.env['loyalty.program'].create({
            'name': 'Promo Program - Max Amount',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_domain': '[["product_variant_ids.name", "ilike", "Awesome"]]',
                'reward_point_mode': 'unit',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_product_ids': self.product_awesome_thing.product_variant_ids.ids,
                'required_points': 1,
                'discount': 100,
                'discount_mode': 'percent',
                'discount_applicability': 'specific',
                'discount_max_amount': 40,
            })],
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.start_pos_tour("PosLoyaltyTour3")

    def test_gift_card_program(self):
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        self.disable_test_program()
        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']
        gift_card_program.pos_report_print_id = self.env.ref('loyalty.report_gift_card')

        self.start_pos_tour("GiftCardProgramTour1")
        self.assertEqual(len(gift_card_program.coupon_ids), 1)
        gift_card_program.coupon_ids.code = '044123456'

        self.start_pos_tour("GiftCardProgramTour2")
        self.assertEqual(gift_card_program.coupon_ids.points, 0.0)

    def test_ewallet_program(self):
        """
        Test for ewallet program.
        - Collect points in EWalletProgramTour1.
        - Use points in EWalletProgramTour2.
        """
        # But activate the ewallet_product_50 because it's shared among new ewallet programs.
        self.disable_test_program()
        self.env.ref('loyalty.ewallet_product_50').product_tmpl_id.write({'active': True})
        ewallet_program = self.create_programs([('arbitrary_name', 'ewallet')])['arbitrary_name']

        # Run the tour to topup ewallets.
        self.start_pos_tour("EWalletProgramTour1")
        ewallet_one = self.env['loyalty.card'].search([('partner_id', '=', self.partner_one.id), ('program_id', '=', ewallet_program.id)])
        self.assertEqual(len(ewallet_one), 1)
        self.assertAlmostEqual(ewallet_one.points, 50, places=2)

        ewallet_two = self.env['loyalty.card'].search([('partner_id', '=', self.partner_two.id), ('program_id', '=', ewallet_program.id)])
        self.assertEqual(len(ewallet_two), 1)
        self.assertAlmostEqual(ewallet_two.points, 10, places=2)

        self.start_pos_tour("EWalletProgramTour2")
        self.assertAlmostEqual(ewallet_one.points, 0, places=2)
        self.assertAlmostEqual(ewallet_two.points, 20, places=2)

    def test_multiple_gift_wallet_programs(self):
        """
        Test for multiple gift_card and ewallet programs.
        """
        self.disable_test_program()
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        self.env.ref('loyalty.ewallet_product_50').product_tmpl_id.write({'active': True})
        programs = self.create_programs([
            ('gift_card_1', 'gift_card'),
            ('gift_card_2', 'gift_card'),
            ('ewallet_1', 'ewallet'),
            ('ewallet_2', 'ewallet')
        ])
        programs['gift_card_1'].pos_report_print_id = self.env.ref('loyalty.report_gift_card')
        programs['gift_card_2'].pos_report_print_id = self.env.ref('loyalty.report_gift_card')

        self.start_pos_tour("MultipleGiftWalletProgramsTour")
        self.assertEqual(len(programs['gift_card_1'].coupon_ids), 1)
        self.assertAlmostEqual(programs['gift_card_1'].coupon_ids.points, 10)
        self.assertEqual(len(programs['gift_card_2'].coupon_ids), 1)
        self.assertAlmostEqual(programs['gift_card_2'].coupon_ids.points, 20)

        ewallet_1_aaa = self.env['loyalty.card'].search([('partner_id', '=', self.partner_one.id), ('program_id', '=', programs['ewallet_1'].id)])
        self.assertEqual(len(ewallet_1_aaa), 1)
        self.assertAlmostEqual(ewallet_1_aaa.points, 18, places=2)
        ewallet_2_aaa = self.env['loyalty.card'].search([('partner_id', '=', self.partner_one.id), ('program_id', '=', programs['ewallet_2'].id)])
        self.assertEqual(len(ewallet_2_aaa), 1)
        self.assertAlmostEqual(ewallet_2_aaa.points, 40, places=2)
        ewallet_1_bbb = self.env['loyalty.card'].search([('partner_id', '=', self.partner_two.id), ('program_id', '=', programs['ewallet_1'].id)])
        self.assertEqual(len(ewallet_1_bbb), 1)
        self.assertAlmostEqual(ewallet_1_bbb.points, 50, places=2)
        ewallet_2_bbb = self.env['loyalty.card'].search([('partner_id', '=', self.partner_two.id), ('program_id', '=', programs['ewallet_2'].id)])
        self.assertEqual(len(ewallet_2_bbb), 1)
        self.assertAlmostEqual(ewallet_2_bbb.points, 0, places=2)

    def test_coupon_change_pricelist(self):
        self.disable_test_program()
        self.product_awesome_item.write({
            'taxes_id': [(4, self.tax_10_include.id)]
        })
        pricelist = self.env["product.pricelist"].create({
            "name": "Test multi-currency",
            "currency_id": self.env.ref("base.USD").id,
            "item_ids": [
                (0, 0, {
                    "base": "standard_price",
                    "product_id": self.product_awesome_article.product_variant_id.id,
                    "compute_price": "percentage",
                    "percent_price": 50,
                }),
                (0, 0, {
                    "base": "standard_price",
                    "product_id": self.product_awesome_item.product_variant_id.id,
                    "compute_price": "percentage",
                    "percent_price": 50,
                })
            ]
        })
        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Coupon Program - Pricelist',
            'program_type': 'coupons',
            'trigger': 'with_code',
            'applies_on': 'current',
            'pos_ok': True,
            'pos_config_ids': [(4, self.pos_config.id)],
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'order',
                'reward_point_amount': 1,
                'minimum_amount': 0,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'required_points': 1,
                'discount': 100,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        })

        self.env["loyalty.generate.wizard"].with_context(
            {"active_id": loyalty_program.id}
        ).create({"coupon_qty": 1, 'points_granted': 4.5}).generate_coupons()
        self.coupon1 = loyalty_program.coupon_ids
        self.coupon1.write({"code": "abcda"})
        self.pos_config.write({
            'use_pricelist': True,
            'available_pricelist_ids': [(4, pricelist.id), (4, self.pos_config.pricelist_id.id)],
            'pricelist_id': pricelist.id,
        })
        self.start_pos_tour("PosLoyaltyTour4")

    def test_promotion_program_with_global_discount(self):
        if not self.env["ir.module.module"].search([("name", "=", "pos_discount"), ("state", "=", "installed")]):
            self.skipTest("pos_discount module is required for this test")

        self.disable_test_program()
        tax = self.env["account.tax"].create({
            "name": "C01 Tax",
            "amount": "0.00",
        })
        self.discount_product = self.env["product.product"].create(
            {
                "name": "Discount Product",
                "type": "service",
                "list_price": 0,
                "available_in_pos": True,
                "taxes_id": [(6, 0, [tax.id])],
            }
        )
        self.pos_config.write({
            'module_pos_discount' : True,
            'discount_product_id': self.discount_product.id,
            'discount_pc': 20,
        })
        self.loyalty_program = self.env['loyalty.program'].create({
            'name': 'Coupon Program - Pricelist',
            'program_type': 'coupons',
            'trigger': 'with_code',
            'applies_on': 'current',
            'pos_ok': True,
            'pos_config_ids': [(4, self.pos_config.id)],
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'order',
                'reward_point_amount': 1,
                'minimum_amount': 0,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'required_points': 1,
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        })
        self.start_pos_tour("PosCouponTour5")

    def test_loyalty_program_using_same_product(self):
        """
        - Create a loyalty program giving free product A for 30 points
        - Trigger the condition of the program using the same product A
        """
        self.disable_test_program()
        self.loyalty_program = self.env['loyalty.program'].create({
            'name': 'Loyalty Program Test',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'pos_ok': True,
            'pos_config_ids': [(4, self.pos_config.id)],
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'order',
                'reward_point_amount': 10,
                'minimum_amount': 5,
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'required_points': 30,
                'reward_product_id': self.product_awesome_item.product_variant_id.id,
                'reward_product_qty': 1,
            })],
        })

        self.env['loyalty.card'].create({
            'partner_id': self.partner_one.id,
            'program_id': self.loyalty_program.id,
            'points': 30,
        })
        self.start_pos_tour("PosLoyaltyFreeProductTour2")

    def test_refund_with_gift_card(self):
        """When adding a gift card when there is a refund in the order, the amount
        of the gift card is set to the amount of the refund"""
        self.disable_test_program()
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        program = self.create_programs([('arbitrary_name', 'gift_card')])
        program['arbitrary_name'].pos_report_print_id = self.env.ref('loyalty.report_gift_card')
        self.start_pos_tour("GiftCardWithRefundtTour")

    def test_loyalty_program_specific_product(self):
        #create a loyalty program with a rules of minimum 2 qty that applies on produt A and B and reward 5 points. The reward is 10$ per order in exchange of 2 points on product A and B
        self.disable_test_program()
        item_variant = self.product_awesome_item.product_variant_id
        article_variant = self.product_awesome_article.product_variant_id
        self.loyalty_program = self.env['loyalty.program'].create({
            'name': 'Loyalty Program Test',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'pos_ok': True,
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'order',
                'reward_point_amount': 10,
                'minimum_qty': 2,
                'product_ids': [(6, 0, [item_variant.id, article_variant.id])],
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'per_order',
                'required_points': 2,
                'discount': 10,
                'discount_applicability': 'specific',
                'discount_product_ids': (item_variant | article_variant).ids,
            }), (0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'per_order',
                'required_points': 5,
                'discount': 30,
                'discount_applicability': 'specific',
                'discount_product_ids': (item_variant | article_variant).ids,
            })],
        })
        self.start_pos_tour("PosLoyaltySpecificDiscountTour")

    def test_discount_specific_product_with_free_product(self):
        self.disable_test_program()
        item_variant = self.product_awesome_item.product_variant_id
        article_variant = self.product_awesome_article.product_variant_id
        thing_variant = self.product_awesome_thing.product_variant_id
        self.env['loyalty.program'].create({
            'name': 'Discount 10%',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'order',
                'reward_point_amount': 1,
                'minimum_amount': 10,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_product_ids': thing_variant.ids,
                'required_points': 1,
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'specific',
            })],
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.env['loyalty.program'].create({
            'name': 'Buy product_a Take product_b',
            'program_type': 'buy_x_get_y',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_ids': item_variant.ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': article_variant.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.start_pos_tour('PosLoyaltySpecificDiscountWithFreeProductTour')

    def test_2_discounts_specific_global(self):
        self.disable_test_program()
        product_categ = self.env['product.category'].create({
            'name': 'Category Items',
        })
        self.product_awesome_item.categ_id = product_categ.id
        self.env['loyalty.program'].create({
            'name': 'Discount 10%',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'order',
                'reward_point_amount': 1,
                'minimum_amount': 1,
                'minimum_qty': 5,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'required_points': 1,
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.env['loyalty.program'].create({
            'name': 'Discount on category',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'order',
                'reward_point_amount': 1,
                'minimum_amount': 1,
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'required_points': 1,
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'specific',
                'discount_product_category_id': product_categ.id,
            })],
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.start_pos_tour("PosLoyalty2DiscountsSpecificGlobal")

    def test_coupon_program_without_rules(self):
        self.disable_test_program()
        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Coupon Program without rules',
            'program_type': 'coupons',
            'trigger': 'with_code',
            'applies_on': 'current',
            'pos_ok': True,
            'rule_ids': [],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        })

        self.env["loyalty.generate.wizard"].with_context(
            {"active_id": loyalty_program.id}
        ).create({"coupon_qty": 1, 'points_granted': 1}).generate_coupons()
        self.coupon1 = loyalty_program.coupon_ids
        self.coupon1.write({"code": "abcda"})
        self.start_pos_tour("PosLoyaltyTour7")

    def test_discount_with_reward_product_domain(self):
        self.disable_test_program()
        product_category_base = self.env.ref('product.product_category_goods')
        product_category_office = self.env['product.category'].create({
            'name': 'Office furnitures',
            'parent_id': product_category_base.id
        })
        self.product_awesome_item.categ_id = product_category_base.id
        self.product_awesome_thing.categ_id = product_category_office.id
        self.env['loyalty.program'].create({
            'name': 'Discount on Specific Products',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'order',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'required_points': 1,
                'discount': 50,
                'discount_mode': 'percent',
                'discount_applicability': 'specific',
                'discount_product_domain': '["&", ("categ_id", "ilike", "office"), ("name", "ilike", "Product B")]',
            })],
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.start_pos_tour("PosLoyaltySpecificDiscountWithRewardProductDomainTour")

    def test_promotion_program_with_loyalty_program(self):
        """
        - Create a promotion with a discount of 10%
        - Create a loyalty program with a fixed discount of 10€
        - Apply both programs to the order
        - Check that no "infinity" discount is applied
        """
        self.disable_test_program()
        self.promo_program = self.env['loyalty.program'].create({
            'name': 'Promo Program',
            'program_type': 'promotion',
            'pos_ok': True,
            'rule_ids': [(0, 0, {
                'minimum_amount': 0,
                'minimum_qty': 0
                })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        })
        self.discount_product = self.env["product.product"].create({
            "name": "Discount Product",
            "type": "service",
            "list_price": 0,
            "available_in_pos": True,
            "taxes_id": False,
        })
        self.loyalty_program = self.env["loyalty.program"].create({
            "name": "Loyalty Program",
            "program_type": "loyalty",
            "pos_ok": True,
            "rule_ids": [(0, 0, {
                "minimum_amount": 1,
                "minimum_qty": 1,
                "reward_point_mode": "order",
                "reward_point_amount": 500,
            })],
            "reward_ids": [(0, 0, {
                "required_points": 500,
                "reward_type": "discount",
                "discount": "10",
                "discount_mode": "per_order",
            })],
        })
        self.env['loyalty.card'].create({
            'partner_id': self.partner_one.id,
            'program_id': self.loyalty_program.id,
            'points': 500,
        })
        self.start_pos_tour("PosLoyaltyPromotion")

    def test_promo_with_free_product(self):
        self.env['loyalty.program'].search([]).write({'active': False})
        self.product_awesome_item.write({
            'taxes_id': [(4, self.tax_15_include.id)]
        })
        self.free_product = self.env['loyalty.program'].create({
            'name': 'Free Product A',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'unit',
                'minimum_qty': 0,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.product_awesome_item.product_variant_id.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        })
        self.env['loyalty.program'].create({
            'name': 'Discount 50%',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'order',
                'reward_point_amount': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'required_points': 1,
                'discount': 50,
                'discount_mode': 'percent',
            })],
        })
        self.start_pos_tour("PosLoyaltyTour8")

    def test_discount_specific_products(self):
        self.disable_test_program()
        product_category_base = self.env.ref('product.product_category_goods')
        product_category_office = self.env['product.category'].create({
            'name': 'Office furnitures',
            'parent_id': product_category_base.id
        })
        self.product_awesome_item.categ_id = product_category_base.id
        self.product_awesome_thing.categ_id = product_category_office.id
        self.env['loyalty.program'].create({
            'name': 'Discount on Specific Products',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'order',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'required_points': 1,
                'discount': 50,
                'discount_mode': 'percent',
                'discount_applicability': 'specific',
                'discount_product_category_id': product_category_office.id,
            })],
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.start_pos_tour("PosLoyaltySpecificDiscountCategoryTour")

    def test_promo_with_different_taxes(self):
        self.env['loyalty.program'].search([]).write({'active': False})
        self.product_awesome_item.write({
            'taxes_id': [(4, self.tax_10_include.id)]
        })
        self.free_product = self.env['loyalty.program'].create({
            'name': 'Free Product A',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'money',
                'reward_point_amount': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'required_points': 5,
                'discount_mode': 'per_order',
                'discount': 5,
            })],
        })
        self.start_pos_tour("PosLoyaltyTour9")

    def test_ewallet_expiration_date(self):
        self.disable_test_program()
        # But activate the ewallet_product_50 because it's shared among new ewallet programs.
        self.env.ref('loyalty.ewallet_product_50').product_tmpl_id.write({'active': True})
        ewallet_program = self.create_programs([('arbitrary_name', 'ewallet')])['arbitrary_name']
        self.env['loyalty.card'].create({
            'partner_id': self.partner_one.id,
            'program_id': ewallet_program.id,
            'points': 50,
            'expiration_date': date(2020, 1, 1),
        })
        self.start_pos_tour("ExpiredEWalletProgramTour")

    def test_loyalty_program_with_tagged_free_product(self):
        self.disable_test_program()
        free_product_tag = self.env['product.tag'].create({'name': 'Free Product'})
        self.product_awesome_item.write({
            'list_price': 1,
            'product_tag_ids': [(4, free_product_tag.id)]
        })
        self.product_awesome_article.write({
            'list_price': 1,
            'product_tag_ids': [(4, free_product_tag.id)]
        })
        self.product_awesome_thing.write({
            'list_price': 1,
        })
        self.env['loyalty.program'].create({
            'name': 'Free Product with Tag',
            'program_type': 'loyalty',
            'applies_on': 'both',
            'trigger': 'auto',
            'portal_visible': True,
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'unit',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_tag_id': free_product_tag.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        })
        self.start_pos_tour("PosLoyaltyTour10")

    def test_loyalty_program_with_next_order_coupon_free_product(self):
        self.env['loyalty.program'].search([]).write({'active': False})
        self.product_awesome_item.write({
            'list_price': 1,
        })
        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Next Order Coupon Program',
            'program_type': 'next_order_coupons',
            'applies_on': 'future',
            'trigger': 'auto',
            'portal_visible': True,
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'unit',
                'minimum_amount': 100,
                'minimum_qty': 0,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.product_awesome_item.product_variant_id.id,
                'reward_product_qty': 1,
                'required_points': 1,
            })],
        })
        self.start_pos_tour("PosLoyaltyTour11.1")

        coupon = loyalty_program.coupon_ids
        self.assertEqual(len(coupon), 1, "Coupon not generated")
        self.assertEqual(coupon.points, 3, "Coupon not generated with correct points")
        coupon.write({"code": "123456"})
        self.start_pos_tour("PosLoyaltyTour11.2")
        self.assertEqual(coupon.points, 0, "Coupon not used")

    def test_loyalty_program_with_tagged_buy_x_get_y(self):
        self.disable_test_program()
        free_product_tag = self.env['product.tag'].create({'name': 'Free Product'})
        self.product_awesome_item.write({
            'list_price': 1,
            'product_tag_ids': [(4, free_product_tag.id)],
        })
        self.product_awesome_article.write({
            'list_price': 5,
            'product_tag_ids': [(4, free_product_tag.id)],
        })
        self.env['loyalty.program'].create({
            'name': 'Buy X get Y with Tag',
            'program_type': 'buy_x_get_y',
            'applies_on': 'current',
            'trigger': 'auto',
            'portal_visible': True,
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'unit',
                'minimum_qty': 1,
                'product_tag_id': free_product_tag.id,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_tag_id': free_product_tag.id,
                'reward_product_qty': 1,
                'required_points': 2,
            })],
        })
        self.start_pos_tour("PosLoyaltyTour12")

    def test_promotion_with_min_amount_and_specific_product_rule(self):
        """
        Test that the discount is applied iff the min amount is reached for the specified product.
        """
        self.env['loyalty.program'].search([]).action_archive()
        self.env['loyalty.program'].create({
            'name': "Discount on specific products",
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'minimum_amount': 40,
                'product_ids': [(4, self.product_awesome_item.product_variant_id.id)],
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'specific',
                'discount_product_ids': [(4, self.product_awesome_item.product_variant_id.id)],
            })],
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.start_pos_tour('PosLoyaltyMinAmountAndSpecificProductTour')

    def test_gift_card_price_no_tax(self):
        """
        Test that the gift card has the right price (especially does not include taxes)
        """
        self.disable_test_program()
        # But activate the gift_card_product_50 because it's shared among new gift card programs.
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']
        gift_card_program.pos_report_print_id = self.env.ref('loyalty.report_gift_card')
        gift_card_program.payment_program_discount_product_id.taxes_id = self.env['account.tax'].create({
            'name': "Test Tax",
            "amount_type": "percent",
            'amount': 15,
        })

        # Generate 1$ gift card.
        self.env["loyalty.generate.wizard"].with_context(
            {"active_id": gift_card_program.id}
        ).create({"coupon_qty": 1, 'points_granted': 1}).generate_coupons()
        gift_card_program.coupon_ids.code = '043123456'
        self.start_pos_tour("GiftCardProgramPriceNoTaxTour")

    def test_physical_gift_card_sale(self):
        """
        Test that the manual gift card sold has been correctly generated.
        """
        self.disable_test_program()
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']
        gift_card_program.pos_report_print_id = self.env.ref('loyalty.report_gift_card')
        self.start_pos_tour("PhysicalGiftCardProgramSaleTour")

        expected_coupons = {
            "test-card-0000": 125,
            "new-card-0001": 250,
        }

        # Check if the expected coupon codes are present
        coupon_codes = {coupon.code for coupon in gift_card_program.coupon_ids}
        for expected_code in expected_coupons:
            self.assertIn(expected_code, coupon_codes, f"Expected coupon code '{expected_code}' not found")

        # Check if the expected number of coupons are generated
        self.assertEqual(len(gift_card_program.coupon_ids), 3, "Three coupons should be generated")

        # Check if the coupon codes and points match the expected values
        for coupon in gift_card_program.coupon_ids:
            if coupon.code in expected_coupons:
                self.assertEqual(coupon.points, expected_coupons[coupon.code], f"Coupon points for '{coupon.code}' should be {expected_coupons[coupon.code]}")
            else:
                # This is the auto-generated coupon with 50 points
                self.assertEqual(coupon.points, 100, "Auto-generated coupon should have 100 points")

        # Check if the total points of all coupons match the expected value
        total_points = sum(coupon.points for coupon in gift_card_program.coupon_ids)
        self.assertEqual(total_points, 475, "Total points should be 425")

    def test_dont_grant_points_reward_order_lines(self):
        """
        Make sure that points granted per unit are only given
        for the product -non reward- lines!
        """
        self.disable_test_program()
        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Loyalty Program',
            'program_type': 'loyalty',
            'applies_on': 'both',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'reward_point_amount': 1,
                'reward_point_mode': 'unit',
                'minimum_qty': 2,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 100,
                'discount_mode': 'percent',
                'discount_applicability': 'cheapest',
                'required_points': 2,
            })],
        })
        self.start_pos_tour("PosLoyaltyDontGrantPointsForRewardOrderLines")
        loyalty_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == self.partner_one.id)
        self.assertTrue(loyalty_card)
        self.assertFalse(loyalty_card.points)

    def test_points_awarded_global_discount_code_no_domain_program(self):
        """
        Check the calculation for points awarded when there is a global discount applied and the
        loyalty program applies on all product (no domain).
        """
        self.disable_test_program()
        self.auto_promo_program_next.applies_on = 'current'
        self.auto_promo_program_next.active = True
        loyalty_program = self.create_programs([('Loyalty P', 'loyalty')])['Loyalty P']
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_one.id,
            'points': 0,
        })
        self.start_pos_tour("PosLoyaltyPointsGlobalDiscountProgramNoDomain")
        self.assertEqual(loyalty_card.points, 90)

    def test_points_awarded_discount_code_no_domain_program(self):
        """
        Check the calculation for points awarded when there is a discount coupon applied and the
        loyalty program applies on all product (no domain).
        """
        self.disable_test_program()
        self.product_awesome_article.write({'list_price': 50})
        loyalty_program = self.create_programs([('Loyalty P', 'loyalty')])['Loyalty P']
        loyalty_program.pos_config_ids = [(4, self.pos_config.id)]
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_one.id,
            'points': 0,
        })

        self.code_promo_program.active = True
        self.code_promo_program.reward_ids.write({
            'description': '10% on your order',
            'discount': 10,
            'discount_applicability': 'order',
            'discount_product_ids': None
        })

        self.start_pos_tour("PosLoyaltyPointsDiscountNoDomainProgramNoDomain")
        self.assertEqual(loyalty_card.points, 135)

    def test_points_awarded_general_discount_code_specific_domain_program(self):
        """
        Check the calculation for points awarded when there is a discount coupon applied and the
        loyalty program applies on a sepcific domain. The discount code has no domain. The product
        related to that discount is not in the domain of the loyalty program.
        Expected behavior: The discount is not included in the computation of points
        """
        self.disable_test_program()
        product_category_food = self.env['product.category'].create({
            'name': 'Food',
        })
        self.product_awesome_item.write({
            'categ_id': product_category_food.id,
        })
        self.product_awesome_article.write({
            'list_price': 50,
        })
        loyalty_program = self.create_programs([('Loyalty P', 'loyalty')])['Loyalty P']
        loyalty_program.rule_ids.product_category_id = product_category_food.id
        loyalty_program.pos_config_ids = [(4, self.pos_config.id)]
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_one.id,
            'points': 0,
        })
        self.code_promo_program.active = True
        self.code_promo_program.reward_ids.write(
            {
                'description': '10% on your order',
                'discount': 10,
                'discount_applicability': 'order',
                'discount_product_ids': None
            })

        self.start_pos_tour("PosLoyaltyPointsDiscountNoDomainProgramDomain")
        self.assertEqual(loyalty_card.points, 100)

    def test_points_awarded_specific_discount_code_specific_domain_program(self):
        """
        Check the calculation for points awarded when there is a discount coupon applied and the
        loyalty program applies on a sepcific domain. The discount code has the same domain as the
        loyalty program. The product related to that discount code is set up to be included in the
        domain of the loyalty program.
        """
        self.disable_test_program()
        product_category_food = self.env['product.category'].create({
            'name': 'Food',
        })
        self.product_awesome_item.write({
            'categ_id': product_category_food.id,
        })
        self.product_awesome_article.write({
            'list_price': 50,
        })
        loyalty_program = self.create_programs([('Loyalty P', 'loyalty')])['Loyalty P']
        loyalty_program.rule_ids.product_category_id = product_category_food.id
        loyalty_program.pos_config_ids = [(4, self.pos_config.id)]
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_one.id,
            'points': 0,
        })

        self.code_promo_program.active = True
        self.code_promo_program.reward_ids.write(
            {
                'description': '10% on your order',
                'discount': 10,
                'discount_product_ids': None,
                'discount_product_category_id': product_category_food.id,
            })

        discount_product = self.env['product.product'].search([('id', '=', self.code_promo_program.reward_ids.discount_line_product_id.id)])
        discount_product.categ_id = product_category_food.id
        discount_product.name = "10% on food"
        discount_product.available_in_pos = True

        self.start_pos_tour("PosLoyaltyPointsDiscountWithDomainProgramDomain")
        self.assertEqual(loyalty_card.points, 90)

    def test_points_awarded_ewallet(self):
        """
        Check the calculation for point awarded when using ewallet
        """
        self.disable_test_program()
        product_category_food = self.env['product.category'].create({
            'name': 'Food',
        })
        self.product_awesome_item.write({
            'categ_id': product_category_food.id,
        })
        loyalty_program = self.create_programs([('Loyalty P', 'loyalty')])['Loyalty P']
        loyalty_program.pos_config_ids = [Command.link(self.pos_config.id)]
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_one.id,
            'points': 0,
        })

        ewallet_program = self.env['loyalty.program'].create({
            'name': 'eWallet Program',
            'program_type': 'ewallet',
            'trigger': 'auto',
            'applies_on': 'future',
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount_mode': 'per_point',
                'discount': 1,
            })],
            'rule_ids': [Command.create({
                'reward_point_amount': '1',
                'reward_point_mode': 'money',
                'product_ids': self.env.ref('loyalty.ewallet_product_50'),
            })],
            'trigger_product_ids': self.env.ref('loyalty.ewallet_product_50'),
        })

        self.env['loyalty.card'].create({
            'program_id': ewallet_program.id,
            'partner_id': self.partner_one.id,
            'points': 10,
        })

        self.pos_config.open_ui()
        self.start_pos_tour("PosLoyaltyPointsEwallet")
        self.assertEqual(loyalty_card.points, 100)

    def test_points_awarded_giftcard(self):
        """
        Check the calculation for point awarded when using a gift card
        """
        self.disable_test_program()
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        gift_card = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']
        gift_card.pos_report_print_id = self.env.ref('loyalty.report_gift_card')
        loyalty_program = self.create_programs([('Loyalty P', 'loyalty')])['Loyalty P']
        loyalty_program.pos_config_ids = [(4, self.pos_config.id)]
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': self.partner_one.id,
            'points': 0,
        })
        self.start_pos_tour("PosLoyaltyPointsGiftcard")
        self.assertEqual(loyalty_card.points, 100)

    def test_archived_reward_products(self):
        """
        Check that a loyalty_reward with no active reward product is not loaded.
        In the case where the reward is based on reward_product_tag_id we also check
        the case where at least one reward is  active.
        """
        self.disable_test_program()
        free_product_tag = self.env['product.tag'].create({'name': 'Free Product'})
        self.product_awesome_article.write({'product_tag_ids': [(4, free_product_tag.id)]})
        self.product_awesome_thing.write({
            'list_price': 1,
            'product_tag_ids': [(4, free_product_tag.id)]
        })
        LoyaltyProgram = self.env['loyalty.program']
        loyalty_program = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])
        loyalty_program_tag = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])
        loyalty_program.reward_ids.write({
            'reward_type': 'product',
            'required_points': 1,
            'reward_product_id': self.product_awesome_article.product_variant_id.id,
        })
        loyalty_program_tag.reward_ids.write({
            'reward_type': 'product',
            'required_points': 1,
            'reward_product_tag_id': free_product_tag.id,
        })
        self.product_awesome_article.active = False
        self.product_awesome_thing.active = False
        self.start_pos_tour("PosLoyaltyArchivedRewardProductsInactive")
        self.product_awesome_thing.active = True
        self.start_pos_tour("PosLoyaltyArchivedRewardProductsActive")

    def test_change_reward_value_with_language(self):
        """
        Verify that the displayed language is not en_US.
        When a user has another language than en_US set,
        he shouldn't have the en_US message displayed but the message of the active language.
        For this test, we shouldn't have the description displayed for selecting the reward in en_US but in en_GB.
        Description in en_US (unexpected): 'A en_US name which should not be displayed'
        Description in en_GB (expected): '$ 2 on your order'
        """

        self.disable_test_program()
        self.env['res.lang']._activate_lang('en_GB')
        env_gb = self.env(context={'lang': 'en_GB'})
        self.pos_user.write({'lang': 'en_GB'})
        loyalty_program = env_gb['loyalty.program'].create({
            'name': 'Loyalty Program',
            'program_type': 'loyalty',
            'applies_on': 'both',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'reward_point_amount': 1,
                'reward_point_mode': 'money',
                'minimum_qty': 0,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 2,
                'discount_mode': 'per_order',
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })
        loyalty_program.reward_ids.update_field_translations('description', {'en_US': 'A en_US name which should not be displayed'})
        self.start_pos_tour("ChangeRewardValueWithLanguage")

    def test_loyalty_reward_product_tag(self):
        """
        We test that a program using product tag to define reward products will
        correctly compute the reward lines.
        """
        self.env['loyalty.program'].search([]).write({'active': False})
        free_product_tag = self.env['product.tag'].create({'name': 'Free Product Tag'})
        self.product_awesome_item.write({
            'product_tag_ids': [(4, free_product_tag.id)],
            'list_price': 2
        })
        self.product_awesome_article.write({
            'product_tag_ids': [(4, free_product_tag.id)],
            'list_price': 5,
        })
        self.env['loyalty.program'].create({
            'name': 'Buy 2 Take 1 Free Product',
            'program_type': 'buy_x_get_y',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_ids': self.product_awesome_thing.product_variant_ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 2,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_tag_id': free_product_tag.id,
                'reward_product_qty': 1,
                'required_points': 2,
            })],
            'pos_config_ids': [Command.link(self.pos_config.id)],
        })
        self.start_pos_tour("PosLoyaltyRewardProductTag")

    def test_gift_card_rewards_using_taxes(self):
        """
        Check the gift card value when the reward has taxes
        """
        self.disable_test_program()
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']
        gift_card_program.pos_report_print_id = self.env.ref('loyalty.report_gift_card')
        gift_card_program.payment_program_discount_product_id.taxes_id = self.tax_15_include
        self.start_pos_tour("PosLoyaltyGiftCardTaxes")
        self.pos_config.current_session_id.close_session_from_ui()

    def test_customer_loyalty_points_displayed(self):
        """
        Verify that the loyalty points of a customer are well displayed.
        This test will only work on big screens because the balance column is not shown when 'ui.isSmall == True'.
        """
        self.env['loyalty.program'].search([]).write({'active': False})
        loyalty_program = self.create_programs([('Loyalty P', 'loyalty')])['Loyalty P']
        self.env['loyalty.card'].create({
            'partner_id': self.partner_one.id,
            'program_id': loyalty_program.id,
            'points': 0
        })
        self.start_pos_tour("CustomerLoyaltyPointsDisplayed")

    def test_cheapest_product_reward_pos_combo(self):
        self.product_awesome_item.write({
            "list_price": 1000,
        })
        self.product_awesome_article.write({
            "list_price": 1,
        })
        setup_product_combo_items(self)
        self.office_combo.write({'lst_price': 50})
        self.env['loyalty.program'].search([]).write({'active': False})
        self.env['loyalty.program'].create({
            'name': 'Auto Promo Program - Cheapest Product',
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'minimum_qty': 2,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'cheapest',
            })]
        })
        self.start_pos_tour('PosComboCheapestRewardProgram')

    def test_specific_product_reward_pos_combo(self):
        setup_product_combo_items(self)
        self.disable_test_program()
        self.office_combo.write({'lst_price': 200})
        self.env['loyalty.program'].create({
            'name': 'Combo Product Promotion',
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'minimum_qty': 1,
                'product_ids': self.office_combo.ids,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'specific',
                'discount_product_ids': self.office_combo.ids,
            })]
        })
        self.start_pos_tour('PosComboSpecificProductProgram')

    def test_apply_reward_on_product_scan(self):
        """
        Test that the rewards are correctly applied if the
        product is scanned rather than added by hand.
        """
        self.disable_test_program()
        self.product_awesome_item.write({
            'barcode': '95412427100283',
        })
        self.env['loyalty.program'].create({
            'name': 'My super program',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'product_ids': [(4, self.product_awesome_item.product_variant_id.id)],
                'reward_point_mode': 'order',
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 50,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.start_pos_tour("PosRewardProductScan")
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        self.start_pos_tour("PosRewardProductScanGS1")

    def test_coupon_pricelist(self):
        self.disable_test_program()
        self.product_awesome_item.write({
            "is_storable": True,
            "list_price": 25,
        })
        pricelist_1 = self.env['product.pricelist'].create({
            "name": "test pricelist 1",
        })
        self.pos_config.write({
            'use_pricelist': True,
            'available_pricelist_ids': [(4, pricelist_1.id)],
            'pricelist_id': pricelist_1.id,
        })
        self.env["loyalty.program"].create({
            "name": "Test Loyalty Program",
            "program_type": "promotion",
            "trigger": "with_code",
            'pos_ok': True,
            "pricelist_ids": [(4, pricelist_1.id)],
            "rule_ids": [
                Command.create({"mode": "with_code", "code": "hellopromo", "minimum_amount": 10}),
            ],
            "reward_ids": [
                Command.create({
                    "reward_type": "discount",
                    "discount": 10,
                    "discount_mode": "percent",
                    "discount_applicability": "order",
                    "required_points": 1,
                }),
            ],
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.start_pos_tour("PosLoyaltyPromocodePricelist")

    def test_gift_card_program_create_with_invoice(self):
        """
        Test for gift card program when pos.config.gift_card_settings == 'create_set'.
        """
        self.disable_test_program()
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']
        gift_card_program.pos_report_print_id = self.env.ref('loyalty.report_gift_card')
        self.start_pos_tour("GiftCardProgramInvoice")
        self.assertEqual(len(gift_card_program.coupon_ids), 1)

    def test_refund_product_part_of_rules(self):
        self.disable_test_program()
        self.env['loyalty.program'].create({
            'name': 'My super program',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'product_ids': [(4, self.product_awesome_item.product_variant_id.id)],
                'reward_point_mode': 'order',
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 50,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.start_pos_tour("RefundRulesProduct")

    def test_cheapest_product_tax_included(self):
        self.disable_test_program()
        self.product_awesome_item.write({
            "list_price": 1,
            "taxes_id": [(6, 0, [self.tax_10_include.id])]
        })
        self.env['loyalty.program'].create({
            'name': 'Auto Promo Program - Cheapest Product',
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {
                'minimum_qty': 2,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'cheapest',
            })]
        })
        self.start_pos_tour('PosCheapestProductTaxInclude')

    def test_next_order_coupon_program_expiration_date(self):
        self.disable_test_program()
        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Next Order Coupon Program',
            'program_type': 'next_order_coupons',
            'applies_on': 'future',
            'trigger': 'auto',
            'portal_visible': True,
            'date_to': date.today() + timedelta(days=2),
            'rule_ids': [(0, 0, {
                'minimum_amount': 10,
                'minimum_qty': 0
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
        })
        self.start_pos_tour("PosLoyaltyNextOrderCouponExpirationDate")
        coupon = loyalty_program.coupon_ids
        self.assertEqual(len(coupon), 1, "Coupon not generated")
        self.assertEqual(coupon.expiration_date, date.today() + timedelta(days=2), "Coupon not generated with correct expiration date")

    def test_ewallet_loyalty_history(self):
        """
        This will test that all transactions made on an ewallet are registered in the loyalty history
        """
        self.disable_test_program()
        self.env.ref('loyalty.ewallet_product_50').product_tmpl_id.write({'active': True})
        ewallet_program = self.create_programs([('arbitrary_name', 'ewallet')])['arbitrary_name']
        self.start_pos_tour("EWalletLoyaltyHistory")
        ewallet_aaa = self.env['loyalty.card'].search([('partner_id', '=', self.partner_one.id), ('program_id', '=', ewallet_program.id)])
        loyalty_history = self.env['loyalty.history'].search([('card_id','=',ewallet_aaa.id)])
        self.assertEqual(loyalty_history.mapped("issued"), [0.0, 50.0])
        self.assertEqual(loyalty_history.mapped("used"), [12.0, 0.0])
