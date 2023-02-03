# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged
from odoo import Command


@tagged("post_install", "-at_install")
class TestUi(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Disable any programs during the test
        cls.env['loyalty.program'].search([]).write({'active': False})

        cls.promo_programs = cls.env["loyalty.program"]

        # code promo program -> discount on specific products
        cls.code_promo_program = cls.env['loyalty.program'].create({
            'name': 'Promo Code Program - Discount on Specific Products',
            'program_type': 'promotion',
            'trigger': 'with_code',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'mode': 'with_code',
                'code': 'promocode',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 50,
                'discount_mode': 'percent',
                'discount_applicability': 'specific',
                'discount_product_ids': cls.whiteboard_pen | cls.magnetic_board | cls.desk_organizer,
            })],
        })
        cls.promo_programs |= cls.code_promo_program

        # auto promo program on current order
        #   -> discount on cheapest product
        cls.auto_promo_program_current = cls.env['loyalty.program'].create({
            'name': 'Auto Promo Program - Cheapest Product',
            'program_type': 'promotion',
            'trigger': 'auto',
            'rule_ids': [(0, 0, {})],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 90,
                'discount_mode': 'percent',
                'discount_applicability': 'cheapest',
            })]
        })
        cls.promo_programs |= cls.auto_promo_program_current

        # auto promo program on next order
        #   -> discount on order (global discount)
        cls.auto_promo_program_next = cls.env['loyalty.program'].create({
            'name': 'Auto Promo Program - Global Discount',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'future',
            'rule_ids': [(0, 0, {})],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount': 10,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })]
        })
        cls.promo_programs |= cls.auto_promo_program_next
        cls.promo_programs.write({
            'pos_config_ids': [Command.link(cls.main_pos_config.id)],
        })

        # coupon program -> free product
        cls.coupon_program = cls.env['loyalty.program'].create({
            'name': 'Coupon Program - Buy 3 Take 2 Free Product',
            'program_type': 'coupons',
            'trigger': 'with_code',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_ids': cls.desk_organizer,
                'reward_point_mode': 'unit',
                'minimum_qty': 3,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': cls.desk_organizer.id,
                'reward_product_qty': 1,
                'required_points': 1.5,
            })],
            'pos_config_ids': [Command.link(cls.main_pos_config.id)],
        })

        # Create coupons for the coupon program and change the code
        # to be able to use them in the frontend tour.
        cls.env["loyalty.generate.wizard"].with_context(
            {"active_id": cls.coupon_program.id}
        ).create({"coupon_qty": 4, 'points_granted': 4.5}).generate_coupons()
        cls.coupon1, cls.coupon2, cls.coupon3, cls.coupon4 = cls.coupon_program.coupon_ids
        cls.coupon1.write({"code": "1234"})
        cls.coupon2.write({"code": "5678"})
        cls.coupon3.write({"code": "1357"})
        cls.coupon4.write({"code": "2468"})

    def setUp(self):
        super().setUp()
        # Set the programs to the pos config.
        # Remove fiscal position and pricelist.
        self.main_pos_config.write({
            'tax_regime_selection': False,
            'use_pricelist': False,
        })
        self.main_pos_config.open_ui()

    def create_programs(self, details):
        """
        Create loyalty programs based on the details given.
        :param details: list of tuple ('name': str, 'program_type': 'gift_card' or 'ewallet')
        """
        LoyaltyProgram = self.env['loyalty.program']
        programs = {} # map: name -> program
        for (name, program_type) in details:
            program_id = LoyaltyProgram.create_from_template(program_type)['res_id']
            program = LoyaltyProgram.browse(program_id)
            program.write({'name': name})
            programs[name] = program
        return programs

    def test_pos_loyalty_tour_basic(self):
        """PoS Loyalty Basic Tour"""
        ##
        # Tour Part 1
        # This part will generate coupons for `auto_promo_program_next`
        # that will be used in the second part of the tour.
        #

        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosLoyaltyTour1",
            login="accountman",
        )

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
        pos_session = self.main_pos_config.current_session_id
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
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosLoyaltyTour2",
            login="accountman",
        )
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
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosLoyaltyValidity1",
            login="accountman",
        )

        self.auto_promo_program_current.write({
            'date_to': date.today() + timedelta(days=2),
        })

        # Second tour that does 2 orders, the first should have the rewards, the second should not
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosLoyaltyValidity2",
            login="accountman",
        )

    def test_loyalty_free_product_rewards(self):
        free_product = self.env['loyalty.program'].create({
            'name': 'Buy 2 Take 1 desk_organizer',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_ids': self.desk_organizer,
                'reward_point_mode': 'unit',
                'minimum_qty': 0,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.desk_organizer.id,
                'reward_product_qty': 1,
                'required_points': 2,
            })],
        })
        free_other_product = self.env['loyalty.program'].create({
            'name': 'Buy 3 magnetic_board, Take 1 whiteboard_pen',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_ids': self.magnetic_board,
                'reward_point_mode': 'unit',
                'minimum_qty': 0,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.whiteboard_pen.id,
                'reward_product_qty': 1,
                'required_points': 3,
            })],
        })
        free_multi_product = self.env['loyalty.program'].create({
            'name': '2 items of shelves, get desk_pad/monitor_stand free',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_ids': (self.wall_shelf | self.small_shelf).ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 0,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_tag_id': self.env['product.tag'].create({
                    'name': 'reward_product_tag',
                    'product_product_ids': (self.desk_pad | self.monitor_stand).ids,
                }).id,
                'reward_product_qty': 1,
                'required_points': 2,
            })],
        })

        (self.promo_programs | self.coupon_program).write({'active': False})

        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosLoyaltyFreeProductTour",
            login="accountman",
        )

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
            'name': 'Buy 4 whiteboard_pen, Take 1 whiteboard_pen',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [(0, 0, {
                'product_ids': self.whiteboard_pen.ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.whiteboard_pen.id,
                'reward_product_qty': 1,
                'required_points': 4,
            })],
        })

        (self.promo_programs | self.coupon_program).write({'active': False})

        partner_aaa = self.env['res.partner'].create({'name': 'Test Partner AAA'})
        partner_bbb = self.env['res.partner'].create({'name': 'Test Partner BBB'})
        partner_ccc = self.env['res.partner'].create({'name': 'Test Partner CCC'})

        # Part 1
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosLoyaltyLoyaltyProgram1",
            login="accountman",
        )

        aaa_loyalty_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == partner_aaa.id)

        self.assertEqual(loyalty_program.pos_order_count, 1)
        self.assertAlmostEqual(aaa_loyalty_card.points, 4)

        # Part 2
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosLoyaltyLoyaltyProgram2",
            login="accountman",
        )

        self.assertEqual(loyalty_program.pos_order_count, 2, msg='Only 2 orders should have reward lines.')
        self.assertAlmostEqual(aaa_loyalty_card.points, 1)

        bbb_loyalty_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == partner_bbb.id)
        ccc_loyalty_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == partner_ccc.id)

        self.assertAlmostEqual(bbb_loyalty_card.points, 3, msg='Reference: Order3_BBB')
        self.assertAlmostEqual(ccc_loyalty_card.points, 4, msg='Reference: Order2_CCC')

        reward_orderline = self.main_pos_config.current_session_id.order_ids[-1].lines.filtered(lambda line: line.is_reward_line)
        self.assertEqual(len(reward_orderline.ids), 0, msg='Reference: Order4_no_reward. Last order should have no reward line.')

    def test_pos_loyalty_tour_max_amount(self):
        """Test the loyalty program with a maximum amount and product with different taxe."""

        self.env['loyalty.program'].search([]).write({'active': False})

        self.promo_product = self.env["product.product"].create(
            {
                "name": "Promo Product",
                "type": "service",
                "list_price": 30,
                "available_in_pos": True,
            }
        )
        tax01 = self.env["account.tax"].create({
            "name": "C01 Tax",
            "amount": "0.00",
        })
        tax02 = self.env["account.tax"].create({
            "name": "C02 Tax",
            "amount": "0.00",
        })

        self.productA = self.env["product.product"].create(
            {
                "name": "Product A",
                "type": "product",
                "list_price": 15,
                "available_in_pos": True,
                "taxes_id": [(6, 0, [tax01.id])],
            }
        )

        # create another product with different taxes_id
        self.productB = self.env["product.product"].create(
            {
                "name": "Product B",
                "type": "product",
                "list_price": 25,
                "available_in_pos": True,
                "taxes_id": [(6, 0, [tax02.id])]
            }
        )

        self.env['loyalty.program'].create({
            'name': 'Promo Program - Max Amount',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_domain': '[["product_variant_ids.name","=","Promo Product"]]',
                'reward_point_mode': 'unit',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_product_ids': (self.productA | self.productB).ids,
                'required_points': 1,
                'discount': 100,
                'discount_mode': 'percent',
                'discount_applicability': 'specific',
                'discount_max_amount': 40,
            })],
            'pos_config_ids': [Command.link(self.main_pos_config.id)],
        })

        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosLoyaltyTour3",
            login="accountman",
        )

    def test_gift_card_program_create_set(self):
        """
        Test for gift card program when pos.config.gift_card_settings == 'create_set'.
        """
        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        # But activate the gift_card_product_50 because it's shared among new gift card programs.
        self.env.ref('loyalty.gift_card_product_50').write({'active': True})
        # Create gift card program
        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']
        # Change the gift card program settings
        self.main_pos_config.write({'gift_card_settings': 'create_set'})
        # Run the tour to create a gift card
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "GiftCardProgramCreateSetTour1",
            login="accountman",
        )
        # Check that gift cards are created
        self.assertEqual(len(gift_card_program.coupon_ids), 1)
        # Change the code to 044123456 so that we can use it in the next tour.
        # Make sure it starts with 044 because it's the prefix of the loyalty cards.
        gift_card_program.coupon_ids.code = '044123456'
        # Run the tour to use the gift card
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "GiftCardProgramCreateSetTour2",
            login="accountman",
        )
        # Check that gift cards are used
        self.assertEqual(gift_card_program.coupon_ids.points, 46.8)

    def test_gift_card_program_scan_use(self):
        """
        Test for gift card program with pos.config.gift_card_settings == 'scan_use'.
        - The gift card coupon codes are known before opening pos.
        - They will be scanned and paid by the customer which links the coupon to the order.
            - Meaning, it's paid.
        - Then it will be scanned for usage.
        """
        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        # But activate the gift_card_product_50 because it's shared among new gift card programs.
        self.env.ref('loyalty.gift_card_product_50').write({'active': True})
        # Create gift card program
        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']
        # Change the gift card program settings
        self.main_pos_config.write({'gift_card_settings': 'scan_use'})
        # Generate 5$ gift card.
        self.env["loyalty.generate.wizard"].with_context(
            {"active_id": gift_card_program.id}
        ).create({"coupon_qty": 1, 'points_granted': 5}).generate_coupons()
        # Change the code of the gift card.
        gift_card_program.coupon_ids.code = '044123456'
        # Run the tour. It will pay the gift card and use it.
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "GiftCardProgramScanUseTour",
            login="accountman",
        )
        # Check that gift cards are used
        self.assertAlmostEqual(gift_card_program.coupon_ids.points, 0, places=2)
        # 3 order should be created.
        self.assertEqual(len(self.main_pos_config.current_session_id.order_ids), 3)

    def test_ewallet_program(self):
        """
        Test for ewallet program.
        - Collect points in EWalletProgramTour1.
        - Use points in EWalletProgramTour2.
        """
        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        # But activate the ewallet_product_50 because it's shared among new ewallet programs.
        self.env.ref('loyalty.ewallet_product_50').write({'active': True})
        # Create ewallet program
        ewallet_program = self.create_programs([('arbitrary_name', 'ewallet')])['arbitrary_name']
        # Create test partners
        partner_aaa = self.env['res.partner'].create({'name': 'AAAAAAA'})
        partner_bbb = self.env['res.partner'].create({'name': 'BBBBBBB'})
        # Run the tour to topup ewallets.
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "EWalletProgramTour1",
            login="accountman",
        )
        # Check that ewallets are created for partner_aaa.
        ewallet_aaa = self.env['loyalty.card'].search([('partner_id', '=', partner_aaa.id), ('program_id', '=', ewallet_program.id)])
        self.assertEqual(len(ewallet_aaa), 1)
        self.assertAlmostEqual(ewallet_aaa.points, 50, places=2)
        # Check that ewallets are created for partner_bbb.
        ewallet_bbb = self.env['loyalty.card'].search([('partner_id', '=', partner_bbb.id), ('program_id', '=', ewallet_program.id)])
        self.assertEqual(len(ewallet_bbb), 1)
        self.assertAlmostEqual(ewallet_bbb.points, 10, places=2)
        # Run the tour consume ewallets.
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "EWalletProgramTour2",
            login="accountman",
        )
        # Check that ewallets are consumed for partner_aaa.
        self.assertAlmostEqual(ewallet_aaa.points, 0, places=2)
        # Check final balance after consumption and refund eWallet for partner_bbb.
        self.assertAlmostEqual(ewallet_bbb.points, 20, places=2)

    def test_multiple_gift_wallet_programs(self):
        """
        Test for multiple gift_card and ewallet programs.
        """
        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        # But activate the gift_card_product_50 and ewallet_product_50 because they're shared among new programs.
        self.env.ref('loyalty.gift_card_product_50').write({'active': True})
        self.env.ref('loyalty.ewallet_product_50').write({'active': True})
        # Create programs
        programs = self.create_programs([
            ('gift_card_1', 'gift_card'),
            ('gift_card_2', 'gift_card'),
            ('ewallet_1', 'ewallet'),
            ('ewallet_2', 'ewallet')
        ])
        # Change the gift card program settings
        self.main_pos_config.write({'gift_card_settings': 'create_set'})
        # Create test partners
        partner_aaa = self.env['res.partner'].create({'name': 'AAAAAAA'})
        partner_bbb = self.env['res.partner'].create({'name': 'BBBBBBB'})
        # Run the tour to topup ewallets.
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "MultipleGiftWalletProgramsTour",
            login="accountman",
        )
        # Check the created gift cards.
        self.assertEqual(len(programs['gift_card_1'].coupon_ids), 1)
        self.assertAlmostEqual(programs['gift_card_1'].coupon_ids.points, 10)
        self.assertEqual(len(programs['gift_card_2'].coupon_ids), 1)
        self.assertAlmostEqual(programs['gift_card_2'].coupon_ids.points, 20)
        # Check the created ewallets.
        ewallet_1_aaa = self.env['loyalty.card'].search([('partner_id', '=', partner_aaa.id), ('program_id', '=', programs['ewallet_1'].id)])
        self.assertEqual(len(ewallet_1_aaa), 1)
        self.assertAlmostEqual(ewallet_1_aaa.points, 18, places=2)
        ewallet_2_aaa = self.env['loyalty.card'].search([('partner_id', '=', partner_aaa.id), ('program_id', '=', programs['ewallet_2'].id)])
        self.assertEqual(len(ewallet_2_aaa), 1)
        self.assertAlmostEqual(ewallet_2_aaa.points, 40, places=2)
        ewallet_1_bbb = self.env['loyalty.card'].search([('partner_id', '=', partner_bbb.id), ('program_id', '=', programs['ewallet_1'].id)])
        self.assertEqual(len(ewallet_1_bbb), 1)
        self.assertAlmostEqual(ewallet_1_bbb.points, 50, places=2)
        ewallet_2_bbb = self.env['loyalty.card'].search([('partner_id', '=', partner_bbb.id), ('program_id', '=', programs['ewallet_2'].id)])
        self.assertEqual(len(ewallet_2_bbb), 1)
        self.assertAlmostEqual(ewallet_2_bbb.points, 0, places=2)

    def test_coupon_change_pricelist(self):
        """Test coupon program with different pricelists."""

        product_1 = self.env["product.product"].create(
            {
                "name": "Test Product 1",
                "type": "product",
                "list_price": 25,
                "available_in_pos": True,
            }
        )

        tax01 = self.env["account.tax"].create({
            "name": "C01 Tax",
            "amount": "0.00",
        })

        product_2 = self.env["product.product"].create(
            {
                "name": "Test Product 2",
                "type": "product",
                "list_price": 25,
                "available_in_pos": True,
                "taxes_id": [(6, 0, [tax01.id])],
            }
        )

        pricelist = self.env["product.pricelist"].create({
            "name": "Test multi-currency",
            "discount_policy": "without_discount",
            "currency_id": self.env.ref("base.USD").id,
            "item_ids": [
                (0, 0, {
                    "base": "standard_price",
                    "product_id": product_1.id,
                    "compute_price": "percentage",
                    "percent_price": 50,
                }),
                (0, 0, {
                    "base": "standard_price",
                    "product_id": product_2.id,
                    "compute_price": "percentage",
                    "percent_price": 50,
                })
            ]
        })

        self.main_pos_config2 = self.main_pos_config.copy()

        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Coupon Program - Pricelist',
            'program_type': 'coupons',
            'trigger': 'with_code',
            'applies_on': 'current',
            'pos_ok': True,
            'pos_config_ids': [Command.link(self.main_pos_config2.id)],
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

        self.main_pos_config2.write({
            'use_pricelist': True,
            'available_pricelist_ids': [(4, pricelist.id), (4, self.main_pos_config.pricelist_id.id)],
            'pricelist_id': pricelist.id,
        })

        self.main_pos_config2.open_ui()
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config2.id,
            "PosLoyaltyTour4",
            login="accountman",
        )

    def test_promotion_program_with_global_discount(self):
        """
        - Create a promotion with a discount of 10%
        - Create a product with no taxes
        - Enable the global discount feature, and make sure the Discount product
            has a tax set on it.
        """

        if not self.env["ir.module.module"].search([("name", "=", "pos_discount"), ("state", "=", "installed")]):
            self.skipTest("pos_discount module is required for this test")

        tax01 = self.env["account.tax"].create({
            "name": "C01 Tax",
            "amount": "0.00"
        })

        self.discount_product = self.env["product.product"].create(
            {
                "name": "Discount Product",
                "type": "service",
                "list_price": 0,
                "available_in_pos": True,
                "taxes_id": [(6, 0, tax01.ids)],
            }
        )

        self.main_pos_config2 = self.main_pos_config.copy()
        self.main_pos_config2.write({
            'module_pos_discount': True,
            'discount_product_id': self.discount_product.id,
            'discount_pc': 20,
        })

        self.loyalty_program = self.env['loyalty.program'].create({
            'name': 'Coupon Program - Pricelist',
            'program_type': 'coupons',
            'trigger': 'with_code',
            'applies_on': 'current',
            'pos_ok': True,
            'pos_config_ids': [Command.link(self.main_pos_config2.id)],
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

        self.product = self.env["product.product"].create(
            {
                "name": "Test Product 1",
                "type": "product",
                "list_price": 100,
                "available_in_pos": True,
            }
        )

        self.main_pos_config2.open_ui()

        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config2.id,
            "PosLoyaltyTour5",
            login="accountman",
        )

    def test_loyalty_program_using_same_product(self):
        """
        - Create a loyalty program giving free product A for 30 points
        - Trigger the condition of the program using the same product A
        """
        LoyaltyProgram = self.env['loyalty.program']
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        self.product_a = self.env["product.product"].create({
            "name": "Test Product A",
            "type": "product",
            "list_price": 10,
            "available_in_pos": True,
        })

        self.loyalty_program = self.env['loyalty.program'].create({
            'name': 'Loyalty Program Test',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'pos_ok': True,
            'pos_config_ids': [Command.link(self.main_pos_config.id)],
            'rule_ids': [(0, 0, {
                'reward_point_mode': 'order',
                'reward_point_amount': 10,
                'minimum_amount': 5,
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'required_points': 30,
                'reward_product_id': self.product_a.id,
                'reward_product_qty': 1,
            })],
        })

        partner_aaa = self.env['res.partner'].create({'name': 'AAA Partner'})
        self.env['loyalty.card'].create({
            'partner_id': partner_aaa.id,
            'program_id': self.loyalty_program.id,
            'points': 30,
        })

        self.main_pos_config.open_ui()

        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosLoyaltyFreeProductTour2",
            login="accountman",
        )
