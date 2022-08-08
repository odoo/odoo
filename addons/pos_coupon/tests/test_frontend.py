# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import Form, tagged


@tagged("post_install", "-at_install")
class TestUi(TestPointOfSaleHttpCommon):
    def setUp(self):
        super().setUp()

        self.promo_programs = self.env["coupon.program"]

        # code promo program -> discount on specific products
        self.code_promo_program = self.env["coupon.program"].create(
            {
                "name": "Promo Code Program - Discount on Specific Products",
                "program_type": "promotion_program",
                "promo_code_usage": "code_needed",
                "promo_code": "promocode",
                "discount_apply_on": "specific_products",
                "discount_percentage": 50,
                "discount_specific_product_ids": (
                    self.whiteboard_pen | self.magnetic_board | self.desk_organizer
                ).ids,
            }
        )
        self.promo_programs |= self.code_promo_program

        # auto promo program on current order
        #   -> discount on cheapest product
        self.auto_promo_program_current = self.env["coupon.program"].create(
            {
                "name": "Auto Promo Program - Cheapest Product",
                "program_type": "promotion_program",
                "promo_code_usage": "no_code_needed",
                "discount_apply_on": "cheapest_product",
                "discount_percentage": 90,
            }
        )
        self.promo_programs |= self.auto_promo_program_current

        # auto promo program on next order
        #   -> discount on order (global discount)
        self.auto_promo_program_next = self.env["coupon.program"].create(
            {
                "name": "Auto Promo Program - Global Discount",
                "program_type": "promotion_program",
                "promo_code_usage": "no_code_needed",
                "promo_applicability": "on_next_order",
                "discount_apply_on": "on_order",
                "discount_percentage": 10,
            }
        )
        self.promo_programs |= self.auto_promo_program_next

        self.code_promo_program_free_product = self.env["coupon.program"].create(
            {
                "name": "Promo Program - Buy 3 Whiteboard Pen, Get 1 Magnetic Board",
                "program_type": "promotion_program",
                "rule_products_domain": "[('name', '=', 'Whiteboard Pen')]",
                "promo_code_usage": "code_needed",
                "promo_code": "board",
                "reward_type": "product",
                "rule_min_quantity": 3,
                "reward_product_id": self.magnetic_board.id,
                "reward_product_quantity": 1,
            }
        )
        self.promo_programs |= self.code_promo_program_free_product

        # coupon program -> free product
        self.coupon_program = self.env["coupon.program"].create(
            {
                "name": "Coupon Program - Buy 3 Take 2 Free Product",
                "program_type": "coupon_program",
                "rule_products_domain": "[('name', '=', 'Desk Organizer')]",
                "reward_type": "product",
                "rule_min_quantity": 3,
                "reward_product_id": self.desk_organizer.id,
                "reward_product_quantity": 2,
            }
        )

        # Create coupons for the coupon program and change the code
        # to be able to use them in the frontend tour.
        self.env["coupon.generate.wizard"].with_context(
            {"active_id": self.coupon_program.id}
        ).create({"nbr_coupons": 4}).generate_coupon()
        (
            self.coupon1,
            self.coupon2,
            self.coupon3,
            self.coupon4,
        ) = self.coupon_program.coupon_ids
        self.coupon1.write({"code": "1234"})
        self.coupon2.write({"code": "5678"})
        self.coupon3.write({"code": "1357"})
        self.coupon4.write({"code": "2468"})

    def test_pos_coupon_tour_basic(self):
        """PoS Coupon Basic Tour"""

        # Set the programs to the pos config.
        # Remove fiscal position and pricelist.
        with Form(self.main_pos_config) as pos_config:
            pos_config.tax_regime_selection = False
            pos_config.use_pricelist = False
            pos_config.pricelist_id = self.env["product.pricelist"].create(
                {"name": "PoS Default Pricelist",}
            )
            pos_config.use_coupon_programs = True
            pos_config.coupon_program_ids.add(self.coupon_program)
            for promo_program in self.promo_programs:
                pos_config.promo_program_ids.add(promo_program)

        self.main_pos_config.open_session_cb()

        ##
        # Tour Part 1
        # This part will generate coupons for `auto_promo_program_next`
        # that will be used in the second part of the tour.
        #

        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosCouponTour1",
            login="accountman",
        )

        # check coupon usage
        self.assertEqual(
            self.coupon1.state, "used", msg="`1234` coupon should have been used."
        )
        self.assertEqual(
            self.coupon2.state,
            "new",
            msg="`5678` coupon code is used but was eventually freed.",
        )
        # check pos_order_count in each program
        self.assertEqual(self.auto_promo_program_current.pos_order_count, 4)
        self.assertEqual(self.auto_promo_program_next.pos_order_count, 0)
        self.assertEqual(self.code_promo_program.pos_order_count, 1)
        self.assertEqual(self.code_promo_program_free_product.pos_order_count, 1)
        self.assertEqual(self.coupon_program.pos_order_count, 1)
        # check number of generated coupons
        self.assertEqual(len(self.auto_promo_program_next.coupon_ids), 6)
        # check number of orders in the session
        pos_session = self.main_pos_config.current_session_id
        self.assertEqual(
            len(pos_session.order_ids), 6, msg="6 orders were made in tour part1."
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

        # use here the generated coupon
        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosCouponTour2",
            login="accountman",
        )
        self.assertEqual(self.coupon4.state, "new")
        self.assertEqual(promo_coupon4.state, "new")
        # check pos_order_count in each program
        self.assertEqual(self.auto_promo_program_current.pos_order_count, 6)
        self.assertEqual(self.auto_promo_program_next.pos_order_count, 2)
        self.assertEqual(self.code_promo_program.pos_order_count, 2)
        self.assertEqual(self.coupon_program.pos_order_count, 3)

    def test_pos_coupon_tour_max_amount(self):
        """PoS Coupon Basic Tour"""

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

        # create a promo program
        self.promo_program_max_amount = self.env["coupon.program"].create(
            {
                "name": "Promo Program - Max Amount",
                "program_type": "promotion_program",
                "rule_products_domain": '[["product_variant_ids","=","Promo Product"]]',
                "discount_max_amount": 40,
                "reward_type": "discount",
                "promo_code_usage": "no_code_needed",
                "discount_type": "percentage",
                "discount_percentage": 100,
                "discount_apply_on": "specific_products",
                "discount_specific_product_ids": (
                    self.productA | self.productB
                ).ids,
            }
        )

        with Form(self.main_pos_config) as pos_config:
            pos_config.tax_regime_selection = False
            pos_config.use_pricelist = False
            pos_config.pricelist_id = self.env["product.pricelist"].create(
                {"name": "PoS Default Pricelist", }
            )
            pos_config.use_coupon_programs = True
            pos_config.coupon_program_ids.add(self.coupon_program)
            pos_config.coupon_program_ids.add(self.promo_program_max_amount)

        self.main_pos_config.open_session_cb()

        self.start_tour(
            "/pos/web?config_id=%d" % self.main_pos_config.id,
            "PosCouponTour3",
            login="accountman",
        )
