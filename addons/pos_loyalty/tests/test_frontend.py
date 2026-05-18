# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta
from unittest.mock import patch
from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


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
                'discount_product_ids': cls.whiteboard_pen.product_variant_id | cls.magnetic_board.product_variant_id | cls.desk_organizer.product_variant_id,
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
                'product_ids': cls.desk_organizer.product_variant_ids.ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 3,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': cls.desk_organizer.product_variant_id.id,
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
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.product_b.uom_id = self.ref('uom.product_uom_unit')

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
        self.start_pos_tour("PosLoyaltyTour2")
        # check pos_order_count in each program
        self.assertEqual(self.auto_promo_program_current.pos_order_count, 6)
        self.assertEqual(self.auto_promo_program_next.pos_order_count, 2)
        self.assertEqual(self.code_promo_program.pos_order_count, 2)
        self.assertEqual(self.coupon_program.pos_order_count, 3)

    def test_loyalty_free_product_loyalty_program(self):
        # In this program, each whiteboard pen gives 1 point.
        # 4 points can be used to get a free whiteboard pen.
        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Buy 4 whiteboard_pen, Take 1 whiteboard_pen',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [(0, 0, {
                'product_ids': self.whiteboard_pen.product_variant_id.ids,
                'reward_point_mode': 'unit',
                'minimum_qty': 1,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.whiteboard_pen.product_variant_id.id,
                'reward_product_qty': 1,
                'required_points': 4,
            })],
        })

        (self.promo_programs | self.coupon_program).write({'active': False})

        partner_aaa = self.env['res.partner'].create({'name': 'AAA Test Partner'})
        partner_bbb = self.env['res.partner'].create({'name': 'BBB Test Partner'})
        partner_ccc = self.env['res.partner'].create({'name': 'CCC Test Partner'})

        # Part 1
        self.start_pos_tour("PosLoyaltyLoyaltyProgram1")

        aaa_loyalty_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == partner_aaa.id)

        self.assertEqual(loyalty_program.pos_order_count, 1)
        self.assertAlmostEqual(aaa_loyalty_card.points, 4)
        histories = aaa_loyalty_card.history_ids.sorted("order_id")
        self.assertEqual(histories.mapped("issued"), [2.0, 2.0, 4.0])
        self.assertEqual(histories.mapped("used"), [0.0, 4.0, 0.0])

        # Part 2
        self.start_pos_tour("PosLoyaltyLoyaltyProgram2")

        self.assertEqual(loyalty_program.pos_order_count, 2, msg='Only 2 orders should have reward lines.')
        self.assertAlmostEqual(aaa_loyalty_card.points, 1)

        bbb_loyalty_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == partner_bbb.id)
        ccc_loyalty_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == partner_ccc.id)

        self.assertAlmostEqual(bbb_loyalty_card.points, 3, msg='Reference: Order3_BBB')
        self.assertAlmostEqual(ccc_loyalty_card.points, 4, msg='Reference: Order2_CCC')

        reward_orderline = self.main_pos_config.current_session_id.order_ids[-1].lines.filtered(lambda line: line.is_reward_line)
        self.assertEqual(len(reward_orderline.ids), 0, msg='Reference: Order4_no_reward. Last order should have no reward line.')

        # Part 3
        partner_ddd = self.env['res.partner'].create({'name': 'DDD Test Partner'})
        self.env['loyalty.card'].create({
            'partner_id': partner_ddd.id,
            'program_id': loyalty_program.id,
            'points': 100,
        })

        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosLoyaltyChangeRewardQty",
            login="pos_user",
        )

    def test_loyalty_free_product_zero_sale_price_loyalty_program(self):
        # In this program, each $ spent gives 1 point.
        # 5 points can be used to get a free whiteboard pen.
        # and the whiteboard pen sale price is zero
        self.whiteboard_pen.product_variant_id.write({'lst_price': 1})

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
                'reward_product_id': self.whiteboard_pen.product_variant_id.id,
                'reward_product_qty': 1,
                'required_points': 5,
            })],
        })

        (self.promo_programs | self.coupon_program).write({'active': False})

        partner_aaa = self.env['res.partner'].create({'name': 'AAA Test Partner'})

        self.start_pos_tour("PosLoyaltyLoyaltyProgram3")

        aaa_loyalty_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == partner_aaa.id)

        self.assertEqual(loyalty_program.pos_order_count, 1)
        self.assertAlmostEqual(aaa_loyalty_card.points, 5.2)

    def test_gift_card_program(self):
        """
        Test for gift card program.
        """
        # Ensure Gift Card product is displayed in the PoS session when the selected category is enabled in the configuration.
        self.main_pos_config.current_session_id.close_session_from_ui()
        pos_category = self.env['pos.category'].search([], limit=1)
        self.main_pos_config.write({
            'limit_categories': True,
            'iface_available_categ_ids': [(6, 0, [pos_category.id])],
        })
        self.whiteboard_pen.write({'pos_categ_ids': [(6, 0, [pos_category.id])]})
        self.main_pos_config.open_ui()
        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        # But activate the gift_card_product_50 because it's shared among new gift card programs.
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        # Create gift card program
        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']
        # Run the tour to create a gift card
        self.start_pos_tour("GiftCardProgramTour1")
        # Check that gift cards are created
        self.assertEqual(len(gift_card_program.coupon_ids), 1)
        gift_card_creation_history = self.env['loyalty.history'].search([('card_id', '=', gift_card_program.coupon_ids.id)])
        self.assertEqual(gift_card_creation_history.issued, 50.0, "The gift card should have 50 points issued.")
        # Change the code to 044123456 so that we can use it in the next tour.
        # Make sure it starts with 044 because it's the prefix of the loyalty cards.
        gift_card_program.coupon_ids.code = '044123456'
        # Run the tour to use the gift card
        self.start_pos_tour("GiftCardProgramTour2")
        # Check that gift cards are used (Whiteboard Pen price is 1.20)
        self.assertEqual(gift_card_program.coupon_ids.points, 46.8)
        loyalty_history = self.env['loyalty.history'].search([('card_id', '=', gift_card_program.coupon_ids.id), ('id', '!=', gift_card_creation_history.id)])
        self.assertEqual(loyalty_history.used, 3.2)

    def test_ewallet_program(self):
        """
        Test for ewallet program.
        - Collect points in EWalletProgramTour1.
        - Use points in EWalletProgramTour2.
        """
        # Ensure eWallet product is displayed in the PoS session when the selected category is enabled in the configuration.
        self.main_pos_config.current_session_id.close_session_from_ui()
        pos_category = self.env['pos.category'].search([], limit=1)
        self.main_pos_config.write({
            'limit_categories': True,
            'iface_available_categ_ids': [(6, 0, [pos_category.id])],
        })
        self.whiteboard_pen.write({'pos_categ_ids': [(6, 0, [pos_category.id])]})
        self.main_pos_config.open_ui()

        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        # But activate the ewallet_product_50 because it's shared among new ewallet programs.
        self.env.ref('loyalty.ewallet_product_50').product_tmpl_id.write({'active': True})
        # Create ewallet program
        ewallet_program = self.create_programs([('arbitrary_name', 'ewallet')])['arbitrary_name']
        # Create test partners
        partner_aaa = self.env['res.partner'].create({'name': 'AAAAAAA'})
        partner_bbb = self.env['res.partner'].create({'name': 'BBBBBBB'})
        # Run the tour to topup ewallets.
        self.start_pos_tour("EWalletProgramTour1")
        # Check that ewallets are created for partner_aaa.
        ewallet_aaa = self.env['loyalty.card'].search([('partner_id', '=', partner_aaa.id), ('program_id', '=', ewallet_program.id)])
        self.assertEqual(len(ewallet_aaa), 1)
        self.assertAlmostEqual(ewallet_aaa.points, 50, places=2)
        # Check that ewallets are created for partner_bbb.
        ewallet_bbb = self.env['loyalty.card'].search([('partner_id', '=', partner_bbb.id), ('program_id', '=', ewallet_program.id)])
        self.assertEqual(len(ewallet_bbb), 1)
        self.assertAlmostEqual(ewallet_bbb.points, 10, places=2)
        self.desk_pad.write({'pos_categ_ids': [(6, 0, [pos_category.id])]})
        # Run the tour consume ewallets.
        self.start_pos_tour("EWalletProgramTour2")
        # Check that ewallets are consumed for partner_aaa.
        self.assertAlmostEqual(ewallet_aaa.points, 0, places=2)
        # Check final balance after consumption and refund eWallet for partner_bbb.
        self.assertAlmostEqual(ewallet_bbb.points, 20, places=2)

    def test_ewallet_refund_credit_note_line_quantity(self):
        """Reproduce: sell+invoice product, refund order, use eWallet refund payment.
        The generated credit note must keep refunded product quantity positive."""
        LoyaltyProgram = self.env['loyalty.program']
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        self.env.ref('loyalty.ewallet_product_50').product_tmpl_id.write({'active': True})
        self.create_programs([('arbitrary_name', 'ewallet')])
        partner_aaa = self.env['res.partner'].create({'name': 'Ewal'})

        self.start_pos_tour("EWalletRefundCreditNoteQtyTour")

        refund_orders = self.main_pos_config.current_session_id.order_ids.filtered(
            lambda o: o.partner_id == partner_aaa and o.refunded_order_id and o.account_move and o.account_move.move_type == 'out_refund'
        )
        self.assertEqual(len(refund_orders), 1, "A single invoiced refund order should be created.")

        refund_order = refund_orders[0]
        refunded_product_line = refund_order.lines.filtered('refunded_orderline_id')[:1]
        self.assertTrue(refunded_product_line, "Refund order should contain a refunded product line.")

        invoice_product_line = refund_order.account_move.invoice_line_ids.filtered(
            lambda l: l.product_id == refunded_product_line.product_id,
        )
        self.assertTrue(invoice_product_line, "Credit note should contain the refunded product line.")
        self.assertEqual(invoice_product_line[:1].quantity, 1, "Refunded product quantity on credit note must be positive (1).")

    def test_multiple_gift_wallet_programs(self):
        """
        Test for multiple gift_card and ewallet programs.
        """
        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        # But activate the gift_card_product_50 and ewallet_product_50 because they're shared among new programs.
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        self.env.ref('loyalty.ewallet_product_50').product_tmpl_id.write({'active': True})
        # Create programs
        programs = self.create_programs([
            ('gift_card_1', 'gift_card'),
            ('gift_card_2', 'gift_card'),
            ('ewallet_1', 'ewallet'),
            ('ewallet_2', 'ewallet')
        ])
        # Create test partners
        partner_aaa = self.env['res.partner'].create({'name': 'AAAAAAA'})
        partner_bbb = self.env['res.partner'].create({'name': 'BBBBBBB'})
        # Run the tour to topup ewallets.
        self.start_pos_tour("MultipleGiftWalletProgramsTour")
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
        # Before the tour there's no card for partner B and ewallet 2
        # During the tour the ewallet 2 is not used for partner 2 and no "points" are granted
        # We don't create cards when there's no point and there's no history on it
        self.assertEqual(len(ewallet_2_bbb), 0)

    def test_loyalty_program_different_orders(self):
        loyalty_program = self.env['loyalty.program'].create({
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

        partner = self.env['res.partner'].create({'name': 'Partner Test 1'})
        card = self.env['loyalty.card'].create({
            'partner_id': partner.id,
            'program_id': loyalty_program.id,
            'points': 0,
        })

        self.main_pos_config.open_ui()

        self.start_pos_tour("PosLoyaltyMultipleOrders")

        self.assertEqual(card.points, 0, "Loyalty card credited for a draft order")

    def test_2_discounts_specific_global(self):
        self.pos_user.group_ids |= self.quick_ref('product.group_product_manager')
        self.env['res.partner'].create({'name': 'AAAA'})
        LoyaltyProgram = self.env['loyalty.program']
        (LoyaltyProgram.search([])).write({'pos_ok': False})

        product_category = self.env['product.category'].create({
            'name': 'Discount category',
        })

        self.product_a = self.env['product.product'].create({
            'name': 'Test Product A',
            'is_storable': True,
            'list_price': 5,
            'available_in_pos': True,
            'taxes_id': False,
        })
        self.product_b = self.env['product.product'].create({
            'name': 'Test Product B',
            'is_storable': True,
            'list_price': 5,
            'available_in_pos': True,
            'taxes_id': False,
            'categ_id': product_category.id,
        })

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
            'pos_config_ids': [Command.link(self.main_pos_config.id)],
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
                'discount_product_category_id': product_category.id,
            })],
            'pos_config_ids': [Command.link(self.main_pos_config.id)],
        })

        self.main_pos_config.open_ui()
        self.start_pos_tour("PosLoyalty2DiscountsSpecificGlobal")

    def test_physical_gift_card_sale(self):
        """
        Test that the manual gift card sold has been correctly generated.
        """
        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference and activate the gift_card_product_50
        LoyaltyProgram.search([]).write({'pos_ok': False})
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})

        # Create gift card program
        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']

        # Run the tour
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PhysicalGiftCardProgramSaleTour",
            login="pos_user"
        )

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

    def test_gift_card_code_links_to_correct_program(self):
        """
        Test that the manual gift card sold has been correctly generated
        with the correct assigned code.
        """
        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference and activate the gift_card_product_50
        LoyaltyProgram.search([]).write({'pos_ok': False})
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})

        # Create gift card programs
        program1 = self.create_programs([('Gift Cards1', 'gift_card')])['Gift Cards1']
        program2 = self.create_programs([('Gift Cards2', 'gift_card')])['Gift Cards2']
        program3 = self.create_programs([('Gift Cards3', 'gift_card')])['Gift Cards3']

        # Run the tour
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "MultiplePhysicalGiftCardProgramSaleTour",
            login="pos_user"
        )

        self.assertTrue(len(program1.coupon_ids) == len(program2.coupon_ids) == len(program3.coupon_ids) == 1)
        self.assertEqual(program1.coupon_ids.code, 'test-card-0000')
        self.assertEqual(program2.coupon_ids.code, 'test-card-0001')
        self.assertEqual(program3.coupon_ids.code, 'test-card-0002')

    def test_dont_grant_points_reward_order_lines(self):
        """
        Make sure that points granted per unit are only given
        for the product -non reward- lines!
        """
        self.env['loyalty.program'].search([]).write({'active': False})

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

        partner = self.env['res.partner'].create({'name': 'A Test Partner'})
        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosLoyaltyDontGrantPointsForRewardOrderLines",
            login="pos_user",
        )

        loyalty_card = loyalty_program.coupon_ids.filtered(lambda coupon: coupon.partner_id.id == partner.id)

        self.assertTrue(loyalty_card)
        self.assertFalse(loyalty_card.points)

    def test_points_awarded_global_discount_code_no_domain_program(self):
        """
        Check the calculation for points awarded when there is a global discount applied and the
        loyalty program applies on all product (no domain).
        """
        self.env['loyalty.program'].search([]).write({'active': False})
        self.product_a.write({
            'list_price': 100,
            'available_in_pos': True,
            'taxes_id': False,
        })

        self.auto_promo_program_next.applies_on = 'current'
        self.auto_promo_program_next.active = True

        loyalty_program = self.create_programs([('Loyalty P', 'loyalty')])['Loyalty P']
        partner_aaa = self.env['res.partner'].create({'name': 'AAAA'})
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': partner_aaa.id,
            'points': 0,
        })

        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosLoyaltyPointsGlobalDiscountProgramNoDomain",
            login="pos_user",
        )
        self.assertEqual(loyalty_card.points, 90)

    def test_points_awarded_discount_code_no_domain_program(self):
        """
        Check the calculation for points awarded when there is a discount coupon applied and the
        loyalty program applies on all product (no domain).
        """
        self.env['loyalty.program'].search([]).write({'active': False})
        self.product_a.write({
            'list_price': 100,
            'available_in_pos': True,
            'taxes_id': False,
        })
        self.product_b.write({
            'list_price': 50,
            'available_in_pos': True,
            'taxes_id': False,
        })
        loyalty_program = self.create_programs([('Loyalty P', 'loyalty')])['Loyalty P']
        loyalty_program.pos_config_ids = [Command.link(self.main_pos_config.id)]
        partner_aaa = self.env['res.partner'].create({'name': 'AAAA'})
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': partner_aaa.id,
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

        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosLoyaltyPointsDiscountNoDomainProgramNoDomain",
            login="pos_user",
        )
        self.assertEqual(loyalty_card.points, 135)

    def test_points_awarded_general_discount_code_specific_domain_program(self):
        """
        Check the calculation for points awarded when there is a discount coupon applied and the
        loyalty program applies on a sepcific domain. The discount code has no domain. The product
        related to that discount is not in the domain of the loyalty program.
        Expected behavior: The discount is not included in the computation of points
        """
        product_category_food = self.env['product.category'].create({
            'name': 'Food',
        })

        self.env['loyalty.program'].search([]).write({'active': False})

        self.product_a.write({
            'list_price': 100,
            'available_in_pos': True,
            'taxes_id': False,
            'categ_id': product_category_food.id,
        })
        self.product_b.write({
            'list_price': 50,
            'available_in_pos': True,
            'taxes_id': False,
        })

        loyalty_program = self.create_programs([('Loyalty P', 'loyalty')])['Loyalty P']
        loyalty_program.rule_ids.product_category_id = product_category_food.id
        loyalty_program.pos_config_ids = [Command.link(self.main_pos_config.id)]
        partner_aaa = self.env['res.partner'].create({'name': 'AAAA'})
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': partner_aaa.id,
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

        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosLoyaltyPointsDiscountNoDomainProgramDomain",
            login="pos_user",
        )
        self.assertEqual(loyalty_card.points, 100)

    def test_points_awarded_specific_discount_code_specific_domain_program(self):
        """
        Check the calculation for points awarded when there is a discount coupon applied and the
        loyalty program applies on a sepcific domain. The discount code has the same domain as the
        loyalty program. The product related to that discount code is set up to be included in the
        domain of the loyalty program.
        """
        product_category_food = self.env['product.category'].create({
            'name': 'Food',
        })

        self.env['loyalty.program'].search([]).write({'active': False})

        self.product_a.write({
            'list_price': 100,
            'available_in_pos': True,
            'taxes_id': False,
            'categ_id': product_category_food.id,
        })
        self.product_b.write({
            'list_price': 50,
            'available_in_pos': True,
            'taxes_id': False,
        })

        loyalty_program = self.create_programs([('Loyalty P', 'loyalty')])['Loyalty P']
        loyalty_program.rule_ids.product_category_id = product_category_food.id
        loyalty_program.pos_config_ids = [Command.link(self.main_pos_config.id)]
        partner_aaa = self.env['res.partner'].create({'name': 'AAAA'})
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': partner_aaa.id,
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

        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosLoyaltyPointsDiscountWithDomainProgramDomain",
            login="pos_user",
        )
        self.assertEqual(loyalty_card.points, 90)

    def test_points_awarded_ewallet(self):
        """
        Check the calculation for point awarded when using ewallet
        """
        self.env['loyalty.program'].search([]).write({'active': False})
        self.product_a.write({
            'list_price': 100,
            'available_in_pos': True,
            'taxes_id': False,
        })

        loyalty_program = self.create_programs([('Loyalty P', 'loyalty')])['Loyalty P']
        loyalty_program.pos_config_ids = [Command.link(self.main_pos_config.id)]
        partner_aaa = self.env['res.partner'].create({'name': 'AAAA'})
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': partner_aaa.id,
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
            'partner_id': partner_aaa.id,
            'points': 10,
        })

        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosLoyaltyPointsEwallet",
            login="pos_user",
        )
        self.assertEqual(loyalty_card.points, 100)

    def test_points_awarded_giftcard(self):
        """
        Check the calculation for point awarded when using a gift card
        """
        self.env['loyalty.program'].search([]).write({'active': False})
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        # Create gift card program
        self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']

        self.product_a.write({
            'list_price': 100,
            'available_in_pos': True,
            'taxes_id': False,
        })

        loyalty_program = self.create_programs([('Loyalty P', 'loyalty')])['Loyalty P']
        loyalty_program.pos_config_ids = [Command.link(self.main_pos_config.id)]
        partner_aaa = self.env['res.partner'].create({'name': 'AAAA'})
        loyalty_card = self.env['loyalty.card'].create({
            'program_id': loyalty_program.id,
            'partner_id': partner_aaa.id,
            'points': 0,
        })

        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosLoyaltyPointsGiftcard",
            login="pos_user",
        )
        self.assertEqual(loyalty_card.points, 100)

    def test_archived_reward_products(self):
        """
        Check that a loyalty_reward with no active reward product is not loaded.
        In the case where the reward is based on reward_product_tag_id we also check
        the case where at least one reward is  active.
        """
        self.pos_user.group_ids |= self.quick_ref('product.group_product_manager')
        self.env['loyalty.program'].search([]).write({'active': False})
        free_product_tag = self.env['product.tag'].create({'name': 'Free Product'})
        self.env['res.partner'].create({'name': 'AAAA'})

        self.product_a.write({
            'name': 'Test Product A',
            'is_storable': True,
            'list_price': 100,
            'available_in_pos': True,
            'taxes_id': False,
        })

        self.product_b.write({'product_tag_ids': [(4, free_product_tag.id)]})
        product_c = self.env['product.product'].create(
            {
                'name': 'Free Product C',
                'list_price': 1,
                'available_in_pos': True,
                'taxes_id': False,
                'product_tag_ids': [(4, free_product_tag.id)],
            }
        )

        LoyaltyProgram = self.env['loyalty.program']
        loyalty_program = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])
        loyalty_program_tag = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])

        loyalty_program.reward_ids.write({
            'reward_type': 'product',
            'required_points': 1,
            'reward_product_id': self.product_b,
        })

        loyalty_program_tag.reward_ids.write({
            'reward_type': 'product',
            'required_points': 1,
            'reward_product_tag_id': free_product_tag.id,
        })

        self.product_b.product_tmpl_id.active = False
        product_c.product_tmpl_id.active = False

        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosLoyaltyArchivedRewardProductsInactive",
            login="pos_user",
        )

        product_c.product_tmpl_id.active = True
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosLoyaltyArchivedRewardProductsActive",
            login="pos_user"
        )

    def test_change_reward_value_with_language(self):
        """
        Verify that the displayed language is not en_US.
        When a user has another language than en_US set,
        he shouldn't have the en_US message displayed but the message of the active language.
        For this test, we shouldn't have the description displayed for selecting the reward in en_US but in en_GB.
        Description in en_US (unexpected): 'A en_US name which should not be displayed'
        Description in en_GB (expected): '$ 2 on your order'
        """

        self.env['loyalty.program'].search([]).write({'active': False})
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

        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "ChangeRewardValueWithLanguage",
            login="pos_user",
        )

    def test_gift_card_rewards_using_taxes(self):
        """
        Check the gift card value when the reward has taxes
        """
        self.env['loyalty.program'].search([]).write({'active': False})
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})

        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']
        self.product_a = self.env["product.product"].create({
            "name": "Test Product A",
            "list_price": 100,
            "available_in_pos": True,
            "taxes_id": False,
        })

        self.tax01 = self.env["account.tax"].create({
            "name": "C01 Tax",
            "amount": "15.00",
        })
        gift_card_program.payment_program_discount_product_id.taxes_id = self.tax01

        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosLoyaltyGiftCardTaxes",
            login="accountman",
        )
        self.main_pos_config.current_session_id.close_session_from_ui()

    def test_apply_reward_on_product_scan(self):
        """
        Test that the rewards are correctly applied if the
        product is scanned rather than added by hand.
        """
        product = self.product_a
        product.write({
            'available_in_pos': True,
            'barcode': '95412427100283',
        })
        self.env['loyalty.program'].search([]).write({'active': False})
        self.env['loyalty.program'].create({
            'name': 'My super program',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'product_ids': [Command.set(product.ids)],
                'reward_point_mode': 'order',
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 50,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
            'pos_config_ids': [Command.link(self.main_pos_config.id)],
        })
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosRewardProductScan",
            login="pos_admin",
        )
        # check the same flow with gs1 nomenclature
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosRewardProductScanGS1",
            login="pos_admin",
        )

    def test_gift_card_program_create_with_invoice(self):
        """
        Test for gift card program when pos.config.gift_card_settings == 'create_set'.
        """
        LoyaltyProgram = self.env['loyalty.program']
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})

        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']
        self.env['res.partner'].create({'name': 'A Test Partner'})

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "GiftCardProgramInvoice",
            login="pos_user",
        )
        self.assertEqual(len(gift_card_program.coupon_ids), 1)

    def test_refund_product_part_of_rules(self):

        self.product_a.available_in_pos = True
        self.env['loyalty.program'].search([]).write({'active': False})
        self.env['loyalty.program'].create({
            'name': 'My super program',
            'program_type': 'promotion',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [Command.create({
                'product_ids': [Command.set(self.product_a.ids)],
                'reward_point_mode': 'order',
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 50,
                'discount_mode': 'percent',
                'discount_applicability': 'order',
            })],
            'pos_config_ids': [Command.link(self.main_pos_config.id)],
        })

        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        self.create_programs([('arbitrary_name', 'gift_card')])

        self.env['res.partner'].create({'name': 'AAAAAAA'})
        self.env.ref('loyalty.ewallet_product_50').product_tmpl_id.write({'active': True})
        self.create_programs([('arbitrary_name', 'ewallet')])

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "RefundRulesProduct",
            login="pos_user",
        )

    def test_next_order_coupon_program_expiration_date(self):
        self.env['loyalty.program'].search([]).write({'active': False})

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

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            "/pos/ui/%d" % self.main_pos_config.id,
            "PosLoyaltyNextOrderCouponExpirationDate",
            login="pos_user",
        )

        coupon = loyalty_program.coupon_ids
        self.assertEqual(len(coupon), 1, "Coupon not generated")
        self.assertEqual(coupon.expiration_date, date.today() + timedelta(days=2), "Coupon not generated with correct expiration date")

    def test_ewallet_loyalty_history(self):
        """
        This will test that all transactions made on an ewallet are registered in the loyalty history
        """
        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        # But activate the ewallet_product_50 because it's shared among new ewallet programs.
        self.env.ref('loyalty.ewallet_product_50').product_tmpl_id.write({'active': True})
        # Create ewallet program
        ewallet_program = self.create_programs([('arbitrary_name', 'ewallet')])['arbitrary_name']
        # Create test partners
        partner_aaa = self.env['res.partner'].create({'name': 'AAAAAAA'})
        # Run the tour to topup ewallets.
        self.start_pos_tour("EWalletLoyaltyHistory")
        # Check that ewallets are created for partner_aaa.
        ewallet_aaa = self.env['loyalty.card'].search([('partner_id', '=', partner_aaa.id), ('program_id', '=', ewallet_program.id)])
        loyalty_history = self.env['loyalty.history'].search([('card_id','=',ewallet_aaa.id)])
        self.assertEqual(loyalty_history.mapped("issued"), [0.0, 50.0])
        self.assertEqual(loyalty_history.mapped("used"), [12.0, 0.0])

    def test_gift_card_no_date(self):
        """
        This test create a physical gift card without expiracy date.
        """
        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference and activate the gift_card_product_50
        LoyaltyProgram.search([]).write({'pos_ok': False})
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})

        # Create gift card program
        self.create_programs([('name', 'gift_card')])
        self.start_pos_tour("test_gift_card_no_date")

    def test_not_create_loyalty_card_expired_program(self):
        self.env['loyalty.program'].search([]).write({'active': False})
        self.env['res.partner'].create({'name': 'Test Partner'})

        LoyaltyProgram = self.env['loyalty.program']
        loyalty_program = LoyaltyProgram.create(LoyaltyProgram._get_template_values()['loyalty'])
        loyalty_program.write({
            'date_from': date.today() - timedelta(days=10),
            'date_to': date.today() - timedelta(days=5),
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "test_not_create_loyalty_card_expired_program",
            login="pos_user",
        )

        self.assertEqual(loyalty_program.coupon_count, 0)

    def test_not_create_loyalty_card_max_usage_program(self):
        self.env['loyalty.program'].search([]).write({'active': False})
        self.env['res.partner'].create({'name': 'Test Partner'})
        self.env['res.partner'].create({'name': 'Test Partner 2'})

        loyalty_program = self.env['loyalty.program'].create({
            'name': 'Loyalty Program',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [(0, 0, {
                'reward_point_amount': 1,
                'reward_point_mode': 'money',
                'minimum_qty': 1,
                'mode': 'auto',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.whiteboard_pen.product_variant_id.id,
                'reward_product_qty': 1,
                'required_points': 5,
            })],
            'limit_usage': True,
            'max_usage': 1,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosOrderClaimReward",
            login="pos_user",
        )

        self.assertEqual(loyalty_program.coupon_count, 1)
        self.assertEqual(loyalty_program.total_order_count, 1)

        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosOrderNoPoints",
            login="pos_user",
        )

        self.assertEqual(loyalty_program.coupon_count, 1)
        self.assertEqual(loyalty_program.total_order_count, 1)

    def test_physical_gift_card_invoiced(self):
        """
        Test that the manual gift card sold has been generated with correct code and partner id"""
        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference and activate the gift_card_product_50
        LoyaltyProgram.search([]).write({'pos_ok': False})
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        partner = self.env['res.partner'].create({'name': 'AABBCC Test Partner'})
        # Create gift card program
        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']

        # Run the tour
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "test_physical_gift_card_invoiced",
            login="pos_user",
        )

        self.assertEqual(len(gift_card_program.coupon_ids), 1, "Gift card not generated")
        self.assertEqual(gift_card_program.coupon_ids[0].code, "test-card-1234", "Gift card code not correct")
        self.assertEqual(gift_card_program.coupon_ids[0].partner_id, partner, "Gift card partner id not correct")

    def test_settle_dont_give_points_again(self):
        """
        Tests that when settling an order that has been partially paid, it does not give the loyalty
        points again. All of them should be given during the first transaction.
        """
        if not self.env["ir.module.module"].search([("name", "=", "pos_settle_due"), ("state", "=", "installed")]):
            self.skipTest("pos_settle_due module is required for this test")
        if self.main_pos_config.current_session_id:
            self.main_pos_config.current_session_id.action_pos_session_closing_control()
        LoyaltyProgram = self.env['loyalty.program']
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        self.loyalty_program = self.env['loyalty.program'].create({
            'name': 'Loyalty Program Test',
            'program_type': 'promotion',
            'pos_ok': True,
            'pos_config_ids': [Command.link(self.main_pos_config.id)],
            'rule_ids': [Command.create({
                'reward_point_mode': 'money',
                'reward_point_amount': 1,
                'minimum_qty': 0,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'discount': 1,
                'discount_mode': 'per_point',
            })],
        })
        partner_aaa = self.env['res.partner'].create({'name': 'AAA Partner'})
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        self.main_pos_config.write({
            'payment_method_ids': [(4, self.customer_account_payment_method.id, 0)],
        })
        self.main_pos_config.open_ui()
        order = self.env['pos.order'].create({
            'company_id': self.company.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'partner_id': partner_aaa.id,
            'lines': [Command.create({
                'product_id': self.wall_shelf.product_variant_id.id,
                'price_unit': 10,
                'discount': 0,
                'qty': 1,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
            'amount_paid': 10.0,
            'amount_total': 10.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': True,
        })
        payment_context = {"active_id": order.id, "active_ids": order.ids}
        self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': 10.0,
            'payment_method_id': self.customer_account_payment_method.id,
        }).check()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_settle_dont_give_points_again', login="accountman")

    def test_refund_does_not_decrease_points(self):
        """
        Tests that when refunding a product bought while spending points, it does not decrease the points a second time
        """
        self.pos_user.group_ids |= self.quick_ref('product.group_product_manager')
        LoyaltyProgram = self.env['loyalty.program']
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        self.loyalty_program = self.env['loyalty.program'].create({
            'name': 'Loyalty Program Test',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'pos_ok': True,
            'pos_config_ids': [Command.link(self.main_pos_config.id)],
            'rule_ids': [Command.create({
                'reward_point_mode': 'money',
                'reward_point_amount': 0.1,
                'minimum_amount': 1,
            })],
            'reward_ids': [Command.create({
                'reward_type': 'discount',
                'required_points': 100,
                'discount': 1,
                'discount_mode': 'per_point',
            })],
        })
        self.product_refund = self.env["product.product"].create({
            "name": "Refund Product",
            "is_storable": True,
            "list_price": 300,
            "available_in_pos": True,
            "taxes_id": False,
        })
        partner_refunding = self.env['res.partner'].create({'name': 'Refunding Guy'})
        card = self.env['loyalty.card'].create({
            'partner_id': partner_refunding.id,
            'program_id': self.loyalty_program.id,
            'points': 100,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_refund_does_not_decrease_points', login="pos_user")
        self.assertEqual(card.points, 30)

    def test_loyalty_reward_with_variant(self):
        self.env['loyalty.program'].search([]).write({'active': False})

        product_tag = self.env['product.tag'].create({'name': 'Test Tag'})
        product_test = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 10,
            'available_in_pos': True,
            'taxes_id': False,
            'product_tag_ids': [(4, product_tag.id)],
        })
        attribute = self.env['product.attribute'].create({
            'name': 'Attribute 1',
            'create_variant': 'always',
        })
        attribute_value_1 = self.env['product.attribute.value'].create({
            'name': 'Value 1',
            'attribute_id': attribute.id,
        })
        attribute_value_2 = self.env['product.attribute.value'].create({
            'name': 'Value 2',
            'attribute_id': attribute.id,
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_test.product_tmpl_id.id,
            'attribute_id': attribute.id,
            'value_ids': [(6, 0, [attribute_value_1.id, attribute_value_2.id])],
        })

        self.env['loyalty.program'].create({
            'name': 'Buy 2 Take 1 with tag',
            'program_type': 'buy_x_get_y',
            'trigger': 'auto',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'product_tag_id': product_tag.id,
                'reward_point_mode': 'unit',
                'minimum_qty': 2,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_tag_id': product_tag.id,
                'reward_product_qty': 1,
                'required_points': 2,
            })],
            'pos_config_ids': [Command.link(self.main_pos_config.id)],
        })

        self.main_pos_config.open_ui()
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "test_loyalty_reward_with_variant",
            login="pos_user",
        )

    def test_physical_gift_card(self):
        self.env['loyalty.program'].search([]).write({'active': False})
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']
        example_order_1, example_order_2, example_order_3 = self.env['pos.order'].create([{
            'name': 'Gift Card Sold',
            'amount_paid': 60.0,
            'amount_total': 60.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'session_id': self.main_pos_config.current_session_id.id,
            'state': 'paid',
        } for _ in range(3)])
        gift_card_valid = self.env['loyalty.card'].create({
            'program_id': gift_card_program.id,
            'source_pos_order_id': example_order_1.id,
            'code': 'gift_card_valid',
            'points': 60.0,
            'history_ids': [(0, 0, {
                'order_model': 'pos.order',
                'order_id': example_order_1.id,
                'description': 'sold',
                'used': 0,
                'issued': 60.0,
            })]
        })
        gift_card_partner = self.env['loyalty.card'].create({
            'program_id': gift_card_program.id,
            'source_pos_order_id': example_order_2.id,
            'code': 'gift_card_partner',
            'points': 60.0,
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'history_ids': [(0, 0, {
                'order_model': 'pos.order',
                'order_id': example_order_2.id,
                'description': 'sold',
                'used': 0,
                'issued': 60.0,
            })]
        })
        with freeze_time(date.today() - timedelta(days=1)):
            gift_card_expired = self.env['loyalty.card'].create({
                'program_id': gift_card_program.id,
                'code': 'gift_card_expired',
                'points': 60.0,
                'expiration_date': date.today(),
            })
        gift_card_sold = self.env['loyalty.card'].create({
            'program_id': gift_card_program.id,
            'source_pos_order_id': example_order_3.id,
            'code': 'gift_card_sold',
            'points': 60.0,
            'history_ids': [(0, 0, {
                'order_model': 'pos.order',
                'order_id': example_order_3.id,
                'description': 'sold',
                'used': 0,
                'issued': 60.0,
            })]
        })
        gift_card_generated_but_not_sold = self.env['loyalty.card'].create({
            'program_id': gift_card_program.id,
            'code': 'gift_card_generated_but_not_sold',
            'points': 60.0,
        })

        self.start_pos_tour("test_physical_gift_card")
        self.assertEqual(gift_card_valid.points, 56.80)
        self.assertEqual(gift_card_sold.points, 53.60)
        self.assertEqual(gift_card_partner.points, 56.80)
        self.assertEqual(gift_card_generated_but_not_sold.points, 47.20)
        self.assertEqual(gift_card_expired.points, 60.0)

        created_gift_card = self.env['loyalty.card'].search([('points', '=', 999)], order='id desc', limit=1)
        last_order = self.env['pos.order'].search([], order='id desc', limit=1)
        self.assertEqual(created_gift_card.points, 999.00)
        self.assertEqual(created_gift_card.partner_id.name, 'A powerful PoS man!')
        self.assertEqual(created_gift_card.source_pos_order_id.id, last_order.id)

    def test_min_qty_points_awarded(self):
        self.env['loyalty.program'].search([]).write({'active': False})
        aa_partner = self.env['res.partner'].create({'name': 'AA Partner'})
        program = self.env['loyalty.program'].create({
            'name': 'Loyalty Program',
            'program_type': 'loyalty',
            'trigger': 'auto',
            'applies_on': 'both',
            'rule_ids': [(0, 0, {
                'reward_point_amount': 10,
                'reward_point_mode': 'money',
                'minimum_qty': 5,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.whiteboard_pen.product_variant_id.id,
                'reward_product_qty': 1,
                'required_points': 5,
            })],
        })

        loyalty_card = self.env['loyalty.card'].create({
            'program_id': program.id,
            'partner_id': aa_partner.id,
            'points': 100,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "test_min_qty_points_awarded",
            login="pos_user",
        )
        self.assertEqual(loyalty_card.points, 90)

    def test_confirm_coupon_programs_one_by_one(self):
        """
        Sync from UI is now syncing orders one by one.
        confirm_coupon_programs should be called 6 times in this tour (6 orders created).
        """
        self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']
        pos_order = self.env.registry.models['pos.order']
        sync_counter = {'count': 0}

        def confirm_coupon_programs_patch(self, coupon_data):
            sync_counter['count'] += 1
            return super(pos_order, self).confirm_coupon_programs(coupon_data)

        with patch.object(pos_order, "confirm_coupon_programs", confirm_coupon_programs_patch):
            self.start_pos_tour("test_confirm_coupon_programs_one_by_one", login="pos_user")
            self.assertEqual(sync_counter['count'], 6)

    def test_specific_reward_product_tax_included_excluded(self):
        """This test makes sure that the value of a reward applied on a specific product is
        the same whether the tax is included or excluded in the product price.
        """
        tax_01 = self.env['account.tax'].create({
                "name": "Tax 1",
                "amount": 10,
                "price_include_override": "tax_included",
        })

        product = self.env['product.product'].create({
            "name": "Product Include",
            "lst_price": 100,
            "available_in_pos": True,
            "taxes_id": [Command.set(tax_01.ids)],
        })

        self.env['loyalty.program'].search([]).write({'active': False})
        self.env["loyalty.program"].create(
            {
                "name": "Test Loyalty Program",
                "program_type": "promotion",
                "trigger": "with_code",
                'pos_ok': True,
                "rule_ids": [
                    Command.create({"mode": "with_code", "code": "hellopromo"}),
                ],
                "reward_ids": [
                    Command.create({
                        "reward_type": "discount",
                        "discount": 10,
                        "discount_mode": "per_order",
                        "discount_applicability": "specific",
                        "required_points": 1,
                        "discount_product_ids": product.ids,
                    }),
                ],
            }
        )

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui/{self.main_pos_config.id}", 'test_specific_reward_product_tax_included_included', login="pos_user")
        tax_01.price_include_override = "tax_excluded"
        # Discount should be the same even if tax mode is changed
        self.start_tour(f"/pos/ui/{self.main_pos_config.id}", 'test_specific_reward_product_tax_included_excluded', login="pos_user")

    def test_order_reward_product_tax_included_excluded(self):
        """This test makes sure that the value of a reward applied on a specific product is
        the same whether the tax is included or excluded in the product price.
        """
        tax_01 = self.env['account.tax'].create({
                "name": "Tax 1",
                "amount": 10,
                "price_include_override": "tax_included",
        })

        self.env['product.product'].create({
            "name": "Product Include",
            "lst_price": 100,
            "available_in_pos": True,
            "taxes_id": [Command.set(tax_01.ids)],
        })

        self.env['loyalty.program'].search([]).write({'active': False})
        self.env["loyalty.program"].create(
            {
                "name": "Test Loyalty Program",
                "program_type": "promotion",
                "trigger": "with_code",
                'pos_ok': True,
                "rule_ids": [
                    Command.create({"mode": "with_code", "code": "hellopromo"}),
                ],
                "reward_ids": [
                    Command.create({
                        "reward_type": "discount",
                        "discount": 10,
                        "discount_mode": "per_order",
                        "discount_applicability": "order",
                        "required_points": 1,
                    }),
                ],
            }
        )

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui/{self.main_pos_config.id}", 'test_order_reward_product_tax_included_included', login="pos_user")
        tax_01.price_include_override = "tax_excluded"
        # Discount should be the same even if tax mode is changed
        self.start_tour(f"/pos/ui/{self.main_pos_config.id}", 'test_order_reward_product_tax_included_excluded', login="pos_user")

    def test_multiple_physical_gift_card_sale(self):
        """
        Test that the manual gift card sold has been correctly generated.
        """
        LoyaltyProgram = self.env['loyalty.program']
        # Deactivate all other programs to avoid interference and activate the gift_card_product_50
        LoyaltyProgram.search([]).write({'pos_ok': False})
        self.env.ref('loyalty.gift_card_product_50').product_tmpl_id.write({'active': True})
        # Create gift card program
        gift_card_program = self.create_programs([('arbitrary_name', 'gift_card')])['arbitrary_name']

        # Run the tour
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "test_multiple_physical_gift_card_sale",
            login="pos_user",
        )
        self.assertEqual(len(gift_card_program.coupon_ids), 2)
